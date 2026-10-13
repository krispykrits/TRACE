"""Tests for fail-closed discovery of the opt-in provider gate."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.run_live_provider_checks import discover_live_provider_suite, main


class LiveProviderGateTests(unittest.TestCase):
    def test_no_paid_call_or_discovery_without_explicit_opt_in(self) -> None:
        with (
            patch.dict("os.environ", {}, clear=True),
            patch(
                "scripts.run_live_provider_checks.discover_live_provider_suite"
            ) as discover,
        ):
            self.assertEqual(main(), 2)
            discover.assert_not_called()

    def test_skipped_live_test_does_not_count_as_verified(self) -> None:
        suite = unittest.TestSuite()
        result = unittest.TestResult()
        result.skipped.append(
            (unittest.FunctionTestCase(lambda: None), "not configured")
        )
        with (
            patch.dict("os.environ", {"TRACE_ALLOW_PAID_LIVE": "1"}),
            patch(
                "scripts.run_live_provider_checks.discover_live_provider_suite",
                return_value=suite,
            ),
            patch("unittest.TextTestRunner.run", return_value=result),
        ):
            self.assertEqual(main(), 2)

    def test_missing_directory_is_not_a_verified_empty_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            test_directory = Path(directory) / "missing"

            self.assertIsNone(discover_live_provider_suite(test_directory))

    def test_empty_directory_is_not_a_verified_empty_gate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            test_directory = Path(directory) / "live_provider"
            test_directory.mkdir()

            self.assertIsNone(discover_live_provider_suite(test_directory))

    def test_suite_with_tests_is_discovered(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            test_directory = Path(directory)
            (test_directory / "test_example.py").write_text(
                "import unittest\n"
                "class Example(unittest.TestCase):\n"
                "    def test_check_is_present(self):\n"
                "        self.assertTrue(True)\n",
                encoding="utf-8",
            )

            suite = discover_live_provider_suite(test_directory)

            self.assertIsNotNone(suite)
            assert suite is not None
            self.assertEqual(suite.countTestCases(), 1)


if __name__ == "__main__":
    unittest.main()
