"""Architecture rules reject regressions even when an import is never executed."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.check_architecture import collect_violations


class ArchitectureTests(unittest.TestCase):
    def test_repository_boundaries(self) -> None:
        root = Path(__file__).resolve().parents[2] / "src/trace_app"
        self.assertEqual(collect_violations(root), [])

    def test_forbidden_dependencies_include_relative_guarded_and_dynamic_imports(
        self,
    ) -> None:
        examples = {
            "knowledge/service.py": [
                "from trace_app.adapters.storage import sqlite",
                "from ..adapters import storage",
                "from trace_app import adapters",
                "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n import numpy",
                "import evaluation.scoring",
                "__import__('evaluation.scoring')",
                "from importlib import import_module as load\nload('evaluation.scoring')",
                "import importlib\nimportlib.import_module(selected)",
            ],
            "adapters/store.py": [
                "from trace_app.bootstrap import create_search_service"
            ],
            "cli/commands.py": ["from trace_app.adapters.storage import sqlite"],
            "runtime/settings.py": ["import sklearn"],
            "demo/replay.py": ["import evaluation"],
            "new_feature.py": ["import os"],
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for filename, sources in examples.items():
                path = root / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                for source in sources:
                    with self.subTest(filename=filename, source=source):
                        path.write_text(source)
                        self.assertTrue(collect_violations(root))
                path.unlink()

    def test_core_ports_and_composition_imports_are_allowed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            files = {
                "knowledge/service.py": "from .ports import Encoder\nfrom trace_app.evidence.models import EvidenceRecord",
                "bootstrap.py": "from trace_app.adapters.retrieval.exact_scoring import LocalExactScorer",
                "cli/commands.py": "from trace_app.bootstrap import create_search_service",
            }
            for filename, source in files.items():
                path = root / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(source)
            self.assertEqual(collect_violations(root), [])
