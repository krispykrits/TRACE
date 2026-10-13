"""Private actual SQLite ledger and spawned Azure-transport adapter workflows."""

from __future__ import annotations

import functools
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from typing import Any, cast

from tests.fixtures.provider_policy import (
    NOW,
    SCOPE,
    SETTINGS,
    TEST_AUTH_VALUE,
    Authority,
    Clock,
    ProcessHttpConnection,
    call,
    record,
)
from trace_app.adapters.models.azure import AzureResponsesTransport
from trace_app.adapters.models.journal import ModelPricing, SqliteProviderJournal
from trace_app.adapters.models.process import ProcessModelProvider
from trace_app.investigation.provider import (
    AdmissionGuard,
    ModelErrorCode,
    ModelProviderError,
    ModelUsage,
)
from trace_app.investigation.provider_policy import (
    EvidenceField,
    PolicyModelProvider,
    PromptTemplate,
    Sensitivity,
)
from trace_app.runtime.logging import configure_logging


def metadata(request_id: str, scope_id: str = "scope-1") -> dict[str, object]:
    return {
        "request_id": request_id,
        "scope_id": scope_id,
        "policy_version": "trace-provider-data-policy.v1",
        "evidence_ids": [],
        "outcome": "structured_response_received",
    }


class ProviderJournalTests(unittest.TestCase):
    def test_atomic_reservations_missing_usage_and_month_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal"
            pricing = ModelPricing("unit-price.v1", 1, 1)
            first = SqliteProviderJournal(
                path, pricing, monthly_limit_nusd=100, initial_spend_nusd=10, now=NOW
            )
            second = SqliteProviderJournal(
                path, pricing, monthly_limit_nusd=100, initial_spend_nusd=10, now=NOW
            )
            first.begin(metadata("one"), (), 30, 30, NOW)
            with self.assertRaises(ModelProviderError) as failure:
                second.begin(metadata("two", "scope-2"), (), 20, 20, NOW)
            self.assertEqual(failure.exception.code, ModelErrorCode.BUDGET)
            first.finish(metadata("one"), ModelUsage(), True, NOW)
            with self.assertRaises(ModelProviderError):
                second.begin(metadata("three", "scope-2"), (), 20, 20, NOW)
            second.begin(metadata("four", "scope-2"), (), 20, 20, NOW + 40 * 86400)
            with sqlite3.connect(path) as connection:
                entry = json.loads(
                    connection.execute(
                        "SELECT metadata FROM attempts WHERE request_id='one'"
                    ).fetchone()[0]
                )
            self.assertIsNone(entry["estimated_cost_nusd"])
            self.assertEqual(entry["reserved_or_estimated_charge_nusd"], 60)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_known_usage_reconciles_reserved_estimate_and_zero_dispatch_refunds(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            journal = SqliteProviderJournal(
                Path(directory) / "journal",
                ModelPricing("unit.v1", 1, 2),
                monthly_limit_nusd=100,
                initial_spend_nusd=0,
                now=NOW,
            )
            journal.begin(metadata("one"), (), 20, 20, NOW)
            journal.finish(metadata("one"), ModelUsage(10, 10), True, NOW)
            journal.begin(metadata("two", "scope-2"), (), 20, 20, NOW)
            journal.finish(metadata("two", "scope-2"), ModelUsage(), False, NOW)
            journal.begin(metadata("three", "scope-2"), (), 20, 20, NOW)

    def test_timeout_and_crashed_pending_attempt_block_same_scope_replay(self) -> None:
        for outcome in (
            "reserved",
            ModelErrorCode.TIMEOUT.value,
            ModelErrorCode.DEPENDENCY.value,
        ):
            with tempfile.TemporaryDirectory() as directory:
                journal = SqliteProviderJournal(
                    Path(directory) / "journal",
                    ModelPricing("unit.v1", 1, 1),
                    monthly_limit_nusd=1000,
                    initial_spend_nusd=0,
                    now=NOW,
                )
                journal.begin(metadata("one"), (), 10, 10, NOW)
                if outcome != "reserved":
                    values = metadata("one")
                    values["outcome"] = outcome
                    journal.finish(values, ModelUsage(), True, NOW)
                with self.assertRaises(ModelProviderError) as failure:
                    journal.begin(metadata("two"), (), 10, 10, NOW)
                self.assertEqual(failure.exception.code, ModelErrorCode.BUDGET)

    def test_journal_configuration_privacy_and_price_change_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "journal"
            pricing = ModelPricing("unit.v1", 1, 1)
            SqliteProviderJournal(
                path, pricing, monthly_limit_nusd=100, initial_spend_nusd=0, now=NOW
            )
            with self.assertRaises(ModelProviderError):
                SqliteProviderJournal(
                    path,
                    ModelPricing("changed.v1", 2, 2),
                    monthly_limit_nusd=100,
                    initial_spend_nusd=0,
                    now=NOW,
                )
            path.chmod(0o644)
            with self.assertRaises(ModelProviderError):
                SqliteProviderJournal(
                    path, pricing, monthly_limit_nusd=100, initial_spend_nusd=0, now=NOW
                )


class AzurePolicyProcessTests(unittest.TestCase):
    def test_spawned_transport_enforces_policy_and_private_sqlite_provenance(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stream = io.StringIO()
            configure_logging(stream=stream, correlation_id="policy-integration")
            clock = Clock()
            guard = AdmissionGuard(b"nonfunctional-process-capability!" * 2, clock)
            transport = AzureResponsesTransport(
                SETTINGS,
                TEST_AUTH_VALUE,
                guard,
                connection_factory=cast(
                    Any, functools.partial(ProcessHttpConnection, capture=root / "http")
                ),
            )
            process = ProcessModelProvider(
                SETTINGS.configuration(),
                SETTINGS.capabilities(),
                transport,
                credential_present=True,
                admission_guard=guard,
            )
            authority = Authority()
            authority.records["evidence-1"] = record(
                fields=(
                    EvidenceField(
                        "observation",
                        "safe event for person@example.invalid " + TEST_AUTH_VALUE,
                        Sensitivity.INTERNAL,
                        True,
                    ),
                )
            )
            journal = SqliteProviderJournal(
                root / "journal",
                ModelPricing("fixture.v1", 1, 1),
                monthly_limit_nusd=1_000_000,
                initial_spend_nusd=0,
                now=NOW,
            )
            policy = PolicyModelProvider(
                SETTINGS.configuration(),
                process,
                authority,
                journal,
                guard,
                SCOPE,
                {
                    "fixture-prompt-v1": PromptTemplate(
                        "Return a JSON health object.", "health.v1"
                    )
                },
                known_secrets=(TEST_AUTH_VALUE,),
                read_clock=clock,
            )
            result = policy.generate(call())
            self.assertEqual(result.structured_response(SCOPE), {"status": "ok"})
            sent = json.loads((root / "http").read_text())
            self.assertEqual(sent["body"]["model"], "fixture-deployment")
            self.assertNotIn(TEST_AUTH_VALUE, json.dumps(sent) + stream.getvalue())
            self.assertNotIn(
                "person@example.invalid", json.dumps(sent) + stream.getvalue()
            )
            audit = [
                json.loads(row)
                for row in stream.getvalue().splitlines()
                if json.loads(row)["event"] == "models.policy.completed"
            ][0]
            self.assertEqual(audit["usage"]["input_tokens"], 23)
            self.assertEqual(audit["usage"]["output_tokens"], 24)
            with sqlite3.connect(root / "journal") as connection:
                saved = connection.execute("SELECT metadata FROM attempts").fetchone()[
                    0
                ]
                provenance = connection.execute(
                    "SELECT provenance FROM redactions"
                ).fetchall()
            self.assertEqual(len(provenance), 2)
            self.assertNotIn(TEST_AUTH_VALUE, saved + repr(provenance))
            self.assertNotIn("person@example.invalid", saved + repr(provenance))
            with self.assertRaises(ModelProviderError):
                process.generate(
                    replace_request_without_receipt(result._result.request)
                )
            self.assertEqual(len((root / "http").read_text().splitlines()), 1)


def replace_request_without_receipt(request: Any) -> Any:
    from dataclasses import replace

    return replace(request, admission=None)
