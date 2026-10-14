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
            "adapters/tools/worker.py": [
                "import evaluation.scoring",
                "from trace_app.cli import main",
                "from trace_app.bootstrap import create_tool_session",
            ],
            "investigation/tools.py": [
                "from trace_app.adapters.tools.local import LocalToolBackend",
                "from trace_app.demo.replay import ReplaySession",
            ],
            "investigation/bundle.py": [
                "import evaluation.tool_evaluation",
                "from scripts.demo_integration import integration_fixture",
                "from trace_app.adapters.tools.local import LocalToolBackend",
            ],
            "investigation/provider.py": [
                "from trace_app.adapters.models.process import ProcessModelProvider",
                "from tests.fixtures.model_provider import FakeModelTransport",
                "import openai",
            ],
            "investigation/provider_policy.py": [
                "import http.client",
                "from urllib.request import urlopen",
                "from trace_app.adapters.models.azure import AzureResponsesTransport",
                "from evaluation.scoring import evaluate",
            ],
            "investigation/assessment_validation.py": [
                "from evaluation.scoring import SupportReview",
                "from tests.fixtures.assessments import Reviews",
                "from trace_app.adapters.storage.sqlite.corpus import SQLiteCorpusStore",
            ],
            "investigation/execution.py": [
                "from trace_app.adapters.storage.sqlite.execution import SqliteExecutionLedger",
                "from evaluation.scoring import evaluate",
                "from tests.fixtures.execution import MemoryLedger",
            ],
            "adapters/models/provider.py": [
                "from trace_app.investigation.execution import ExecutionSession",
                "from trace_app.investigation.assessment_validation import AssessmentValidator",
                "from trace_app.investigation.tools import ToolSession",
                "from trace_app.adapters.tools.local import LocalToolBackend",
                "from trace_app.adapters.storage.sqlite import investigations",
                "from trace_app.knowledge.ports import CorpusReader",
                "from trace_app.bootstrap import create_search_service",
                "from tests.fixtures.model_provider import FakeModelTransport",
            ],
            "cli/commands.py": [
                "from trace_app.adapters.storage import sqlite",
                "import http.client",
            ],
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
                "adapters/models/process.py": "from trace_app.investigation.provider import ModelRequest\nfrom trace_app.runtime.logging import configure_logging",
                "adapters/models/journal.py": "from trace_app.investigation.provider_policy import Redaction",
                "adapters/models/azure.py": "import http.client\nimport ssl",
            }
            for filename, source in files.items():
                path = root / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(source)
            self.assertEqual(collect_violations(root), [])
