# Local MVP security verification

Recorded 2026-10-16 (America/New_York) for [#67](https://github.com/krispykrits/TRACE/issues/67). Final implementation checkout: `a64497b960083cbd4cbcae52fbed12ac240f65d3`. [checks.json](checks.json) records source hashes, exact validation counts, observed properties and limitations. No paid provider calls, actual human support judgments or actual final-test labels were used.

## Validation

The full required command passed: **46 unit, 119 contract and 220 integration tests**, plus compile, lint/formatting, typing, architecture and installed-wheel/entry-point/workflow/evaluator-exclusion checks. Full integration took 965.648 seconds. This also revalidated #66's corrected lease-expiry and accepted-restore checks in a successful complete run; the original recovery receipt remains unchanged.

The full discovery began at `994213f58c311f2e12bd6adba1c48debb6530f6f`. After its original canary cases ran, the harness was hardened to retain a violation flag even if application error handling catches the observer exception. Its four canary tests passed a focused rerun (49.799 seconds), and the added negative control passed separately (1.729 seconds). Fast gates passed again. The new control is not included in the full discovery's 220 count; all 221 current integration cases have passing results across these runs. There was no runtime core behavior change.

```sh
make check lint format-check type-check architecture-check test integration package-check
uv run --locked python -m unittest tests.integration.test_local_security -v
```

Use the recorded checkout for this evidence. Fresh fixture paths are required; timings may differ. The [security matrix](../../../docs/security/local-mvp-matrix.md) maps each boundary to the exact CLI/provider/tool/corpus/wheel checks. The [probe harness](../../../scripts/local_security_fixture.py) remains outside the installed application.

## Findings and limits

Generated evaluator-only label/report/manifest/review/reserved-file contents did not enter observed model requests, tool results or delivered reports; parent open/import probes stayed clear. Known synthetic credentials were removed before model dispatch, while citations and restricted sensitivity survived. Correlated logs/provider audit excluded removed values and raw injected/report prose. Private config/databases/journals/probe files remained 0600 under 0700 fixture roots. Hostile backend exceptions and model-proposed shell tools failed without disclosure or execution. Current source/transmission revocation stopped refinement/correction after one model invocation; independent scope/applicability/ID/path checks denied protected saved delivery.

The harness defect was in verification tooling: a caught observer exception could be mistaken for an expected application denial. Persistent violation tracking and a deliberate negative control now make that probe fail. Corrected development test expectations use the actual `knowledge.resolve` catalog name and distinguish incident applicability from the current freshness clock. Runtime controls required no fixes.

The canary paths use the unchanged 40-call ceiling and review-required proposals. Refinement/correction probes reuse the existing larger demonstration policy to isolate current-rights checks; they do not prove those paths fit 40. Fully reviewed scripted publication still exhausts 40. The owner retained 40 for S6; accepted-path measurement remains before S7.

Python audit hooks instrument the parent, not a complete child filesystem/OS sandbox. Scripted models cannot establish real-model resistance or diagnostic quality. Trusted filesystem/composition does not authenticate an operational owner or tenant, supply real-source retention rights, erase prior authorized copies, cancel remote charges or accept the independent Operational Pilot. Any unexpected critical disclosure/authority regression still blocks S6 readiness.

[Security tests](../../../tests/integration/test_local_security.py) · [Saved CLI checks](../../../tests/integration/test_investigator_cli.py) · [Security guide](../../../docs/security/README.md)
