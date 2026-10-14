"""Actual SQLite job/attempt state and monthly journal; injected clock/fake provider."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from threading import Barrier, Thread

from tests.fixtures.execution import PRICING, QUERY, TOOL_SCOPE
from tests.fixtures.provider_policy import (
    NOW,
    SETTINGS,
    Clock,
    RecordingProvider,
    call,
    record,
)
from trace_app.adapters.models.journal import SqliteProviderJournal
from trace_app.adapters.storage.sqlite.investigations import SQLiteInvestigationStore
from trace_app.bootstrap import create_execution_session, create_tool_session
from trace_app.evidence.models import SourceAvailability
from trace_app.investigation.execution import (
    ExecutionIdentity,
    ExecutionPolicy,
    ExecutionRejected,
)
from trace_app.investigation.models import EvidenceSnapshot, InvestigationRequest
from trace_app.investigation.provider import (
    AdmissionGuard,
    ModelErrorCode,
    ModelProviderError,
    ModelUsage,
)
from trace_app.investigation.provider_policy import (
    PolicyModelProvider,
    PromptTemplate,
    ProviderScope,
)


class ExecutionIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "jobs.sqlite"
        self.clock = Clock()
        self.created = datetime.fromtimestamp(NOW - 2, timezone.utc)
        with SQLiteInvestigationStore(self.path) as store:
            job = store.submit(
                InvestigationRequest(
                    "budget-fixture",
                    "order",
                    "test",
                    "fixture-scope",
                    "2026-01-01T00:00:00Z",
                    "2026-01-01T00:00:02Z",
                ),
                at=self.created,
            )
            claimed = store.claim_next(
                lease_seconds=120,
                at=datetime.fromtimestamp(NOW, timezone.utc),
            )
            assert claimed is not None and claimed.active_attempt_id is not None
            self.identity = ExecutionIdentity(
                job.investigation_id,
                claimed.active_attempt_id,
                "corr-budget-integration",
                "fixture-scope",
            )

    def session(self, policy: ExecutionPolicy = ExecutionPolicy(), *, identity=None):
        return create_execution_session(
            evidence_db=self.path,
            identity=identity or self.identity,
            pricing=PRICING,
            policy=policy,
            clock=self.clock,
        )

    def saved(self):
        with sqlite3.connect(self.path) as connection:
            state = json.loads(
                connection.execute("SELECT state FROM execution_runs").fetchone()[0]
            )
            records = [
                json.loads(row[0])
                for row in connection.execute("SELECT metadata FROM execution_calls")
            ]
        return state, records

    def test_restart_keeps_counts_token_reservations_and_original_deadline(
        self,
    ) -> None:
        policy = ExecutionPolicy(max_model_calls=2, deadline_ms=1000)
        first = self.session(policy)
        ticket = first.begin("model")
        first.reserve(
            ticket,
            100,
            20,
            {"policy_version": "trace-provider-data-policy.v1", "evidence_ids": ["e1"]},
        )
        first.dispatch(ticket)
        first.finish(ticket, "structured_response_received", ModelUsage())
        second = self.session(policy)
        self.clock.now += 0.5
        second_ticket = second.begin("model")
        second.reserve(second_ticket, 100, 20, {})
        second.dispatch(second_ticket)
        second.finish(second_ticket, "structured_response_received", ModelUsage(5, 2))
        third = self.session(policy)
        with self.assertRaises(ExecutionRejected) as failure:
            third.begin("model")
        self.assertEqual(failure.exception.outcome, "budget_exhausted")
        state, records = self.saved()
        self.assertEqual(state["started_at"], NOW)
        self.assertEqual(state["charged_tokens"], 127)
        self.assertEqual(state["model_calls"], 3)
        self.assertEqual(len(records), 3)
        self.assertIsNone(records[0]["estimated_cost_nusd"])
        self.assertEqual(records[1]["estimated_cost_nusd"], 16)
        self.assertEqual(records[1]["end_to_end_duration_ms"], 2500)

    def test_pending_dispatch_survives_restart_and_blocks_replay(self) -> None:
        session = self.session()
        ticket = session.begin("model")
        session.reserve(ticket, 100, 20, {})
        session.dispatch(ticket)
        restarted = self.session()
        for kind in ("model", "tool"):
            with self.assertRaises(ExecutionRejected) as failure:
                restarted.begin(kind)
            self.assertEqual(failure.exception.outcome, "call_active")
        state, records = self.saved()
        self.assertEqual(state["charged_tokens"], 120)
        self.assertTrue(records[0]["dispatched"])

    def test_current_durable_cancellation_lease_and_attempt_identity_gate_every_dispatch(
        self,
    ) -> None:
        session = self.session()
        ticket = session.begin("model")
        session.reserve(ticket, 100, 20, {})
        with SQLiteInvestigationStore(self.path) as store:
            store.cancel(
                self.identity.investigation_id,
                access_scope=self.identity.access_scope,
                at=datetime.fromtimestamp(NOW, timezone.utc),
            )
        with self.assertRaises(ExecutionRejected) as failure:
            session.dispatch(ticket)
        self.assertEqual(failure.exception.outcome, "cancelled")
        self.assertEqual(session.finish(ticket, "cancelled"), "cancelled")
        self.assertEqual(self.saved()[0]["charged_tokens"], 0)

    def test_lease_expiry_and_recovery_do_not_reset_aggregate_budget(self) -> None:
        session = self.session()
        ticket = session.begin("tool")
        session.dispatch(ticket)
        session.finish(ticket, "ok")
        self.clock.now += 121
        with self.assertRaises(ExecutionRejected) as failure:
            session.begin("tool")
        self.assertEqual(failure.exception.outcome, "expired")
        with SQLiteInvestigationStore(self.path) as store:
            store.recover(at=datetime.fromtimestamp(self.clock.now, timezone.utc))
            claimed = store.claim_next(
                lease_seconds=120,
                at=datetime.fromtimestamp(self.clock.now, timezone.utc),
            )
        assert claimed is not None and claimed.active_attempt_id is not None
        new_identity = replace(self.identity, attempt_id=claimed.active_attempt_id)
        with self.assertRaises(ExecutionRejected):
            self.session(identity=new_identity).begin("model")
        self.assertEqual(self.saved()[0]["started_at"], NOW)

    def test_policy_pricing_and_scope_changes_cannot_reset_limits(self) -> None:
        self.session()
        with self.assertRaises(ExecutionRejected):
            self.session(ExecutionPolicy(max_model_calls=4))
        with self.assertRaises(ExecutionRejected):
            self.session(identity=replace(self.identity, access_scope="other-scope"))
        with self.assertRaises(ExecutionRejected):
            create_execution_session(
                evidence_db=self.path,
                identity=self.identity,
                pricing=replace(PRICING, version="changed.v1"),
                clock=self.clock,
            )
        self.assertEqual(self.saved()[0]["model_calls"], 0)

    def test_simultaneous_sessions_admit_only_one_call_atomically(self) -> None:
        self.session()
        barrier = Barrier(2)
        outcomes: list[str] = []

        def invoke():
            session = self.session()
            barrier.wait(timeout=2)
            try:
                session.begin("tool")
                outcomes.append("admitted")
            except ExecutionRejected as error:
                outcomes.append(error.outcome)

        threads = [Thread(target=invoke) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=3)
            self.assertFalse(thread.is_alive())
        self.assertEqual(sorted(outcomes), ["admitted", "call_active"])
        self.assertEqual(len(self.saved()[1]), 2)

    def test_stale_attempt_cannot_poison_current_worker_or_extend_lease_bounds(
        self,
    ) -> None:
        session = self.session()
        with self.assertRaises(ExecutionRejected):
            self.session(
                identity=replace(self.identity, attempt_id=self.identity.attempt_id + 1)
            )
        self.assertIsNone(self.saved()[0]["stop_reason"])
        self.clock.now += 119
        ticket = session.begin("model")
        self.assertLessEqual(ticket.timeout_ms, 1000)
        session.reserve(ticket, 100, 20, {})
        self.assertLessEqual(session.dispatch(ticket), 1000)
        session.finish(ticket, "structured_response_received", ModelUsage(5, 2))

    def test_v1_migration_preserves_jobs_and_adds_empty_execution_tables(self) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute("DROP TABLE execution_calls")
            connection.execute("DROP TABLE execution_runs")
            connection.execute("PRAGMA user_version=1")
        with SQLiteInvestigationStore(self.path) as store:
            self.assertEqual(
                store.get_investigation(
                    self.identity.investigation_id,
                    access_scope=self.identity.access_scope,
                ).active_attempt_id,
                self.identity.attempt_id,
            )
        self.session()
        with sqlite3.connect(self.path) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 2)
        self.assertEqual(self.saved()[1], [])

    def provider(self):
        session = self.session()
        scope = ProviderScope("fixture-user", self.identity.investigation_id)

        class Authority:
            def resolve(self, current, evidence_id):
                return (
                    record()
                    if current == scope and evidence_id == "evidence-1"
                    else None
                )

        guard = AdmissionGuard(b"nonfunctional-budget-capability!" * 2, self.clock)
        transport = RecordingProvider(guard)
        journal_path = Path(self.directory.name) / "provider.sqlite"
        journal = SqliteProviderJournal(
            journal_path,
            PRICING,
            monthly_limit_nusd=1_000_000,
            initial_spend_nusd=0,
            now=self.clock(),
        )
        provider = PolicyModelProvider(
            SETTINGS.configuration(),
            transport,
            Authority(),
            journal,
            guard,
            scope,
            {
                "fixture-prompt-v1": PromptTemplate(
                    "Return a JSON health object.", "health.v1"
                )
            },
            read_clock=self.clock,
            duration_clock=self.clock,
            execution=session,
        )
        return provider, transport, journal_path

    def test_actual_monthly_and_execution_ledgers_correlate_without_raw_content(
        self,
    ) -> None:
        provider, transport, journal_path = self.provider()
        provider.generate(call())
        with sqlite3.connect(journal_path) as connection:
            monthly = json.loads(
                connection.execute("SELECT metadata FROM attempts").fetchone()[0]
            )
        _, calls = self.saved()
        execution = calls[0]
        self.assertEqual(monthly["request_id"], execution["call_id"])
        self.assertEqual(monthly["attempt_id"], execution["attempt_id"])
        self.assertEqual(monthly["correlation_id"], execution["correlation_id"])
        self.assertEqual(
            monthly["estimated_cost_nusd"], execution["estimated_cost_nusd"]
        )
        self.assertEqual(monthly["usage"], execution["usage"])
        self.assertNotIn(
            "Synthetic observation", json.dumps(monthly) + json.dumps(execution)
        )
        self.assertEqual(len(transport.requests), 1)

    def test_late_reply_cancellation_withholds_response_and_records_both_journals(
        self,
    ) -> None:
        provider, transport, journal_path = self.provider()
        generate = transport.generate

        def cancelling(request):
            reply = generate(request)
            with SQLiteInvestigationStore(self.path) as store:
                store.cancel(
                    self.identity.investigation_id,
                    access_scope=self.identity.access_scope,
                    at=datetime.fromtimestamp(NOW, timezone.utc),
                )
            return reply

        transport.generate = cancelling
        with self.assertRaises(ModelProviderError) as failure:
            provider.generate(call())
        self.assertEqual(failure.exception.code, ModelErrorCode.CANCELLED)
        with sqlite3.connect(journal_path) as connection:
            monthly = json.loads(
                connection.execute("SELECT metadata FROM attempts").fetchone()[0]
            )
        self.assertEqual(monthly["outcome"], "cancelled")
        self.assertEqual(self.saved()[1][0]["outcome"], "cancelled")
        self.assertEqual(monthly["usage"]["input_tokens"], 23)
        with self.assertRaises(ModelProviderError):
            provider.generate(call())
        self.assertEqual(len(transport.requests), 1)

    def test_missing_private_database_fails_closed_without_recreating(self) -> None:
        session = self.session()
        self.path.unlink()
        with self.assertRaises(ExecutionRejected) as failure:
            session.begin("model")
        self.assertEqual(failure.exception.outcome, "audit_unavailable")
        self.assertFalse(self.path.exists())

    def test_corrupt_or_incomplete_state_cannot_silently_reset_accounting(self) -> None:
        self.session()
        original, _ = self.saved()
        for change in ("missing", "negative", "unbounded"):
            state = dict(original)
            if change == "missing":
                del state["charged_tokens"]
            elif change == "negative":
                state["charged_tokens"] = -1
            else:
                state["last_at"] = float("inf")
            with sqlite3.connect(self.path) as connection:
                connection.execute(
                    "UPDATE execution_runs SET state=?", (json.dumps(state),)
                )
            with (
                self.subTest(change=change),
                self.assertRaises(ExecutionRejected) as failure,
            ):
                self.session()
            self.assertEqual(failure.exception.outcome, "audit_unavailable")

    def test_actual_readonly_tool_worker_uses_shared_durable_admission(self) -> None:
        with SQLiteInvestigationStore(self.path) as store:
            store.ingest_snapshot(
                self.identity.investigation_id,
                EvidenceSnapshot(
                    (),
                    QUERY["window_start"],
                    QUERY["window_end"],
                    (SourceAvailability("synthetic_replay", "available"),),
                ),
                access_scope=self.identity.access_scope,
                at=datetime.fromtimestamp(NOW, timezone.utc),
            )
        session = self.session(ExecutionPolicy(max_tool_calls=1))
        scope = replace(
            TOOL_SCOPE,
            investigation_id=self.identity.investigation_id,
            correlation_id=self.identity.correlation_id,
            evidence=replace(
                TOOL_SCOPE.evidence, access_scope=self.identity.access_scope
            ),
        )
        tools = create_tool_session(
            evidence_db=self.path,
            corpus_db=self.path,
            index_root=Path(self.directory.name),
            scope=scope,
            execution=session,
            read_clock=lambda: datetime.fromtimestamp(self.clock(), timezone.utc),
        )
        first = tools.invoke("logs.query", QUERY)
        self.assertEqual(first.payload.status, "empty")
        self.assertEqual(
            tools.invoke("logs.query", QUERY).payload.status, "budget_exhausted"
        )
        records = self.saved()[1]
        self.assertEqual(len(records), 2)
        self.assertTrue(records[0]["dispatched"])
        self.assertFalse(records[1]["dispatched"])
        self.assertEqual(records[0]["call_id"], first.audit.attempt_id)
        self.assertEqual(records[0]["tool_version"], first.audit.version)

    def test_partial_usage_above_reservation_keeps_unknown_dimension_in_both_ledgers(
        self,
    ) -> None:
        provider, transport, journal_path = self.provider()
        transport.reply = replace(transport.reply, usage=ModelUsage(100_000))
        with self.assertRaises(ModelProviderError) as failure:
            provider.generate(call())
        self.assertEqual(failure.exception.code, ModelErrorCode.BUDGET)
        with sqlite3.connect(journal_path) as connection:
            monthly = json.loads(
                connection.execute("SELECT metadata FROM attempts").fetchone()[0]
            )
        execution = self.saved()[1][0]
        expected = PRICING.estimate(100_000, 256)
        self.assertIsNone(monthly["estimated_cost_nusd"])
        self.assertIsNone(execution["estimated_cost_nusd"])
        self.assertEqual(monthly["reserved_or_estimated_charge_nusd"], expected)
        self.assertEqual(execution["reserved_or_estimated_charge_nusd"], expected)
        self.assertEqual(monthly["usage"], ModelUsage(100_000).to_dict())
