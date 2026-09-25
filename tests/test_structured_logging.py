"""Deterministic tests for structured logging and redaction."""

from __future__ import annotations

import io
import json
import logging
import unittest
from datetime import datetime

from trace_app.structured_logging import configure_logging


class StructuredLoggingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.output = io.StringIO()
        self.correlation_id = configure_logging(
            level="INFO",
            secret_values=("fixture-secret-123",),
            stream=self.output,
            correlation_id="investigation-42",
        )

    def tearDown(self) -> None:
        logging.getLogger("trace_app").handlers.clear()

    def test_emits_parseable_correlated_json_with_required_fields(self) -> None:
        logging.getLogger("trace_app.evidence").info(
            "Evidence query completed.",
            extra={
                "event": "evidence.query.completed",
                "tool_attempt_id": "tool-attempt-7",
                "source_version": "fixture-v1",
            },
        )

        record = json.loads(self.output.getvalue())
        self.assertEqual(record["level"], "INFO")
        self.assertEqual(record["component"], "evidence")
        self.assertEqual(record["correlation_id"], self.correlation_id)
        self.assertEqual(record["event"], "evidence.query.completed")
        self.assertEqual(record["tool_attempt_id"], "tool-attempt-7")
        self.assertEqual(record["source_version"], "fixture-v1")
        datetime.fromisoformat(record["timestamp"].replace("Z", "+00:00"))

    def test_redacts_secret_fields_values_and_exception_text(self) -> None:
        logger = logging.getLogger("trace_app.provider")
        try:
            raise RuntimeError("provider rejected fixture-secret-123")
        except RuntimeError:
            logger.exception(
                "Request failed for fixture-secret-123",
                extra={
                    "authorization": "Bearer fixture-secret-123",
                    "nested": {"api_key": "fixture-secret-123"},
                },
            )

        output = self.output.getvalue()
        self.assertNotIn("fixture-secret-123", output)
        record = json.loads(output)
        self.assertIn("[REDACTED]", record["message"])
        self.assertEqual(record["authorization"], "[REDACTED]")
        self.assertEqual(record["nested"]["api_key"], "[REDACTED]")
        self.assertIn("[REDACTED]", record["exception"])


if __name__ == "__main__":
    unittest.main()
