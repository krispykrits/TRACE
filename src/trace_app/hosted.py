"""Compose the hosted worker and report access with the existing source adapters."""

from __future__ import annotations

import os
import threading
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from trace_app.adapters.models.journal import ModelPricing
from trace_app.adapters.sources.local_investigator import (
    LocalEvidenceAuthority,
    LocalInvestigatorProfile,
    LocalSupportReviews,
)
from trace_app.adapters.storage.postgres.evidence import PostgresEvidenceStore
from trace_app.adapters.storage.postgres.execution import PostgresExecutionLedger
from trace_app.adapters.storage.postgres.jobs import PostgresJobs
from trace_app.adapters.storage.postgres.reports import PostgresReportReader
from trace_app.adapters.storage.postgres.workflow import PostgresWorkflowStore
from trace_app.adapters.storage.sqlite.investigations import SQLiteInvestigationStore
from trace_app.adapters.tools.local import (
    LocalToolBackend,
    LocalToolSources,
    LoggingToolAudit,
)
from trace_app.evidence.models import _parse_utc
from trace_app.investigation.execution import ExecutionIdentity, ExecutionSession
from trace_app.investigation.models import (
    EvidenceSnapshot,
    Investigation,
    StoreAccessError,
)
from trace_app.investigation.provider_policy import ProviderScope, SourceAccessPolicy
from trace_app.investigation.reports import ReportAccess
from trace_app.investigation.tools import (
    ToolCall,
    ToolPayload,
    ToolPolicy,
    ToolScope,
    ToolSession,
)
from trace_app.investigation.worker import InvestigationWorker
from trace_app.investigation.workflow import BoundedInvestigation, WorkflowOptions


class SourceTools:
    """Read the configured source capture while retaining the hosted job identity."""

    def __init__(self, profile: LocalInvestigatorProfile) -> None:
        self.profile = profile
        self.backend = LocalToolBackend(
            LocalToolSources(
                profile.evidence_db, profile.corpus_db, profile.index_root
            ),
            read_clock=lambda: datetime.fromtimestamp(profile.clock(), UTC),
        )

    def execute(
        self, call: ToolCall, scope: ToolScope, policy: ToolPolicy, *, timeout_ms: int
    ) -> ToolPayload:
        self.profile.current()
        source_scope = replace(
            scope, investigation_id=self.profile.source_investigation_id
        )
        return self.backend.execute(call, source_scope, policy, timeout_ms=timeout_ms)


def _scope(
    profile: LocalInvestigatorProfile,
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
    profile: LocalInvestigatorProfile,
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
    def __init__(self, dsn: str, profile: LocalInvestigatorProfile) -> None:
        self.dsn, self.profile = dsn, profile

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
        with SQLiteInvestigationStore(
            self.profile.evidence_db, read_only=True
        ) as source:
            source_job = source.get_investigation(
                self.profile.source_investigation_id,
                access_scope=self.profile.evidence.access_scope,
            )
            self.profile.check_job(source_job)
            snapshot = source.get_snapshot(
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
                and e.record.service in self.profile.evidence.allowed_services
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
        execution = ExecutionSession(
            identity,
            self.profile.policy,
            PostgresExecutionLedger(self.dsn),
            ModelPricing("azure-luna-global-ceiling-2026-09-22.v1", 250, 750),
        )
        tools = ToolSession(
            SourceTools(self.profile),
            ToolScope(
                job.investigation_id,
                identity.correlation_id,
                self.profile.evidence,
                self.profile.knowledge,
            ),
            LoggingToolAudit(),
            ToolPolicy(max_attempts=self.profile.policy.max_tool_calls),
            execution=execution,
        )
        workflow = BoundedInvestigation(
            store,
            tools,
            None,
            authority,
            LocalSupportReviews(self.profile),
            execution,
            scope,
            options=WorkflowOptions(evidence_only=True),
        )
        try:
            workflow.run()
        finally:
            workflow.close()


def main() -> None:
    dsn = os.environ["TRACE_POSTGRES_DSN"]
    from psycopg.conninfo import conninfo_to_dict

    settings = conninfo_to_dict(dsn)
    if settings.get("sslmode") != "verify-full" or not settings.get("host"):
        raise ValueError("PostgreSQL must use a hostname and sslmode=verify-full.")
    profile = LocalInvestigatorProfile(Path(os.environ["TRACE_SOURCE_PROFILE"]))
    worker = InvestigationWorker(
        PostgresJobs(dsn),
        HostedProcessor(dsn, profile),
        lease_seconds=min(3600, (profile.policy.deadline_ms + 999) // 1000 + 10),
    )
    worker.run(threading.Event())


if __name__ == "__main__":
    main()
