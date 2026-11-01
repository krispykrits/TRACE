"""Shared transaction and attempt fencing for investigation execution limits."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import asdict
from typing import Any

import psycopg
from psycopg.rows import dict_row

from trace_app.investigation.execution import (
    CallTicket,
    ExecutionIdentity,
    ExecutionPolicy,
    ExecutionRejected,
    ExecutionState,
)


class PostgresExecutionLedger:
    """Serialize execution state with the durable job and its active attempt."""

    def __init__(self, dsn: str) -> None:
        if not dsn:
            raise ValueError("PostgreSQL connection configuration is required.")
        self._dsn = dsn

    def apply(
        self,
        identity: ExecutionIdentity,
        policy: ExecutionPolicy,
        now: float,
        operation: Callable[[ExecutionState], dict[str, object] | None],
    ) -> dict[str, object] | None:
        policy_json = json.dumps(asdict(policy), sort_keys=True)
        try:
            with psycopg.connect(
                self._dsn, row_factory=dict_row, connect_timeout=5
            ) as connection:
                job = connection.execute(
                    """SELECT status, active_attempt_id, lease_until, created_at,
                    submitted_tenant, submitted_object, access_scope, service, environment,
                    clock_timestamp() AS database_now FROM trace_jobs
                    WHERE investigation_id=%s AND access_scope=%s FOR UPDATE""",
                    (identity.investigation_id, identity.access_scope),
                ).fetchone()
                if job is None or (
                    job["status"] == "running"
                    and job["active_attempt_id"] != identity.attempt_id
                ):
                    raise ExecutionRejected("attempt_not_active")
                grant = connection.execute(
                    """SELECT access_scope, environment, services, actions
                    FROM trace_principal_grants WHERE tenant_id=%s AND object_id=%s FOR SHARE""",
                    (job["submitted_tenant"], job["submitted_object"]),
                ).fetchone()
                if (
                    grant is None
                    or grant["access_scope"] != job["access_scope"]
                    or grant["environment"] != job["environment"]
                    or job["service"] not in grant["services"]
                    or "submit" not in grant["actions"]
                ):
                    raise ExecutionRejected("attempt_not_active")
                row = connection.execute(
                    "SELECT policy, state FROM trace_execution_runs WHERE investigation_id=%s",
                    (identity.investigation_id,),
                ).fetchone()
                if row is None:
                    if job["status"] != "running":
                        raise ExecutionRejected("attempt_not_active")
                    state = ExecutionState(now, job["created_at"].timestamp(), now)
                else:
                    if row["policy"] != policy_json:
                        raise ExecutionRejected("configuration_changed")
                    data: dict[str, Any] = json.loads(row["state"])
                    if set(data) != set(ExecutionState.__dataclass_fields__):
                        raise ExecutionRejected("audit_unavailable")
                    if data["active"] is not None:
                        data["active"] = CallTicket(**data["active"])
                    state = ExecutionState(**data)
                lease = job["lease_until"]
                state.authority_deadline = lease.timestamp() if lease else None
                if job["status"] == "cancelled":
                    state.stop_reason = "cancelled"
                elif lease is not None and lease <= job["database_now"]:
                    state.stop_reason = state.stop_reason or "expired"
                elif (
                    job["status"] != "running"
                    or job["active_attempt_id"] != identity.attempt_id
                ):
                    state.stop_reason = state.stop_reason or "attempt_not_active"
                record = operation(state)
                connection.execute(
                    """INSERT INTO trace_execution_runs VALUES (%s,%s,%s)
                    ON CONFLICT (investigation_id) DO UPDATE SET state=excluded.state""",
                    (
                        identity.investigation_id,
                        policy_json,
                        json.dumps(asdict(state), allow_nan=False),
                    ),
                )
                if record is not None:
                    previous = connection.execute(
                        "SELECT metadata FROM trace_execution_calls WHERE call_id=%s",
                        (record["call_id"],),
                    ).fetchone()
                    merged = {
                        **(json.loads(previous["metadata"]) if previous else {}),
                        **record,
                    }
                    connection.execute(
                        """INSERT INTO trace_execution_calls VALUES (%s,%s,%s)
                        ON CONFLICT (call_id) DO UPDATE SET metadata=excluded.metadata""",
                        (
                            record["call_id"],
                            identity.investigation_id,
                            json.dumps(merged, allow_nan=False),
                        ),
                    )
                return record
        except ExecutionRejected:
            raise
        except (psycopg.Error, ValueError, KeyError, TypeError):
            raise ExecutionRejected("audit_unavailable") from None
