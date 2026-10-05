"""SQLite adapter for bounded operational snapshots and recoverable local jobs."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sqlite3
import stat
import uuid
from contextlib import contextmanager
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator, Literal

from trace_app.evidence import (
    EVIDENCE_SCHEMA_VERSION,
    EvidenceRecord,
    SourceAvailability,
    format_utc,
)
from trace_app.investigation_state import (
    Attempt,
    DeploymentPayload,
    EvidenceEntry,
    EvidencePayload,
    EvidenceSnapshot,
    Investigation,
    InvestigationRequest,
    LogPayload,
    MetricPayload,
    StoreAccessError,
    StoreConflictError,
    StoreDependencyError,
    StoreInputError,
    StoreSchemaError,
    StoreStateError,
    _identifier,
)

_SCHEMA_VERSION = 1
_LOG = logging.getLogger("trace_app.persistence")
_SCHEMA = (
    """CREATE TABLE investigations (
        investigation_id TEXT PRIMARY KEY,
        submission_key TEXT NOT NULL,
        request_hash TEXT NOT NULL,
        service TEXT NOT NULL,
        environment TEXT NOT NULL,
        access_scope TEXT NOT NULL,
        window_start TEXT NOT NULL,
        window_end TEXT NOT NULL,
        expires_at TEXT,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN
            ('queued','running','completed','failed','cancelled','expired')),
        assessment_status TEXT NOT NULL CHECK(assessment_status IN
            ('pending','supported','abstained')),
        review_status TEXT NOT NULL CHECK(review_status IN
            ('pending','unreviewed','approved','rejected')),
        attempt_count INTEGER NOT NULL DEFAULT 0,
        max_attempts INTEGER NOT NULL CHECK(max_attempts > 0),
        active_attempt_id INTEGER,
        lease_until TEXT,
        finished_at TEXT,
        failure_code TEXT,
        UNIQUE(access_scope, submission_key)
    )""",
    """CREATE TABLE attempts (
        attempt_id INTEGER PRIMARY KEY AUTOINCREMENT,
        investigation_id TEXT NOT NULL REFERENCES investigations(investigation_id)
            ON DELETE CASCADE,
        attempt_number INTEGER NOT NULL,
        started_at TEXT NOT NULL,
        lease_until TEXT NOT NULL,
        finished_at TEXT,
        outcome TEXT NOT NULL CHECK(outcome IN
            ('running','completed','failed','interrupted','cancelled','expired')),
        failure_code TEXT,
        UNIQUE(investigation_id, attempt_number)
    )""",
    """CREATE TABLE snapshots (
        investigation_id TEXT PRIMARY KEY REFERENCES investigations(investigation_id)
            ON DELETE CASCADE,
        schema_version TEXT NOT NULL,
        window_start TEXT NOT NULL,
        window_end TEXT NOT NULL,
        sources_json TEXT NOT NULL,
        fingerprint TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE evidence (
        investigation_id TEXT NOT NULL REFERENCES snapshots(investigation_id)
            ON DELETE CASCADE,
        evidence_id TEXT NOT NULL,
        ordinal INTEGER NOT NULL,
        kind TEXT NOT NULL CHECK(kind IN ('log','metric','deployment')),
        record_json TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        source_record_id TEXT NOT NULL,
        source_revision TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        PRIMARY KEY(investigation_id, evidence_id),
        UNIQUE(investigation_id, ordinal),
        UNIQUE(investigation_id, source_record_id, source_revision)
    )""",
    """CREATE TABLE deletion_audit (
        investigation_id TEXT PRIMARY KEY,
        access_scope TEXT NOT NULL,
        deleted_at TEXT NOT NULL,
        evidence_count INTEGER NOT NULL
    )""",
    "CREATE INDEX evidence_observed_idx ON evidence(investigation_id, observed_at, evidence_id)",
    "CREATE INDEX investigations_queue_idx ON investigations(status, created_at, investigation_id)",
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _payload(kind: str, serialized: str) -> EvidencePayload:
    data = json.loads(serialized)
    if not isinstance(data, dict):
        raise StoreSchemaError("Stored evidence payload is invalid.")
    if kind == "log" and set(data) == {"message"}:
        return LogPayload(message=data["message"])
    if kind == "metric" and set(data) == {"name", "value", "unit"}:
        return MetricPayload(name=data["name"], value=data["value"], unit=data["unit"])
    if kind == "deployment" and set(data) == {"revision", "phase"}:
        return DeploymentPayload(revision=data["revision"], phase=data["phase"])
    raise StoreSchemaError("Stored evidence payload kind or fields are invalid.")


def _at(value: datetime) -> str:
    if not isinstance(value, datetime):
        raise StoreInputError("at must be a UTC datetime.")
    try:
        format_utc(value)
    except ValueError as error:
        raise StoreInputError(f"at: {error}") from error
    return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class SQLiteInvestigationStore:
    """One-process SQLite adapter. Caller supplies a trusted access scope."""

    def __init__(
        self,
        path: Path,
        *,
        max_records: int = 1_000,
        max_snapshot_bytes: int = 1_000_000,
    ) -> None:
        if type(max_records) is not int or max_records <= 0:
            raise StoreInputError("max_records must be a positive integer.")
        if type(max_snapshot_bytes) is not int or max_snapshot_bytes <= 0:
            raise StoreInputError("max_snapshot_bytes must be a positive integer.")
        self.max_records = max_records
        self.max_snapshot_bytes = max_snapshot_bytes
        self.path = Path(path)
        if self.path.is_symlink():
            raise StoreInputError("path must not be a symbolic link.")
        if not self.path.parent.is_dir():
            raise StoreInputError("path parent directory must exist.")
        if self.path.exists():
            mode = self.path.stat().st_mode
            if not stat.S_ISREG(mode) or mode & 0o077:
                raise StoreInputError(
                    "path must be a private regular file (mode 0600)."
                )
        else:
            descriptor = os.open(
                self.path, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600
            )
            os.close(descriptor)
        self._db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        self._db.execute("PRAGMA secure_delete = ON")
        self.initialize()

    def __enter__(self) -> SQLiteInvestigationStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._db.close()

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        self._db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self._db.execute("COMMIT")
        except BaseException:
            if self._db.in_transaction:
                self._db.execute("ROLLBACK")
            raise

    def initialize(self) -> None:
        with self._transaction():
            version = self._db.execute("PRAGMA user_version").fetchone()[0]
            if version > _SCHEMA_VERSION:
                raise StoreSchemaError(
                    f"SQLite schema version {version} is newer than supported version {_SCHEMA_VERSION}."
                )
            if version == 0:
                for statement in _SCHEMA:
                    self._db.execute(statement)
                self._db.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
            elif version != _SCHEMA_VERSION:
                raise StoreSchemaError(
                    f"SQLite schema version {version} is unsupported."
                )

    def _investigation(self, row: sqlite3.Row) -> Investigation:
        request = InvestigationRequest(
            submission_key=row["submission_key"],
            service=row["service"],
            environment=row["environment"],
            access_scope=row["access_scope"],
            window_start=row["window_start"],
            window_end=row["window_end"],
            expires_at=row["expires_at"],
            max_attempts=row["max_attempts"],
        )
        return Investigation(
            investigation_id=row["investigation_id"],
            request=request,
            created_at=row["created_at"],
            status=row["status"],
            assessment_status=row["assessment_status"],
            review_status=row["review_status"],
            attempt_count=row["attempt_count"],
            active_attempt_id=row["active_attempt_id"],
            lease_until=row["lease_until"],
            finished_at=row["finished_at"],
            failure_code=row["failure_code"],
        )

    def _scoped_row(self, investigation_id: str, access_scope: str) -> sqlite3.Row:
        _identifier("investigation_id", investigation_id)
        _identifier("access_scope", access_scope)
        try:
            row = self._db.execute(
                "SELECT * FROM investigations WHERE investigation_id = ? AND access_scope = ?",
                (investigation_id, access_scope),
            ).fetchone()
        except sqlite3.Error as error:
            raise StoreDependencyError("Evidence storage is unavailable.") from error
        if row is None:
            raise StoreAccessError(
                "Investigation is absent or outside the access scope."
            )
        return row

    def get_investigation(
        self, investigation_id: str, *, access_scope: str
    ) -> Investigation:
        row = self._scoped_row(investigation_id, access_scope)
        try:
            return self._investigation(row)
        except (ValueError, KeyError, TypeError) as error:
            raise StoreDependencyError("Stored investigation is invalid.") from error

    def submit(self, request: InvestigationRequest, *, at: datetime) -> Investigation:
        timestamp = _at(at)
        if request.environment not in ("development", "test"):
            raise StoreInputError(
                "environment must be development or test for local fixtures."
            )
        request_hash = _sha(_json(asdict(request)))
        with self._transaction():
            row = self._db.execute(
                "SELECT * FROM investigations WHERE access_scope = ? AND submission_key = ?",
                (request.access_scope, request.submission_key),
            ).fetchone()
            if row is not None:
                if row["request_hash"] != request_hash:
                    raise StoreConflictError(
                        "submission_key conflicts with an existing request."
                    )
                return self._investigation(row)
            if request.expires_at is not None and request.expires_at <= timestamp:
                raise StoreInputError("expires_at must be later than submission time.")
            investigation_id = uuid.uuid4().hex
            self._db.execute(
                """INSERT INTO investigations (
                    investigation_id, submission_key, request_hash, service, environment,
                    access_scope, window_start, window_end, expires_at, created_at,
                    max_attempts, status, assessment_status, review_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued', 'pending', 'pending')""",
                (
                    investigation_id,
                    request.submission_key,
                    request_hash,
                    request.service,
                    request.environment,
                    request.access_scope,
                    request.window_start,
                    request.window_end,
                    request.expires_at,
                    timestamp,
                    request.max_attempts,
                ),
            )
            row = self._db.execute(
                "SELECT * FROM investigations WHERE investigation_id = ?",
                (investigation_id,),
            ).fetchone()
        _LOG.info(
            "Investigation submitted.",
            extra={
                "event": "investigation.submitted",
                "investigation_id": investigation_id,
            },
        )
        return self._investigation(row)

    def ingest_snapshot(
        self,
        investigation_id: str,
        snapshot: EvidenceSnapshot,
        *,
        access_scope: str,
        at: datetime,
    ) -> int:
        timestamp = _at(at)
        if len(snapshot.entries) > self.max_records:
            raise StoreInputError("entries exceeds max_records.")
        bundle = snapshot.to_bundle()
        serialized = _json(
            {
                "bundle": bundle.to_dict(),
                "entries": [
                    {"kind": entry.kind, "payload": asdict(entry.payload)}
                    for entry in snapshot.entries
                ],
            }
        )
        if len(serialized.encode("utf-8")) > self.max_snapshot_bytes:
            raise StoreInputError("snapshot exceeds max_snapshot_bytes.")
        logical = bundle.to_dict()
        logical["records"] = [
            {
                key: value
                for key, value in entry.record.to_dict().items()
                if key != "collected_at"
            }
            for entry in snapshot.entries
        ]
        fingerprint = _sha(
            _json(
                {
                    "bundle": logical,
                    "entries": [
                        {"kind": entry.kind, "payload": asdict(entry.payload)}
                        for entry in snapshot.entries
                    ],
                }
            )
        )
        with self._transaction():
            investigation = self._scoped_row(investigation_id, access_scope)
            if (
                snapshot.window_start != investigation["window_start"]
                or snapshot.window_end != investigation["window_end"]
            ):
                raise StoreInputError("query_window differs from investigation window.")
            if any(
                entry.record.environment != investigation["environment"]
                for entry in snapshot.entries
            ):
                raise StoreInputError(
                    "environment differs from investigation environment."
                )
            if any(
                entry.record.access_classification != "synthetic_public"
                for entry in snapshot.entries
            ):
                raise StoreInputError(
                    "access_classification requires an authorized source adapter."
                )
            existing = self._db.execute(
                "SELECT fingerprint FROM snapshots WHERE investigation_id = ?",
                (investigation_id,),
            ).fetchone()
            if existing is not None:
                if existing["fingerprint"] != fingerprint:
                    raise StoreConflictError(
                        "Snapshot conflicts with existing evidence for this investigation."
                    )
                return 0
            if investigation["status"] not in ("queued", "running"):
                raise StoreStateError(
                    "Evidence can only be ingested for an active investigation."
                )
            self._db.execute(
                """INSERT INTO snapshots (
                    investigation_id, schema_version, window_start, window_end,
                    sources_json, fingerprint, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    investigation_id,
                    EVIDENCE_SCHEMA_VERSION,
                    snapshot.window_start,
                    snapshot.window_end,
                    _json([source.to_dict() for source in snapshot.sources]),
                    fingerprint,
                    timestamp,
                ),
            )
            for index, entry in enumerate(snapshot.entries):
                record = entry.record
                self._db.execute(
                    """INSERT INTO evidence (
                        investigation_id, evidence_id, ordinal, kind, record_json,
                        payload_json, source_record_id, source_revision, observed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        investigation_id,
                        record.evidence_id,
                        index,
                        entry.kind,
                        _json(record.to_dict()),
                        _json(asdict(entry.payload)),
                        record.source_record_id,
                        record.source_revision,
                        record.observed_at,
                    ),
                )
        _LOG.info(
            "Evidence snapshot ingested.",
            extra={
                "event": "evidence.ingested",
                "investigation_id": investigation_id,
                "evidence_count": len(snapshot.entries),
            },
        )
        return len(snapshot.entries)

    def get_snapshot(
        self, investigation_id: str, *, access_scope: str
    ) -> EvidenceSnapshot:
        self._scoped_row(investigation_id, access_scope)
        try:
            row = self._db.execute(
                "SELECT * FROM snapshots WHERE investigation_id = ?",
                (investigation_id,),
            ).fetchone()
            if row is None:
                raise StoreAccessError(
                    "Evidence snapshot is absent or outside the access scope."
                )
            if row["schema_version"] != EVIDENCE_SCHEMA_VERSION:
                raise StoreSchemaError("Evidence schema version is unsupported.")
            count = self._db.execute(
                "SELECT COUNT(*) FROM evidence WHERE investigation_id = ?",
                (investigation_id,),
            ).fetchone()[0]
            if count > self.max_records:
                raise StoreDependencyError(
                    "Stored evidence exceeds the configured read bound."
                )
            rows = self._db.execute(
                "SELECT * FROM evidence WHERE investigation_id = ? ORDER BY ordinal",
                (investigation_id,),
            ).fetchall()
        except sqlite3.Error as error:
            raise StoreDependencyError("Evidence storage is unavailable.") from error
        try:
            sources = tuple(
                SourceAvailability(
                    source=value["source"],
                    status=value["status"],
                    reason=value["reason"],
                )
                for value in json.loads(row["sources_json"])
            )
            entries = tuple(
                EvidenceEntry(
                    kind=value["kind"],
                    record=EvidenceRecord.from_dict(json.loads(value["record_json"])),
                    payload=_payload(value["kind"], value["payload_json"]),
                )
                for value in rows
            )
            return EvidenceSnapshot(
                entries=entries,
                window_start=row["window_start"],
                window_end=row["window_end"],
                sources=sources,
            )
        except (ValueError, KeyError, TypeError, AttributeError) as error:
            raise StoreDependencyError("Stored evidence is invalid.") from error

    def get_evidence(
        self, investigation_id: str, evidence_id: str, *, access_scope: str
    ) -> EvidenceEntry:
        self._scoped_row(investigation_id, access_scope)
        _identifier("evidence_id", evidence_id)
        row = self._db.execute(
            "SELECT kind, record_json, payload_json FROM evidence WHERE investigation_id = ? AND evidence_id = ?",
            (investigation_id, evidence_id),
        ).fetchone()
        if row is None:
            raise StoreAccessError("Evidence is absent or outside the access scope.")
        return EvidenceEntry(
            kind=row["kind"],
            record=EvidenceRecord.from_dict(json.loads(row["record_json"])),
            payload=_payload(row["kind"], row["payload_json"]),
        )

    def _recover_locked(self, timestamp: str) -> int:
        expired = self._db.execute(
            """SELECT investigation_id, active_attempt_id FROM investigations
               WHERE status IN ('queued','running') AND expires_at IS NOT NULL
               AND expires_at <= ?""",
            (timestamp,),
        ).fetchall()
        for row in expired:
            if row["active_attempt_id"] is not None:
                self._db.execute(
                    """UPDATE attempts SET outcome='expired', finished_at=?
                       WHERE attempt_id=? AND outcome='running'""",
                    (timestamp, row["active_attempt_id"]),
                )
            self._db.execute(
                """UPDATE investigations SET status='expired', active_attempt_id=NULL,
                   lease_until=NULL, finished_at=? WHERE investigation_id=?""",
                (timestamp, row["investigation_id"]),
            )
        interrupted = self._db.execute(
            """SELECT investigation_id, active_attempt_id, attempt_count, max_attempts
               FROM investigations WHERE status='running' AND lease_until <= ?""",
            (timestamp,),
        ).fetchall()
        for row in interrupted:
            self._db.execute(
                """UPDATE attempts SET outcome='interrupted', finished_at=?,
                   failure_code='lease_expired' WHERE attempt_id=? AND outcome='running'""",
                (timestamp, row["active_attempt_id"]),
            )
            exhausted = row["attempt_count"] >= row["max_attempts"]
            self._db.execute(
                """UPDATE investigations SET status=?, active_attempt_id=NULL,
                   lease_until=NULL, finished_at=?, failure_code='lease_expired'
                   WHERE investigation_id=?""",
                (
                    "failed" if exhausted else "queued",
                    timestamp if exhausted else None,
                    row["investigation_id"],
                ),
            )
        exhausted = self._db.execute(
            """UPDATE investigations SET status='failed', finished_at=?,
               failure_code='attempt_limit'
               WHERE status='queued' AND attempt_count >= max_attempts""",
            (timestamp,),
        ).rowcount
        return len(expired) + len(interrupted) + exhausted

    def recover(self, *, at: datetime) -> int:
        timestamp = _at(at)
        with self._transaction():
            count = self._recover_locked(timestamp)
        if count:
            _LOG.warning(
                "Investigations recovered after expiry or interruption.",
                extra={"event": "investigation.recovered", "count": count},
            )
        return count

    def claim_next(
        self,
        *,
        at: datetime,
        lease_seconds: int = 30,
    ) -> Investigation | None:
        timestamp = _at(at)
        if type(lease_seconds) is not int or lease_seconds <= 0:
            raise StoreInputError("lease_seconds must be a positive integer.")
        lease_until = _at(at + timedelta(seconds=lease_seconds))
        with self._transaction():
            self._recover_locked(timestamp)
            row = self._db.execute(
                """SELECT * FROM investigations WHERE status='queued'
                   AND attempt_count < max_attempts
                   AND (expires_at IS NULL OR expires_at > ?)
                   AND created_at <= ?
                   ORDER BY created_at, investigation_id LIMIT 1""",
                (timestamp, timestamp),
            ).fetchone()
            if row is None:
                return None
            attempt_number = row["attempt_count"] + 1
            cursor = self._db.execute(
                """INSERT INTO attempts (
                    investigation_id, attempt_number, started_at, lease_until, outcome
                ) VALUES (?, ?, ?, ?, 'running')""",
                (row["investigation_id"], attempt_number, timestamp, lease_until),
            )
            self._db.execute(
                """UPDATE investigations SET status='running', attempt_count=?,
                   active_attempt_id=?, lease_until=?, finished_at=NULL
                   WHERE investigation_id=?""",
                (
                    attempt_number,
                    cursor.lastrowid,
                    lease_until,
                    row["investigation_id"],
                ),
            )
            claimed = self._db.execute(
                "SELECT * FROM investigations WHERE investigation_id=?",
                (row["investigation_id"],),
            ).fetchone()
        _LOG.info(
            "Investigation claimed.",
            extra={
                "event": "investigation.claimed",
                "investigation_id": claimed["investigation_id"],
                "attempt_id": claimed["active_attempt_id"],
            },
        )
        return self._investigation(claimed)

    def _active(
        self,
        investigation_id: str,
        access_scope: str,
        attempt_id: int,
        timestamp: str,
    ) -> sqlite3.Row:
        row = self._scoped_row(investigation_id, access_scope)
        if row["status"] != "running" or row["active_attempt_id"] != attempt_id:
            raise StoreStateError("Attempt is no longer active for this investigation.")
        started_at = self._db.execute(
            "SELECT started_at FROM attempts WHERE attempt_id=?", (attempt_id,)
        ).fetchone()["started_at"]
        if timestamp < started_at:
            raise StoreInputError("at must not precede attempt start.")
        if row["lease_until"] <= timestamp:
            raise StoreStateError("Attempt lease has expired; recover before retry.")
        if row["expires_at"] is not None and row["expires_at"] <= timestamp:
            raise StoreStateError("Investigation has expired; recover before retry.")
        return row

    def complete(
        self,
        investigation_id: str,
        attempt_id: int,
        *,
        access_scope: str,
        assessment_status: Literal["supported", "abstained"],
        at: datetime,
    ) -> Investigation:
        timestamp = _at(at)
        if assessment_status not in ("supported", "abstained"):
            raise StoreInputError("assessment_status must be supported or abstained.")
        with self._transaction():
            self._active(investigation_id, access_scope, attempt_id, timestamp)
            snapshot = self._db.execute(
                "SELECT 1 FROM snapshots WHERE investigation_id=?",
                (investigation_id,),
            ).fetchone()
            if snapshot is None:
                raise StoreStateError(
                    "An evidence snapshot is required before completion."
                )
            if assessment_status == "supported":
                count = self._db.execute(
                    "SELECT COUNT(*) FROM evidence WHERE investigation_id=?",
                    (investigation_id,),
                ).fetchone()[0]
                if count == 0:
                    raise StoreStateError(
                        "Supported assessment requires observed evidence."
                    )
            self._db.execute(
                """UPDATE attempts SET outcome='completed', finished_at=?
                   WHERE attempt_id=?""",
                (timestamp, attempt_id),
            )
            self._db.execute(
                """UPDATE investigations SET status='completed', assessment_status=?,
                   review_status='unreviewed', active_attempt_id=NULL,
                   lease_until=NULL, finished_at=?, failure_code=NULL
                   WHERE investigation_id=?""",
                (assessment_status, timestamp, investigation_id),
            )
        _LOG.info(
            "Investigation completed.",
            extra={
                "event": "investigation.completed",
                "investigation_id": investigation_id,
                "assessment_status": assessment_status,
            },
        )
        return self.get_investigation(investigation_id, access_scope=access_scope)

    def fail_attempt(
        self,
        investigation_id: str,
        attempt_id: int,
        *,
        access_scope: str,
        failure_code: str,
        retry: bool,
        at: datetime,
    ) -> Investigation:
        timestamp = _at(at)
        _identifier("failure_code", failure_code)
        if type(retry) is not bool:
            raise StoreInputError("retry must be a boolean.")
        with self._transaction():
            row = self._active(investigation_id, access_scope, attempt_id, timestamp)
            queued = retry and row["attempt_count"] < row["max_attempts"]
            self._db.execute(
                """UPDATE attempts SET outcome='failed', finished_at=?, failure_code=?
                   WHERE attempt_id=?""",
                (timestamp, failure_code, attempt_id),
            )
            self._db.execute(
                """UPDATE investigations SET status=?, active_attempt_id=NULL,
                   lease_until=NULL, finished_at=?, failure_code=?
                   WHERE investigation_id=?""",
                (
                    "queued" if queued else "failed",
                    None if queued else timestamp,
                    failure_code,
                    investigation_id,
                ),
            )
        _LOG.warning(
            "Investigation attempt failed.",
            extra={
                "event": "investigation.attempt_failed",
                "investigation_id": investigation_id,
                "retry_queued": queued,
                "failure_code": failure_code,
            },
        )
        return self.get_investigation(investigation_id, access_scope=access_scope)

    def cancel(
        self, investigation_id: str, *, access_scope: str, at: datetime
    ) -> Investigation:
        timestamp = _at(at)
        with self._transaction():
            row = self._scoped_row(investigation_id, access_scope)
            if row["status"] == "cancelled":
                return self._investigation(row)
            if row["status"] not in ("queued", "running"):
                raise StoreStateError(
                    "Only queued or running investigations can be cancelled."
                )
            if row["active_attempt_id"] is not None:
                self._db.execute(
                    """UPDATE attempts SET outcome='cancelled', finished_at=?
                       WHERE attempt_id=?""",
                    (timestamp, row["active_attempt_id"]),
                )
            self._db.execute(
                """UPDATE investigations SET status='cancelled', active_attempt_id=NULL,
                   lease_until=NULL, finished_at=? WHERE investigation_id=?""",
                (timestamp, investigation_id),
            )
        _LOG.info(
            "Investigation cancelled.",
            extra={
                "event": "investigation.cancelled",
                "investigation_id": investigation_id,
            },
        )
        return self.get_investigation(investigation_id, access_scope=access_scope)

    def review(
        self,
        investigation_id: str,
        *,
        access_scope: str,
        decision: Literal["approved", "rejected"],
    ) -> Investigation:
        if decision not in ("approved", "rejected"):
            raise StoreInputError("decision must be approved or rejected.")
        with self._transaction():
            row = self._scoped_row(investigation_id, access_scope)
            if row["status"] != "completed":
                raise StoreStateError("Only completed assessments can be reviewed.")
            if row["review_status"] not in ("unreviewed", decision):
                raise StoreConflictError(
                    "Review decision conflicts with existing review."
                )
            self._db.execute(
                "UPDATE investigations SET review_status=? WHERE investigation_id=?",
                (decision, investigation_id),
            )
        _LOG.info(
            "Assessment review recorded.",
            extra={
                "event": "investigation.reviewed",
                "investigation_id": investigation_id,
                "decision": decision,
            },
        )
        return self.get_investigation(investigation_id, access_scope=access_scope)

    def list_attempts(
        self, investigation_id: str, *, access_scope: str
    ) -> tuple[Attempt, ...]:
        self._scoped_row(investigation_id, access_scope)
        return tuple(
            Attempt(
                attempt_id=row["attempt_id"],
                investigation_id=row["investigation_id"],
                attempt_number=row["attempt_number"],
                started_at=row["started_at"],
                lease_until=row["lease_until"],
                finished_at=row["finished_at"],
                outcome=row["outcome"],
                failure_code=row["failure_code"],
            )
            for row in self._db.execute(
                """SELECT * FROM attempts WHERE investigation_id=?
                   ORDER BY attempt_number""",
                (investigation_id,),
            )
        )

    def delete_terminal(
        self, investigation_id: str, *, access_scope: str, at: datetime
    ) -> int:
        timestamp = _at(at)
        with self._transaction():
            row = self._scoped_row(investigation_id, access_scope)
            if row["status"] not in ("completed", "failed", "cancelled", "expired"):
                raise StoreStateError("Only terminal investigations can be deleted.")
            count = self._db.execute(
                "SELECT COUNT(*) FROM evidence WHERE investigation_id=?",
                (investigation_id,),
            ).fetchone()[0]
            self._db.execute(
                """INSERT INTO deletion_audit (
                    investigation_id, access_scope, deleted_at, evidence_count
                ) VALUES (?, ?, ?, ?)""",
                (investigation_id, access_scope, timestamp, count),
            )
            self._db.execute(
                "DELETE FROM investigations WHERE investigation_id=?",
                (investigation_id,),
            )
        _LOG.info(
            "Investigation deleted.",
            extra={
                "event": "investigation.deleted",
                "investigation_id": investigation_id,
                "evidence_count": count,
            },
        )
        return count
