# ADR 0014: Durable shared investigation budgets

- **Status:** Proposed in #36 / [PR #53](https://github.com/krispykrits/TRACE/pull/53) for owner review
- **Date:** 2026-10-14 (America/New_York)
- **Scope:** Local MVP read-only execution enabler; workflow integration remains #37

## Context

PR #52 is merged and #35 is Project Done. Current tool sessions enforce finite read-only limits; the Azure provider enforces per-request data policy, native output/process bounds and a private monthly reservation journal capped at the owner's $20. Those independent controls do not limit a whole investigation across both ports or survive resetting an in-memory session. #36 requires correlated execution/usage/cost evidence from the first investigator invocation, without conflating execution failure with abstention.

## Decision

Place `ExecutionPolicy`, admission/accounting rules and an atomic `ExecutionLedger` port in `investigation.execution`. Bootstrap selects `adapters/storage/sqlite/execution` against the existing private investigation database. The adapter revalidates trusted access scope, current durable job/attempt, lease and expiry inside the same transaction that updates the shared counters, active ticket and content-free call record. A stale attempt cannot change the current worker's budget. Model transports cannot import execution state or acquire tool/source handles; the existing architecture negatives and installed-wheel gate enforce that placement.

Pin the complete finite policy and versioned pricing snapshot to one investigation. Reopening uses the original start/deadline, counters and reservations; a changed configuration/pricing snapshot cannot silently reset them. Schema 2 adds execution tables transactionally to schema 1 without altering jobs/evidence. No new dependency or broker is introduced.

Both `PolicyModelProvider` and `ToolSession` accept the same composed session. Admission counts requests, including invalid/denied requests, and serializes dispatch. Check current cancellation/terminal state before admission, after preparation/audit writes immediately before dispatch and after dependency completion. Clamp per-call bounds to remaining investigation and active-lease time. A late result is withheld; a local timeout is not proof of remote cancellation. A cancelled job cannot release a later result or start another call.

Reserve UTF-8 instruction/context bytes plus 1,024 framing tokens and the native output-token cap before each model dispatch. Charge reported dimensions when available; retain the corresponding allowance for missing dimensions. Actual usage above the allowance is recorded, with the result withheld and execution exhausted. Failed/retried/corrected calls remain separate attempts. Default retry/correction quotas are zero, with no automatic retry. Explicit bounded retries/corrections re-run the complete transmission policy and reserve again. Pending dispatches and uncertain model timeout/dependency/audit outcomes block all further dispatch; no automatic reconciliation or exactly-once billing claim is introduced.

Move `ModelPricing` to the provider-neutral contract while preserving the existing journal import alias. Record price version, USD nanodollars, provider-reported usage basis and `cost_kind=estimate`. Missing usage/cost remains null, distinct from known zero. The shared job ledger and existing monthly journal correlate by call ID; a failure between their transactions blocks continuation. They are separate stores, not a distributed atomic transaction or Azure account-wide cap.

## Alternatives and tradeoffs

A prompt-only budget or in-memory counters would allow indefinite/restarted calls. Extending only the monthly journal would give a model transport authority over job/tool state. A new queue, workflow engine or generic telemetry service exceeds this enabler. A narrow atomic state-update port keeps rule ownership in core and SQLite transaction/state checks in the adapter.

UTC deadlines persist across restart and include preparation and idle time. Clock rollback fails closed; real transport workers retain monotonic watchdogs. SQLite writes may wait for the bounded busy timeout, but dispatch rechecks the remaining time afterward. The filesystem, application composition and opaque metadata identities are trusted; this is not an arbitrary-Python sandbox. Retained metadata must use an eventual owner-approved access/retention policy before operational use.

## Verification and revisit conditions

Injected-clock contracts cover both ports, cancellation around reservations/dispatch/results, call/token/retry/correction exhaustion, late responses, failed/unknown/partial/zero usage, sensitive provider identifiers, content-free correlation and versioned cost. Actual SQLite checks cover schema upgrade, current durable cancellation/leases/stale workers, concurrency, restart/pending reservations and both journals. No paid model call is required.

#37 must compose every gather/citation/model/correction step with the same session and map these outcomes into durable workflow transitions; a failed execution remains separate from a completed abstaining assessment. #38 supplies scoped inspection/review persistence. Revisit atomicity/clock/recovery for Cloud MVP PostgreSQL workers, authenticated operational source/reviewer ownership and retention, and measured pricing/workload changes. Synthetic checks do not establish Local MVP release, operational usefulness, hosted CloudWatch delivery or remediation acceptance.
