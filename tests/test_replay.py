"""Acceptance checks for seeded dependency replay and evidence isolation."""

from __future__ import annotations

import json
import unittest
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

from trace_app.evidence import EvidenceBundle, EvidenceRecord, SourceAvailability
from trace_app.replay import ReplayConfig, ReplaySession

_MANIFEST = (
    Path(__file__).resolve().parents[1]
    / "evaluation"
    / "ground_truth"
    / "payment_dependency_v1.json"
)
_CAPTURED_AT = datetime(2026, 10, 5, 12, 0, tzinfo=UTC)


class ReplayTests(unittest.TestCase):
    def test_reset_replays_the_same_logical_evidence(self) -> None:
        session = ReplaySession(ReplayConfig(seed=17, mode="failure"))
        first = session.replay(collected_at=_CAPTURED_AT)
        with self.assertRaisesRegex(RuntimeError, "reset"):
            session.replay(collected_at=_CAPTURED_AT)
        session.reset()
        second = session.replay(collected_at=_CAPTURED_AT)
        self.assertEqual(first, second)
        self.assertEqual(session.notification_count, 0)

        session.reset()
        later = session.replay(collected_at=_CAPTURED_AT + timedelta(hours=1))
        self.assertEqual(
            [
                (record.evidence_id, record.observed_at, record.event)
                for record in first.evidence.records
            ],
            [
                (record.evidence_id, record.observed_at, record.event)
                for record in later.evidence.records
            ],
        )
        self.assertNotEqual(
            first.evidence.records[0].collected_at,
            later.evidence.records[0].collected_at,
        )

    def test_normal_and_timeout_follow_the_actual_dependency_path(self) -> None:
        normal = ReplaySession(ReplayConfig(seed=4, mode="normal"))
        failed = ReplaySession(ReplayConfig(seed=4, mode="failure"))
        good = normal.replay(collected_at=_CAPTURED_AT)
        bad = failed.replay(collected_at=_CAPTURED_AT)
        self.assertEqual(good.status, "accepted")
        self.assertEqual(bad.status, "dependency_failed")
        self.assertEqual(normal.notification_count, 1)
        self.assertEqual(failed.notification_count, 0)
        self.assertEqual(
            [record.event for record in good.evidence.records],
            [
                "order.requested",
                "customer.found",
                "payment.authorized",
                "notification.recorded",
                "order.accepted",
            ],
        )
        self.assertEqual(
            [record.event for record in bad.evidence.records],
            [
                "order.requested",
                "customer.found",
                "payment.timeout",
                "order.dependency_failed",
            ],
        )
        self.assertEqual(
            [record.service for record in bad.evidence.records],
            ["order", "customer", "payment", "order"],
        )
        self.assertNotEqual(
            good.evidence.records[0].evidence_id, bad.evidence.records[0].evidence_id
        )

    def test_evidence_schema_utc_identity_and_ordered_timeline(self) -> None:
        bundle = (
            ReplaySession(ReplayConfig(seed=99, mode="normal"))
            .replay(collected_at=_CAPTURED_AT)
            .evidence
        )
        exported = bundle.to_dict()
        self.assertEqual(exported["schema_version"], "1")
        self.assertEqual(
            exported["sources"],
            [
                {"source": "synthetic_replay", "status": "available", "reason": None},
                {
                    "source": "sanitized_export",
                    "status": "unavailable",
                    "reason": "no_authorized_export_supplied",
                },
            ],
        )
        self.assertEqual(
            exported["query_window"],
            {
                "start": bundle.records[0].observed_at,
                "end": bundle.records[-1].observed_at,
            },
        )
        self.assertEqual(bundle.timeline(), bundle.records)
        ids = {record.evidence_id for record in bundle.records}
        self.assertEqual(len(ids), len(bundle.records))
        self.assertEqual(
            {record.correlation_id for record in bundle.records},
            {bundle.records[0].correlation_id},
        )
        for record in bundle.records:
            self.assertEqual(
                set(record.to_dict()),
                {
                    "schema_version",
                    "evidence_id",
                    "service",
                    "environment",
                    "observed_at",
                    "collected_at",
                    "source_record_id",
                    "source_revision",
                    "access_classification",
                    "redaction_status",
                    "correlation_id",
                    "event",
                    "integrity_sha256",
                },
            )
            self.assertTrue(record.observed_at.endswith("Z"))
            self.assertEqual(record.collected_at, "2026-10-05T12:00:00Z")
            self.assertEqual(record.source_revision, "payment-dependency.v1")
            self.assertEqual(len(record.integrity_sha256), 64)

    def test_partial_source_status_and_invalid_envelopes_are_explicit(self) -> None:
        truncated = SourceAvailability("sanitized_export", "truncated", "source_limit")
        bundle = EvidenceBundle(
            records=(),
            window_start="2026-01-01T00:00:00Z",
            window_end="2026-01-01T00:01:00Z",
            sources=(truncated,),
        )
        self.assertEqual(
            bundle.to_dict()["sources"],
            [
                {
                    "source": "sanitized_export",
                    "status": "truncated",
                    "reason": "source_limit",
                }
            ],
        )
        with self.assertRaisesRegex(ValueError, "reason"):
            SourceAvailability("sanitized_export", "unavailable")
        with self.assertRaisesRegex(ValueError, "window"):
            EvidenceBundle(
                records=(),
                window_start="2026-01-01T00:01:00Z",
                window_end="2026-01-01T00:00:00Z",
                sources=(truncated,),
            )
        record = (
            ReplaySession(ReplayConfig(seed=1, mode="normal"))
            .replay(collected_at=_CAPTURED_AT)
            .evidence.records[0]
        )
        with self.assertRaisesRegex(ValueError, "UTC"):
            EvidenceRecord(
                **{
                    **{
                        key: value
                        for key, value in record.to_dict().items()
                        if key != "schema_version"
                    },
                    "observed_at": "2026-01-01T00:00:00",
                }
            )

    def test_ground_truth_is_separate_from_operational_export(self) -> None:
        manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
        failed = ReplaySession(ReplayConfig(seed=4, mode="failure")).replay(
            collected_at=_CAPTURED_AT
        )
        operational = json.loads(failed.evidence.to_json())
        self.assertEqual(
            manifest["expected_evidence"],
            [record["event"] for record in operational["records"]],
        )
        self.assertEqual(manifest["cause_service"], "payment")
        for forbidden in (
            "cause_service",
            "mechanism",
            "symptoms",
            "expected_evidence",
            "ground_truth",
            "label",
            "failure",
        ):
            self.assertNotIn(forbidden, json.dumps(operational))
        self.assertEqual(
            set(operational), {"schema_version", "query_window", "sources", "records"}
        )

    def test_invalid_configuration_and_non_utc_collection_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ReplayConfig(seed=-1, mode="normal")
        with self.assertRaises(ValueError):
            ReplayConfig(seed=True, mode="normal")
        with self.assertRaises(ValueError):
            ReplayConfig(seed=1, mode="unknown")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            ReplayConfig(seed=1, mode="normal", environment="production")  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            ReplayConfig(seed=1, mode="normal", version="other")
        session = ReplaySession(ReplayConfig(seed=1, mode="normal"))
        with self.assertRaisesRegex(ValueError, "UTC"):
            session.replay(collected_at=datetime(2026, 1, 1))
        with self.assertRaisesRegex(ValueError, "UTC"):
            session.replay(
                collected_at=datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=1)))
            )


if __name__ == "__main__":
    unittest.main()
