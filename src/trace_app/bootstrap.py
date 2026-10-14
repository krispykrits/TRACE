"""Composition roots: only this boundary selects application adapters."""

from __future__ import annotations

import secrets
import time
from collections.abc import Mapping
from datetime import datetime
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
) -> ToolSession:
    return ToolSession(
        LocalToolBackend(
            LocalToolSources(evidence_db, corpus_db, index_root), read_clock=read_clock
        ),
        scope,
        LoggingToolAudit(),
        policy,
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
