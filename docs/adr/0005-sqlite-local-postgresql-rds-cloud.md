# ADR 0005: SQLite for Local MVP and PostgreSQL on RDS for Cloud MVP

- **Status:** Accepted direction by the owner, 2026-09-25; implementation and migration pending
- **Decision owner:** Project owner
- **Scope:** Investigation execution state and bounded evidence snapshots; this does not select an incident log source or a retrieval index.

## Context

The Local MVP needs durable evidence and investigation state in Sprint 3 [issue #10](https://github.com/krispykrits/TRACE/issues/10), after issue #8 defines the evidence contract. The Cloud MVP moves the same workflow to Terraform-managed EC2 in S7–S9. The [approved amendment](../planning/production-roadmap-amendment.md) requires recoverable dispatch, duplicate handling, backup/restore and retention/deletion before hosted investigations. The owner selected SQLite for the Local MVP and a later switch to PostgreSQL through Amazon RDS. Cloud workload, overall spending limits, access policy and database sizing remain open [charter](../charter.md) gates.

## Decision

Implement the Local MVP's durable investigation/evidence store with Python's standard-library `sqlite3` in issue #10. Store operational evidence snapshots, provenance and source revisions, stable IDs, investigation execution state, attempt records and assessment/review status under explicit schema versions. Keep evaluator-only labels and ground truth in separate paths and credentials. Define transactional ingestion/idempotency and migration behavior in #10; prove restart, duplicate handling and failure behavior before claiming acceptance. Do not copy whole operational log sources into this store by default.

During S7 design and S8 deployment, migrate the Cloud MVP's shared state to PostgreSQL on Amazon RDS. Keep storage access behind the narrow TRACE-owned contract exercised by #10/#11 so the migration can be tested without changing investigator-facing evidence identities. Define the RDS engine version and any approved extension version, instance/storage/backup configuration, network and database roles, secrets, retention/deletion, migration/rollback and spending estimate before provisioning. S9 acceptance must demonstrate data migration, recovery/restore, access boundaries and teardown/recreation. This decision selects the database product direction, not an AWS apply, a cost commitment or an authorization to ingest real operational data.

## Alternatives

| Option | Tradeoff and disposition |
| --- | --- |
| SQLite locally, PostgreSQL on RDS in cloud | Selected: minimal credential-free Local MVP persistence, then a managed shared database at the cloud gate. Requires an explicit migration and two adapter validations. |
| PostgreSQL from Sprint 3 | Deferred: adds a local server and operational setup before the small synthetic workflow needs them. |
| SQLite as the final cloud state store | Rejected as the planned Cloud MVP destination by owner choice; it would keep state tied to the EC2 host and require a different shared access/recovery design. |
| Ad hoc JSON files or a separate NoSQL store | Rejected for investigation/job state because transactional updates, queries, migrations and duplicate policy are required. |

## Consequences

SQLite keeps Local MVP setup within the existing Python runtime and works well for local application storage with modest concurrent writes; it allows only one writer at a time. PostgreSQL/RDS adds AWS cost, network and identity configuration, schema/data migration, backup/restore and operational ownership. Keep source authorization independent of caller-selected filters and enforce it for evidence reads, exports and citations; database row-level security, if later used, is defense in depth and must be tested with the actual runtime role. CloudWatch remains the selected store for TRACE application logs, not the investigation-state database. A vector storage decision is recorded separately so retrieval storage does not silently become the system of record for evidence.

## Evidence and limits

The owner's 2026-09-25 selection sets the direction. [Issue #10](https://github.com/krispykrits/TRACE/issues/10), the [capstone plan](../planning/capstone-project-plan.md) and the [production-usefulness amendment](../planning/production-roadmap-amendment.md) supply the acceptance and migration gates. [SQLite's usage guidance](https://www.sqlite.org/whentouse.html) describes its local-storage and single-writer fit; [Amazon RDS resilience guidance](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/disaster-recovery-resiliency.html) describes backup and restore options. No TRACE schema, SQLite store, RDS database, migration or measured workload exists yet.

## Revisit conditions

Revisit implementation details when #8 fixes the evidence envelope, #10 measures local write/restart behavior, and S7 establishes workload, budget, authorized AWS identity and recovery requirements. If the selected RDS shape cannot meet those gates, record the constraint and obtain a new owner decision before changing the product direction. Do not claim migration success until a tested export/import or equivalent repeatable path preserves evidence IDs, provenance, access scope and job state.
