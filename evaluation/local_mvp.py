"""Prepare a bound Local MVP acceptance plan; never dispatch a provider or tool."""

from __future__ import annotations

import argparse
import math
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evaluation.runner import _json, _parse, _read, _sha

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "evaluation/local_mvp_protocol_v1.json"
DECISIONS = ROOT / "evaluation/local_mvp_decisions_v1.json"
_APPROVAL_KEYS = {
    "owner",
    "recorded_at",
    "reference",
    "protocol_sha256",
    "decisions_sha256",
    "source_snapshot_sha256",
}
_INTEGER_BOUNDS = {
    "repeats": (1, 100),
    "review.claims_per_model_arm": (1, 1000),
    "review.reviewers_per_claim": (2, 100),
    "review.minimum_determinate_claims_per_arm": (1, 1000),
    "limits.model_calls_per_attempt": (1, 100),
    "limits.input_tokens_per_call": (1, 263168),
    "limits.output_tokens_per_call": (16, 100000),
    "limits.tool_calls_per_attempt": (1, 100),
    "limits.attempt_deadline_ms": (1, 600000),
    "resources.memory_limit_mb": (1, 1000000),
    "resources.disk_limit_mb": (1, 1000000),
    "resources.retention_days": (1, 36500),
    "spending.monthly_cap_nusd": (1, 20000000000),
    "spending.prior_spend_nusd": (0, 20000000000),
    "spending.outstanding_reservations_nusd": (0, 20000000000),
    "spending.scope_allowance_nusd": (1, 20000000000),
}


def _object(value: Any, keys: set[str], name: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{name}: invalid object fields")
    return value


def _text(value: Any, name: str) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > 512:
        raise ValueError(f"{name}: expected bounded nonempty text")


def _timestamp(value: Any, name: str) -> None:
    _text(value, name)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError(f"{name}: expected an aware ISO timestamp") from None
    if parsed.tzinfo is None:
        raise ValueError(f"{name}: expected an aware ISO timestamp")


def validate_decisions(value: Any, protocol: dict[str, Any]) -> dict[str, Any]:
    """Null means unresolved; malformed supplied decisions fail, never become defaults."""
    template = _object(
        _parse(_read(DECISIONS)),
        {
            "schema_version",
            "revision",
            "thresholds",
            "repeats",
            "review",
            "limits",
            "resources",
            "provider",
            "spending",
            "authorization",
            "approval",
        },
        "decision template",
    )
    result = _object(value, set(template), "decisions")
    if result["schema_version"] != "local-mvp-decisions.v1":
        raise ValueError("Unsupported decision schema")
    _text(result["revision"], "revision")
    for section, fields in template.items():
        if isinstance(fields, dict):
            keys = (
                set(protocol["threshold_metrics"])
                if section == "thresholds"
                else set(fields)
            )
            _object(result[section], keys, section)
    leaves = {"repeats": result["repeats"]}
    leaves.update(
        (f"{section}.{key}", item)
        for section, fields in result.items()
        if section != "approval" and isinstance(fields, dict)
        for key, item in fields.items()
    )
    for name, item in leaves.items():
        if item is None:
            continue
        if name in _INTEGER_BOUNDS:
            low, high = _INTEGER_BOUNDS[name]
            if type(item) is not int or not low <= item <= high:
                raise ValueError(f"{name}: integer outside supported bounds")
        elif name.startswith("thresholds."):
            metric = protocol["threshold_metrics"][name.split(".")[1]]
            if (
                type(item) not in (int, float)
                or (type(item) is float and not math.isfinite(item))
                or item < 0
                or (metric["kind"] == "rate" and item > 1)
            ):
                raise ValueError(f"{name}: invalid numeric threshold")
        else:
            _text(item, name)
    provider = result["provider"]
    if provider["provider"] not in (None, "azure") or provider["model_id"] not in (
        None,
        "gpt-6-luna",
    ):
        raise ValueError("Only the selected Azure Luna pricing contract is supported")
    spending = result["spending"]
    if spending["month"] is not None and not re.fullmatch(
        r"[0-9]{4}-(0[1-9]|1[0-2])", spending["month"]
    ):
        raise ValueError("spending.month: expected YYYY-MM")
    if spending["accounting_observed_at"] is not None:
        _timestamp(
            spending["accounting_observed_at"], "spending.accounting_observed_at"
        )
        if (
            spending["month"] is not None
            and datetime.fromisoformat(
                spending["accounting_observed_at"].replace("Z", "+00:00")
            )
            .astimezone(UTC)
            .strftime("%Y-%m")
            != spending["month"]
        ):
            raise ValueError("Spending snapshot must identify the declared month")
    review = result["review"]
    if (
        review["claims_per_model_arm"] is not None
        and review["minimum_determinate_claims_per_arm"] is not None
        and review["minimum_determinate_claims_per_arm"]
        > review["claims_per_model_arm"]
    ):
        raise ValueError("Determinate coverage exceeds the selected sample")
    approval = result["approval"]
    if approval is not None:
        _object(approval, _APPROVAL_KEYS, "approval")
        for name, item in approval.items():
            _text(item, f"approval.{name}")
            if name.endswith("_sha256") and not re.fullmatch(r"[0-9a-f]{64}", item):
                raise ValueError("approval: invalid SHA-256 binding")
        _timestamp(approval["recorded_at"], "approval.recorded_at")
    return result


def assess_rate(
    numerator: int,
    denominator: int,
    threshold: float | None,
    *,
    direction: str = "minimum",
) -> dict[str, Any]:
    """Compare a rate without allowing an empty or unapproved denominator to pass."""
    if (
        type(numerator) is not int
        or type(denominator) is not int
        or not 0 <= numerator <= denominator
        or direction not in ("minimum", "maximum")
        or (
            threshold is not None
            and (type(threshold) not in (int, float) or not 0 <= threshold <= 1)
        )
    ):
        raise ValueError("Invalid rate or threshold")
    value = numerator / denominator if denominator else None
    status = "unmeasured" if value is None else "threshold_pending"
    if value is not None and threshold is not None:
        passed = value >= threshold if direction == "minimum" else value <= threshold
        status = "passed" if passed else "failed"
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": value,
        "threshold": threshold,
        "status": status,
    }


def _source_hashes() -> dict[str, str]:
    # Only named development inputs and implementation; never discover held-out data,
    # private profiles, credentials, model caches, journals or saved report contents.
    paths = {
        path
        for folder in ("src/trace_app", "scripts", "evaluation")
        for path in (ROOT / folder).rglob("*.py")
    }
    paths.update((ROOT / "corpus/development").rglob("*.md"))
    paths.update(
        ROOT / name
        for name in (
            "pyproject.toml",
            "uv.lock",
            "corpus/development/manifest.json",
            "evaluation/ground_truth/mvp_suite_v1.json",
            "evaluation/investigator_protocol_v1.json",
            "docs/architecture/development-evaluation.md",
            "docs/planning/local-mvp-acceptance.md",
        )
    )
    return {p.relative_to(ROOT).as_posix(): _sha(_read(p)) for p in sorted(paths)}


def plan(decisions_path: Path = DECISIONS) -> dict[str, Any]:
    protocol_bytes = _read(PROTOCOL)
    protocol = _parse(protocol_bytes)
    if (
        not isinstance(protocol, dict)
        or protocol.get("schema_version") != "local-mvp-protocol.v1"
    ):
        raise ValueError("Unsupported local protocol schema")
    decisions_bytes = _read(decisions_path)
    decisions = validate_decisions(_parse(decisions_bytes), protocol)
    blockers = []
    for section, value in decisions.items():
        if value is None:
            blockers.append(f"missing:{section}")
        elif isinstance(value, dict) and section != "approval":
            blockers.extend(
                f"missing:{section}.{k}" for k, v in value.items() if v is None
            )
    sources = _source_hashes()
    binding = {
        "protocol_sha256": _sha(protocol_bytes),
        "decisions_sha256": _sha(
            _json({k: v for k, v in decisions.items() if k != "approval"})
        ),
        "source_snapshot_sha256": _sha(_json(sources)),
    }
    approval = decisions["approval"]
    if approval:
        blockers.extend(
            f"approval_mismatch:{k}" for k, v in binding.items() if approval[k] != v
        )
    arms = [arm["id"] for arm in protocol["arms"]]
    schedule = []
    repeats = decisions["repeats"]
    if repeats is not None:
        for repeat in range(repeats):
            for index, case in enumerate(protocol["cohort"]["case_ids"]):
                rotation = (repeat + index) % len(arms)
                for arm in arms[rotation:] + arms[:rotation]:
                    schedule.append(
                        {"case_id": case, "seed": 17, "repeat": repeat + 1, "arm": arm}
                    )
    limits = decisions["limits"]
    model_attempts = sum(row["arm"] != "evidence_bundle" for row in schedule)
    projected = None
    if repeats is not None and all(
        limits[k] is not None
        for k in (
            "model_calls_per_attempt",
            "input_tokens_per_call",
            "output_tokens_per_call",
        )
    ):
        pricing = protocol["pricing"]
        projected = (
            model_attempts
            * limits["model_calls_per_attempt"]
            * (
                limits["input_tokens_per_call"] * pricing["input_nusd_per_token"]
                + limits["output_tokens_per_call"] * pricing["output_nusd_per_token"]
            )
        )
    spending = decisions["spending"]
    if projected is not None and spending["scope_allowance_nusd"] is not None:
        if projected > spending["scope_allowance_nusd"]:
            blockers.append("budget:projected_scope_exceeds_allowance")
    available = None
    if all(
        spending[k] is not None
        for k in (
            "monthly_cap_nusd",
            "prior_spend_nusd",
            "outstanding_reservations_nusd",
        )
    ):
        available = (
            spending["monthly_cap_nusd"]
            - spending["prior_spend_nusd"]
            - spending["outstanding_reservations_nusd"]
        )
        if available < 0 or (projected is not None and projected > available):
            blockers.append("budget:monthly_headroom_exceeded")
        if (
            spending["scope_allowance_nusd"] is not None
            and spending["scope_allowance_nusd"] > available
        ):
            blockers.append("budget:scope_allowance_exceeds_monthly_headroom")
    return {
        "schema_version": "local-mvp-dry-run.v1",
        "protocol_revision": protocol["revision"],
        "decisions_revision": decisions["revision"],
        "binding": binding,
        "decision_artifact_sha256": _sha(decisions_bytes),
        "approval": approval,
        "approval_sha256": _sha(_json(approval)) if approval else None,
        "source_sha256": sources,
        "preflight": "blocked" if blockers else "inputs_complete_for_review",
        "blockers": blockers,
        "execution": "dry_run_only; comparison runner pending #64; no authorization granted",
        "schedule": schedule,
        "schedule_status": "declared"
        if repeats is not None
        else "blocked_missing_repeats",
        "schedule_template": [
            {"case_id": c, "arm": a}
            for c in protocol["cohort"]["case_ids"]
            for a in arms
        ],
        "boundary_protocol": protocol["cohort"]["boundary_protocol"],
        "boundary_attempt_ids": protocol["cohort"]["boundary_attempt_ids"],
        "projected_model_attempts": model_attempts if repeats is not None else None,
        "projected_cost_ceiling_nusd": projected,
        "monthly_available_nusd": available,
        "pricing": protocol["pricing"],
        "actual_provider_calls": 0,
        "measured_usage": None,
        "local_mvp_release": "not_assessed",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decisions", type=Path, default=DECISIONS)
    parser.add_argument(
        "--output", type=Path, required=True, help="New private directory"
    )
    args = parser.parse_args(argv)
    try:
        manifest = plan(args.decisions)
        protocol_bytes, decisions_bytes = _read(PROTOCOL), _read(args.decisions)
        if (
            _sha(protocol_bytes) != manifest["binding"]["protocol_sha256"]
            or _sha(decisions_bytes) != manifest["decision_artifact_sha256"]
        ):
            raise ValueError("Planning inputs changed before publication")
        args.output.mkdir(mode=0o700, parents=False, exist_ok=False)
        # Keep exact inputs beside the manifest, with no overwrite or symlink following.
        for name, data in (
            ("protocol.json", protocol_bytes),
            ("decisions.json", decisions_bytes),
            ("manifest.json", _json(manifest)),
        ):
            descriptor = os.open(
                args.output / name,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                0o600,
            )
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
    except (OSError, ValueError, TypeError):
        print(
            "Local MVP planning failed: invalid input or unavailable private output.",
            file=sys.stderr,
        )
        return 2
    print(_json(manifest).decode(), end="")
    return 1 if manifest["blockers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
