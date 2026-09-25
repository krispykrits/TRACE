"""Offline integration checks for TRACE's real CLI process boundary."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def _minimal_environment() -> dict[str, str]:
    """Keep inherited credentials and developer settings out of the child."""
    environment = {"PATH": os.environ.get("PATH", os.defpath)}
    for name in ("SYSTEMROOT", "WINDIR"):
        if value := os.environ.get(name):
            environment[name] = value
    return environment


def _run_check_config(env_file: Path, working_directory: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "trace_app.cli",
            "check-config",
            "--env-file",
            str(env_file),
        ],
        cwd=working_directory,
        env=_minimal_environment(),
        capture_output=True,
        check=False,
        text=True,
        timeout=15,
    )


class CliProcessIntegrationTests(unittest.TestCase):
    def test_two_consecutive_runs_are_isolated_and_successful(self) -> None:
        for expected_environment in ("development", "test"):
            with self.subTest(environment=expected_environment):
                with tempfile.TemporaryDirectory(prefix="trace-integration-") as directory:
                    working_directory = Path(directory)
                    env_file = working_directory / "settings.env"
                    env_file.write_text(
                        f"TRACE_ENVIRONMENT={expected_environment}\n",
                        encoding="utf-8",
                    )

                    result = _run_check_config(env_file, working_directory)

                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, "")
                    record = json.loads(result.stderr)
                    self.assertEqual(record["event"], "configuration.validated")
                    self.assertEqual(record["environment"], expected_environment)
                    self.assertTrue(record["correlation_id"])

    def test_fixture_is_removed_after_cli_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="trace-integration-") as directory:
            working_directory = Path(directory)
            env_file = working_directory / "settings.env"
            env_file.write_text(
                "TRACE_ENVIRONMENT=invalid-fixture-value\n",
                encoding="utf-8",
            )

            result = _run_check_config(env_file, working_directory)

            self.assertEqual(result.returncode, 2)
            self.assertNotIn("invalid-fixture-value", result.stderr)
            record = json.loads(result.stderr)
            self.assertEqual(record["event"], "configuration.invalid")
            self.assertIn("TRACE_ENVIRONMENT", record["error"])

        self.assertFalse(working_directory.exists())
        self.assertFalse(env_file.exists())


if __name__ == "__main__":
    unittest.main()
