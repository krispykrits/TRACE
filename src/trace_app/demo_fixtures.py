"""Deterministic, process-local adapters for the Order → Payment demo."""

from __future__ import annotations

from dataclasses import dataclass

from trace_app.order_workflow import BoundaryContext


@dataclass(frozen=True, slots=True)
class CustomerFixture:
    """Recognize a fixed synthetic customer without storing personal data."""

    known_ids: frozenset[str] = frozenset({"customer-001"})

    def contains(self, customer_id: str, *, context: BoundaryContext) -> bool:
        return customer_id in self.known_ids


class PaymentFixture:
    """Return a stable synthetic authorization ID; no money moves."""

    def authorize(
        self, *, order_id: str, amount_cents: int, context: BoundaryContext
    ) -> str:
        return f"auth-{order_id}"


@dataclass(frozen=True, slots=True)
class NotificationRecord:
    order_id: str
    customer_id: str
    context: BoundaryContext


class NotificationFixture:
    """Retain notifications in memory; never send a message."""

    def __init__(self) -> None:
        self.records: list[NotificationRecord] = []

    def record(
        self, *, order_id: str, customer_id: str, context: BoundaryContext
    ) -> None:
        self.records.append(NotificationRecord(order_id, customer_id, context))
