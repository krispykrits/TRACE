# ADR 0004: Synchronous in-process Order–Payment synthetic workflow

- **Status:** Accepted for the scoped Sprint 2 synthetic workflow; revisit before real integrations
- **Date:** 2026-09-25
- **Decision owner:** TRACE project team, through [issue #7](https://github.com/krispykrits/TRACE/issues/7) review

## Context

The first Order → Payment path needs understandable operational context for later incident fixtures. The [charter](../charter.md) calls for one modular Python application and a CLI first; Customer and Notification remain lightweight fixtures. The [approved amendment](../planning/production-roadmap-amendment.md) requires source-neutral service/environment and correlation identities at workflow boundaries. No pilot source, payment provider, queue, persistent order store or independent service deployment is approved for this increment.

## Decision

Expose `trace-app demo-order` in `development` or `test` only. It validates an order ID, customer ID and positive integer amount in cents. One `OrderWorkflow` synchronously checks the Customer fixture, requests a synthetic Payment authorization, records a Notification fixture event, then returns an accepted outcome. An unknown customer produces an explicit rejected business outcome without calling Payment or Notification. Fixture dependency errors propagate; no accepted receipt is returned. Notification failure after Payment is a partial outcome requiring reconciliation, so the workflow never retries automatically. A `BoundaryContext` carries `service`, `environment` and one `correlation_id` into every adapter call and operational log.

Customer, Payment and Notification are typed in-process adapter contracts with deterministic fixtures. The Payment fixture produces an authorization ID without moving money; the Notification fixture stores an in-memory record without sending a message. The workflow does not persist orders or collect incident evidence. The [workflow and contract guide](../architecture/order-payment-workflow.md) defines the CLI result and failure codes. Issue #8 owns seeded Payment failures, replay/reset, evidence identities/timestamps and evaluator-only ground truth.

## Alternatives

| Option | Decision and tradeoff |
| --- | --- |
| One synchronous in-process path with fixtures | Selected: request outcome and trace are explicit without network, queue or deployment obligations. |
| Separate Order, Payment, Customer and Notification services | Deferred: adds transport, identity, deployment and recovery work before a measured need. |
| Asynchronous Payment or notification queue | Deferred: Payment authorization must precede an accepted result; durable dispatch and retries need persistence/recovery design before hosting. |
| Real payment or notification providers | Rejected for this synthetic increment: no provider, budget, access or operational authorization has been selected. |

## Consequences

The CLI can demonstrate Order → Payment behavior and failure propagation with no credentials or AWS resources. Service identities are logical boundaries, not independently deployed processes. The fixtures do not model real payment semantics, persistence, concurrency, idempotency, network delay or external delivery; repeat CLI calls have no shared state. No synthetic result proves operational usefulness. Before real adapters, decide authorization scope, durable state, retries/reconciliation, source provenance and data retention. A future notification failure after authorization must be reconciled rather than blindly retried.

## Evidence

[Unit and contract tests](../../tests/test_order_workflow.py) exercise validation, boundary context propagation, rejection and dependency failures. [Process integration tests](../../tests/test_cli_process.py) run the real CLI, validate the accepted result and correlated service logs, and reject unsafe input/production use. The [implementation review](../planning/production-usefulness-review.md) and [approved amendment](../planning/production-roadmap-amendment.md) constrain claims and future adapters.

## Revisit conditions

Revisit when a real authorized source or payment/notification integration is scoped; when measured workload requires separate processes or asynchronous work; or when durable order state, idempotency and recovery are specified. Record owner approval, security/cost impact and failure evidence before replacing the in-process boundary.
