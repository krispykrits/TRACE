# Local recovery verification

Recorded 2026-10-16 (America/New_York) for [#66](https://github.com/krispykrits/TRACE/issues/66), at implementation checkout `284dd7e11ed843fc6abaf6438116fc4c66601613`. [checks.json](checks.json) records source hashes, exact validation outcomes and limitations. No external provider calls or actual human support judgments were made.

## Evidence

| Requirement | Observed coverage |
| --- | --- |
| Process interruption and atomic publication | Seven actual SIGKILL boundaries around retention, durable model dispatch and atomic publication; partial publication rolls back; committed review-required output survives |
| Duplicate/concurrent execution | Same-key fresh CLI processes leave all calls, token state and monthly records unchanged; two competing processes create one claimed attempt |
| Expiry and uncertain replay | Recovery after the persisted lease preserves original execution accounting; restored in-flight monthly reservation refuses a new request for the same investigation |
| Consistent restore | Quiescent SQLite backup of jobs/execution/artifacts, corpus and spending state, with corresponding index/profile relocation; original evidence/report/citation/review identities retained |
| Restored authority | Revoked source blocks restored review-required output; copied fictional support permits accepted inspection until support is revoked, then delivery is denied |
| Schema/corruption | Actual CLI refuses newer, corrupt and incomplete state with empty stdout/content-free errors and no destructive repair; existing migration regressions preserve old jobs/reservations |
| Cancellation/deadline/cleanup | Existing execution/workflow/tool regressions cover cancellation, stale publication, original deadlines, unknown usage and actual worker termination/reaping |

The full required command ran 46 unit, 119 contract and 212 integration cases. Integration passed 211 and failed one **test assumption**: the CLI lease is deadline plus five seconds, rather than the hard-coded 120 seconds. The corrected regression derives expiry from the stored lease; all seven recovery cases passed on focused rerun. A subsequently added accepted-report restore case passed separately. Across those runs, all 213 current integration cases have passing results. This is not a claim that the original full invocation returned success. Fast gates and installed-wheel/entry-point/workflow/evaluator-exclusion checks passed separately.

## Reproduction and limits

```sh
uv run --locked python -m unittest tests.integration.test_local_recovery -v
make check lint format-check type-check architecture-check test integration package-check
```

Use the recorded checkout for this evidence; timings may differ. The 40-call readiness probes publish review-required proposals. A separate expected-denial test confirms the fully reviewed scripted path exhausts 40 without accepted publication. The accepted-restore test uses the original larger demonstration policy solely to check copying and fresh support revocation. No owner setting or quality threshold changed.

These are local synthetic mechanical checks, not live diagnostic quality, operational backup acceptance, paid-replay authorization or hosted recovery. An operator must stop all writers, retain the latest complete shared monthly journal and reconcile uncertain outcomes before any separately approved dispatch. Arbitrary administrator-supplied rollback is outside automatic detection in the trusted-filesystem composition. The [runbook](../../../docs/operations/local-recovery.md) owns procedure, ownership and deletion/retention boundaries.

[Recovery tests](../../../tests/integration/test_local_recovery.py) · [Fault harness](../../../scripts/local_recovery_fixture.py)
