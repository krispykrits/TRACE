"""Hand-authored reports and explicitly synthetic support-review decisions."""

from __future__ import annotations

import json
from dataclasses import dataclass, field, replace
from typing import Any

from tests.fixtures.provider_policy import (
    SETTINGS,
    Clock,
    MemoryJournal,
    RecordingProvider,
)
from trace_app.investigation.assessment_context import (
    AssessmentBoundaryError,
    AssessmentContext,
)
from trace_app.investigation.assessment_schema import ASSESSMENT_VERSION
from trace_app.investigation.assessment_validation import (
    AssessmentValidator,
    ProtectedAssessment,
    SupportDecision,
)
from trace_app.investigation.bundle import EvidencePackage
from trace_app.investigation.provider import (
    AdmissionGuard,
    ModelCallBounds,
    ModelReply,
    ModelUsage,
)
from trace_app.investigation.provider_policy import (
    AuthorizedEvidence,
    EvidenceField,
    EvidenceSelection,
    PolicyModelProvider,
    PromptTemplate,
    ProviderCall,
    ProviderScope,
    Sensitivity,
    SourceKind,
)
from trace_app.knowledge.models import canonical, digest

SCOPE = ProviderScope("assessment-fixture-user", "assessment-fixture-investigation")
START, END = "2026-10-12T12:00:00Z", "2026-10-12T12:10:00Z"


@dataclass
class Authority:
    scope: ProviderScope
    records: dict[str, AuthorizedEvidence]

    def resolve(self, scope: ProviderScope, identity: str) -> AuthorizedEvidence | None:
        return self.records.get(identity) if scope == self.scope else None


@dataclass
class Reviews:
    scope: ProviderScope
    decisions: dict[str, tuple[SupportDecision, ...]] = field(default_factory=dict)

    def read(
        self, scope: ProviderScope, binding_id: str
    ) -> tuple[SupportDecision, ...]:
        if scope != self.scope:
            raise AssessmentBoundaryError("review_denied")
        return self.decisions.get(binding_id, ())

    def endorse(self, handle: ProtectedAssessment, **changes: Any) -> None:
        for task in handle.review_packet(self.scope)["tasks"]:
            decision = SupportDecision(
                task["binding_id"],
                task["claim_id"],
                "supported",
                "synthetic-reviewer",
                "Synthetic rubric decision; not real human acceptance.",
            )
            self.decisions[task["binding_id"]] = (replace(decision, **changes),)


@dataclass
class Resolver:
    scope: ProviderScope
    denied: set[str] = field(default_factory=set)
    revision: str = "revision-1"
    failure: bool = False

    def resolve(self, scope: ProviderScope, identity: str) -> dict[str, object]:
        if self.failure:
            raise AssessmentBoundaryError("execution_failure")
        if scope != self.scope or identity in self.denied:
            raise AssessmentBoundaryError("citation_denied")
        return {
            "source_revision": self.revision,
            "kind": "evidence",
            "observed_at": START,
            "collected_at": END,
        }


def package(scope: ProviderScope = SCOPE) -> EvidencePackage:
    events = [
        {
            "evidence_id": identity,
            "kind": "log",
            "causal_status": "observed",
            "payload": {},
            "record": {
                "evidence_id": identity,
                "observed_at": START,
                "collected_at": END,
                "source_revision": "revision-1",
            },
        }
        for identity in ("evidence-1", "evidence-2")
    ]
    data = {
        "content_role": "untrusted_source_data",
        "timeline": {
            "status": "incomplete",
            "failure_code": None,
            "events": events,
            "sources": [{"source": "logs", "status": "available"}],
            "truncated": False,
            "query": {"window_start": START, "window_end": END},
        },
        "knowledge": {
            "context": {
                "status": "empty",
                "data": {"citations": {}, "passages": []},
                "incomplete": False,
                "omitted": [],
            }
        },
        "references": {
            "all_resolved": True,
            "evidence": [e["evidence_id"] for e in events],
            "knowledge": [],
        },
        "missing_knowledge": True,
    }
    return EvidencePackage(
        "partial", data, digest(canonical(data)), scope.investigation_id, (), None
    )


def report(abstained: bool = False) -> dict[str, Any]:
    observation = {
        "claim_id": "observation-1",
        "statement": "The selected evidence records a timeout.",
        "citations": ["evidence-1"],
    }
    hypothesis = {
        "claim": {
            "claim_id": "hypothesis-1",
            "statement": "A downstream timeout mechanism is plausible.",
            "citations": ["evidence-1"],
        },
        "service": "payment",
        "cause": "downstream_timeout",
        "contradicting_citations": ["evidence-2"],
        "causal_basis": "mechanism",
    }
    alternative = {
        **hypothesis,
        "claim": {
            "claim_id": "alternative-1",
            "statement": "An unrelated deployment remains a competing explanation to investigate.",
            "citations": ["evidence-2"],
        },
        "contradicting_citations": ["evidence-1"],
        "causal_basis": "temporal_only",
    }
    return {
        "schema_version": ASSESSMENT_VERSION,
        "assessment_status": "abstained" if abstained else "supported",
        "observations": [observation],
        "primary_hypothesis": None if abstained else hypothesis,
        "alternative_hypotheses": [alternative],
        "uncertainty": "A cited observation supports a hypothesis, not causal certainty; contradictions remain.",
        "missing_evidence": ["No supporting knowledge excerpt was collected."],
        "source_gaps": ["knowledge:missing"],
        "abstention_reason": "The captures cannot distinguish the competing mechanisms."
        if abstained
        else None,
        "next_check": {
            "tool": "logs.query",
            "arguments": {"window_start": START, "window_end": END, "limit": 5},
            "reason": "Inspect the relevant bounded downstream logs.",
        },
        "timeline_evidence_ids": ["evidence-1", "evidence-2"],
    }


def fixture(
    value: dict[str, Any] | None = None,
    *,
    sensitivity: Sensitivity = Sensitivity.INTERNAL,
):
    clock = Clock()
    records = {
        identity: AuthorizedEvidence(
            identity,
            "fixture-source",
            "revision-1",
            SourceKind.SYNTHETIC,
            (
                EvidenceField(
                    "observation",
                    (
                        "A downstream timeout was recorded."
                        if identity == "evidence-1"
                        else "A downstream probe succeeded while an unrelated customer deployment was recorded."
                    ),
                    sensitivity,
                    True,
                ),
            ),
            True,
            True,
            True,
            True,
            clock() + 3600,
        )
        for identity in ("evidence-1", "evidence-2")
    }
    authority = Authority(SCOPE, records)
    guard = AdmissionGuard(b"nonfunctional-assessment-capability" * 2, clock)
    transport = RecordingProvider(
        guard,
        ModelReply(
            json.dumps(value or report()), "response-fixture", ModelUsage(10, 10)
        ),
    )
    policy = PolicyModelProvider(
        SETTINGS.configuration(),
        transport,
        authority,
        MemoryJournal(),
        guard,
        SCOPE,
        {
            "assessment-prompt.v1": PromptTemplate(
                "Return a JSON assessment.", ASSESSMENT_VERSION
            )
        },
        read_clock=clock,
    )
    response = policy.generate(
        ProviderCall(
            "assessment-prompt.v1",
            tuple(
                EvidenceSelection(identity, "revision-1", ("observation",))
                for identity in records
            ),
            ModelCallBounds(5000, 65536, 256),
        )
    )
    reviews, resolver = Reviews(SCOPE), Resolver(SCOPE)
    validator = AssessmentValidator(
        AssessmentContext.from_package(package(), SCOPE), resolver, reviews
    )
    return validator, response, authority, reviews, resolver
