"""Preparation commits a captured local job without running a worker or model."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

from trace_app.adapters.storage.sqlite.investigations import SQLiteInvestigationStore
from trace_app.evidence.models import SourceAvailability
from trace_app.evidence.queries import TrustedQueryContext
from trace_app.investigation.assessment_context import AssessmentBoundaryError
from trace_app.investigation.local_service import LocalInvestigator
from trace_app.investigation.models import (
    EvidenceSnapshot,
    InvestigationRequest,
    StoreAccessError,
)

START = "2026-01-01T00:00:00Z"
END = "2026-01-01T01:00:00Z"


class LocalPreparationTests(unittest.TestCase):
    def test_competing_worker_processes_do_not_start_two_attempts(self) -> None:
        from scripts.demo_investigator import Clock
        from scripts.investigator_fixture import prepare
        from trace_app.bootstrap import create_local_investigator

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fixture"
            profile = prepare(root)
            config = json.loads(profile.read_text())
            producer = create_local_investigator(profile, clock=Clock())
            job = producer.prepare(
                service="order",
                environment="test",
                window_start=config["fixture"]["window_start"],
                window_end=config["fixture"]["window_end"],
            )
            producer.close()
            command = [
                sys.executable,
                "-m",
                "scripts.investigator_fixture",
                "--directory",
                str(root),
                "--",
                "run-prepared-investigation",
                "--investigation-id",
                job.investigation_id,
                "--format",
                "json",
            ]

            def run_worker() -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    command, capture_output=True, text=True, timeout=120
                )

            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: run_worker(), range(2)))
            self.assertTrue(any(result.returncode == 0 for result in results))
            self.assertTrue(all(result.returncode in (0, 6) for result in results))
            with sqlite3.connect(config["evidence_db"]) as db:
                count = db.execute(
                    "SELECT COUNT(*) FROM attempts WHERE investigation_id = ?",
                    (job.investigation_id,),
                ).fetchone()[0]
            self.assertEqual(count, 1)

    def test_cli_submits_and_runs_in_separate_processes(self) -> None:
        from scripts.investigator_fixture import prepare

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "fixture"
            profile = prepare(root)
            fixture = json.loads(profile.read_text())["fixture"]
            command = [
                sys.executable,
                "-m",
                "scripts.investigator_fixture",
                "--directory",
                str(root),
                "--",
            ]
            submitted = subprocess.run(
                [
                    *command,
                    "prepare-investigation",
                    "--service",
                    "order",
                    "--environment",
                    "test",
                    "--window-start",
                    fixture["window_start"],
                    "--window-end",
                    fixture["window_end"],
                    "--format",
                    "json",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=120,
            )
            queued = json.loads(submitted.stdout)
            self.assertEqual(queued["execution_status"], "queued")
            worker = subprocess.run(
                [
                    *command,
                    "run-prepared-investigation",
                    "--investigation-id",
                    queued["investigation_id"],
                    "--format",
                    "json",
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=120,
            )
            result = json.loads(worker.stdout)
            self.assertEqual(result["execution_status"], "completed")
            self.assertEqual(result["configuration"]["mode"], "evidence_only")
            self.assertEqual(len(result["attempts"]), 1)

    def test_prepare_then_run_in_separate_compositions_without_model(self) -> None:
        from scripts.demo_investigator import Clock
        from scripts.investigator_fixture import prepare
        from trace_app.bootstrap import create_local_investigator

        with tempfile.TemporaryDirectory() as directory:
            profile_path = prepare(Path(directory) / "fixture")
            fixture = json.loads(profile_path.read_text())["fixture"]
            producer = create_local_investigator(profile_path, clock=Clock())
            job = producer.prepare(
                service="order",
                environment="test",
                window_start=fixture["window_start"],
                window_end=fixture["window_end"],
            )
            self.assertEqual(job.status, "queued")
            producer.close()

            worker = create_local_investigator(profile_path, clock=Clock())
            self.addCleanup(worker.close)
            result = worker.run_prepared(job.investigation_id)
            self.assertEqual(result["execution_status"], "completed")
            self.assertIsNone(result["report"])
            self.assertEqual(result["configuration"]["mode"], "evidence_only")
            again = worker.run_prepared(job.investigation_id)
            self.assertEqual(len(again["attempts"]), 1)

    def test_cancelled_prepared_job_is_not_executed(self) -> None:
        from scripts.demo_investigator import Clock
        from scripts.investigator_fixture import prepare
        from trace_app.bootstrap import create_local_investigator

        with tempfile.TemporaryDirectory() as directory:
            profile_path = prepare(Path(directory) / "fixture")
            fixture = json.loads(profile_path.read_text())["fixture"]
            app = create_local_investigator(profile_path, clock=Clock())
            self.addCleanup(app.close)
            job = app.prepare(
                service="order",
                environment="test",
                window_start=fixture["window_start"],
                window_end=fixture["window_end"],
            )
            app.cancel(job.investigation_id)
            result = app.run_prepared(job.investigation_id)
            self.assertEqual(result["execution_status"], "cancelled")
            self.assertEqual(result["attempts"], [])

    def test_prepare_persists_snapshot_without_claim_or_dispatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "jobs.db"
            store = SQLiteInvestigationStore(path)
            self.addCleanup(store.close)
            snapshot = EvidenceSnapshot(
                (), START, END, (SourceAvailability("logs", "available"),)
            )
            workflow = Mock(side_effect=AssertionError("worker must not run"))
            app = LocalInvestigator(
                store,
                TrustedQueryContext("scope", "test", ("order",)),
                lambda: snapshot,
                workflow,
                Mock(),
                Mock(),
                clock=lambda: datetime(2026, 1, 1, 2, tzinfo=UTC).timestamp(),
            )
            request = dict(
                service="order", environment="test", window_start=START, window_end=END
            )
            job = app.prepare(**request)
            self.assertEqual(job.status, "queued")
            self.assertEqual(job.attempt_count, 0)
            self.assertEqual(
                app.prepare(**request).investigation_id, job.investigation_id
            )
            workflow.assert_not_called()
            with SQLiteInvestigationStore(path, read_only=True) as reopened:
                persisted = reopened.get_investigation(
                    job.investigation_id, access_scope="scope"
                )
                captured = reopened.get_snapshot(
                    job.investigation_id, access_scope="scope"
                )
            self.assertEqual(persisted.status, "queued")
            self.assertEqual(persisted.attempt_count, 0)
            self.assertEqual(captured.sources, snapshot.sources)

    def test_denied_request_does_not_read_source_or_submit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteInvestigationStore(Path(directory) / "jobs.db")
            self.addCleanup(store.close)
            source = Mock(side_effect=AssertionError("source must not be read"))
            app = LocalInvestigator(
                store,
                TrustedQueryContext("scope", "test", ("order",)),
                source,
                Mock(),
                Mock(),
                Mock(),
            )
            with self.assertRaises(AssessmentBoundaryError):
                app.prepare(
                    service="payment",
                    environment="test",
                    window_start=START,
                    window_end=END,
                )
            source.assert_not_called()

    def test_worker_does_not_claim_incomplete_submission(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteInvestigationStore(Path(directory) / "jobs.db")
            self.addCleanup(store.close)
            job = store.submit(
                InvestigationRequest("key", "order", "test", "scope", START, END),
                at=datetime(2026, 1, 1, 2, tzinfo=UTC),
            )
            workflow = Mock(side_effect=AssertionError("worker must not run"))
            app = LocalInvestigator(
                store,
                TrustedQueryContext("scope", "test", ("order",)),
                Mock(),
                workflow,
                Mock(),
                Mock(),
            )
            with self.assertRaises(StoreAccessError):
                app.run_prepared(job.investigation_id)
            persisted = store.get_investigation(
                job.investigation_id, access_scope="scope"
            )
            self.assertEqual(persisted.status, "queued")
            self.assertEqual(persisted.attempt_count, 0)
            workflow.assert_not_called()

    def test_worker_respects_disabled_evidence_only_mode(self) -> None:
        store = Mock()
        app = LocalInvestigator(
            store,
            TrustedQueryContext("scope", "test", ("order",)),
            Mock(),
            Mock(),
            Mock(),
            Mock(),
            allowed_providers=("azure",),
        )
        with self.assertRaisesRegex(ValueError, "unavailable"):
            app.run_prepared("job")
        store.get_investigation.assert_not_called()


if __name__ == "__main__":
    unittest.main()
