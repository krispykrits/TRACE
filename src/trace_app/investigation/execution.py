"""Shared, durable investigation admission; no evidence or transport authority."""

from __future__ import annotations

import logging
import math
import time
import uuid
from collections.abc import Callable
from dataclasses import asdict, dataclass, replace
from typing import Literal, Protocol

from trace_app.investigation.models import _identifier
from trace_app.investigation.provider import (
    ModelCallBounds,
    ModelErrorCode,
    ModelPricing,
    ModelUsage,
)

EXECUTION_POLICY_VERSION = "trace-execution-policy.v1"
CallKind = Literal["model", "tool"]
CallPurpose = Literal["initial", "retry", "correction"]
_SUCCESS = frozenset({"structured_response_received", "ok", "empty", "partial"})
_UNCERTAIN = frozenset({"timeout", "dependency_failure", "audit_unavailable"})
_OUTCOMES = (
    _SUCCESS
    | {value.value for value in ModelErrorCode}
    | {
        "validation_error",
        "authorization_error",
        "execution_stopped",
        "clock_invalid",
        "attempt_not_active",
        "completed",
        "failed",
        "reconciliation_required",
    }
)
_METADATA = frozenset(
    {
        "policy_version",
        "configuration",
        "evidence_ids",
        "sensitivity",
        "prompt_version",
        "reported_model",
        "provider_operation_id",
        "tool_version",
        "tool",
        "http_status",
        "provider_error_code",
        "provider_error_parameter",
    }
)


class ExecutionRejected(RuntimeError):
    """A fixed outcome, never dependency exception text or source content."""

    def __init__(self, outcome: str) -> None:
        self.outcome = outcome
        super().__init__(f"Investigation execution stopped: {outcome}.")


@dataclass(frozen=True, slots=True)
class ExecutionIdentity:
    investigation_id: str
    attempt_id: int
    correlation_id: str
    access_scope: str

    def __post_init__(self) -> None:
        for name in ("investigation_id", "correlation_id", "access_scope"):
            _identifier(name, getattr(self, name))
        if type(self.attempt_id) is not int or self.attempt_id <= 0:
            raise ValueError("attempt_id requires an active durable attempt.")


@dataclass(frozen=True, slots=True)
class ExecutionPolicy:
    """Finite implementation controls, not owner quality targets or monetary caps."""

    configuration_id: str = "local-execution.v1"
    deadline_ms: int = 120_000
    max_model_calls: int = 3
    max_tool_calls: int = 20
    max_retries: int = 0
    max_corrections: int = 0
    model_timeout_ms: int = 30_000
    tool_timeout_ms: int = 5_000
    max_input_tokens: int = 10_000
    max_output_tokens: int = 1_024
    max_total_tokens: int = 40_000
    max_model_response_bytes: int = 65_536
    max_tool_result_bytes: int = 65_536

    def __post_init__(self) -> None:
        _identifier("configuration_id", self.configuration_id)
        ceilings = {
            "deadline_ms": 600_000,
            "max_model_calls": 100,
            "max_tool_calls": 100,
            "max_retries": 10,
            "max_corrections": 10,
            "model_timeout_ms": 600_000,
            "tool_timeout_ms": 10_000,
            "max_input_tokens": 263_168,
            "max_output_tokens": 100_000,
            "max_total_tokens": 10_000_000,
            "max_model_response_bytes": 1_000_000,
            "max_tool_result_bytes": 1_000_000,
        }
        for name, ceiling in ceilings.items():
            value = getattr(self, name)
            minimum = 0 if name in ("max_retries", "max_corrections") else 1
            if type(value) is not int or not minimum <= value <= ceiling:
                raise ValueError(f"{name} is outside its finite supported bound.")
        if self.max_tool_result_bytes < 512:
            raise ValueError("max_tool_result_bytes must be at least 512.")


@dataclass(frozen=True, slots=True)
class CallTicket:
    call_id: str
    kind: CallKind
    purpose: CallPurpose
    started_at: float
    timeout_ms: int
    input_allowance: int = 0
    output_allowance: int = 0
    dispatched: bool = False

    def __post_init__(self) -> None:
        _identifier("call_id", self.call_id)
        if (
            self.kind not in ("model", "tool")
            or self.purpose not in ("initial", "retry", "correction")
            or type(self.started_at) not in (int, float)
            or not math.isfinite(self.started_at)
            or type(self.timeout_ms) is not int
            or not 1 <= self.timeout_ms <= 600_000
            or type(self.dispatched) is not bool
            or any(
                type(value) is not int or value < 0
                for value in (self.input_allowance, self.output_allowance)
            )
        ):
            raise ValueError("Invalid execution ticket.")


@dataclass(slots=True)
class ExecutionState:
    started_at: float
    created_at: float
    last_at: float
    model_calls: int = 0
    tool_calls: int = 0
    retries: int = 0
    corrections: int = 0
    charged_tokens: int = 0
    stop_reason: str | None = None
    active: CallTicket | None = None
    last_kind: CallKind | None = None
    last_outcome: str | None = None
    pricing: dict[str, object] | None = None
    authority_deadline: float | None = None

    def __post_init__(self) -> None:
        if (
            any(
                type(value) not in (int, float) or not math.isfinite(value)
                for value in (self.started_at, self.created_at, self.last_at)
            )
            or self.last_at < max(self.started_at, self.created_at)
            or any(
                type(value) is not int or value < 0
                for value in (
                    self.model_calls,
                    self.tool_calls,
                    self.retries,
                    self.corrections,
                    self.charged_tokens,
                )
            )
            or self.stop_reason
            not in (
                None,
                "completed",
                "failed",
                "cancelled",
                "expired",
                "budget_exhausted",
                "clock_invalid",
                "attempt_not_active",
                "reconciliation_required",
            )
            or self.last_kind not in (None, "model", "tool")
            or self.last_outcome is not None
            and self.last_outcome not in _OUTCOMES
            or self.active is not None
            and not isinstance(self.active, CallTicket)
        ):
            raise ValueError("Invalid execution state.")


class ExecutionLedger(Protocol):
    """Atomically revalidate job authority and persist admission/state/audit together."""

    def apply(
        self,
        identity: ExecutionIdentity,
        policy: ExecutionPolicy,
        now: float,
        operation: Callable[[ExecutionState], dict[str, object] | None],
    ) -> dict[str, object] | None: ...


class ExecutionSession:
    def __init__(
        self,
        identity: ExecutionIdentity,
        policy: ExecutionPolicy,
        ledger: ExecutionLedger,
        pricing: ModelPricing,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self.identity, self.policy, self.pricing = identity, policy, pricing
        self._ledger, self._clock = ledger, clock
        self._apply(lambda state, now: None)

    def _apply(
        self,
        operation: Callable[[ExecutionState, float], dict[str, object] | None],
    ) -> dict[str, object] | None:
        now = self._clock()
        if type(now) not in (int, float) or not math.isfinite(now):
            raise ExecutionRejected("clock_invalid")

        def update(state: ExecutionState) -> dict[str, object] | None:
            if state.pricing is None:
                state.pricing = asdict(self.pricing)
            elif state.pricing != asdict(self.pricing):
                raise ExecutionRejected("configuration_changed")
            if now < state.last_at:
                state.stop_reason = state.stop_reason or "clock_invalid"
            state.last_at = max(now, state.last_at)
            if (now - state.started_at) * 1000 >= self.policy.deadline_ms:
                state.stop_reason = state.stop_reason or "expired"
            return operation(state, now)

        try:
            record = self._ledger.apply(self.identity, self.policy, now, update)
        except ExecutionRejected:
            raise
        except Exception:
            raise ExecutionRejected("audit_unavailable") from None
        if record is not None:
            logging.getLogger("trace_app.execution").info(
                "Investigation call recorded.",
                extra={"event": "execution.call", **record},
            )
        return record

    def _record(
        self,
        state: ExecutionState,
        ticket: CallTicket,
        now: float,
        outcome: str,
    ) -> dict[str, object]:
        return {
            "execution_policy_version": EXECUTION_POLICY_VERSION,
            "execution_configuration_id": self.policy.configuration_id,
            "investigation_id": self.identity.investigation_id,
            "attempt_id": self.identity.attempt_id,
            "correlation_id": self.identity.correlation_id,
            "call_id": ticket.call_id,
            "kind": ticket.kind,
            "purpose": ticket.purpose,
            "outcome": outcome,
            "dispatched": ticket.dispatched,
            "duration_ms": max(0, int((now - ticket.started_at) * 1000)),
            "end_to_end_duration_ms": max(0, int((now - state.created_at) * 1000)),
            "execution_duration_ms": max(0, int((now - state.started_at) * 1000)),
            "input_allowance": ticket.input_allowance,
            "output_allowance": ticket.output_allowance,
            "model_calls": state.model_calls,
            "tool_calls": state.tool_calls,
            "retries": state.retries,
            "corrections": state.corrections,
            "charged_tokens": state.charged_tokens,
            "execution_outcome": state.stop_reason or "running",
            "usage": ModelUsage().to_dict(),
            "reported_model": None,
            "provider_operation_id": None,
            "estimated_cost_nusd": None,
            "pricing_version": self.pricing.version,
            "currency": "USD",
            "cost_kind": "estimate",
            "usage_basis": "provider_reported",
        }

    def begin(
        self,
        kind: CallKind,
        purpose: CallPurpose = "initial",
        *,
        metadata: dict[str, object] | None = None,
    ) -> CallTicket:
        ticket: CallTicket | None = None
        reason: str | None = None

        def admit(state: ExecutionState, now: float) -> dict[str, object]:
            nonlocal ticket, reason
            timeout = (
                self.policy.model_timeout_ms
                if kind == "model"
                else self.policy.tool_timeout_ms
            )
            remaining = int(self.policy.deadline_ms - (now - state.started_at) * 1000)
            if state.authority_deadline is not None:
                remaining = min(remaining, int((state.authority_deadline - now) * 1000))
            ticket = CallTicket(
                uuid.uuid4().hex,
                kind if kind in ("model", "tool") else "tool",
                purpose if purpose in ("initial", "retry", "correction") else "initial",
                now,
                max(1, min(timeout, remaining)),
            )
            reason = state.stop_reason
            if kind not in ("model", "tool") or purpose not in (
                "initial",
                "retry",
                "correction",
            ):
                reason = reason or "invalid_call"
            elif state.active is not None:
                reason = reason or "call_active"
            else:
                if kind == "model":
                    state.model_calls += 1
                    exhausted = state.model_calls > self.policy.max_model_calls
                else:
                    state.tool_calls += 1
                    exhausted = state.tool_calls > self.policy.max_tool_calls
                if purpose == "retry":
                    state.retries += 1
                    exhausted |= state.retries > self.policy.max_retries
                    if state.last_kind != kind or state.last_outcome not in (
                        "rate_limit",
                        "dependency_failure",
                    ):
                        reason = reason or "retry_not_permitted"
                elif purpose == "correction":
                    state.corrections += 1
                    exhausted |= state.corrections > self.policy.max_corrections
                    if (
                        kind != "model"
                        or state.last_kind != "model"
                        or state.last_outcome
                        not in (_SUCCESS | {"malformed_response", "output_limit"})
                    ):
                        reason = reason or "correction_not_permitted"
                elif state.last_kind == kind and state.last_outcome not in _SUCCESS:
                    reason = reason or "retry_or_correction_required"
                if exhausted:
                    state.stop_reason = state.stop_reason or "budget_exhausted"
                    reason = state.stop_reason
            if reason is None:
                state.active = ticket
            return {
                **self._record(state, ticket, now, reason or "admitted"),
                **self._metadata(metadata or {}),
            }

        self._apply(admit)
        if reason is not None:
            raise ExecutionRejected(reason)
        assert ticket is not None
        return ticket

    @staticmethod
    def _active(state: ExecutionState, ticket: CallTicket) -> CallTicket:
        if state.active is None or state.active.call_id != ticket.call_id:
            raise ExecutionRejected("attempt_not_active")
        return state.active

    def reserve(
        self,
        ticket: CallTicket,
        input_allowance: int,
        output_allowance: int,
        metadata: dict[str, object],
    ) -> None:
        reason: str | None = None

        def reserve(state: ExecutionState, now: float) -> dict[str, object]:
            nonlocal reason
            active = self._active(state, ticket)
            reason = state.stop_reason
            if (
                active.input_allowance
                or active.output_allowance
                or active.kind != "model"
            ):
                reason = reason or "invalid_reservation"
            elif (
                type(input_allowance) is not int
                or type(output_allowance) is not int
                or not 1 <= input_allowance <= self.policy.max_input_tokens
                or not 1 <= output_allowance <= self.policy.max_output_tokens
                or state.charged_tokens + input_allowance + output_allowance
                > self.policy.max_total_tokens
            ):
                reason = reason or "budget_exhausted"
                state.stop_reason = reason
            if reason is None:
                state.active = active = replace(
                    active,
                    input_allowance=input_allowance,
                    output_allowance=output_allowance,
                )
                state.charged_tokens += input_allowance + output_allowance
            return {
                **self._record(state, active, now, reason or "reserved"),
                **self._metadata(metadata),
            }

        self._apply(reserve)
        if reason is not None:
            raise ExecutionRejected(reason)

    def dispatch(self, ticket: CallTicket) -> int:
        reason: str | None = None
        timeout = 0

        def dispatch(state: ExecutionState, now: float) -> dict[str, object]:
            nonlocal reason, timeout
            active = self._active(state, ticket)
            reason = state.stop_reason
            if active.dispatched:
                reason = reason or "call_already_dispatched"
            remaining = int(
                min(
                    self.policy.deadline_ms - (now - state.started_at) * 1000,
                    active.timeout_ms - (now - active.started_at) * 1000,
                )
            )
            if state.authority_deadline is not None:
                remaining = min(remaining, int((state.authority_deadline - now) * 1000))
            if remaining < 1:
                state.stop_reason = reason = reason or "expired"
            if active.kind == "model" and active.input_allowance == 0:
                reason = reason or "invalid_reservation"
            if reason is None:
                timeout = remaining
                state.active = active = replace(active, dispatched=True)
            return self._record(state, active, now, reason or "dispatched")

        self._apply(dispatch)
        if reason is not None:
            raise ExecutionRejected(reason)
        return timeout

    def model_bounds(
        self, bounds: ModelCallBounds, ticket: CallTicket
    ) -> ModelCallBounds:
        return ModelCallBounds(
            min(bounds.timeout_ms, ticket.timeout_ms),
            min(bounds.max_response_bytes, self.policy.max_model_response_bytes),
            min(bounds.max_output_tokens, self.policy.max_output_tokens),
        )

    @staticmethod
    def _metadata(metadata: dict[str, object]) -> dict[str, object]:
        # Called only with the policy boundary's approved metadata, never a reply/payload.
        return {name: value for name, value in metadata.items() if name in _METADATA}

    def finish(
        self,
        ticket: CallTicket,
        outcome: str,
        usage: ModelUsage = ModelUsage(),
        *,
        metadata: dict[str, object] | None = None,
    ) -> str:
        if outcome not in _OUTCOMES:
            raise ExecutionRejected("invalid_outcome")
        final = outcome

        def finish(state: ExecutionState, now: float) -> dict[str, object]:
            nonlocal final
            active = self._active(state, ticket)
            late = (now - active.started_at) * 1000 >= active.timeout_ms
            if late and active.dispatched:
                final = "timeout"
            final = state.stop_reason or final
            charged = active.input_allowance + active.output_allowance
            if active.kind == "model":
                if not active.dispatched:
                    charged = 0
                else:
                    charged = max(
                        usage.input_tokens or 0,
                        active.input_allowance if usage.input_tokens is None else 0,
                    ) + max(
                        usage.output_tokens or 0,
                        active.output_allowance if usage.output_tokens is None else 0,
                    )
                state.charged_tokens += (
                    charged - active.input_allowance - active.output_allowance
                )
                if (
                    usage.input_tokens is not None
                    and usage.input_tokens > active.input_allowance
                    or usage.output_tokens is not None
                    and usage.output_tokens > active.output_allowance
                    or state.charged_tokens > self.policy.max_total_tokens
                ):
                    state.stop_reason = final = "budget_exhausted"
            if active.dispatched and final in _UNCERTAIN:
                state.stop_reason = "reconciliation_required"
            elif final == "timeout":
                state.stop_reason = "failed"
            if final in ("budget_exhausted", "cancelled", "expired"):
                state.stop_reason = state.stop_reason or final
            if final in (
                "policy_rejected",
                "authentication_error",
                "configuration_error",
                "audit_unavailable",
            ):
                state.stop_reason = state.stop_reason or "failed"
            state.last_kind, state.last_outcome, state.active = active.kind, final, None
            estimate = (
                self.pricing.estimate(usage.input_tokens, usage.output_tokens)
                if active.dispatched
                and usage.input_tokens is not None
                and usage.output_tokens is not None
                else None
            )
            return {
                **self._record(state, active, now, final),
                **self._metadata(metadata or {}),
                "usage": usage.to_dict(),
                "usage_basis": "provider_reported",
                "estimated_cost_nusd": estimate,
                "pricing_version": self.pricing.version,
                "currency": "USD",
                "cost_kind": "estimate",
                "reserved_or_estimated_charge_nusd": self.pricing.estimate(
                    usage.input_tokens
                    if usage.input_tokens is not None
                    else active.input_allowance,
                    usage.output_tokens
                    if usage.output_tokens is not None
                    else active.output_allowance,
                )
                if active.dispatched and estimate is None
                else estimate
                if estimate is not None
                else 0,
                "call_charged_tokens": charged,
            }

        self._apply(finish)
        return final

    def stop(self, outcome: Literal["completed", "failed", "cancelled"]) -> None:
        def stop(state: ExecutionState, now: float) -> None:
            if outcome not in ("completed", "failed", "cancelled"):
                raise ExecutionRejected("invalid_outcome")
            if state.active is not None:
                raise ExecutionRejected("call_active")
            state.stop_reason = state.stop_reason or outcome

        self._apply(stop)
