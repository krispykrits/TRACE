# Data contracts and decisions

Status: Sprint 2 Order–Payment slice, 2026-09-25. Configuration, application logs and synthetic Order workflow records exist. None is an incident evidence record.

| Existing record | Current contract | Source |
| --- | --- | --- |
| Settings | `TRACE_ENVIRONMENT` is required (`development`, `test`, `production`); `TRACE_LOG_LEVEL` is optional; invalid/unknown TRACE settings fail without echoing values | [Configuration code](../../src/trace_app/configuration.py), [development guide](../development.md) |
| Operational log | JSON to stderr with UTC timestamp, level, component, correlation ID, event, message and application version; secret fields/registered values are redacted | [Logging code](../../src/trace_app/structured_logging.py), [ADR 0003](../adr/0003-cloudwatch-hosted-logging.md) |
| Synthetic Order request/outcome | Validated order/customer IDs and positive amount in cents; accepted/rejected result with `service`, `environment` and `correlation_id` | [Workflow contract](order-payment-workflow.md), [workflow code](../../src/trace_app/order_workflow.py) |
| Boundary context | The receiving logical service name changes at each Customer, Payment and Notification call; environment and correlation ID remain unchanged | [ADR 0004](../adr/0004-synchronous-synthetic-order-workflow.md) |

## Planned evidence boundary

Issue #8 in S2 defines a source-neutral evidence envelope and read-only adapter contract; S3 adds durable investigation state and evidence snapshots; S4 adds real-source identity, access enforcement, freshness and revocation. Issue #8 will define the source-neutral envelope using synthetic fixtures; real-source-specific fields and permissions remain gated by an authorized source and use case. The [approved amendment](../planning/production-roadmap-amendment.md) and [implementation review](../planning/production-usefulness-review.md) require service/environment, event and collection time, stable source identity/revision, authorization scope, integrity/redaction state, query window and retrieval/tool version to survive normalization. Missing, partial and truncated results must be explicit. Evaluator-only labels must stay outside operational inputs.

Before ingesting real evidence, identify a pilot operator/team and source owner, obtain permitted/sanitized access, and decide retention, deletion/revocation, evidence snapshot access, redaction and recovery ownership. Those are [charter gates](../charter.md), not permissions supplied by this document. Synthetic fixtures can test contracts; they do not establish Operational Pilot usefulness.
