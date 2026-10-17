"""Canary disclosure/isolation and fresh dispatch rights using real local storage."""

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.demo_integration import integration_fixture
from scripts.demo_investigator import compose
from scripts.local_security_fixture import HIDDEN, MODES, REMOVED
from trace_app.adapters.tools.local import LocalToolBackend
from trace_app.investigation.workflow import WorkflowOptions

ROOT = Path(__file__).resolve().parents[2]


class CanaryHarnessControlTests(unittest.TestCase):
    def test_caught_tool_leak_still_fails_the_security_probe(self) -> None:
        # Negative control: inject a canary at the backend-result observation
        # boundary. Normal application error handling withholds the result, but
        # that must not erase the fact that this boundary was violated.
        with tempfile.TemporaryDirectory() as temporary:
            code = (
                "import sys; from pathlib import Path; from unittest.mock import patch; "
                "from scripts import local_security_fixture as probe; "
                "from trace_app.adapters.tools.local import LocalToolBackend; "
                "from trace_app.investigation.tools import ToolPayload; "
                "patcher=patch.object(LocalToolBackend,'execute',return_value=ToolPayload('ok',{'canary':probe.HIDDEN})); "
                "patcher.start(); "
                "probe.execute(Path(sys.argv[1]),'model_tool')"
            )
            process = subprocess.run(
                [sys.executable, "-c", code, str(Path(temporary) / "negative-control")],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=30,
                env={
                    "PATH": os.environ.get("PATH", os.defpath),
                    "OPENBLAS_NUM_THREADS": "1",
                },
            )
            self.assertNotEqual(process.returncode, 0)
            self.assertIn("Protected canary reached delivery or audit", process.stderr)
            self.assertNotIn(HIDDEN, process.stdout + process.stderr)


class LocalSecurityCanaryTests(unittest.TestCase):
    temporary: tempfile.TemporaryDirectory[str]
    root: Path

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(prefix="trace-local-security-")
        cls.root = Path(cls.temporary.name)
        for mode in MODES:
            process = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "scripts.local_security_fixture",
                    "--directory",
                    str(cls.root / mode),
                    "--mode",
                    mode,
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
            if process.returncode != 0:
                raise AssertionError((mode, process.returncode, process.stderr[-1500:]))
            if (
                HIDDEN in process.stdout + process.stderr
                or REMOVED in process.stdout + process.stderr
            ):
                raise AssertionError("Protected canary appeared on process output.")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def read(self, mode: str, name: str):
        return json.loads((self.root / mode / name).read_text())

    def test_evaluator_canaries_never_reach_tools_prompts_delivery_or_imports(
        self,
    ) -> None:
        for mode in MODES:
            with self.subTest(mode=mode):
                probes = self.read(mode, "security.json")
                execution = self.read(mode, "execution.json")
                self.assertEqual(probes["forbidden_opens"], 0)
                self.assertEqual(probes["forbidden_imports"], 0)
                self.assertEqual(probes["canary_violations"], 0)
                self.assertEqual(execution["evaluation_modules_loaded"], [])
                log_lines = [
                    line
                    for stream in probes["logs"]
                    for line in stream.splitlines()
                    if line
                ]
                self.assertTrue(log_lines)
                for line in log_lines:
                    event = json.loads(line)
                    self.assertTrue(event["correlation_id"])
                    self.assertTrue(event["event"])
                    self.assertNotIn("UNTRUSTED_ATTACK_v1", line)
                    self.assertNotIn(
                        "A synthetic downstream failure is a proposal", line
                    )

                self.assertEqual(execution["actual_provider_calls"], 0)
                self.assertFalse(execution["actual_human_review"])
                self.assertTrue(
                    all(
                        request["canaries_absent"]
                        for request in probes["model_requests"]
                    )
                )
                serialized = (
                    json.dumps(self.read(mode, "result.json"))
                    + json.dumps(execution)
                    + json.dumps(probes)
                )
                self.assertNotIn(HIDDEN, serialized)
                self.assertNotIn(REMOVED, serialized)

    def test_injection_does_not_supply_grants_tools_or_mutation_authority(self) -> None:
        execution = self.read("injection", "execution.json")
        probes = self.read("injection", "security.json")
        result = self.read("injection", "result.json")
        self.assertEqual(execution["model_invocations"], 1)
        self.assertTrue(probes["model_requests"][0]["attack_seen"])
        self.assertFalse(execution["authority_changed"])
        self.assertEqual(execution["execution_policies"][0]["max_tool_calls"], 40)
        self.assertEqual(result["validation_outcome"], "review_required")
        self.assertFalse(result["mutation_authority"])
        self.assertTrue(all(execution["guard_checks"].values()))
        self.assertLessEqual(
            sum(
                call["kind"] == "tool" and call["dispatched"]
                for call in execution["calls"]
            ),
            40,
        )
        allowed = {
            "logs.query",
            "metrics.query",
            "deployments.query",
            "evidence.get",
            "knowledge.search",
            "knowledge.resolve",
        }
        self.assertTrue(set(probes["tool_names"]) <= allowed)

    def test_redaction_keeps_citations_and_input_derived_sensitivity(self) -> None:
        result = self.read("redaction", "result.json")
        execution = self.read("redaction", "execution.json")
        self.assertEqual(execution["model_invocations"], 1)
        self.assertEqual(result["validation_outcome"], "review_required")
        self.assertEqual(result["sensitivity"], "restricted")
        self.assertTrue(result["citations"])
        self.assertTrue(
            any(view["redactions"] for view in result["citations"].values())
        )
        self.assertTrue(all(execution["guard_checks"].values()))
        for mode in MODES:
            directory = self.root / mode
            self.assertEqual(directory.stat().st_mode & 0o777, 0o700)
            for name in (
                "profile.json",
                "evidence.sqlite3",
                "corpus.sqlite3",
                "provider.sqlite3",
                "security.json",
            ):
                self.assertEqual((directory / name).stat().st_mode & 0o777, 0o600)
            with sqlite3.connect(directory / "provider.sqlite3") as db:
                audit = json.dumps(
                    db.execute("SELECT metadata FROM attempts").fetchall()
                )
                audit += json.dumps(
                    db.execute("SELECT provenance FROM redactions").fetchall()
                )
            self.assertNotIn(HIDDEN, audit)
            self.assertNotIn(REMOVED, audit)

    def test_hostile_errors_and_model_tool_proposals_fail_without_content(self) -> None:
        for mode in ("hostile_error", "model_tool"):
            with self.subTest(mode=mode):
                execution = self.read(mode, "execution.json")
                result = self.read(mode, "result.json")
                self.assertEqual(execution["jobs"][0]["execution_status"], "failed")
                self.assertFalse(result and result.get("report"))
                self.assertFalse(
                    any(
                        name.startswith(("shell", "sql", "write"))
                        for name in self.read(mode, "security.json")["tool_names"]
                    )
                )
        self.assertEqual(
            self.read("hostile_error", "execution.json")["model_invocations"], 0
        )


class LocalSecurityDispatchTests(unittest.TestCase):
    def test_refinement_and_correction_cannot_reuse_revoked_input_rights(self) -> None:
        # Existing larger demonstration policy isolates fresh authority checks;
        # this does not claim refinement/accepted publication fits 40 calls.
        for phase in ("refinement", "correction"):
            for permission in ("access", "transmission"):
                with (
                    self.subTest(phase=phase, permission=permission),
                    integration_fixture() as setup,
                ):
                    workflow, model, authority, _, _ = compose(
                        setup,
                        options=WorkflowOptions(
                            next_check=phase == "refinement",
                            correction=phase == "correction",
                        ),
                    )
                    self.addCleanup(workflow.close)
                    if phase == "correction":

                        def invalid(value, request):
                            value["observations"][0]["citations"] = [
                                "unadmitted-citation"
                            ]

                        model.transform = invalid
                    execute = LocalToolBackend.execute
                    revoked = []

                    def revoke(backend, call, *arguments, **keywords):
                        result = execute(backend, call, *arguments, **keywords)
                        trigger = (
                            "logs.query" if phase == "refinement" else "evidence.get"
                        )
                        if model.requests and call.name == trigger:
                            setattr(authority, permission, False)
                            revoked.append(True)
                        return result

                    with patch.object(LocalToolBackend, "execute", revoke):
                        result = workflow.run()
                    self.assertTrue(revoked)
                    self.assertEqual(len(model.requests), 1)
                    self.assertNotEqual(result.execution_status, "completed")
                    with sqlite3.connect(setup.root / "evidence.sqlite3") as db:
                        self.assertEqual(
                            db.execute(
                                "SELECT COUNT(*) FROM workflow_artifacts WHERE role IN ('accepted','review_required')"
                            ).fetchone()[0],
                            0,
                        )
