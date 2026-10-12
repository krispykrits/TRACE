# Request boundary
The development Order interface accepts an order ID, customer ID and amount in cents. It asks Customer for eligibility, invokes Payment, and dispatches the in-process Notification fixture after a successful payment.

# Observability
A correlation ID follows one request across the logical boundaries. Service identity changes at the receiving boundary. Preserve both fields rather than treating all correlated records as one service. Failed requests and accepted receipts are distinct observations.

# Limits
The current fixtures have no operational telemetry adapter. Notification activity or a deployment near an Order error is not sufficient evidence that Notification caused it. This reference describes the development interface, not a deployed production topology.
