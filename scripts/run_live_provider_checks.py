"""Run opt-in provider checks and reject an absent or empty suite."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


def discover_live_provider_suite(test_directory: Path) -> unittest.TestSuite | None:
    """Return discovered live tests, or None when the gate has no tests to run."""
    if not test_directory.is_dir():
        return None
    suite = unittest.defaultTestLoader.discover(
        start_dir=str(test_directory),
        pattern="test_*.py",
        top_level_dir=str(test_directory),
    )
    return suite if suite.countTestCases() else None


def main() -> int:
    """Run tests/live_provider and fail closed until it contains real tests."""
    test_directory = Path(__file__).resolve().parents[1] / "tests" / "live_provider"
    suite = discover_live_provider_suite(test_directory)
    if suite is None:
        if test_directory.is_dir():
            reason = "No live provider tests were discovered"
        else:
            reason = "No live provider checks are configured"
        print(
            f"{reason} under tests/live_provider; "
            "this gate cannot be reported as verified.",
            file=sys.stderr,
        )
        return 2

    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
