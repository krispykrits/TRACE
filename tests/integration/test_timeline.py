"""Time ordering, identity, scoped citations and missing-evidence acceptance."""

from __future__ import annotations

import json
import random
import unittest
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from trace_app.adapters.storage.sqlite.investigations import SQLiteInvestigationStore
from trace_app.demo.scenarios import CASE_IDS, ScenarioConfig, ScenarioSession
from trace_app.evidence.models import (
    EvidenceBundle,
    EvidenceRecord,
    SourceAvailability,
    normalize_timestamp,
)
from trace_app.evidence.queries import (
    EvidenceQuery,
    EvidenceQueryService,
    TrustedQueryContext,
)
from trace_app.evidence.timeline import TimelineService, order_evidence
from trace_app.investigation.models import (
    EvidenceSnapshot,
    InvestigationRequest,
    StoreAccessError,
    StoreConflictError,
    StoreDependencyError,
    StoreInputError,
)

_CAPTURE = datetime(2026, 10, 12, 12, tzinfo=UTC)
_CONTEXT = TrustedQueryContext(
    "local:synthetic", "test", ("order", "payment", "customer", "notification")
)


def _snapshot(case: str = "c01") -> EvidenceSnapshot:
    return (
        ScenarioSession(ScenarioConfig(case, 17)).replay(collected_at=_CAPTURE).snapshot
    )


class TimestampTests(unittest.TestCase):
    def test_source_offsets_normalize_both_times_without_losing_provenance(
        self,
    ) -> None:
        source = _snapshot().entries[0].record.to_dict()
        utc = "2026-01-01T00:00:17Z"
        for offset in (
            "2025-12-31T19:00:17-05:00",
            "2026-01-01T05:30:17+05:30",
            "2026-01-01T00:00:17+00:00",
        ):
            with self.subTest(offset=offset):
                record = EvidenceRecord.from_source_dict(
                    {**source, "observed_at": offset, "collected_at": offset}
                )
                self.assertEqual(record.observed_at, utc)
                self.assertEqual(record.collected_at, utc)
                for field in (
                    "evidence_id",
                    "source_record_id",
                    "source_revision",
                    "integrity_sha256",
                ):
                    self.assertEqual(record.to_dict()[field], source[field])
        self.assertEqual(
            normalize_timestamp("2025-12-31T23:00:17.123456-01:00"),
            "2026-01-01T00:00:17.123456Z",
        )
        with self.assertRaisesRegex(ValueError, "not allowed"):
            EvidenceRecord.from_source_dict({**source, "cause_label": "hidden"})
        # Stored-envelope parsing stays strict; source normalization is explicit.
        with self.assertRaisesRegex(ValueError, "observed_at"):
            EvidenceRecord.from_dict(
                {**source, "observed_at": "2025-12-31T19:00:17-05:00"}
            )

    def test_ambiguous_invalid_or_unrepresentable_times_are_rejected(self) -> None:
        for value in (
            "2026-01-01",
            "2026-01-01T01:00:00",
            "2026-11-01T01:30:00 EST",
            "2026-01-01T00:00:00-00:00",
            "2026-01-01 00:00:00Z",
            "2026-01-01T00:00:00+01:60",
            "2026-01-01T00:00:00+24:00",
            "2026-02-30T00:00:00Z",
            "2026-01-01T00:00:60Z",
            "2026-01-01T00:00:00.1234567Z",
            "0001-01-01T00:00:00+01:00",
            "9999-12-31T23:59:59-01:00",
            "",
            None,
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_timestamp(value)  # type: ignore[arg-type]
        source = _snapshot().entries[0].record.to_dict()
        for field in ("observed_at", "collected_at"):
            with self.assertRaisesRegex(ValueError, field):
                EvidenceRecord.from_source_dict({**source, field: "invalid"})

    def test_fractional_seconds_and_equal_instants_use_ids_not_text_order(self) -> None:
        snapshot = _snapshot()
        base = snapshot.entries[0]
        times = (
            ("ev-b", "2026-01-01T00:00:17Z"),
            ("ev-c", "2026-01-01T00:00:17.5Z"),
            ("ev-a", "2026-01-01T00:00:17.000000Z"),
        )
        entries = tuple(
            replace(
                base,
                record=replace(
                    base.record,
                    evidence_id=identity,
                    source_record_id=identity,
                    observed_at=time,
                ),
            )
            for identity, time in times
        )
        expected = ["ev-a", "ev-b", "ev-c"]
        self.assertEqual(
            [e.record.evidence_id for e in order_evidence(entries)], expected
        )
        bundle = EvidenceBundle(
            tuple(e.record for e in entries),
            snapshot.window_start,
            snapshot.window_end,
            snapshot.sources,
        )
        self.assertEqual([e.evidence_id for e in bundle.timeline()], expected)


class TimelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = TemporaryDirectory(prefix="trace-timeline-test-")
        self.addCleanup(self.temp.cleanup)
        self.store = SQLiteInvestigationStore(Path(self.temp.name) / "state.db")
        self.addCleanup(self.store.close)
        self.service = TimelineService(EvidenceQueryService(self.store))

    def _seed(
        self, snapshot: EvidenceSnapshot | None = None, *, key: str = "timeline"
    ) -> tuple[str, EvidenceQuery]:
        window = snapshot or _snapshot()
        investigation = self.store.submit(
            InvestigationRequest(
                key,
                "order",
                "test",
                _CONTEXT.access_scope,
                window.window_start,
                window.window_end,
            ),
            at=_CAPTURE,
        )
        if snapshot is not None:
            self.store.ingest_snapshot(
                investigation.investigation_id,
                snapshot,
                access_scope=_CONTEXT.access_scope,
                at=_CAPTURE,
            )
        return investigation.investigation_id, EvidenceQuery(
            window.window_start, window.window_end
        )

    def test_shuffled_development_cases_have_exact_expected_inclusion_and_links(
        self,
    ) -> None:
        expected = ["000", "001", "002", "d01", "003", "004", "005", "006", "007"]
        for case in CASE_IDS:
            snapshot = _snapshot(case)
            for shuffle_seed in (0, 7):
                entries = list(snapshot.entries)
                random.Random(shuffle_seed).shuffle(entries)
                investigation_id, query = self._seed(
                    replace(snapshot, entries=tuple(entries)),
                    key=f"{case}-{shuffle_seed}",
                )
                timeline = self.service.build(investigation_id, query, context=_CONTEXT)
                wanted = (
                    expected if case in ("c01", "c02") else ["002", "d01", "003", "007"]
                )
                self.assertEqual(
                    [e.record.evidence_id.rsplit("-", 1)[1] for e in timeline.events],
                    wanted,
                )
                self.assertEqual(timeline.status, "incomplete")
                self.assertEqual(timeline.sources, snapshot.sources)
                for event in timeline.events:
                    self.assertEqual(
                        self.service.resolve(
                            timeline, event.record.evidence_id, context=_CONTEXT
                        ),
                        event,
                    )
                exported = timeline.to_dict()
                self.assertEqual(exported["schema_version"], "1")
                exported_events = exported["events"]
                assert isinstance(exported_events, list)
                for event in exported_events:
                    self.assertEqual(event["causal_status"], "observed")
                    self.assertEqual(
                        event["evidence_id"], event["record"]["evidence_id"]
                    )
                for forbidden in (
                    "cause_label",
                    "cause_service",
                    "ground_truth",
                    "expected_assessment",
                    "caused_by",
                ):
                    self.assertNotIn(forbidden, json.dumps(exported))

    def test_collection_delay_does_not_reorder_observations(self) -> None:
        snapshot = _snapshot()
        investigation_id, query = self._seed(snapshot)
        timeline = self.service.build(investigation_id, query, context=_CONTEXT)
        first = timeline.events[0]
        later_log = timeline.events[2]
        self.assertLess(first.record.observed_at, later_log.record.observed_at)
        self.assertGreater(first.record.collected_at, later_log.record.collected_at)
        self.assertEqual(first, snapshot.entries[0])
        self.assertEqual(first.record.source_revision, "mvp-suite.v1")

    def test_identical_and_conflicting_duplicate_identities_are_rejected(self) -> None:
        base = _snapshot().entries[0]
        for duplicate in (
            base,
            replace(base, record=replace(base.record, event="other.event")),
            replace(base, record=replace(base.record, evidence_id="another-id")),
        ):
            with self.subTest(duplicate=duplicate), self.assertRaises(StoreInputError):
                order_evidence((base, duplicate))

    def test_source_gaps_limits_empty_and_failures_remain_distinct(self) -> None:
        snapshot = replace(
            _snapshot(), sources=(SourceAvailability("replay", "available"),)
        )
        investigation_id, query = self._seed(snapshot)
        complete = self.service.build(investigation_id, query, context=_CONTEXT)
        self.assertEqual(complete.status, "complete")
        empty_query = replace(
            query,
            window_start="2026-01-01T00:00:17.1Z",
            window_end="2026-01-01T00:00:17.2Z",
        )
        empty = self.service.build(investigation_id, empty_query, context=_CONTEXT)
        self.assertEqual(empty.status, "empty")
        self.assertEqual(empty.events, ())
        limited = self.service.build(
            investigation_id, replace(query, limit=1), context=_CONTEXT
        )
        self.assertEqual(limited.events, complete.events[:1])
        self.assertTrue(limited.truncated)
        self.assertEqual(limited.matching_count, 9)
        self.assertEqual(limited.status, "incomplete")
        with self.assertRaises(StoreAccessError):
            self.service.resolve(
                limited, complete.events[-1].record.evidence_id, context=_CONTEXT
            )
        partial_id, partial_query = self._seed(
            replace(
                snapshot,
                entries=(),
                sources=(SourceAvailability("replay", "truncated", "source_limit"),),
            ),
            key="partial",
        )
        partial = self.service.build(partial_id, partial_query, context=_CONTEXT)
        self.assertEqual(partial.status, "incomplete")
        self.assertEqual(partial.events, ())
        self.assertEqual(partial.sources[0].reason, "source_limit")
        missing_id, missing_query = self._seed(key="missing")
        missing = self.service.build(missing_id, missing_query, context=_CONTEXT)
        self.assertEqual(missing.status, "snapshot_missing")
        self.assertEqual(missing.failure_code, "snapshot_missing")
        self.store.close()
        failed = self.service.build(investigation_id, query, context=_CONTEXT)
        self.assertEqual(failed.status, "storage_failure")
        self.assertEqual(failed.failure_code, "storage_failure")
        self.assertEqual(failed.events, ())
        with self.assertRaises(StoreDependencyError):
            self.service.resolve(
                complete, complete.events[0].record.evidence_id, context=_CONTEXT
            )

    def test_build_and_saved_citations_cannot_expand_authority(self) -> None:
        investigation_id, query = self._seed(_snapshot())
        timeline = self.service.build(investigation_id, query, context=_CONTEXT)
        payment = next(e for e in timeline.events if e.record.service == "payment")
        order_only = replace(_CONTEXT, allowed_services=("order",))
        narrowed = self.service.build(investigation_id, query, context=order_only)
        self.assertEqual({e.record.service for e in narrowed.events}, {"order"})
        with self.assertRaises(StoreAccessError):
            self.service.resolve(
                timeline, payment.record.evidence_id, context=order_only
            )
        with self.assertRaises(StoreAccessError):
            self.service.build(
                investigation_id, replace(query, service="payment"), context=order_only
            )
        for context in (
            replace(_CONTEXT, access_scope="other:scope"),
            replace(_CONTEXT, environment="production"),
        ):
            with self.subTest(context=context), self.assertRaises(StoreAccessError):
                self.service.build(investigation_id, query, context=context)
            with self.subTest(context=context), self.assertRaises(StoreAccessError):
                self.service.resolve(
                    timeline, payment.record.evidence_id, context=context
                )
        outside = replace(
            timeline, query=replace(query, window_start="2026-01-01T00:00:24Z")
        )
        with self.assertRaises(StoreAccessError):
            self.service.resolve(outside, payment.record.evidence_id, context=_CONTEXT)
        with self.assertRaises(StoreInputError):
            self.service.build(
                investigation_id, replace(query, limit=101), context=_CONTEXT
            )

    def test_deleted_or_changed_source_cannot_resolve_saved_citation(self) -> None:
        investigation_id, query = self._seed(_snapshot())
        timeline = self.service.build(investigation_id, query, context=_CONTEXT)
        first = timeline.events[0]
        altered = replace(
            timeline,
            events=(
                replace(first, record=replace(first.record, event="invented.event")),
            ),
        )
        with self.assertRaises(StoreConflictError):
            self.service.resolve(altered, first.record.evidence_id, context=_CONTEXT)
        self.store.cancel(
            investigation_id, access_scope=_CONTEXT.access_scope, at=_CAPTURE
        )
        self.store.delete_terminal(
            investigation_id, access_scope=_CONTEXT.access_scope, at=_CAPTURE
        )
        with self.assertRaises(StoreAccessError):
            self.service.resolve(timeline, first.record.evidence_id, context=_CONTEXT)
