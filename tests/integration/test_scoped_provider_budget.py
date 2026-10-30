"""Scoped allowance shares the same atomic journal as monthly reservations."""

from __future__ import annotations

import concurrent.futures
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from threading import Barrier

from trace_app.adapters.models.journal import ModelPricing, SqliteProviderJournal
from trace_app.investigation.provider import (
    ModelErrorCode,
    ModelProviderError,
    ModelUsage,
)

AT = datetime(2026, 10, 16, tzinfo=UTC).timestamp()
RUN = "a" * 64
PRICE = ModelPricing("test-pricing", 1, 1)


class ScopedProviderBudgetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "journal.sqlite3"

    def journal(
        self, *, run: str = RUN, limit: int = 100, now: float = AT
    ) -> SqliteProviderJournal:
        return SqliteProviderJournal(
            self.path,
            PRICE,
            monthly_limit_nusd=1000,
            initial_spend_nusd=0,
            now=now,
            run_id=run,
            run_limit_nusd=limit,
        )

    @staticmethod
    def begin(journal: SqliteProviderJournal, name: str, size: int) -> None:
        journal.begin({"request_id": name, "scope_id": name}, (), size, 0, AT)

    def test_run_cap_shared_across_scopes_and_restart(self) -> None:
        first = self.journal()
        self.begin(first, "a", 60)
        first.finish(
            {
                "request_id": "a",
                "scope_id": "a",
                "outcome": "structured_response_received",
            },
            ModelUsage(60, 0),
            True,
            AT,
        )
        restarted = self.journal()
        with self.assertRaises(ModelProviderError) as rejected:
            self.begin(restarted, "b", 41)
        self.assertEqual(rejected.exception.code, ModelErrorCode.BUDGET)
        self.begin(restarted, "c", 40)
        with sqlite3.connect(self.path) as db:
            self.assertEqual(
                db.execute("SELECT COUNT(*) FROM scoped_run_attempts").fetchone()[0], 2
            )

    def test_uncertain_dispatched_attempt_blocks_other_scopes(self) -> None:
        journal = self.journal()
        self.begin(journal, "a", 20)
        journal.finish(
            {
                "request_id": "a",
                "scope_id": "a",
                "outcome": ModelErrorCode.TIMEOUT.value,
            },
            ModelUsage(),
            True,
            AT,
        )
        with self.assertRaises(ModelProviderError) as rejected:
            self.begin(self.journal(), "b", 20)
        self.assertEqual(rejected.exception.code, ModelErrorCode.BUDGET)

    def test_denied_before_dispatch_releases_scoped_reservation(self) -> None:
        journal = self.journal()
        self.begin(journal, "a", 100)
        journal.finish(
            {
                "request_id": "a",
                "scope_id": "a",
                "outcome": ModelErrorCode.POLICY.value,
            },
            ModelUsage(),
            False,
            AT,
        )
        self.begin(self.journal(), "b", 100)

    def test_concurrent_different_scopes_cannot_both_reserve(self) -> None:
        self.journal()
        barrier = Barrier(2)

        def submit(name: str) -> bool:
            journal = self.journal()
            barrier.wait()
            try:
                self.begin(journal, name, 60)
                return True
            except ModelProviderError as error:
                self.assertEqual(error.code, ModelErrorCode.BUDGET)
                return False

        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(submit, ("a", "b")))
        self.assertEqual(sorted(outcomes), [False, True])

    def test_run_configuration_cannot_change_or_cross_month(self) -> None:
        self.journal()
        with self.assertRaises(ModelProviderError):
            self.journal(limit=101)
        later = datetime(2026, 11, 1, tzinfo=UTC).timestamp()
        with self.assertRaises(ModelProviderError):
            self.journal(now=later)
        with self.assertRaises(ModelProviderError):
            self.journal(run="not-a-bound-hash")


if __name__ == "__main__":
    unittest.main()
