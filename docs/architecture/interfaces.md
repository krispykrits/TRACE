# Interfaces and API contract gates

Status: Sprint 3 local foundations merged; Sprint 4 corpus boundary proposed, 2026-10-12. TRACE exposes a local `trace-app` command, not a network API.

| Existing CLI behavior | Contract and evidence |
| --- | --- |
| `trace-app` / `--help` / `--version` | Prints help or package version without an incident source; see [CLI](../../src/trace_app/cli.py) and [smoke tests](../../tests/test_cli.py) |
| `trace-app check-config` | Validates current environment/log configuration, emits one correlated JSON operational record on success and an actionable error on invalid input; see [development guide](../development.md) |
| `trace-app demo-order` | Validates a synthetic Order request, calls in-process Customer/Payment/Notification fixtures, and returns a JSON business outcome with service/environment/correlation identity; see [workflow contract](order-payment-workflow.md) and [ADR 0004](../adr/0004-synchronous-synthetic-order-workflow.md) |

A developer-only `scripts/demo_persistence.py` command ingests, reads and queries synthetic evidence across process restarts using a fixed local scope. No investigator-facing incident request, report response, real source-query API or remediation action endpoint is implemented. The first interaction remains a CLI under the [charter](../charter.md). A future HTTP surface needs a demonstrated user need and an ADR; no route names or wire schemas are promised here.

Issue #7 defines the synthetic Order workflow; issue #8 defines the source-neutral evidence envelope; issue #10 adds the internal [SQLite snapshot and job-state contract](sqlite-investigation-store.md); issue #11 implements [bounded local evidence reads](bounded-evidence-queries.md). Those contracts must preserve source provenance, timestamps and access scope while keeping evaluator labels separate. S4 will define bounded read-only source operations and enforce authorization independently of caller-selected filters, including evidence and citation reads. S5 will define report/citation and abstention behavior. Production mutation must use the separate approval-bound executor in the [remediation scope](../planning/production-remediation-scope.md), never an investigation tool. Design and test these contracts against the [approved amendment](../planning/production-roadmap-amendment.md) when their scoped issues begin.

## Development-suite replay

`trace-app replay-scenario --environment test --case c01 --seed 17` selects an explicit synthetic fixture (`c01`–`c04`), with optional `--without-distractor`. Stdout contains only observed status and a version 1 typed evidence snapshot; configuration and evaluator labels are excluded. Replay is restricted to development/test, invalid inputs fail with exit 2, and valid exports return 0 even for observed dependency failure. See the [scenario contract](development-scenarios.md) for source availability, identity, reset, delayed capture and split boundaries. This fixture selector is a developer command, not an investigator access grant.

## Corpus ingestion and read boundary

`uv run --locked python scripts/demo_corpus.py` ingests the six curated development sources twice across a restart and resolves 18 stable chunks. This developer command uses a fixed synthetic clock, grants and temporary database. The [corpus contract](knowledge-corpus.md) exposes `CorpusSource.load()` for trusted source adapters and scoped `read_chunks`/`resolve` operations. Ingestion, withdrawal and retention purge are publisher administration, not investigator tools. Current access/freshness/tombstones also apply to saved generations. No embedding/search endpoint, live source publisher or remote authentication is implemented here.
