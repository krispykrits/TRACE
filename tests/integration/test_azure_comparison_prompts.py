"""Exercise candidate comparison prompts in isolated offline child compositions."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from evaluation.local_mvp import DECISIONS
from evaluation.local_mvp_comparison import execution_policy
from scripts.azure_comparison_prompts import (
    BRIEF_PROMPT,
    BRIEF_PROMPT_ID,
    COMMON_BRIEF,
    INTEGRATED_PROMPT,
    INTEGRATED_PROMPT_ID,
)
from trace_app.knowledge.models import digest

ROOT = Path(__file__).resolve().parents[2]
CHILD = """
import json, sys
from pathlib import Path
from unittest.mock import patch
from scripts import investigator_suite, local_mvp_reference
from scripts.azure_comparison_prompts import (
    BRIEF_PROMPT, BRIEF_PROMPT_ID, COMMON_BRIEF, INTEGRATED_PROMPT,
    INTEGRATED_PROMPT_ID,
)
from trace_app.investigation.execution import ExecutionPolicy
root = Path(sys.argv[1])
policy = json.loads((root / 'policy.json').read_text())
assert COMMON_BRIEF == investigator_suite.COMPARISON_SYMPTOM
with (patch.object(investigator_suite, 'COMPARISON_PROMPT_ID', INTEGRATED_PROMPT_ID),
      patch.object(investigator_suite, 'COMPARISON_PROMPT', INTEGRATED_PROMPT)):
    investigator_suite.execute(root / 'integrated', 'c01', 'none', policy=policy, reviewed=False)
with (patch.object(local_mvp_reference, 'PROMPT_ID', BRIEF_PROMPT_ID),
      patch.object(local_mvp_reference, 'PROMPT', BRIEF_PROMPT)):
    local_mvp_reference.execute(root / 'brief', 'c01', 'llm_only', ExecutionPolicy(**policy))
"""


class AzureComparisonPromptTests(unittest.TestCase):
    def test_candidate_prompts_work_in_offline_arm_compositions(self) -> None:
        # Deterministic models test composition, not real-model quality.
        self.assertNotEqual(BRIEF_PROMPT_ID, INTEGRATED_PROMPT_ID)
        self.assertNotEqual(
            digest(BRIEF_PROMPT.instructions), digest(INTEGRATED_PROMPT.instructions)
        )
        self.assertIn(COMMON_BRIEF, BRIEF_PROMPT.instructions)
        self.assertIn(COMMON_BRIEF, INTEGRATED_PROMPT.instructions)
        policy = execution_policy(json.loads(DECISIONS.read_text()))
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "policy.json").write_text(json.dumps(asdict(policy)))
            process = subprocess.run(
                [sys.executable, "-c", CHILD, str(root)],
                cwd=ROOT,
                env={
                    "PATH": os.environ.get("PATH", os.defpath),
                    "OPENBLAS_NUM_THREADS": "1",
                },
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            self.assertEqual(process.returncode, 0, process.stderr[-2000:])
            integrated = json.loads((root / "integrated/execution.json").read_text())
            brief = json.loads((root / "brief/execution.json").read_text())
            self.assertEqual(integrated["prompt_version"], INTEGRATED_PROMPT_ID)
            self.assertEqual(
                integrated["prompt_sha256"], digest(INTEGRATED_PROMPT.instructions)
            )
            self.assertEqual(integrated["actual_provider_calls"], 0)
            self.assertEqual(integrated["evaluation_modules_loaded"], [])
            self.assertEqual(integrated["jobs"][0]["execution_status"], "completed")
            self.assertEqual(brief["prompt_version"], BRIEF_PROMPT_ID)
            self.assertEqual(brief["prompt_sha256"], digest(BRIEF_PROMPT.instructions))
            self.assertEqual(brief["actual_provider_calls"], 0)
            self.assertEqual(brief["evaluation_modules_loaded"], [])
            self.assertEqual(brief["jobs"][0]["execution_status"], "completed")
            self.assertFalse(any(call["kind"] == "tool" for call in brief["calls"]))


if __name__ == "__main__":
    unittest.main()
