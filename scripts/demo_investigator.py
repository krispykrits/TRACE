"""Explicit offline, hand-authored model/review simulation using the real use case."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.demo_integration import AT, IntegrationFixture, integration_fixture
from trace_app.adapters.models.journal import SqliteProviderJournal
from trace_app.adapters.retrieval.local_index import load_index
from trace_app.adapters.storage.sqlite.corpus import SQLiteCorpusStore
from trace_app.adapters.storage.sqlite.investigations import SQLiteInvestigationStore
from trace_app.bootstrap import (
    create_execution_session,
    create_investigation_workflow,
    create_tool_session,
)
from trace_app.investigation.assessment_validation import SupportDecision
from trace_app.investigation.execution import ExecutionIdentity, ExecutionPolicy
from trace_app.investigation.provider import (
    AdmissionGuard,
    ModelConfiguration,
    ModelErrorCode,
    ModelPricing,
    ModelProviderError,
    ModelReply,
    ModelRequest,
    ModelResult,
    ModelUsage,
    validate_model_reply,
)
from trace_app.investigation.provider_policy import (
    AuthorizedEvidence,
    EvidenceField,
    PolicyModelProvider,
    ProviderScope,
    Sensitivity,
    SourceKind,
)
from trace_app.investigation.tools import ToolPolicy
from trace_app.investigation.workflow import WORKFLOW_PROMPT, WorkflowOptions
from trace_app.investigation.workflow_prompt import ASSESSMENT_PROMPT
from trace_app.knowledge.models import canonical, digest
from trace_app.runtime.logging import configure_logging

DEMO_PRICING = ModelPricing("offline-simulation-price.v1", 1, 1)
DEMO_POLICY = ExecutionPolicy(
    configuration_id="bounded-workflow.v1",
    max_tool_calls=100,
    max_corrections=1,
    max_input_tokens=20_000,
    max_output_tokens=2048,
    max_total_tokens=70_000,
)


@dataclass
class Clock:
    now: float = AT.timestamp()

    def __call__(self) -> float:
        return self.now


@dataclass
class ScriptedReviews:
    """Synthetic port records only; no model text or actual human endorsement."""

    scope: ProviderScope
    endorsed: bool = False
    decisions: dict[str, tuple[SupportDecision, ...]] = field(default_factory=dict)
    claim_ids: tuple[str, ...] = (
        "observation",
        "primary",
        "alternative",
        "assessment-outcome",
    )
    cursor: int = 0

    def read(
        self, scope: ProviderScope, binding_id: str
    ) -> tuple[SupportDecision, ...]:
        if scope != self.scope or not self.endorsed:
            return ()
        if binding_id not in self.decisions:
            claim_id = self.claim_ids[self.cursor % len(self.claim_ids)]
            self.cursor += 1
            self.decisions[binding_id] = (
                SupportDecision(
                    binding_id,
                    claim_id,
                    "supported",
                    "synthetic-reviewer",
                    "Hand-authored simulation record; not actual human endorsement or diagnosis-quality evidence.",
                ),
            )
        return self.decisions[binding_id]


@dataclass
class ScriptedModel:
    """A fake outside the runtime wheel, never a fallback for Azure."""

    guard: AdmissionGuard
    abstained: bool = False
    requests: list[ModelRequest] = field(default_factory=list)
    error: ModelErrorCode | None = None
    transform: Any = None
    after_call: Any = None

    def generate(self, request: ModelRequest) -> ModelResult:
        self.guard.verify(request)
        self.requests.append(request)
        if self.error is not None:
            raise ModelProviderError(self.error)
        context = json.loads(request.source_context)
        frame = context["investigation_context"]
        ids = frame["timeline_evidence_ids"]
        first = ids[0] if ids else context["untrusted_evidence"][0]["citation_id"]
        second = ids[-1] if len(ids) > 1 else first
        primary = {
            "claim": {
                "claim_id": "primary",
                "statement": "A synthetic downstream failure is a proposal requiring review.",
                "citations": [first],
            },
            "service": "payment",
            "cause": "synthetic_mechanism",
            "contradicting_citations": [],
            "causal_basis": "mechanism",
        }
        alternative = {
            **primary,
            "claim": {
                "claim_id": "alternative",
                "statement": "Another explanation remains possible; proximity alone cannot establish cause.",
                "citations": [second],
            },
            "causal_basis": "temporal_only",
        }
        value = {
            "schema_version": "assessment.v2",
            "assessment_status": "abstained" if self.abstained else "supported",
            "observations": [
                {
                    "claim_id": "observation",
                    "statement": "A selected synthetic source records an incident observation.",
                    "citations": [first],
                }
            ],
            "primary_hypothesis": None if self.abstained else primary,
            "alternative_hypotheses": [alternative],
            "uncertainty": "This hand-authored simulation verifies orchestration, not diagnostic quality.",
            "missing_evidence": [
                "Missing captures and omitted context prevent causal certainty."
            ],
            "source_gaps": frame["source_gaps"],
            "abstention_reason": "The available captures cannot distinguish mechanisms."
            if self.abstained
            else None,
            "next_check": {
                "tool": "logs.query",
                "arguments": {
                    "window_start": frame["window_start"],
                    "window_end": frame["window_end"],
                    "limit": 5,
                },
                "reason": "Inspect the same bounded authorized window.",
            },
            "timeline_evidence_ids": ids,
        }
        if self.transform is not None:
            self.transform(value, request)
        if self.after_call is not None:
            self.after_call()
        return validate_model_reply(
            request, ModelReply(json.dumps(value), "offline-response", ModelUsage(0, 0))
        )


@dataclass
class SyntheticAuthority:
    """Explicit synthetic fixture grants plus fresh private SQLite source reads."""

    fixture: IntegrationFixture
    scope: ProviderScope
    clock: Clock
    transmission: bool = True
    access: bool = True
    sensitivity: Sensitivity = Sensitivity.INTERNAL

    def resolve(self, scope: ProviderScope, identity: str) -> AuthorizedEvidence | None:
        if scope != self.scope:
            return None
        at = datetime.fromtimestamp(self.clock(), timezone.utc)
        root = self.fixture.root
        try:
            with SQLiteInvestigationStore(
                root / "evidence.sqlite3", read_only=True
            ) as store:
                snapshot = store.get_snapshot(
                    scope.investigation_id,
                    access_scope=self.fixture.scope.evidence.access_scope,
                )
                event = next(
                    (
                        entry
                        for entry in snapshot.entries
                        if entry.record.evidence_id == identity
                    ),
                    None,
                )
                if event is not None:
                    value = canonical(
                        {
                            "kind": event.kind,
                            "record": event.record.to_dict(),
                            "payload": asdict(event.payload),
                        }
                    )
                    return self._record(
                        identity,
                        event.record.source_revision,
                        SourceKind.SYNTHETIC,
                        value,
                    )
            index = load_index(root / "index")
            with SQLiteCorpusStore(root / "corpus.sqlite3", read_only=True) as corpus:
                chunks = corpus.read_chunks(
                    context=self.fixture.scope.knowledge,
                    at=at,
                    generation_id=index.corpus_generation_id,
                )
                for chunk in chunks:
                    citation_id = "knowledge-" + digest(
                        canonical(
                            {
                                "corpus_generation_id": index.corpus_generation_id,
                                "chunk_id": chunk.chunk_id,
                            }
                        )
                    )
                    if citation_id != identity:
                        continue
                    mapping = {
                        "corpus_generation_id": index.corpus_generation_id,
                        "chunk_id": chunk.chunk_id,
                        "document_sha256": chunk.document_sha256,
                        "section": chunk.section,
                        "start_offset": chunk.start_offset,
                        "end_offset": chunk.end_offset,
                        "metadata": chunk.metadata.to_dict(),
                    }
                    value = canonical(
                        {
                            "passage": {"citation_id": identity, "text": chunk.text},
                            "citation": mapping,
                        }
                    )
                    return self._record(
                        identity,
                        chunk.metadata.source_revision,
                        SourceKind.RUNBOOK,
                        value,
                    )
        except Exception:
            return None
        return None

    def _record(
        self, identity: str, revision: str, kind: SourceKind, content: str
    ) -> AuthorizedEvidence:
        # Explicit fictional fixture permission; never derive real transmission rights from repository access.
        return AuthorizedEvidence(
            identity,
            "synthetic-fixture-source",
            revision,
            kind,
            (EvidenceField("content", content, self.sensitivity, True),),
            self.access,
            self.transmission,
            True,
            True,
            AT.timestamp() + 3600,
        )


def compose(
    fixture: IntegrationFixture,
    *,
    abstained: bool = False,
    reviewed: bool = False,
    options: WorkflowOptions = WorkflowOptions(),
    policy: ExecutionPolicy = DEMO_POLICY,
):
    clock = Clock()
    with SQLiteInvestigationStore(fixture.root / "evidence.sqlite3") as store:
        claimed = store.claim_next(at=AT, lease_seconds=120)
    assert claimed is not None and claimed.active_attempt_id is not None
    scope = ProviderScope("synthetic-workflow-operator", claimed.investigation_id)
    identity = ExecutionIdentity(
        scope.investigation_id,
        claimed.active_attempt_id,
        fixture.scope.correlation_id,
        fixture.scope.evidence.access_scope,
    )
    execution = create_execution_session(
        evidence_db=fixture.root / "evidence.sqlite3",
        identity=identity,
        pricing=DEMO_PRICING,
        policy=policy,
        clock=clock,
    )
    tools = create_tool_session(
        evidence_db=fixture.root / "evidence.sqlite3",
        corpus_db=fixture.root / "corpus.sqlite3",
        index_root=fixture.root / "index",
        scope=fixture.scope,
        policy=ToolPolicy(max_attempts=100, call_timeout_ms=10_000),
        execution=execution,
        read_clock=lambda: datetime.fromtimestamp(clock(), timezone.utc),
    )
    authority = SyntheticAuthority(fixture, scope, clock)
    guard = AdmissionGuard(b"nonfunctional-offline-workflow-capability" * 2, clock)
    model = ScriptedModel(guard, abstained)
    reviews = ScriptedReviews(
        scope,
        reviewed,
        claim_ids=("observation", "alternative", "assessment-outcome")
        if abstained
        else ("observation", "primary", "alternative", "assessment-outcome"),
    )
    configuration = ModelConfiguration(
        "offline-simulation",
        "hand-authored-fixture",
        "offline-workflow.v1",
        "scripted-model.v1",
        mode="offline_test",
    )
    journal = SqliteProviderJournal(
        fixture.root / "provider.sqlite3",
        DEMO_PRICING,
        monthly_limit_nusd=20_000_000_000,
        initial_spend_nusd=0,
        now=clock(),
    )
    provider = PolicyModelProvider(
        configuration,
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
    workflow = create_investigation_workflow(
        evidence_db=fixture.root / "evidence.sqlite3",
        tools=tools,
        provider=provider,
        authority=authority,
        reviews=reviews,
        execution=execution,
        scope=scope,
        options=options,
        clock=clock,
    )
    return workflow, model, authority, reviews, clock


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="private JSON artifact for the offline demonstration",
    )
    args = parser.parse_args()
    configure_logging()
    results = []
    for case_id, abstained, error in (
        ("c01", False, None),
        ("c04", True, None),
        ("c01", False, ModelErrorCode.TIMEOUT),
    ):
        with integration_fixture(case_id) as fixture:
            workflow, model, _, _, _ = compose(
                fixture, abstained=abstained, reviewed=True
            )
            try:
                model.error = error
                result = workflow.run()
                data = result.read(workflow.scope)
                data["demonstration_role"] = "offline_hand_authored_simulation"
                data["actual_human_review"] = False
                data["actual_provider_calls"] = 0
                results.append(data)
            finally:
                workflow.close()
    descriptor = os.open(
        args.output, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "w") as stream:
        json.dump(
            {"artifact_role": "offline_simulation", "runs": results}, stream, indent=2
        )
        stream.write("\n")
    print(
        json.dumps(
            {"runs": len(results), "paid_calls": 0, "actual_human_review": False}
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
