"""Smoke tests for the installed TRACE command."""

from __future__ import annotations

import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from trace_app.cli import main


class CliSmokeTests(unittest.TestCase):
    def test_default_invocation_prints_help_and_exits_successfully(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main([])

        self.assertEqual(result, 0)
        self.assertIn("TRACE incident investigation scaffold.", output.getvalue())
        self.assertIn("--version", output.getvalue())

    def test_console_entry_point_reads_version_option(self) -> None:
        output = io.StringIO()
        with (
            patch("sys.argv", ["trace-app", "--version"]),
            contextlib.redirect_stdout(output),
            self.assertRaises(SystemExit) as raised,
        ):
            main()

        self.assertEqual(raised.exception.code, 0)
        self.assertIn("trace-app 0.1.0", output.getvalue())

    def test_check_config_emits_parseable_success_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text("TRACE_ENVIRONMENT=production\n", encoding="utf-8")
            output = io.StringIO()
            with (
                patch.dict(os.environ, {}, clear=True),
                contextlib.redirect_stderr(output),
            ):
                result = main(
                    [
                        "check-config",
                        "--env-file",
                        str(env_file),
                        "--environment",
                        "test",
                        "--log-level",
                        "INFO",
                    ]
                )

        self.assertEqual(result, 0)
        record = json.loads(output.getvalue())
        self.assertEqual(record["event"], "configuration.validated")
        self.assertEqual(record["environment"], "test")
        self.assertEqual(record["component"], "configuration")
        self.assertTrue(record["correlation_id"])
        self.assertEqual(record["application_version"], "0.1.0")
        self.assertIn("timestamp", record)

    def test_check_config_redacts_secret_from_failure_log(self) -> None:
        secret_fixture = "cli-provider-secret-456"
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text("", encoding="utf-8")
            output = io.StringIO()
            with (
                patch.dict(
                    os.environ, {"TRACE_PROVIDER_API_KEY": secret_fixture}, clear=True
                ),
                contextlib.redirect_stderr(output),
            ):
                result = main(
                    [
                        "check-config",
                        "--env-file",
                        str(env_file),
                        "--environment",
                        "development",
                    ]
                )

        self.assertEqual(result, 2)
        self.assertNotIn(secret_fixture, output.getvalue())
        record = json.loads(output.getvalue())
        self.assertEqual(record["event"], "configuration.invalid")
        self.assertEqual(record["level"], "ERROR")
        self.assertIn("TRACE_PROVIDER_API_KEY", record["error"])


if __name__ == "__main__":
    unittest.main()
