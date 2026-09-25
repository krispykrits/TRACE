# Synthetic Order → Payment workflow

Status: Sprint 2 issue [#7](https://github.com/krispykrits/TRACE/issues/7), 2026-09-25. [ADR 0004](../adr/0004-synchronous-synthetic-order-workflow.md) records the communication choice. This is a deterministic business-context demo, not an incident investigator, real payment, notification delivery or operational source integration.

```mermaid
sequenceDiagram
    actor Engineer
    participant CLI as trace-app demo-order
    participant Order as OrderWorkflow
    participant Customer as Customer fixture
    participant Payment as Payment fixture
    participant Notification as Notification fixture
    Engineer->>CLI: order_id, customer_id, amount_cents
    CLI->>Order: OrderRequest + BoundaryContext
    Order->>Customer: contains(customer_id, context)
    Customer-->>Order: known / unknown
    alt known customer
        Order->>Payment: authorize(order_id, amount_cents, context)
        Payment-->>Order: synthetic authorization ID
        Order->>Notification: record(order_id, customer_id, context)
        Notification-->>Order: in-memory record
        Order-->>CLI: accepted outcome
    else unknown customer
        Order-->>CLI: rejected outcome; no Payment or Notification call
    end
    CLI-->>Engineer: JSON outcome on stdout; JSON logs on stderr
```

All calls are synchronous and in one process. Payment completes before the accepted result; Notification is recorded only after Payment. Customer is a read-only lookup of `customer-001`, Payment returns `auth-<order_id>` without moving money, and Notification records in memory without sending a message. These are logical service identities for later evidence correlation, not separately deployed services. No callback, queue, database or network request exists in this path.

## Runnable request

From the repository root with Python 3.12 and uv 0.12.17:

```sh
uv run --locked trace-app demo-order --environment test --order-id order-001 --customer-id customer-001 --amount-cents 1250
```

The command returns one JSON object on stdout. The expected stable fields are `status="accepted"`, `order_id="order-001"`, `service="order"`, `environment="test"`, `payment_authorization_id="auth-order-001"`, `notification_recorded=true` and `reason=null`. `correlation_id` is generated per invocation. JSON operational log lines on stderr show `order.requested`, `customer.found`, `payment.authorized`, `notification.recorded` and `order.accepted` with that same ID and the corresponding logical service names. Log timestamps are runtime timestamps; they are **not** the versioned incident evidence that issue #8 will define.

`OrderRequest` accepts ID fields of 1–64 ASCII letters, digits, underscores or hyphens, beginning with a letter or digit, and a positive integer `amount_cents`. It contains no payment credentials or personal details. `BoundaryContext(service, environment, correlation_id)` is passed to Customer, Payment and Notification with service changed to the receiving boundary and environment/correlation unchanged. These names are source-neutral; they do not select a cloud provider or authorize access to a real source. Future operational adapters must derive authorization from an authenticated principal independently of caller-supplied filters.

| Condition | CLI result | Dependency behavior |
| --- | --- | --- |
| Known customer and valid request | Exit 0, `accepted` JSON | Payment authorized synthetically; Notification recorded in memory |
| Unknown customer | Exit 0, `rejected` JSON with `reason="customer_not_found"` | No Payment or Notification call |
| Invalid ID/amount/configuration or production environment | Exit 2, actionable error on stderr, no outcome JSON | No workflow dependency call |
| Customer, Payment or Notification adapter failure | Exit 3, `order.dependency_failed` log, no accepted receipt | No automatic retry; Notification failure can follow Payment authorization and needs reconciliation |

The current CLI fixtures do not deliberately fail; unit tests inject failing adapters to prove propagation. Issue [#8](https://github.com/krispykrits/TRACE/issues/8) adds a seeded Payment dependency failure, reset/replay, source-neutral evidence envelope, UTC event times and a protected evaluator manifest. The operational input and stdout result here contain no incident cause or ground-truth label. Synthetic success does not satisfy the independent Operational Pilot gate.
