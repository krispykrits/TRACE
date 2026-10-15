# ADR 0019: Local CLI and current-authority saved report access

- Status: Accepted for the scoped local implementation by #38 / [PR #82](https://github.com/krispykrits/TRACE/pull/82) merge on 2026-10-15; operational gates remain separate
- Date: 2026-10-15
- Scope: Local MVP CLI over existing development/test captures; no operational authentication or new source ingestion

## Context

The bounded investigator saves private evidence and protected assessments, but its in-memory response handle cannot survive process exit. Scope-only restoration would lose original input sensitivity, source/revision/transmission checks and current independent support. A repeat CLI command must not replay an uncertain paid attempt. The local job/provider contracts currently reject production captures.

## Decision

Keep one modular application. Core `local_service` owns normalized request/idempotency and explicit command orchestration; `reports` owns saved disclosure through a private reader port. Bootstrap composes SQLite and owner-managed local JSON/source/review adapters. The CLI only parses, renders and exports already authorized application results. No network service, arbitrary-module provider or caller-selected grant flags are introduced.

Factor original dependency validation into `SourceAccessPolicy` shared with `PolicyModelProvider`. Persist original actor/investigation, selected source/revision/field fingerprints, original sensitivity and support binding IDs privately at publication. Retained evidence receives a separate binding for its contributing package. Restoration checks current independently resolved originals and reviewed owner grants, source/corpus/profile retention, actor/clearance and independent support. Missing historical bindings deny content. Display/export never creates new tools/model calls.

Owner-managed mode-0600 local profiles are the trusted composition boundary, separate from query filters. Direct filesystem/composition access is trusted, consistent with current Local MVP. JSON stdout/file output additionally requires current transmission/source-owner permission; summary/redaction cannot widen clearance. Export returns admitted sanitized views; retained evidence inspection exposes provenance/timeline rather than raw unreviewed payloads. Unknown/secret/evaluator sensitivity is denied. A stored outcome is not a grant or current support decision.

Use a stable scoped submission identity for normalized service/environment/window, independent of provider choice; one attempt, targeted atomic claim and no automatic paid rerun. SIGINT/SIGTERM preserve durable cancellation and already retained records. A hard-killed/uncertain attempt stays blocked from replay and requires separate reconciliation. Development fixture providers/reviews stay in scripts/tests and require explicit trusted harness injection, with simulation metadata. Live Azure requires explicit selection and paid opt-in plus existing budget/policy controls.

## Alternatives

- Scope-only stored-body reads: rejected because scope cannot restore current input-derived permissions.
- Automatically reconstruct provider clients/paid sessions during report reads: rejected because inspection needs no credential, transport or dispatch authority.
- Caller flags for grants or plugin/module paths: rejected because filters would become authority and normal calls could silently use fakes.
- Add operational identity/UI/service now: deferred to separately scoped work; local file ownership does not establish operational authentication.
- Automatically rerun expired/failed requests: rejected because provider outcome/charges may be unknown.

## Consequences and revisit conditions

No dependency or database version is added. Old unbound artifacts fail closed, preserving their bytes. Current sources and trusted support records must remain available; authorized exports cannot be recalled. Manual trusted support records are persisted/rechecked but this scope does not add reviewer authentication or saved-result promotion. Source/retention/reviewer/remote-audience identity, distributed access/deletion and shared admission must be revisited before real-source, cloud or operational acceptance. Change the capture source adapter through #73 rather than treating real telemetry as synthetic. CLI simulation checks establish orchestration and disclosure behavior only; actual-output scoring and release gates remain #39/S6.

## Validation

Required deterministic checks and process cases are recorded in the implementation PR. The [CLI contract](../architecture/investigator-cli.md) documents reproduction, profile/source grants, exit behavior and unrun live work.
