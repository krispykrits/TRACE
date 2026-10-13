"""Deterministic suite, mechanism, capture-gap and operational isolation checks."""

from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

from trace_app.adapters.storage.sqlite.investigations import SQLiteInvestigationStore
from trace_app.demo.order_workflow import BoundaryContext, DependencyUnavailable
from trace_app.demo.scenarios import CASE_IDS, ScenarioConfig, ScenarioSession, _Payment
from trace_app.evidence.models import EvidenceRecord
from trace_app.evidence.queries import (
    EvidenceQuery,
    EvidenceQueryService,
    TrustedQueryContext,
)
from trace_app.investigation.models import InvestigationRequest, MetricPayload

_CAPTURE = datetime(2026, 10, 12, 12, tzinfo=UTC)
_MANIFEST_PATH = (
    Path(__file__).resolve().parents[2] / "evaluation/ground_truth/mvp_suite_v1.json"
)


def _replay(case: str, *, distractor: bool = True):
    return ScenarioSession(
        ScenarioConfig(case, 17, notification_deployment=distractor)
    ).replay(collected_at=_CAPTURE)


class ScenarioTests(unittest.TestCase):
    def test_every_case_resets_and_retains_identity_across_collection_runs(
        self,
    ) -> None:
        for case in CASE_IDS:
            with self.subTest(case=case):
                session = ScenarioSession(ScenarioConfig(case, 17))
                first = session.replay(collected_at=_CAPTURE)
                self.assertEqual(session.notification_count, 0)
                self.assertEqual(first.status, "dependency_failed")
                with self.assertRaisesRegex(RuntimeError, "reset"):
                    session.replay(collected_at=_CAPTURE)
                session.reset()
                self.assertEqual(first, session.replay(collected_at=_CAPTURE))
                session.reset()
                later = session.replay(collected_at=_CAPTURE + timedelta(hours=1))
                self.assertEqual(
                    [
                        replace(
                            e.record,
                            collected_at=first.snapshot.entries[i].record.collected_at,
                        )
                        for i, e in enumerate(later.snapshot.entries)
                    ],
                    [e.record for e in first.snapshot.entries],
                )
                self.assertNotEqual(
                    first.snapshot.entries[0].record.collected_at,
                    later.snapshot.entries[0].record.collected_at,
                )
                other_seed = ScenarioSession(ScenarioConfig(case, 18)).replay(
                    collected_at=_CAPTURE
                )
                self.assertNotEqual(
                    first.snapshot.entries[0].record.evidence_id,
                    other_seed.snapshot.entries[0].record.evidence_id,
                )

    def test_budget_and_work_counterfactuals_drive_failure_not_time_order(self) -> None:
        context = BoundaryContext("payment", "test", "counterfactual")
        events: list[str] = []
        for budget, work, fails in (
            (5, 10, True),
            (50, 10, False),
            (50, 100, True),
            (50, 50, False),
        ):
            with self.subTest(budget=budget, work=work):
                events.clear()
                payment = _Payment(
                    lambda s, event, k, p: events.append(event),
                    budget_ms=budget,
                    work_ms=work,
                )
                if fails:
                    with self.assertRaises(DependencyUnavailable):
                        payment.authorize(
                            order_id="order-17", amount_cents=1250, context=context
                        )
                    self.assertEqual(events[-1], "payment.timeout")
                else:
                    self.assertEqual(
                        payment.authorize(
                            order_id="order-17", amount_cents=1250, context=context
                        ),
                        "auth-order-17",
                    )
                    self.assertEqual(events[-1], "payment.authorized")
        for case, expected in (("c01", [50, 5, 10]), ("c02", [50, 50, 100])):
            result = _replay(case)
            self.assertEqual(
                [
                    e.payload.value
                    for e in result.snapshot.entries
                    if isinstance(e.payload, MetricPayload)
                ],
                expected,
            )
            self.assertIn(
                "payment.timeout", [e.record.event for e in result.snapshot.entries]
            )

    def test_noncausal_deployment_removal_preserves_all_other_evidence(self) -> None:
        for case in CASE_IDS:
            with self.subTest(case=case):
                with_deployment = _replay(case)
                without = _replay(case, distractor=False)
                self.assertEqual(with_deployment.status, without.status)
                self.assertEqual(
                    tuple(
                        e
                        for e in with_deployment.snapshot.entries
                        if e.record.service != "notification"
                    ),
                    without.snapshot.entries,
                )
                self.assertEqual(
                    with_deployment.snapshot.window_end, without.snapshot.window_end
                )
                deployment = with_deployment.snapshot.entries[-1]
                self.assertEqual(deployment.record.service, "notification")
                self.assertEqual(
                    asdict(deployment.payload), {"revision": "v2", "phase": "completed"}
                )

    def test_missing_cases_have_matched_observations_and_explicit_capture_gaps(
        self,
    ) -> None:
        first, second = _replay("c03"), _replay("c04")

        def observations(result):
            return [
                (
                    e.kind,
                    e.record.service,
                    e.record.event,
                    e.record.observed_at,
                    e.payload,
                )
                for e in result.snapshot.entries
            ]

        self.assertEqual(observations(first), observations(second))
        self.assertEqual(first.snapshot.sources, second.snapshot.sources)
        self.assertEqual(
            [s.source for s in first.snapshot.sources if s.reason == "capture_gap"],
            ["payment_logs", "payment_metrics", "payment_deployments"],
        )
        self.assertFalse(
            any(e.record.service == "payment" for e in first.snapshot.entries)
        )
        complete = _replay("c01")
        log = next(e.record for e in complete.snapshot.entries if e.kind == "log")
        metric = next(e.record for e in complete.snapshot.entries if e.kind == "metric")
        self.assertEqual(
            datetime.fromisoformat(metric.collected_at)
            - datetime.fromisoformat(log.collected_at),
            timedelta(seconds=30),
        )
        self.assertNotEqual(metric.observed_at, metric.collected_at)

    def test_manifest_matches_records_support_and_split_policy(self) -> None:
        manifest = json.loads(_MANIFEST_PATH.read_text())
        self.assertEqual(manifest["suite_version"], "mvp-suite.v1")
        self.assertEqual({c["case_id"] for c in manifest["cases"]}, set(CASE_IDS))
        groups = set()
        for case in manifest["cases"]:
            self.assertEqual(case["configuration"]["seed"], manifest["seeds"][0])
            result = _replay(case["case_id"])
            entries = result.snapshot.entries
            self.assertEqual(case["expected_events"], [e.record.event for e in entries])
            ordinals = {e.record.evidence_id.rsplit("-", 1)[1] for e in entries}
            self.assertTrue(set(case["supporting_ordinals"]) <= ordinals)
            self.assertFalse(set(case["missing_ordinals"]) & ordinals)
            self.assertTrue(case["abstention_conditions"])
            self.assertTrue(case["causal_chain"])
            groups.add(case["template_group"])
        self.assertEqual(groups, set(manifest["split_policy"]["development_groups"]))
        self.assertEqual(manifest["split_policy"]["validation_groups"], [])
        self.assertEqual(manifest["split_policy"]["final_test_groups"], [])
        self.assertEqual(
            manifest["split_policy"]["historical_replay"]["status"], "blocked"
        )
        self.assertEqual(manifest["cases"][2]["expected_assessment"], "abstained")
        self.assertNotEqual(
            manifest["cases"][2]["cause_label"], manifest["cases"][3]["cause_label"]
        )

    def test_roundtrip_queries_and_exports_exclude_evaluator_fields(self) -> None:
        forbidden = {
            "case_id",
            "seed",
            "cause_label",
            "cause_service",
            "mechanism",
            "ground_truth",
            "supporting_ordinals",
            "expected_assessment",
            "template_group",
        }

        def check_keys(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden & value.keys())
                for child in value.values():
                    check_keys(child)
            elif isinstance(value, list):
                for child in value:
                    check_keys(child)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.db"
            for case in CASE_IDS:
                result = _replay(case)
                snapshot = result.snapshot
                check_keys(result.to_dict())
                for entry in snapshot.entries:
                    self.assertEqual(
                        entry.record, EvidenceRecord.from_dict(entry.record.to_dict())
                    )
                    with self.assertRaisesRegex(ValueError, "cause_label"):
                        EvidenceRecord.from_dict(
                            {**entry.record.to_dict(), "cause_label": "injected"}
                        )
                request = InvestigationRequest(
                    case,
                    "order",
                    "test",
                    "local:synthetic",
                    snapshot.window_start,
                    snapshot.window_end,
                )
                with SQLiteInvestigationStore(path) as store:
                    investigation = store.submit(request, at=_CAPTURE)
                    store.ingest_snapshot(
                        investigation.investigation_id,
                        snapshot,
                        access_scope="local:synthetic",
                        at=_CAPTURE,
                    )
                with SQLiteInvestigationStore(path) as store:
                    context = TrustedQueryContext(
                        "local:synthetic",
                        "test",
                        ("order", "customer", "payment", "notification"),
                    )
                    response = EvidenceQueryService(store).query(
                        investigation.investigation_id,
                        EvidenceQuery(snapshot.window_start, snapshot.window_end),
                        context=context,
                    )
                    self.assertEqual(set(response.entries), set(snapshot.entries))
                    self.assertEqual(response.status, "incomplete")
                    for entry in response.entries:
                        resolved = EvidenceQueryService(store).get_by_id(
                            investigation.investigation_id,
                            entry.record.evidence_id,
                            EvidenceQuery(snapshot.window_start, snapshot.window_end),
                            context=context,
                        )
                        self.assertEqual(resolved, entry)

    def test_invalid_configuration_and_capture_time_fail_before_replay(self) -> None:
        for change in (
            {"case_id": "unknown"},
            {"seed": True},
            {"seed": -1},
            {"seed": 1_000_000_001},
            {"environment": "production"},
            {"version": "v2"},
            {"notification_deployment": 1},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                ScenarioConfig(**{"case_id": "c01", "seed": 17, **change})  # type: ignore[arg-type]
        session = ScenarioSession(ScenarioConfig("c01", 17))
        with self.assertRaisesRegex(ValueError, "UTC"):
            session.replay(collected_at=datetime(2026, 1, 1))
        self.assertEqual(
            session.replay(collected_at=_CAPTURE).status, "dependency_failed"
        )
