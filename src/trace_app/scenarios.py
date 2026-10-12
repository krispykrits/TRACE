"""Small development replay suite; operational output contains no evaluator labels."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from trace_app.demo_fixtures import CustomerFixture, NotificationFixture, PaymentFixture
from trace_app.evidence import EvidenceRecord, SourceAvailability, format_utc
from trace_app.investigation_state import (
    DeploymentPayload,
    EvidenceEntry,
    EvidenceKind,
    EvidencePayload,
    EvidenceSnapshot,
    LogPayload,
    MetricPayload,
)
from trace_app.order_workflow import (
    BoundaryContext,
    DependencyUnavailable,
    OrderRequest,
    OrderWorkflow,
)

SUITE_VERSION = "mvp-suite.v1"
CASE_IDS = ("c01", "c02", "c03", "c04")
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_Emit = Callable[[str, str, EvidenceKind, EvidencePayload], None]


@dataclass(frozen=True, slots=True)
class ScenarioConfig:
    """Synthetic generator inputs; never serialize them into investigator evidence."""

    case_id: str
    seed: int
    environment: Literal["development", "test"] = "test"
    notification_deployment: bool = True
    version: str = SUITE_VERSION

    def __post_init__(self) -> None:
        if self.case_id not in CASE_IDS:
            raise ValueError("case_id must be c01, c02, c03 or c04.")
        if type(self.seed) is not int or not 0 <= self.seed <= 1_000_000_000:
            raise ValueError("seed must be an integer from 0 to 1000000000.")
        if self.environment not in ("development", "test"):
            raise ValueError("environment must be development or test.")
        if type(self.notification_deployment) is not bool:
            raise ValueError("notification_deployment must be a boolean.")
        if self.version != SUITE_VERSION:
            raise ValueError("version is unsupported.")


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    status: Literal["accepted", "dependency_failed"]
    snapshot: EvidenceSnapshot

    def to_dict(self) -> dict[str, object]:
        """Explicit operational allowlist; no case, seed or cause metadata."""
        bundle = self.snapshot.to_bundle().to_dict()
        bundle.pop("records")
        bundle["entries"] = [
            {
                "kind": entry.kind,
                "record": entry.record.to_dict(),
                "payload": asdict(entry.payload),
            }
            for entry in self.snapshot.entries
        ]
        return {"status": self.status, "evidence": bundle}


class _Customer:
    def __init__(self, emit: _Emit) -> None:
        self._fixture = CustomerFixture()
        self._emit = emit

    def contains(self, customer_id: str, *, context: BoundaryContext) -> bool:
        found = self._fixture.contains(customer_id, context=context)
        self._emit("customer", "customer.found", "log", LogPayload("customer.found"))
        return found


class _Payment(PaymentFixture):
    def __init__(self, emit: _Emit, *, budget_ms: int, work_ms: int) -> None:
        self._emit = emit
        self._budget_ms = budget_ms
        self._work_ms = work_ms

    def authorize(
        self, *, order_id: str, amount_cents: int, context: BoundaryContext
    ) -> str:
        for name, value in (
            ("authorization_budget_ms", self._budget_ms),
            ("dependency_work_ms", self._work_ms),
        ):
            self._emit(
                "payment", "metric.sample", "metric", MetricPayload(name, value, "ms")
            )
        if self._work_ms > self._budget_ms:
            self._emit(
                "payment", "payment.timeout", "log", LogPayload("payment.timeout")
            )
            raise DependencyUnavailable("payment")
        self._emit(
            "payment", "payment.authorized", "log", LogPayload("payment.authorized")
        )
        return super().authorize(
            order_id=order_id, amount_cents=amount_cents, context=context
        )


class ScenarioSession:
    """One replay per reset, with deterministic causal events and capture delays."""

    def __init__(self, config: ScenarioConfig) -> None:
        self.config = config
        self.reset()

    def reset(self) -> None:
        self._played = False
        self._events: list[tuple[str, str, EvidenceKind, EvidencePayload]] = []
        self.notification_count = 0

    def _emit(
        self, service: str, event: str, kind: EvidenceKind, payload: EvidencePayload
    ) -> None:
        self._events.append((service, event, kind, payload))

    def replay(self, *, collected_at: datetime | None = None) -> ScenarioResult:
        if self._played:
            raise RuntimeError(
                "Scenario session already used; call reset before replay."
            )
        capture = collected_at if collected_at is not None else datetime.now(UTC)
        format_utc(capture)
        self._played = True
        config = self.config
        short_budget = config.case_id in ("c01", "c03")
        missing = config.case_id in ("c03", "c04")
        budget = 5 if short_budget else 50
        work = 10 if short_budget else 100
        # Identity depends on causal configuration, never collection time or distractor.
        identity = hashlib.sha256(
            f"{config.version}:{config.case_id}:{config.seed}:{config.environment}".encode()
        ).hexdigest()[:20]
        start = _BASE_TIME + timedelta(seconds=config.seed % 86_400)
        context = BoundaryContext("order", config.environment, f"synthetic-{identity}")
        self._emit(
            "payment",
            "metric.sample",
            "metric",
            MetricPayload("authorization_budget_ms", 50, "ms"),
        )
        self._emit(
            "payment",
            "deployment.completed",
            "deployment",
            DeploymentPayload("v2", "completed"),
        )
        self._emit("order", "order.requested", "log", LogPayload("order.requested"))
        notifications = NotificationFixture()
        workflow = OrderWorkflow(
            customers=_Customer(self._emit),
            payments=_Payment(self._emit, budget_ms=budget, work_ms=work),
            notifications=notifications,
        )
        try:
            workflow.place(
                OrderRequest(f"order-{config.seed}", "customer-001", 1250),
                context=context,
            )
        except DependencyUnavailable as error:
            if error.dependency != "payment":
                raise
            self._emit(
                "order",
                "order.dependency_failed",
                "log",
                LogPayload("order.dependency_failed"),
            )
            status: Literal["accepted", "dependency_failed"] = "dependency_failed"
        else:
            self._emit("order", "order.accepted", "log", LogPayload("order.accepted"))
            status = "accepted"
        self.notification_count = len(notifications.records)
        entries: list[EvidenceEntry] = []
        for index, (service, event, kind, payload) in enumerate(self._events):
            if missing and service == "payment":
                continue
            entries.append(
                self._entry(
                    identity,
                    f"{index:03d}",
                    service,
                    event,
                    kind,
                    payload,
                    start + timedelta(seconds=index),
                    capture if kind == "metric" else capture - timedelta(seconds=30),
                )
            )
        # Insert a nearby successful deployment without changing the causal execution.
        if config.notification_deployment:
            entries.append(
                self._entry(
                    identity,
                    "d01",
                    "notification",
                    "deployment.completed",
                    "deployment",
                    DeploymentPayload("v2", "completed"),
                    start + timedelta(seconds=2),
                    capture - timedelta(seconds=30),
                )
            )
        sources = (
            SourceAvailability("order_logs", "available"),
            SourceAvailability("customer_logs", "available"),
            SourceAvailability("payment_logs", "unavailable", "capture_gap")
            if missing
            else SourceAvailability("payment_logs", "available"),
            SourceAvailability("payment_metrics", "unavailable", "capture_gap")
            if missing
            else SourceAvailability("payment_metrics", "available"),
            SourceAvailability("payment_deployments", "unavailable", "capture_gap")
            if missing
            else SourceAvailability("payment_deployments", "available"),
            SourceAvailability("notification_deployments", "available")
            if config.notification_deployment
            else SourceAvailability(
                "notification_deployments", "unavailable", "capture_disabled"
            ),
            SourceAvailability(
                "sanitized_export", "unavailable", "no_authorized_export_supplied"
            ),
        )
        snapshot = EvidenceSnapshot(
            entries=tuple(entries),
            window_start=format_utc(start),
            window_end=format_utc(start + timedelta(seconds=len(self._events) - 1)),
            sources=sources,
        )
        return ScenarioResult(status, snapshot)

    def _entry(
        self,
        identity: str,
        ordinal: str,
        service: str,
        event: str,
        kind: EvidenceKind,
        payload: EvidencePayload,
        observed: datetime,
        collected: datetime,
    ) -> EvidenceEntry:
        source_id = f"synthetic:{identity}:{ordinal}"
        observed_at = format_utc(observed)
        correlation = f"synthetic-{identity}"
        canonical = json.dumps(
            [
                source_id,
                service,
                event,
                kind,
                asdict(payload),
                observed_at,
                correlation,
            ],
            sort_keys=True,
            separators=(",", ":"),
        )
        record = EvidenceRecord(
            evidence_id=f"ev-{identity}-{ordinal}",
            service=service,
            environment=self.config.environment,
            observed_at=observed_at,
            collected_at=format_utc(collected),
            source_record_id=source_id,
            source_revision=SUITE_VERSION,
            access_classification="synthetic_public",
            redaction_status="not_required",
            correlation_id=correlation,
            event=event,
            integrity_sha256=hashlib.sha256(canonical.encode()).hexdigest(),
        )
        return EvidenceEntry(kind, record, payload)
