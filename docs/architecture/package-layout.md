# Package layout and dependency boundaries

Accepted direction for [#46](https://github.com/krispykrits/TRACE/issues/46), merged in [PR #47](https://github.com/krispykrits/TRACE/pull/47). [ADR 0010](../adr/0010-capability-packages-and-adapter-boundaries.md) records this change. TRACE remains one installable `trace_app` application. Its public `trace-app` and `python -m trace_app.cli` entry points, serialized schemas and retrieval defaults are preserved.

## Runtime placement

| Package | Responsibility and placement rule |
| --- | --- |
| `evidence` | Source-neutral records, bounded queries, reader contracts and deterministic timelines |
| `knowledge` | Documents/chunks, corpus/index identities, ports, vector validation, authorized search and bounded context |
| `investigation` | Request/execution, strict assessment schemas/current citation validation/protected support review, provider-neutral contracts/policy, fixed read-only tools; future bounded investigator |
| `adapters/storage/sqlite` | Existing database implementations; storage-specific schema and mapping stay here |
| `adapters/retrieval` | Exact numerical scoring and local artifact publication/loading |
| `adapters/embeddings` | Cached Sentence Transformers implementation |
| `adapters/sources` | Curated-file ingestion implementation |
| `adapters/tools` | Fixed local read worker, deadline termination and metadata-only logging audit, selected by bootstrap |
| `adapters/models` | Policy-admitted Azure Responses call in a bounded process and private SQLite provenance/spending journal |
| `runtime` | Configuration and correlated structured logging |
| `demo` | Explicit synthetic Order fixtures, replay and development scenario generation |
| `cli` | Argument handling, presentation and exit behavior |
| `bootstrap.py` | Composition factories selecting implementations for application ports |

Core packages (`evidence`, `knowledge`, `investigation`) may import each other and the standard library, never adapters, SDKs, CLI, bootstrap, demos or evaluator code. An adapter implements a TRACE-owned port and cannot import bootstrap or CLI. CLI imports composition factories rather than concrete adapters. Runtime utilities do not depend on core use cases or adapters. Demos may use core contracts but cannot access evaluators or adapters. Root `__init__.py` carries package identity; new root modules or capabilities require an explicit reviewed boundary decision.

For retrieval, `SearchService` receives `ScoreBackend`; it never imports sklearn/NumPy implementations. `create_search_service` supplies the existing exact scorer. `CorpusGeneration`, `IndexGeneration` and vector validation are framework-independent contracts, not SQLite/index-adapter exports. Source batching is a core contract; reading and hashing files is a source adapter. No serialized identity, threshold, permission or algorithm is changed by these moves.

Introduce PostgreSQL, HTTP API or remediation packages only with their scoped implementation/ADR. The [model boundary](model-provider.md) / accepted [ADR 0012](../adr/0012-model-provider-contract-and-bounded-call.md) limits `adapters/models` imports within TRACE to `investigation.provider`, `investigation.provider_policy` and runtime utilities: no evidence/knowledge/source/storage/tool handles or investigation state/bundle imports. Core admission resolves evidence independently; transports receive only prepared text. Network imports belong to adapters (core `urllib.parse` is permitted). Bootstrap selects the Azure transport and private journal explicitly; fakes/authorities remain test-only and outside the wheel. A future remediation executor remains a separate authority boundary.

## Tests and nonruntime content

| Location | Purpose |
| --- | --- |
| `tests/unit` | Isolated validation, workflow and architecture checks |
| `tests/contracts` | Port/scoring requirements exercised without external systems |
| `tests/integration` | SQLite, local artifacts, evaluator workflows and CLI subprocesses |
| `tests/live` | Explicitly opted-in provider/source checks; an empty suite fails closed |
| `tests/fixtures` | Shared test-only helpers when needed; no application imports |
| `evaluation` | Independent suites, judgments, protocols and selected retained reports |
| `corpus` | Curated development reference material, never an implicit production source |
| `docs/operations`, `docs/security` | Current operational limitations and security boundaries |

The wheel contains only `trace_app` plus distribution metadata. Tests, scripts, evaluator labels and reference corpora are excluded. Data exclusion from packaging complements authorization and evaluator isolation; it is not proof of process sandboxing. Store databases, downloaded models and generated runs outside tracked application source. Existing selected report evidence stays versioned without rewriting its hashes.

## Enforcement and contribution workflow

`make architecture-check` parses all runtime imports, including relative, type-checking and literal dynamic imports. It rejects forbidden dependencies, evaluator/test/script imports, nonliteral dynamic imports and undeclared top-level packages. Negative unit fixtures demonstrate the checks. This is a structural guardrail, not a sandbox or a substitute for code review of reflective behavior, file/network access and authorization.

Every change must identify its capability/adapter boundary, keep application contracts independent of implementation details, and update composition explicitly. Run `make check lint format-check type-check architecture-check test integration package-check`; fast CI runs the same gates. `make test` runs unit and contract suites once, `make integration` runs the integration suite, and `make integration-live` remains separate.

`make package-check` builds a wheel, exports hashed locked runtime dependencies, installs both into an isolated environment and verifies module/console entry points and the synthetic workflow from outside the checkout. It inspects wheel contents and confirms evaluator/test packages are absent. No live service, paid model or AWS operation is used.

## Evaluation provenance through the move

The v4 passage reports bind the pre-refactor scorer implementation. Use commit `43582e3f084ff645b1227bc139d4d441b99fd220` (merged #17) for exact historical rescoring. Keep those snapshots unchanged. Fresh runs use current nested source manifests; the general evaluator hashes runtime modules recursively. Do not claim that moving packages reaccepts a benchmark, or rewrite historical hashes to make current code match old evidence.

Create a new lexical exploration report with a fresh output path, then rescore it with the current checkout. The archive checkout and commands are recorded in [the evaluator guide](../../evaluation/README.md).

For #19, `investigation.bundle` composes the fixed read-only `ToolInvoker` port into a cited observed package. It imports no evaluator, demo, script or adapter; the developer fixture publisher remains in scripts and tool-choice expectations remain in evaluation. The existing import checker and negative fixtures enforce that placement.

For #35, `assessment_schema`, `assessment_context` and `assessment_validation` stay inside investigation. The fixed tool port supplies current references and an independently composed review reader supplies human support. Model adapters cannot import those acceptance/readers; core cannot import evaluator `SupportReview`/fixtures or storage adapters. ADR 0013, checker negatives and wheel requirements record this boundary without a new capability package or dependency.

For #36, `investigation.execution` owns shared admission rules and the atomic `ExecutionLedger` port. `adapters/storage/sqlite/execution` persists them beside durable jobs and revalidates active attempt/scope/lease/status inside each transaction. Pricing is a provider-neutral contract in `investigation.provider` (the journal retains its existing import alias). Policy/tool boundaries share a session selected by bootstrap; transports still receive prepared text and cannot import execution state. ADR 0014, negative imports and wheel requirements preserve that boundary. No dependency is added.
