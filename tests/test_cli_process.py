"""Offline integration checks for TRACE's real CLI process boundary."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def _minimal_environment() -> dict[str, str]:
    """Keep inherited credentials and developer settings out of the child."""
    environment = {"PATH": os.environ.get("PATH", os.defpath)}
    for name in ("SYSTEMROOT", "WINDIR"):
        if value := os.environ.get(name):
            environment[name] = value
    return environment


def _run_check_config(
    env_file: Path, working_directory: Path
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "trace_app.cli",
            "check-config",
            "--env-file",
            str(env_file),
        ],
        cwd=working_directory,
        env=_minimal_environment(),
        capture_output=True,
        check=False,
        text=True,
        timeout=15,
    )


def _run_demo_order(*arguments: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="trace-demo-") as directory:
        env_file = Path(directory) / "settings.env"
        env_file.write_text("", encoding="utf-8")
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "trace_app.cli",
                "demo-order",
                "--env-file",
                str(env_file),
                *arguments,
            ],
            cwd=directory,
            env=_minimal_environment(),
            capture_output=True,
            check=False,
            text=True,
            timeout=15,
        )


class CliProcessIntegrationTests(unittest.TestCase):
    def test_two_consecutive_runs_are_isolated_and_successful(self) -> None:
        for expected_environment in ("development", "test"):
            with self.subTest(environment=expected_environment):
                with tempfile.TemporaryDirectory(
                    prefix="trace-integration-"
                ) as directory:
                    working_directory = Path(directory)
                    env_file = working_directory / "settings.env"
                    env_file.write_text(
                        f"TRACE_ENVIRONMENT={expected_environment}\n",
                        encoding="utf-8",
                    )

                    result = _run_check_config(env_file, working_directory)

                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout, "")
                    record = json.loads(result.stderr)
                    self.assertEqual(record["event"], "configuration.validated")
                    self.assertEqual(record["environment"], expected_environment)
                    self.assertTrue(record["correlation_id"])

    def test_demo_order_traces_one_request_across_all_boundaries(self) -> None:
        result = _run_demo_order(
            "--environment",
            "test",
            "--order-id",
            "order-001",
            "--customer-id",
            "customer-001",
            "--amount-cents",
            "1250",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        outcome = json.loads(result.stdout)
        self.assertEqual(outcome["status"], "accepted")
        self.assertEqual(outcome["payment_authorization_id"], "auth-order-001")
        self.assertTrue(outcome["notification_recorded"])
        self.assertEqual(outcome["service"], "order")
        self.assertEqual(outcome["environment"], "test")
        records = [json.loads(line) for line in result.stderr.splitlines()]
        self.assertEqual(
            [record["event"] for record in records],
            [
                "order.requested",
                "customer.found",
                "payment.authorized",
                "notification.recorded",
                "order.accepted",
            ],
        )
        self.assertEqual(
            [record["service"] for record in records],
            ["order", "customer", "payment", "notification", "order"],
        )
        self.assertTrue(outcome["correlation_id"])
        self.assertEqual(
            {record["correlation_id"] for record in records},
            {outcome["correlation_id"]},
        )
        self.assertEqual({record["environment"] for record in records}, {"test"})

    def test_demo_order_rejects_unknown_customer_without_payment(self) -> None:
        result = _run_demo_order(
            "--environment",
            "test",
            "--order-id",
            "order-002",
            "--customer-id",
            "customer-unknown",
            "--amount-cents",
            "1250",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        outcome = json.loads(result.stdout)
        self.assertEqual(outcome["status"], "rejected")
        self.assertEqual(outcome["reason"], "customer_not_found")
        self.assertIsNone(outcome["payment_authorization_id"])
        self.assertFalse(outcome["notification_recorded"])
        self.assertNotIn("payment.authorized", result.stderr)
        self.assertNotIn("notification.recorded", result.stderr)

    def test_demo_order_rejects_invalid_input_without_echoing_it(self) -> None:
        unsafe_id = "order\nspoofed"
        result = _run_demo_order(
            "--environment",
            "test",
            "--order-id",
            unsafe_id,
            "--customer-id",
            "customer-001",
            "--amount-cents",
            "1250",
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertNotIn(unsafe_id, result.stderr)
        self.assertEqual(json.loads(result.stderr)["event"], "order.invalid")

    def test_demo_order_cannot_run_in_production_environment(self) -> None:
        result = _run_demo_order(
            "--environment",
            "production",
            "--order-id",
            "order-001",
            "--customer-id",
            "customer-001",
            "--amount-cents",
            "1250",
        )

        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(
            json.loads(result.stderr)["event"], "order.demo_environment_rejected"
        )

    def test_fixture_is_removed_after_cli_failure(self) -> None:
        with tempfile.TemporaryDirectory(prefix="trace-integration-") as directory:
            working_directory = Path(directory)
            env_file = working_directory / "settings.env"
            env_file.write_text(
                "TRACE_ENVIRONMENT=invalid-fixture-value\n",
                encoding="utf-8",
            )

            result = _run_check_config(env_file, working_directory)

            self.assertEqual(result.returncode, 2)
            self.assertNotIn("invalid-fixture-value", result.stderr)
            record = json.loads(result.stderr)
            self.assertEqual(record["event"], "configuration.invalid")
            self.assertIn("TRACE_ENVIRONMENT", record["error"])

        self.assertFalse(working_directory.exists())
        self.assertFalse(env_file.exists())


if __name__ == "__main__":
    unittest.main()
