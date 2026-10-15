"""Construction failures have fixed, content-free CLI outcomes before dispatch."""

import argparse
import contextlib
import io
import unittest
from unittest.mock import patch

from trace_app.cli.investigator import run
from trace_app.investigation.provider import ModelErrorCode, ModelProviderError


class InvestigatorCliFailureTests(unittest.TestCase):
    def test_provider_setup_dependency_denial_and_timeout_are_distinct(self) -> None:
        for error, expected in (
            (ModelErrorCode.CONFIGURATION, 2),
            (ModelErrorCode.DEPENDENCY, 3),
            (ModelErrorCode.POLICY, 4),
            (ModelErrorCode.TIMEOUT, 5),
        ):
            output = io.StringIO()
            with (
                self.subTest(error=error),
                patch.dict(
                    "os.environ",
                    {"TRACE_INVESTIGATOR_PROFILE": "/private/profile.json"},
                ),
                patch(
                    "trace_app.cli.investigator.create_local_investigator",
                    side_effect=ModelProviderError(error),
                ),
                contextlib.redirect_stdout(output),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                self.assertEqual(
                    run(
                        argparse.Namespace(
                            command="report",
                            output=None,
                            format="json",
                            investigation_id="investigation",
                        )
                    ),
                    expected,
                )
                self.assertEqual(output.getvalue(), "")
