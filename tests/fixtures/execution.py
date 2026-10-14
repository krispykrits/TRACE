"""Injected clock, transactional execution ledger and scoped read-only tools."""

from __future__ import annotations

import copy
from collections.abc import Callable
from dataclasses import dataclass, field

from tests.fixtures.provider_policy import NOW, SCOPE, Clock
from trace_app.evidence.queries import TrustedQueryContext
from trace_app.investigation.execution import (
    ExecutionIdentity,
    ExecutionPolicy,
    ExecutionSession,
    ExecutionState,
)
from trace_app.investigation.provider import ModelPricing
from trace_app.investigation.tools import ToolAudit, ToolPayload, ToolScope
from trace_app.knowledge.models import CorpusReadContext

PRICING = ModelPricing("fixture-price.v1", 2, 3)
IDENTITY = ExecutionIdentity(
    SCOPE.investigation_id, 1, "corr-budget-fixture", "fixture-scope"
)
TOOL_SCOPE = ToolScope(
    SCOPE.investigation_id,
    IDENTITY.correlation_id,
    TrustedQueryContext("local:synthetic", "test", ("order",)),
    CorpusReadContext(
        "local:knowledge-development",
        "test",
        ("payment",),
        "development_reference",
        "2026-10-12T12:00:00Z",
    ),
)
QUERY = {"window_start": "2026-01-01T00:00:00Z", "window_end": "2026-01-01T00:00:02Z"}


@dataclass
class MemoryLedger:
    state: ExecutionState = field(
        default_factory=lambda: ExecutionState(NOW, NOW - 2, NOW)
    )
    records: dict[str, dict[str, object]] = field(default_factory=dict)
    terminal: str | None = None
    fail: bool = False

    def apply(
        self,
        identity: ExecutionIdentity,
        policy: ExecutionPolicy,
        now: float,
        operation: Callable[[ExecutionState], dict[str, object] | None],
    ) -> dict[str, object] | None:
        if self.fail:
            raise RuntimeError("password=untrusted-audit-exception")
        pending = copy.deepcopy(self.state)
        if self.terminal is not None:
            pending.stop_reason = self.terminal
        record = operation(pending)
        self.state = pending
        if record is not None:
            call_id = str(record["call_id"])
            self.records[call_id] = {
                **self.records.get(call_id, {}),
                **copy.deepcopy(record),
            }
        return record


def execution_fixture(
    policy: ExecutionPolicy = ExecutionPolicy(),
) -> tuple[ExecutionSession, MemoryLedger, Clock]:
    ledger, clock = MemoryLedger(), Clock()
    return (
        ExecutionSession(IDENTITY, policy, ledger, PRICING, clock=clock),
        ledger,
        clock,
    )


@dataclass
class Audit:
    records: list[ToolAudit] = field(default_factory=list)

    def emit(self, record: ToolAudit) -> None:
        self.records.append(record)


@dataclass
class Backend:
    calls: int = 0
    timeouts: list[int] = field(default_factory=list)
    after_dispatch: Callable[[], None] = lambda: None
    payload: ToolPayload = field(
        default_factory=lambda: ToolPayload("ok", {"entries": []})
    )

    def execute(self, call, scope, policy, *, timeout_ms) -> ToolPayload:
        self.calls += 1
        self.timeouts.append(timeout_ms)
        self.after_dispatch()
        return self.payload
