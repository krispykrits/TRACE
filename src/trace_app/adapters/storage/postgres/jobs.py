"""Transactional PostgreSQL investigation queue; no provider calls occur here."""

from __future__ import annotations

import hashlib
import json
import uuid
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row

from trace_app.evidence.models import format_utc
from trace_app.investigation.models import (
    Investigation,
    InvestigationRequest,
    StoreAccessError,
    StoreConflictError,
    StoreDependencyError,
    StoreInputError,
    StoreStateError,
    _identifier,
)
from trace_app.investigation.submission import InvestigationGrant


def _time(value: datetime | None) -> str | None:
    return format_utc(value) if value is not None else None


def _job(row: dict[str, Any]) -> Investigation:
    return Investigation(
        investigation_id=row["investigation_id"],
        request=InvestigationRequest(
            submission_key=row["submission_key"],
            service=row["service"],
            environment=row["environment"],
            access_scope=row["access_scope"],
            window_start=row["window_start"],
            window_end=row["window_end"],
            expires_at=row["expires_at"],
            max_attempts=row["max_attempts"],
        ),
        created_at=_time(row["created_at"]) or "",
        status=row["status"],
        assessment_status=row["assessment_status"],
        review_status=row["review_status"],
        attempt_count=row["attempt_count"],
        active_attempt_id=row["active_attempt_id"],
        lease_until=_time(row["lease_until"]),
        finished_at=_time(row["finished_at"]),
        failure_code=row["failure_code"],
    )


class PostgresJobs:
    """One short transaction per operation; connections must use TLS in deployment."""

    def __init__(self, dsn: str) -> None:
        if not dsn:
            raise ValueError("PostgreSQL connection configuration is required.")
        self._dsn = dsn

    @contextmanager
    def _connection(self) -> Iterator[Any]:
        try:
            with psycopg.connect(
                self._dsn, row_factory=dict_row, connect_timeout=5
            ) as connection:
                yield connection
        except psycopg.Error as error:
            raise StoreDependencyError(
                "Investigation storage is unavailable."
            ) from error

    def grant_for(self, tenant_id: str, object_id: str) -> InvestigationGrant:
        with self._connection() as connection:
            row = connection.execute(
                """SELECT access_scope, environment, services, actions
                FROM trace_principal_grants WHERE tenant_id=%s AND object_id=%s""",
                (tenant_id, object_id),
            ).fetchone()
            if row is None:
                raise StoreAccessError("Principal has no investigation grant.")
            return InvestigationGrant(
                row["access_scope"],
                row["environment"],
                frozenset(row["services"]),
                frozenset(row["actions"]),
            )

    def submit(self, request: InvestigationRequest, *, at: datetime) -> Investigation:
        # Database time is authoritative for all queue and lease transitions.
        if request.max_attempts != 1:
            raise StoreInputError("Hosted work is limited to one attempt.")
        if request.expires_at is not None:
            raise StoreInputError("Expiration is not supported by this queue yet.")
        digest = hashlib.sha256(
            json.dumps(asdict(request), sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        identity = uuid.uuid4().hex
        with self._connection() as connection:
            row = connection.execute(
                """INSERT INTO trace_jobs
                (investigation_id, access_scope, submission_key, request_hash, service,
                 environment, window_start, window_end, expires_at, max_attempts, status)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'queued')
                ON CONFLICT (access_scope, submission_key) DO NOTHING RETURNING *""",
                (
                    identity,
                    request.access_scope,
                    request.submission_key,
                    digest,
                    request.service,
                    request.environment,
                    request.window_start,
                    request.window_end,
                    request.expires_at,
                    request.max_attempts,
                ),
            ).fetchone()
            if row is None:
                row = connection.execute(
                    "SELECT * FROM trace_jobs WHERE access_scope=%s AND submission_key=%s",
                    (request.access_scope, request.submission_key),
                ).fetchone()
                if row is None or row["request_hash"] != digest:
                    raise StoreConflictError(
                        "Submission key conflicts with an existing request."
                    )
            return _job(row)

    def get_investigation(
        self, investigation_id: str, *, access_scope: str
    ) -> Investigation:
        _identifier("investigation_id", investigation_id)
        _identifier("access_scope", access_scope)
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM trace_jobs WHERE investigation_id=%s AND access_scope=%s",
                (investigation_id, access_scope),
            ).fetchone()
            if row is None:
                raise StoreAccessError("Investigation is not accessible.")
            return _job(row)

    def cancel(
        self, investigation_id: str, *, access_scope: str, at: datetime
    ) -> Investigation:
        _identifier("investigation_id", investigation_id)
        _identifier("access_scope", access_scope)
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM trace_jobs WHERE investigation_id=%s AND access_scope=%s FOR UPDATE",
                (investigation_id, access_scope),
            ).fetchone()
            if row is None:
                raise StoreAccessError("Investigation is not accessible.")
            if row["status"] == "cancelled":
                return _job(row)
            if row["status"] not in ("queued", "running"):
                raise StoreStateError("Investigation cannot be cancelled.")
            if row["active_attempt_id"] is not None:
                connection.execute(
                    "UPDATE trace_job_attempts SET outcome='cancelled', finished_at=clock_timestamp() WHERE attempt_id=%s",
                    (row["active_attempt_id"],),
                )
            row = connection.execute(
                """UPDATE trace_jobs SET status='cancelled', active_attempt_id=NULL,
                lease_until=NULL, finished_at=clock_timestamp() WHERE investigation_id=%s RETURNING *""",
                (investigation_id,),
            ).fetchone()
            return _job(row)

    def claim(self, *, lease_seconds: int) -> Investigation | None:
        if type(lease_seconds) is not int or not 1 <= lease_seconds <= 3600:
            raise StoreInputError("Invalid lease duration.")
        with self._connection() as connection:
            # Never replay an expired attempt: a provider call may have occurred.
            stale = connection.execute(
                """UPDATE trace_jobs SET status='failed', failure_code='outcome_unknown',
                finished_at=clock_timestamp(), active_attempt_id=NULL, lease_until=NULL
                WHERE status='running' AND lease_until <= clock_timestamp()
                RETURNING investigation_id"""
            ).fetchall()
            for item in stale:
                connection.execute(
                    """UPDATE trace_job_attempts SET outcome='interrupted', finished_at=clock_timestamp()
                    WHERE investigation_id=%s AND outcome='running'""",
                    (item["investigation_id"],),
                )
            row = connection.execute(
                """SELECT * FROM trace_jobs WHERE status='queued' ORDER BY created_at, investigation_id
                LIMIT 1 FOR UPDATE SKIP LOCKED"""
            ).fetchone()
            if row is None:
                return None
            attempt = connection.execute(
                """INSERT INTO trace_job_attempts (investigation_id, lease_until, outcome)
                VALUES (%s, clock_timestamp() + (%s * interval '1 second'), 'running') RETURNING *""",
                (row["investigation_id"], lease_seconds),
            ).fetchone()
            row = connection.execute(
                """UPDATE trace_jobs SET status='running', attempt_count=1, active_attempt_id=%s,
                lease_until=%s WHERE investigation_id=%s RETURNING *""",
                (
                    attempt["attempt_id"],
                    attempt["lease_until"],
                    row["investigation_id"],
                ),
            ).fetchone()
            return _job(row)

    def fail(self, job: Investigation, *, failure_code: str) -> None:
        _identifier("failure_code", failure_code)
        with self._connection() as connection:
            row = connection.execute(
                """UPDATE trace_jobs SET status='failed', failure_code=%s, finished_at=clock_timestamp(),
                active_attempt_id=NULL, lease_until=NULL WHERE investigation_id=%s AND status='running'
                AND active_attempt_id=%s AND lease_until > clock_timestamp() RETURNING investigation_id""",
                (failure_code, job.investigation_id, job.active_attempt_id),
            ).fetchone()
            if row is None:
                raise StoreStateError("Attempt is no longer active.")
            connection.execute(
                "UPDATE trace_job_attempts SET outcome='failed', finished_at=clock_timestamp() WHERE attempt_id=%s",
                (job.active_attempt_id,),
            )
