"""Offline SQLite persistence, recovery and access-boundary acceptance tests."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from trace_app.evidence import EvidenceRecord, SourceAvailability
from trace_app.investigation_state import (
    DeploymentPayload,
    EvidenceEntry,
    EvidenceKind,
    EvidenceSnapshot,
    Investigation,
    InvestigationRequest,
    LogPayload,
    MetricPayload,
    StoreAccessError,
    StoreConflictError,
    StoreInputError,
    StoreSchemaError,
    StoreStateError,
)
from trace_app.sqlite_store import SQLiteInvestigationStore

_NOW = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)
_WINDOW_START = "2026-01-01T00:00:00Z"
_WINDOW_END = "2026-01-01T00:01:00Z"
_SCOPE = "local:synthetic"


def _record(
    kind: str, index: int, *, collected_at: str = "2026-10-05T12:00:00Z"
) -> EvidenceRecord:
    return EvidenceRecord(
        evidence_id=f"ev-{kind}-{index}",
        service="payment" if kind == "metric" else "order",
        environment="test",
        observed_at=f"2026-01-01T00:00:0{index}Z",
        collected_at=collected_at,
        source_record_id=f"synthetic:{kind}:{index}",
        source_revision="fixture.v1",
        access_classification="synthetic_public",
        redaction_status="not_required",
        correlation_id="corr-001",
        event=f"{kind}.observed",
        integrity_sha256="a" * 64,
    )


def _payload(kind: EvidenceKind) -> LogPayload | MetricPayload | DeploymentPayload:
    if kind == "log":
        return LogPayload("Synthetic order requested.")
    if kind == "metric":
        return MetricPayload("payment_latency", 12.5, "ms")
    return DeploymentPayload("deploy-001", "started")


def _snapshot() -> EvidenceSnapshot:
    kinds: tuple[EvidenceKind, ...] = ("log", "metric", "deployment")
    entries = tuple(
        EvidenceEntry(kind, _record(kind, index), _payload(kind))
        for index, kind in enumerate(kinds)
    )
    return EvidenceSnapshot(
        entries=entries,
        window_start=_WINDOW_START,
        window_end=_WINDOW_END,
        sources=(
            SourceAvailability("synthetic_replay", "available"),
            SourceAvailability("sanitized_export", "unavailable", "no_access"),
        ),
    )


def _request(
    *,
    key: str = "submission-1",
    expiry: str | None = None,
    max_attempts: int = 3,
) -> InvestigationRequest:
    return InvestigationRequest(
        submission_key=key,
        service="order",
        environment="test",
        access_scope=_SCOPE,
        window_start=_WINDOW_START,
        window_end=_WINDOW_END,
        expires_at=expiry,
        max_attempts=max_attempts,
    )


def _attempt_id(investigation: Investigation) -> int:
    assert investigation.active_attempt_id is not None
    return investigation.active_attempt_id


class SQLiteStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="trace-store-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "state.sqlite3"

    def test_log_metric_deployment_roundtrip_after_reopen(self) -> None:
        snapshot = _snapshot()
        with SQLiteInvestigationStore(self.path) as store:
            initial = store.submit(_request(), at=_NOW)
            self.assertEqual(
                store.ingest_snapshot(
                    initial.investigation_id, snapshot, access_scope=_SCOPE, at=_NOW
                ),
                3,
            )
            store.initialize()
            self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        with SQLiteInvestigationStore(self.path) as store:
            restored = store.get_investigation(
                initial.investigation_id, access_scope=_SCOPE
            )
            self.assertEqual(restored, initial)
            returned = store.get_snapshot(initial.investigation_id, access_scope=_SCOPE)
            self.assertEqual(returned, snapshot)
            self.assertEqual(
                [entry.kind for entry in returned.entries],
                ["log", "metric", "deployment"],
            )
            for entry in snapshot.entries:
                self.assertEqual(
                    store.get_evidence(
                        initial.investigation_id,
                        entry.record.evidence_id,
                        access_scope=_SCOPE,
                    ),
                    entry,
                )
        with sqlite3.connect(self.path) as database:
            self.assertEqual(database.execute("PRAGMA user_version").fetchone()[0], 1)

    def test_duplicate_submission_and_collection_time_policy(self) -> None:
        expiry = "2026-10-06T00:00:00Z"
        snapshot = _snapshot()
        with SQLiteInvestigationStore(self.path) as store:
            initial = store.submit(_request(expiry=expiry), at=_NOW)
            self.assertEqual(
                store.submit(
                    _request(expiry=expiry), at=_NOW + timedelta(days=2)
                ).investigation_id,
                initial.investigation_id,
            )
            with self.assertRaises(StoreConflictError):
                store.submit(_request(expiry=None), at=_NOW)
            store.ingest_snapshot(
                initial.investigation_id, snapshot, access_scope=_SCOPE, at=_NOW
            )
            later = EvidenceSnapshot(
                entries=tuple(
                    EvidenceEntry(
                        entry.kind,
                        replace(entry.record, collected_at="2026-10-05T13:00:00Z"),
                        entry.payload,
                    )
                    for entry in snapshot.entries
                ),
                window_start=snapshot.window_start,
                window_end=snapshot.window_end,
                sources=snapshot.sources,
            )
            self.assertEqual(
                store.ingest_snapshot(
                    initial.investigation_id, later, access_scope=_SCOPE, at=_NOW
                ),
                0,
            )
            self.assertEqual(
                store.get_snapshot(initial.investigation_id, access_scope=_SCOPE),
                snapshot,
            )
            changed = EvidenceSnapshot(
                entries=(
                    EvidenceEntry(
                        "log",
                        replace(snapshot.entries[0].record, event="log.changed"),
                        snapshot.entries[0].payload,
                    ),
                    *snapshot.entries[1:],
                ),
                window_start=snapshot.window_start,
                window_end=snapshot.window_end,
                sources=snapshot.sources,
            )
            with self.assertRaises(StoreConflictError):
                store.ingest_snapshot(
                    initial.investigation_id, changed, access_scope=_SCOPE, at=_NOW
                )

    def test_changed_payload_conflicts_and_window_scope_are_validated(self) -> None:
        snapshot = _snapshot()
        with SQLiteInvestigationStore(self.path) as store:
            investigation = store.submit(_request(), at=_NOW)
            shifted_window = EvidenceSnapshot(
                entries=snapshot.entries,
                window_start=snapshot.window_start,
                window_end="2026-01-01T00:01:01Z",
                sources=snapshot.sources,
            )
            with self.assertRaisesRegex(StoreInputError, "query_window"):
                store.ingest_snapshot(
                    investigation.investigation_id,
                    shifted_window,
                    access_scope=_SCOPE,
                    at=_NOW,
                )
            with self.assertRaises(StoreAccessError):
                store.ingest_snapshot(
                    investigation.investigation_id,
                    snapshot,
                    access_scope="other:team",
                    at=_NOW,
                )
            store.ingest_snapshot(
                investigation.investigation_id,
                snapshot,
                access_scope=_SCOPE,
                at=_NOW,
            )
            changed = EvidenceSnapshot(
                entries=(
                    snapshot.entries[0],
                    replace(
                        snapshot.entries[1],
                        payload=MetricPayload("payment_latency", 99.0, "ms"),
                    ),
                    snapshot.entries[2],
                ),
                window_start=snapshot.window_start,
                window_end=snapshot.window_end,
                sources=snapshot.sources,
            )
            with self.assertRaises(StoreConflictError):
                store.ingest_snapshot(
                    investigation.investigation_id,
                    changed,
                    access_scope=_SCOPE,
                    at=_NOW,
                )
        with self.assertRaisesRegex(StoreInputError, "value"):
            MetricPayload("payment_latency", float("nan"), "ms")
        with self.assertRaisesRegex(StoreInputError, "value"):
            MetricPayload("payment_latency", 10**1000, "ms")
        with self.assertRaisesRegex(StoreInputError, "payload"):
            EvidenceEntry("metric", _record("metric", 1), LogPayload("wrong"))

    def test_empty_snapshot_abstention_and_attempt_limit(self) -> None:
        with SQLiteInvestigationStore(self.path) as store:
            empty = store.submit(_request(key="empty"), at=_NOW)
            store.ingest_snapshot(
                empty.investigation_id,
                EvidenceSnapshot(
                    entries=(),
                    window_start=_WINDOW_START,
                    window_end=_WINDOW_END,
                    sources=(
                        SourceAvailability(
                            "synthetic_replay", "unavailable", "missing"
                        ),
                    ),
                ),
                access_scope=_SCOPE,
                at=_NOW,
            )
            claimed = store.claim_next(at=_NOW)
            assert claimed is not None
            with self.assertRaisesRegex(StoreStateError, "observed evidence"):
                store.complete(
                    empty.investigation_id,
                    _attempt_id(claimed),
                    access_scope=_SCOPE,
                    assessment_status="supported",
                    at=_NOW,
                )
            self.assertEqual(
                store.complete(
                    empty.investigation_id,
                    _attempt_id(claimed),
                    access_scope=_SCOPE,
                    assessment_status="abstained",
                    at=_NOW,
                ).assessment_status,
                "abstained",
            )
            limited = store.submit(_request(key="limited", max_attempts=1), at=_NOW)
            running = store.claim_next(at=_NOW, lease_seconds=1)
            assert running is not None
            self.assertEqual(running.investigation_id, limited.investigation_id)
            self.assertEqual(store.recover(at=_NOW + timedelta(seconds=2)), 1)
            self.assertEqual(
                store.get_investigation(
                    limited.investigation_id, access_scope=_SCOPE
                ).status,
                "failed",
            )
            self.assertIsNone(store.claim_next(at=_NOW + timedelta(seconds=2)))

    def test_ingestion_rollback_on_mid_batch_database_failure(self) -> None:
        snapshot = _snapshot()
        with SQLiteInvestigationStore(self.path) as store:
            investigation = store.submit(_request(), at=_NOW)
            with sqlite3.connect(self.path) as database:
                database.execute(
                    """CREATE TRIGGER reject_second_evidence BEFORE INSERT ON evidence
                       WHEN NEW.ordinal = 1 BEGIN SELECT RAISE(ABORT, 'test fault'); END"""
                )
            with self.assertRaises(sqlite3.IntegrityError):
                store.ingest_snapshot(
                    investigation.investigation_id,
                    snapshot,
                    access_scope=_SCOPE,
                    at=_NOW,
                )
            with self.assertRaises(StoreAccessError):
                store.get_snapshot(investigation.investigation_id, access_scope=_SCOPE)
            with sqlite3.connect(self.path) as database:
                self.assertEqual(
                    database.execute("SELECT COUNT(*) FROM evidence").fetchone()[0], 0
                )
                database.execute("DROP TRIGGER reject_second_evidence")
            self.assertEqual(
                store.ingest_snapshot(
                    investigation.investigation_id,
                    snapshot,
                    access_scope=_SCOPE,
                    at=_NOW,
                ),
                3,
            )

    def test_recovery_retries_and_stale_attempt_rejection_after_restart(self) -> None:
        with SQLiteInvestigationStore(self.path) as store:
            investigation = store.submit(_request(), at=_NOW)
            store.ingest_snapshot(
                investigation.investigation_id,
                _snapshot(),
                access_scope=_SCOPE,
                at=_NOW,
            )
            first = store.claim_next(at=_NOW, lease_seconds=10)
            self.assertIsNotNone(first)
            assert first is not None
            self.assertEqual(first.status, "running")
        with SQLiteInvestigationStore(self.path) as store:
            with self.assertRaisesRegex(StoreStateError, "lease"):
                store.complete(
                    investigation.investigation_id,
                    _attempt_id(first),
                    access_scope=_SCOPE,
                    assessment_status="supported",
                    at=_NOW + timedelta(seconds=11),
                )
            self.assertEqual(store.recover(at=_NOW + timedelta(seconds=11)), 1)
            self.assertEqual(
                store.get_investigation(
                    investigation.investigation_id, access_scope=_SCOPE
                ).status,
                "queued",
            )
            second = store.claim_next(at=_NOW + timedelta(seconds=12))
            assert second is not None
            self.assertNotEqual(_attempt_id(first), _attempt_id(second))
            with self.assertRaises(StoreStateError):
                store.complete(
                    investigation.investigation_id,
                    _attempt_id(first),
                    access_scope=_SCOPE,
                    assessment_status="supported",
                    at=_NOW + timedelta(seconds=13),
                )
            retried = store.fail_attempt(
                investigation.investigation_id,
                _attempt_id(second),
                access_scope=_SCOPE,
                failure_code="source_unavailable",
                retry=True,
                at=_NOW + timedelta(seconds=13),
            )
            self.assertEqual(retried.status, "queued")
            third = store.claim_next(at=_NOW + timedelta(seconds=14))
            assert third is not None
            completed = store.complete(
                investigation.investigation_id,
                _attempt_id(third),
                access_scope=_SCOPE,
                assessment_status="abstained",
                at=_NOW + timedelta(seconds=15),
            )
            self.assertEqual(completed.status, "completed")
            self.assertEqual(completed.assessment_status, "abstained")
            self.assertEqual(completed.review_status, "unreviewed")
            self.assertEqual(
                [
                    attempt.outcome
                    for attempt in store.list_attempts(
                        investigation.investigation_id, access_scope=_SCOPE
                    )
                ],
                ["interrupted", "failed", "completed"],
            )
            reviewed = store.review(
                investigation.investigation_id,
                access_scope=_SCOPE,
                decision="approved",
            )
            self.assertEqual(reviewed.review_status, "approved")
            with self.assertRaises(StoreConflictError):
                store.review(
                    investigation.investigation_id,
                    access_scope=_SCOPE,
                    decision="rejected",
                )

    def test_retry_limit_is_persisted_across_restart(self) -> None:
        with SQLiteInvestigationStore(self.path) as store:
            investigation = store.submit(
                _request(key="one-attempt", max_attempts=1), at=_NOW
            )
            claimed = store.claim_next(at=_NOW, lease_seconds=1)
            assert claimed is not None
            self.assertEqual(claimed.request.max_attempts, 1)
        with SQLiteInvestigationStore(self.path) as store:
            self.assertEqual(
                store.get_investigation(
                    investigation.investigation_id, access_scope=_SCOPE
                ).request.max_attempts,
                1,
            )
            self.assertEqual(store.recover(at=_NOW + timedelta(seconds=2)), 1)
            self.assertEqual(
                store.get_investigation(
                    investigation.investigation_id, access_scope=_SCOPE
                ).status,
                "failed",
            )
            self.assertIsNone(store.claim_next(at=_NOW + timedelta(seconds=2)))

    def test_expiry_and_lease_compare_fractional_utc_times_correctly(self) -> None:
        start = datetime(2026, 10, 5, 12, 0, 0, 900_000, tzinfo=UTC)
        request = _request(
            key="fractional",
            expiry="2026-10-05T12:00:00.950000Z",
        )
        with SQLiteInvestigationStore(self.path) as store:
            investigation = store.submit(request, at=start)
            self.assertEqual(
                store.recover(at=datetime(2026, 10, 5, 12, 0, 0, 925_000, tzinfo=UTC)),
                0,
            )
            self.assertEqual(
                store.get_investigation(
                    investigation.investigation_id, access_scope=_SCOPE
                ).status,
                "queued",
            )
            self.assertEqual(
                store.recover(at=datetime(2026, 10, 5, 12, 0, 0, 951_000, tzinfo=UTC)),
                1,
            )
            self.assertEqual(
                store.get_investigation(
                    investigation.investigation_id, access_scope=_SCOPE
                ).status,
                "expired",
            )

        lease_path = Path(self.temp.name) / "lease.sqlite3"
        with SQLiteInvestigationStore(lease_path) as store:
            pending = store.submit(_request(key="lease"), at=start)
            store.ingest_snapshot(
                pending.investigation_id, _snapshot(), access_scope=_SCOPE, at=start
            )
            claimed = store.claim_next(at=start, lease_seconds=1)
            assert claimed is not None
            with self.assertRaisesRegex(StoreStateError, "lease"):
                store.complete(
                    pending.investigation_id,
                    _attempt_id(claimed),
                    access_scope=_SCOPE,
                    assessment_status="supported",
                    at=datetime(2026, 10, 5, 12, 0, 1, 901_000, tzinfo=UTC),
                )

    def test_failed_cancelled_and_expired_stay_distinct_from_abstention(self) -> None:
        with SQLiteInvestigationStore(self.path) as store:
            failed = store.submit(_request(key="failure"), at=_NOW)
            claimed = store.claim_next(at=_NOW)
            assert claimed is not None
            self.assertEqual(
                store.fail_attempt(
                    failed.investigation_id,
                    _attempt_id(claimed),
                    access_scope=_SCOPE,
                    failure_code="dependency_failed",
                    retry=False,
                    at=_NOW + timedelta(seconds=1),
                ).status,
                "failed",
            )
            cancelled = store.submit(_request(key="cancel"), at=_NOW)
            cancel_attempt = store.claim_next(at=_NOW)
            assert cancel_attempt is not None
            self.assertEqual(
                store.cancel(
                    cancelled.investigation_id, access_scope=_SCOPE, at=_NOW
                ).status,
                "cancelled",
            )
            self.assertEqual(
                store.list_attempts(cancelled.investigation_id, access_scope=_SCOPE)[
                    0
                ].outcome,
                "cancelled",
            )
            with self.assertRaises(StoreStateError):
                store.complete(
                    cancelled.investigation_id,
                    _attempt_id(cancel_attempt),
                    access_scope=_SCOPE,
                    assessment_status="supported",
                    at=_NOW,
                )
            expiring = store.submit(
                _request(key="expire", expiry="2026-10-05T12:00:05Z"), at=_NOW
            )
            self.assertEqual(store.recover(at=_NOW + timedelta(seconds=6)), 1)
            self.assertEqual(
                store.get_investigation(
                    expiring.investigation_id, access_scope=_SCOPE
                ).status,
                "expired",
            )
            for item in (failed, cancelled, expiring):
                state = store.get_investigation(
                    item.investigation_id, access_scope=_SCOPE
                )
                self.assertEqual(state.assessment_status, "pending")
                self.assertEqual(state.review_status, "pending")

    def test_scope_and_ground_truth_are_excluded_from_store_reads(self) -> None:
        with SQLiteInvestigationStore(self.path) as store:
            investigation = store.submit(_request(), at=_NOW)
            snapshot = _snapshot()
            store.ingest_snapshot(
                investigation.investigation_id, snapshot, access_scope=_SCOPE, at=_NOW
            )
            for read in (
                lambda: store.get_investigation(
                    investigation.investigation_id, access_scope="other:team"
                ),
                lambda: store.get_snapshot(
                    investigation.investigation_id, access_scope="other:team"
                ),
                lambda: store.get_evidence(
                    investigation.investigation_id,
                    snapshot.entries[0].record.evidence_id,
                    access_scope="other:team",
                ),
            ):
                with self.assertRaises(StoreAccessError):
                    read()
            with self.assertRaises(StoreInputError):
                store.ingest_snapshot(
                    investigation.investigation_id,
                    EvidenceSnapshot(
                        entries=(
                            EvidenceEntry(
                                "log",
                                replace(
                                    snapshot.entries[0].record,
                                    access_classification="restricted",
                                ),
                                snapshot.entries[0].payload,
                            ),
                        ),
                        window_start=snapshot.window_start,
                        window_end=snapshot.window_end,
                        sources=snapshot.sources,
                    ),
                    access_scope=_SCOPE,
                    at=_NOW,
                )
            with sqlite3.connect(self.path) as database:
                tables = {
                    row[0]
                    for row in database.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
                self.assertTrue(
                    {"investigations", "attempts", "snapshots", "evidence"} <= tables
                )
                self.assertFalse(
                    any("truth" in name or "label" in name for name in tables)
                )
                stored = database.execute(
                    "SELECT record_json FROM evidence LIMIT 1"
                ).fetchone()[0]
                for forbidden in (
                    "ground_truth",
                    "cause_service",
                    "mechanism",
                    "label",
                ):
                    self.assertNotIn(forbidden, stored)
                self.assertEqual(
                    json.loads(stored)["evidence_id"],
                    snapshot.entries[0].record.evidence_id,
                )

    def test_field_errors_limits_schema_and_deletion(self) -> None:
        record = _record("log", 0).to_dict()
        with self.assertRaisesRegex(ValueError, "observed_at"):
            EvidenceRecord.from_dict({**record, "observed_at": "bad"})
        with self.assertRaisesRegex(ValueError, "ground_truth"):
            EvidenceRecord.from_dict({**record, "ground_truth": "secret"})
        with self.assertRaisesRegex(StoreInputError, "source_record_id"):
            EvidenceSnapshot(
                entries=(
                    EvidenceEntry("log", _record("log", 0), _payload("log")),
                    EvidenceEntry(
                        "metric",
                        replace(
                            _record("metric", 1),
                            source_record_id=_record("log", 0).source_record_id,
                        ),
                        _payload("metric"),
                    ),
                ),
                window_start=_WINDOW_START,
                window_end=_WINDOW_END,
                sources=(SourceAvailability("synthetic_replay", "available"),),
            )
        with SQLiteInvestigationStore(self.path, max_records=1) as store:
            investigation = store.submit(_request(), at=_NOW)
            with self.assertRaisesRegex(StoreInputError, "max_records"):
                store.ingest_snapshot(
                    investigation.investigation_id,
                    _snapshot(),
                    access_scope=_SCOPE,
                    at=_NOW,
                )
        with SQLiteInvestigationStore(self.path) as store:
            store.ingest_snapshot(
                investigation.investigation_id,
                _snapshot(),
                access_scope=_SCOPE,
                at=_NOW,
            )
            with self.assertRaises(StoreStateError):
                store.delete_terminal(
                    investigation.investigation_id, access_scope=_SCOPE, at=_NOW
                )
            claimed = store.claim_next(at=_NOW)
            assert claimed is not None
            store.complete(
                investigation.investigation_id,
                _attempt_id(claimed),
                access_scope=_SCOPE,
                assessment_status="supported",
                at=_NOW,
            )
            self.assertEqual(
                store.delete_terminal(
                    investigation.investigation_id, access_scope=_SCOPE, at=_NOW
                ),
                3,
            )
            with self.assertRaises(StoreAccessError):
                store.get_snapshot(investigation.investigation_id, access_scope=_SCOPE)
            with sqlite3.connect(self.path) as database:
                self.assertEqual(
                    database.execute("SELECT COUNT(*) FROM evidence").fetchone()[0], 0
                )
                self.assertEqual(
                    database.execute(
                        "SELECT evidence_count FROM deletion_audit"
                    ).fetchone()[0],
                    3,
                )
        broad = Path(self.temp.name) / "broad.sqlite3"
        broad.write_bytes(b"")
        os.chmod(broad, 0o644)
        with self.assertRaisesRegex(StoreInputError, "0600"):
            SQLiteInvestigationStore(broad)
        future = Path(self.temp.name) / "future.sqlite3"
        with sqlite3.connect(future) as database:
            database.execute("PRAGMA user_version=99")
        os.chmod(future, 0o600)
        with self.assertRaises(StoreSchemaError):
            SQLiteInvestigationStore(future)


if __name__ == "__main__":
    unittest.main()
