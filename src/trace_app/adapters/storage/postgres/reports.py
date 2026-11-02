"""Private report reader for use behind the current source-authorization policy."""

from __future__ import annotations

import json

from trace_app.adapters.storage.postgres.jobs import PostgresJobs, _job, _time
from trace_app.investigation.models import (
    Attempt,
    StoreAccessError,
    StoreDependencyError,
    _identifier,
)
from trace_app.investigation.reports import SavedInvestigation


class PostgresReportReader:
    """Read bounded stored artifacts; callers must enforce source and review rights."""

    def __init__(self, dsn: str, *, principal: tuple[str, str]) -> None:
        self._jobs = PostgresJobs(dsn, principal=principal)

    def load(self, investigation_id: str, *, access_scope: str) -> SavedInvestigation:
        _identifier("investigation_id", investigation_id)
        _identifier("access_scope", access_scope)
        with self._jobs._connection() as connection:
            job = connection.execute(
                "SELECT * FROM trace_jobs WHERE investigation_id=%s AND access_scope=%s FOR SHARE",
                (investigation_id, access_scope),
            ).fetchone()
            if job is None:
                raise StoreAccessError("Investigation is not accessible.")
            self._jobs._authorize(
                connection,
                access_scope=access_scope,
                service=job["service"],
                environment=job["environment"],
                action="read",
            )
            rows = connection.execute(
                """SELECT artifact_id, role, metadata, body FROM trace_workflow_artifacts
                WHERE investigation_id=%s ORDER BY ordinal LIMIT 11""",
                (investigation_id,),
            ).fetchall()
            attempt_rows = connection.execute(
                "SELECT * FROM trace_job_attempts WHERE investigation_id=%s ORDER BY attempt_id LIMIT 2",
                (investigation_id,),
            ).fetchall()
            if (
                len(rows) > 10
                or len(attempt_rows) > 1
                or any(
                    len(row["metadata"].encode()) + len(row["body"].encode())
                    > 1_000_000
                    for row in rows
                )
            ):
                raise StoreDependencyError("Stored report exceeds its bounds.")
            try:
                artifacts = tuple(
                    {
                        "artifact_id": row["artifact_id"],
                        "role": row["role"],
                        "metadata": json.loads(row["metadata"]),
                        "body": json.loads(row["body"]),
                    }
                    for row in rows
                )
                if any(
                    not isinstance(item["metadata"], dict)
                    or not isinstance(item["body"], dict)
                    for item in artifacts
                ):
                    raise ValueError("Invalid stored artifact.")
                attempts = tuple(
                    Attempt(
                        attempt_id=row["attempt_id"],
                        investigation_id=row["investigation_id"],
                        attempt_number=1,
                        started_at=_time(row["started_at"]) or "",
                        lease_until=_time(row["lease_until"]) or "",
                        finished_at=_time(row["finished_at"]),
                        outcome=row["outcome"],
                        failure_code=job["failure_code"]
                        if row["outcome"] in ("failed", "interrupted")
                        else None,
                    )
                    for row in attempt_rows
                )
                return SavedInvestigation(_job(job), attempts, artifacts)
            except (ValueError, TypeError, KeyError):
                raise StoreDependencyError("Stored investigation is invalid.") from None
