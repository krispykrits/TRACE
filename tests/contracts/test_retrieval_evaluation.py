"""Development ranking metrics retain failed attempts and exclude absent judgments."""

from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from evaluation.retrieval_baseline import metrics


class RetrievalEvaluationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.suite = {
            "top_k": 3,
            "queries": [
                {"id": "known", "relevant_documents": ["a", "b"]},
                {"id": "failed", "relevant_documents": ["c"]},
                {"id": "absent", "relevant_documents": []},
            ],
        }
        self.attempts = [
            {
                "mode": mode,
                "query_id": query,
                "document_ids": ranks,
                "status": status,
                "search_ms": 2.0,
            }
            for mode in ("lexical", "semantic", "hybrid")
            for query, ranks, status in (
                ("known", ["x", "a"], "ok"),
                ("failed", ["c"], "provider_failure"),
                ("absent", ["x"], "ok"),
            )
        ]

    def test_failed_attempts_count_and_absent_queries_are_reported_separately(
        self,
    ) -> None:
        for result in metrics(self.suite, self.attempts).values():
            self.assertEqual(result["attempts"], 3)
            self.assertEqual(result["answerable_queries"], 2)
            self.assertEqual(result["document_recall_at_3"], 0.25)
            self.assertEqual(result["mrr_at_3"], 0.25)
            self.assertEqual(result["failures"], 1)
            self.assertEqual(result["absent_queries_returning_candidates"], 1)

    def test_missing_duplicate_and_out_of_bound_attempts_are_rejected(self) -> None:
        for attempts in (self.attempts[:-1], self.attempts + [self.attempts[0]]):
            with self.assertRaises(ValueError):
                metrics(self.suite, attempts)
        attempts = copy.deepcopy(self.attempts)
        attempts[0]["document_ids"] = ["a", "b", "c", "d"]
        with self.assertRaises(ValueError):
            metrics(self.suite, attempts)
        attempts[0]["document_ids"] = ["a", "a"]
        with self.assertRaises(ValueError):
            metrics(self.suite, attempts)

    def test_development_judgments_stay_out_of_curated_documents(self) -> None:
        root = Path(__file__).resolve().parents[2]
        suite = json.loads((root / "evaluation/retrieval/queries_v1.json").read_text())
        self.assertEqual(suite["cohort"], "development")
        manifest = json.loads((root / "corpus/development/manifest.json").read_text())
        for entry in manifest["documents"]:
            document = (root / "corpus/development" / entry["path"]).read_text()
            self.assertNotIn("relevant_documents", document)
            self.assertNotIn("trace-retrieval-development.v1", document)


if __name__ == "__main__":
    unittest.main()
