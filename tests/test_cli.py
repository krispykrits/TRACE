"""Smoke tests for the installed TRACE command."""

from __future__ import annotations

import contextlib
import io
import unittest

from trace_app.cli import main


class CliSmokeTests(unittest.TestCase):
    def test_default_invocation_prints_help_and_exits_successfully(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main([])

        self.assertEqual(result, 0)
        self.assertIn("TRACE incident investigation scaffold.", output.getvalue())
        self.assertIn("--version", output.getvalue())

    def test_version_option_prints_package_version(self) -> None:
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as raised:
            main(["--version"])

        self.assertEqual(raised.exception.code, 0)
        self.assertIn("trace-app 0.1.0", output.getvalue())


if __name__ == "__main__":
    unittest.main()
