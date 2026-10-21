# Local MVP security verification

This matrix covers the trusted local CLI/application, real SQLite protected artifacts, read-only tool workers and explicit scripted provider seams. It is S6 local-readiness evidence for #67, not authenticated operational source ownership, multitenant isolation, actual-model prompt-injection resistance or release acceptance. Actual Azure diagnostic measurement and owner quality review remain S7 work. No paid calls, real secrets or final-test labels are needed.

## Checks and authority boundaries

| Boundary | Assembled negative/positive checks | Verification sources |
| --- | --- | --- |
| Independent grants and caller filters | Saved delivery denies wrong principal/audience, evidence service scope, independent corpus scope/service/applicability and changed environment. Caller windows cannot widen captured scope. Artifact/citation paths and IDs confer no access; insecure profiles fail closed. | [CLI tests](../../tests/integration/test_investigator_cli.py), [tool tests](../../tests/integration/test_tools.py) |
| Current source and transmission rights | Initial admission, later tool results, refinement, correction and retained history recheck current source and transmission rights independently. Real SQLite refinement/correction probes revoke each right after the first model call and permit no second model invocation or publication. | [Security dispatch tests](../../tests/integration/test_local_security.py), [provider contracts](../../tests/contracts/test_provider_policy.py), [workflow contracts](../../tests/contracts/test_workflow.py), [provider process tests](../../tests/integration/test_provider_policy.py) |
| Fixed tools and transitions | Synthetic log instructions request evaluator-file reads, shell/SQL writes and remediation; actual tool calls stay in the fixed read-only catalog. A model-proposed shell tool fails schema validation without execution. Unknown tools, arbitrary arguments/windows and cross-scope citations are rejected rather than converted into grants. | [Canary tests](../../tests/integration/test_local_security.py), [workflow contracts](../../tests/contracts/test_workflow.py), [tools](../../tests/integration/test_tools.py) |
| Input-derived sensitivity and current protected delivery | A synthetic credential excerpt is removed before model dispatch while citation mappings and restricted sensitivity survive. Narrower audience, denied export, changed source revision/withdrawal and revoked support deny saved delivery. A full captured timeline is distinct from admitted model citations. | [Security canaries](../../tests/integration/test_local_security.py), [saved CLI](../../tests/integration/test_investigator_cli.py), [restored support](../../tests/integration/test_local_recovery.py) |
| Evaluator isolation | Generated evaluator-only files represent labels, fixture reports, manifests, reviews and reserved data. Instructions can name their paths, but contents do not enter model requests, tool results or delivered reports. The harness observes forbidden parent-process opens/imports; runtime tool results and exports are separately checked. Ingestion rejects evaluator-role/answer-bearing knowledge and forbidden source metadata. No actual held-out labels are opened. | [Fault harness](../../scripts/local_security_fixture.py), [canary tests](../../tests/integration/test_local_security.py), [corpus rejection](../../tests/integration/test_corpus.py), [ingestion](../../tests/integration/test_sqlite_store.py) |
| Logs, exceptions and files | Correlated JSON logs exclude synthetic credential values, evaluator canaries, injected source instructions and report prose. A hostile backend exception fails without disclosing its value. Provider provenance/redaction tables contain no removed value. Private config/databases/journals/probe files use 0600 under 0700 fixture roots. | [Canary/disclosure tests](../../tests/integration/test_local_security.py), [provider tests](../../tests/integration/test_provider_policy.py) |
| Installed runtime | Wheel namespace restrictions and isolated installed imports exclude evaluator/tests/scripts. Runtime archive bytes must not contain the synthetic isolation/credential sentinels. Installed entry points and actual tool worker are exercised outside the checkout. | [Installed-wheel gate](../../scripts/check_package.py), [architecture gate](../../scripts/check_architecture.py) |

## Reproduce

```sh
uv run --locked python -m unittest tests.integration.test_local_security -v
uv run --locked python -m unittest tests.integration.test_investigator_cli -v
make check lint format-check type-check architecture-check test integration package-check
```

The dedicated script runs only explicit development probes, outside the runtime wheel. Use a fresh private path:

```sh
uv run --locked python -m scripts.local_security_fixture --directory /tmp/trace-local-security-injection --mode injection
```

Other modes are `redaction`, `hostile_error` and `model_tool`. `security.json` retains content-free probe flags/tool names and correlated CLI logs; the normal harness retains controlled synthetic observed input, result and execution artifacts. Original synthetic input can include a credential canary in private `observed.json`/retained untrusted evidence; that is intentionally distinct from model context, public report export and content-free logs/audit. Never replace the synthetic string with a real credential or treat a private source artifact as a safe public export.

A negative control deliberately injects a canary at the backend-result observation boundary. The probe must fail even when normal application error handling catches and withholds the result; persistent violation flags prevent that denial from masking a detected leak. This control tests the instrumentation and does not count as successful application disclosure.

The four canary probes use a 40-call ceiling and review-required proposals. They change no owner setting and create no human support judgments. Refinement/correction authority probes reuse the existing larger demonstration policy to isolate fresh-permission behavior. They do not establish that refinement or accepted publication fits 40; #66's measured accepted-path bound remains explicit.

## Residual limits and gate interpretation

Any unexpected source/model/export/canary disclosure, unauthorized tool dispatch, authority widening, evaluator import or loss of sensitivity is a critical local regression and blocks S6 readiness. An expected denial is passing mechanical evidence; it is not diagnostic quality or a successful investigation. Missing/unknown usage remains explicit, never fabricated as zero.

The Python audit hook instruments the probe parent; it is not an OS sandbox or proof of every possible child filesystem access. Worker-result checks, source validation, fixed tool contracts, architecture checks and installed-wheel isolation supply separate evidence. Scripted models establish deterministic boundary behavior, not resistance by a real model. Pattern scanners cannot establish that arbitrary prose is free of secrets/labels; reviewed field/source classification remains mandatory.

Direct trusted filesystem/composition access can alter grants, data or backups. Local file ownership is not authentication or tenant isolation. Permissions cannot retroactively erase an authorized copy or cancel a remote request already dispatched. Operational identity/grant derivation, real-source processing/retention/deletion, shared cloud admission, native pod identity and independent Operational Pilot acceptance remain gated separately.

[Security guide](README.md) · [Provider contract](../architecture/model-provider.md) · [Local recovery](../operations/local-recovery.md)

[Recorded verification](../../evaluation/reports/local_security_v1/README.md) preserves the complete/focused check counts, pinned sources and canary-control finding.
