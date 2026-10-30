"""Preflight reads existing accounting without making or authorizing model calls."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from evaluation.azure_comparison_preflight import inspect_journal, preflight
from tests.contracts.test_local_mvp_protocol import fixture_decisions
from trace_app.adapters.models.journal import ModelPricing, SqliteProviderJournal
from trace_app.investigation.provider import ModelErrorCode

NOW = datetime(2026, 10, 16, 13, tzinfo=UTC)
PRICING = ModelPricing("azure-luna-global-ceiling-2026-09-22.v1", 250, 750)


class AzureComparisonPreflightTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.journal = self.root / "journal.sqlite3"
        SqliteProviderJournal(
            self.journal,
            PRICING,
            monthly_limit_nusd=20_000_000_000,
            initial_spend_nusd=50,
            now=NOW.timestamp(),
        )
        self.decisions = self.root / "decisions.json"
        self.decisions.write_text(json.dumps(fixture_decisions()))

    def insert(self, request: str, outcome: str, dispatched: int) -> None:
        with sqlite3.connect(self.journal) as connection:
            connection.execute(
                "INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)",
                (request, request, "2026-10", 100, 100, outcome, "{}", dispatched),
            )

    def test_unresolved_reservations_and_uncertain_dispatches_block_without_mutation(
        self,
    ) -> None:
        self.insert("reserved", "reserved", 0)
        self.insert("timeout", ModelErrorCode.TIMEOUT.value, 1)
        self.insert("dependency", ModelErrorCode.DEPENDENCY.value, 1)
        self.insert("undispatched", ModelErrorCode.CANCELLED.value, 0)
        before = hashlib.sha256(self.journal.read_bytes()).hexdigest()
        with (
            patch("socket.socket", side_effect=AssertionError("unexpected network")),
            patch(
                "subprocess.run", side_effect=AssertionError("unexpected subprocess")
            ),
        ):
            result = preflight(self.decisions, self.journal, NOW)
        self.assertEqual(result["journal"]["unresolved_attempts"], 3)
        self.assertEqual(result["journal"]["charged_nusd"], 400)
        self.assertIn("journal:unresolved_attempts", result["blockers"])
        self.assertIn("live_composition:not_implemented", result["blockers"])
        self.assertFalse(result["dispatch_authorized"])
        self.assertEqual(before, hashlib.sha256(self.journal.read_bytes()).hexdigest())

    def test_missing_insecure_symlink_and_wrong_month_never_create_a_journal(
        self,
    ) -> None:
        missing = self.root / "missing.sqlite3"
        self.assertEqual(inspect_journal(missing, "2026-10")["status"], "unavailable")
        self.assertFalse(missing.exists())
        link = self.root / "link.sqlite3"
        link.symlink_to(self.journal)
        self.assertEqual(inspect_journal(link, "2026-10")["status"], "unavailable")
        self.journal.chmod(0o644)
        self.assertEqual(
            inspect_journal(self.journal, "2026-10")["status"], "unavailable"
        )
        self.journal.chmod(0o600)
        self.assertEqual(
            inspect_journal(self.journal, "2026-11")["status"], "unavailable"
        )

    def test_future_or_wrong_month_spending_is_blocked(self) -> None:
        values = fixture_decisions()
        values["spending"]["accounting_observed_at"] = "2026-10-16T14:00:00Z"
        self.decisions.write_text(json.dumps(values))
        self.assertIn(
            "spending:future_snapshot",
            preflight(self.decisions, self.journal, NOW)["blockers"],
        )
        later = datetime(2026, 11, 1, tzinfo=UTC)
        blocked = preflight(self.decisions, self.journal, later)["blockers"]
        self.assertIn("journal:current_month_not_bound", blocked)
        self.assertIn("journal:unavailable_or_missing_current_month", blocked)

    def test_mismatched_limit_and_pricing_are_reported(self) -> None:
        with sqlite3.connect(self.journal) as connection:
            connection.execute(
                "UPDATE configuration SET limit_nusd=?, input_rate=? WHERE id=1",
                (10_000_000_000, 251),
            )
        blocked = preflight(self.decisions, self.journal, NOW)["blockers"]
        self.assertIn("journal:monthly_limit_mismatch", blocked)
        self.assertIn("journal:pricing_mismatch", blocked)

    def test_complete_synthetic_planning_inputs_never_authorize_dispatch(self) -> None:
        from evaluation.local_mvp import plan

        value = fixture_decisions()
        self.decisions.write_text(json.dumps(value))
        draft = plan(self.decisions)
        value["approval"] = {
            "owner": "test-only",
            "recorded_at": "2026-10-16T12:00:00Z",
            "reference": "synthetic test fixture",
            **draft["binding"],
        }
        self.decisions.write_text(json.dumps(value))
        self.assertEqual(plan(self.decisions)["blockers"], [])
        report = preflight(self.decisions, self.journal, NOW)
        self.assertEqual(report["status"], "blocked")
        self.assertFalse(report["dispatch_authorized"])
        self.assertIn("live_composition:not_implemented", report["blockers"])
        self.assertIn("run_allowance:shared_enforcement_unverified", report["blockers"])

    def test_changed_decisions_cannot_be_bound_to_an_earlier_plan(self) -> None:
        from evaluation.local_mvp import plan

        original = plan(self.decisions)
        value = fixture_decisions()
        value["revision"] = "changed"
        self.decisions.write_text(json.dumps(value))
        with patch("evaluation.azure_comparison_preflight.plan", return_value=original):
            with self.assertRaises(ValueError):
                preflight(self.decisions, self.journal, NOW)


if __name__ == "__main__":
    unittest.main()
