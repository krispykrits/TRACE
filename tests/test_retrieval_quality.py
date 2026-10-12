"""Hand-computed passage ranks, review provenance and pre-execution acceptance gates."""

from __future__ import annotations

import copy
import hashlib
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

from evaluation.retrieval_quality import (
    SCORER_VERSION,
    acceptance_checks,
    read_json,
    rescore,
    review_bundle,
    review_summary,
    review_targets,
    run,
    score,
    validate_protocol,
    validate_suite,
)
from trace_app.knowledge import canonical, digest
from trace_app.retrieval_contracts import EncoderFailure

_ROOT = Path(__file__).resolve().parents[1]
_AT = datetime(2026, 10, 12, 20, tzinfo=UTC)


class PassageEvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.suite = validate_suite(
            read_json(_ROOT / "evaluation/retrieval/queries_v2.json")
        )
        self.protocol = read_json(_ROOT / "evaluation/retrieval/acceptance_v1.json")
        self.reviews = read_json(_ROOT / "evaluation/retrieval/reviews_v2.json")

    def test_hand_computed_recalls_mrr_failures_and_empty_gold_denominators(
        self,
    ) -> None:
        suite = {
            "queries": [
                {"id": "one", "judgments": [{"chunk_id": "a"}, {"chunk_id": "b"}]},
                {"id": "two", "judgments": [{"chunk_id": "c"}]},
                {"id": "none", "judgments": []},
            ]
        }
        rows: list[dict[str, Any]] = [
            {
                "mode": "lexical",
                "query_id": "one",
                "chunk_ids": ["x", "a", "b"],
                "failure_code": None,
                "search_status": "ok",
                "context_status": "ok",
            },
            {
                "mode": "lexical",
                "query_id": "two",
                "chunk_ids": ["c"],
                "failure_code": "provider_failure",
                "search_status": "provider_failure",
                "context_status": "retrieval_failed",
            },
            {
                "mode": "lexical",
                "query_id": "none",
                "chunk_ids": ["x"],
                "failure_code": None,
                "search_status": "ok",
                "context_status": "ok",
            },
        ]
        result = score(suite, rows, modes=("lexical",), ks=(1, 2, 3), candidate_k=3)[
            "lexical"
        ]
        self.assertEqual(result["attempts"], 3)
        self.assertEqual(result["failures"], 1)
        self.assertEqual(result["by_k"]["1"]["passage_recall"]["value"], 0.0)
        self.assertEqual(
            result["by_k"]["2"]["passage_recall"],
            {"numerator": 0.5, "denominator": 2, "value": 0.25},
        )
        self.assertEqual(result["by_k"]["3"]["passage_recall"]["value"], 0.5)
        self.assertEqual(result["by_k"]["3"]["mrr"]["value"], 0.25)
        self.assertEqual(result["by_k"]["3"]["no_relevant_queries"], 1)
        self.assertEqual(
            result["by_k"]["3"]["no_relevant_queries_returning_candidates"], 1
        )
        rows[1]["failure_code"] = None
        self.assertEqual(
            score(suite, rows, modes=("lexical",), ks=(3,), candidate_k=3)["lexical"][
                "failures"
            ],
            1,
        )
        empty = {"queries": [{"id": "none", "judgments": []}]}
        rate = score(empty, rows[-1:], modes=("lexical",), ks=(3,), candidate_k=3)[
            "lexical"
        ]["by_k"]["3"]["mrr"]
        self.assertEqual(rate, {"numerator": 0, "denominator": 0, "value": None})
        for invalid in (rows[:-1], rows + rows[:1]):
            with self.assertRaises(ValueError):
                score(suite, invalid, modes=("lexical",), ks=(3,), candidate_k=3)
        rows[0]["chunk_ids"] = ["a", "a"]
        with self.assertRaises(ValueError):
            score(suite, rows, modes=("lexical",), ks=(3,), candidate_k=3)

    def test_suite_queries_protocol_and_review_material_are_bound_before_execution(
        self,
    ) -> None:
        self.assertEqual(len(self.suite["queries"]), 100)
        self.assertEqual(len({q["family"] for q in self.suite["queries"]}), 15)
        self.assertEqual(len(review_targets(self.suite)), 198)
        protocol = validate_protocol(self.protocol, self.suite, run_at=_AT)
        self.assertEqual(protocol["candidate_k"], 20)
        self.assertEqual(
            protocol["acceptance"],
            {
                "recall_at_5": 0.9,
                "mrr_at_5": 0.8,
                "recall_at_10": 0.95,
                "minimum_evaluation_queries": 100,
            },
        )
        with self.assertRaises(ValueError):
            validate_protocol(
                protocol, self.suite, run_at=datetime(2026, 10, 12, 19, tzinfo=UTC)
            )
        wrong = copy.deepcopy(protocol)
        wrong["acceptance"]["recall_at_5"] = True
        with self.assertRaises(ValueError):
            validate_protocol(wrong, self.suite, run_at=_AT)
        invalid = copy.deepcopy(self.suite)
        invalid["queries"][1]["id"] = invalid["queries"][0]["id"]
        with self.assertRaises(ValueError):
            validate_suite(invalid)
        invalid = copy.deepcopy(self.suite)
        invalid["cohort"] = "final_test"
        with self.assertRaises(ValueError):
            validate_suite(invalid)
        bundle = review_bundle(self.suite)
        self.assertIn("no human sign-off", bundle)
        self.assertIn("relevance:stale-certificate", bundle)
        self.assertIn("Original offsets", bundle)
        self.assertEqual(
            bundle.rstrip("\n"),
            (_ROOT / "evaluation/retrieval/review_bundle_v2.md")
            .read_text()
            .rstrip("\n"),
        )

    def test_fixture_expectations_cannot_satisfy_human_review_and_disagreement_is_preserved(
        self,
    ) -> None:
        target = next(iter(review_targets(self.suite)))
        record = {
            "claim_id": target,
            "verdict": "supported",
            "reviewer_id": "synthetic-test-reviewer",
            "rationale": "Test fixture; not actual human evidence.",
            "kind": "fixture_expectation",
        }
        reviews = copy.deepcopy(self.reviews)
        reviews["reviews"] = [record]
        summary = review_summary(self.suite, reviews)
        self.assertEqual(summary["human_reviewed_targets"], 0)
        self.assertFalse(summary["complete"])
        self.assertIsNone(summary["human_unsupported_claim_rate"]["value"])
        record["kind"] = "human_review"
        self.assertEqual(
            review_summary(self.suite, reviews)["human_reviewed_targets"], 1
        )
        reviews["reviews"].append(
            {
                **record,
                "reviewer_id": "second-synthetic-test-reviewer",
                "verdict": "unsupported",
            }
        )
        self.assertEqual(review_summary(self.suite, reviews)["disagreements"], [target])
        reviews["reviews"].append(record)
        with self.assertRaises(ValueError):
            review_summary(self.suite, reviews)

    def test_acceptance_waits_for_real_reviews_before_loading_any_model(self) -> None:
        with patch("evaluation.retrieval_quality.LocalSentenceEncoder") as encoder:
            with self.assertRaisesRegex(ValueError, "human"):
                run(
                    self.suite,
                    self.reviews,
                    self.protocol,
                    modes=("lexical", "semantic", "hybrid"),
                    acceptance=True,
                )
            encoder.assert_not_called()
        result = {
            "lexical": {
                "by_k": {
                    "5": {"passage_recall": {"value": 0.90}, "mrr": {"value": 0.80}},
                    "10": {"passage_recall": {"value": 0.95}},
                }
            }
        }
        self.assertTrue(all(acceptance_checks(self.protocol, result, 100).values()))
        self.assertFalse(
            acceptance_checks(self.protocol, result, 99)["minimum_queries"]
        )
        result["lexical"]["by_k"]["10"]["passage_recall"]["value"] = 0.949
        self.assertFalse(acceptance_checks(self.protocol, result, 100)["recall_at_10"])

    def test_failed_dense_provider_preserves_scheduled_attempts_and_saved_rescoring(
        self,
    ) -> None:
        suite = copy.deepcopy(self.suite)
        suite["queries"] = suite["queries"][:2] + suite["queries"][-1:]
        protocol = copy.deepcopy(self.protocol)
        protocol["suite_sha256"] = digest(canonical(suite))
        reviews = {
            "schema_version": "1",
            "suite_sha256": digest(canonical(suite)),
            "reviews": [],
        }
        with patch(
            "evaluation.retrieval_quality.LocalSentenceEncoder",
            side_effect=EncoderFailure("private error"),
        ):
            report = run(
                suite,
                reviews,
                protocol,
                modes=("lexical", "semantic", "hybrid"),
                acceptance=False,
            )
        self.assertEqual(len(report["attempts"]), 9)
        self.assertEqual(report["metrics"]["semantic"]["failures"], 3)
        self.assertEqual(report["metrics"]["hybrid"]["failures"], 3)
        self.assertEqual(report["metrics"]["lexical"]["failures"], 0)
        self.assertNotIn("private error", canonical(report))
        self.assertEqual(rescore(report), report["metrics"])
        altered = copy.deepcopy(report)
        altered["attempts"][0]["chunk_ids"] = []
        with self.assertRaisesRegex(ValueError, "hash"):
            rescore(altered)
        altered = copy.deepcopy(report)
        altered["acceptance_status"] = "passed"
        with self.assertRaisesRegex(ValueError, "acceptance"):
            rescore(altered)
        altered = copy.deepcopy(report)
        altered["configuration"]["max_chunks_per_document"] = 1
        with self.assertRaisesRegex(ValueError, "hash"):
            rescore(altered)
        altered = copy.deepcopy(report)
        altered["purpose"] = "acceptance"
        altered["acceptance_status"] = "failed"
        with self.assertRaisesRegex(ValueError, "human"):
            rescore(altered)
        self.assertEqual(report["scorer_version"], SCORER_VERSION)
        self.assertEqual(
            report["source_sha256"]["evaluation/retrieval_quality.py"],
            hashlib.sha256(
                (_ROOT / "evaluation/retrieval_quality.py").read_bytes()
            ).hexdigest(),
        )
        self.assertFalse(report["human_review"]["complete"])
        stale = [
            row
            for row in report["attempts"]
            if row["mode"] == "lexical" and row["query_id"].startswith("stale")
        ][0]
        self.assertEqual(stale["eligible_chunks"], 6)
        self.assertEqual(stale["context_status"], "ok")

    def test_input_file_bounds_and_duplicate_json_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text('{"key":1,"key":2}')
            with self.assertRaises(ValueError):
                read_json(path)
            with self.assertRaises(ValueError):
                read_json(path, max_bytes=1)
            other = Path(directory) / "link"
            other.symlink_to(path)
            with self.assertRaises(ValueError):
                read_json(other)


if __name__ == "__main__":
    unittest.main()
