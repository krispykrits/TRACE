# Local recovery and consistent restore

This procedure covers TRACE's trusted local Linux/filesystem composition and synthetic SQLite data. It does not establish operational authentication, real-source retention approval, Azure PostgreSQL/AKS recovery or provider-side reconciliation. Initial investigation remains read-only. The invoking maintainer owns stopping every local writer and restricting the backup; the final operational cleanup owner remains an owner input.

## Interruption and restart

Stop the CLI, tool/model workers and every other process sharing the job database or monthly provider journal. Preserve the original files before investigation. Do not delete a database, change submission identity, replace the journal, increase limits or initialize spending to zero to make a failed attempt run again. Leave `TRACE_ALLOW_PAID_LIVE` unset during recovery inspection.

Inspect job/attempt status, execution calls and monthly reservations through trusted local access. A retained evidence artifact can exist without a published assessment. A review-required proposal is not an accepted assessment; neither a completed job nor an abstention proves service recovery. A crash inside publication must leave both its artifact and completed status absent, or both committed. Inspect saved reports through the CLI so current source/revision/sensitivity/support/transmission checks run again.

Same-key CLI submission returns the original investigation; it does not resume an interrupted provider request. Lease recovery marks interruption/expiry but does not clear the execution ledger, original deadline, token allowances or monetary reservation. New claims must still pass existing execution admission. An uncertain dispatched or reserved monthly attempt blocks another request for that investigation. The journal may report this conservatively as `budget_exhausted`; it is not evidence that a request was free or definitely never dispatched.

There is no automatic provider reconciliation/replay procedure. Keep uncertain reservations charged and dispatch disabled until actual provider/account records can be reconciled under a separately reviewed implementation/decision. Do not hand-edit journal outcomes or infer that `failed`, cancellation or lease expiry releases spending. Cancellation/deadline propagation is best effort for an already dispatched external request; unknown outcomes remain explicit.

## Quiescent backup set

A consistent recovery set contains the job/evidence/workflow/execution database, associated corpus database and exact immutable index generation, provider spending journal, source/review/configuration bindings and an inventory of hashes. Keep secret credentials in their separately controlled store; a backup does not create new source or transmission rights. Use private directories (0700) and files (0600).

1. Stop **all** writers, including other investigations sharing the monthly journal. Confirm worker termination. Do not take independent live copies of related databases while calls can occur between snapshots.
2. Use SQLite's backup API for each database after quiescence. Copying only a live `.sqlite3` file can omit committed WAL contents; deleting WAL/SHM files is not recovery.
3. Copy the corresponding index and private profile/review metadata. Record each file's SHA-256 and identify the selected configuration, source/corpus revisions and backup time. Keep the original set unchanged.
4. Run `PRAGMA integrity_check` and `PRAGMA foreign_key_check` on each copied database; verify inventory, schema support, job/attempt/artifact identities and ledger contents. Hashes detect changed bytes, not whether an old snapshot is current.
5. Restore into a new private directory while dispatch remains disabled. Rebind only filesystem paths required for the relocated set; retain investigation IDs, submission keys, source/review identities and configuration. Do not overwrite the original set.
6. Establish that the monthly journal is the latest complete record for **all** its consumers. Reconcile later calls and initial/account spend separately. An older job backup must not roll back the latest journal, and an older journal must never be silently installed as current. If freshness/completeness is unknown, stop: the current trusted-filesystem design cannot detect every administrator-supplied rollback. No paid restart is authorized by this procedure.
7. Reopen and inspect through the supported CLI. Verify original evidence, pending/completed status, call/token/deadline state and reserved/charged amounts; revoked sources or support decisions must still deny protected delivery. A successful `integrity_check` alone is insufficient.

## Reproduce the synthetic checks

Run the assembled regressions without credentials or paid opt-in:

```sh
uv run --locked python -m unittest tests.integration.test_local_recovery -v
```

The harness SIGKILLs an explicitly scripted CLI at seven boundaries: before/after evidence retention, before/after durable model dispatch, before/inside/after atomic publication. It uses real SQLite and monthly journals, then starts fresh CLI processes with the same submission identity. The 40-call path publishes review-required proposals; fictional review ports are not human judgments. A separate negative regression confirms that the current fully reviewed scripted path exhausts 40 calls before accepted publication and leaves no partial accepted artifact. Existing accepted-publication regressions use their explicitly larger test policy. This is a known bound for future accepted-path design, not an increase of the owner-approved ceiling or proof that accepted publication works within 40 calls.

For a separately inspectable scratch fixture, choose fresh paths. This standalone seam inherits the original development fixture’s demonstration policy and fictional review configuration; the automated regression explicitly overrides it to 40 calls and review-required delivery. Neither authorizes a paid run:

```sh
uv run --locked python -m scripts.local_recovery_fixture --directory /tmp/trace-recovery-demo --point after_dispatch --marker /tmp/trace-recovery-demo.marker
```

The command intentionally dies with SIGKILL (shell status 137); the marker confirms the selected boundary. Do not treat this as an ordinary successful CLI exit. The directory contains synthetic private `evidence.sqlite3`, `corpus.sqlite3`, `provider.sqlite3`, `index/` and `profile.json`. No real provider request is made. The following illustrates the backup API for one member; repeat for every database only after the entire set is quiescent:

```sh
uv run --locked python - <<'PY'
import os
import sqlite3
from pathlib import Path
source = Path('/tmp/trace-recovery-demo/evidence.sqlite3')
backup = Path('/tmp/trace-recovery-demo-backup')
backup.mkdir(mode=0o700)
with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as src:
    target = backup / source.name
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    os.close(fd)
    with sqlite3.connect(target) as dst:
        src.backup(dst)
        assert dst.execute('PRAGMA integrity_check').fetchone() == ('ok',)
        assert not dst.execute('PRAGMA foreign_key_check').fetchall()
PY
```

This one-file illustration is **not** a complete backup set. The regression performs the complete three-database/index/profile relocation, compares the durable ledgers exactly, refuses another reservation for the uncertain scope, and rechecks source revocation after restored report inspection. It also tests competing process claims and incompatible, corrupt and incomplete state through the actual CLI. Existing execution/workflow/tool regressions cover supported upgrades, stale/cancelled publication, original deadlines, unknown usage and worker termination/reaping.

## Retention and deletion

The owner selected a 30-day Local MVP planning expectation; it does not implement automatic cleanup or authorize retention of real operational data. `delete_terminal` removes a terminal investigation's evidence/job/attempt/execution/artifact state with a metadata-only audit. It does not erase exports, indexes, filesystem snapshots or backups, and it must not be used to release monetary reservations. Keep the monthly provider journal separately: multiple investigations share its cap and unresolved outcomes must survive job cleanup. Deleting or replacing that journal is not a supported budget reset.

Track backup/export copies and their access and deletion responsibility. Restrict or retire restored credentials/source bindings as required by their owner; never treat copied grants or frozen reports as standing authorization. Missing cleanup ownership and any real-source retention/reconciliation policy remain explicit acceptance inputs.

[Operations](README.md) · [SQLite contract](../architecture/sqlite-investigation-store.md) · [Execution policy](../architecture/investigation-budgets.md)

[Recorded local verification](../../evaluation/reports/local_recovery_v1/README.md) preserves the validation history and known bounds.
