# ADR 0006: pgvector on PostgreSQL for cloud retrieval storage

- **Status:** Proposed response to the owner's vector-database request; confirm in PR review
- **Date:** 2026-09-25
- **Decision owner:** Project owner, with retrieval evidence from issue #16
- **Scope:** Versioned knowledge chunks and embeddings; investigation/evidence state remains under [ADR 0005](0005-sqlite-local-postgresql-rds-cloud.md).

## Context

The owner requested a vector database alongside SQLite for the Local MVP and PostgreSQL on Amazon RDS later. The request did not name a vector product or a deployment phase. TRACE's [Local MVP plan](../planning/capstone-project-plan.md) keeps a small exact-search retrieval baseline, and [issue #16](https://github.com/krispykrits/TRACE/issues/16) requires an embedding/storage ADR, reproducible configuration, measured retrieval and authorized citation resolution. PostgreSQL on RDS is already the selected Cloud MVP state destination. Amazon RDS for PostgreSQL lists `pgvector` as a supported extension, with version availability depending on the engine release; the exact compatible versions must be checked during S7 design.

## Proposed decision

Use PostgreSQL with the `pgvector` extension as TRACE's initial **cloud vector database**, in the same RDS product selected for durable state. Keep knowledge chunks, source revisions, access metadata, embedding model/version and index generation explicitly versioned. Preserve the exact in-process retrieval baseline for the small Local MVP corpus while #16 evaluates semantic, lexical and hybrid retrieval. Do not add an approximate nearest-neighbor index by default: compare exact search first and add HNSW or another index only when measured latency/recall results justify it. Enforce authorized scope before candidate retrieval and again when resolving citation IDs; a caller-selected service filter never grants access.

S7 checks RDS engine/extension compatibility, data model, authorized filtering, backup/restore and cost. If this proposal is approved, S8 enables the extension and migrates the selected corpus/index with a documented rebuild/rollback path. The extension must not be provisioned before the relevant budget, workload, source-access and deployment gates are met. A separate hosted vector service is not selected by this proposal; if the owner intended one, revise this ADR before infrastructure work.

## Alternatives

| Option | Tradeoff and disposition |
| --- | --- |
| PostgreSQL plus pgvector on the selected RDS database | Proposed: one cloud database product can hold relational metadata and vectors, with a versioned retrieval contract. Adds extension/version and index maintenance work. |
| Separate vector database service | Deferred pending an explicit owner choice or measured need; adds another cost, identity, access, backup and deletion boundary. |
| Exact in-process search only | Retained as Local MVP correctness baseline; insufficient to fulfill the requested cloud vector-database direction by itself. |
| SQLite vector extension for Local MVP | Deferred: would add an extension dependency before #16 establishes a need for one. |

## Consequences

The Local MVP remains credential-free and uses a small exact-search baseline. Cloud retrieval storage shares RDS availability and cost gates with investigation state, while retaining separate tables/contracts and authorization tests. Embedding and index versions, source revision, redaction, deletion/revocation and citation identity need migration/rebuild tests. Approximate indexes can change result recall and filtering behavior; measure them against the exact baseline. A vector distance is retrieval evidence, not diagnostic confidence or causal proof. No pgvector extension, RDS instance, embedding model or corpus migration is implemented by this ADR.

## Evidence and limits

The [pgvector project](https://github.com/pgvector/pgvector) documents exact search and optional HNSW/IVFFlat indexes; the [RDS PostgreSQL extension catalog](https://docs.aws.amazon.com/AmazonRDS/latest/PostgreSQLReleaseNotes/postgresql-extensions.html) lists supported `pgvector` versions. The [production-usefulness review](../planning/production-usefulness-review.md) recommends preserving the small exact-search baseline and moving storage behind an adapter only when needed. No TRACE retrieval benchmark, target dimensions, RDS version, cost estimate or authorized operational corpus has been selected yet.

## Revisit conditions

Revisit the separate-service choice if the owner clarifies that intent, or if #16/S7 measurements show pgvector cannot meet authorized filtering, quality, latency, scale, recovery or cost constraints. Freeze model/index versions and thresholds before acceptance runs; document a migration and citation-integrity path before changing storage.
