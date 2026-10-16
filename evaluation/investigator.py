"""Execute actual offline investigator outputs, then hash-verified model-free scoring."""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, cast

from evaluation.investigator_scoring import (
    SCORER_VERSION,
    review_sample,
    score_output,
    summarize,
)
from evaluation.runner import _expected, _json, _parse, _read, _sha
from evaluation.scoring import SupportReview
from trace_app.knowledge.models import canonical
from trace_app.runtime.logging import configure_logging

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "evaluation/investigator_protocol_v1.json"
VERSION = "investigator-evaluation-run.v1"
FILES = ("observed.json", "result.json", "execution.json", "sources.json")
_LOG = logging.getLogger("trace_app.evaluation")


def _source_hashes() -> dict[str, str]:
    paths = [
        path
        for folder in ("src/trace_app", "evaluation", "scripts")
        for path in (ROOT / folder).rglob("*.py")
    ]
    paths += [ROOT / "pyproject.toml", ROOT / "uv.lock"]
    return {
        path.relative_to(ROOT).as_posix(): _sha(_read(path)) for path in sorted(paths)
    }


def _write(path: Path, data: bytes) -> None:
    descriptor = os.open(
        path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600
    )
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(data)


def _artifact(directory: Path, name: str) -> bytes:
    if directory.is_symlink() or any(
        (directory / parent).is_symlink()
        for parent in Path(name).parents
        if str(parent) != "."
    ):
        raise ValueError("Artifact directories must not be symbolic links.")
    return _read(directory / name)


def _protocol(value: Any) -> dict[str, Any]:
    # The recorded protocol is frozen before measurement; no caller-supplied cohorts.
    expected = _parse(_read(PROTOCOL))
    if (
        value != expected
        or value["version"] != "sprint-05-investigator-protocol.v1"
        or len(value["cases"]) != 10
        or len({case["id"] for case in value["cases"]}) != 10
    ):
        raise ValueError("Only the frozen seed-17 development protocol is supported.")
    return value


def _review_map(
    sample: list[dict[str, Any]], data: dict[str, Any]
) -> dict[str, tuple[SupportReview, ...]]:
    if (
        set(data) != {"schema_version", "sample_sha256", "reviews"}
        or data["schema_version"] != "investigator-support-review.v1"
        or data["sample_sha256"] != _sha(_json(sample))
        or not isinstance(data["reviews"], list)
        or len(data["reviews"]) > 1000
    ):
        raise ValueError("Review input must bind to this exact sampled artifact.")
    tasks = {row["binding_id"]: row for row in sample}
    result: dict[str, list[SupportReview]] = {}
    seen = set()
    for row in data["reviews"]:
        if (
            not isinstance(row, dict)
            or set(row) != {"binding_id", "reviewer_id", "verdict", "rationale", "kind"}
            or row["binding_id"] not in tasks
            or row["kind"] != "human_review"
        ):
            raise ValueError(
                "Review must reference a sampled binding and a declared human decision."
            )
        task = tasks[row["binding_id"]]
        review = SupportReview.from_dict(
            {
                "claim_id": task["claim_id"],
                **{k: v for k, v in row.items() if k != "binding_id"},
            }
        )
        key = (row["binding_id"], review.reviewer_id)
        if key in seen:
            raise ValueError("Duplicate reviewer decision for the same binding.")
        seen.add(key)
        result.setdefault(task["attempt_id"], []).append(review)
    return {key: tuple(rows) for key, rows in result.items()}


def _score(
    files: dict[str, Any], reviews: dict[str, Any] | None = None
) -> dict[str, Any]:
    protocol = _protocol(files["protocol.json"])
    expected = _expected(files["ground_truth.json"])
    sample = files["support_sample.json"]
    # Rebuild sample bindings from actual outputs, never fixture support-port records.
    rebuilt = []
    for case in protocol["cases"]:
        if case["role"] == "development_incident":
            rebuilt.extend(
                review_sample(
                    case,
                    files[f"artifacts/{case['id']}/observed.json"],
                    files[f"artifacts/{case['id']}/result.json"],
                )
            )
    if canonical(sample) != canonical(rebuilt):
        raise ValueError("Support sample disagrees with the recorded outputs.")
    decisions = _review_map(
        sample, reviews if reviews is not None else files["human_reviews.json"]
    )
    scores = []
    for case in protocol["cases"]:
        path = f"artifacts/{case['id']}/"
        score = score_output(
            case,
            files[path + "observed.json"],
            files[path + "result.json"],
            files[path + "execution.json"],
            files[path + "sources.json"],
            expected[case["case_id"]],
            decisions.get(case["id"], ()),
        )
        score["cohort_role"] = case["role"]
        scores.append(score)
    summary = summarize(scores)
    gate = (
        summary["contract_results"]["passed"] == len(protocol["cases"])
        and not summary["critical_boundary_failures"]
    )
    return {
        "schema_version": "investigator-evaluation-scores.v1",
        "scorer_version": SCORER_VERSION,
        "mode": "offline_fixture",
        "cohort": protocol["cohort"],
        "summary": summary,
        "cohorts": {
            role: summarize([s for s in scores if s["cohort_role"] == role])
            for role in ("development_incident", "boundary_check")
        },
        "attempts": [
            {k: v for k, v in score.items() if k != "_base"} for score in scores
        ],
        "gate": {
            "offline_contract": "passed" if gate else "failed",
            "diagnostic_quality": "not_accepted_offline_provider",
            "human_support": "recorded_sample_only"
            if decisions
            else "blocked_no_actual_reviews",
            "live_end_to_end": protocol["live_end_to_end"],
            "local_mvp_release": "pending_sprint_06",
        },
        "actual_provider_calls": 0,
        "actual_human_review_decisions": sum(len(rows) for rows in decisions.values()),
        "limitations": [
            "Hand-authored model and fictional runtime support ports; no diagnostic model quality or operational usefulness claim.",
            "The fake proposes a constant placeholder cause; negative cause scores are retained, never fitted to evaluator labels.",
            "Citation existence, source mappings and structural abstention are distinct from human evidentiary support.",
            "All variants remain in one development template group; no validation/final-test material is generated or accessed.",
        ],
    }


def _missing(case: dict[str, Any], directory: Path, reason: str) -> None:
    from datetime import UTC, datetime

    from trace_app.demo.scenarios import ScenarioConfig, ScenarioSession

    replay = (
        ScenarioSession(ScenarioConfig(case["case_id"], 17))
        .replay(collected_at=datetime(2026, 10, 12, 12, tzinfo=UTC))
        .snapshot
    )
    defaults: dict[str, Any] = {
        "observed.json": {
            "schema_version": "1",
            "query_window": {"start": replay.window_start, "end": replay.window_end},
            "sources": [
                {"source": "harness_capture", "status": "unavailable", "reason": reason}
            ],
            "entries": [],
        },
        "result.json": None,
        "sources.json": [],
        "execution.json": {
            "jobs": [
                {
                    "investigation_id": None,
                    "execution_status": "failed",
                    "failure_code": reason,
                }
            ],
            "calls": [],
            "calls_available": False,
            "authority_changed": None,
            "evaluation_modules_loaded": [],
            "latency_ms": None,
            "actual_provider_calls": 0,
        },
    }
    for name, value in defaults.items():
        if not (directory / name).exists():
            _write(directory / name, _json(value))


def run(output: Path, *, mode: str = "offline_fixture") -> dict[str, Any]:
    if mode != "offline_fixture":
        raise ValueError(
            "Live suite blocked: explicit owner run/budget/source approvals, predeclared criteria and review coverage are not supplied; no offline fallback."
        )
    protocol_bytes = _read(PROTOCOL)
    protocol = _protocol(_parse(protocol_bytes))
    truth = _read(ROOT / "evaluation/ground_truth/mvp_suite_v1.json")
    _expected(_parse(truth))
    source_hashes = _source_hashes()
    output.mkdir(mode=0o700)
    (output / "artifacts").mkdir(mode=0o700)
    files: dict[str, bytes] = {
        "protocol.json": protocol_bytes,
        "ground_truth.json": truth,
    }
    with tempfile.TemporaryDirectory(prefix="trace-investigator-suite-") as temporary:
        for case in protocol["cases"]:
            workspace = Path(temporary) / case["id"]
            process_status = None
            timed_out = False
            try:
                process = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "scripts.investigator_suite",
                        "--directory",
                        str(workspace),
                        "--case",
                        case["case_id"],
                        "--fault",
                        case["fault"],
                    ],
                    cwd=ROOT,
                    env={
                        "PATH": os.environ.get("PATH", os.defpath),
                        "OPENBLAS_NUM_THREADS": "1",
                        "OMP_NUM_THREADS": "1",
                    },
                    capture_output=True,
                    timeout=180,
                    check=False,
                )
                process_status = process.returncode
                if process.returncode:
                    workspace.mkdir(mode=0o700, exist_ok=True)
                    _missing(case, workspace, "harness_failure")
            except subprocess.TimeoutExpired:
                timed_out = True
                workspace.mkdir(mode=0o700, exist_ok=True)
                _missing(case, workspace, "harness_timeout")
            execution = json.loads(_read(workspace / "execution.json"))
            execution["harness_exit_code"] = process_status
            execution["harness_timeout"] = timed_out
            execution_bytes = _json(execution)
            target = output / "artifacts" / case["id"]
            target.mkdir(mode=0o700)
            for name in FILES:
                files[f"artifacts/{case['id']}/{name}"] = (
                    execution_bytes
                    if name == "execution.json"
                    else _read(workspace / name)
                )
    parsed: dict[str, Any] = {name: _parse(data) for name, data in files.items()}
    sample = []
    for case in protocol["cases"]:
        if case["role"] == "development_incident":
            sample.extend(
                review_sample(
                    case,
                    parsed[f"artifacts/{case['id']}/observed.json"],
                    parsed[f"artifacts/{case['id']}/result.json"],
                )
            )
    files["support_sample.json"] = _json(sample)
    files["human_reviews.json"] = _json(
        {
            "schema_version": "investigator-support-review.v1",
            "sample_sha256": _sha(files["support_sample.json"]),
            "reviews": [],
        }
    )
    scores = _score({name: _parse(data) for name, data in files.items()})
    files["scores.json"] = _json(scores)
    if source_hashes != _source_hashes():
        raise ValueError(
            "Implementation changed during measurement; use a fresh run after freezing it."
        )
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    dirty = bool(
        subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )
    manifest = {
        "schema_version": VERSION,
        "scorer_version": SCORER_VERSION,
        "mode": "offline_fixture",
        "protocol_sha256": _sha(protocol_bytes),
        "implementation_sha256": source_hashes,
        "checkout": head,
        "working_tree_dirty": dirty,
        "artifact_sha256": {name: _sha(data) for name, data in files.items()},
        "component_evidence_sha256": {
            name: _sha(_read(ROOT / name))
            for name in (
                "evaluation/reports/retrieval_passage_acceptance_v4.json",
                "evaluation/reports/tool_choices_development_v1.json",
            )
        },
    }
    # Manifest last: partial writes never count as a complete evaluation run.
    for name, data in {**files, "manifest.json": _json(manifest)}.items():
        _write(output / name, data)
    return scores


def _load(directory: Path) -> dict[str, Any]:
    manifest = _parse(_artifact(directory, "manifest.json"))
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_version") != VERSION
        or manifest.get("scorer_version") != SCORER_VERSION
        or manifest.get("mode") != "offline_fixture"
        or manifest.get("implementation_sha256") != _source_hashes()
        or manifest.get("protocol_sha256") != _sha(_read(PROTOCOL))
    ):
        raise ValueError(
            "Saved run requires its recorded implementation/protocol checkout."
        )
    protocol = _protocol(_parse(_artifact(directory, "protocol.json")))
    names = {
        "protocol.json",
        "ground_truth.json",
        "support_sample.json",
        "human_reviews.json",
        "scores.json",
    } | {
        f"artifacts/{case['id']}/{name}" for case in protocol["cases"] for name in FILES
    }
    if set(manifest["artifact_sha256"]) != names:
        raise ValueError("Manifest must account for every planned case and artifact.")
    files = {}
    for name in sorted(names):
        data = _artifact(directory, name)
        if _sha(data) != manifest["artifact_sha256"][name]:
            raise ValueError("Saved artifact bytes disagree with their hash.")
        files[name] = _parse(data)
    if _sha(_json(files["ground_truth.json"])) != _sha(
        _json(_parse(_read(ROOT / "evaluation/ground_truth/mvp_suite_v1.json")))
    ):
        raise ValueError("Ground truth must match its recorded development checkout.")
    component_names = {
        "evaluation/reports/retrieval_passage_acceptance_v4.json",
        "evaluation/reports/tool_choices_development_v1.json",
    }
    if set(manifest.get("component_evidence_sha256", {})) != component_names or any(
        _sha(_read(ROOT / name)) != manifest["component_evidence_sha256"][name]
        for name in component_names
    ):
        raise ValueError(
            "Independent component evidence does not match its recorded bytes."
        )
    return files


def rescore(directory: Path) -> dict[str, Any]:
    files = _load(directory)
    scores = _score(files)
    if _json(scores) != _json(files["scores.json"]):
        raise ValueError("Deterministic scores disagree with the saved report.")
    return scores


def review(directory: Path, review_path: Path, output: Path) -> dict[str, Any]:
    files = _load(directory)
    review_bytes = _read(review_path)
    result = _score(files, cast(dict[str, Any], _parse(review_bytes)))
    _write(
        output,
        _json(
            {
                "score_artifact": result,
                "review_file_sha256": _sha(review_bytes),
                "run_manifest_sha256": _sha(_artifact(directory, "manifest.json")),
            }
        ),
    )
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    execute = commands.add_parser("run")
    execute.add_argument("--output", type=Path, required=True)
    execute.add_argument(
        "--mode", choices=("offline_fixture", "live"), default="offline_fixture"
    )
    for name in ("rescore", "review"):
        command = commands.add_parser(name)
        command.add_argument("--run-dir", type=Path, required=True)
        if name == "review":
            command.add_argument("--reviews", type=Path, required=True)
            command.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    configure_logging()
    try:
        scores = (
            run(args.output, mode=args.mode)
            if args.command == "run"
            else rescore(args.run_dir)
            if args.command == "rescore"
            else review(args.run_dir, args.reviews, args.output)
        )
    except (ValueError, OSError, KeyError, TypeError, RecursionError):
        _LOG.error(
            "Investigator evaluation failed without disclosing content.",
            extra={"event": "investigator_evaluation.failed"},
        )
        return 2
    _LOG.info(
        "Investigator evaluation artifacts ready.",
        extra={
            "event": "investigator_evaluation.completed",
            "attempted": scores["summary"]["attempted"],
            "offline_contract": scores["gate"]["offline_contract"],
        },
    )
    print(_json(scores).decode(), end="")
    return 0 if scores["gate"]["offline_contract"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
