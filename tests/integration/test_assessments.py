"""Actual SQLite evidence/corpus tools with protected provider projections."""

from __future__ import annotations

import json
import unittest
from dataclasses import asdict, replace
from datetime import timedelta

from scripts.demo_integration import AT, integration_fixture
from tests.fixtures.assessments import Authority, Reviews, report
from tests.fixtures.provider_policy import (
    SETTINGS,
    Clock,
    MemoryJournal,
    RecordingProvider,
)
from trace_app.adapters.storage.sqlite.corpus import SQLiteCorpusStore
from trace_app.bootstrap import create_assessment_validator
from trace_app.investigation.assessment_context import (
    AssessmentBoundaryError,
    AssessmentContext,
)
from trace_app.investigation.assessment_schema import ASSESSMENT_VERSION
from trace_app.investigation.bundle import build_evidence_package
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


def setup_assessment(setup, *, at=AT, denied_knowledge=False):
    session = setup.session()
    package = build_evidence_package(
        session,
        investigation_id=setup.scope.investigation_id,
        query=setup.query,
        knowledge_query="Payment timeout evidence",
        knowledge_service="payment",
    )
    assert package.data is not None
    scope = ProviderScope("synthetic-assessment-operator", package.investigation_id)
    context = AssessmentContext.from_package(package, scope)
    event = next(e for e in package.data["timeline"]["events"] if e["kind"] == "log")
    passage = package.data["knowledge"]["context"]["data"]["passages"][0]
    mapping = package.data["knowledge"]["context"]["data"]["citations"][
        passage["citation_id"]
    ]
    ids = [event["evidence_id"], passage["citation_id"]]
    clock = Clock()
    records = {
        ids[0]: AuthorizedEvidence(
            ids[0],
            "synthetic-log-source",
            event["record"]["source_revision"],
            SourceKind.SYNTHETIC,
            (
                EvidenceField(
                    "observation", event["record"]["event"], Sensitivity.INTERNAL, True
                ),
            ),
            True,
            True,
            True,
            True,
            clock() + 3600,
        ),
        ids[1]: AuthorizedEvidence(
            ids[1],
            "synthetic-knowledge-source",
            mapping["metadata"]["source_revision"],
            SourceKind.RUNBOOK,
            (EvidenceField("excerpt", passage["text"], Sensitivity.INTERNAL, True),),
            True,
            True,
            True,
            True,
            clock() + 3600,
        ),
    }
    value = report()
    value["observations"][0]["citations"] = [ids[0]]
    value["primary_hypothesis"]["claim"]["citations"] = ids
    value["primary_hypothesis"]["contradicting_citations"] = []
    value["alternative_hypotheses"] = []
    value["timeline_evidence_ids"] = [ids[0]]
    value["source_gaps"] = list(context.gaps())
    value["next_check"]["arguments"] = {
        k: v for k, v in asdict(setup.query).items() if k != "kind"
    }
    guard = AdmissionGuard(b"nonfunctional-integration-capability" * 2, clock)
    transport = RecordingProvider(
        guard, ModelReply(json.dumps(value), "response-fixture", ModelUsage(10, 10))
    )
    provider = PolicyModelProvider(
        SETTINGS.configuration(),
        transport,
        Authority(scope, records),
        MemoryJournal(),
        guard,
        scope,
        {"assessment-prompt.v1": PromptTemplate("Return JSON.", ASSESSMENT_VERSION)},
        read_clock=clock,
    )
    response = provider.generate(
        ProviderCall(
            "assessment-prompt.v1",
            tuple(
                EvidenceSelection(
                    identity,
                    records[identity].revision,
                    tuple(f.name for f in records[identity].fields),
                )
                for identity in ids
            ),
            ModelCallBounds(5000, 65536, 256),
        )
    )
    tool_scope = setup.scope
    if denied_knowledge:
        tool_scope = replace(
            tool_scope,
            knowledge=replace(tool_scope.knowledge, access_scope="other-scope"),
        )
    reviews = Reviews(scope)
    validator = create_assessment_validator(
        package,
        scope=scope,
        tools=setup.session(scope=tool_scope, at=at),
        reviews=reviews,
    )
    return validator, response, reviews, scope, mapping


class AssessmentIntegrationTests(unittest.TestCase):
    def test_actual_evidence_and_knowledge_resolve_then_fixture_review_accepts(
        self,
    ) -> None:
        with integration_fixture() as setup:
            validator, response, reviews, scope, _ = setup_assessment(setup)
            pending = validator.validate(response, scope)
            self.assertEqual(pending.outcome, "review_required", pending.reason)
            assert pending.assessment is not None
            reviews.endorse(pending.assessment)
            self.assertEqual(validator.validate(response, scope).outcome, "accepted")
            body = pending.assessment.read(scope)
            kinds = {
                value["source_mapping"]["kind"] for value in body["citations"].values()
            }
            self.assertEqual(kinds, {"evidence", "knowledge"})
            self.assertEqual(body["timeline"][0]["causal_status"], "observed")
            self.assertTrue(body["report"]["source_gaps"])
            self.assertFalse(body["mutation_authority"])

    def test_revoked_knowledge_invalidates_prior_review_and_reads(self) -> None:
        with integration_fixture() as setup:
            validator, response, reviews, scope, mapping = setup_assessment(setup)
            pending = validator.validate(response, scope)
            assert pending.assessment is not None
            reviews.endorse(pending.assessment)
            with SQLiteCorpusStore(setup.root / "corpus.sqlite3") as corpus:
                corpus.withdraw(
                    mapping["metadata"]["document_id"], reason="revoked", at=AT
                )
            self.assertEqual(
                validator.validate(response, scope).reason, "citation_denied"
            )
            with self.assertRaises(AssessmentBoundaryError):
                pending.assessment.read(scope)

    def test_denied_and_expired_corpus_scope_cannot_supply_support(self) -> None:
        for kwargs in ({"denied_knowledge": True}, {"at": AT + timedelta(days=1000)}):
            with integration_fixture() as setup:
                validator, response, _, scope, _ = setup_assessment(setup, **kwargs)
                result = validator.validate(response, scope)
                self.assertEqual(
                    (result.outcome, result.reason), ("rejected", "citation_denied")
                )

    def test_real_dependency_failure_cannot_become_abstention(self) -> None:
        with integration_fixture() as setup:
            validator, response, _, scope, _ = setup_assessment(setup)
            (setup.root / "evidence.sqlite3").unlink()
            result = validator.validate(response, scope)
            self.assertEqual(
                (result.outcome, result.reason),
                ("execution_failed", "execution_failure"),
            )

    def test_composition_rejects_mismatched_investigation_without_reads(self) -> None:
        with integration_fixture() as setup:
            package = build_evidence_package(
                setup.session(),
                investigation_id=setup.scope.investigation_id,
                query=setup.query,
                knowledge_query="Payment timeout evidence",
                knowledge_service="payment",
            )
            scope = ProviderScope("fixture-operator", "wrong-investigation")
            with self.assertRaises(AssessmentBoundaryError):
                create_assessment_validator(
                    package, scope=scope, tools=setup.session(), reviews=Reviews(scope)
                )
