"""Unit and contract tests for the synthetic Order → Payment path."""

from __future__ import annotations

import unittest

from trace_app.demo_fixtures import CustomerFixture, NotificationFixture, PaymentFixture
from trace_app.order_workflow import (
    BoundaryContext,
    DependencyUnavailable,
    OrderInputError,
    OrderRequest,
    OrderWorkflow,
)


class RecordingCustomers:
    def __init__(self, *, exists: bool = True, unavailable: bool = False) -> None:
        self.exists = exists
        self.unavailable = unavailable
        self.contexts: list[BoundaryContext] = []

    def contains(self, customer_id: str, *, context: BoundaryContext) -> bool:
        self.contexts.append(context)
        if self.unavailable:
            raise DependencyUnavailable("customer")
        return self.exists


class RecordingPayments:
    def __init__(self, *, unavailable: bool = False) -> None:
        self.unavailable = unavailable
        self.contexts: list[BoundaryContext] = []
        self.calls: list[tuple[str, int]] = []

    def authorize(
        self, *, order_id: str, amount_cents: int, context: BoundaryContext
    ) -> str:
        self.contexts.append(context)
        self.calls.append((order_id, amount_cents))
        if self.unavailable:
            raise DependencyUnavailable("payment")
        return "auth-recorded"


class RecordingNotifications:
    def __init__(self, *, unavailable: bool = False) -> None:
        self.unavailable = unavailable
        self.contexts: list[BoundaryContext] = []
        self.calls: list[tuple[str, str]] = []

    def record(
        self, *, order_id: str, customer_id: str, context: BoundaryContext
    ) -> None:
        self.contexts.append(context)
        self.calls.append((order_id, customer_id))
        if self.unavailable:
            raise DependencyUnavailable("notification")


class OrderWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request = OrderRequest("order-001", "customer-001", 1250)
        self.context = BoundaryContext("order", "test", "corr-001")
        self.customers = RecordingCustomers()
        self.payments = RecordingPayments()
        self.notifications = RecordingNotifications()
        self.workflow = OrderWorkflow(
            customers=self.customers,
            payments=self.payments,
            notifications=self.notifications,
        )

    def test_accepts_order_and_preserves_identity_across_boundaries(self) -> None:
        outcome = self.workflow.place(self.request, context=self.context)

        self.assertEqual(outcome.status, "accepted")
        self.assertEqual(outcome.order_id, "order-001")
        self.assertEqual(outcome.context, self.context)
        self.assertEqual(outcome.payment_authorization_id, "auth-recorded")
        self.assertTrue(outcome.notification_recorded)
        self.assertIsNone(outcome.reason)
        self.assertEqual(self.payments.calls, [("order-001", 1250)])
        self.assertEqual(self.notifications.calls, [("order-001", "customer-001")])
        for expected_service, contexts in (
            ("customer", self.customers.contexts),
            ("payment", self.payments.contexts),
            ("notification", self.notifications.contexts),
        ):
            self.assertEqual(len(contexts), 1)
            self.assertEqual(contexts[0].service, expected_service)
            self.assertEqual(contexts[0].environment, "test")
            self.assertEqual(contexts[0].correlation_id, "corr-001")

    def test_maximum_length_order_id_accepts_fixture_authorization(self) -> None:
        order_id = "o" * 64
        workflow = OrderWorkflow(
            customers=CustomerFixture(),
            payments=PaymentFixture(),
            notifications=NotificationFixture(),
        )

        outcome = workflow.place(
            OrderRequest(order_id, "customer-001", 1250), context=self.context
        )

        self.assertEqual(outcome.status, "accepted")
        self.assertEqual(outcome.payment_authorization_id, f"auth-{order_id}")

    def test_unknown_customer_rejects_without_payment_or_notification(self) -> None:
        self.customers.exists = False

        outcome = self.workflow.place(self.request, context=self.context)

        self.assertEqual(outcome.status, "rejected")
        self.assertEqual(outcome.reason, "customer_not_found")
        self.assertIsNone(outcome.payment_authorization_id)
        self.assertFalse(outcome.notification_recorded)
        self.assertEqual(self.payments.calls, [])
        self.assertEqual(self.notifications.calls, [])

    def test_customer_failure_propagates_without_other_calls(self) -> None:
        self.customers.unavailable = True

        with self.assertRaises(DependencyUnavailable) as raised:
            self.workflow.place(self.request, context=self.context)

        self.assertEqual(raised.exception.dependency, "customer")
        self.assertEqual(self.payments.calls, [])
        self.assertEqual(self.notifications.calls, [])

    def test_payment_failure_propagates_without_notification(self) -> None:
        self.payments.unavailable = True

        with self.assertRaises(DependencyUnavailable) as raised:
            self.workflow.place(self.request, context=self.context)

        self.assertEqual(raised.exception.dependency, "payment")
        self.assertEqual(self.notifications.calls, [])

    def test_invalid_payment_response_does_not_notify_or_accept(self) -> None:
        class InvalidPayment:
            def authorize(
                self, *, order_id: str, amount_cents: int, context: BoundaryContext
            ) -> str:
                return ""

        workflow = OrderWorkflow(
            customers=self.customers,
            payments=InvalidPayment(),
            notifications=self.notifications,
        )

        with self.assertRaises(DependencyUnavailable) as raised:
            workflow.place(self.request, context=self.context)

        self.assertEqual(raised.exception.dependency, "payment")
        self.assertEqual(self.notifications.calls, [])

    def test_notification_failure_does_not_return_success_receipt(self) -> None:
        self.notifications.unavailable = True

        with self.assertRaises(DependencyUnavailable) as raised:
            self.workflow.place(self.request, context=self.context)

        self.assertEqual(raised.exception.dependency, "notification")
        self.assertEqual(self.payments.calls, [("order-001", 1250)])

    def test_request_rejects_malformed_fields(self) -> None:
        invalid = (
            ("", "customer-001", 1250),
            ("order\nspoofed", "customer-001", 1250),
            ("a" * 65, "customer-001", 1250),
            ("order-001", "invalid customer", 1250),
            ("order-001", "customer-001", 0),
            ("order-001", "customer-001", -1),
        )
        for order_id, customer_id, amount_cents in invalid:
            with self.subTest(
                order_id=order_id, customer_id=customer_id, amount=amount_cents
            ):
                with self.assertRaises(OrderInputError):
                    OrderRequest(order_id, customer_id, amount_cents)

    def test_wrong_service_context_is_rejected_before_dependencies(self) -> None:
        with self.assertRaises(ValueError):
            self.workflow.place(
                self.request,
                context=BoundaryContext("payment", "test", "corr-001"),
            )
        self.assertEqual(self.customers.contexts, [])

    def test_process_local_fixtures_have_no_external_effect(self) -> None:
        notification = NotificationFixture()
        workflow = OrderWorkflow(
            customers=CustomerFixture(),
            payments=PaymentFixture(),
            notifications=notification,
        )

        outcome = workflow.place(self.request, context=self.context)

        self.assertEqual(outcome.payment_authorization_id, "auth-order-001")
        self.assertEqual(len(notification.records), 1)
        self.assertEqual(notification.records[0].context.service, "notification")
        self.assertEqual(notification.records[0].context.correlation_id, "corr-001")


if __name__ == "__main__":
    unittest.main()
