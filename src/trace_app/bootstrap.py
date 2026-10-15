"""Composition roots: only this boundary selects application adapters."""

from __future__ import annotations

import os
import secrets
import time
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from trace_app.adapters.models.azure import (
    AzureModelSettings,
    AzureResponsesTransport,
    load_azure_settings,
)
from trace_app.adapters.models.journal import ModelPricing, SqliteProviderJournal
from trace_app.adapters.models.process import ProcessModelProvider
from trace_app.adapters.retrieval.exact_scoring import LocalExactScorer
from trace_app.adapters.storage.sqlite.execution import SqliteExecutionLedger
from trace_app.adapters.storage.sqlite.workflow import SQLiteWorkflowStore
from trace_app.adapters.tools.local import (
    LocalToolBackend,
    LocalToolSources,
    LoggingToolAudit,
)
from trace_app.demo.fixtures import CustomerFixture, NotificationFixture, PaymentFixture
from trace_app.demo.order_workflow import OrderWorkflow
from trace_app.investigation.assessment_context import (
    AssessmentBoundaryError,
    AssessmentContext,
    ToolCitationResolver,
)
from trace_app.investigation.assessment_validation import (
    AssessmentValidator,
    SupportReviewReader,
)
from trace_app.investigation.bundle import EvidencePackage
from trace_app.investigation.execution import (
    ExecutionIdentity,
    ExecutionPolicy,
    ExecutionSession,
)
from trace_app.investigation.local_service import LocalInvestigator
from trace_app.investigation.models import (
    EvidenceSnapshot,
    Investigation,
    StoreStateError,
)
from trace_app.investigation.provider import (
    AdmissionGuard,
    ModelCapabilities,
    ModelConfiguration,
    ModelTransport,
)
from trace_app.investigation.provider_policy import (
    EvidenceAuthority,
    PolicyModelProvider,
    PromptTemplate,
    ProviderScope,
)
from trace_app.investigation.tools import ToolPolicy, ToolScope, ToolSession
from trace_app.investigation.workflow import BoundedInvestigation, WorkflowOptions
from trace_app.knowledge.index import IndexGeneration
from trace_app.knowledge.ports import CorpusReader, Encoder
from trace_app.knowledge.search import SearchService


def create_model_provider(
    configuration: ModelConfiguration,
    capabilities: ModelCapabilities,
    transport: ModelTransport,
    *,
    credential_present: bool,
    admission_guard: AdmissionGuard | None = None,
) -> ProcessModelProvider:
    """Explicit composition; live calls additionally require admission receipts."""
    return ProcessModelProvider(
        configuration,
        capabilities,
        transport,
        credential_present=credential_present,
        admission_guard=admission_guard,
    )


def create_azure_model_provider(
    settings: AzureModelSettings,
    api_key: str,
    *,
    authority: EvidenceAuthority,
    scope: ProviderScope,
    prompts: Mapping[str, PromptTemplate],
    journal_path: Path,
    monthly_limit_nusd: int,
    initial_spend_nusd: int,
    read_clock: Callable[[], float] = time.time,
    execution: ExecutionSession | None = None,
) -> PolicyModelProvider:
    """Explicit, policy-gated composition; a missing source authority never defaults."""
    guard = AdmissionGuard(secrets.token_bytes(32), read_clock)
    transport = AzureResponsesTransport(settings, api_key, guard)
    process = create_model_provider(
        settings.configuration(),
        settings.capabilities(),
        transport,
        credential_present=bool(api_key),
        admission_guard=guard,
    )
    # Long-context cached-write input and long-context output ceiling rates.
    # Conservative estimates, not an Azure account-wide billing hard cap.
    journal = SqliteProviderJournal(
        journal_path,
        ModelPricing("azure-luna-global-ceiling-2026-09-22.v1", 250, 750),
        monthly_limit_nusd=monthly_limit_nusd,
        initial_spend_nusd=initial_spend_nusd,
        now=read_clock(),
    )
    if execution is not None and execution.pricing != journal.pricing:
        raise ValueError(
            "Execution and monthly journals require the same pricing snapshot."
        )
    return PolicyModelProvider(
        settings.configuration(),
        process,
        authority,
        journal,
        guard,
        scope,
        prompts,
        known_secrets=(api_key,),
        read_clock=read_clock,
        execution=execution,
    )


def create_azure_model_provider_from_files(
    setup_path: Path,
    secrets_path: Path,
    *,
    authority: EvidenceAuthority,
    scope: ProviderScope,
    prompts: Mapping[str, PromptTemplate],
    journal_path: Path,
    monthly_limit_nusd: int,
    initial_spend_nusd: int,
    read_clock: Callable[[], float] = time.time,
    execution: ExecutionSession | None = None,
) -> PolicyModelProvider:
    """Load explicit private files and return only the gated application interface."""
    settings, api_key = load_azure_settings(setup_path, secrets_path)
    return create_azure_model_provider(
        settings,
        api_key,
        authority=authority,
        scope=scope,
        prompts=prompts,
        journal_path=journal_path,
        monthly_limit_nusd=monthly_limit_nusd,
        initial_spend_nusd=initial_spend_nusd,
        read_clock=read_clock,
        execution=execution,
    )


def create_assessment_validator(
    package: EvidencePackage,
    *,
    scope: ProviderScope,
    tools: ToolSession,
    reviews: SupportReviewReader,
) -> AssessmentValidator:
    if tools.investigation_id != scope.investigation_id:
        raise AssessmentBoundaryError("scope_mismatch")
    context = AssessmentContext.from_package(package, scope)
    return AssessmentValidator(context, ToolCitationResolver(tools, context), reviews)


def create_tool_session(
    *,
    evidence_db: Path,
    corpus_db: Path,
    index_root: Path,
    scope: ToolScope,
    policy: ToolPolicy = ToolPolicy(),
    read_clock: Callable[[], datetime] | None = None,
    execution: ExecutionSession | None = None,
) -> ToolSession:
    return ToolSession(
        LocalToolBackend(
            LocalToolSources(evidence_db, corpus_db, index_root), read_clock=read_clock
        ),
        scope,
        LoggingToolAudit(),
        policy,
        execution=execution,
    )


def create_execution_session(
    *,
    evidence_db: Path,
    identity: ExecutionIdentity,
    pricing: ModelPricing,
    policy: ExecutionPolicy = ExecutionPolicy(),
    clock: Callable[[], float] = time.time,
) -> ExecutionSession:
    """Bind shared limits to an existing active durable job; no transport/source grants."""
    return ExecutionSession(
        identity, policy, SqliteExecutionLedger(evidence_db), pricing, clock=clock
    )


def create_investigation_workflow(
    *,
    evidence_db: Path,
    tools: ToolSession,
    provider: PolicyModelProvider | None,
    authority: EvidenceAuthority,
    reviews: SupportReviewReader,
    execution: ExecutionSession,
    scope: ProviderScope,
    options: WorkflowOptions = WorkflowOptions(),
    clock: Callable[[], float] = time.time,
) -> BoundedInvestigation:
    """Explicit granted composition; no default source authority, model or reviewer."""
    return BoundedInvestigation(
        SQLiteWorkflowStore(evidence_db),
        tools,
        provider,
        authority,
        reviews,
        execution,
        scope,
        options=options,
        clock=clock,
    )


def create_search_service(
    reader: CorpusReader, index: IndexGeneration, encoder: Encoder | None = None
) -> SearchService:
    return SearchService(reader, index, encoder, scorer=LocalExactScorer())


def create_demo_order_workflow() -> OrderWorkflow:
    return OrderWorkflow(
        customers=CustomerFixture(),
        payments=PaymentFixture(),
        notifications=NotificationFixture(),
    )


def create_local_investigator(
    profile_path: Path,
    *,
    clock: Callable[[], float] = time.time,
    fixture_provider: Callable[
        [ProviderScope, EvidenceAuthority, ExecutionSession], PolicyModelProvider
    ]
    | None = None,
) -> LocalInvestigator:
    """Owner-managed local sources; offline models require an external explicit harness."""
    from trace_app.adapters.sources.local_investigator import (
        LocalEvidenceAuthority,
        LocalInvestigatorProfile,
        LocalSupportReviews,
    )
    from trace_app.adapters.storage.sqlite.investigations import (
        SQLiteInvestigationStore,
    )
    from trace_app.adapters.storage.sqlite.reports import SQLiteReportReader
    from trace_app.investigation.provider_policy import SourceAccessPolicy
    from trace_app.investigation.reports import ReportAccess
    from trace_app.investigation.tools import ToolScope
    from trace_app.investigation.workflow import WORKFLOW_PROMPT
    from trace_app.investigation.workflow_prompt import ASSESSMENT_PROMPT

    profile = LocalInvestigatorProfile(profile_path, clock=clock)
    jobs = SQLiteInvestigationStore(profile.evidence_db)

    def snapshot() -> EvidenceSnapshot:
        profile.current()
        with SQLiteInvestigationStore(profile.evidence_db, read_only=True) as store:
            source_job = store.get_investigation(
                profile.source_investigation_id,
                access_scope=profile.evidence.access_scope,
            )
            profile.check_job(source_job)
            return store.get_snapshot(
                profile.source_investigation_id,
                access_scope=profile.evidence.access_scope,
            )

    def reports(investigation_id: str) -> ReportAccess:
        scope = profile.scope(investigation_id)
        return ReportAccess(
            SQLiteReportReader(profile.evidence_db),
            SourceAccessPolicy(
                LocalEvidenceAuthority(profile, scope), scope, clock=clock
            ),
            LocalSupportReviews(profile),
            scope,
            profile.evidence.access_scope,
            profile.clearance,
        )

    def workflow(job: Investigation, provider_name: str) -> BoundedInvestigation:
        if job.active_attempt_id is None:
            raise StoreStateError("An active attempt is required.")
        scope = profile.scope(job.investigation_id)
        identity = ExecutionIdentity(
            job.investigation_id,
            job.active_attempt_id,
            "cli-" + job.investigation_id,
            profile.evidence.access_scope,
        )
        authority = LocalEvidenceAuthority(profile, scope)
        if provider_name not in ("azure", "evidence-only") and not (
            provider_name == "offline-fixture" and fixture_provider is not None
        ):
            raise ValueError(
                "Offline fixtures require the explicit development harness."
            )
        pricing = ModelPricing("azure-luna-global-ceiling-2026-09-22.v1", 250, 750)
        execution = create_execution_session(
            evidence_db=profile.evidence_db,
            identity=identity,
            pricing=pricing,
            policy=profile.policy,
            clock=clock,
        )
        tools = create_tool_session(
            evidence_db=profile.evidence_db,
            corpus_db=profile.corpus_db,
            index_root=profile.index_root,
            scope=ToolScope(
                job.investigation_id,
                identity.correlation_id,
                profile.evidence,
                profile.knowledge,
            ),
            policy=ToolPolicy(max_attempts=profile.policy.max_tool_calls),
            execution=execution,
            read_clock=lambda: datetime.fromtimestamp(clock(), UTC),
        )
        provider = None
        if provider_name == "offline-fixture" and fixture_provider is not None:
            provider = fixture_provider(scope, authority, execution)
        if provider_name == "azure":
            if os.environ.get("TRACE_ALLOW_PAID_LIVE") != "1":
                raise ValueError("Azure requires explicit paid-live opt-in.")
            data = profile.current()["azure"]
            provider = create_azure_model_provider_from_files(
                Path(data["setup_path"]),
                Path(data["secrets_path"]),
                authority=authority,
                scope=scope,
                prompts={WORKFLOW_PROMPT: ASSESSMENT_PROMPT},
                journal_path=Path(data["journal_path"]),
                monthly_limit_nusd=data["monthly_limit_nusd"],
                initial_spend_nusd=data["initial_spend_nusd"],
                execution=execution,
                read_clock=clock,
            )
        return create_investigation_workflow(
            evidence_db=profile.evidence_db,
            tools=tools,
            provider=provider,
            authority=authority,
            reviews=LocalSupportReviews(profile),
            execution=execution,
            scope=scope,
            options=WorkflowOptions(evidence_only=provider_name == "evidence-only"),
            clock=clock,
        )

    return LocalInvestigator(
        jobs,
        profile.evidence,
        snapshot,
        workflow,
        reports,
        profile.check_job,
        clock=clock,
        lease_seconds=(profile.policy.deadline_ms + 999) // 1000 + 5,
        allowed_providers=("azure", "evidence-only", "offline-fixture")
        if fixture_provider
        else ("azure", "evidence-only"),
    )
