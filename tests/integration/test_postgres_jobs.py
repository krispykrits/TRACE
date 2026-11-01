"""PostgreSQL queue contracts, executed only against an isolated test database."""

from __future__ import annotations

import os
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import psycopg

from trace_app.adapters.storage.postgres.jobs import PostgresJobs
from trace_app.investigation.models import (
    Investigation,
    InvestigationRequest,
    StoreStateError,
)

DSN = os.environ.get("TRACE_TEST_POSTGRES_DSN")


@unittest.skipUnless(
    DSN, "Set TRACE_TEST_POSTGRES_DSN to an isolated trace_test database"
)
class PostgresJobsTests(unittest.TestCase):
    def setUp(self) -> None:
        assert DSN is not None
        self.dsn = DSN
        with psycopg.connect(self.dsn, autocommit=True) as connection:
            if connection.info.dbname != "trace_test":
                raise RuntimeError(
                    "Queue tests require a disposable trace_test database."
                )
            connection.execute(
                "DROP TABLE IF EXISTS trace_job_attempts, trace_jobs CASCADE"
            )
            schema = Path(
                "src/trace_app/adapters/storage/postgres/schema.sql"
            ).read_text()
            connection.execute(schema)
        self.store = PostgresJobs(self.dsn)
        self.now = datetime.now(UTC)

    def test_concurrent_submission_claim_and_stale_attempt(self) -> None:
        request = InvestigationRequest(
            "key",
            "orders",
            "test",
            "scope:a",
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:01:00Z",
            max_attempts=1,
        )
        barrier = threading.Barrier(2)

        def submit() -> str:
            barrier.wait()
            return PostgresJobs(self.dsn).submit(request, at=self.now).investigation_id

        with ThreadPoolExecutor(max_workers=2) as pool:
            ids = list(pool.map(lambda _: submit(), range(2)))
        self.assertEqual(ids[0], ids[1])
        barrier = threading.Barrier(2)

        def claim() -> Investigation | None:
            barrier.wait()
            return PostgresJobs(self.dsn).claim(lease_seconds=60)

        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = list(pool.map(lambda _: claim(), range(2)))
        claimed = [job for job in jobs if job is not None]
        self.assertEqual(len(claimed), 1)
        with psycopg.connect(self.dsn) as connection:
            connection.execute(
                "UPDATE trace_jobs SET lease_until=clock_timestamp() - interval '1 second' WHERE investigation_id=%s",
                (ids[0],),
            )
        self.assertIsNone(self.store.claim(lease_seconds=60))
        failed = self.store.get_investigation(ids[0], access_scope="scope:a")
        self.assertEqual(
            (failed.status, failed.failure_code), ("failed", "outcome_unknown")
        )
        with self.assertRaises(StoreStateError):
            self.store.fail(claimed[0], failure_code="failed")

    def test_cancel_is_idempotent_and_prevents_claim(self) -> None:
        request = InvestigationRequest(
            "key",
            "orders",
            "test",
            "scope:a",
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:01:00Z",
            max_attempts=1,
        )
        job = self.store.submit(request, at=self.now)
        for _ in range(2):
            self.assertEqual(
                self.store.cancel(
                    job.investigation_id, access_scope="scope:a", at=self.now
                ).status,
                "cancelled",
            )
        self.assertIsNone(self.store.claim(lease_seconds=60))
