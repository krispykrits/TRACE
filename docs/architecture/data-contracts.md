# Data contracts and decisions

Status: Sprint 2 dependency replay proposal, 2026-10-05. Configuration, application logs, synthetic Order records and version 1 synthetic incident evidence have distinct contracts.

| Existing record | Current contract | Source |
| --- | --- | --- |
| Settings | `TRACE_ENVIRONMENT` is required (`development`, `test`, `production`); `TRACE_LOG_LEVEL` is optional; invalid/unknown TRACE settings fail without echoing values | [Configuration code](../../src/trace_app/configuration.py), [development guide](../development.md) |
| Operational log | JSON to stderr with UTC timestamp, level, component, correlation ID, event, message and application version; secret fields/registered values are redacted | [Logging code](../../src/trace_app/structured_logging.py), [ADR 0003](../adr/0003-cloudwatch-hosted-logging.md) |
| Synthetic Order request/outcome | Validated order/customer IDs and positive amount in cents; accepted/rejected result with `service`, `environment` and `correlation_id` | [Workflow contract](order-payment-workflow.md), [workflow code](../../src/trace_app/order_workflow.py) |
| Boundary context | The receiving logical service name changes at each Customer, Payment and Notification call; environment and correlation ID remain unchanged | [ADR 0004](../adr/0004-synchronous-synthetic-order-workflow.md) |
| Synthetic incident evidence | Version 1 envelope with stable evidence/source IDs, UTC observed and collected times, provenance, access/redaction status, correlation, window and source availability | [Dependency replay contract](dependency-replay-evidence.md), [ADR 0007](../adr/0007-synthetic-evidence-identity-and-isolation.md) |

## Evidence boundary and next increment

Issue #8 implements the [synthetic replay envelope](dependency-replay-evidence.md) and an explicit unavailable status for the unsupplied sanitized export. Evaluator-only labels remain outside operational inputs and exports. The [approved amendment](../planning/production-roadmap-amendment.md) and [implementation review](../planning/production-usefulness-review.md) still require S3 durable investigation/evidence state and S4 real-source identity, authorization across reads/citations, freshness and revocation. Missing or truncated source results must be represented explicitly; no absent telemetry becomes an observation.

Before ingesting real evidence, identify a pilot operator/team and source owner, obtain permitted/sanitized access, and decide retention, deletion/revocation, evidence snapshot access, redaction and recovery ownership. Those are [charter gates](../charter.md), not permissions supplied by this document. Synthetic fixtures can test contracts; they do not establish Operational Pilot usefulness.
