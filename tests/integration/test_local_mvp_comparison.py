"""Comparison process isolation, complete denominators and immutable rescoring."""

from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evaluation.local_mvp import plan
from evaluation.local_mvp_comparison import main, rescore, run, schedule_rows, score
from evaluation.runner import _json, _parse, _read


class LocalMVPComparisonTests(unittest.TestCase):
    def test_declared_schedule_has_rotated_paired_repeats(self) -> None:
        rows = schedule_rows(plan())
        self.assertEqual(len(rows), 36)
        self.assertEqual(len({row["id"] for row in rows}), 36)
        for repeat in range(1, 4):
            for case in ("c01", "c02", "c03", "c04"):
                self.assertEqual(
                    {
                        r["arm"]
                        for r in rows
                        if r["repeat"] == repeat and r["case_id"] == case
                    },
                    {"llm_only", "evidence_bundle", "rag_tools"},
                )

    def test_real_process_arms_and_model_free_tamper_resistant_rescore(self) -> None:
        planning = plan()
        planning["schedule"] = planning["schedule"][:3]
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("evaluation.local_mvp_comparison.plan", return_value=planning),
        ):
            output = Path(directory) / "run"
            result = run(output)
            self.assertEqual(result["scheduled"], 3)
            self.assertEqual(result["actual_provider_calls"], 0)
            self.assertEqual(
                result["arms"]["evidence_bundle"]["diagnostic_metrics"],
                "not_applicable",
            )
            self.assertEqual(result["arms"]["evidence_bundle"]["completed"], 1)
            self.assertEqual(result["arms"]["rag_tools"]["attempted"], 1)
            self.assertEqual(result["arms"]["llm_only"]["attempted"], 1)
            self.assertTrue(result["live_diagnostics"]["blockers"])
            with (
                patch(
                    "subprocess.run",
                    side_effect=AssertionError("Rescore dispatch forbidden"),
                ),
                patch("socket.socket", side_effect=AssertionError("Network forbidden")),
            ):
                self.assertEqual(rescore(output), result)
            manifest = _parse(_read(output / "manifest.json"))
            self.assertIsInstance(manifest, dict)
            self.assertEqual(output.stat().st_mode & 0o777, 0o700)
            self.assertTrue(
                all(p.stat().st_mode & 0o777 == 0o600 for p in output.rglob("*.json"))
            )
            original = (output / "scores.json").read_bytes()
            (output / "scores.json").write_bytes(original + b" ")
            with self.assertRaises(ValueError):
                rescore(output)
            (output / "scores.json").write_bytes(original)
            artifact = output / "artifacts/a001/result.json"
            artifact.unlink()
            with self.assertRaises(OSError):
                rescore(output)

    def test_all_process_failures_keep_all_scheduled_denominators(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("subprocess.run") as process,
        ):
            process.return_value.returncode = 1
            output = Path(directory) / "failed"
            result = run(output)
            self.assertEqual(result["scheduled"], 36)
            self.assertEqual(result["arms"]["rag_tools"]["attempted"], 12)
            self.assertEqual(
                result["arms"]["rag_tools"]["execution_counts"]["failed"], 12
            )
            self.assertEqual(
                result["arms"]["llm_only"]["execution_counts"]["failed"], 12
            )
            self.assertEqual(result["arms"]["evidence_bundle"]["completed"], 0)
            self.assertEqual(len(result["attempts"]), 36)
            self.assertEqual(rescore(output), result)
            manifest = _parse(_read(output / "manifest.json"))
            assert isinstance(manifest, dict)
            del manifest["artifact_sha256"]["artifacts/a001/result.json"]
            (output / "manifest.json").write_bytes(_json(manifest))
            with self.assertRaises(ValueError):
                rescore(output)

    def test_live_is_blocked_before_any_process_or_output(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("subprocess.run", side_effect=AssertionError("No dispatch")),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            output = Path(directory) / "live"
            self.assertEqual(
                main(["run", "--mode", "live", "--output", str(output)]), 2
            )
            self.assertFalse(output.exists())

    def test_altered_source_pair_cannot_supply_comparison(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("subprocess.run") as process,
        ):
            process.return_value.returncode = 1
            output = Path(directory) / "run"
            run(output)
            files = {
                p.relative_to(output).as_posix(): _parse(_read(p))
                for p in output.rglob("*.json")
                if p.name != "manifest.json"
            }
            observed = files["artifacts/a002/observed.json"]
            assert isinstance(observed, dict)
            observed["sources"][0]["reason"] = "changed"
            with self.assertRaises(ValueError):
                score(files)
