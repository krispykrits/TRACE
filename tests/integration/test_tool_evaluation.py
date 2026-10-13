"""Reusable evaluator expectations are isolated from runtime scripted requests."""

from __future__ import annotations

import copy
import unittest
from typing import Any, ClassVar

from evaluation.tool_evaluation import (
    FIXTURES,
    choice_matches,
    read_json,
    rescore,
    resolve_arguments,
    run_fixture_checks,
    summarize,
    validate_fixture,
)


class ToolEvaluationTests(unittest.TestCase):
    fixture: ClassVar[dict[str, Any]]
    report: ClassVar[dict[str, Any]]

    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = validate_fixture(read_json(FIXTURES))
        cls.report = run_fixture_checks(cls.fixture)

    def test_all_declared_api_examples_execute_and_rescore_without_a_model(
        self,
    ) -> None:
        summary = rescore(self.report)
        self.assertEqual(
            summary,
            {"cases": 18, "scheduled_examples": 21, "failures": [], "passed": True},
        )
        self.assertEqual(self.report["model_evaluation"], "not_run")
        self.assertEqual(self.report["paid_calls"], 0)

    def test_tool_choice_quality_is_separate_from_legal_api_calls(self) -> None:
        case = self.fixture["cases"][0]
        arguments = resolve_arguments(
            case["acceptable_calls"][0]["arguments"], self.report["observations"]
        )
        self.assertTrue(
            choice_matches(case, "logs.query", arguments, self.report["observations"])
        )
        self.assertFalse(
            choice_matches(
                case, "metrics.query", arguments, self.report["observations"]
            )
        )
        self.assertFalse(
            choice_matches(
                case,
                "logs.query",
                {**arguments, "limit": True},
                self.report["observations"],
            )
        )

    def test_saved_tampering_missing_duplicate_or_unscheduled_attempts_are_rejected(
        self,
    ) -> None:
        report = copy.deepcopy(self.report)
        report["attempts"][0]["actual_status"] = "ok"
        with self.assertRaisesRegex(ValueError, "hash"):
            rescore(report)
        for attempts in (
            self.report["attempts"][:-1],
            self.report["attempts"] + [self.report["attempts"][0]],
        ):
            report = {**self.report, "attempts": attempts}
            with self.assertRaises(ValueError):
                summarize(report)
        report = copy.deepcopy(self.report)
        report["attempts"][0]["case_id"] = "unscheduled"
        with self.assertRaises(ValueError):
            summarize(report)

    def test_unexpected_api_failure_stays_in_the_report(self) -> None:
        report = copy.deepcopy(self.report)
        report["attempts"][0]["actual_status"] = "dependency_failure"
        summary = summarize(report)
        self.assertFalse(summary["passed"])
        self.assertEqual(len(summary["failures"]), 1)
        self.assertEqual(summary["scheduled_examples"], 21)

    def test_fixture_schema_and_context_tokens_reject_unknown_inputs(self) -> None:
        fixture = copy.deepcopy(self.fixture)
        fixture["cases"][0]["acceptable_calls"][0]["arguments"]["window_start"] = (
            "$cause_label"
        )
        with self.assertRaises(ValueError):
            validate_fixture(fixture)
        fixture = copy.deepcopy(self.fixture)
        fixture["cases"][0]["acceptable_calls"][0]["name"] = "shell"
        with self.assertRaises(ValueError):
            validate_fixture(fixture)
