# Current operational boundary

TRACE currently supports a local CLI, synthetic replay, SQLite state, curated knowledge and offline evaluation. The [development guide](../development.md) supplies supported commands; [package layout](../architecture/package-layout.md) identifies the implementation boundaries. Run the deterministic quality gates before promoting a code change.

The selected EC2/RDS/CloudWatch direction is deployment preparation. No hosted runtime, backup/restore procedure, automated retention scheduler or operational-source integration is verified. See [infrastructure responsibilities](../../deploy/README.md) for the apply and recovery gates. Synthetic demonstrations create temporary state and cannot establish hosted acceptance.

Add service-specific deployment, startup/readiness, migration, backup/restore, retention/deletion, rollback and escalation procedures here when their implementations are introduced. Each procedure must identify the exact environment/release, owner, prerequisites, commands, expected outcomes and verification evidence. Record blocked or untested steps explicitly. Do not describe a local deletion method as backup deletion or an issued provider request as verified recovery.
