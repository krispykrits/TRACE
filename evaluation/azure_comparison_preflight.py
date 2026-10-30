"""Inspect local Azure-comparison prerequisites without dispatching a provider."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import stat
import sys
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from evaluation.local_mvp import DECISIONS, plan
from evaluation.runner import _json, _parse, _read, _sha
from trace_app.investigation.provider import ModelErrorCode

UNCERTAIN = tuple(
    error.value
    for error in (
        ModelErrorCode.TIMEOUT,
        ModelErrorCode.AUDIT,
        ModelErrorCode.DEPENDENCY,
        ModelErrorCode.CANCELLED,
        ModelErrorCode.EXPIRED,
    )
)


def inspect_journal(path: Path, month: str) -> dict[str, Any]:
    """Read aggregate journal facts only. Never create, repair or settle a journal."""
    result: dict[str, Any] = {
        "status": "unavailable",
        "month": month,
        "initial_nusd": None,
        "charged_nusd": None,
        "unresolved_attempts": None,
        "limit_nusd": None,
        "pricing_version": None,
        "input_rate": None,
        "output_rate": None,
    }
    try:
        info = path.lstat()
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
        ):
            return result
        with closing(
            sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
        ) as db:
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN")
            config = db.execute(
                "SELECT limit_nusd, pricing, input_rate, output_rate FROM configuration WHERE id=1"
            ).fetchone()
            initial = db.execute(
                "SELECT initial_nusd FROM months WHERE month=?", (month,)
            ).fetchone()
            charged = db.execute(
                "SELECT COALESCE(SUM(charged_nusd),0) FROM attempts WHERE month=?",
                (month,),
            ).fetchone()
            unresolved = db.execute(
                "SELECT COUNT(*) FROM attempts WHERE outcome='reserved' OR "
                "(dispatched=1 AND outcome IN (?,?,?,?,?))",
                UNCERTAIN,
            ).fetchone()
            if (
                config is None
                or initial is None
                or charged is None
                or unresolved is None
            ):
                return result
            limit, pricing, input_rate, output_rate = config
            values = (
                limit,
                input_rate,
                output_rate,
                initial[0],
                charged[0],
                unresolved[0],
            )
            if any(type(value) is not int or value < 0 for value in values):
                return result
            if not isinstance(pricing, str) or not pricing or len(pricing) > 128:
                return result
            result.update(
                status="read",
                initial_nusd=initial[0],
                charged_nusd=charged[0],
                unresolved_attempts=unresolved[0],
                limit_nusd=limit,
                pricing_version=pricing,
                input_rate=input_rate,
                output_rate=output_rate,
            )
    except (OSError, sqlite3.Error, ValueError):
        pass
    return result


def preflight(
    decisions_path: Path, journal_path: Path, now: datetime
) -> dict[str, Any]:
    """Return an advisory report; no result from this function authorizes dispatch."""
    if now.tzinfo is None:
        raise ValueError("An aware clock is required")
    now = now.astimezone(UTC)
    planned = plan(decisions_path)
    decisions_bytes = _read(decisions_path)
    if _sha(decisions_bytes) != planned["decision_artifact_sha256"]:
        raise ValueError("Decisions changed during preflight")
    decisions = cast(dict[str, Any], _parse(decisions_bytes))
    spending = decisions["spending"]
    month = now.strftime("%Y-%m")
    journal = inspect_journal(journal_path, month)
    blockers = list(planned["blockers"])
    if spending["month"] != month:
        blockers.append("journal:current_month_not_bound")
    if journal["status"] != "read":
        blockers.append("journal:unavailable_or_missing_current_month")
    else:
        if journal["unresolved_attempts"]:
            blockers.append("journal:unresolved_attempts")
        if journal["limit_nusd"] != spending["monthly_cap_nusd"]:
            blockers.append("journal:monthly_limit_mismatch")
        if (
            journal["pricing_version"] != planned["pricing"]["version"]
            or journal["input_rate"] != planned["pricing"]["input_nusd_per_token"]
            or journal["output_rate"] != planned["pricing"]["output_nusd_per_token"]
        ):
            blockers.append("journal:pricing_mismatch")
    observed = spending["accounting_observed_at"]
    if observed is not None:
        snapshot = datetime.fromisoformat(observed.replace("Z", "+00:00"))
        if snapshot.astimezone(UTC) > now:
            blockers.append("spending:future_snapshot")
    # These are deliberately explicit until the live runner implements and checks
    # the final owner-approved source, journal, scope and run-level controls.
    blockers.extend(
        (
            "live_composition:not_implemented",
            "run_allowance:shared_enforcement_unverified",
            "spending_snapshot:freshness_and_external_spend_unverified",
            "source_and_run_authorization:current_binding_unverified",
        )
    )
    return {
        "schema_version": "azure-comparison-preflight.v1",
        "checked_at": now.isoformat(),
        "status": "blocked",
        "dispatch_authorized": False,
        "planning_binding": planned["binding"],
        "scheduled_attempts": len(planned["schedule"]),
        "projected_cost_ceiling_nusd": planned["projected_cost_ceiling_nusd"],
        "journal": journal,
        "blockers": sorted(set(blockers)),
        "limitations": [
            "Read-only planning evidence; journal estimates are not Azure billing.",
            "This report does not check credentials, provider connectivity or real source rights.",
            "No live comparison runner or paid call is invoked.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decisions", type=Path, default=DECISIONS)
    parser.add_argument("--journal", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = preflight(args.decisions, args.journal, datetime.now(UTC))
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        print(
            "Preflight failed: invalid inputs or unavailable planning data.",
            file=sys.stderr,
        )
        return 2
    print(_json(result).decode(), end="")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
