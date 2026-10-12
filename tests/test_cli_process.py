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


def _run_replay(*arguments: str) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(prefix="trace-replay-") as directory:
        env_file = Path(directory) / "settings.env"
        env_file.write_text("", encoding="utf-8")
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "trace_app.cli",
                "replay-dependency",
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


def _run_persistence_demo(
    *arguments: str, working_directory: Path
) -> subprocess.CompletedProcess[str]:
    script = Path(__file__).resolve().parents[1] / "scripts" / "demo_persistence.py"
    return subprocess.run(
        [sys.executable, str(script), *arguments],
        cwd=working_directory,
        env=_minimal_environment(),
        capture_output=True,
        check=False,
        text=True,
        timeout=15,
    )


class CliProcessIntegrationTests(unittest.TestCase):
    def test_search_demo_repeats_resolves_and_checks_bounds_without_a_model(
        self,
    ) -> None:
        script = Path(__file__).resolve().parents[1] / "scripts/demo_search.py"
        with tempfile.TemporaryDirectory(prefix="trace-search-cli-") as directory:

            def execute(*arguments: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [sys.executable, str(script), *arguments],
                    cwd=directory,
                    env=_minimal_environment(),
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=15,
                )

            first = execute("--query", "TLS certificate expiry", "--top-k", "1")
            second = execute("--query", "TLS certificate expiry", "--top-k", "1")
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(first.stdout, second.stdout)
            output = json.loads(first.stdout)
            self.assertEqual(output["search"]["mode"], "lexical")
            self.assertIsNone(output["embedding"])
            self.assertEqual(len(output["search"]["results"]), 1)
            result = output["search"]["results"][0]
            self.assertEqual(
                result["chunk"]["metadata"]["document_id"],
                "trace-dev-history-certificate",
            )
            self.assertEqual(
                output["resolved_chunk_ids"], [result["citation"]["chunk_id"]]
            )
            log = json.loads(first.stderr.splitlines()[-1])
            self.assertEqual(log["event"], "retrieval.completed")
            self.assertNotEqual(log["correlation_id"], "unassigned")
            self.assertNotIn("query", log)
            empty = execute("--query", "zzzzzzzzzz")
            self.assertEqual(empty.returncode, 0, empty.stderr)
            self.assertEqual(json.loads(empty.stdout)["search"]["status"], "no_results")
            for arguments in (
                ("--top-k", "21"),
                ("--query", ""),
                ("--service", "notification"),
            ):
                failed = execute(*arguments)
                self.assertEqual(failed.returncode, 2)
                self.assertEqual(failed.stdout, "")
                self.assertEqual(json.loads(failed.stderr)["status"], "error")
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_corpus_demo_repeats_resolves_sources_and_rejects_invalid_input(
        self,
    ) -> None:
        script = Path(__file__).resolve().parents[1] / "scripts/demo_corpus.py"
        with tempfile.TemporaryDirectory(prefix="trace-corpus-cli-") as directory:

            def execute(*arguments: str) -> subprocess.CompletedProcess[str]:
                return subprocess.run(
                    [sys.executable, str(script), *arguments],
                    cwd=directory,
                    env=_minimal_environment(),
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=15,
                )

            first = execute()
            second = execute()
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(first.stdout, second.stdout)
            result = json.loads(first.stdout)
            self.assertTrue(result["same_generation"])
            self.assertTrue(result["first_created"])
            self.assertFalse(result["second_created"])
            self.assertEqual(result["generation"]["document_count"], 6)
            self.assertEqual(len(result["chunks"]), 18)
            self.assertTrue(
                all(
                    chunk["content_role"] == "untrusted_source_data"
                    and chunk["metadata"]["source_revision"]
                    for chunk in result["chunks"]
                )
            )
            logs = [json.loads(line) for line in first.stderr.splitlines()]
            self.assertEqual(
                [log["event"] for log in logs], ["corpus.ingested", "corpus.ingested"]
            )
            self.assertEqual(len({log["correlation_id"] for log in logs}), 1)
            rejected = execute("--corpus", directory)
            self.assertEqual(rejected.returncode, 2)
            self.assertEqual(rejected.stdout, "")
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_evaluation_runner_rescores_saved_artifacts_and_rejects_tampering(
        self,
    ) -> None:
        repository = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(prefix="trace-evaluation-cli-") as directory:
            output = Path(directory) / "run"
            first = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "evaluation.runner",
                    "run",
                    "--output",
                    str(output),
                ],
                cwd=repository,
                env=_minimal_environment(),
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            score = json.loads(first.stdout)
            self.assertEqual(score["summary"]["attempted"], 7)
            self.assertEqual(first.stdout, (output / "scores.json").read_text())
            self.assertTrue(
                all(
                    all(value is None for value in item["usage"].values())
                    for item in score["attempts"]
                )
            )
            logs = [json.loads(line) for line in first.stderr.splitlines()]
            self.assertEqual(logs[-1]["event"], "evaluation.artifacts.ready")
            self.assertTrue(logs[-1]["correlation_id"])
            self.assertEqual(len(logs[-1]["manifest_sha256"]), 64)
            second = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "evaluation.runner",
                    "rescore",
                    "--run-dir",
                    str(output),
                ],
                cwd=repository,
                env=_minimal_environment(),
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(second.stdout, first.stdout)
            (output / "inputs/c01.json").write_text("{}\n")
            failed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "evaluation.runner",
                    "rescore",
                    "--run-dir",
                    str(output),
                ],
                cwd=repository,
                env=_minimal_environment(),
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
            self.assertEqual(failed.returncode, 2)
            self.assertEqual(failed.stdout, "")
            self.assertIn("hash", failed.stderr)

    def test_timeline_demo_shuffles_resolves_and_preserves_incompleteness(self) -> None:
        script = Path(__file__).resolve().parents[1] / "scripts" / "demo_timeline.py"
        with tempfile.TemporaryDirectory(prefix="trace-timeline-cli-") as directory:
            for arguments, expected_count in (
                (
                    [
                        "--case",
                        "c01",
                        "--window-start",
                        "2026-01-01T05:30:17+05:30",
                        "--window-end",
                        "2026-01-01T05:30:24+05:30",
                    ],
                    9,
                ),
                (["--case", "c03"], 4),
                (["--case", "c02", "--limit", "1"], 1),
            ):
                result = subprocess.run(
                    [sys.executable, str(script), *arguments],
                    cwd=directory,
                    env=_minimal_environment(),
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=15,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                timeline = json.loads(result.stdout)
                self.assertEqual(timeline["status"], "incomplete")
                self.assertEqual(
                    timeline["query"]["window_start"], "2026-01-01T00:00:17Z"
                )
                self.assertEqual(len(timeline["events"]), expected_count)
                self.assertEqual(
                    timeline["resolved_evidence_ids"],
                    [e["evidence_id"] for e in timeline["events"]],
                )
                self.assertTrue(
                    all(e["causal_status"] == "observed" for e in timeline["events"])
                )
                self.assertEqual(timeline["truncated"], expected_count == 1)
                logs = [json.loads(line) for line in result.stderr.splitlines()]
                self.assertEqual(logs[-1]["event"], "timeline.constructed")
                self.assertEqual(
                    logs[-1]["investigation_id"], timeline["investigation_id"]
                )
                self.assertNotIn("cause_label", result.stdout)
            invalid = subprocess.run(
                [sys.executable, str(script), "--window-start", "2026-01-01T01:00:00"],
                cwd=directory,
                env=_minimal_environment(),
                capture_output=True,
                text=True,
                check=False,
                timeout=15,
            )
            self.assertEqual(invalid.returncode, 2)
            self.assertEqual(invalid.stdout, "")
            self.assertIn("numeric offset", invalid.stderr)
            self.assertEqual(list(Path(directory).iterdir()), [])

    def test_development_suite_cli_export_and_invalid_requests(self) -> None:
        with tempfile.TemporaryDirectory(prefix="trace-suite-") as directory:
            env_file = Path(directory) / "settings.env"
            env_file.write_text("", encoding="utf-8")
            for case in ("c01", "c02", "c03", "c04"):
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "trace_app.cli",
                        "replay-scenario",
                        "--env-file",
                        str(env_file),
                        "--environment",
                        "test",
                        "--case",
                        case,
                        "--seed",
                        "17",
                    ],
                    cwd=directory,
                    env=_minimal_environment(),
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=15,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                output = json.loads(result.stdout)
                self.assertEqual(output["status"], "dependency_failed")
                self.assertEqual(
                    len(output["evidence"]["entries"]),
                    9 if case in ("c01", "c02") else 4,
                )
                for forbidden in (
                    "cause_label",
                    "ground_truth",
                    "expected_assessment",
                    "case_id",
                    "mvp_suite_v1.json",
                ):
                    self.assertNotIn(forbidden, result.stdout + result.stderr)
                logs = [json.loads(line) for line in result.stderr.splitlines()]
                self.assertEqual(logs[-1]["event"], "replay.completed")
                self.assertEqual(len({record["correlation_id"] for record in logs}), 1)
            for environment, seed in (("production", "17"), ("test", "-1")):
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "trace_app.cli",
                        "replay-scenario",
                        "--env-file",
                        str(env_file),
                        "--environment",
                        environment,
                        "--case",
                        "c01",
                        "--seed",
                        seed,
                    ],
                    cwd=directory,
                    env=_minimal_environment(),
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=15,
                )
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertEqual(result.stdout, "")
                self.assertNotIn("order.requested", result.stderr)

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

    def test_replay_failure_process_exports_evidence_without_evaluator_data(
        self,
    ) -> None:
        arguments = (
            "--environment",
            "test",
            "--seed",
            "17",
            "--mode",
            "failure",
        )
        first = _run_replay(*arguments)
        second = _run_replay(*arguments)

        self.assertEqual(first.returncode, 0, first.stderr)
        self.assertEqual(second.returncode, 0, second.stderr)
        first_result = json.loads(first.stdout)
        second_result = json.loads(second.stdout)
        self.assertEqual(first_result["status"], "dependency_failed")
        self.assertEqual(
            [record["event"] for record in first_result["evidence"]["records"]],
            [
                "order.requested",
                "customer.found",
                "payment.timeout",
                "order.dependency_failed",
            ],
        )
        self.assertEqual(
            [record["evidence_id"] for record in first_result["evidence"]["records"]],
            [record["evidence_id"] for record in second_result["evidence"]["records"]],
        )
        self.assertNotIn("notification.recorded", first.stdout)
        self.assertNotIn("ground_truth", first.stdout)
        self.assertNotIn("mechanism", first.stdout)
        self.assertNotIn("expected_evidence", first.stdout)
        self.assertIn('"event":"replay.completed"', first.stderr)
        self.assertNotIn("ground_truth", first.stderr)

    def test_replay_rejects_production_environment(self) -> None:
        result = _run_replay(
            "--environment", "production", "--seed", "17", "--mode", "normal"
        )
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, "")
        self.assertEqual(json.loads(result.stderr)["event"], "replay.invalid")

    def test_persistence_demo_restarts_and_rejects_invalid_input(self) -> None:
        with tempfile.TemporaryDirectory(prefix="trace-store-process-") as directory:
            working_directory = Path(directory)
            database = working_directory / "state.sqlite3"
            invalid = _run_persistence_demo(
                "ingest",
                "--db",
                str(database),
                "--seed",
                "-1",
                "--mode",
                "failure",
                "--submission-key",
                "case-17",
                working_directory=working_directory,
            )
            self.assertEqual(invalid.returncode, 2)
            self.assertEqual(invalid.stdout, "")
            self.assertIn("seed", invalid.stderr)
            self.assertFalse(database.exists())

            arguments = (
                "ingest",
                "--db",
                str(database),
                "--seed",
                "17",
                "--mode",
                "failure",
                "--submission-key",
                "case-17",
            )
            first = _run_persistence_demo(
                *arguments, working_directory=working_directory
            )
            self.assertEqual(first.returncode, 0, first.stderr)
            ingested = json.loads(first.stdout)
            self.assertEqual(ingested["ingested"], 4)
            second = _run_persistence_demo(
                *arguments, working_directory=working_directory
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(json.loads(second.stdout)["ingested"], 0)
            shown = _run_persistence_demo(
                "show",
                "--db",
                str(database),
                "--investigation-id",
                ingested["investigation_id"],
                working_directory=working_directory,
            )
            self.assertEqual(shown.returncode, 0, shown.stderr)
            result = json.loads(shown.stdout)
            self.assertEqual(result["status"], "queued")
            self.assertEqual(
                [entry["record"]["evidence_id"] for entry in result["evidence"]],
                ingested["evidence_ids"],
            )
            self.assertEqual(
                [entry["record"]["event"] for entry in result["evidence"]],
                [
                    "order.requested",
                    "customer.found",
                    "payment.timeout",
                    "order.dependency_failed",
                ],
            )
            self.assertNotIn("ground_truth", shown.stdout)
            self.assertNotIn("cause_service", shown.stdout)

            query_arguments = (
                "query",
                "--db",
                str(database),
                "--investigation-id",
                ingested["investigation_id"],
            )
            queried = _run_persistence_demo(
                *query_arguments,
                "--service",
                "payment",
                "--window-start",
                "2026-01-01T00:00:19Z",
                "--window-end",
                "2026-01-01T00:00:19Z",
                working_directory=working_directory,
            )
            self.assertEqual(queried.returncode, 0, queried.stderr)
            query_result = json.loads(queried.stdout)
            self.assertEqual(query_result["status"], "incomplete")
            self.assertEqual(query_result["matching_count"], 1)
            self.assertFalse(query_result["truncated"])
            self.assertEqual(
                query_result["evidence"][0]["record"]["event"], "payment.timeout"
            )
            self.assertEqual(query_result["sources"][1]["status"], "unavailable")
            self.assertNotIn("ground_truth", queried.stdout)

            bounded = _run_persistence_demo(
                *query_arguments, "--limit", "1", working_directory=working_directory
            )
            self.assertEqual(bounded.returncode, 0, bounded.stderr)
            self.assertTrue(json.loads(bounded.stdout)["truncated"])
            self.assertEqual(json.loads(bounded.stdout)["matching_count"], 4)

            invalid_query = _run_persistence_demo(
                *query_arguments,
                "--window-start",
                "2026-01-01T00:00:20Z",
                "--window-end",
                "2026-01-01T00:00:17Z",
                working_directory=working_directory,
            )
            self.assertEqual(invalid_query.returncode, 2)
            self.assertEqual(invalid_query.stdout, "")
            self.assertIn("window_start", invalid_query.stderr)

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
