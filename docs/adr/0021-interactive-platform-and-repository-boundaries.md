# ADR 0021: Interactive platform and repository boundaries

Status: Accepted owner direction, 2026-10-15; S7 design refinement and implementation pending.
Owner: krispykrits.
Supersedes the single-repository/CLI-default hosted direction in ADRs 0001, 0015 and 0017 only. Local CLI behavior, core import rules, Azure selection and JSON-first delivery remain valid.

## Context
TRACE's intended end state is an interactive incident investigation and engineer-approved response platform. The current Python CLI is a useful local entry point, not the final hosted interface. Repository separation must follow responsibility rather than creating one service for each internal capability.

## Decision
| Repository | Ownership | Runtime |
| --- | --- | --- |
| TRACE (existing; logical name trace) | Modular Python core, API, runner, adapters, tests and independent evaluation tooling | HTTP API and persistent investigation worker |
| trace-web | Submission, progress, evidence/timeline, cited reports, response comparison and approval interface | Web application |
| trace-testbed | .NET Order/Payment services, telemetry/export contracts and bounded scenarios | Two APIs and scenario jobs |
| trace-platform | Terraform, AKS environment composition, identity/network/monitoring and deployment operations | Infrastructure/release pipelines |
| trace-executor | Supported deterministic operational actions and verification; introduce with S14 remediation | Restricted executor |

Names other than the existing TRACE repository are intended destinations, not created repositories. S7 refines extraction and release contracts. Keep Dockerfiles and component CI with source; deploy immutable digests through platform configuration. Keep evaluation with TRACE, excluded from runtime packages/images; preserve original reports and reproduction commits.

The API authenticates users, authorizes scope, durably submits idempotent investigations, returns IDs, exposes status/cancellation and protected reports, and records response selection/approval. A persistent worker executes bounded investigations independently of HTTP requests. CLI remains available for local development, evaluation and scripted use. API and worker may share an image with distinct entry points and scoped identities.

Use PostgreSQL-backed durable work dispatch initially: transactional submission, atomic claims, leases, retries, cancellation and attempt/spending admission. Treat uncertain external outcomes conservatively. No separate message broker is required. Revisit if measured throughput, dispatch latency, contention or additional consumers justify one. Persistent workers support recurring interactive requests and reusable model/cache initialization; batch Jobs remain appropriate for evaluation, corpus rebuilds, migrations and scenarios.

## Flexible source boundary
Use source-neutral capability contracts for telemetry, knowledge, change/deployment records and workload state, with shared provenance and access rules. JSON and Azure Monitor are initial implementations, not the abstraction.
Adapters declare supported capabilities/filters, enforce scope/time/result/byte/deadline/pagination bounds, and normalize original identity/revision, event/collection timestamps, correlation, units, provenance and explicit completeness. Preserve distinct unavailable, partial, denied and successful-empty outcomes.
Allow on-demand reads, batch import and scheduled/event-driven ingestion where required. Add a dedicated ingestion worker only for demonstrated lifecycle, volume or credential-isolation needs. No arbitrary provider query language is granted to model text.
Keep source reads, transmission to models and saved disclosure independently authorized. Retrieval, model access, embeddings and ML stay modules until independent hardware/scaling/ownership needs establish extraction.

## Authority and response
The UI uses the API; it holds no database/source credentials. Separate API, investigation-read, collection/deployment and execution authority. One database server may host separate schemas/roles without sharing unrestricted credentials.
Recommendations and selections do not grant execution authority. Code/configuration changes follow reviewed tests/releases. The executor verifies durable concrete approval and current target state, executes a supported action, reconciles duplicates/unknown outcomes and verifies results using separate write credentials.

## Delivery and consequences
S6 preserves Local MVP acceptance. S7 owns architecture/repository/contracts/identity refinement and capacity sizing. S8 implements API/worker and state/deployment; S9 accepts hosted behavior. A required web delivery track follows API stabilization and completes before S15 pilot; it can use an additional undated increment if capacity requires. S14 integrates ranked responses and executor/approval UI.
Benefits: interactive operation, isolated workload/platform/action ownership and reusable core.
Costs: cross-repository releases, user authentication, asynchronous recovery and extra deployment operations. Cross-repository schema compatibility, pinned versions and smoke checks are required. Do not claim implementation or create resources through this ADR.
