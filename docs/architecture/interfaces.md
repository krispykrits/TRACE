# Interfaces and API contract gates

Status: Sprint 1 foundation, 2026-09-25. TRACE exposes a local `trace-app` command, not a network API.

| Existing CLI behavior | Contract and evidence |
| --- | --- |
| `trace-app` / `--help` / `--version` | Prints help or package version without an incident source; see [CLI](../../src/trace_app/cli.py) and [smoke tests](../../tests/test_cli.py) |
| `trace-app check-config` | Validates current environment/log configuration, emits one correlated JSON operational record on success and an actionable error on invalid input; see [development guide](../development.md) |

No investigation request, report response, source-query API or remediation action endpoint is implemented. The first interaction remains a CLI under the [charter](../charter.md). A future HTTP surface needs a demonstrated user need and an ADR; no route names or wire schemas are promised here.

S2 will define a TRACE-owned investigation input and evidence adapter contract. It must preserve source provenance, timestamps and access scope while keeping evaluator labels separate. S4 will define bounded read-only source operations and enforce authorization independently of caller-selected filters, including evidence and citation reads. S5 will define report/citation and abstention behavior. Production mutation must use the separate approval-bound executor in the [remediation scope](../planning/production-remediation-scope.md), never an investigation tool. Design and test these contracts against the [approved amendment](../planning/production-roadmap-amendment.md) when their scoped issues begin.
