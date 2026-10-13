"""Independent development tool-choice fixtures and actual API boundary smoke."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.demo_integration import ROOT, integration_fixture
from trace_app.investigation.bundle import build_evidence_package
from trace_app.investigation.tools import TOOL_NAMES, ToolStatus
from trace_app.knowledge.models import canonical, digest
from trace_app.runtime.logging import configure_logging

FIXTURES = ROOT / "evaluation/fixtures/tool_choices_v1.json"
SCORER_VERSION = "tool-choice-scorer.v1"
_TOKENS = {
    "$window_start",
    "$window_end",
    "$evidence_id",
    "$generation_id",
    "$chunk_id",
}


def read_json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 2_000_000:
        raise ValueError("Evaluator input requires a bounded regular nonsymlink file.")

    def pairs(values):
        result = {}
        for key, value in values:
            if key in result:
                raise ValueError("Duplicate JSON key.")
            result[key] = value
        return result

    def constant(value):
        raise ValueError("Nonfinite JSON is forbidden.")

    return json.loads(
        path.read_bytes(), object_pairs_hook=pairs, parse_constant=constant
    )


def validate_fixture(value: dict[str, Any]) -> dict[str, Any]:
    if set(value) != {
        "schema_version",
        "version",
        "evaluation_role",
        "judgment_kind",
        "limitations",
        "cases",
    } or (
        value["schema_version"] != "1"
        or value["version"] != "tool-choice-fixtures.v1"
        or value["evaluation_role"] != "development_evaluator_only"
        or value["judgment_kind"] != "agent_authored_fixture_expectation"
    ):
        raise ValueError("Unsupported tool fixture schema.")
    if not isinstance(value["cases"], list) or not 1 <= len(value["cases"]) <= 100:
        raise ValueError("Tool fixture count exceeds bound.")
    identities = set()
    statuses: set[ToolStatus] = {
        "ok",
        "partial",
        "empty",
        "validation_error",
        "authorization_error",
        "dependency_failure",
        "timeout",
        "budget_exhausted",
    }
    for case in value["cases"]:
        if (
            set(case) != {"id", "question", "acceptable_calls", "rejected_calls"}
            or case["id"] in identities
        ):
            raise ValueError("Invalid or duplicate tool case.")
        identities.add(case["id"])
        if (
            not isinstance(case["question"], str)
            or not 1 <= len(case["question"]) <= 2000
        ):
            raise ValueError("Invalid tool question.")
        for field in ("acceptable_calls", "rejected_calls"):
            calls = case[field]
            if not isinstance(calls, list) or len(calls) > 10:
                raise ValueError("Tool examples exceed bound.")
            for call in calls:
                if set(call) != {
                    "name",
                    "arguments",
                    "allowed_statuses",
                } or not isinstance(call["arguments"], dict):
                    raise ValueError("Invalid example call.")
                if field == "acceptable_calls" and call["name"] not in TOOL_NAMES:
                    raise ValueError("Unknown acceptable tool.")
                if (
                    not isinstance(call["allowed_statuses"], list)
                    or not call["allowed_statuses"]
                    or set(call["allowed_statuses"]) - statuses
                ):
                    raise ValueError("Invalid expected API outcome.")
                for argument in call["arguments"].values():
                    if (
                        isinstance(argument, str)
                        and argument.startswith("$")
                        and argument not in _TOKENS
                    ):
                        raise ValueError("Unknown supplied-observation token.")
        if not case["acceptable_calls"] and not case["rejected_calls"]:
            raise ValueError("Tool case has no examples.")
    return value


def resolve_arguments(
    arguments: dict[str, Any], observations: dict[str, str]
) -> dict[str, Any]:
    return {
        key: observations[value]
        if isinstance(value, str) and value in _TOKENS
        else value
        for key, value in arguments.items()
    }


def choice_matches(
    case: dict[str, Any],
    name: str,
    arguments: dict[str, Any],
    observations: dict[str, str],
) -> bool:
    """Exact declared alternatives; never consult root-cause ground truth."""
    return any(
        name == call["name"]
        and canonical(arguments)
        == canonical(resolve_arguments(call["arguments"], observations))
        for call in case["acceptable_calls"]
    )


def run_fixture_checks(fixture: dict[str, Any]) -> dict[str, Any]:
    validate_fixture(fixture)
    with integration_fixture() as setup:
        package = build_evidence_package(
            setup.session(),
            investigation_id=setup.scope.investigation_id,
            query=setup.query,
            knowledge_query="Payment timeout evidence",
            knowledge_service="payment",
        )
        if package.data is None:
            raise ValueError("Integration package failed before evaluator smoke.")
        citations = package.data["knowledge"]["context"]["data"]["citations"]
        citation = next(iter(citations.values()))
        observations = {
            "$window_start": setup.query.window_start,
            "$window_end": setup.query.window_end,
            "$evidence_id": package.data["references"]["evidence"][0],
            "$generation_id": citation["corpus_generation_id"],
            "$chunk_id": citation["chunk_id"],
        }
        attempts = []
        for case in fixture["cases"]:
            for field in ("acceptable_calls", "rejected_calls"):
                for ordinal, call in enumerate(case[field]):
                    arguments = resolve_arguments(call["arguments"], observations)
                    result = setup.session().invoke(call["name"], arguments)
                    attempts.append(
                        {
                            "case_id": case["id"],
                            "example_kind": field,
                            "example_index": ordinal,
                            "name": call["name"],
                            "arguments": arguments,
                            "actual_status": result.payload.status,
                            "reason": result.payload.reason,
                            "audit": result.to_dict()["audit"],
                        }
                    )
    report = {
        "schema_version": "1",
        "scorer_version": SCORER_VERSION,
        "fixture": fixture,
        "observations": observations,
        "attempts": attempts,
        "runtime_package_sha256": package.data_sha256,
        "model_evaluation": "not_run",
        "paid_calls": 0,
        "source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in [
                *sorted((ROOT / "src/trace_app").rglob("*.py")),
                Path(__file__).resolve(),
                ROOT / "scripts/demo_integration.py",
                ROOT / "uv.lock",
            ]
        },
    }
    report["input_sha256"] = {
        field: digest(canonical(report[field]))
        for field in ("fixture", "observations", "attempts")
    }
    report["summary"] = summarize(report)
    return report


def summarize(report: dict[str, Any]) -> dict[str, Any]:
    fixture = validate_fixture(report["fixture"])
    scheduled = {
        (case["id"], field, ordinal): call
        for case in fixture["cases"]
        for field in ("acceptable_calls", "rejected_calls")
        for ordinal, call in enumerate(case[field])
    }
    seen = set()
    failures = []
    for attempt in report["attempts"]:
        key = (attempt["case_id"], attempt["example_kind"], attempt["example_index"])
        if key not in scheduled or key in seen:
            raise ValueError("Unscheduled or duplicate tool example.")
        seen.add(key)
        call = scheduled[key]
        if attempt["name"] != call["name"] or attempt["arguments"] != resolve_arguments(
            call["arguments"], report["observations"]
        ):
            raise ValueError("Recorded tool arguments differ from schedule.")
        if attempt["actual_status"] not in call["allowed_statuses"]:
            failures.append(":".join(map(str, key)))
    if seen != set(scheduled):
        raise ValueError("Missing scheduled tool examples.")
    return {
        "cases": len(fixture["cases"]),
        "scheduled_examples": len(scheduled),
        "failures": failures,
        "passed": not failures,
    }


def rescore(report: dict[str, Any]) -> dict[str, Any]:
    if (
        report["scorer_version"] != SCORER_VERSION
        or report["source_sha256"]["evaluation/tool_evaluation.py"]
        != hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    ):
        raise ValueError("Saved tool scorer differs.")
    for field in ("fixture", "observations", "attempts"):
        if report["input_sha256"][field] != digest(canonical(report[field])):
            raise ValueError("Saved tool input hash differs.")
    summary = summarize(report)
    if (
        summary != report["summary"]
        or report["model_evaluation"] != "not_run"
        or report["paid_calls"] != 0
    ):
        raise ValueError("Saved tool summary or measurement claim differs.")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--output", type=Path)
    group.add_argument("--rescore", type=Path)
    args = parser.parse_args()
    configure_logging()
    try:
        if args.rescore:
            summary = rescore(read_json(args.rescore))
        else:
            report = run_fixture_checks(validate_fixture(read_json(FIXTURES)))
            with args.output.open("x", encoding="utf-8") as stream:
                json.dump(report, stream, indent=2, allow_nan=False)
                stream.write("\n")
            summary = report["summary"]
        print(json.dumps(summary))
        return int(not summary["passed"])
    except (ValueError, OSError, TypeError, KeyError) as error:
        print(json.dumps({"status": "error", "error": str(error)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
