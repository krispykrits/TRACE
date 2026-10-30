# Operating boundary

Use [current status](../current-status.md) for progress and [development](../development.md) for runnable local commands.

## What can be operated now

| Capability | Current operating limit |
| --- | --- |
| CLI/replay and knowledge demos | Local synthetic development/test behavior |
| SQLite evidence/jobs/workflow artifacts | Private local storage; schema-1/2 job databases migrate to schema 3 through writable startup |
| Azure connector | Explicit trusted composition/private files and separate paid-check authorization; historical synthetic check only |
| Bounded investigator | [Local CLI](../architecture/investigator-cli.md) with explicit provider, current-authority saved inspection/export, cancellation and no automatic paid replay; trusted local files |
| Hosted runtime/source integration | AKS, shared PostgreSQL, pod identity, Azure collection and operational source acceptance remain planned |

## Local handling

- Use fresh private output paths for demonstrations; do not overwrite accepted/frozen artifacts.
- Preserve existing job/provider/execution journals after interruption. Deleting or switching a journal cannot reset spending or authorize an uncertain paid replay.
- Open older job databases once through writable `SQLiteInvestigationStore` before read-only workers; unsupported newer schemas fail explicitly. [The storage contract](../architecture/sqlite-investigation-store.md) owns migration/deletion semantics.
- Inspect current job/attempt/lease and unknown outcomes through trusted application contracts. A completed job can still require support review; no report or successful API submission proves service recovery.
- Keep database, private config/key files, output and backup access restricted. Application terminal deletion is not proof that filesystem copies or backups were erased.
- Report source/provider/storage failures and missing permissions explicitly. Do not replace them with fixtures or unsupported diagnosis.

The [local readiness guide](local-readiness.md) covers the offline comparison, protected inspection and owner handoff. The [local recovery procedure](local-recovery.md) covers quiescent synthetic backup/restore, interruption, unknown outcomes, journal ownership and retention/deletion boundaries. Its real CLI/SQLite fault checks are development evidence. Operational backup/restore acceptance, automatic retention, provider reconciliation, hosted collector recovery and production runbooks remain separate gates.

## Hosted runbook requirements

[Deployment](../../deploy/README.md), [cloud design](../architecture/azure-cloud.md) and [#55–#60](../planning/azure-cloud-backlog.md) own the Azure acceptance sequence.

Each procedure must identify environment/release, accountable owner, prerequisites, exact commands, expected outcome and verification. Cover:

- Image digest/config identity, startup/readiness and graceful termination.
- Pod identity and least privilege, credential ownership/rotation and account restrictions.
- Schema/shared-state migration, spending admission, duplicate/crash handling and uncertain-call reconciliation.
- Backup/restore/vector rebuild, source revocation, retention/deletion including derived data/backups.
- Log correlation/access/retention, collector outage/recovery and content-free audit.
- Release rollback, escalation/stop/recovery and teardown/recreation with residual billable resources.

Kubernetes retries do not authorize paid replay. Keep infrastructure/account cost separate from the $20/month application model cap. Initial investigation remains read-only; real remediation uses [exact-action approval and outcome verification](../planning/production-remediation-scope.md).
