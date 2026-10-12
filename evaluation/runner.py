"""Offline development fixture runner and hash-verified saved-artifact rescoring."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Literal, cast

from evaluation.scoring import (
    SCORER_VERSION,
    EvaluationAttempt,
    ExpectedOutcome,
    aggregate_scores,
    score_candidate,
)
from trace_app.demo.scenarios import (
    CASE_IDS,
    SUITE_VERSION,
    ScenarioConfig,
    ScenarioSession,
)
from trace_app.evidence.models import (
    EVIDENCE_SCHEMA_VERSION,
    EvidenceRecord,
    SourceAvailability,
)
from trace_app.evidence.timeline import TIMELINE_SCHEMA_VERSION
from trace_app.investigation.assessment import REPORT_SCHEMA_VERSION, _object, _text
from trace_app.investigation.models import (
    DeploymentPayload,
    EvidenceEntry,
    EvidenceSnapshot,
    LogPayload,
    MetricPayload,
)
from trace_app.runtime.logging import configure_logging

_ROOT = Path(__file__).resolve().parents[1]
_CONFIG = {
    "version": "development-evaluation.v1",
    "collected_at": "2026-10-12T12:00:00Z",
}
_FIXTURE_VERSION = "candidate-fixtures.v1"
_MAX_FILE_BYTES = 2_000_000
_LOG = logging.getLogger("trace_app.evaluation")


def _json(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
    ).encode()


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("JSON contains duplicate object keys.")
        result[key] = value
    return result


def _constant(value: str) -> object:
    raise ValueError("Nonfinite JSON constants are not allowed.")


def _read(path: Path) -> bytes:
    if path.is_symlink():
        raise ValueError("Artifact files must not be symbolic links.")
    with path.open("rb") as stream:
        data = stream.read(_MAX_FILE_BYTES + 1)
    if len(data) > _MAX_FILE_BYTES:
        raise ValueError("Artifact file exceeds the input byte bound.")
    return data


def _parse(data: bytes) -> object:
    return json.loads(data, object_pairs_hook=_pairs, parse_constant=_constant)


def _implementation_hashes() -> dict[str, str]:
    files = sorted((_ROOT / "src/trace_app").rglob("*.py")) + sorted(
        (_ROOT / "evaluation").glob("*.py")
    )
    return {path.relative_to(_ROOT).as_posix(): _sha(_read(path)) for path in files}


def _expected(data: object) -> dict[str, ExpectedOutcome]:
    root = _object(
        data,
        {"schema_version", "suite_version", "seeds", "cases", "split_policy"},
        "ground_truth",
    )
    if (
        root["schema_version"] != "1"
        or root["suite_version"] != SUITE_VERSION
        or root["seeds"] != [17]
    ):
        raise ValueError(
            "Ground truth must be the versioned seed-17 development suite."
        )
    if not isinstance(root["cases"], list):
        raise ValueError("ground_truth.cases must be a list.")
    result: dict[str, ExpectedOutcome] = {}
    for case in root["cases"]:
        if not isinstance(case, dict):
            raise ValueError("ground_truth.case is invalid.")
        expected = ExpectedOutcome.from_manifest_case(case)
        if expected.case_id in result:
            raise ValueError("Duplicate ground-truth case.")
        configuration = case.get("configuration")
        if (
            not isinstance(configuration, dict)
            or configuration.get("seed") != 17
            or configuration.get("environment") != "test"
            or configuration.get("notification_deployment") is not True
        ):
            raise ValueError(
                "Ground-truth configuration does not match the selected replay."
            )
        result[expected.case_id] = expected
    if set(result) != set(CASE_IDS):
        raise ValueError("Ground-truth cases must match the development generator.")
    return result


def _attempts(data: object) -> tuple[EvaluationAttempt, ...]:
    root = _object(
        data, {"schema_version", "fixture_version", "attempts"}, "candidate_fixtures"
    )
    if root["schema_version"] != "1" or root["fixture_version"] != _FIXTURE_VERSION:
        raise ValueError("Candidate fixture version is unsupported.")
    if not isinstance(root["attempts"], list) or not 1 <= len(root["attempts"]) <= 100:
        raise ValueError("attempts requires 1–100 fixtures.")
    result = tuple(EvaluationAttempt.from_dict(value) for value in root["attempts"])
    if len({attempt.attempt_id for attempt in result}) != len(result):
        raise ValueError("attempt_id must be unique.")
    for attempt in result:
        if attempt.case_id not in CASE_IDS or attempt.seed != 17:
            raise ValueError(
                "Attempt references a case/seed outside the development suite."
            )
    return result


def _snapshot(data: object) -> EvidenceSnapshot:
    root = _object(
        data, {"schema_version", "query_window", "sources", "entries"}, "input"
    )
    if root["schema_version"] != EVIDENCE_SCHEMA_VERSION:
        raise ValueError("Input evidence schema version is unsupported.")
    window = _object(root["query_window"], {"start", "end"}, "query_window")
    if not isinstance(root["entries"], list) or len(root["entries"]) > 100:
        raise ValueError("input.entries requires at most 100 records.")
    entries: list[EvidenceEntry] = []
    for value in root["entries"]:
        item = _object(value, {"kind", "record", "payload"}, "entry")
        if not isinstance(item["record"], dict):
            raise ValueError("entry.record is invalid.")
        record = EvidenceRecord.from_dict(item["record"])
        if (
            record.environment != "test"
            or record.access_classification != "synthetic_public"
        ):
            raise ValueError("Only synthetic test evidence is allowed in this runner.")
        if item["kind"] == "log":
            payload = _object(item["payload"], {"message"}, "log_payload")
            entries.append(
                EvidenceEntry("log", record, LogPayload(cast(str, payload["message"])))
            )
        elif item["kind"] == "metric":
            payload = _object(
                item["payload"], {"name", "value", "unit"}, "metric_payload"
            )
            entries.append(
                EvidenceEntry(
                    "metric",
                    record,
                    MetricPayload(
                        cast(str, payload["name"]),
                        cast(float, payload["value"]),
                        cast(str, payload["unit"]),
                    ),
                )
            )
        elif item["kind"] == "deployment":
            payload = _object(
                item["payload"], {"revision", "phase"}, "deployment_payload"
            )
            entries.append(
                EvidenceEntry(
                    "deployment",
                    record,
                    DeploymentPayload(
                        cast(str, payload["revision"]), cast(str, payload["phase"])
                    ),
                )
            )
        else:
            raise ValueError("entry.kind is unsupported.")
    if not isinstance(root["sources"], list) or len(root["sources"]) > 100:
        raise ValueError("input.sources requires a bounded list.")
    sources: list[SourceAvailability] = []
    for value in root["sources"]:
        source = _object(value, {"source", "status", "reason"}, "source")
        sources.append(
            SourceAvailability(
                _text(source["source"], "source.source"),
                cast(
                    Literal["available", "unavailable", "truncated"], source["status"]
                ),
                None
                if source["reason"] is None
                else _text(source["reason"], "source.reason"),
            )
        )
    return EvidenceSnapshot(
        tuple(entries),
        cast(str, window["start"]),
        cast(str, window["end"]),
        tuple(sources),
    )


def _scores(
    ground_truth: object, candidates: object, inputs: dict[str, object]
) -> dict[str, object]:
    expected = _expected(ground_truth)
    attempts = _attempts(candidates)
    snapshots = {case: _snapshot(inputs[case]) for case in CASE_IDS}
    scores = tuple(
        score_candidate(attempt, snapshots[attempt.case_id], expected[attempt.case_id])
        for attempt in attempts
    )
    _LOG.info(
        "Development fixture scoring completed.",
        extra={
            "event": "evaluation.scoring.completed",
            "attempted_count": len(scores),
            "execution_failure_count": sum(
                s.execution_status != "completed" for s in scores
            ),
            "invalid_report_count": sum(s.schema_error is not None for s in scores),
        },
    )
    return {
        "schema_version": "1",
        "scorer_version": SCORER_VERSION,
        "mode": "hand_authored_fixture",
        "cohort": "synthetic_development",
        "summary": aggregate_scores(scores),
        "attempts": [
            {**score.to_dict(), "usage": attempt.usage}
            for score, attempt in zip(scores, attempts, strict=True)
        ],
    }


def run(output: Path) -> dict[str, object]:
    """Create an exclusive evaluator artifact directory; never overwrite a run."""
    truth_bytes = _read(_ROOT / "evaluation/ground_truth/mvp_suite_v1.json")
    candidate_bytes = _read(_ROOT / "evaluation/fixtures/candidates_v1.json")
    truth, candidates = _parse(truth_bytes), _parse(candidate_bytes)
    _expected(truth)
    _attempts(candidates)
    inputs = {
        case: ScenarioSession(ScenarioConfig(case, 17))
        .replay(collected_at=datetime.fromisoformat(_CONFIG["collected_at"]))
        .to_dict()["evidence"]
        for case in CASE_IDS
    }
    scores = _scores(truth, candidates, inputs)
    files = {
        "ground_truth.json": truth_bytes,
        "attempts.json": candidate_bytes,
        "scores.json": _json(scores),
    }
    files.update(
        {f"inputs/{case}.json": _json(value) for case, value in inputs.items()}
    )
    manifest = {
        "schema_version": "1",
        "scorer_version": SCORER_VERSION,
        "mode": "hand_authored_fixture",
        "cohort": "synthetic_development",
        "suite_version": SUITE_VERSION,
        "seeds": [17],
        "configuration": _CONFIG,
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "evidence_schema_version": EVIDENCE_SCHEMA_VERSION,
        "timeline_schema_version": TIMELINE_SCHEMA_VERSION,
        "fixture_version": _FIXTURE_VERSION,
        "model_version": None,
        "prompt_version": None,
        "implementation_sha256": _implementation_hashes(),
        "artifact_sha256": {name: _sha(data) for name, data in files.items()},
    }
    output.mkdir(mode=0o700)
    (output / "inputs").mkdir(mode=0o700)
    # Write manifest last: a partially failed write cannot masquerade as a complete run.
    for name, data in {**files, "manifest.json": _json(manifest)}.items():
        descriptor = os.open(output / name, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
    return scores


def rescore(directory: Path) -> dict[str, object]:
    """Verify exact inputs/code versions before deterministic offline rescoring."""
    fields = {
        "schema_version",
        "scorer_version",
        "mode",
        "cohort",
        "suite_version",
        "seeds",
        "configuration",
        "report_schema_version",
        "evidence_schema_version",
        "timeline_schema_version",
        "fixture_version",
        "model_version",
        "prompt_version",
        "implementation_sha256",
        "artifact_sha256",
    }
    manifest = _object(
        _parse(_read(directory / "manifest.json")), fields, "run_manifest"
    )
    expected_versions = {
        "schema_version": "1",
        "scorer_version": SCORER_VERSION,
        "mode": "hand_authored_fixture",
        "cohort": "synthetic_development",
        "suite_version": SUITE_VERSION,
        "seeds": [17],
        "configuration": _CONFIG,
        "report_schema_version": REPORT_SCHEMA_VERSION,
        "evidence_schema_version": EVIDENCE_SCHEMA_VERSION,
        "timeline_schema_version": TIMELINE_SCHEMA_VERSION,
        "fixture_version": _FIXTURE_VERSION,
        "model_version": None,
        "prompt_version": None,
        "implementation_sha256": _implementation_hashes(),
    }
    if any(manifest[name] != value for name, value in expected_versions.items()):
        raise ValueError("Run versions/configuration/code do not match this scorer.")
    names = {"ground_truth.json", "attempts.json", "scores.json"} | {
        f"inputs/{case}.json" for case in CASE_IDS
    }
    hashes = _object(manifest["artifact_sha256"], names, "artifact_sha256")
    files: dict[str, object] = {}
    for name in sorted(names):
        data = _read(directory / name)
        if _sha(data) != hashes[name]:
            raise ValueError("Saved artifact hash does not match its manifest.")
        files[name] = _parse(data)
    scores = _scores(
        files["ground_truth.json"],
        files["attempts.json"],
        {case: files[f"inputs/{case}.json"] for case in CASE_IDS},
    )
    if _json(scores) != _json(files["scores.json"]):
        raise ValueError("Recomputed scores disagree with the saved score artifact.")
    return scores


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    execute = commands.add_parser("run")
    execute.add_argument("--output", required=True, type=Path)
    replay = commands.add_parser("rescore")
    replay.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args(argv)
    configure_logging(level="INFO")
    try:
        result = run(args.output) if args.command == "run" else rescore(args.run_dir)
        directory = args.output if args.command == "run" else args.run_dir
        manifest_hash = _sha(_read(directory / "manifest.json"))
    except (ValueError, OSError) as error:
        _LOG.error(
            "Development evaluation failed.",
            extra={"event": "evaluation.failed", "error_type": type(error).__name__},
        )
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2
    _LOG.info(
        "Evaluation artifacts ready.",
        extra={
            "event": "evaluation.artifacts.ready",
            "operation": args.command,
            "manifest_sha256": manifest_hash,
        },
    )
    print(_json(result).decode(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
