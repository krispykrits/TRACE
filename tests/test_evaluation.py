"""Known-score, artifact reproducibility and evaluator-isolation checks."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

from evaluation.runner import _attempts, _expected, _parse, _snapshot, rescore, run
from evaluation.scoring import (
    EvaluationAttempt,
    SupportReview,
    aggregate_scores,
    score_candidate,
)
from trace_app.assessment import CandidateReport, ReportInputError
from trace_app.scenarios import ScenarioConfig, ScenarioSession

_ROOT = Path(__file__).resolve().parents[1]
_CAPTURE = datetime(2026, 10, 12, 12, tzinfo=UTC)


def _fixtures() -> dict[str, Any]:
    return json.loads((_ROOT / "evaluation/fixtures/candidates_v1.json").read_text())


def _truth() -> dict[str, Any]:
    return json.loads((_ROOT / "evaluation/ground_truth/mvp_suite_v1.json").read_text())


def _json_dict(value: object) -> dict[str, Any]:
    return json.loads(json.dumps(value))


class ReportContractTests(unittest.TestCase):
    def test_roundtrip_and_observation_hypothesis_abstention_separation(self) -> None:
        for fixture in _fixtures()["attempts"][:4]:
            raw = fixture["report"]
            self.assertEqual(CandidateReport.from_dict(raw).to_dict(), raw)
        abstained = CandidateReport.from_dict(_fixtures()["attempts"][2]["report"])
        self.assertIsNone(abstained.primary_hypothesis)
        self.assertTrue(abstained.abstention_reason)
        self.assertEqual(len(abstained.alternative_hypotheses), 2)

    def test_unknown_labels_scores_versions_and_inconsistent_status_fail(self) -> None:
        base = _fixtures()["attempts"][0]["report"]
        invalid_changes: tuple[dict[str, object], ...] = (
            {"schema_version": "future"},
            {"ground_truth": "secret"},
            {"anomaly_score": 0.9},
            {"class_probability": 0.9},
            {"retrieval_rank_score": 0.9},
            {"uncertainty": ""},
            {"assessment_status": "abstained"},
            {"primary_hypothesis": None},
            {"observations": {}},
        )
        for changes in invalid_changes:
            with self.subTest(changes=changes), self.assertRaises(ReportInputError):
                CandidateReport.from_dict({**base, **changes})
        nested = copy.deepcopy(base)
        nested["primary_hypothesis"]["ground_truth"] = "secret"
        with self.assertRaises(ReportInputError):
            CandidateReport.from_dict(nested)
        duplicated = copy.deepcopy(base)
        duplicated["observations"][0]["claim_id"] = "h1"
        with self.assertRaisesRegex(ReportInputError, "claim_id"):
            CandidateReport.from_dict(duplicated)
        duplicated = copy.deepcopy(base)
        duplicated["timeline_evidence_ids"].append(
            duplicated["timeline_evidence_ids"][0]
        )
        with self.assertRaisesRegex(ReportInputError, "duplicate"):
            CandidateReport.from_dict(duplicated)


class ScorerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.attempts = _attempts(_fixtures())
        self.expected = _expected(_truth())
        self.evidence = {
            case: ScenarioSession(ScenarioConfig(case, 17))
            .replay(collected_at=_CAPTURE)
            .snapshot
            for case in self.expected
        }

    def _score(self, attempt):
        return score_candidate(
            attempt, self.evidence[attempt.case_id], self.expected[attempt.case_id]
        )

    def test_known_scores_keep_failed_missing_and_invalid_attempts_in_denominators(
        self,
    ) -> None:
        scores = tuple(self._score(attempt) for attempt in self.attempts)
        summary = aggregate_scores(scores)
        self.assertEqual(summary["attempted"], 7)
        for metric, numerator, denominator in (
            ("schema_validity", 4, 7),
            ("cause_accuracy", 1, 5),
            ("service_accuracy", 1, 5),
            ("assessment_accuracy", 3, 7),
            ("abstention_contract_accuracy", 1, 2),
            ("citation_validity", 13, 14),
            ("timeline_order_accuracy", 3, 7),
            ("timeline_complete_accuracy", 3, 7),
        ):
            self.assertEqual(
                summary[metric],
                {
                    "numerator": numerator,
                    "denominator": denominator,
                    "value": numerator / denominator,
                },
            )
        self.assertEqual(summary["missing_reports"], 1)
        self.assertEqual(summary["invalid_reports"], 1)
        self.assertEqual(
            summary["execution_counts"],
            {"completed": 6, "failed": 1, "cancelled": 0, "expired": 0},
        )
        self.assertEqual(summary["source_incomplete_attempts"], 7)
        self.assertEqual(summary["capture_gap_attempts"], 2)
        self.assertEqual(summary["structurally_unsupported_claims"], 1)
        self.assertEqual(summary["fixture_expected_unsupported_claims"], 2)
        self.assertEqual(
            summary["human_unsupported_claim_rate"],
            {"numerator": 0, "denominator": 0, "value": None},
        )
        self.assertEqual(summary["unreviewed_claims"], 10)
        self.assertEqual(scores[1].invalid_citations, ("ev-not-present",))
        # Guessing the hidden correct label in incomplete evidence earns no cause credit.
        self.assertIsNone(scores[3].cause_correct)
        self.assertFalse(scores[3].abstention_correct)

    def test_valid_ids_do_not_establish_support_and_review_disagreement_is_explicit(
        self,
    ) -> None:
        forced = self.attempts[3]
        score = self._score(forced)
        self.assertFalse(score.invalid_citations)
        self.assertEqual(score.fixture_unsupported_claim_ids, ("h1",))
        self.assertEqual(score.human_unsupported_claim_ids, ())
        self.assertEqual(score.unreviewed_claim_ids, ("o1", "h1"))
        first = SupportReview(
            "h1",
            "unsupported",
            "reviewer-a",
            "The cited symptom does not distinguish this cause.",
            "human_review",
        )
        second = replace(first, verdict="supported", reviewer_id="reviewer-b")
        disagreed = self._score(replace(forced, support_reviews=(first, second)))
        self.assertEqual(disagreed.disputed_claim_ids, ("h1",))
        self.assertEqual(
            _json_dict(aggregate_scores((disagreed,)))["human_unsupported_claim_rate"][
                "value"
            ],
            None,
        )
        single = self._score(replace(forced, support_reviews=(first,)))
        self.assertEqual(single.human_unsupported_claim_ids, ("h1",))
        self.assertEqual(
            _json_dict(aggregate_scores((single,)))["human_unsupported_claim_rate"][
                "value"
            ],
            1,
        )
        indeterminate = self._score(
            replace(forced, support_reviews=(replace(first, verdict="indeterminate"),))
        )
        self.assertEqual(indeterminate.human_indeterminate_claim_ids, ("h1",))
        self.assertIsNone(
            _json_dict(aggregate_scores((indeterminate,)))[
                "human_unsupported_claim_rate"
            ]["value"]
        )
        with self.assertRaisesRegex(ValueError, "absent claim"):
            self._score(
                replace(forced, support_reviews=(replace(first, claim_id="absent"),))
            )

    def test_uncited_foreign_and_invalid_timeline_references_are_explicit(self) -> None:
        fixture = self.attempts[0]
        raw = copy.deepcopy(cast(dict[str, Any], fixture.report))
        raw["observations"][0]["citations"] = []
        raw["primary_hypothesis"]["claim"]["citations"] = [
            self.evidence["c02"].entries[0].record.evidence_id
        ]
        raw["timeline_evidence_ids"] = ["ev-outside-window"]
        score = self._score(replace(fixture, report=raw))
        self.assertEqual(score.uncited_claim_ids, ("o1",))
        self.assertEqual(score.structurally_unsupported_claim_ids, ("o1", "h1"))
        self.assertTrue(score.invalid_citations)
        self.assertEqual(score.invalid_timeline_citations, ("ev-outside-window",))
        self.assertFalse(score.timeline_order_correct)
        self.assertFalse(score.timeline_complete_correct)
        raw["timeline_evidence_ids"] = []
        self.assertFalse(
            self._score(replace(fixture, report=raw)).timeline_order_correct
        )

    def test_job_outcomes_partial_sources_and_abstention_are_distinct(self) -> None:
        fixture = self.attempts[0]
        for status in ("failed", "cancelled", "expired"):
            score = self._score(
                replace(
                    fixture, execution_status=status, failure_code="fixture_failure"
                )
            )
            self.assertFalse(score.schema_valid)
            self.assertFalse(score.cause_correct)
            self.assertEqual(score.execution_status, status)
        abstained = self._score(self.attempts[2])
        self.assertTrue(abstained.abstention_correct)
        self.assertEqual(abstained.execution_status, "completed")
        self.assertEqual(
            set(abstained.capture_gap_sources),
            {"payment_logs", "payment_metrics", "payment_deployments"},
        )
        raw = copy.deepcopy(cast(dict[str, Any], self.attempts[2].report))
        raw["missing_evidence"] = ["nonexistent-source"]
        self.assertFalse(
            self._score(replace(self.attempts[2], report=raw)).abstention_correct
        )
        self.assertIsNone(
            _json_dict(aggregate_scores(()))["citation_validity"]["value"]
        )

    def test_evaluator_input_schema_rejects_bad_usage_review_case_and_seed(
        self,
    ) -> None:
        fixture = _fixtures()["attempts"][0]
        for value in (-1, True, float("nan"), float("inf"), "unknown"):
            raw = copy.deepcopy(fixture)
            raw["usage"]["latency_ms"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                EvaluationAttempt.from_dict(raw)
        raw = copy.deepcopy(fixture)
        raw["usage"]["tokens"] = 0.5
        with self.assertRaises(ValueError):
            EvaluationAttempt.from_dict(raw)
        raw = copy.deepcopy(_fixtures())
        raw["attempts"][0]["seed"] = 18
        with self.assertRaisesRegex(ValueError, "case/seed"):
            _attempts(raw)
        truth = _truth()
        truth["cases"][0]["role"] = "final_test"
        with self.assertRaisesRegex(ValueError, "development"):
            _expected(truth)
        self.assertTrue(
            all(
                all(value is None for value in attempt.usage.values())
                for attempt in self.attempts
            )
        )


class ArtifactTests(unittest.TestCase):
    def test_runs_and_saved_rescoring_reproduce_exact_manifests_and_scores(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first, second = Path(directory) / "first", Path(directory) / "second"
            scores = run(first)
            self.assertEqual(scores, run(second))
            self.assertEqual(scores, rescore(first))
            for path in first.rglob("*.json"):
                self.assertEqual(
                    path.read_bytes(), (second / path.relative_to(first)).read_bytes()
                )
            manifest = json.loads((first / "manifest.json").read_bytes())
            self.assertEqual(manifest["seeds"], [17])
            self.assertEqual(manifest["suite_version"], "mvp-suite.v1")
            self.assertTrue(manifest["implementation_sha256"])
            self.assertIsNone(manifest["model_version"])
            self.assertTrue(
                all(
                    all(value is None for value in attempt["usage"].values())
                    for attempt in _json_dict(scores)["attempts"]
                )
            )
            for input_file in (first / "inputs").glob("*.json"):
                serialized = input_file.read_text()
                for forbidden in (
                    "cause_label",
                    "cause_service",
                    "expected_assessment",
                    "ground_truth",
                    "template_group",
                    "supporting_ordinals",
                ):
                    self.assertNotIn(forbidden, serialized)
            with self.assertRaises(FileExistsError):
                run(first)

    def test_hash_missing_version_and_rescore_mismatch_fail_without_fallback(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "run"
            run(target)
            original = (target / "scores.json").read_bytes()
            (target / "scores.json").write_bytes(b"{}\n")
            with self.assertRaisesRegex(ValueError, "hash"):
                rescore(target)
            manifest = json.loads((target / "manifest.json").read_bytes())
            manifest["artifact_sha256"]["scores.json"] = hashlib.sha256(
                b"{}\n"
            ).hexdigest()
            (target / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "disagree"):
                rescore(target)
            manifest["configuration"]["version"] = "future"
            (target / "manifest.json").write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "versions"):
                rescore(target)
            (target / "scores.json").write_bytes(original)
            (target / "manifest.json").unlink()
            with self.assertRaises(FileNotFoundError):
                rescore(target)

    def test_json_boundary_and_runtime_imports_preserve_evaluator_isolation(
        self,
    ) -> None:
        for data in (b'{"a":1,"a":2}', b'{"a":NaN}'):
            with self.assertRaises(ValueError):
                _parse(data)
        operational = (
            ScenarioSession(ScenarioConfig("c01", 17))
            .replay(collected_at=_CAPTURE)
            .to_dict()["evidence"]
        )
        self.assertEqual(len(_snapshot(operational).entries), 9)
        with self.assertRaises(ValueError):
            _snapshot({**cast(dict[str, object], operational), "cause_label": "secret"})
        for path in (_ROOT / "src/trace_app").glob("*.py"):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    self.assertFalse((node.module or "").startswith("evaluation"), path)
                elif isinstance(node, ast.Import):
                    self.assertFalse(
                        any(
                            alias.name.startswith("evaluation") for alias in node.names
                        ),
                        path,
                    )
        with (
            patch("evaluation.runner._MAX_FILE_BYTES", 1),
            tempfile.TemporaryDirectory() as directory,
        ):
            with self.assertRaisesRegex(ValueError, "byte bound"):
                run(Path(directory) / "run")
