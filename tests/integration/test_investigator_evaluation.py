"""Check that failed evaluation runs remain visible in results."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from evaluation.investigator import run


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
