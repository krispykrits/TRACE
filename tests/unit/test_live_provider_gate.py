"""Tests for fail-closed discovery of the opt-in provider gate."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.run_live_provider_checks import discover_live_provider_suite


class LiveProviderGateTests(unittest.TestCase):
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
