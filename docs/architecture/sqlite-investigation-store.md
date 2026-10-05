# Local SQLite investigation and evidence store

Status: Sprint 3 issue [#10](https://github.com/krispykrits/TRACE/issues/10), implementation proposed 2026-10-05. [ADR 0005](../adr/0005-sqlite-local-postgresql-rds-cloud.md) selects SQLite locally and PostgreSQL on RDS later. This store accepts synthetic development/test evidence only.

## Reproduce the restart demonstration

Use Python 3.12 and the locked development environment. Choose a database path outside the repository:

```sh
uv run --locked python scripts/demo_persistence.py ingest --db /tmp/trace-story-10.sqlite3 --seed 17 --mode failure --submission-key case-17
uv run --locked python scripts/demo_persistence.py show --db /tmp/trace-story-10.sqlite3 --investigation-id <id-from-ingest>
```

The second command opens the file in a new process and returns the same evidence IDs, source provenance, log payloads and source availability. Repeating `ingest` with the same submission key and scenario reports zero newly ingested records. An invalid seed fails before creating the file. The demo uses the fixed trusted scope `local:synthetic`; it is a contributor check, not an investigator or real-source API.

## Contract and schema

`InvestigationRequest` records submission key, service, environment, access scope, UTC query window and optional expiry. `EvidenceSnapshot` carries ordered `EvidenceEntry` values and source availability. Each entry preserves the version 1 [evidence envelope](dependency-replay-evidence.md) and one typed payload:

| Kind | Payload |
| --- | --- |
| Log | Bounded message |
| Metric | Name, finite numeric value, unit |
| Deployment | Revision, phase |

Only these fields enter the operational store. Raw evidence parsing rejects missing fields, unsupported schema versions and extra fields, including evaluator labels. Every record retains its evidence ID, service/environment, observed and collected UTC times, source record ID/revision, access/redaction status, correlation and integrity digest. Source `available`, `unavailable` and `truncated` status survives round-trip; absent telemetry is never synthesized.

SQLite `PRAGMA user_version=1` creates `investigations`, `attempts`, `snapshots`, `evidence` and `deletion_audit` in one transaction. Reopening a version 1 database is repeatable; newer schemas are rejected. No evaluator manifest or label table is in this database. The ground-truth file remains under `evaluation/ground_truth`, outside the application wheel and store. The SQLite database is created mode 0600; existing files with broader permissions or symlink paths are rejected.

Snapshots are bounded by default to 1,000 records and 1,000,000 serialized bytes; callers can lower these limits. A snapshot query window must equal its investigation window. One transaction inserts the snapshot and all records. A mid-batch failure rolls back everything. The key `(access_scope, submission_key)` makes identical submissions return the existing investigation; changed request content under that key conflicts. Re-ingesting logically identical evidence returns zero even when collection time changed, preserving the first stored `collected_at`. Changed event, provenance, kind, payload, query window or source availability conflicts. Duplicate source record ID/revision or evidence ID within a snapshot is rejected.

## Execution state and dispatch

`queued → running → completed` records a separate `supported` or `abstained` assessment and `unreviewed` review status. Failed, cancelled and expired investigations retain `pending` assessment/review status. A review decision records `approved` or `rejected` for a completed assessment; this is not approval to execute a remediation.

Execution timestamps and optional expiry are normalized to fixed-width UTC microseconds before SQLite comparisons. A worker can transactionally claim one queued investigation and gets an attempt ID and lease. The default lease is 30 seconds. Each submission stores its maximum attempt count (default three), so recovery uses the same bound after restart. These are safety limits, not service targets. A worker must submit its attempt ID before the lease expires to complete or fail an attempt. A supported assessment requires at least one stored observation; an empty snapshot can complete as abstained. Expired leases become interrupted attempts and return to the queue until the attempt limit is reached. Stale completions are rejected. Explicit failure can queue a retry or mark the investigation failed. Recovery, expiry, cancellation and retry updates are transactional. There is no broker or background worker in this story; later orchestration may poll the database using this contract.

## Access, retention and deletion

Application reads require the trusted access scope recorded at submission; a wrong scope and an absent ID produce the same access error. The developer demo fixes its scope internally and cannot select another scope. Direct filesystem access to SQLite bypasses application checks, so the containing machine and backup access must also be restricted. No real operational source has been authorized. The store rejects non-synthetic evidence classification and production-environment submissions until source ownership, authorization, redaction, retention and deletion policy are settled. These are [charter gates](../charter.md), not permissions implied by this implementation.

No retention duration has been approved. Keep only local synthetic fixtures for now. `delete_terminal` removes a terminal investigation, its attempts and evidence in one transaction and retains a metadata-only deletion audit row. SQLite secure deletion is enabled; filesystem copies and backups require their own deletion handling. Automatic retention, authorized real-source reads, multi-process worker operations, backup/restore and SQLite-to-RDS migration remain later gates. Tests cover restart, failure rollback, duplicate submission/ingestion, scope denial, label isolation, stale attempts and terminal deletion.
