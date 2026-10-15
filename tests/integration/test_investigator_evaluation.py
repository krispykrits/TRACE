"""Actual development CLI matrix, private artifact regeneration and evaluator isolation."""

from __future__ import annotations

import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

from evaluation.investigator import ROOT, _json, _load, rescore, review, run


class InvestigatorEvaluationTests(unittest.TestCase):
    temporary: tempfile.TemporaryDirectory[str]
    directory: Path
    scores: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.temporary = tempfile.TemporaryDirectory(
            prefix="trace-investigator-evaluation-"
        )
        cls.directory = Path(cls.temporary.name) / "run"
        cls.scores = run(cls.directory)

    @classmethod
    def tearDownClass(cls) -> None:
        cls.temporary.cleanup()

    def test_all_planned_outputs_and_failures_are_accounted_for(self) -> None:
        scores = self.scores
        self.assertEqual(scores["mode"], "offline_fixture")
        self.assertEqual(scores["summary"]["attempted"], 10)
        self.assertEqual(
            scores["summary"]["contract_results"], {"passed": 10, "attempted": 10}
        )
        self.assertEqual(scores["summary"]["critical_boundary_failures"], [])
        self.assertEqual(scores["summary"]["execution_counts"]["failed"], 5)
        self.assertEqual(scores["summary"]["malformed_rejections"], 1)
        self.assertEqual(scores["summary"]["citation_rejections"], 1)
        self.assertEqual(
            scores["summary"]["cause_accuracy"],
            {"numerator": 0, "denominator": 8, "value": 0.0},
        )
        self.assertEqual(
            scores["summary"]["abstention_contract_accuracy"]["numerator"], 2
        )
        self.assertEqual(
            scores["summary"]["human_unsupported_claim_rate"]["denominator"], 0
        )
        self.assertEqual(scores["actual_human_review_decisions"], 0)
        self.assertEqual(scores["actual_provider_calls"], 0)
        self.assertEqual(
            scores["gate"]["diagnostic_quality"], "not_accepted_offline_provider"
        )
        self.assertEqual(scores["cohorts"]["development_incident"]["attempted"], 4)
        self.assertEqual(scores["cohorts"]["boundary_check"]["attempted"], 6)
        cases = {row["attempt_id"]: row for row in scores["attempts"]}
        self.assertIsNone(cases["b02"]["usage"]["tokens"])
        self.assertIsNone(cases["b02"]["usage"]["estimated_cost_usd"])
        for path in self.directory.rglob("*.json"):
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.directory.stat().st_mode & 0o777, 0o700)

    def test_rescoring_is_byte_identical_and_never_dispatches(self) -> None:
        with patch(
            "evaluation.investigator.subprocess.run",
            side_effect=AssertionError(
                "Rescoring cannot execute a provider or command"
            ),
        ):
            self.assertEqual(
                _json(rescore(self.directory)),
                (self.directory / "scores.json").read_bytes(),
            )
        process = subprocess.run(
            [
                sys.executable,
                "-m",
                "evaluation.investigator",
                "rescore",
                "--run-dir",
                str(self.directory),
            ],
            cwd=ROOT,
            env={"PATH": os.environ.get("PATH", os.defpath)},
            capture_output=True,
            text=True,
            timeout=15,
        )
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(
            process.stdout.encode(), (self.directory / "scores.json").read_bytes()
        )
        self.assertNotIn("synthetic_mechanism", process.stderr)

    def test_reviews_create_new_scores_and_preserve_immutable_originals(self) -> None:
        original = (self.directory / "scores.json").read_bytes()
        sample = json.loads((self.directory / "support_sample.json").read_text())
        envelope = json.loads((self.directory / "human_reviews.json").read_text())
        # Synthetic contract records exercise review parsing/disagreement only.
        envelope["reviews"] = [
            {
                "binding_id": sample[0]["binding_id"],
                "reviewer_id": "unit-fixture-a",
                "kind": "human_review",
                "verdict": "supported",
                "rationale": "Synthetic test record, not actual human endorsement.",
            },
            {
                "binding_id": sample[0]["binding_id"],
                "reviewer_id": "unit-fixture-b",
                "kind": "human_review",
                "verdict": "unsupported",
                "rationale": "Synthetic disagreement test, not actual human endorsement.",
            },
        ]
        review_path = Path(self.temporary.name) / "fixture-review.json"
        review_path.write_text(json.dumps(envelope))
        destination = Path(self.temporary.name) / "fixture-review-scores.json"
        with patch(
            "evaluation.investigator.subprocess.run",
            side_effect=AssertionError("No dispatch"),
        ):
            result = review(self.directory, review_path, destination)
        self.assertEqual(result["summary"]["reviewer_disagreements"], 1)
        self.assertEqual(destination.stat().st_mode & 0o777, 0o600)
        self.assertEqual((self.directory / "scores.json").read_bytes(), original)
        self.assertEqual(self.scores["actual_human_review_decisions"], 0)

    def test_modified_missing_traversal_and_symlink_artifacts_are_denied(self) -> None:
        with tempfile.TemporaryDirectory(
            prefix="trace-evaluation-tamper-"
        ) as temporary:
            copy = Path(temporary) / "copy"
            shutil.copytree(self.directory, copy)
            result_path = copy / "artifacts/d01/result.json"
            original = result_path.read_bytes()
            result_path.write_bytes(original + b" ")
            with self.assertRaises(ValueError):
                rescore(copy)
            result_path.write_bytes(original)
            result_path.unlink()
            with self.assertRaises(OSError):
                rescore(copy)
            result_path.write_bytes(original)
            manifest_path = copy / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["artifact_sha256"]["../../private.json"] = "0" * 64
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                rescore(copy)
            manifest_path.write_bytes((self.directory / "manifest.json").read_bytes())
            shutil.rmtree(copy / "artifacts/d01")
            (copy / "artifacts/d01").symlink_to(
                self.directory / "artifacts/d01", target_is_directory=True
            )
            with self.assertRaises(ValueError):
                rescore(copy)

    def test_child_inputs_have_no_evaluator_labels_or_held_out_material(self) -> None:
        files = _load(self.directory)
        self.assertEqual(
            files["protocol.json"]["final_test"], "reserved_not_generated_or_accessed"
        )
        for case in files["protocol.json"]["cases"]:
            execution = files[f"artifacts/{case['id']}/execution.json"]
            self.assertEqual(execution["evaluation_modules_loaded"], [])
            self.assertFalse(execution["authority_changed"])
            self.assertEqual(execution["actual_provider_calls"], 0)
            for request in execution["request_metadata"]:
                self.assertTrue(request["untrusted_instructions_present"])
        tree = ast.parse((ROOT / "scripts/investigator_suite.py").read_text())
        imports = [
            node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
        ]
        self.assertFalse(
            any(name and name.startswith("evaluation") for name in imports)
        )

    def test_live_mode_and_existing_outputs_are_not_silently_replaced(self) -> None:
        with self.assertRaises(ValueError):
            run(self.directory, mode="live")
        with self.assertRaises(FileExistsError):
            run(self.directory)


class InvestigatorCaptureFailureTests(unittest.TestCase):
    def test_failed_children_all_remain_in_the_score_denominator(self) -> None:
        original = subprocess.run

        def fail_child(command, *args, **kwargs):
            if command[0] == sys.executable:
                return subprocess.CompletedProcess(
                    command, 9, stdout=b"", stderr=b"opaque child error"
                )
            return original(command, *args, **kwargs)

        with (
            tempfile.TemporaryDirectory(prefix="trace-missing-captures-") as temporary,
            patch("evaluation.investigator.subprocess.run", side_effect=fail_child),
        ):
            scores = run(Path(temporary) / "failed")
        self.assertEqual(scores["summary"]["attempted"], 10)
        self.assertEqual(scores["summary"]["output_missing"], 10)
        self.assertEqual(scores["summary"]["execution_counts"]["failed"], 10)
        self.assertEqual(scores["gate"]["offline_contract"], "failed")
