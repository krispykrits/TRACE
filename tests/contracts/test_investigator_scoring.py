"""Known-score v2 projections preserve #14 and distinguish safety from support."""

from __future__ import annotations

import copy
import unittest
from typing import Any

from evaluation.investigator import _review_map
from evaluation.investigator_scoring import review_sample, score_output, summarize
from evaluation.runner import _json, _sha
from tests.fixtures.investigator_evaluation import score_fixture
from trace_app.knowledge.models import canonical, digest


class InvestigatorScoringTests(unittest.TestCase):
    def setUp(self) -> None:
        (
            self.case,
            self.observed,
            self.result,
            self.execution,
            self.sources,
            self.expected,
        ) = score_fixture()

    def score(self, **changes):
        return score_output(
            changes.get("case", self.case),
            changes.get("observed", self.observed),
            changes.get("result", self.result),
            changes.get("execution", self.execution),
            changes.get("sources", self.sources),
            self.expected,
            changes.get("reviews", ()),
        )

    def test_known_labels_citations_timeline_and_usage_have_explicit_denominators(
        self,
    ) -> None:
        score = self.score()
        self.assertTrue(score["cause_correct"])
        self.assertTrue(score["service_correct"])
        self.assertTrue(score["schema_valid"])
        self.assertTrue(score["timeline_order_correct"])
        self.assertTrue(score["timeline_complete_correct"])
        self.assertTrue(score["deterministic_timeline_valid"])
        self.assertTrue(score["contract_pass"])
        summary = summarize([score])
        self.assertEqual(
            summary["cause_accuracy"], {"numerator": 1, "denominator": 1, "value": 1.0}
        )
        self.assertEqual(summary["human_unsupported_claim_rate"]["denominator"], 0)
        self.assertEqual(
            score["usage"],
            {
                "latency_ms": 12.0,
                "tokens": 8,
                "estimated_cost_usd": 8e-9,
                "tool_calls": 1,
            },
        )

    def test_knowledge_citations_are_validated_independently_of_event_ids(self) -> None:
        generation, chunk = "gen-" + "a" * 64, "chunk-" + "b" * 64
        identity = "knowledge-" + digest(
            canonical({"corpus_generation_id": generation, "chunk_id": chunk})
        )
        content = canonical({"passage": "Reviewed development quote"})
        self.sources.append(
            {
                "citation_id": identity,
                "revision": "r1",
                "kind": "internal_runbook",
                "content_sha256": digest(content),
            }
        )
        self.result["citations"][identity] = {
            "citation_id": identity,
            "source_revision": "r1",
            "fields": {"content": content},
            "redactions": [],
            "source_mapping": {
                "kind": "knowledge",
                "source_revision": "r1",
                "corpus_generation_id": generation,
                "chunk_id": chunk,
            },
        }
        self.result["report"]["observations"][0]["citations"] = [identity]
        score = self.score()
        self.assertFalse(score["invalid_citations"])
        self.result["citations"][identity]["source_mapping"]["chunk_id"] = (
            "chunk-" + "c" * 64
        )
        score = self.score()
        self.assertIn(identity, score["invalid_citations"])
        self.assertFalse(score["boundary_pass"])

    def test_cross_scope_and_changed_citation_mappings_fail_the_critical_gate(
        self,
    ) -> None:
        identity = self.result["report"]["observations"][0]["citations"][0]
        self.result["citations"][identity]["source_mapping"]["source_revision"] = (
            "other-scope-revision"
        )
        score = self.score()
        self.assertFalse(score["boundary_pass"])
        self.assertIn("d01", summarize([score])["critical_boundary_failures"])

    def test_missing_and_malformed_outputs_are_not_dropped_or_conflated(self) -> None:
        missing = self.score(result=None)
        bad = copy.deepcopy(self.result)
        bad["report"] = {"schema_version": "unknown"}
        malformed = self.score(result=bad)
        self.assertTrue(missing["output_missing"])
        self.assertFalse(malformed["report_missing"])
        self.assertEqual(malformed["schema_error"], "invalid_assessment_v2")
        self.assertEqual(
            summarize([missing, malformed])["cause_accuracy"]["denominator"], 2
        )
        self.assertEqual(summarize([missing, malformed])["attempted"], 2)

    def test_human_reviews_bind_to_sample_and_record_disagreement(self) -> None:
        sample = review_sample(self.case, self.observed, self.result)
        row = sample[0]
        data: dict[str, Any] = {
            "schema_version": "investigator-support-review.v1",
            "sample_sha256": _sha(_json(sample)),
            "reviews": [
                {
                    "binding_id": row["binding_id"],
                    "reviewer_id": "owner-a",
                    "kind": "human_review",
                    "verdict": "supported",
                    "rationale": "The quoted record supports this observation.",
                },
                {
                    "binding_id": row["binding_id"],
                    "reviewer_id": "owner-b",
                    "kind": "human_review",
                    "verdict": "unsupported",
                    "rationale": "The observation extends beyond the selected source.",
                },
            ],
        }
        reviews = _review_map(sample, data)["d01"]
        score = self.score(reviews=reviews)
        self.assertEqual(summarize([score])["reviewer_disagreements"], 1)
        self.assertEqual(
            summarize([score])["human_unsupported_claim_rate"]["denominator"], 0
        )
        altered = copy.deepcopy(data)
        altered["reviews"][0]["binding_id"] = "other-report-binding"
        with self.assertRaises(ValueError):
            _review_map(sample, altered)
        with self.assertRaises(ValueError):
            _review_map(sample, {**data, "sample_sha256": "0" * 64})

    def test_missing_guard_checks_and_model_label_imports_cannot_pass(self) -> None:
        variants: tuple[dict[str, Any], ...] = (
            {"guard_checks": {}},
            {"guard_checks": {"narrow_audience": True}},
            {"evaluation_modules_loaded": ["evaluation.scoring"]},
            {"harness_exit_code": 1},
            {"evaluation_modules_loaded": None},
        )
        for changes in variants:
            with self.subTest(changes=changes):
                self.assertFalse(
                    self.score(execution={**self.execution, **changes})["contract_pass"]
                )

    def test_unknown_usage_stays_null_and_valid_citations_do_not_supply_support(
        self,
    ) -> None:
        calls = [
            {
                "kind": "model",
                "usage": {"input_tokens": None, "output_tokens": None},
                "estimated_cost_nusd": None,
            }
        ]
        score = self.score(execution={**self.execution, "calls": calls})
        self.assertIsNone(score["usage"]["tokens"])
        self.assertIsNone(score["usage"]["estimated_cost_usd"])
        self.assertFalse(score["actual_human_review"])
        self.assertGreater(len(score["unreviewed_claim_ids"]), 0)

    def test_invalid_cli_envelope_is_a_scored_failure_not_a_dropped_attempt(
        self,
    ) -> None:
        result = {**self.result, "schema_version": "future"}
        score = self.score(result=result)
        self.assertFalse(score["output_missing"])
        self.assertEqual(score["schema_error"], "invalid_cli_envelope")
        self.assertEqual(score["job_execution_status"], "completed")
        self.assertFalse(score["boundary_pass"])
        self.assertEqual(summarize([score])["attempted"], 1)
