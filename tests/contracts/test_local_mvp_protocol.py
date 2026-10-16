"""Acceptance planning rejects missing denominators, invented inputs and stale approval."""

from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evaluation.local_mvp import (
    _INTEGER_BOUNDS,
    DECISIONS,
    PROTOCOL,
    assess_rate,
    plan,
    validate_decisions,
)


def fixture_decisions() -> dict:
    """Synthetic validator input only; never actual thresholds, grants or endorsement."""
    value = json.loads(DECISIONS.read_text())
    for section in ("thresholds", "provider", "resources", "spending", "authorization"):
        for name, item in value[section].items():
            if item is None:
                value[section][name] = (
                    0.5 if section == "thresholds" else "test-fixture"
                )
    for name, (low, _) in _INTEGER_BOUNDS.items():
        if "." in name:
            section, field = name.split(".")
            value[section][field] = low
        else:
            value[name] = low
    value["limits"].update(
        model_calls_per_attempt=3,
        input_tokens_per_call=10000,
        output_tokens_per_call=1024,
        attempt_deadline_ms=120000,
    )
    value["review"].update(
        claims_per_model_arm=10, minimum_determinate_claims_per_arm=5
    )
    value["provider"]["model_id"] = "gpt-6-luna"
    value["spending"].update(
        month="2026-10",
        monthly_cap_nusd=20000000000,
        scope_allowance_nusd=1000000000,
        accounting_observed_at="2026-10-16T12:00:00Z",
    )
    return value


class LocalMVPProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.protocol = json.loads(PROTOCOL.read_text())

    def test_empty_or_unselected_rates_cannot_pass(self) -> None:
        self.assertEqual(assess_rate(0, 0, 1)["status"], "unmeasured")
        self.assertIsNone(assess_rate(0, 0, 1)["value"])
        self.assertEqual(assess_rate(1, 1, None)["status"], "threshold_pending")
        # One correct result among three planned answerable attempts: failures stay in.
        scored = assess_rate(1, 3, 0.5)
        self.assertEqual(scored["denominator"], 3)
        self.assertEqual(scored["status"], "failed")
        self.assertEqual(assess_rate(1, 2, 0.5)["status"], "passed")
        self.assertEqual(
            assess_rate(1, 2, 0.5, direction="maximum")["status"], "passed"
        )
        self.assertEqual(
            assess_rate(1, 2, 0.4, direction="maximum")["status"], "failed"
        )

    def test_impossible_boolean_and_nonfinite_rates_are_invalid(self) -> None:
        for numerator, denominator, threshold in (
            (2, 1, 0.5),
            (True, 1, 0.5),
            (0, -1, 0.5),
            (0, 1, True),
            (0, 1, float("nan")),
            (0, 1, float("inf")),
        ):
            with (
                self.subTest(values=(numerator, denominator, threshold)),
                self.assertRaises(ValueError),
            ):
                assess_rate(numerator, denominator, threshold)

    def test_supplied_thresholds_bounds_and_unknown_fields_are_validated(self) -> None:
        for section, key, item in (
            ("thresholds", "cause_accuracy", True),
            ("thresholds", "cause_accuracy", 1.1),
            ("thresholds", "elapsed_p95_ms", -1),
            ("thresholds", "elapsed_p95_ms", float("nan")),
            ("spending", "monthly_cap_nusd", 20000000001),
            ("spending", "prior_spend_nusd", -1),
            ("limits", "model_calls_per_attempt", 101),
            ("limits", "output_tokens_per_call", 15),
            ("review", "reviewers_per_claim", 1),
            ("provider", "provider", "unapproved-provider"),
            ("spending", "month", "2026-13"),
            ("spending", "accounting_observed_at", "2026-10-16T12:00:00"),
            ("spending", "accounting_observed_at", "2026-11-01T12:00:00Z"),
        ):
            value = fixture_decisions()
            value[section][key] = item
            with (
                self.subTest(field=f"{section}.{key}", value=item),
                self.assertRaises(ValueError),
            ):
                validate_decisions(value, self.protocol)
        value = fixture_decisions()
        value["thresholds"]["unexpected"] = 0
        with self.assertRaises(ValueError):
            validate_decisions(value, self.protocol)

    def test_review_coverage_cannot_exceed_population(self) -> None:
        value = fixture_decisions()
        value["review"]["minimum_determinate_claims_per_arm"] = 11
        with self.assertRaises(ValueError):
            validate_decisions(value, self.protocol)

    def test_spending_month_uses_the_shared_journals_utc_month(self) -> None:
        value = fixture_decisions()
        value["spending"]["accounting_observed_at"] = "2026-11-01T00:30:00+02:00"
        validate_decisions(value, self.protocol)
        value["spending"]["month"] = "2026-11"
        with self.assertRaises(ValueError):
            validate_decisions(value, self.protocol)

    def test_missing_owner_decisions_do_not_become_defaults_or_zero_spend(self) -> None:
        result = plan()
        self.assertEqual(result["preflight"], "blocked")
        self.assertIn("missing:thresholds.cause_accuracy", result["blockers"])
        self.assertIn("missing:spending.prior_spend_nusd", result["blockers"])
        self.assertIn("missing:approval", result["blockers"])
        self.assertIsNone(result["projected_cost_ceiling_nusd"])
        self.assertIsNone(result["monthly_available_nusd"])
        self.assertEqual(result["schedule"], [])
        self.assertEqual(len(result["schedule_template"]), 12)
        self.assertEqual(result["actual_provider_calls"], 0)

    def test_schedule_cost_and_approval_bind_the_exact_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            value = fixture_decisions()
            value["repeats"] = 2
            path.write_text(json.dumps(value))
            draft = plan(path)
            self.assertEqual(len(draft["schedule"]), 24)
            self.assertEqual(draft["projected_model_attempts"], 16)
            self.assertEqual(
                draft["projected_cost_ceiling_nusd"],
                16 * 3 * (10000 * 250 + 1024 * 750),
            )
            self.assertEqual(draft["schedule"][0]["arm"], "llm_only")
            self.assertEqual(draft["schedule"][3]["arm"], "evidence_bundle")
            self.assertEqual(draft["schedule"][12]["arm"], "evidence_bundle")
            value["approval"] = {
                "owner": "synthetic-validator-fixture",
                "recorded_at": "2026-10-16T12:00:00Z",
                "reference": "test-only; no actual endorsement",
                **draft["binding"],
            }
            path.write_text(json.dumps(value))
            ready = plan(path)
            self.assertEqual(ready["blockers"], [])
            self.assertEqual(ready["preflight"], "inputs_complete_for_review")
            self.assertEqual(ready["binding"], draft["binding"])
            self.assertNotEqual(
                ready["decision_artifact_sha256"], draft["decision_artifact_sha256"]
            )
            self.assertEqual(plan(path), ready)
            value["thresholds"]["cause_accuracy"] = 0.75
            path.write_text(json.dumps(value))
            self.assertIn("approval_mismatch:decisions_sha256", plan(path)["blockers"])
            path.write_text(
                json.dumps({**value, "thresholds": fixture_decisions()["thresholds"]})
            )
            changed_sources = copy.deepcopy(ready["source_sha256"])
            changed_sources["uv.lock"] = "0" * 64
            with patch(
                "evaluation.local_mvp._source_hashes", return_value=changed_sources
            ):
                self.assertIn(
                    "approval_mismatch:source_snapshot_sha256", plan(path)["blockers"]
                )

    def test_scope_and_monthly_spending_include_outstanding_reservations(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json"
            value = fixture_decisions()
            value["spending"].update(
                prior_spend_nusd=19000000000,
                outstanding_reservations_nusd=999999999,
                scope_allowance_nusd=1,
            )
            path.write_text(json.dumps(value))
            result = plan(path)
            self.assertEqual(result["monthly_available_nusd"], 1)
            self.assertIn("budget:monthly_headroom_exceeded", result["blockers"])
            self.assertIn(
                "budget:projected_scope_exceeds_allowance", result["blockers"]
            )
            value["spending"]["scope_allowance_nusd"] = 2
            path.write_text(json.dumps(value))
            self.assertIn(
                "budget:scope_allowance_exceeds_monthly_headroom",
                plan(path)["blockers"],
            )
