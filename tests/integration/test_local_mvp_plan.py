"""Private dry-run artifacts, no dispatch and immutable planning inputs."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evaluation.local_mvp import DECISIONS, PROTOCOL, main
from evaluation.runner import _read, _sha


class LocalMVPPlanTests(unittest.TestCase):
    def test_draft_creates_bound_private_artifacts_without_dispatch(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            patch("socket.socket", side_effect=AssertionError("No network")),
            patch("subprocess.run", side_effect=AssertionError("No child or provider")),
            contextlib.redirect_stdout(io.StringIO()) as stdout,
        ):
            output = Path(directory) / "plan"
            self.assertEqual(main(["--output", str(output)]), 1)
            manifest = json.loads((output / "manifest.json").read_bytes())
            self.assertEqual(manifest, json.loads(stdout.getvalue()))
            self.assertEqual(
                (output / "protocol.json").read_bytes(), PROTOCOL.read_bytes()
            )
            self.assertEqual(
                (output / "decisions.json").read_bytes(), DECISIONS.read_bytes()
            )
            self.assertEqual(
                _sha((output / "protocol.json").read_bytes()),
                manifest["binding"]["protocol_sha256"],
            )
            self.assertEqual(output.stat().st_mode & 0o777, 0o700)
            self.assertTrue(
                all(p.stat().st_mode & 0o777 == 0o600 for p in output.iterdir())
            )
            self.assertIsNone(manifest["measured_usage"])
            self.assertEqual(manifest["local_mvp_release"], "not_assessed")
            self.assertFalse(
                any("final_test" in name for name in manifest["source_sha256"])
            )

    def test_existing_output_and_symlink_inputs_are_not_overwritten(self) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            output = Path(directory) / "plan"
            self.assertEqual(main(["--output", str(output)]), 1)
            original = (output / "manifest.json").read_bytes()
            self.assertEqual(main(["--output", str(output)]), 2)
            self.assertEqual((output / "manifest.json").read_bytes(), original)
            symlink = Path(directory) / "decisions.json"
            symlink.symlink_to(DECISIONS)
            fresh = Path(directory) / "fresh"
            self.assertEqual(
                main(["--decisions", str(symlink), "--output", str(fresh)]), 2
            )
            self.assertFalse(fresh.exists())

    def test_duplicate_keys_nonfinite_or_unknown_inputs_fail_before_output(
        self,
    ) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()) as stderr,
        ):
            path = Path(directory) / "invalid.json"
            for data in (
                '{"repeats":1,"repeats":2}',
                '{"repeats":NaN}',
                '{"unknown":"secret-value-must-not-appear"}',
            ):
                path.write_text(data)
                output = Path(directory) / "output"
                self.assertEqual(
                    main(["--decisions", str(path), "--output", str(output)]), 2
                )
                self.assertFalse(output.exists())
            self.assertNotIn("secret-value-must-not-appear", stderr.getvalue())

    def test_inputs_changed_during_planning_cannot_publish_a_mismatched_snapshot(
        self,
    ) -> None:
        with (
            tempfile.TemporaryDirectory() as directory,
            contextlib.redirect_stdout(io.StringIO()),
            contextlib.redirect_stderr(io.StringIO()),
        ):
            decisions = Path(directory) / "decisions.json"
            decisions.write_bytes(DECISIONS.read_bytes())
            output = Path(directory) / "plan"
            reads = 0

            def changed(path: Path) -> bytes:
                nonlocal reads
                data = _read(path)
                if path == decisions:
                    reads += 1
                    return data + b" " if reads > 1 else data
                return data

            with patch("evaluation.local_mvp._read", side_effect=changed):
                self.assertEqual(
                    main(["--decisions", str(decisions), "--output", str(output)]), 2
                )
            self.assertFalse(output.exists())
