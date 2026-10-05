# Interfaces and API contract gates

Status: Sprint 3 local persistence merged; bounded queries proposed, 2026-10-05. TRACE exposes a local `trace-app` command, not a network API.

| Existing CLI behavior | Contract and evidence |
| --- | --- |
| `trace-app` / `--help` / `--version` | Prints help or package version without an incident source; see [CLI](../../src/trace_app/cli.py) and [smoke tests](../../tests/test_cli.py) |
| `trace-app check-config` | Validates current environment/log configuration, emits one correlated JSON operational record on success and an actionable error on invalid input; see [development guide](../development.md) |
| `trace-app demo-order` | Validates a synthetic Order request, calls in-process Customer/Payment/Notification fixtures, and returns a JSON business outcome with service/environment/correlation identity; see [workflow contract](order-payment-workflow.md) and [ADR 0004](../adr/0004-synchronous-synthetic-order-workflow.md) |

A developer-only `scripts/demo_persistence.py` command ingests, reads and queries synthetic evidence across process restarts using a fixed local scope. No investigator-facing incident request, report response, real source-query API or remediation action endpoint is implemented. The first interaction remains a CLI under the [charter](../charter.md). A future HTTP surface needs a demonstrated user need and an ADR; no route names or wire schemas are promised here.

Issue #7 defines the synthetic Order workflow; issue #8 defines the source-neutral evidence envelope; issue #10 adds the internal [SQLite snapshot and job-state contract](sqlite-investigation-store.md); issue #11 proposes [bounded local evidence reads](bounded-evidence-queries.md). Those contracts must preserve source provenance, timestamps and access scope while keeping evaluator labels separate. S4 will define bounded read-only source operations and enforce authorization independently of caller-selected filters, including evidence and citation reads. S5 will define report/citation and abstention behavior. Production mutation must use the separate approval-bound executor in the [remediation scope](../planning/production-remediation-scope.md), never an investigation tool. Design and test these contracts against the [approved amendment](../planning/production-roadmap-amendment.md) when their scoped issues begin.
