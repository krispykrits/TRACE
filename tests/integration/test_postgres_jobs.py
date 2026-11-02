"""PostgreSQL queue contracts, executed only against an isolated test database."""

from __future__ import annotations

import os
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import psycopg

from trace_app.adapters.storage.postgres.execution import PostgresExecutionLedger
from trace_app.adapters.storage.postgres.jobs import PostgresJobs
from trace_app.adapters.storage.postgres.model_journal import PostgresModelJournal
from trace_app.adapters.storage.postgres.reports import PostgresReportReader
from trace_app.adapters.storage.postgres.workflow import PostgresWorkflowStore
from trace_app.investigation.bundle import EvidencePackage
from trace_app.investigation.execution import (
    ExecutionIdentity,
    ExecutionPolicy,
    ExecutionRejected,
    ExecutionState,
)
from trace_app.investigation.models import (
    Investigation,
    InvestigationRequest,
    StoreAccessError,
    StoreStateError,
)
from trace_app.investigation.provider import (
    ModelErrorCode,
    ModelPricing,
    ModelProviderError,
    ModelUsage,
)
from trace_app.investigation.worker import InvestigationWorker

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
                "DROP TABLE IF EXISTS trace_workflow_artifacts, trace_workflow_runs, trace_snapshots, trace_model_redactions, trace_model_attempts, trace_model_months, trace_model_budget, trace_execution_calls, trace_execution_runs, trace_job_attempts, trace_jobs, trace_principal_grants CASCADE"
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

    def test_execution_ledger_serializes_and_fences_attempts(self) -> None:
        request = InvestigationRequest(
            "key",
            "orders",
            "test",
            "scope:a",
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:01:00Z",
            max_attempts=1,
        )
        self.store.submit(request, at=self.now)
        job = self.store.claim(lease_seconds=60)
        assert job is not None and job.active_attempt_id is not None
        identity = ExecutionIdentity(
            job.investigation_id, job.active_attempt_id, "correlation", "scope:a"
        )
        ledger = PostgresExecutionLedger(self.dsn)
        barrier = threading.Barrier(2)

        def increment() -> None:
            barrier.wait()

            def operation(state: ExecutionState) -> None:
                state.tool_calls += 1

            ledger.apply(identity, ExecutionPolicy(), time.time(), operation)

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda _: increment(), range(2)))
        with psycopg.connect(self.dsn) as connection:
            row = connection.execute(
                "SELECT state FROM trace_execution_runs WHERE investigation_id=%s",
                (job.investigation_id,),
            ).fetchone()
        assert row is not None
        import json

        self.assertEqual(json.loads(row[0])["tool_calls"], 2)
        wrong_attempt = ExecutionIdentity(
            job.investigation_id, job.active_attempt_id + 1, "correlation", "scope:a"
        )
        with self.assertRaises(ExecutionRejected):
            ledger.apply(
                wrong_attempt, ExecutionPolicy(), time.time(), lambda state: None
            )
        with psycopg.connect(self.dsn) as connection:
            connection.execute(
                "DELETE FROM trace_principal_grants WHERE tenant_id=%s AND object_id=%s",
                PRINCIPAL,
            )
        with self.assertRaises(ExecutionRejected):
            ledger.apply(identity, ExecutionPolicy(), time.time(), lambda state: None)

    def test_model_budget_is_shared_and_unknown_usage_is_conservative(self) -> None:
        pricing = ModelPricing("pricing.v1", 1, 1)
        with psycopg.connect(self.dsn) as connection:
            connection.execute(
                "INSERT INTO trace_model_budget VALUES (1,15,'pricing.v1',1,1)"
            )
            connection.execute(
                "INSERT INTO trace_model_months SELECT to_char(clock_timestamp() AT TIME ZONE 'UTC', 'YYYY-MM'), 0"
            )
        jobs = []
        for key in ("one", "two"):
            request = InvestigationRequest(
                key,
                "orders",
                "test",
                "scope:a",
                "2026-01-01T00:00:00Z",
                "2026-01-01T00:01:00Z",
                max_attempts=1,
            )
            self.store.submit(request, at=self.now)
            job = self.store.claim(lease_seconds=60)
            assert job is not None and job.active_attempt_id is not None
            jobs.append(job)
        barrier = threading.Barrier(2)
        journal = PostgresModelJournal(self.dsn, pricing, monthly_limit_nusd=15)

        def reserve(index: int) -> tuple[dict[str, object], str]:
            job = jobs[index]
            metadata: dict[str, object] = {
                "request_id": f"call-{index}",
                "scope_id": job.investigation_id,
                "attempt_id": job.active_attempt_id,
            }
            barrier.wait()
            try:
                journal.begin(metadata, (), 10, 0, time.time())
                return metadata, "reserved"
            except ModelProviderError as error:
                return metadata, error.code.value

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(reserve, range(2)))
        self.assertEqual(
            sorted(result for _, result in results),
            sorted(["reserved", ModelErrorCode.BUDGET.value]),
        )
        metadata = next(meta for meta, result in results if result == "reserved")
        journal.finish(
            metadata | {"outcome": "timeout"}, ModelUsage(20, None), True, time.time()
        )
        with psycopg.connect(self.dsn) as connection:
            row = connection.execute(
                "SELECT charged_nusd, dispatched FROM trace_model_attempts WHERE request_id=%s",
                (metadata["request_id"],),
            ).fetchone()
        self.assertEqual(row, (20, True))

    def test_worker_fails_unpublished_attempt_without_replay(self) -> None:
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
        seen: list[str] = []
        worker = InvestigationWorker(
            self.store,
            lambda claimed: seen.append(claimed.investigation_id),
            lease_seconds=60,
        )
        self.assertTrue(worker.run_once())
        self.assertFalse(worker.run_once())
        self.assertEqual(seen, [job.investigation_id])
        result = self.store.get_investigation(
            job.investigation_id, access_scope="scope:a"
        )
        self.assertEqual(
            (result.status, result.failure_code), ("failed", "executor_incomplete")
        )

    def test_workflow_retention_completion_and_fencing(self) -> None:
        request = InvestigationRequest(
            "key",
            "orders",
            "test",
            "scope:a",
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:01:00Z",
            max_attempts=1,
        )
        self.store.submit(request, at=self.now)
        job = self.store.claim(lease_seconds=60)
        assert job is not None and job.active_attempt_id is not None
        identity = ExecutionIdentity(
            job.investigation_id, job.active_attempt_id, "correlation", "scope:a"
        )
        workflow = PostgresWorkflowStore(self.dsn)
        workflow.start(identity, at=self.now)
        with self.assertRaises(StoreStateError):
            workflow.start(identity, at=self.now)
        workflow.phase(identity, "gathering", at=self.now)
        with self.assertRaises(StoreStateError):
            workflow.phase(identity, "evidence_only", at=self.now)
        package = EvidencePackage(
            "partial", {"events": []}, "digest", job.investigation_id, (), None
        )
        artifact = workflow.retain(identity, package, at=self.now)
        self.assertTrue(artifact)
        with psycopg.connect(self.dsn) as connection:
            connection.execute(
                "UPDATE trace_jobs SET lease_until=clock_timestamp()-interval '1 second' WHERE investigation_id=%s",
                (job.investigation_id,),
            )
        with self.assertRaises(StoreStateError):
            workflow.phase(identity, "evidence_only", at=self.now)
        with psycopg.connect(self.dsn) as connection:
            row = connection.execute(
                "SELECT status FROM trace_jobs WHERE investigation_id=%s",
                (job.investigation_id,),
            ).fetchone()
        self.assertEqual(row, ("running",))

        second = InvestigationRequest(
            "key-2",
            "orders",
            "test",
            "scope:a",
            "2026-01-01T00:00:00Z",
            "2026-01-01T00:01:00Z",
            max_attempts=1,
        )
        self.store.submit(second, at=self.now)
        second_job = self.store.claim(lease_seconds=60)
        assert second_job is not None and second_job.active_attempt_id is not None
        second_identity = ExecutionIdentity(
            second_job.investigation_id,
            second_job.active_attempt_id,
            "correlation",
            "scope:a",
        )
        workflow.start(second_identity, at=self.now)
        workflow.phase(second_identity, "gathering", at=self.now)
        second_artifact = workflow.retain(
            second_identity,
            EvidencePackage(
                "partial",
                {"events": []},
                "digest",
                second_job.investigation_id,
                (),
                None,
            ),
            at=self.now,
        )
        workflow.phase(second_identity, "evidence_only", at=self.now)
        completed = self.store.get_investigation(
            second_job.investigation_id, access_scope="scope:a"
        )
        self.assertEqual(
            (completed.status, completed.assessment_status), ("completed", "pending")
        )
        reader = PostgresReportReader(self.dsn, principal=PRINCIPAL)
        saved = reader.load(second_job.investigation_id, access_scope="scope:a")
        self.assertEqual(saved.artifacts[0]["artifact_id"], second_artifact)
        self.assertEqual(saved.attempts[0].outcome, "completed")
        with psycopg.connect(self.dsn) as connection:
            connection.execute(
                "DELETE FROM trace_principal_grants WHERE tenant_id=%s AND object_id=%s",
                PRINCIPAL,
            )
        with self.assertRaises(StoreAccessError):
            reader.load(second_job.investigation_id, access_scope="scope:a")
