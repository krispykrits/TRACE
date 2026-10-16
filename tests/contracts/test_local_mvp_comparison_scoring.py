"""Known-score and empty/unknown measurement checks for three-arm comparisons."""

from __future__ import annotations

import unittest
from pathlib import Path

from evaluation.local_mvp_comparison import _reference_score, measurements, score
from evaluation.runner import _json, _parse, _read
from tests.fixtures.investigator_evaluation import score_fixture


class LocalMVPComparisonScoringTests(unittest.TestCase):
    def test_known_supported_proposal_keeps_labels_separate_from_review(self) -> None:
        case, observed, result, execution, sources, _ = score_fixture()
        case.update(arm="rag_tools", repeat=1)
        execution.update(evaluation_modules_loaded=[], actual_provider_calls=0)
        files = {
            "schedule.json": [case],
            "ground_truth.json": _parse(
                _read(Path("evaluation/ground_truth/mvp_suite_v1.json"))
            ),
            "protocol.json": {"limitations": []},
            "decisions.json": {
                "thresholds": {"cause_accuracy": 0.8, "human_unsupported_claim_rate": 0}
            },
            "plan.json": {"blockers": ["missing:approval"]},
        }
        for name, value in zip(
            ("observed.json", "result.json", "execution.json", "sources.json"),
            (observed, result, execution, sources),
            strict=True,
        ):
            files[f"artifacts/{case['id']}/{name}"] = value
        scores = score(files)
        self.assertEqual(scores["arms"]["rag_tools"]["cause_accuracy"]["value"], 1)
        self.assertEqual(
            scores["integrated_fixture_thresholds"]["human_unsupported_claim_rate"][
                "status"
            ],
            "unmeasured",
        )
        self.assertEqual(scores["actual_human_review_decisions"], 0)
        self.assertTrue(scores["support_sample"])
        self.assertEqual(_json(scores), _json(score(files)))

    def test_malformed_reference_is_invalid_and_failed_reference_stays_in_denominator(
        self,
    ) -> None:
        case, observed, _, execution, _, expected = score_fixture()
        malformed = _reference_score(
            case,
            observed,
            {"execution_status": "completed", "report": {"bad": "shape"}},
            execution,
            expected,
        )
        self.assertFalse(malformed["schema_valid"])
        self.assertEqual(malformed["schema_error"], "invalid_assessment_v2")
        failed = _reference_score(case, observed, None, execution, expected)
        self.assertFalse(failed["schema_valid"])
        self.assertFalse(failed["cause_correct"])

    def test_missing_latency_or_cost_is_unknown_and_p95_uses_nearest_rank(self) -> None:
        unknown = measurements(
            [
                {"usage": {"latency_ms": 10, "estimated_cost_usd": 0}},
                {"usage": {"latency_ms": None, "estimated_cost_usd": None}},
            ]
        )
        self.assertIsNone(unknown["elapsed_p95_ms"])
        self.assertIsNone(unknown["estimated_cost_per_attempt_nusd"])
        known = measurements(
            [{"latency_ms": value, "estimated_cost_usd": 0} for value in range(1, 21)]
        )
        self.assertEqual(known["elapsed_p95_ms"], 19)
