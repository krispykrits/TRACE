"""Shared model/tool limits: fake dependencies, injected time, no paid calls."""

from __future__ import annotations

import io
import json
import unittest
from dataclasses import replace

from tests.fixtures.execution import (
    QUERY,
    TOOL_SCOPE,
    Audit,
    Backend,
    execution_fixture,
)
from tests.fixtures.provider_policy import (
    TEST_AUTH_VALUE,
    EvidenceField,
    Sensitivity,
    call,
    policy_fixture,
    record,
)
from trace_app.investigation.execution import ExecutionPolicy, ExecutionRejected
from trace_app.investigation.provider import (
    ModelCallBounds,
    ModelErrorCode,
    ModelProviderError,
    ModelReply,
    ModelUsage,
)
from trace_app.investigation.tools import ToolPayload, ToolSession
from trace_app.runtime.logging import configure_logging


class ExecutionContracts(unittest.TestCase):
    def fixture(self, policy: ExecutionPolicy = ExecutionPolicy()):
        execution, ledger, clock = execution_fixture(policy)
        provider, transport, authority, journal = policy_fixture(
            execution=execution,
            read_clock=clock,
            duration_clock=clock,
        )
        backend = Backend()
        tools = ToolSession(
            backend, TOOL_SCOPE, Audit(), clock=clock, execution=execution
        )
        return (
            execution,
            ledger,
            clock,
            provider,
            transport,
            authority,
            journal,
            tools,
            backend,
        )

    def test_shared_counts_are_durable_and_exhaustion_stops_both_ports(self) -> None:
        _, ledger, _, provider, transport, _, _, tools, backend = self.fixture(
            ExecutionPolicy(max_model_calls=1)
        )
        self.assertEqual(tools.invoke("logs.query", QUERY).payload.status, "ok")
        provider.generate(call())
        with self.assertRaises(ModelProviderError) as failure:
            provider.generate(call())
        self.assertEqual(failure.exception.code, ModelErrorCode.BUDGET)
        self.assertEqual(
            tools.invoke("logs.query", QUERY).payload.status, "budget_exhausted"
        )
        self.assertEqual((len(transport.requests), backend.calls), (1, 1))
        self.assertEqual(len(ledger.records), 4)

    def test_invalid_tool_calls_count_and_do_not_dispatch(self) -> None:
        _, ledger, _, _, transport, _, _, tools, backend = self.fixture(
            ExecutionPolicy(max_tool_calls=1)
        )
        self.assertEqual(
            tools.invoke("sql.query", {"password": "private"}).payload.status,
            "validation_error",
        )
        self.assertEqual(
            tools.invoke("logs.query", QUERY).payload.status, "budget_exhausted"
        )
        self.assertEqual((backend.calls, len(transport.requests)), (0, 0))
        self.assertNotIn("password", json.dumps(ledger.records))

    def test_expiry_and_terminal_state_prevent_new_model_or_tool_dispatch(self) -> None:
        for reason in ("cancelled", "completed", "failed", "expired"):
            _, ledger, _, provider, transport, _, _, tools, backend = self.fixture()
            ledger.terminal = reason
            with self.subTest(reason=reason), self.assertRaises(ModelProviderError):
                provider.generate(call())
            self.assertNotIn(
                tools.invoke("logs.query", QUERY).payload.status,
                ("ok", "partial", "empty"),
            )
            self.assertEqual((len(transport.requests), backend.calls), (0, 0))
        _, ledger, clock, provider, transport, _, _, tools, backend = self.fixture(
            ExecutionPolicy(deadline_ms=100)
        )
        clock.now += 0.1
        with self.assertRaises(ModelProviderError) as failure:
            provider.generate(call())
        self.assertEqual(failure.exception.code, ModelErrorCode.EXPIRED)
        self.assertEqual(tools.invoke("logs.query", QUERY).payload.status, "expired")
        self.assertEqual((len(transport.requests), backend.calls), (0, 0))

    def test_cancellation_after_monthly_reservation_prevents_dispatch_and_refunds_tokens(
        self,
    ) -> None:
        _, ledger, _, provider, transport, _, journal, _, _ = self.fixture()
        journal.after_begin = lambda: setattr(ledger, "terminal", "cancelled")
        with self.assertRaises(ModelProviderError) as failure:
            provider.generate(call())
        self.assertEqual(failure.exception.code, ModelErrorCode.CANCELLED)
        self.assertEqual(transport.requests, [])
        self.assertEqual(ledger.state.charged_tokens, 0)
        self.assertEqual(list(ledger.records.values())[0]["dispatched"], False)

    def test_deadline_rechecked_after_policy_and_audit_work(self) -> None:
        _, _, clock, provider, transport, _, journal, _, _ = self.fixture(
            ExecutionPolicy(deadline_ms=10)
        )
        journal.after_begin = lambda: setattr(clock, "now", clock.now + 0.011)
        with self.assertRaises(ModelProviderError) as failure:
            provider.generate(call())
        self.assertEqual(failure.exception.code, ModelErrorCode.EXPIRED)
        self.assertEqual(transport.requests, [])

    def test_late_model_reply_is_accounted_and_never_released_or_retried(self) -> None:
        _, ledger, clock, provider, transport, _, journal, tools, backend = (
            self.fixture(ExecutionPolicy(model_timeout_ms=10))
        )
        generate = transport.generate

        def late(request):
            result = generate(request)
            clock.now += 0.011
            return result

        transport.generate = late
        with self.assertRaises(ModelProviderError) as failure:
            provider.generate(call())
        self.assertEqual(failure.exception.code, ModelErrorCode.TIMEOUT)
        self.assertEqual(journal.entries[-1]["outcome"], "timeout")
        saved = list(ledger.records.values())[0]
        self.assertEqual(saved["usage"]["input_tokens"], 23)
        self.assertEqual(saved["estimated_cost_nusd"], 23 * 2 + 24 * 3)
        self.assertEqual(saved["execution_outcome"], "reconciliation_required")
        self.assertEqual(
            tools.invoke("logs.query", QUERY).payload.status, "execution_stopped"
        )
        self.assertEqual((len(transport.requests), backend.calls), (1, 0))

    def test_unknown_partial_and_zero_usage_remain_distinct(self) -> None:
        for usage, availability, charged, estimate in (
            (ModelUsage(), "unavailable", None, None),
            (ModelUsage(23), "partial", None, None),
            (ModelUsage(0, 0), "available", 0, 0),
        ):
            _, ledger, _, provider, transport, _, _, _, _ = self.fixture()
            transport.reply = replace(transport.reply, usage=usage)
            provider.generate(call())
            saved = list(ledger.records.values())[0]
            with self.subTest(usage=usage):
                self.assertEqual(saved["usage"], usage.to_dict())
                self.assertEqual(saved["usage"]["availability"], availability)
                self.assertEqual(saved["estimated_cost_nusd"], estimate)
                if charged is None:
                    self.assertGreater(saved["call_charged_tokens"], 0)
                else:
                    self.assertEqual(saved["call_charged_tokens"], charged)

    def test_sensitive_provider_metadata_is_withheld_without_losing_numeric_usage(
        self,
    ) -> None:
        for field in ("operation_id", "reported_model"):
            _, ledger, _, provider, transport, _, journal, _, _ = self.fixture()
            transport.reply = replace(transport.reply, **{field: TEST_AUTH_VALUE})
            with (
                self.subTest(field=field),
                self.assertRaises(ModelProviderError) as failure,
            ):
                provider.generate(call())
            self.assertEqual(failure.exception.code, ModelErrorCode.POLICY)
            self.assertNotIn(
                TEST_AUTH_VALUE,
                json.dumps(ledger.records) + json.dumps(journal.entries),
            )
            self.assertEqual(
                list(ledger.records.values())[0]["usage"]["input_tokens"], 23
            )

    def test_unknown_usage_holds_allowance_and_next_call_cannot_overspend_tokens(
        self,
    ) -> None:
        _, ledger, _, provider, transport, _, _, _, _ = self.fixture(
            ExecutionPolicy(max_total_tokens=2500)
        )
        transport.reply = replace(transport.reply, usage=ModelUsage())
        provider.generate(call())
        held = ledger.state.charged_tokens
        with self.assertRaises(ModelProviderError) as failure:
            provider.generate(call())
        self.assertEqual(failure.exception.code, ModelErrorCode.BUDGET)
        self.assertEqual(len(transport.requests), 1)
        self.assertEqual(ledger.state.charged_tokens, held)

    def test_input_and_native_output_limits_enforced_before_provider(self) -> None:
        _, _, _, provider, transport, _, _, _, _ = self.fixture(
            ExecutionPolicy(max_input_tokens=1)
        )
        with self.assertRaises(ModelProviderError) as failure:
            provider.generate(call())
        self.assertEqual(failure.exception.code, ModelErrorCode.BUDGET)
        self.assertEqual(transport.requests, [])
        _, _, _, provider, transport, _, _, _, _ = self.fixture(
            ExecutionPolicy(max_output_tokens=25, max_model_response_bytes=512)
        )
        provider.generate(call(bounds=ModelCallBounds(60_000, 100_000, 5000)))
        self.assertEqual(transport.requests[0].bounds.max_output_tokens, 25)
        self.assertEqual(transport.requests[0].bounds.max_response_bytes, 512)
        self.assertLessEqual(transport.requests[0].bounds.timeout_ms, 30_000)

    def test_failed_call_usage_and_explicit_bounded_retry_and_correction(self) -> None:
        execution, ledger, _, provider, transport, _, _, _, _ = self.fixture(
            ExecutionPolicy(max_model_calls=4, max_retries=1, max_corrections=1)
        )
        transport.error = ModelErrorCode.RATE_LIMIT
        with self.assertRaises(ModelProviderError):
            provider.generate(call())
        self.assertGreater(ledger.state.charged_tokens, 0)
        transport.error = None
        prior = provider.generate(call(purpose="retry"))
        provider.generate(call(purpose="correction", history=(prior,)))
        with self.assertRaises(ModelProviderError) as failure:
            provider.generate(call(purpose="correction"))
        self.assertEqual(failure.exception.code, ModelErrorCode.BUDGET)
        self.assertEqual(len(transport.requests), 3)
        self.assertEqual((ledger.state.retries, ledger.state.corrections), (1, 2))
        self.assertEqual(execution.policy.max_retries, 1)

    def test_failed_request_with_known_usage_and_unknown_outcome_reservation(
        self,
    ) -> None:
        for code, usage in (
            (ModelErrorCode.RATE_LIMIT, ModelUsage(5, 2)),
            (ModelErrorCode.DEPENDENCY, ModelUsage()),
        ):
            _, ledger, _, provider, transport, _, _, tools, backend = self.fixture()

            def failed(request):
                transport.requests.append(request)
                raise ModelProviderError(code, usage=usage)

            transport.generate = failed
            with self.assertRaises(ModelProviderError):
                provider.generate(call())
            saved = list(ledger.records.values())[0]
            self.assertEqual(saved["usage"], usage.to_dict())
            if code == ModelErrorCode.RATE_LIMIT:
                self.assertEqual(saved["estimated_cost_nusd"], 16)
                self.assertEqual(saved["call_charged_tokens"], 7)
            else:
                self.assertIsNone(saved["estimated_cost_nusd"])
                self.assertEqual(saved["execution_outcome"], "reconciliation_required")
                self.assertEqual(
                    tools.invoke("logs.query", QUERY).payload.status,
                    "execution_stopped",
                )
                self.assertEqual(backend.calls, 0)

    def test_cancel_and_timeout_during_tool_discard_content_and_stop_future_calls(
        self,
    ) -> None:
        for cancel in (True, False):
            _, ledger, clock, provider, transport, _, _, tools, backend = self.fixture(
                ExecutionPolicy(tool_timeout_ms=10)
            )
            backend.payload = ToolPayload("ok", {"text": "sensitive tool content"})
            backend.after_dispatch = lambda: (
                setattr(ledger, "terminal", "cancelled")
                if cancel
                else setattr(clock, "now", clock.now + 0.011)
            )
            result = tools.invoke("logs.query", QUERY)
            self.assertEqual(
                result.payload.status, "cancelled" if cancel else "timeout"
            )
            self.assertEqual(result.payload.data, {})
            with self.assertRaises(ModelProviderError):
                provider.generate(call())
            self.assertEqual((backend.calls, len(transport.requests)), (1, 0))
            self.assertNotIn("sensitive tool content", json.dumps(ledger.records))

    def test_audit_completeness_content_exclusion_and_numeric_usage_logs(self) -> None:
        stream = io.StringIO()
        configure_logging(stream=stream, secret_values=(TEST_AUTH_VALUE,))
        _, ledger, clock, provider, transport, authority, _, _, _ = self.fixture()
        authority.records["evidence-1"] = record(
            fields=(
                EvidenceField(
                    "observation",
                    "private-excerpt " + TEST_AUTH_VALUE,
                    Sensitivity.INTERNAL,
                    True,
                ),
            )
        )
        transport.reply = ModelReply(
            '{"status":"private-response"}',
            "resp_fixture",
            ModelUsage(23, 24),
            reported_model="gpt-6-luna",
        )
        provider.generate(call())
        saved = list(ledger.records.values())[0]
        for name in (
            "investigation_id",
            "attempt_id",
            "correlation_id",
            "call_id",
            "execution_policy_version",
            "execution_configuration_id",
            "policy_version",
            "evidence_ids",
            "configuration",
            "prompt_version",
            "reported_model",
            "provider_operation_id",
            "usage",
            "duration_ms",
            "end_to_end_duration_ms",
            "pricing_version",
            "currency",
            "cost_kind",
            "outcome",
        ):
            self.assertIn(name, saved)
        self.assertEqual(saved["evidence_ids"], ["evidence-1"])
        self.assertEqual(saved["end_to_end_duration_ms"], 2000)
        self.assertEqual(saved["configuration"]["deployment_id"], "fixture-deployment")
        text = json.dumps(ledger.records) + stream.getvalue()
        for private in (
            TEST_AUTH_VALUE,
            "private-excerpt",
            "private-response",
            "Return a synthetic",
        ):
            self.assertNotIn(private, text)
        logs = [json.loads(line) for line in stream.getvalue().splitlines()]
        final = [item for item in logs if item.get("event") == "execution.call"][-1]
        self.assertEqual(final["usage"]["input_tokens"], 23)
        self.assertEqual(final["usage"]["output_tokens"], 24)
        self.assertEqual(final["charged_tokens"], 47)
        self.assertEqual(clock.now, ledger.state.last_at)

    def test_clock_rollback_audit_failure_and_completed_stop_fail_closed(self) -> None:
        execution, ledger, clock, provider, transport, _, _, tools, backend = (
            self.fixture()
        )
        clock.now -= 1
        with self.assertRaises(ModelProviderError):
            provider.generate(call())
        self.assertEqual(transport.requests, [])
        self.assertEqual(ledger.state.stop_reason, "clock_invalid")
        execution, ledger, _, provider, transport, _, _, tools, backend = self.fixture()
        ledger.fail = True
        with self.assertRaises(ModelProviderError) as failure:
            provider.generate(call())
        self.assertEqual(failure.exception.code, ModelErrorCode.AUDIT)
        self.assertEqual(
            tools.invoke("logs.query", QUERY).payload.status, "dependency_failure"
        )
        self.assertEqual((len(transport.requests), backend.calls), (0, 0))
        execution, _, _, provider, transport, _, _, _, _ = self.fixture()
        execution.stop("completed")
        with self.assertRaises(ModelProviderError):
            provider.generate(call())
        self.assertEqual(transport.requests, [])

    def test_replay_purpose_and_active_ticket_cannot_dispatch_twice(self) -> None:
        execution, _, _ = execution_fixture(
            ExecutionPolicy(max_retries=1, max_corrections=1)
        )
        with self.assertRaises(ExecutionRejected):
            execution.begin("model", "retry")
        first = execution.begin("tool")
        execution.dispatch(first)
        with self.assertRaises(ExecutionRejected):
            execution.dispatch(first)
        with self.assertRaises(ExecutionRejected):
            execution.begin("model")
        execution.finish(first, "ok")

    def test_usage_over_allowance_is_recorded_and_response_withheld(self) -> None:
        _, ledger, _, provider, transport, _, _, _, _ = self.fixture()
        transport.reply = replace(transport.reply, usage=ModelUsage(100_000, 24))
        with self.assertRaises(ModelProviderError) as failure:
            provider.generate(call())
        self.assertEqual(failure.exception.code, ModelErrorCode.BUDGET)
        self.assertEqual(len(transport.requests), 1)
        self.assertEqual(ledger.state.charged_tokens, 100_024)
