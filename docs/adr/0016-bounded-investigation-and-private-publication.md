# ADR 0016: Bounded investigation and private publication

- **Status:** Accepted for scoped Local MVP workflow/publication in [merged PR #62](https://github.com/krispykrits/TRACE/pull/62), 2026-10-14; operational inspection and release acceptance remain separate
- **Date:** 2026-10-14 (America/New_York)
- **Scope:** Local MVP read-only application use case; operational identity and #38 inspection remain separate

Later implementation note (2026-10-15): #38 / [ADR 0019](0019-local-cli-and-saved-report-access.md) adds trusted-local saved restoration/inspection/export with original dependency bindings and current authority/support checks. Operational authentication remains a separate gate; the original #37 scope below is preserved.

## Context

The owner merged PR #53 at `5cf913e`; #36 is closed and Project Done. Source-neutral evidence/timeline/context, controlled tools, per-request provider admission, assessment validation and durable budgets are implemented. They need one prescribed workflow, with private outcomes and no paid-call replay or model-created permissions. Valid reports without trusted human support remain proposals.

## Decision

Implement `investigation.workflow.BoundedInvestigation` and a versioned TRACE-owned prompt. Bootstrap explicitly supplies the current scoped job/attempt, one shared execution session, fixed tool session, gated provider, independent current evidence authority and support reader. No source authority, model or reviewer defaults. Validate the stored subject service/environment/window against the trusted context before gathering. Caller filters and model/source text cannot grant permissions.

Use fixed phases: gathering → model → optional checking/regathering/refining → validating → optional correcting/validating → publishing. At most one read-only check and one configured correction are permitted, with no automatic retries. Every model request passes the complete #34 gate, including retained response dependencies and newly retrieved results. All investigator tool calls, reference validation and model attempts use the same #36 session; checkpoints revalidate durable ownership/cancellation/expiry between steps. Remember each port's last outcome so intervening citation reads do not prevent an explicitly bounded correction or disguise a retry.

Bound model inputs to two latest logs, one latest metric and one latest deployment, plus two retrieved passages. This is deterministic context selection, not a causal ranker or accepted quality threshold. Preserve the full observed package locally and disclose excluded IDs/gaps; retained history remains admitted and retains its original sensitivity. After a check, re-gather, reject changed observed sources, retain old knowledge mappings and bound merged whole quotes. A closed `InvestigationFrame` supplies service/window, deterministic admitted ordering, gaps and fixed phase/reason metadata. It contains no grants, free-text policy, provider selection or budget changes.

Allow explicitly selected `offline_test` composition through the same data gate. Azure remains live and cannot silently fall back. Scripted model/review implementations remain outside the runtime wheel, with truthful simulation metadata. The earlier Azure connector health check does not verify this new assessment prompt or diagnosis quality.

Schema 3 adds private `workflow_runs` and `workflow_artifacts`. Writable startup upgrades schemas 1/2 without altering jobs/evidence or budget reservations. A legacy record with prior port calls but an unknown previous outcome cannot authorize another initial/retry/correction dispatch. One workflow row per investigation prevents duplicate/restarted attempts from implicitly replaying paid steps. Retain the gathered bundle before model execution. Only a workflow-issued publication can commit a validated report/proposal, together with job/attempt completion under a fresh active lease check. Cancellation, stale ownership, expiry or publication failure cannot expose an accepted report.

An accepted supported/abstaining report records the corresponding assessment status. A completed workflow with a schema/citation-valid unreviewed proposal records `assessment_status=pending` and `outcome=review_required`; execution completion is not support acceptance. Explicit evidence-only mode also stays pending. Model/dependency/malformed/deadline/budget failure remains failed/cancelled/expired, with retained evidence and no fabricated assessment. The older coarse job review flag is not the #35 support authority.

Store necessary structured assessment/citation/provenance content with its inherited sensitivity in mode-0600 storage; keep raw prompts, malformed responses and source bodies out of telemetry. Evidence bundles retain conservative unknown sensitivity. Metadata inspection is scoped and content-free; no persisted-body getter is introduced. Live in-process delivery rechecks original scope, exact current source projections/permissions, protected response dependencies and current trusted support bindings, including a second source check after review reads. These checks resolve authorization; they do not resume investigator tool/model dispatch after terminal state. Already read dictionaries cannot be retroactively erased. #38 must enforce current source/review access and sensitivity when restoring/displaying/exporting persisted content.

## Alternatives and tradeoffs

An autonomous tool loop, workflow framework or broker exceeds this scope. Accepting unreviewed proposals as supported would bypass #35. Recording a missing provider as successful abstention would hide failure. Keeping results only in memory would lose provenance/state; exposing stored report bodies through a scope-only reader would bypass current source/review rights. The private artifact boundary defers authenticated restoration to #38 without silently weakening delivery protection.

Two latest logs and limited passages can omit useful mechanisms; explicit omissions and abstention remain required. Retry after unresolved dispatch is blocked rather than treated as exactly once. Publication and provider/budget journals commit separately; crash windows remain conservative. Local source/clock/filesystem/composition are trusted boundaries, not an arbitrary-Python sandbox. No operational source permissions, retention period or spending limit is invented.

## Verification and revisit conditions

Use fake ports/injected clocks for accepted/competing/abstaining/pending outcomes, optional check/correction gates, scope/injection/invalid-tool failures, revocation and duplicate/stale/cancelled publication. Use real SQLite/corpus/read-only workers for persistence, schema migration, protected delivery/revocation and retained evidence after model failure. Demonstrate the answerable and insufficient development incidents plus an explicit timeout with hand-authored simulation records, no actual provider/human acceptance.

Revisit context selection on measured development results, authenticated restoration/review persistence in #38, the S6 quality/baseline gate, and cloud worker recovery/operational-source identity/retention. Preserve frozen evaluator contracts/reports. No synthetic workflow success proves an Operational Pilot, hosted Azure telemetry delivery, Cloud MVP or production remediation.
