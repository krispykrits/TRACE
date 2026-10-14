"""Atomic execution ledger beside the existing investigation/attempt records."""

from __future__ import annotations

import json
import sqlite3
import stat
from collections.abc import Callable
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from trace_app.investigation.execution import (
    CallTicket,
    ExecutionIdentity,
    ExecutionPolicy,
    ExecutionRejected,
    ExecutionState,
)

EXECUTION_SCHEMA = (
    """CREATE TABLE execution_runs (
        investigation_id TEXT PRIMARY KEY REFERENCES investigations(investigation_id) ON DELETE CASCADE,
        policy TEXT NOT NULL, state TEXT NOT NULL
    )""",
    """CREATE TABLE execution_calls (
        call_id TEXT PRIMARY KEY,
        investigation_id TEXT NOT NULL REFERENCES investigations(investigation_id) ON DELETE CASCADE,
        metadata TEXT NOT NULL
    )""",
)


class SqliteExecutionLedger:
    """No independent state authority: check job, active attempt, lease and expiry atomically."""

    def __init__(self, path: Path) -> None:
        if path.is_symlink() or not path.is_file():
            raise ExecutionRejected("audit_unavailable")
        mode = path.stat().st_mode
        if not stat.S_ISREG(mode) or mode & 0o077:
            raise ExecutionRejected("audit_unavailable")
        self._path = path

    def apply(
        self,
        identity: ExecutionIdentity,
        policy: ExecutionPolicy,
        now: float,
        operation: Callable[[ExecutionState], dict[str, object] | None],
    ) -> dict[str, object] | None:
        policy_json = json.dumps(asdict(policy), sort_keys=True)
        try:
            # mode=rw prevents accidentally recreating a deleted job database.
            connection = sqlite3.connect(
                self._path.resolve().as_uri() + "?mode=rw", uri=True, timeout=5
            )
            try:
                connection.execute("PRAGMA foreign_keys=ON")
                connection.execute("BEGIN IMMEDIATE")
                job = connection.execute(
                    """SELECT status,active_attempt_id,lease_until,expires_at,created_at
                       FROM investigations WHERE investigation_id=? AND access_scope=?""",
                    (identity.investigation_id, identity.access_scope),
                ).fetchone()
                if job is None:
                    raise ExecutionRejected("attempt_not_active")
                if job[0] == "running" and job[1] != identity.attempt_id:
                    # A stale worker cannot poison the current worker's shared budget.
                    raise ExecutionRejected("attempt_not_active")
                row = connection.execute(
                    "SELECT policy,state FROM execution_runs WHERE investigation_id=?",
                    (identity.investigation_id,),
                ).fetchone()
                if row is None:
                    if job[0] != "running":
                        raise ExecutionRejected("attempt_not_active")
                    state = ExecutionState(
                        now, datetime.fromisoformat(job[4]).timestamp(), now
                    )
                else:
                    if row[0] != policy_json:
                        raise ExecutionRejected("configuration_changed")
                    data = json.loads(row[1])
                    if set(data) != set(ExecutionState.__dataclass_fields__):
                        raise ExecutionRejected("audit_unavailable")
                    if data["active"] is not None:
                        data["active"] = CallTicket(**data["active"])
                    state = ExecutionState(**data)
                deadlines = [
                    datetime.fromisoformat(value).timestamp()
                    for value in (job[2], job[3])
                    if value is not None
                ]
                state.authority_deadline = min(deadlines) if deadlines else None
                if job[0] == "cancelled":
                    state.stop_reason = "cancelled"
                elif job[0] == "expired" or any(
                    value is not None
                    and datetime.fromisoformat(value).timestamp() <= now
                    for value in (job[2], job[3])
                ):
                    state.stop_reason = state.stop_reason or "expired"
                elif job[0] != "running" or job[1] != identity.attempt_id:
                    state.stop_reason = state.stop_reason or "attempt_not_active"
                record = operation(state)
                connection.execute(
                    """INSERT INTO execution_runs VALUES(?,?,?) ON CONFLICT(investigation_id)
                       DO UPDATE SET state=excluded.state""",
                    (
                        identity.investigation_id,
                        policy_json,
                        json.dumps(asdict(state), allow_nan=False),
                    ),
                )
                if record is not None:
                    previous = connection.execute(
                        "SELECT metadata FROM execution_calls WHERE call_id=?",
                        (record["call_id"],),
                    ).fetchone()
                    merged = {**(json.loads(previous[0]) if previous else {}), **record}
                    connection.execute(
                        """INSERT INTO execution_calls VALUES(?,?,?) ON CONFLICT(call_id)
                           DO UPDATE SET metadata=excluded.metadata""",
                        (
                            record["call_id"],
                            identity.investigation_id,
                            json.dumps(merged, allow_nan=False),
                        ),
                    )
                connection.commit()
                return record
            finally:
                connection.close()
        except ExecutionRejected:
            raise
        except (OSError, sqlite3.Error, ValueError, KeyError, TypeError):
            raise ExecutionRejected("audit_unavailable") from None
