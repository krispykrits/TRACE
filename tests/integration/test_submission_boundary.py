"""Exercise submission and cancellation through a real persistent store."""

from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

from trace_app.adapters.storage.sqlite.investigations import SQLiteInvestigationStore
from trace_app.investigation.models import (
    StoreAccessError,
    StoreConflictError,
    StoreInputError,
)
from trace_app.investigation.submission import (
    InvestigationGrant,
    InvestigationSubmission,
)


class SubmissionParameters(TypedDict):
    submission_key: str
    service: str
    environment: str
    window_start: str
    window_end: str
    at: datetime


class SubmissionBoundaryTest(unittest.TestCase):
    def test_reopen_idempotency_scope_revocation_and_cancellation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobs.sqlite"
            now = datetime(2026, 1, 1, 1, tzinfo=UTC)
            grant = InvestigationGrant("team:a", "test", frozenset({"orders"}))
            request: SubmissionParameters = dict(
                submission_key="request-1",
                service="orders",
                environment="test",
                window_start="2026-01-01T00:00:00Z",
                window_end="2026-01-01T00:30:00Z",
                at=now,
            )
            with SQLiteInvestigationStore(path) as store:
                boundary = InvestigationSubmission(store)
                job = boundary.submit(grant, **request)
                self.assertEqual(job.status, "queued")
                self.assertEqual(job.attempt_count, 0)
                self.assertEqual(
                    boundary.submit(grant, **request).investigation_id,
                    job.investigation_id,
                )
                with self.assertRaises(StoreConflictError):
                    changed = request.copy()
                    changed["window_end"] = "2026-01-01T00:20:00Z"
                    boundary.submit(grant, **changed)
                with self.assertRaises(StoreAccessError):
                    changed = request.copy()
                    changed["service"] = "payments"
                    boundary.submit(grant, **changed)
                with self.assertRaises(StoreInputError):
                    changed = request.copy()
                    changed["window_end"] = "2026-01-02T00:00:01Z"
                    boundary.submit(grant, **changed)

            with SQLiteInvestigationStore(path) as store:
                boundary = InvestigationSubmission(store)
                other_scope = InvestigationGrant(
                    "team:b", "test", frozenset({"orders"})
                )
                revoked = InvestigationGrant("team:a", "test", frozenset())
                for rejected in (other_scope, revoked):
                    with self.assertRaises(StoreAccessError):
                        boundary.read(rejected, job.investigation_id)
                    with self.assertRaises(StoreAccessError):
                        boundary.cancel(rejected, job.investigation_id, at=now)
                self.assertEqual(
                    boundary.read(grant, job.investigation_id).status, "queued"
                )
                self.assertEqual(
                    boundary.cancel(grant, job.investigation_id, at=now).status,
                    "cancelled",
                )
                self.assertIsNone(store.claim_next(at=now))


if __name__ == "__main__":
    unittest.main()
