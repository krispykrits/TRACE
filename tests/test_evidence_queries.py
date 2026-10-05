"""Offline acceptance tests for bounded, scope-aware evidence reads."""

from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from trace_app.evidence import EvidenceRecord, SourceAvailability
from trace_app.evidence_queries import (
    EvidenceQuery,
    EvidenceQueryService,
    TrustedQueryContext,
)
from trace_app.investigation_state import (
    DeploymentPayload,
    EvidenceEntry,
    EvidenceSnapshot,
    InvestigationRequest,
    LogPayload,
    MetricPayload,
    StoreAccessError,
    StoreDependencyError,
    StoreInputError,
)
from trace_app.sqlite_store import SQLiteInvestigationStore

_SCOPE = "local:synthetic"
_NOW = datetime(2026, 10, 5, tzinfo=UTC)
_START = "2026-01-01T00:00:00Z"
_END = "2026-01-01T00:00:02Z"
_CONTEXT = TrustedQueryContext(_SCOPE, "test", ("order", "payment"))


def _entry(
    evidence_id: str,
    service: str,
    observed_at: str,
    kind: str,
) -> EvidenceEntry:
    record = EvidenceRecord(
        evidence_id=evidence_id,
        service=service,
        environment="test",
        observed_at=observed_at,
        collected_at="2026-10-05T00:00:00Z",
        source_record_id=f"synthetic:{evidence_id}",
        source_revision="fixture.v1",
        access_classification="synthetic_public",
        redaction_status="not_required",
        correlation_id="corr-11",
        event=f"{kind}.observed",
        integrity_sha256="a" * 64,
    )
    if kind == "metric":
        return EvidenceEntry("metric", record, MetricPayload("latency", 12.5, "ms"))
    if kind == "deployment":
        return EvidenceEntry(
            "deployment", record, DeploymentPayload("revision-1", "started")
        )
    return EvidenceEntry("log", record, LogPayload("Synthetic event."))


def _snapshot(
    *, sources: tuple[SourceAvailability, ...] | None = None
) -> EvidenceSnapshot:
    return EvidenceSnapshot(
        entries=(
            _entry("ev-end", "order", _END, "deployment"),
            _entry("ev-middle", "payment", "2026-01-01T00:00:00.5Z", "metric"),
            _entry("ev-start", "order", _START, "log"),
            _entry("ev-payment", "payment", "2026-01-01T00:00:01Z", "log"),
        ),
        window_start=_START,
        window_end=_END,
        sources=sources
        if sources is not None
        else (SourceAvailability("synthetic_replay", "available"),),
    )


def _query(**changes: object) -> EvidenceQuery:
    values: dict[str, object] = {"window_start": _START, "window_end": _END}
    values.update(changes)
    return EvidenceQuery(**values)  # type: ignore[arg-type]


class EvidenceQueryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="trace-query-")
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "state.sqlite3"

    def _seed(
        self,
        store: SQLiteInvestigationStore,
        *,
        snapshot: EvidenceSnapshot | None = None,
    ) -> str:
        investigation = store.submit(
            InvestigationRequest(
                submission_key="query-case",
                service="order",
                environment="test",
                access_scope=_SCOPE,
                window_start=_START,
                window_end=_END,
            ),
            at=_NOW,
        )
        if snapshot is not None:
            store.ingest_snapshot(
                investigation.investigation_id,
                snapshot,
                access_scope=_SCOPE,
                at=_NOW,
            )
        return investigation.investigation_id

    def test_inclusive_time_edges_filters_order_and_provenance(self) -> None:
        with SQLiteInvestigationStore(self.path) as store:
            investigation_id = self._seed(store, snapshot=_snapshot())
            service = EvidenceQueryService(store)
            result = service.query(investigation_id, _query(), context=_CONTEXT)
            self.assertEqual(result.status, "complete")
            self.assertEqual(
                [entry.record.evidence_id for entry in result.entries],
                ["ev-start", "ev-middle", "ev-payment", "ev-end"],
            )
            self.assertEqual(result.matching_count, 4)
            self.assertFalse(result.truncated)
            for entry in result.entries:
                self.assertEqual(
                    service.get_by_id(
                        investigation_id,
                        entry.record.evidence_id,
                        _query(),
                        context=_CONTEXT,
                    ),
                    entry,
                )
                self.assertEqual(entry.record.source_revision, "fixture.v1")
                self.assertEqual(entry.record.correlation_id, "corr-11")
            self.assertEqual(
                [
                    entry.record.evidence_id
                    for entry in service.query(
                        investigation_id,
                        _query(service="payment", kind="metric"),
                        context=_CONTEXT,
                    ).entries
                ],
                ["ev-middle"],
            )
            self.assertEqual(
                [
                    entry.record.evidence_id
                    for entry in service.query(
                        investigation_id,
                        _query(window_start=_END, window_end=_END),
                        context=_CONTEXT,
                    ).entries
                ],
                ["ev-end"],
            )

    def test_event_time_not_collection_time_and_explicit_empty(self) -> None:
        with SQLiteInvestigationStore(self.path) as store:
            investigation_id = self._seed(store, snapshot=_snapshot())
            service = EvidenceQueryService(store)
            query = _query(
                window_start="2026-01-01T00:00:00.000001Z",
                window_end="2026-01-01T00:00:00.499999Z",
            )
            result = service.query(investigation_id, query, context=_CONTEXT)
            self.assertEqual(result.status, "empty")
            self.assertEqual(result.entries, ())
            self.assertEqual(result.matching_count, 0)
            with self.assertRaises(StoreAccessError):
                service.get_by_id(investigation_id, "ev-start", query, context=_CONTEXT)
            self.assertEqual(
                service.query(
                    investigation_id,
                    _query(
                        window_start="2026-01-01T00:00:00.5Z",
                        window_end="2026-01-01T00:00:00.5Z",
                    ),
                    context=_CONTEXT,
                )
                .entries[0]
                .record.evidence_id,
                "ev-middle",
            )

    def test_limits_and_source_incompleteness_are_disclosed(self) -> None:
        snapshot = _snapshot(
            sources=(
                SourceAvailability("synthetic_replay", "available"),
                SourceAvailability("sanitized_export", "unavailable", "no_access"),
            )
        )
        with SQLiteInvestigationStore(self.path) as store:
            investigation_id = self._seed(store, snapshot=snapshot)
            service = EvidenceQueryService(store, max_limit=2)
            result = service.query(investigation_id, _query(limit=2), context=_CONTEXT)
            self.assertEqual(result.status, "incomplete")
            self.assertTrue(result.truncated)
            self.assertEqual(result.matching_count, 4)
            self.assertEqual(len(result.entries), 2)
            self.assertEqual(result.sources[1].status, "unavailable")
            empty = service.query(
                investigation_id,
                _query(
                    service="payment",
                    kind="deployment",
                    limit=2,
                ),
                context=_CONTEXT,
            )
            self.assertEqual(empty.status, "incomplete")
            self.assertEqual(empty.matching_count, 0)
            self.assertFalse(empty.truncated)
            with self.assertRaisesRegex(StoreInputError, "max_limit"):
                service.query(investigation_id, _query(limit=3), context=_CONTEXT)

    def test_absent_source_manifest_is_not_a_complete_result(self) -> None:
        with SQLiteInvestigationStore(self.path) as store:
            investigation_id = self._seed(store, snapshot=_snapshot(sources=()))
            result = EvidenceQueryService(store).query(
                investigation_id, _query(), context=_CONTEXT
            )
            self.assertEqual(result.status, "incomplete")
            self.assertEqual(result.sources, ())
            self.assertEqual(result.matching_count, 4)

    def test_scope_environment_service_and_direct_id_access(self) -> None:
        with SQLiteInvestigationStore(self.path) as store:
            investigation_id = self._seed(store, snapshot=_snapshot())
            service = EvidenceQueryService(store)
            order_only = TrustedQueryContext(_SCOPE, "test", ("order",))
            result = service.query(investigation_id, _query(), context=order_only)
            self.assertEqual(
                [entry.record.evidence_id for entry in result.entries],
                ["ev-start", "ev-end"],
            )
            with self.assertRaises(StoreAccessError):
                service.query(
                    investigation_id,
                    _query(service="payment"),
                    context=order_only,
                )
            with self.assertRaises(StoreAccessError):
                service.get_by_id(
                    investigation_id,
                    "ev-middle",
                    _query(),
                    context=order_only,
                )
            for context in (
                TrustedQueryContext("other:scope", "test", ("order", "payment")),
                TrustedQueryContext(_SCOPE, "production", ("order", "payment")),
            ):
                with self.subTest(context=context):
                    with self.assertRaises(StoreAccessError):
                        service.query(investigation_id, _query(), context=context)
                    with self.assertRaises(StoreAccessError):
                        service.get_by_id(
                            investigation_id,
                            "ev-start",
                            _query(),
                            context=context,
                        )
            with self.assertRaises(StoreAccessError):
                service.get_by_id(
                    investigation_id, "ev-does-not-exist", _query(), context=_CONTEXT
                )

    def test_invalid_requests_and_investigation_window_bounds(self) -> None:
        with self.assertRaisesRegex(StoreInputError, "window_start"):
            _query(window_start="2026-01-01")
        with self.assertRaisesRegex(StoreInputError, "window_start"):
            _query(window_start=_END, window_end=_START)
        with self.assertRaisesRegex(StoreInputError, "limit"):
            _query(limit=0)
        with self.assertRaisesRegex(StoreInputError, "kind"):
            _query(kind="arbitrary")
        with self.assertRaisesRegex(StoreInputError, "service"):
            _query(service="order; DROP TABLE evidence")
        with self.assertRaisesRegex(StoreInputError, "allowed_services"):
            TrustedQueryContext(_SCOPE, "test", ())
        with SQLiteInvestigationStore(self.path) as store:
            investigation_id = self._seed(store, snapshot=_snapshot())
            service = EvidenceQueryService(store, max_window=timedelta(seconds=1))
            with self.assertRaisesRegex(StoreInputError, "max_window"):
                service.query(investigation_id, _query(), context=_CONTEXT)
            with self.assertRaisesRegex(StoreInputError, "investigation window"):
                service.query(
                    investigation_id,
                    _query(
                        window_start="2025-12-31T23:59:59Z",
                        window_end=_START,
                    ),
                    context=_CONTEXT,
                )

    def test_missing_snapshot_and_database_failure_are_distinct(self) -> None:
        with SQLiteInvestigationStore(self.path) as store:
            investigation_id = self._seed(store)
            service = EvidenceQueryService(store)
            missing = service.query(investigation_id, _query(), context=_CONTEXT)
            self.assertEqual(missing.status, "snapshot_missing")
            self.assertEqual(missing.failure_code, "snapshot_missing")
            self.assertEqual(missing.sources, ())
            store.close()
            failed = service.query(investigation_id, _query(), context=_CONTEXT)
            self.assertEqual(failed.status, "storage_failure")
            self.assertEqual(failed.failure_code, "storage_failure")
            self.assertNotEqual(failed.status, "empty")
            with self.assertRaises(StoreDependencyError):
                service.get_by_id(
                    investigation_id, "ev-start", _query(), context=_CONTEXT
                )

    def test_corrupted_stored_record_is_storage_failure(self) -> None:
        with SQLiteInvestigationStore(self.path) as store:
            investigation_id = self._seed(store, snapshot=_snapshot())
        with sqlite3.connect(self.path) as database:
            database.execute(
                "UPDATE evidence SET record_json = ? WHERE investigation_id = ? AND evidence_id = ?",
                ("{invalid", investigation_id, "ev-start"),
            )
        with SQLiteInvestigationStore(self.path) as store:
            result = EvidenceQueryService(store).query(
                investigation_id, _query(), context=_CONTEXT
            )
            self.assertEqual(result.status, "storage_failure")
            self.assertEqual(result.failure_code, "storage_failure")
            self.assertEqual(result.entries, ())

    def test_incompatible_snapshot_schema_is_storage_failure(self) -> None:
        with SQLiteInvestigationStore(self.path) as store:
            investigation_id = self._seed(store, snapshot=_snapshot())
        with sqlite3.connect(self.path) as database:
            database.execute(
                "UPDATE snapshots SET schema_version = ? WHERE investigation_id = ?",
                ("2", investigation_id),
            )
        with SQLiteInvestigationStore(self.path) as store:
            result = EvidenceQueryService(store).query(
                investigation_id, _query(), context=_CONTEXT
            )
            self.assertEqual(result.status, "storage_failure")
            self.assertEqual(result.failure_code, "schema_incompatible")
            self.assertEqual(result.entries, ())

    def test_read_bound_survives_reopen_and_rejects_oversized_snapshot(self) -> None:
        with SQLiteInvestigationStore(self.path) as store:
            investigation_id = self._seed(store, snapshot=_snapshot())
        with SQLiteInvestigationStore(self.path, max_records=2) as store:
            failed = EvidenceQueryService(store).query(
                investigation_id, _query(), context=_CONTEXT
            )
            self.assertEqual(failed.status, "storage_failure")
            self.assertEqual(failed.failure_code, "storage_failure")
