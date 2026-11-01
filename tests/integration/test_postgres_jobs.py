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
PRINCIPAL = (
    "00000000-0000-0000-0000-000000000001",
    "00000000-0000-0000-0000-000000000002",
)


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
                "DROP TABLE IF EXISTS trace_job_attempts, trace_jobs, trace_principal_grants CASCADE"
            )
            schema = Path(
                "src/trace_app/adapters/storage/postgres/schema.sql"
            ).read_text()
            connection.execute(schema)
            connection.execute(
                "INSERT INTO trace_principal_grants VALUES (%s,%s,%s,%s,%s,%s)",
                (
                    *PRINCIPAL,
                    "scope:a",
                    "test",
                    ["orders"],
                    ["submit", "read", "cancel"],
                ),
            )
        self.store = PostgresJobs(self.dsn, principal=PRINCIPAL)
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
            return (
                PostgresJobs(self.dsn, principal=PRINCIPAL)
                .submit(request, at=self.now)
                .investigation_id
            )

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

    def test_revoked_submitter_cannot_be_claimed(self) -> None:
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
        with psycopg.connect(self.dsn) as connection:
            connection.execute(
                "DELETE FROM trace_principal_grants WHERE tenant_id=%s AND object_id=%s",
                PRINCIPAL,
            )
        self.assertIsNone(self.store.claim(lease_seconds=60))
        with psycopg.connect(self.dsn) as connection:
            row = connection.execute(
                "SELECT status, failure_code FROM trace_jobs WHERE investigation_id=%s",
                (job.investigation_id,),
            ).fetchone()
        self.assertEqual(row, ("failed", "access_denied"))
