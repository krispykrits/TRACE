"""SIGKILL at real CLI/SQLite boundaries; synthetic providers, no paid calls."""

from __future__ import annotations

import json
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from scripts.demo_integration import AT
from scripts.investigator_fixture import prepare
from scripts.local_recovery_fixture import POINTS
from trace_app.adapters.models.journal import SqliteProviderJournal
from trace_app.adapters.storage.sqlite.investigations import SQLiteInvestigationStore
from trace_app.investigation.models import InvestigationRequest
from trace_app.investigation.provider import (
    ModelErrorCode,
    ModelPricing,
    ModelProviderError,
)

ROOT = Path(__file__).resolve().parents[2]


def run_fixture(directory: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "scripts.investigator_fixture",
            "--directory",
            str(directory),
            *arguments,
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        env={"PATH": os.environ.get("PATH", os.defpath), "OPENBLAS_NUM_THREADS": "1"},
    )


def ledger(directory: Path) -> tuple:
    with sqlite3.connect(directory / "evidence.sqlite3") as db:
        job = db.execute(
            "SELECT investigation_id,status,assessment_status FROM investigations "
            "WHERE investigation_id IN (SELECT investigation_id FROM workflow_runs)"
        ).fetchone()
        artifacts = db.execute(
            "SELECT role,body FROM workflow_artifacts ORDER BY rowid"
        ).fetchall()
        calls = db.execute(
            "SELECT metadata FROM execution_calls ORDER BY rowid"
        ).fetchall()
        state = db.execute("SELECT state FROM execution_runs").fetchone()[0]
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    with sqlite3.connect(directory / "provider.sqlite3") as db:
        reservations = db.execute(
            "SELECT * FROM attempts ORDER BY request_id"
        ).fetchall()
        months = db.execute("SELECT * FROM months ORDER BY month").fetchall()
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    return job, artifacts, calls, state, reservations, months


class AcceptedRestoreTests(unittest.TestCase):
    def test_accepted_restore_preserves_review_identity_and_rechecks_support(
        self,
    ) -> None:
        # Original demonstration policy, deliberately distinct from the 40-call
        # review-required readiness probes; fictional verdicts are not humans.
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original, restored = root / "source", root / "restored"
            prepare(original, reviewed=True)
            process = run_fixture(original)
            self.assertEqual(process.returncode, 0, process.stderr)
            result = json.loads(process.stdout)
            restored.mkdir(mode=0o700)
            for name in ("evidence.sqlite3", "corpus.sqlite3", "provider.sqlite3"):
                with (
                    sqlite3.connect(original / name) as source,
                    sqlite3.connect(restored / name) as target,
                ):
                    source.backup(target)
                (restored / name).chmod(0o600)
            shutil.copytree(original / "index", restored / "index")
            data = json.loads((original / "profile.json").read_text())
            self.assertTrue(data["reviews"])
            reviews = data["reviews"]
            for key, name in (
                ("evidence_db", "evidence.sqlite3"),
                ("corpus_db", "corpus.sqlite3"),
                ("index_root", "index"),
            ):
                data[key] = str(restored / name)
            profile = restored / "profile.json"
            profile.write_text(json.dumps(data))
            profile.chmod(0o600)
            self.assertEqual(json.loads(profile.read_text())["reviews"], reviews)
            self.assertEqual(ledger(restored), ledger(original))
            arguments = (
                "--",
                "report",
                "--investigation-id",
                result["investigation_id"],
                "--format",
                "json",
            )
            inspected = run_fixture(restored, *arguments)
            self.assertEqual(inspected.returncode, 0, inspected.stderr)
            delivered = json.loads(inspected.stdout)
            for name in ("report", "citations", "timeline"):
                self.assertEqual(delivered[name], result[name])
            self.assertFalse(delivered["actual_human_review"])
            data["reviews"] = []
            profile.write_text(json.dumps(data))
            denied = run_fixture(restored, *arguments)
            self.assertEqual(denied.returncode, 4, denied.stderr)
            self.assertEqual(denied.stdout, "")
            self.assertNotIn("synthetic_mechanism", denied.stderr)
            self.assertEqual(ledger(restored), ledger(original))


class LocalRecoveryTests(unittest.TestCase):
    temporary: tempfile.TemporaryDirectory[str]
    root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="trace-local-recovery-")
        cls.root = Path(cls.temporary.name)
        for point in POINTS:
            directory = cls.root / point
            profile = prepare(directory, reviewed=False)
            data = json.loads(profile.read_text())
            data["execution_policy"]["max_tool_calls"] = 40
            profile.write_text(json.dumps(data))
            marker = cls.root / (point + ".marker")
            process = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "scripts.local_recovery_fixture",
                    "--point",
                    point,
                    "--marker",
                    str(marker),
                    "--directory",
                    str(directory),
                ],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=120,
                env={
                    "PATH": os.environ.get("PATH", os.defpath),
                    "OPENBLAS_NUM_THREADS": "1",
                },
            )
            if process.returncode != -signal.SIGKILL or marker.read_text() != point:
                raise AssertionError(
                    (point, process.returncode, process.stderr[-1000:])
                )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_atomic_publication_and_evidence_survive_process_death(self) -> None:
        for point in POINTS:
            with self.subTest(point=point):
                job, artifacts, calls, state, reservations, _ = ledger(
                    self.root / point
                )
                self.assertEqual(
                    job[1], "completed" if point == "after_publication" else "running"
                )
                self.assertEqual(
                    sum(role == "review_required" for role, _ in artifacts),
                    int(point == "after_publication"),
                )
                self.assertEqual(
                    sum(role == "untrusted_evidence" for role, _ in artifacts),
                    int(point != "before_retention"),
                )
                saved = json.loads(state)
                self.assertLessEqual(saved["tool_calls"], 40)
                model = [
                    json.loads(row[0])
                    for row in calls
                    if json.loads(row[0])["kind"] == "model"
                ]
                if point in ("before_dispatch", "after_dispatch"):
                    self.assertEqual(len(reservations), 1)
                    self.assertEqual(reservations[0][5], "reserved")
                    self.assertGreater(reservations[0][4], 0)
                    self.assertEqual(model[0]["dispatched"], point == "after_dispatch")

    def test_duplicate_cli_restart_never_resets_or_dispatches(self) -> None:
        for point in POINTS:
            with self.subTest(point=point):
                directory = self.root / point
                before = ledger(directory)
                process = run_fixture(directory)
                self.assertIn(process.returncode, (6, 7), process.stderr)
                self.assertEqual(ledger(directory), before)

    def test_consistent_quiescent_restore_preserves_reports_and_reservations(
        self,
    ) -> None:
        for point in ("after_dispatch", "after_publication"):
            with self.subTest(point=point), tempfile.TemporaryDirectory() as temporary:
                original = self.root / point
                restored = Path(temporary) / "restore"
                restored.mkdir(mode=0o700)
                # No writers remain. SQLite backup includes committed WAL state.
                for name in ("evidence.sqlite3", "corpus.sqlite3", "provider.sqlite3"):
                    with (
                        sqlite3.connect(original / name) as source,
                        sqlite3.connect(restored / name) as target,
                    ):
                        source.backup(target)
                    (restored / name).chmod(0o600)
                shutil.copytree(original / "index", restored / "index")
                data = json.loads((original / "profile.json").read_text())
                for key, name in (
                    ("evidence_db", "evidence.sqlite3"),
                    ("corpus_db", "corpus.sqlite3"),
                    ("index_root", "index"),
                ):
                    data[key] = str(restored / name)
                profile = restored / "profile.json"
                profile.write_text(json.dumps(data))
                profile.chmod(0o600)
                self.assertEqual(ledger(restored), ledger(original))
                before = ledger(restored)
                process = run_fixture(restored)
                self.assertIn(process.returncode, (6, 7), process.stderr)
                self.assertEqual(ledger(restored), before)
                if point == "after_dispatch":
                    with sqlite3.connect(restored / "provider.sqlite3") as db:
                        limit, version, input_rate, output_rate = db.execute(
                            "SELECT limit_nusd,pricing,input_rate,output_rate FROM configuration"
                        ).fetchone()
                    journal = SqliteProviderJournal(
                        restored / "provider.sqlite3",
                        ModelPricing(version, input_rate, output_rate),
                        monthly_limit_nusd=limit,
                        initial_spend_nusd=0,
                        now=AT.timestamp(),
                    )
                    metadata = json.loads(before[4][0][6])
                    metadata["request_id"] = "refused-recovery-replay"
                    with self.assertRaises(ModelProviderError) as failure:
                        journal.begin(metadata, (), 1, 1, AT.timestamp())
                    self.assertEqual(failure.exception.code, ModelErrorCode.BUDGET)
                    self.assertEqual(ledger(restored), before)
                if point == "after_publication":
                    identity = before[0][0]
                    inspected = run_fixture(
                        restored,
                        "--",
                        "report",
                        "--investigation-id",
                        identity,
                        "--format",
                        "json",
                    )
                    self.assertEqual(inspected.returncode, 7, inspected.stderr)
                    self.assertTrue(json.loads(inspected.stdout)["timeline"])
                    event = json.loads(inspected.stdout)["timeline"][0]["citation_id"]
                    data["grants"][event]["access_allowed"] = False
                    profile.write_text(json.dumps(data))
                    denied = run_fixture(
                        restored,
                        "--",
                        "report",
                        "--investigation-id",
                        identity,
                        "--format",
                        "json",
                    )
                    self.assertEqual(denied.returncode, 4, denied.stderr)
                    self.assertEqual(denied.stdout, "")

    def test_expired_recovery_keeps_accounting_without_replay(self) -> None:
        original = self.root / "after_dispatch"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "jobs.sqlite3"
            with (
                sqlite3.connect(original / "evidence.sqlite3") as source,
                sqlite3.connect(path) as target,
            ):
                source.backup(target)
            path.chmod(0o600)
            before = ledger(original)
            profile = json.loads((original / "profile.json").read_text())
            with SQLiteInvestigationStore(path) as store:
                active = store.get_investigation(
                    before[0][0], access_scope=profile["evidence_scope"]["access_scope"]
                )
                assert active.lease_until is not None
                expired_at = datetime.fromisoformat(active.lease_until) + timedelta(
                    seconds=1
                )
                self.assertGreater(store.recover(at=expired_at), 0)
                job = store.get_investigation(
                    before[0][0], access_scope=profile["evidence_scope"]["access_scope"]
                )
                self.assertNotEqual(job.status, "completed")
            with sqlite3.connect(path) as db:
                self.assertEqual(
                    db.execute("SELECT state FROM execution_runs").fetchone()[0],
                    before[3],
                )
                self.assertEqual(
                    db.execute(
                        "SELECT COUNT(*) FROM workflow_artifacts WHERE role='accepted'"
                    ).fetchone()[0],
                    0,
                )

    def test_competing_processes_claim_one_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "claims.sqlite3"
            with SQLiteInvestigationStore(path) as store:
                job = store.submit(
                    InvestigationRequest(
                        "same-key",
                        "order",
                        "test",
                        "recovery-scope",
                        "2026-01-01T00:00:00Z",
                        "2026-01-01T00:00:01Z",
                    ),
                    at=AT,
                )
                self.assertEqual(
                    store.submit(job.request, at=AT).investigation_id,
                    job.investigation_id,
                )
            code = (
                "import sys; from pathlib import Path; from scripts.demo_integration import AT; "
                "from trace_app.adapters.storage.sqlite.investigations import SQLiteInvestigationStore; "
                "store=SQLiteInvestigationStore(Path(sys.argv[1])); "
                "job=store.claim_next(at=AT,lease_seconds=120); "
                "print('claimed' if job else 'unavailable'); store.close()"
            )
            processes = [
                subprocess.Popen(
                    [sys.executable, "-c", code, str(path)],
                    cwd=ROOT,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                )
                for _ in range(2)
            ]
            try:
                outputs = [process.communicate(timeout=30) for process in processes]
                self.assertEqual(
                    sorted(out.strip() for out, _ in outputs),
                    ["claimed", "unavailable"],
                )
                self.assertTrue(all(process.returncode == 0 for process in processes))
            finally:
                for process in processes:
                    if process.poll() is None:
                        process.kill()
                    process.wait(timeout=5)
            with sqlite3.connect(path) as db:
                self.assertEqual(
                    db.execute("SELECT COUNT(*) FROM attempts").fetchone()[0], 1
                )

    def test_reviewed_fixture_stops_at_40_without_partial_publication(self) -> None:
        directory = self.root / "reviewed-budget-boundary"
        profile = prepare(directory, reviewed=True)
        data = json.loads(profile.read_text())
        data["execution_policy"]["max_tool_calls"] = 40
        profile.write_text(json.dumps(data))
        process = run_fixture(directory)
        self.assertEqual(process.returncode, 3, process.stderr)
        job, artifacts, calls, _, _, _ = ledger(directory)
        self.assertEqual(job[1], "failed")
        self.assertFalse(any(role == "accepted" for role, _ in artifacts))
        dispatched = [json.loads(row[0]) for row in calls]
        self.assertLessEqual(
            sum(row["kind"] == "tool" and row["dispatched"] for row in dispatched), 40
        )
        self.assertTrue(any(row["outcome"] == "budget_exhausted" for row in dispatched))

    def test_incompatible_corrupt_and_incomplete_state_refuse_cli_delivery(
        self,
    ) -> None:
        original = self.root / "after_publication"
        for failure in ("newer_schema", "corrupt", "incomplete"):
            with (
                self.subTest(failure=failure),
                tempfile.TemporaryDirectory() as temporary,
            ):
                directory = Path(temporary)
                path = directory / "evidence.sqlite3"
                with (
                    sqlite3.connect(original / path.name) as source,
                    sqlite3.connect(path) as target,
                ):
                    source.backup(target)
                path.chmod(0o600)
                if failure == "corrupt":
                    path.write_bytes(b"invalid sqlite state")
                else:
                    with sqlite3.connect(path) as db:
                        db.execute(
                            "PRAGMA user_version=999"
                            if failure == "newer_schema"
                            else "DROP TABLE workflow_artifacts"
                        )
                data = json.loads((original / "profile.json").read_text())
                data["evidence_db"] = str(path)
                profile = directory / "profile.json"
                profile.write_text(json.dumps(data))
                profile.chmod(0o600)
                before = path.read_bytes()
                identity = ledger(original)[0][0]
                # Actual CLI composition/handler, with only its clock replaced.
                code = (
                    "import sys; from unittest.mock import patch; "
                    "from scripts.demo_investigator import Clock; "
                    "from trace_app.bootstrap import create_local_investigator; "
                    "from trace_app.cli import main; "
                    "factory=lambda path:create_local_investigator(path,clock=Clock()); "
                    "patcher=patch('trace_app.cli.investigator.create_local_investigator',factory); "
                    "patcher.start(); raise SystemExit(main(sys.argv[1:]))"
                )
                process = subprocess.run(
                    [
                        sys.executable,
                        "-c",
                        code,
                        "report",
                        "--investigation-id",
                        identity,
                        "--format",
                        "json",
                    ],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    env={
                        "PATH": os.environ.get("PATH", os.defpath),
                        "TRACE_INVESTIGATOR_PROFILE": str(profile),
                    },
                )
                self.assertIn(process.returncode, (2, 3, 6), process.stderr)
                self.assertEqual(process.stdout, "")
                self.assertNotIn("Traceback", process.stderr)
                self.assertNotIn("synthetic_mechanism", process.stderr)
                self.assertEqual(path.read_bytes(), before)
