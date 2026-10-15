"""Real CLI processes, durable restart and current disclosure policy; no paid calls."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


class InvestigatorCliTests(unittest.TestCase):
    temporary: tempfile.TemporaryDirectory[str]
    root: Path
    results: dict[str, dict[str, Any]]
    profile_path: Path
    original_profile: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="trace-cli-38-")
        cls.root = Path(cls.temporary.name)
        cls.results = {}
        for case, extra in (
            ("answered", []),
            ("abstained", ["--case", "c04"]),
            ("timeout", ["--failure", "timeout"]),
            ("cancelled", ["--failure", "cancelled"]),
            ("pending", ["--unreviewed"]),
        ):
            process = cls.execute(case, *extra)
            expected = (
                5
                if case == "timeout"
                else 130
                if case == "cancelled"
                else 7
                if case == "pending"
                else 0
            )
            if process.returncode != expected:
                raise AssertionError((case, process.returncode, process.stderr[-2000:]))
            cls.results[case] = json.loads(process.stdout)
        cls.profile_path = cls.root / "answered/profile.json"
        cls.original_profile = cls.profile_path.read_text()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def tearDown(self) -> None:
        self.profile_path.write_text(self.original_profile)
        self.profile_path.chmod(0o600)

    @classmethod
    def execute(cls, case: str, *arguments: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.investigator_fixture",
                "--directory",
                str(cls.root / case),
                *arguments,
            ],
            cwd=ROOT,
            env={
                "PATH": os.environ.get("PATH", os.defpath),
                "OPENBLAS_NUM_THREADS": "1",
            },
            capture_output=True,
            text=True,
            timeout=120,
        )

    def report(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        return self.execute(
            "answered",
            "--",
            "report",
            "--investigation-id",
            self.results["answered"]["investigation_id"],
            *arguments,
        )

    def change_profile(self, transform: Any) -> None:
        data = json.loads(self.original_profile)
        transform(data)
        self.profile_path.write_text(json.dumps(data))

    def assert_denied(self, process: subprocess.CompletedProcess[str]) -> None:
        self.assertEqual(process.returncode, 4, process.stderr)
        self.assertEqual(process.stdout, "")
        self.assertNotIn("synthetic_mechanism", process.stderr)
        self.assertNotIn("source records", process.stderr)
        self.assertIn('"outcome":"access_denied"', process.stderr)

    def test_answerable_abstention_pending_timeout_and_cancel_are_distinct(
        self,
    ) -> None:
        for case in ("answered", "abstained"):
            result = self.results[case]
            self.assertEqual(result["schema_version"], "investigation-cli.v1")
            self.assertEqual(result["configuration"]["mode"], "offline_test")
            self.assertEqual(result["execution_status"], "completed")
            self.assertEqual(
                result["assessment_status"],
                "abstained" if case == "abstained" else "supported",
            )
            self.assertFalse(result["actual_human_review"])
            self.assertEqual(result["content_role"], "offline_hand_authored_simulation")
            self.assertEqual(
                result["timeline"],
                sorted(
                    result["timeline"],
                    key=lambda event: (event["observed_at"], event["citation_id"]),
                ),
            )
            self.assertTrue(result["report"]["observations"])
            self.assertTrue(result["report"]["alternative_hypotheses"])
            self.assertTrue(result["report"]["missing_evidence"])
            self.assertTrue(result["report"]["next_check"])
        for case in ("timeout", "cancelled"):
            result = self.results[case]
            self.assertIsNone(result["report"])
            self.assertTrue(result["timeline"])
            self.assertEqual(
                result["attempts"][0]["outcome"],
                "failed" if case == "timeout" else "cancelled",
            )
        self.assertEqual(self.results["pending"]["assessment_status"], "pending")
        self.assertEqual(
            self.results["pending"]["validation_outcome"], "review_required"
        )

    def test_restart_inspect_citation_export_and_no_overwrite(self) -> None:
        self.assertEqual(self.report().returncode, 0)
        citation = next(iter(self.results["answered"]["citations"]))
        resolved = self.report("--citation-id", citation, "--format", "json")
        self.assertEqual(resolved.returncode, 0, resolved.stderr)
        self.assertEqual(json.loads(resolved.stdout)["citation_id"], citation)
        destination = self.root / "private-export.json"
        exported = self.report("--format", "json", "--output", str(destination))
        self.assertEqual(exported.returncode, 0, exported.stderr)
        self.assertEqual(destination.stat().st_mode & 0o777, 0o600)
        original = destination.read_bytes()
        result = json.loads(original)
        self.assertNotIn("ground_truth", original.decode())
        self.assertNotIn("password", original.decode())
        self.assertNotIn("principal_id", result)
        self.assertNotIn("tasks", result)
        self.assertEqual(
            self.report("--format", "json", "--output", str(destination)).returncode, 3
        )
        self.assertEqual(destination.read_bytes(), original)

    def test_repeat_never_dispatches_again_even_when_provider_changes(self) -> None:
        path = self.root / "answered/evidence.sqlite3"

        def counts():
            with sqlite3.connect(path) as db:
                return db.execute(
                    "SELECT COUNT(*) FROM execution_calls WHERE json_extract(metadata, '$.kind')='model'"
                ).fetchone()[0], db.execute("SELECT COUNT(*) FROM attempts").fetchone()[
                    0
                ]

        before = counts()
        repeated = self.execute("answered")
        self.assertEqual(repeated.returncode, 0, repeated.stderr)
        self.assertEqual(
            json.loads(repeated.stdout)["investigation_id"],
            self.results["answered"]["investigation_id"],
        )
        config = json.loads(self.original_profile)["fixture"]
        changed = self.execute(
            "answered",
            "--",
            "investigate",
            "--service",
            "order",
            "--environment",
            "test",
            "--window-start",
            config["window_start"],
            "--window-end",
            config["window_end"],
            "--provider",
            "azure",
            "--format",
            "json",
        )
        self.assertEqual(changed.returncode, 0, changed.stderr)
        self.assertEqual(
            json.loads(changed.stdout)["configuration"]["mode"], "offline_test"
        )
        self.assertEqual(counts(), before)

    def test_revoked_input_blocks_report_and_saved_evidence(self) -> None:
        self.change_profile(
            lambda d: next(iter(d["grants"].values())).__setitem__(
                "access_allowed", False
            )
        )
        self.assert_denied(self.report())
        artifact = self.results["answered"]["artifacts"][0]["artifact_id"]
        self.assert_denied(self.report("--artifact-id", artifact, "--format", "json"))

    def test_narrower_audience_different_principal_and_scope_are_denied(self) -> None:
        for field, value in (
            ("clearance", "public"),
            ("principal_id", "different-operator"),
        ):
            with self.subTest(field=field):
                self.change_profile(lambda d: d.__setitem__(field, value))
                self.assert_denied(self.report("--format", "json"))
        self.change_profile(
            lambda d: d["evidence_scope"].__setitem__("access_scope", "unrelated-scope")
        )
        self.assert_denied(self.report())

    def test_expired_grant_profile_changed_classification_or_removed_review_denied(
        self,
    ) -> None:
        transforms = [
            lambda d: d.__setitem__("expires_at", "2026-10-12T11:00:00Z"),
            lambda d: next(iter(d["grants"].values())).__setitem__(
                "expires_at", "2026-10-12T11:00:00Z"
            ),
            lambda d: next(iter(d["grants"].values())).__setitem__(
                "sensitivity", "public"
            ),
            lambda d: d.__setitem__("reviews", []),
            lambda d: d["reviews"][0]["decision"].__setitem__("verdict", "unsupported"),
        ]
        for transform in transforms:
            self.change_profile(transform)
            self.assert_denied(self.report())

    def test_transmission_revocation_blocks_json_but_local_display_can_read(
        self,
    ) -> None:
        self.change_profile(
            lambda d: [
                g.__setitem__("transmission_allowed", False)
                for g in d["grants"].values()
            ]
        )
        self.assertEqual(self.report().returncode, 0)
        self.assert_denied(self.report("--format", "json"))
        destination = self.root / "denied-export.json"
        self.assert_denied(
            self.report("--format", "json", "--output", str(destination))
        )
        self.assertFalse(destination.exists())

    def test_withdrawn_knowledge_and_changed_originals_are_denied(self) -> None:
        from scripts.demo_integration import AT
        from trace_app.adapters.storage.sqlite.corpus import SQLiteCorpusStore

        path = self.root / "answered/corpus.sqlite3"
        original = path.read_bytes()
        try:
            with sqlite3.connect(path) as db:
                identity = db.execute(
                    "SELECT document_id FROM sources LIMIT 1"
                ).fetchone()[0]
            with SQLiteCorpusStore(path) as corpus:
                corpus.withdraw(identity, reason="revoked", at=AT)
            self.assert_denied(self.report())
        finally:
            path.write_bytes(original)
        self.change_profile(
            lambda d: [
                g.__setitem__("content_sha256", "0" * 64)
                for k, g in d["grants"].items()
                if k.startswith("knowledge-")
            ]
        )
        self.assert_denied(self.report())

    def test_invalid_input_precedes_any_profile_or_provider_access(self) -> None:
        environment = {
            "PATH": os.environ.get("PATH", os.defpath),
            "TRACE_INVESTIGATOR_PROFILE": "/does/not/exist",
        }
        for arguments in (
            (
                "--service",
                "order",
                "--window-start",
                "invalid",
                "--window-end",
                "invalid",
            ),
            (
                "--service",
                "bad\nvalue",
                "--window-start",
                "2026-01-01T00:00:00Z",
                "--window-end",
                "2026-01-01T00:00:01Z",
            ),
        ):
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "trace_app.cli",
                    "investigate",
                    "--environment",
                    "test",
                    "--provider",
                    "azure",
                    *arguments,
                ],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("bad\\nvalue", result.stderr)

    def test_public_cli_cannot_activate_fixture_provider(self) -> None:
        from scripts.demo_investigator import Clock
        from trace_app.bootstrap import create_local_investigator

        app = create_local_investigator(self.profile_path, clock=Clock())
        self.addCleanup(app.close)
        config = json.loads(self.original_profile)["fixture"]
        with self.assertRaises(ValueError):
            app.investigate(
                service="order",
                environment="test",
                window_start=config["window_start"],
                window_end=config["window_end"],
                provider="offline-fixture",
            )


class InvestigatorDependencyProcessTests(unittest.TestCase):
    def test_provider_dependency_failure_and_queued_capture_cancellation(self) -> None:
        with tempfile.TemporaryDirectory(prefix="trace-cli-dependency-") as directory:
            root = Path(directory) / "state"
            command = [
                sys.executable,
                "-m",
                "scripts.investigator_fixture",
                "--directory",
                str(root),
            ]
            failed = subprocess.run(
                [*command, "--failure", "dependency_failure"],
                cwd=ROOT,
                env={"PATH": os.environ.get("PATH", os.defpath)},
                capture_output=True,
                text=True,
                timeout=120,
            )
            self.assertEqual(failed.returncode, 3, failed.stderr)
            data = json.loads(failed.stdout)
            self.assertEqual(data["failure_code"], "dependency_failure")
            self.assertIsNone(data["report"])
            self.assertTrue(data["timeline"])
            profile = json.loads((root / "profile.json").read_text())
            cancelled = subprocess.run(
                [
                    *command,
                    "--",
                    "cancel-investigation",
                    "--investigation-id",
                    profile["source_investigation_id"],
                    "--format",
                    "json",
                ],
                cwd=ROOT,
                env={"PATH": os.environ.get("PATH", os.defpath)},
                capture_output=True,
                text=True,
                timeout=20,
            )
            self.assertEqual(cancelled.returncode, 130, cancelled.stderr)
            self.assertEqual(
                json.loads(cancelled.stdout)["execution_status"], "cancelled"
            )
            self.assertEqual(json.loads(cancelled.stdout)["attempts"], [])


class InvestigatorTargetedClaimTests(unittest.TestCase):
    def test_targeted_claim_cannot_claim_or_recover_another_scope(self) -> None:
        from datetime import timedelta

        from scripts.demo_integration import AT
        from trace_app.adapters.storage.sqlite.investigations import (
            SQLiteInvestigationStore,
        )
        from trace_app.investigation.models import (
            InvestigationRequest,
            StoreAccessError,
            StoreInputError,
        )

        with tempfile.TemporaryDirectory(prefix="trace-targeted-claim-") as directory:
            with SQLiteInvestigationStore(Path(directory) / "jobs.sqlite3") as jobs:
                first = jobs.submit(
                    InvestigationRequest(
                        "other",
                        "order",
                        "test",
                        "other-scope",
                        "2026-01-01T00:00:00Z",
                        "2026-01-01T00:00:01Z",
                    ),
                    at=AT,
                )
                jobs.claim_next(at=AT, lease_seconds=1)
                target = jobs.submit(
                    InvestigationRequest(
                        "target",
                        "order",
                        "test",
                        "target-scope",
                        "2026-01-01T00:00:00Z",
                        "2026-01-01T00:00:01Z",
                    ),
                    at=AT,
                )
                with self.assertRaises(StoreAccessError):
                    jobs.claim_next(
                        at=AT,
                        investigation_id=target.investigation_id,
                        access_scope="other-scope",
                    )
                with self.assertRaises(StoreInputError):
                    jobs.claim_next(at=AT, access_scope="other-scope")
                claimed = jobs.claim_next(
                    at=AT + timedelta(seconds=2),
                    investigation_id=target.investigation_id,
                    access_scope="target-scope",
                )
                self.assertIsNotNone(claimed)
                self.assertEqual(
                    jobs.get_investigation(
                        first.investigation_id, access_scope="other-scope"
                    ).status,
                    "running",
                )


class InvestigatorLegacyCommandTests(unittest.TestCase):
    def test_replay_ignores_investigator_only_process_settings(self) -> None:
        with tempfile.TemporaryDirectory(prefix="trace-cli-legacy-") as directory:
            env_file = Path(directory) / "empty.env"
            env_file.write_text("")
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "trace_app.cli",
                    "replay-dependency",
                    "--env-file",
                    str(env_file),
                    "--environment",
                    "test",
                    "--seed",
                    "17",
                    "--mode",
                    "normal",
                ],
                cwd=directory,
                env={
                    "PATH": os.environ.get("PATH", os.defpath),
                    "TRACE_INVESTIGATOR_PROFILE": "/private/nonexistent-profile.json",
                    "TRACE_ALLOW_PAID_LIVE": "1",
                },
                capture_output=True,
                text=True,
                timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("/private", result.stdout + result.stderr)
            self.assertTrue(json.loads(result.stdout)["evidence"]["records"])
