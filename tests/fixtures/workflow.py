"""Pure workflow seams: synthetic source envelopes, fake adapters and clock."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
from datetime import timedelta
from typing import Any

from scripts.demo_integration import AT
from scripts.demo_investigator import (
    DEMO_POLICY,
    DEMO_PRICING,
    Clock,
    ScriptedModel,
    ScriptedReviews,
)
from tests.fixtures.execution import Audit, MemoryLedger
from tests.fixtures.provider_policy import MemoryJournal
from trace_app.demo.scenarios import ScenarioConfig, ScenarioSession
from trace_app.evidence.queries import TrustedQueryContext
from trace_app.investigation.execution import (
    ExecutionIdentity,
    ExecutionSession,
    ExecutionState,
)
from trace_app.investigation.models import (
    Investigation,
    InvestigationRequest,
    StoreStateError,
)
from trace_app.investigation.provider import AdmissionGuard, ModelConfiguration
from trace_app.investigation.provider_policy import (
    AuthorizedEvidence,
    EvidenceField,
    PolicyModelProvider,
    ProviderScope,
    Sensitivity,
    SourceKind,
)
from trace_app.investigation.tools import (
    EvidenceArguments,
    ToolPayload,
    ToolPolicy,
    ToolScope,
    ToolSession,
)
from trace_app.investigation.workflow import (
    WORKFLOW_PROMPT,
    WORKFLOW_TRANSITIONS,
    BoundedInvestigation,
    WorkflowOptions,
)
from trace_app.investigation.workflow_prompt import ASSESSMENT_PROMPT
from trace_app.knowledge.context import CONTEXT_VERSION
from trace_app.knowledge.models import CorpusReadContext, canonical


@dataclass
class Authority:
    scope: ProviderScope
    records: dict[str, AuthorizedEvidence]

    def resolve(self, scope, identity):
        return self.records.get(identity) if scope == self.scope else None


@dataclass
class Store:
    job: Investigation
    clock: Clock
    phase_name: str | None = None
    packages: list[Any] = field(default_factory=list)
    publications: list[Any] = field(default_factory=list)
    before_publish: Any = None

    def close(self):
        pass

    def get_investigation(self, identity):
        return self.job

    def active(self, identity):
        if (
            self.job.status != "running"
            or self.job.active_attempt_id != identity.attempt_id
        ):
            raise StoreStateError("inactive")

    def start(self, identity, *, at):
        self.active(identity)
        if self.phase_name is not None:
            raise StoreStateError("duplicate")
        self.phase_name = "started"

    def phase(self, identity, name, *, at):
        self.active(identity)
        if name not in WORKFLOW_TRANSITIONS[self.phase_name]:
            raise StoreStateError("transition")
        self.phase_name = name
        if name == "evidence_only":
            self.job = replace(
                self.job,
                status="completed",
                assessment_status="pending",
                active_attempt_id=None,
            )

    def retain(self, identity, package, *, at):
        self.active(identity)
        self.packages.append(package)
        return f"artifact-{len(self.packages)}"

    def publish(self, publication, *, at):
        if self.before_publish is not None:
            self.before_publish()
        self.active(publication.identity)
        if not publication.is_issued():
            raise StoreStateError("not issued")
        self.publications.append(publication)
        self.job = replace(
            self.job,
            status="completed",
            assessment_status=publication.assessment_status,
            review_status="unreviewed",
            active_attempt_id=None,
        )

    def fail(self, identity, code, *, at):
        if self.job.status in ("cancelled", "expired"):
            return self.job.status
        self.active(identity)
        self.job = replace(
            self.job, status="failed", failure_code=code, active_attempt_id=None
        )
        return "failed"


@dataclass
class Backend:
    snapshot: Any
    calls: list[str] = field(default_factory=list)
    after_call: Any = None
    failure: str | None = None
    transform: Any = None

    def execute(self, call, scope, policy, *, timeout_ms):
        self.calls.append(call.name)
        if self.after_call is not None:
            self.after_call(call)
        if self.failure is not None:
            return ToolPayload("dependency_failure", {}, "source_unavailable")
        if isinstance(call.arguments, EvidenceArguments):
            args = call.arguments
            entries = [
                e
                for e in self.snapshot.entries
                if args.query.kind is None or e.kind == args.query.kind
            ]
            if args.evidence_id is not None:
                entries = [
                    e for e in entries if e.record.evidence_id == args.evidence_id
                ]
            matching = len(entries)
            entries = entries[: args.query.limit]
            data = {
                "content_role": "untrusted_source_data",
                "entries": [
                    {
                        "kind": e.kind,
                        "record": e.record.to_dict(),
                        "payload": asdict(e.payload),
                    }
                    for e in entries
                ],
                "sources": [asdict(source) for source in self.snapshot.sources],
                "matching_count": matching,
                "truncated": matching > len(entries),
            }
            if self.transform is not None:
                self.transform(data)
            return ToolPayload("ok" if entries else "empty", data)
        context = {
            "schema_version": "1",
            "content_role": "untrusted_source_data",
            "passages": [],
            "citations": {},
        }
        return ToolPayload(
            "empty",
            {
                "version": CONTEXT_VERSION,
                "status": "empty",
                "data": context,
                "used_bytes": len(canonical(context).encode()),
                "budget": {"max_bytes": 8192, "max_passages": 5},
                "omitted": [],
                "incomplete": False,
            },
        )


def fixture(
    *, abstained=False, reviewed=False, options=WorkflowOptions(), policy=DEMO_POLICY
):
    clock = Clock()
    snapshot = (
        ScenarioSession(ScenarioConfig("c04" if abstained else "c01", 17))
        .replay(collected_at=AT)
        .snapshot
    )
    scope = ProviderScope("fixture-user", "workflow-fixture")
    identity = ExecutionIdentity(
        scope.investigation_id, 1, "corr-workflow", "local:synthetic"
    )
    job = Investigation(
        scope.investigation_id,
        InvestigationRequest(
            "fixture-key",
            "order",
            "test",
            identity.access_scope,
            snapshot.window_start,
            snapshot.window_end,
        ),
        AT.isoformat(),
        "running",
        "pending",
        "pending",
        1,
        1,
        (AT + timedelta(seconds=120)).isoformat(),
        None,
        None,
    )
    store = Store(job, clock)
    ledger = MemoryLedger(state=ExecutionState(clock(), clock(), clock()))
    execution = ExecutionSession(identity, policy, ledger, DEMO_PRICING, clock=clock)
    backend = Backend(snapshot)
    tool_scope = ToolScope(
        scope.investigation_id,
        identity.correlation_id,
        TrustedQueryContext(
            identity.access_scope,
            "test",
            ("order", "payment", "customer", "notification"),
        ),
        CorpusReadContext(
            "local:knowledge-development",
            "test",
            ("order", "payment"),
            "development_reference",
            snapshot.window_start,
        ),
    )
    tools = ToolSession(
        backend,
        tool_scope,
        Audit(),
        ToolPolicy(max_attempts=100),
        clock=clock,
        execution=execution,
    )
    records = {
        e.record.evidence_id: AuthorizedEvidence(
            e.record.evidence_id,
            "fixture-source",
            e.record.source_revision,
            SourceKind.SYNTHETIC,
            (
                EvidenceField(
                    "content",
                    canonical(
                        {
                            "kind": e.kind,
                            "record": e.record.to_dict(),
                            "payload": asdict(e.payload),
                        }
                    ),
                    Sensitivity.INTERNAL,
                    True,
                ),
            ),
            True,
            True,
            True,
            True,
            clock() + 3600,
        )
        for e in snapshot.entries
    }
    authority = Authority(scope, records)
    guard = AdmissionGuard(b"nonfunctional-workflow-fixture-capability" * 2, clock)
    model = ScriptedModel(guard, abstained)
    reviews = ScriptedReviews(
        scope,
        reviewed,
        claim_ids=("observation", "alternative", "assessment-outcome")
        if abstained
        else ("observation", "primary", "alternative", "assessment-outcome"),
    )
    journal = MemoryJournal()
    provider = PolicyModelProvider(
        ModelConfiguration(
            "offline-simulation",
            "fixture-model",
            "fixture.v1",
            "fixture-adapter.v1",
            mode="offline_test",
        ),
        model,
        authority,
        journal,
        guard,
        scope,
        {WORKFLOW_PROMPT: ASSESSMENT_PROMPT},
        execution=execution,
        read_clock=clock,
        duration_clock=clock,
    )
    workflow = BoundedInvestigation(
        store,
        tools,
        provider,
        authority,
        reviews,
        execution,
        scope,
        options=options,
        clock=clock,
    )
    return workflow, model, authority, reviews, clock, store, backend, ledger, journal
