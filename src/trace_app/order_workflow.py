"""Synthetic Order → Payment workflow and TRACE-owned boundary contracts."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Literal, Protocol

_ORDER_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_AUTHORIZATION_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
ORDER_SERVICE = "order"
CUSTOMER_SERVICE = "customer"
PAYMENT_SERVICE = "payment"
NOTIFICATION_SERVICE = "notification"


class OrderInputError(ValueError):
    """A request field is invalid; messages name fields without echoing values."""


class DependencyUnavailable(RuntimeError):
    """A workflow dependency failed without an accepted order outcome."""

    def __init__(self, dependency: Literal["customer", "payment", "notification"]):
        self.dependency = dependency
        super().__init__(f"{dependency} dependency is unavailable")


@dataclass(frozen=True, slots=True)
class BoundaryContext:
    """Source-neutral service, environment and trace identity for one boundary."""

    service: str
    environment: str
    correlation_id: str

    def __post_init__(self) -> None:
        if not self.service or not self.environment or not self.correlation_id:
            raise ValueError(
                "Boundary context requires service, environment and correlation ID."
            )

    def for_service(self, service: str) -> BoundaryContext:
        return BoundaryContext(
            service=service,
            environment=self.environment,
            correlation_id=self.correlation_id,
        )


@dataclass(frozen=True, slots=True)
class OrderRequest:
    """A validated synthetic order request; no payment credentials or PII."""

    order_id: str
    customer_id: str
    amount_cents: int

    def __post_init__(self) -> None:
        if not isinstance(self.order_id, str) or not _ORDER_ID.fullmatch(self.order_id):
            raise OrderInputError(
                "Invalid order_id; use 1–64 ASCII letters, digits, underscores or hyphens, starting with a letter or digit."
            )
        if not isinstance(self.customer_id, str) or not _ORDER_ID.fullmatch(
            self.customer_id
        ):
            raise OrderInputError(
                "Invalid customer_id; use 1–64 ASCII letters, digits, underscores or hyphens, starting with a letter or digit."
            )
        if type(self.amount_cents) is not int or self.amount_cents <= 0:
            raise OrderInputError("Invalid amount_cents; supply a positive integer.")


@dataclass(frozen=True, slots=True)
class OrderOutcome:
    """Business result, separate from process/dependency failure."""

    status: Literal["accepted", "rejected"]
    order_id: str
    context: BoundaryContext
    payment_authorization_id: str | None = None
    notification_recorded: bool = False
    reason: str | None = None


class CustomerDirectory(Protocol):
    """Read-only customer lookup boundary."""

    def contains(self, customer_id: str, *, context: BoundaryContext) -> bool: ...


class PaymentAuthorizer(Protocol):
    """Synthetic payment authorization boundary for this increment."""

    def authorize(
        self, *, order_id: str, amount_cents: int, context: BoundaryContext
    ) -> str: ...


class NotificationRecorder(Protocol):
    """Record a synthetic notification without external delivery."""

    def record(
        self, *, order_id: str, customer_id: str, context: BoundaryContext
    ) -> None: ...


def _log(context: BoundaryContext, event: str, message: str) -> None:
    logging.getLogger(f"trace_app.{context.service}").info(
        message,
        extra={
            "event": event,
            "service": context.service,
            "environment": context.environment,
            "correlation_id": context.correlation_id,
        },
    )


class OrderWorkflow:
    """Place one synthetic order using explicit, replaceable dependencies."""

    def __init__(
        self,
        *,
        customers: CustomerDirectory,
        payments: PaymentAuthorizer,
        notifications: NotificationRecorder,
    ) -> None:
        self._customers = customers
        self._payments = payments
        self._notifications = notifications

    def place(self, request: OrderRequest, *, context: BoundaryContext) -> OrderOutcome:
        if context.service != ORDER_SERVICE:
            raise ValueError("Order workflow requires the order service context.")
        _log(context, "order.requested", "Synthetic order received.")

        customer_context = context.for_service(CUSTOMER_SERVICE)
        if not self._customers.contains(request.customer_id, context=customer_context):
            _log(
                customer_context, "customer.not_found", "Customer fixture has no match."
            )
            _log(context, "order.rejected", "Synthetic order rejected.")
            return OrderOutcome(
                status="rejected",
                order_id=request.order_id,
                context=context,
                reason="customer_not_found",
            )
        _log(customer_context, "customer.found", "Customer fixture matched.")

        payment_context = context.for_service(PAYMENT_SERVICE)
        authorization_id = self._payments.authorize(
            order_id=request.order_id,
            amount_cents=request.amount_cents,
            context=payment_context,
        )
        if not isinstance(authorization_id, str) or not _AUTHORIZATION_ID.fullmatch(
            authorization_id
        ):
            raise DependencyUnavailable("payment")
        _log(payment_context, "payment.authorized", "Synthetic payment authorized.")

        notification_context = context.for_service(NOTIFICATION_SERVICE)
        self._notifications.record(
            order_id=request.order_id,
            customer_id=request.customer_id,
            context=notification_context,
        )
        _log(
            notification_context,
            "notification.recorded",
            "Notification fixture recorded.",
        )
        _log(context, "order.accepted", "Synthetic order accepted.")
        return OrderOutcome(
            status="accepted",
            order_id=request.order_id,
            context=context,
            payment_authorization_id=authorization_id,
            notification_recorded=True,
        )
