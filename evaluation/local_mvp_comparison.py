"""Run the declared three-arm offline contract comparison; rescore without dispatch."""

from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
import tempfile
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from evaluation.investigator import FILES, _artifact, _missing, _write
from evaluation.investigator_scoring import review_sample, score_output, summarize
from evaluation.local_mvp import (
    DECISIONS,
    PROTOCOL,
    ROOT,
    _source_hashes,
    assess_rate,
    plan,
)
from evaluation.runner import _expected, _json, _parse, _read, _sha, _snapshot
from evaluation.scoring import EvaluationAttempt, aggregate_scores, score_candidate
from trace_app.investigation.assessment_schema import AssessmentReport
from trace_app.investigation.execution import ExecutionPolicy

VERSION = "local-mvp-comparison.v1"


def capture(case: str) -> dict[str, Any]:
    from trace_app.demo.scenarios import ScenarioConfig, ScenarioSession

    snapshot = (
        ScenarioSession(ScenarioConfig(case, 17))
        .replay(collected_at=datetime(2026, 10, 12, 12, tzinfo=UTC))
        .snapshot
    )
    return {
        "schema_version": "1",
        "query_window": {"start": snapshot.window_start, "end": snapshot.window_end},
        "sources": [asdict(source) for source in snapshot.sources],
        "entries": [
            {
                "kind": entry.kind,
                "record": entry.record.to_dict(),
                "payload": asdict(entry.payload),
            }
            for entry in snapshot.entries
        ],
    }


def execution_policy(decisions: dict[str, Any]) -> ExecutionPolicy:
    limits = decisions["limits"]
    return ExecutionPolicy(
        configuration_id="local-mvp-approved.v2",
        deadline_ms=limits["attempt_deadline_ms"],
        max_model_calls=limits["model_calls_per_attempt"],
        max_tool_calls=limits["tool_calls_per_attempt"],
        max_retries=limits["automatic_paid_retries"],
        max_input_tokens=limits["input_tokens_per_call"],
        max_output_tokens=limits["output_tokens_per_call"],
        max_total_tokens=limits["model_calls_per_attempt"]
        * (limits["input_tokens_per_call"] + limits["output_tokens_per_call"]),
    )


def schedule_rows(planning: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {**row, "id": f"a{index:03d}", "fault": "none"}
        for index, row in enumerate(planning["schedule"], 1)
    ]


def _reference_score(
    case: dict, observed: dict, result: Any, execution: dict, expected: Any
) -> dict:
    status = (result or {}).get("execution_status", "failed")
    report = (result or {}).get("report")
    projected = None
    malformed = False
    if report is not None:
        try:
            projected = AssessmentReport.from_dict(report).candidate.to_dict()
        except ValueError:
            malformed = True
    calls = execution.get("calls", [])
    model_calls = [c for c in calls if c["kind"] == "model"]
    usage = {
        "latency_ms": execution.get("latency_ms"),
        "tokens": sum(
            c["usage"]["input_tokens"] + c["usage"]["output_tokens"]
            for c in model_calls
        )
        if model_calls
        and all(
            type(c.get("usage", {}).get(k)) is int
            for c in model_calls
            for k in ("input_tokens", "output_tokens")
        )
        else None,
        "estimated_cost_usd": sum(c["estimated_cost_nusd"] for c in model_calls)
        / 1_000_000_000
        if model_calls
        and all(type(c.get("estimated_cost_nusd")) is int for c in model_calls)
        else None,
        "tool_calls": sum(c["kind"] == "tool" for c in calls)
        if execution.get("calls_available", True)
        else None,
    }
    citations = (result or {}).get("citations", {})
    brief = (result or {}).get("brief")
    view = citations.get("incident-brief", {})
    valid: frozenset[str] = frozenset()
    if set(citations) == {"incident-brief"}:
        content = view.get("fields", {}).get("content", "")
        try:
            if (
                _parse(content.encode()) == brief
                and view.get("source_revision") == "brief.v1"
            ):
                valid = frozenset({"incident-brief"})
        except ValueError:
            pass
    attempt = EvaluationAttempt.from_dict(
        {
            "attempt_id": case["id"],
            "case_id": case["case_id"],
            "seed": case["seed"],
            "execution_status": status,
            "failure_code": None
            if status == "completed"
            else (result or {}).get("failure_code") or "output_missing",
            "report": projected,
            "usage": usage,
            "support_reviews": [],
        }
    )
    base = score_candidate(
        attempt, _snapshot(observed), expected, valid_citation_ids=valid
    )
    if malformed:
        base = replace(base, schema_error="invalid_assessment_v2", report_missing=False)
    return {
        **base.to_dict(),
        "usage": usage,
        "model_calls": len(model_calls),
        "_base": base,
    }


def measurements(rows: list[dict[str, Any]]) -> dict[str, Any]:
    usage = [row.get("usage", row) for row in rows]
    latencies = [row.get("latency_ms") for row in usage]
    costs = [row.get("estimated_cost_usd") for row in usage]
    return {
        "elapsed_p95_ms": sorted(latencies)[math.ceil(0.95 * len(latencies)) - 1]
        if latencies and all(type(v) in (int, float) for v in latencies)
        else None,
        "estimated_cost_per_attempt_nusd": max(costs) * 1_000_000_000
        if costs and all(type(v) in (int, float) for v in costs)
        else None,
        "usage_origin": "synthetic_port_measurements; no Azure diagnostic measurements",
        "attempt_usage": usage,
    }


def thresholds(
    summary: dict[str, Any], measured: dict[str, Any], decisions: dict[str, Any]
) -> dict[str, Any]:
    result = {}
    metrics = dict(summary)
    metrics["completion_rate"] = {
        "numerator": summary["execution_counts"]["completed"],
        "denominator": summary["attempted"],
    }
    for name, threshold in decisions["thresholds"].items():
        value = metrics.get(name)
        if isinstance(value, dict) and "numerator" in value:
            result[name] = assess_rate(
                value["numerator"],
                value["denominator"],
                threshold,
                direction="maximum"
                if name == "human_unsupported_claim_rate"
                else "minimum",
            )
        else:
            scalar = measured.get(name)
            result[name] = {
                "value": scalar,
                "threshold": threshold,
                "status": "unmeasured"
                if scalar is None
                else "threshold_pending"
                if threshold is None
                else "passed"
                if scalar <= threshold
                else "failed",
            }
    return result


def score(files: dict[str, Any]) -> dict[str, Any]:
    expected = _expected(files["ground_truth.json"])
    rows = files["schedule.json"]
    arms: dict[str, list[dict]] = {
        a: [] for a in ("llm_only", "evidence_bundle", "rag_tools")
    }
    outcomes = []
    samples = []
    paired: dict[tuple[str, int, int], str] = {}
    for row in rows:
        prefix = f"artifacts/{row['id']}/"
        observed, result, execution, sources = (files[prefix + n] for n in FILES)
        status = execution.get("jobs", [{}])[0].get("execution_status", "failed")
        pairing = (row["case_id"], row["seed"], row["repeat"])
        if observed != capture(row["case_id"]):
            raise ValueError(
                "Observed capture differs from the declared synthetic source."
            )
        observed_hash = _sha(_json(observed))
        if pairing in paired and paired[pairing] != observed_hash:
            raise ValueError("Paired arms did not observe the same captured source.")
        paired[pairing] = observed_hash
        if (
            execution.get("evaluation_modules_loaded") != []
            or execution.get("actual_provider_calls") != 0
        ):
            raise ValueError(
                "Offline comparison isolation or provider boundary violated."
            )
        if row["arm"] == "rag_tools":
            scored = score_output(
                row, observed, result, execution, sources, expected[row["case_id"]]
            )
            arms[row["arm"]].append(scored)
        elif row["arm"] == "llm_only":
            scored = _reference_score(
                row, observed, result, execution, expected[row["case_id"]]
            )
            arms[row["arm"]].append(scored)
        else:
            ordered = sorted(
                observed["entries"],
                key=lambda e: (e["record"]["observed_at"], e["record"]["evidence_id"]),
            )
            timeline = (result or {}).get("timeline", [])
            valid = (
                status == "completed"
                and [r["citation_id"] for r in timeline]
                == [e["record"]["evidence_id"] for e in ordered]
                and all(
                    r
                    == {
                        "citation_id": e["record"]["evidence_id"],
                        "source_revision": e["record"]["source_revision"],
                        "observed_at": e["record"]["observed_at"],
                        "collected_at": e["record"]["collected_at"],
                        "causal_status": "observed",
                    }
                    for r, e in zip(timeline, ordered, strict=False)
                )
            )
            scored = {
                "completed": status == "completed",
                "deterministic_timeline_valid": valid,
                "diagnostic_metrics": "not_applicable",
                "tool_calls": sum(
                    c["kind"] == "tool" for c in execution.get("calls", [])
                ),
                "latency_ms": execution.get("latency_ms"),
            }
            arms[row["arm"]].append(scored)
        if row["arm"] != "evidence_bundle":
            samples.extend(review_sample(row, observed, result))
        outcomes.append(
            {
                **row,
                "source_sha256": observed_hash,
                "execution_status": status,
                "failure_code": execution.get("jobs", [{}])[0].get("failure_code"),
                "score": {k: v for k, v in scored.items() if k != "_base"},
            }
        )
    bundle = arms["evidence_bundle"]
    integrated = summarize(arms["rag_tools"])
    measured = {arm: measurements(values) for arm, values in arms.items()}
    return {
        "schema_version": "local-mvp-comparison-scores.v1",
        "mode": "offline_fixture",
        "scheduled": len(rows),
        "actual_provider_calls": 0,
        "actual_human_review_decisions": 0,
        "arms": {
            "rag_tools": integrated,
            "llm_only": aggregate_scores(tuple(s["_base"] for s in arms["llm_only"])),
            "evidence_bundle": {
                "attempted": len(bundle),
                "completed": sum(s["completed"] for s in bundle),
                "deterministic_timeline_valid": sum(
                    s["deterministic_timeline_valid"] for s in bundle
                ),
                "diagnostic_metrics": "not_applicable",
                "model_calls": 0,
            },
        },
        "measurements": measured,
        "integrated_fixture_thresholds": thresholds(
            integrated, measured["rag_tools"], files["decisions.json"]
        ),
        "threshold_applicability": {
            "rag_tools": "fixture-only comparison; no live acceptance",
            "llm_only": "descriptive reference",
            "evidence_bundle": "completion, full observed timeline and latency only; diagnosis/support/cost nonapplicable",
        },
        "attempts": outcomes,
        "support_sample": samples,
        "paired_development_results": [
            {
                "case_id": key[0],
                "seed": key[1],
                "repeat": key[2],
                "source_sha256": value,
                "attempt_ids": [
                    r["id"]
                    for r in rows
                    if (r["case_id"], r["seed"], r["repeat"]) == key
                ],
            }
            for key, value in paired.items()
        ],
        "live_diagnostics": {
            "status": "blocked",
            "blockers": files["plan.json"]["blockers"],
        },
        "release": "not_assessed; offline fixtures do not measure model quality or human support",
        "limitations": files["protocol.json"]["limitations"]
        + [
            "Scripted model measurements are contract fixtures, not Azure diagnostic results.",
            "All scheduled failures remain in denominators; no automatic retries or replacement runs.",
            "Review-required proposals remain unendorsed; claim review is a separate #65 artifact.",
        ],
    }


def run(output: Path, *, mode: str = "offline_fixture") -> dict[str, Any]:
    if mode != "offline_fixture":
        raise ValueError(
            "Live dispatch unavailable: unresolved owner run, source/transmission and current spending bindings; no fallback."
        )
    planning = plan()
    rows = schedule_rows(planning)
    decisions = cast(dict[str, Any], _parse(_read(DECISIONS)))
    policy = execution_policy(decisions)
    sources = _source_hashes()
    if sources != planning["source_sha256"]:
        raise ValueError("Planning sources changed before dispatch.")
    files = {
        "protocol.json": _read(PROTOCOL),
        "decisions.json": _read(DECISIONS),
        "plan.json": _json(planning),
        "schedule.json": _json(rows),
        "ground_truth.json": _read(ROOT / "evaluation/ground_truth/mvp_suite_v1.json"),
        "execution_policy.json": _json(asdict(policy)),
    }
    captures = {row["case_id"]: _json(capture(row["case_id"])) for row in rows}
    output.mkdir(mode=0o700)
    (output / "artifacts").mkdir(mode=0o700)
    for name, data in files.items():
        _write(output / name, data)
    with tempfile.TemporaryDirectory(prefix="trace-local-mvp-") as temp:
        policy_path = Path(temp) / "policy.json"
        _write(policy_path, files["execution_policy.json"])
        for row in rows:
            workspace = Path(temp) / row["id"]
            arguments = [
                sys.executable,
                "-m",
                "scripts.investigator_suite"
                if row["arm"] == "rag_tools"
                else "scripts.local_mvp_reference",
                "--directory",
                str(workspace),
                "--case",
                row["case_id"],
                "--policy",
                str(policy_path),
            ]
            arguments += (
                ["--unreviewed"] if row["arm"] == "rag_tools" else ["--arm", row["arm"]]
            )
            exit_code, timeout = None, False
            try:
                process = subprocess.run(
                    arguments,
                    cwd=ROOT,
                    env={
                        "PATH": os.environ.get("PATH", os.defpath),
                        "OPENBLAS_NUM_THREADS": "1",
                        "OMP_NUM_THREADS": "1",
                    },
                    capture_output=True,
                    timeout=policy.deadline_ms / 1000 + 10,
                    check=False,
                )
                exit_code = process.returncode
            except subprocess.TimeoutExpired:
                timeout = True
            workspace.mkdir(mode=0o700, exist_ok=True)
            unavailable = exit_code != 0 or any(
                not (workspace / n).is_file() for n in FILES
            )
            if unavailable:
                _missing(
                    row, workspace, "harness_timeout" if timeout else "harness_failure"
                )
            execution = cast(
                dict[str, Any], _parse(_read(workspace / "execution.json"))
            )
            execution.update(harness_exit_code=exit_code, harness_timeout=timeout)
            if unavailable:
                execution["jobs"] = [
                    {
                        "investigation_id": None,
                        "execution_status": "failed",
                        "failure_code": "harness_timeout"
                        if timeout
                        else "harness_failure",
                    }
                ]
                execution["capture_available"] = False
            if (
                execution.get("evaluation_modules_loaded") != []
                or execution.get("actual_provider_calls") != 0
                or (not unavailable and execution.get("authority_changed") is not False)
            ):
                raise ValueError(
                    "Critical offline isolation boundary failed; no further dispatch."
                )
            target = output / "artifacts" / row["id"]
            target.mkdir(mode=0o700)
            for name in FILES:
                files[f"artifacts/{row['id']}/{name}"] = (
                    _json(execution)
                    if name == "execution.json"
                    else _json(None)
                    if name == "result.json" and unavailable
                    else captures[row["case_id"]]
                    if name == "observed.json" and unavailable
                    else _read(workspace / name)
                )
                _write(
                    output / f"artifacts/{row['id']}/{name}",
                    files[f"artifacts/{row['id']}/{name}"],
                )
    report = score({name: _parse(data) for name, data in files.items()})
    files["scores.json"] = _json(report)
    if sources != _source_hashes():
        raise ValueError("Sources changed during comparison.")
    _write(output / "scores.json", files["scores.json"])
    _write(
        output / "manifest.json",
        _json(
            {
                "schema_version": VERSION,
                "mode": mode,
                "implementation_sha256": sources,
                "artifact_sha256": {name: _sha(data) for name, data in files.items()},
            }
        ),
    )
    return report


def rescore(directory: Path) -> dict[str, Any]:
    manifest = cast(dict[str, Any], _parse(_artifact(directory, "manifest.json")))
    if (
        manifest.get("schema_version") != VERSION
        or manifest.get("mode") != "offline_fixture"
        or manifest.get("implementation_sha256") != _source_hashes()
    ):
        raise ValueError("Use the recorded comparison checkout.")
    rows = schedule_rows(plan())
    names = {
        "protocol.json",
        "decisions.json",
        "plan.json",
        "schedule.json",
        "ground_truth.json",
        "execution_policy.json",
        "scores.json",
    } | {f"artifacts/{row['id']}/{name}" for row in rows for name in FILES}
    if set(manifest["artifact_sha256"]) != names:
        raise ValueError("Incomplete declared artifact inventory.")
    files = {}
    for name in sorted(names):
        data = _artifact(directory, name)
        if _sha(data) != manifest["artifact_sha256"][name]:
            raise ValueError("Changed comparison artifact.")
        files[name] = _parse(data)
    if (
        files["schedule.json"] != rows
        or files["protocol.json"] != _parse(_read(PROTOCOL))
        or files["decisions.json"] != _parse(_read(DECISIONS))
        or files["ground_truth.json"]
        != _parse(_read(ROOT / "evaluation/ground_truth/mvp_suite_v1.json"))
    ):
        raise ValueError("Comparison inputs differ from declared checkout.")
    if files["plan.json"] != plan() or files["execution_policy.json"] != asdict(
        execution_policy(cast(dict[str, Any], files["decisions.json"]))
    ):
        raise ValueError("Recorded plan or execution bounds changed.")
    result = score(files)
    if _json(result) != _json(files["scores.json"]):
        raise ValueError("Saved comparison scores disagree.")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    execute = commands.add_parser("run")
    execute.add_argument("--output", type=Path, required=True)
    execute.add_argument(
        "--mode", choices=("offline_fixture", "live"), default="offline_fixture"
    )
    saved = commands.add_parser("rescore")
    saved.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = (
            run(args.output, mode=args.mode)
            if args.command == "run"
            else rescore(args.run_dir)
        )
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        print(
            "Comparison failed: invalid input, incomplete artifact or unavailable output.",
            file=sys.stderr,
        )
        return 2
    print(_json(report).decode(), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
