# Typed read-only investigation tools

Accepted implementation for [#18](https://github.com/krispykrits/TRACE/issues/18) in merged [PR #48](https://github.com/krispykrits/TRACE/pull/48), 2026-10-12. The [#19 integration package](scripted-evidence-package.md) composes these tools and revalidates every emitted reference. [ADR 0011](../adr/0011-read-only-tool-execution.md) records the authority and deadline boundary. This wraps the existing [evidence queries](bounded-evidence-queries.md), [knowledge search](knowledge-retrieval.md) and [bounded context](retrieval-evaluation-context.md), within the accepted [package layout](package-layout.md).

## Catalog and input schemas

`ToolSession.invoke(name, arguments)` parses a closed object into `EvidenceArguments`, `KnowledgeArguments` or `CitationArguments`. Unknown tools/fields are rejected before a worker starts. Each tool has one bounded attempt and no automatic retry.

| Tool | Required fields | Optional fields | Result |
| --- | --- | --- | --- |
| `logs.query` | `window_start`, `window_end` | `service`, `limit` | Original log records and payloads |
| `metrics.query` | `window_start`, `window_end` | `service`, `limit` | Raw metric records, values and units; no unattributed aggregation |
| `deployments.query` | `window_start`, `window_end` | `service`, `limit` | Deployment records and revision/phase payloads; no causal inference |
| `evidence.get` | `window_start`, `window_end`, `evidence_id` | `service`, `limit`, `kind` | One evidence record, subject to the same window/service/scope rules |
| `knowledge.search` | `query` | `service`, `limit` | Original passages, full authorized citations and omission ledger |
| `knowledge.resolve` | `generation_id`, `chunk_id` | `service` | One currently authorized, generation-bound original chunk |

Fields use the existing UTC/inclusive-window contract. Window strings are at most 64 characters; identifiers/service filters are 1–128 safe ASCII characters. `kind` is `log`, `metric` or `deployment`, and cannot override a list tool's fixed kind. `limit` must be an integer, never a boolean. Operational limits default to the trusted policy's maximum of 100; knowledge defaults to five passages and supports 1–5, further restricted by policy. `query` is 1–4,000 nonblank characters without NUL. Citation IDs require `gen-` or `chunk-` followed by 64 lowercase hex characters.

No argument can select an investigation, environment, grants, files, credentials, deadline, SQL, shell, encoder, publisher method or evaluator store. SQL/shell-shaped free text in a knowledge query remains search data; it is never executed. The catalog has no operational mutations, evaluator-label read tool or arbitrary method dispatch.

## Trusted composition and permissions

`bootstrap.create_tool_session` receives configured evidence/corpus/index paths and a validated `ToolScope`. The scope fixes an investigation ID, correlation ID, independent `TrustedQueryContext`/`CorpusReadContext` grants and one consistent environment. These come from trusted application composition, not model-selected fields or source text. A selected service only narrows the relevant source's grants. Omitting it never means unrestricted access.

Operational queries use `EvidenceQueryService` under those grants. Direct IDs receive the same checks, including event window, kind and environment; absent and inaccessible IDs return the same authorization result. Knowledge search checks policy before ranking and before returning citations. Citation reads check the configured index generation, source fingerprint, current source grants, retention/freshness and withdrawals; a selected service must also match the chunk. Rank scores are not confidence or proof of answerability.

Each local worker opens existing private SQLite files with `mode=ro` and `query_only=ON`. Read-only opening does not create a database, migrate a schema or initialize publisher tables. Corpus read snapshots use deferred read transactions. Source publishing, ingestion, job writes and withdrawal remain separate owner/application operations through separate handles. The tool catalog cannot select them. Index artifacts are read, never rebuilt by a tool.

The worker is a fixed installed module, launched with Python `-I` and a small explicit environment; it does not inherit publisher database handles, caller Python path configuration or secret environment variables. Worker stderr is suppressed; failures expose safe reason codes, not exception text, paths or credentials. Configured paths are trusted deployment inputs and must point to approved source stores. Filesystem/OS access still requires deployment controls: this worker is deadline isolation, not a general file/network sandbox. No real operational adapter, remote authentication or cloud credential is added here.

The default read clock is current UTC inside the worker. A trusted `read_clock` injection exists for deterministic tests and the explicitly synthetic demo; it is not a tool argument or production clock configuration. Real-source composition must retain the current clock and current grants.

## Execution and result bounds

| Policy field | Default | Supported ceiling |
| --- | --- | --- |
| `max_attempts` | 20 | 100 |
| `max_duration_ms` | 120,000 | 600,000 |
| `call_timeout_ms` | 5,000 | 10,000 |
| `max_results` | 100 | 100 |
| `max_window_seconds` | 86,400 | 86,400 |
| `max_result_bytes` | 65,536 | 1,000,000; minimum 512 |

These are configurable implementation safety bounds, not owner performance/cost thresholds or an operational SLA. The session's monotonic duration includes gaps between requests. Validation failures and concurrent denied calls consume attempts. Only one worker can be active in a session; concurrent requests are rejected and audited, with no queued workers or retries. A worker's timeout is the smaller remaining session duration and per-call limit. Timeout kills and reaps the worker; no late or partial worker output is released. OS startup/termination scheduling adds overhead, and returned audit duration reports observed elapsed time rather than promising hard real-time behavior.

The private worker request is bounded to 32,768 bytes. The result-byte bound covers UTF-8 JSON of `ToolPayload` (`status`, `data`, `reason`), including metadata/escaping. It excludes the separate audit envelope and future model prompt. Operational results retain whole records; dropped records are disclosed through `byte_budget_omissions`, `truncated` and original authorized `matching_count`. Result-limit truncation and source gaps remain explicit. If even an individual result or its metadata cannot fit, the entire result is omitted with `whole_result_omitted: true`, `truncated: true` and `result_byte_bound_exceeded`; no source quote is cut or rewritten.

Knowledge search retains 20 lexical candidates with up to 20 passages per document, then uses the #17 assembler for at most the requested five passages and 8,192 canonical data bytes, further restricted by the outer result bound. Its diagnostic ledger remains available. No reranker, new default, semantic dependency or model call is introduced.

## Output and error matrix

The result is `{audit, status, data, reason}`. `audit.version` is `investigation-tools.v1`. Successful source data is explicitly `untrusted_source_data`; it retains source revisions, event/collection timestamps, source identity, access/redaction status and integrity/citation mappings. Evidence record envelopes preserve their `schema_version`. The adapter does not silently rewrite source content or claim to sanitize a future real source; source publishers must supply appropriately redacted authorized material.

| Status | Meaning and payload behavior |
| --- | --- |
| `ok` | Authorized data returned within the bounds |
| `empty` | A successful complete query has no matches |
| `partial` | Source availability gaps, result/byte limits or context omissions; inspect diagnostics even when no items fit |
| `validation_error` | Unknown tool, extra/malformed fields, unsafe identifier or result/window limit; no source read |
| `authorization_error` | Service/grants/environment/window/source policy or direct-ID/citation denial; no data |
| `timeout` | Worker deadline expired or a late backend result was discarded; no data |
| `dependency_failure` | Missing snapshot, incompatible/missing source/index, read/worker failure, invalid output or failed audit; no fabricated successful empty result |
| `budget_exhausted` | Attempt/session budget exhausted or another call is active; no worker starts |

Reasons are bounded safe codes. Missing snapshots remain `snapshot_missing`; other dependency failures expose safe availability codes. Audit sink failure returns `audit_unavailable` without releasing source content. Assessing or endorsing a report cannot authorize a consequential action; production remediation remains a separate deterministic executor with concrete approval and verification gates.

## Audit and demonstration

Every attempt records version, tool catalog name (or `unknown`), correlation ID, unique attempt ID, attempt number, monotonic elapsed milliseconds and outcome. `LoggingToolAudit` emits `tools.attempt.completed` through the existing structured/redacted TRACE logger. It logs neither arguments, source bodies, model query text, grants, configured paths nor exception text. A normal host caller configures logging at startup. Child readers' incidental logs are not mixed into the parent result/audit channel. CloudWatch agent delivery and hosted audit acceptance remain separate deployment work; local records do not supply that evidence.

From the repository root:

```sh
uv run --locked python scripts/demo_tools.py
uv run --locked python scripts/demo_tools.py --output /tmp/trace-tools-demo.json
uv run --locked python -m unittest tests.contracts.test_tools tests.integration.test_tools -v
make check lint format-check type-check architecture-check test integration package-check
```

Use a fresh output filename. The demo publishes explicit synthetic log/metric/deployment fixtures and the development knowledge corpus through separate administration handles, then closes them before invoking the six read tools. It also shows denied Notification access, a rejected 101-record request and a rejected shell call. Sources disclose the missing authorized operational export. Its source clock is fixed to 2026-10-12; audit elapsed times/attempt IDs are real execution metadata. Temporary stores/indexes are removed before return. Neither the demo nor tests read benchmark labels or supply Operational Pilot acceptance.

Tests exercise kind separation and original provenance, direct-ID/grant/environment/window denial, complete empty versus partial/missing results, saved-citation scope/generation/freshness/withdrawal, whole-record/whole-context byte omissions, rejected writes and no database creation/migration, actual timeout/worker reaping, session attempts/duration/concurrency, hostile input/source text and metadata-only redacted audit. The installed-wheel check verifies that the isolated worker module is present and fails closed on an invalid private protocol outside the source checkout.

The [saved demonstration](../../evaluation/reports/investigation_tools_demo_v1.json) records nine calls: three partial operational lists with disclosed missing-source coverage, three successful direct evidence/knowledge/citation reads, and the expected authorization/limit/shell rejections. Full local checks passed with 36 unit, 14 contract and 119 integration tests (including 16 CLI process checks), plus architecture and installed-wheel verification. The first package-check attempt could not resolve PyPI in the restricted sandbox; the required check passed after fetching the already-pinned build dependency with approved network access.
