"""Compose the hosted worker and report access with the existing source adapters."""

from __future__ import annotations

import logging
import os
import secrets
import sys
import threading
from collections.abc import Callable
from dataclasses import replace

from trace_app.adapters.models.azure import (
    AzureResponsesTransport,
    entra_settings,
    entra_token,
)
from trace_app.adapters.models.journal import ModelPricing
from trace_app.adapters.models.process import ProcessModelProvider
from trace_app.adapters.sources.authority import (
    LocalEvidenceAuthority,
    LocalSupportReviews,
)
from trace_app.adapters.sources.postgres_investigator import PostgresInvestigatorProfile
from trace_app.adapters.storage.postgres.evidence import PostgresEvidenceStore
from trace_app.adapters.storage.postgres.execution import PostgresExecutionLedger
from trace_app.adapters.storage.postgres.jobs import PostgresJobs
from trace_app.adapters.storage.postgres.model_journal import PostgresModelJournal
from trace_app.adapters.storage.postgres.reports import PostgresReportReader
from trace_app.adapters.storage.postgres.workflow import PostgresWorkflowStore
from trace_app.adapters.tools.local import LoggingToolAudit
from trace_app.adapters.tools.postgres import PostgresToolBackend
from trace_app.evidence.models import _parse_utc
from trace_app.investigation.assessment_context import AssessmentBoundaryError
from trace_app.investigation.execution import ExecutionIdentity, ExecutionSession
from trace_app.investigation.models import (
    EvidenceSnapshot,
    Investigation,
    StoreAccessError,
)
from trace_app.investigation.provider import AdmissionGuard
from trace_app.investigation.provider_policy import (
    EvidenceAuthority,
    PolicyModelProvider,
    ProviderScope,
    SourceAccessPolicy,
)
from trace_app.investigation.reports import ReportAccess
from trace_app.investigation.tools import (
    ToolCall,
    ToolPayload,
    ToolPolicy,
    ToolScope,
    ToolSession,
)
from trace_app.investigation.worker import InvestigationWorker
from trace_app.investigation.workflow import (
    WORKFLOW_PROMPT,
    BoundedInvestigation,
    WorkflowOptions,
)
from trace_app.investigation.workflow_prompt import ASSESSMENT_PROMPT


class SourceTools:
    """Read the configured source capture while retaining the hosted job identity."""

    def __init__(self, profile: PostgresInvestigatorProfile) -> None:
        self.profile = profile
        self.backend = PostgresToolBackend(profile)

    def execute(
        self, call: ToolCall, scope: ToolScope, policy: ToolPolicy, *, timeout_ms: int
    ) -> ToolPayload:
        return self.backend.execute(call, scope, policy, timeout_ms=timeout_ms)

    def revalidate_scope(self, scope: ToolScope) -> None:
        self.profile.current()
        allowed = set(self.profile.allowed_for_job(scope.investigation_id))
        if (
            replace(
                scope.evidence, allowed_services=self.profile.evidence.allowed_services
            )
            != self.profile.evidence
            or replace(
                scope.knowledge,
                allowed_services=self.profile.knowledge.allowed_services,
            )
            != self.profile.knowledge
            or not set(scope.evidence.allowed_services)
            <= allowed.intersection(self.profile.evidence.allowed_services)
            or not set(scope.knowledge.allowed_services)
            <= allowed.intersection(self.profile.knowledge.allowed_services)
        ):
            raise AssessmentBoundaryError("access_denied")


def _scope(
    profile: PostgresInvestigatorProfile,
    principal: tuple[str, str],
    job_id: str,
    access_scope: str,
) -> ProviderScope:
    if (
        profile.principal_id != f"entra:{principal[0]}:{principal[1]}"
        or profile.evidence.access_scope != access_scope
    ):
        raise StoreAccessError("Source is not accessible.")
    return profile.scope(job_id)


def report_access(
    dsn: str,
    profile: PostgresInvestigatorProfile,
    principal: tuple[str, str],
    job_id: str,
    access_scope: str,
) -> ReportAccess:
    scope = _scope(profile, principal, job_id, access_scope)
    return ReportAccess(
        PostgresReportReader(dsn, principal=principal),
        SourceAccessPolicy(LocalEvidenceAuthority(profile, scope), scope),
        LocalSupportReviews(profile),
        scope,
        access_scope,
        profile.clearance,
    )


class HostedProcessor:
    def __init__(
        self,
        dsn: str,
        profile: PostgresInvestigatorProfile,
        provider: Callable[
            [ProviderScope, EvidenceAuthority, ExecutionSession], PolicyModelProvider
        ]
        | None = None,
    ) -> None:
        self.dsn, self.profile = dsn, profile
        self.provider = provider

    def __call__(self, job: Investigation) -> None:
        if job.active_attempt_id is None:
            raise StoreAccessError("No active attempt.")
        identity = ExecutionIdentity(
            job.investigation_id,
            job.active_attempt_id,
            "worker-" + job.investigation_id,
            job.request.access_scope,
        )
        store = PostgresWorkflowStore(self.dsn)
        with store._jobs._connection() as connection:
            row = store._active(connection, identity)
            principal = (str(row["submitted_tenant"]), str(row["submitted_object"]))
        scope = _scope(
            self.profile, principal, job.investigation_id, job.request.access_scope
        )
        self.profile.check_job(job)
        granted = self.profile.allowed_for_job(job.investigation_id)
        evidence_services = tuple(
            service
            for service in self.profile.evidence.allowed_services
            if service in granted
        )
        knowledge_services = tuple(
            service
            for service in self.profile.knowledge.allowed_services
            if service in granted
        )
        if not evidence_services or not knowledge_services:
            raise StoreAccessError("No source services are authorized.")
        snapshot = self.profile.get_snapshot(
            self.profile.source_investigation_id,
            access_scope=self.profile.evidence.access_scope,
        )
        start, end = (
            _parse_utc(job.request.window_start),
            _parse_utc(job.request.window_end),
        )
        if start < _parse_utc(snapshot.window_start) or end > _parse_utc(
            snapshot.window_end
        ):
            raise StoreAccessError("Requested window is outside the source capture.")
        selected = EvidenceSnapshot(
            tuple(
                e
                for e in snapshot.entries
                if start <= _parse_utc(e.record.observed_at) <= end
                and e.record.service in evidence_services
                and e.record.environment == job.request.environment
            ),
            job.request.window_start,
            job.request.window_end,
            snapshot.sources,
        )
        authority = LocalEvidenceAuthority(self.profile, scope)
        PostgresEvidenceStore(
            store,
            identity,
            SourceAccessPolicy(authority, scope),
            clearance=self.profile.clearance,
        ).ingest_snapshot(selected)
        with PostgresExecutionLedger(self.dsn) as ledger:
            execution = ExecutionSession(
                identity,
                self.profile.policy,
                ledger,
                ModelPricing("azure-luna-global-ceiling-2026-09-22.v1", 250, 750),
            )
            tools = ToolSession(
                SourceTools(self.profile),
                ToolScope(
                    job.investigation_id,
                    identity.correlation_id,
                    replace(self.profile.evidence, allowed_services=evidence_services),
                    replace(
                        self.profile.knowledge, allowed_services=knowledge_services
                    ),
                ),
                LoggingToolAudit(),
                ToolPolicy(
                    max_attempts=self.profile.policy.max_tool_calls,
                    call_timeout_ms=self.profile.policy.tool_timeout_ms,
                ),
                execution=execution,
            )
            workflow = BoundedInvestigation(
                store,
                tools,
                self.provider(scope, authority, execution) if self.provider else None,
                authority,
                LocalSupportReviews(self.profile),
                execution,
                scope,
                options=WorkflowOptions(evidence_only=self.provider is None),
            )
            try:
                result = workflow.run()
                logging.getLogger("trace_app.worker").info(
                    "%s investigation_id=%s status=%s failure_code=%s",
                    "job_completed"
                    if result.execution_status == "completed"
                    else "job_failed",
                    job.investigation_id,
                    result.execution_status,
                    result.failure_code,
                )
            finally:
                workflow.close()


def main() -> None:
    logging.basicConfig(
        level=logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )
    logging.getLogger("trace_app.worker").setLevel(logging.INFO)
    logging.getLogger("trace_app.tools").setLevel(logging.INFO)
    if os.environ.get("TRACE_POSTGRES_AUTH") != "entra":
        raise ValueError("Hosted PostgreSQL requires Entra authentication.")
    dsn = os.environ["TRACE_POSTGRES_DSN"]
    from psycopg.conninfo import conninfo_to_dict

    settings = conninfo_to_dict(dsn)
    if settings.get("sslmode") != "verify-full" or not settings.get("host"):
        raise ValueError("PostgreSQL must use a hostname and sslmode=verify-full.")
    profile = PostgresInvestigatorProfile(dsn, os.environ["TRACE_SOURCE_ID"])
    mode = os.environ.get("TRACE_WORKER_MODE", "azure")
    provider = None
    if mode == "azure":
        azure_settings = entra_settings(dict(os.environ))

        def provider(
            scope: ProviderScope,
            authority: EvidenceAuthority,
            execution: ExecutionSession,
        ) -> PolicyModelProvider:
            guard = AdmissionGuard(secrets.token_bytes(32))
            transport = AzureResponsesTransport(
                azure_settings, "", guard, token_provider=entra_token
            )
            model = ProcessModelProvider(
                azure_settings.configuration(),
                azure_settings.capabilities(),
                transport,
                credential_present=True,
                admission_guard=guard,
            )
            journal = PostgresModelJournal(
                dsn, execution.pricing, monthly_limit_nusd=20_000_000_000
            )
            return PolicyModelProvider(
                azure_settings.configuration(),
                model,
                authority,
                journal,
                guard,
                scope,
                {WORKFLOW_PROMPT: ASSESSMENT_PROMPT},
                execution=execution,
            )
    elif mode != "evidence-only":
        raise ValueError("Unsupported worker mode.")
    worker = InvestigationWorker(
        PostgresJobs(dsn),
        HostedProcessor(dsn, profile, provider),
        lease_seconds=min(3600, (profile.policy.deadline_ms + 999) // 1000 + 10),
    )
    worker.run(threading.Event())


if __name__ == "__main__":
    main()
