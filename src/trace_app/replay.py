"""Reproducible synthetic dependency replay and investigator-safe evidence."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from trace_app.demo_fixtures import CustomerFixture, NotificationFixture, PaymentFixture
from trace_app.evidence import (
    EvidenceBundle,
    EvidenceRecord,
    SourceAvailability,
    format_utc,
)
from trace_app.order_workflow import (
    ORDER_SERVICE,
    BoundaryContext,
    DependencyUnavailable,
    OrderRequest,
    OrderWorkflow,
)

SCENARIO_VERSION = "payment-dependency.v1"
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
Mode = Literal["normal", "failure"]


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class ReplayConfig:
    """Versioned replay input; mode is never included in operational output."""

    seed: int
    mode: Mode
    environment: Literal["development", "test"] = "test"
    version: str = SCENARIO_VERSION

    def __post_init__(self) -> None:
        if self.version != SCENARIO_VERSION:
            raise ValueError("Unsupported replay scenario version.")
        if type(self.seed) is not int or not 0 <= self.seed <= 1_000_000_000:
            raise ValueError("Replay seed must be an integer from 0 to 1000000000.")
        if self.mode not in ("normal", "failure"):
            raise ValueError("Replay mode must be normal or failure.")
        if self.environment not in ("development", "test"):
            raise ValueError("Synthetic replay is restricted to development and test.")


@dataclass(frozen=True, slots=True)
class ReplayResult:
    status: Literal["accepted", "dependency_failed"]
    evidence: EvidenceBundle


class _RecordingCustomer:
    def __init__(self, emit: Callable[[BoundaryContext, str], None]) -> None:
        self._emit = emit
        self._fixture = CustomerFixture()

    def contains(self, customer_id: str, *, context: BoundaryContext) -> bool:
        found = self._fixture.contains(customer_id, context=context)
        self._emit(context, "customer.found" if found else "customer.not_found")
        return found


class _RecordingPayment:
    def __init__(
        self, emit: Callable[[BoundaryContext, str], None], *, mode: Mode
    ) -> None:
        self._emit = emit
        self._mode = mode
        self._fixture = PaymentFixture()

    def authorize(
        self, *, order_id: str, amount_cents: int, context: BoundaryContext
    ) -> str:
        if self._mode == "failure":
            self._emit(context, "payment.timeout")
            raise DependencyUnavailable("payment")
        authorization = self._fixture.authorize(
            order_id=order_id, amount_cents=amount_cents, context=context
        )
        self._emit(context, "payment.authorized")
        return authorization


class _RecordingNotification(NotificationFixture):
    def __init__(self, emit: Callable[[BoundaryContext, str], None]) -> None:
        super().__init__()
        self._emit = emit

    def record(
        self, *, order_id: str, customer_id: str, context: BoundaryContext
    ) -> None:
        super().record(order_id=order_id, customer_id=customer_id, context=context)
        self._emit(context, "notification.recorded")


class ReplaySession:
    """One run per reset, so repeated plays cannot silently append evidence."""

    def __init__(self, config: ReplayConfig) -> None:
        self.config = config
        self.reset()

    def reset(self) -> None:
        self._events: list[tuple[BoundaryContext, str]] = []
        self._played = False
        self.notification_count = 0

    def _emit(self, context: BoundaryContext, event: str) -> None:
        self._events.append((context, event))

    def replay(self, *, collected_at: datetime | None = None) -> ReplayResult:
        if self._played:
            raise RuntimeError("Replay session already used; call reset before replay.")
        collection_time = format_utc(collected_at or datetime.now(UTC))
        self._played = True
        identity = _digest(
            f"{self.config.version}:{self.config.seed}:{self.config.mode}:"
            f"{self.config.environment}"
        )[:20]
        context = BoundaryContext(
            service=ORDER_SERVICE,
            environment=self.config.environment,
            correlation_id=f"synthetic-{identity}",
        )
        request = OrderRequest(
            order_id=f"order-{self.config.seed}",
            customer_id="customer-001",
            amount_cents=1250,
        )
        notifications = _RecordingNotification(self._emit)
        workflow = OrderWorkflow(
            customers=_RecordingCustomer(self._emit),
            payments=_RecordingPayment(self._emit, mode=self.config.mode),
            notifications=notifications,
        )
        self._emit(context, "order.requested")
        try:
            workflow.place(request, context=context)
        except DependencyUnavailable as error:
            if error.dependency != "payment":
                raise
            self._emit(context, "order.dependency_failed")
            status: Literal["accepted", "dependency_failed"] = "dependency_failed"
        else:
            self._emit(context, "order.accepted")
            status = "accepted"
        self.notification_count = len(notifications.records)
        start = _BASE_TIME + timedelta(seconds=self.config.seed % 86_400)
        records: list[EvidenceRecord] = []
        for index, (event_context, event) in enumerate(self._events):
            observed_at = format_utc(start + timedelta(seconds=index))
            source_record_id = f"synthetic:{identity}:{index:03d}"
            integrity = _digest(
                f"{source_record_id}:{event_context.service}:{event}:"
                f"{observed_at}:{context.correlation_id}"
            )
            records.append(
                EvidenceRecord(
                    evidence_id=f"ev-{identity}-{index:03d}",
                    service=event_context.service,
                    environment=event_context.environment,
                    observed_at=observed_at,
                    collected_at=collection_time,
                    source_record_id=source_record_id,
                    source_revision=self.config.version,
                    access_classification="synthetic_public",
                    redaction_status="not_required",
                    correlation_id=context.correlation_id,
                    event=event,
                    integrity_sha256=integrity,
                )
            )
        bundle = EvidenceBundle(
            records=tuple(records),
            window_start=records[0].observed_at,
            window_end=records[-1].observed_at,
            sources=(
                SourceAvailability("synthetic_replay", "available"),
                SourceAvailability(
                    "sanitized_export", "unavailable", "no_authorized_export_supplied"
                ),
            ),
        )
        return ReplayResult(status=status, evidence=bundle)
