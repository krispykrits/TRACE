# Shared investigation execution limits and usage records

Scoped enabler [#36](https://github.com/krispykrits/TRACE/issues/36), merged in [PR #53](https://github.com/krispykrits/TRACE/pull/53), following merged PR #52 / accepted #35. [ADR 0014](../adr/0014-durable-investigation-budgets.md) records the accepted Local MVP durable admission decision. This supplies bounded model/tool interfaces for #37; an investigator loop, production mutation and operational source authority are outside this change.

## Configuration and composition

Create one `bootstrap.create_execution_session(evidence_db=..., identity=..., policy=..., pricing=..., clock=...)` after the SQLite job is claimed. `ExecutionIdentity` requires the investigation ID, actual durable attempt ID, correlation ID and independently trusted access scope. Pass the same object as `execution=` to `create_tool_session` and `create_azure_model_provider` (or the explicit file-loading variant). Use that tool session for gathering and subsequent citation validation. Execution identity supplies no evidence/transmission grants; the provider's independent source authority and protected-response checks still run before each request/history/correction.

The database must exist privately and hold a current running job under the supplied scope/attempt. Schema 2 adds `execution_runs` and `execution_calls`; writable `SQLiteInvestigationStore` startup upgrades schema 1 transactionally before read-only tool workers open it. Policy and pricing are pinned per investigation. Restart cannot reset counts, elapsed time or pending reservations. Changing the scope, policy or pricing fails closed. A stale worker cannot poison a newer active worker's budget.

`ExecutionPolicy` rejects booleans, null/unbounded/negative/excessive limits and unsafe configuration IDs before execution:

| Setting | Finite default | Supported ceiling |
| --- | ---: | ---: |
| `deadline_ms` | 120,000 | 600,000 |
| `max_model_calls` / `max_tool_calls` | 3 / 20 | 100 each |
| `max_retries` / `max_corrections` | 0 / 0 | 10 each |
| `model_timeout_ms` / `tool_timeout_ms` | 30,000 / 5,000 | 600,000 / 10,000 |
| `max_input_tokens` / `max_output_tokens` per model call | 10,000 / 1,024 | 263,168 / 100,000 |
| `max_total_tokens` | 40,000 | 10,000,000 |
| `max_model_response_bytes` / `max_tool_result_bytes` | 65,536 each | 1,000,000 each |

These defaults are implementation safety controls, not owner latency/quality targets or an additional financial commitment. Tool results require at least 512 bytes. Caller-supplied per-call model bounds and the existing tool policy can narrow the shared ceilings. Native response bytes/output tokens and tool worker timeouts are clipped outside the prompt, including remaining investigation and lease time. The original shared deadline starts at the first composed session; per-call and execution durations include preparation/idle time, and end-to-end duration also includes queue wait from the durable submission time.

Use the existing monthly journal with the owner's explicit spending allowance (at most $20/month), known prior-spending seed and shared journal path. The Azure factory requires its existing versioned ceiling-price snapshot to match the execution session; no new monetary limit or zero prior-spend assumption is inferred. Standalone explicitly authorized connector diagnostics continue to use their existing per-call/monthly bounds; they do not start an investigator workflow. #37 must use the composed session for every investigation step.

## Admission, cancellation and failure

The atomic ledger checks the current durable job, active attempt, lease/expiry and shared state at admission, reservation, dispatch and completion. It persists the counters/ticket and audit record together. Only one call can be active across model and tool sessions; repeated dispatch of the same ticket is rejected. Invalid arguments and denied/exhausted attempts are recorded. After budget exhaustion, cancellation, expiry, explicit terminal completion/failure or an unresolved dispatched model outcome, no new model or tool call starts.

Cancellation before dispatch releases the local token reservation and the spending journal refunds its allowance. Cancellation during a call withholds its later result and retains available usage/charges; it may wait until the finite local worker deadline. Killing a worker or withholding a late result does not prove the provider stopped processing or charging. UTC clock rollback/nonfinite time fails closed; transport workers retain monotonic deadline enforcement. Current source rights/revisions are checked independently by the existing provider/tool contracts.

There is no automatic retry or correction. A trusted workflow must mark `ProviderCall.purpose` / `ToolSession.invoke(..., purpose=...)` as `retry` or `correction`. Repeating the same port after failure requires an explicit purpose; retry/correction requests consume their quota and the normal call/token allowance. Retries are eligible only for rate-limit/dependency failures; model corrections follow a received response or malformed/output-limited response. The workflow is responsible for labeling the purpose truthfully; the boundary cannot infer semantic intent from two different successful prompts. A timeout, unknown dispatched dependency/audit failure or crashed pending ticket blocks replay even when retry quotas remain. No reconciliation/reset endpoint or successful assessment is invented.

`budget_exhausted`, `cancelled`, `expired`, `timeout`, `execution_stopped`, `rate_limit`, provider errors and `audit_unavailable` are fixed actionable outcomes. Inspect the correlated record, fix configuration/authorization/quota or reconcile the unresolved attempt before starting fresh authorized work. A late/failed execution cannot become completed abstention. `ExecutionSession.stop()` closes the budget; #37 remains responsible for actual job transitions and separate assessment status.

## Usage, reservations and estimates

Before dispatch, reserve the actual admitted UTF-8 instruction/context byte count plus 1,024 tokens for framing, and the native output-token cap. Byte count is a conservative input allowance for this text-only contract, not a tokenizer measurement or a provider input-token control. Returned `input_tokens` and `output_tokens` remain numeric; credential tokens remain redacted. Availability is `available`, `partial` or `unavailable` with null missing dimensions. Known zero is zero.

Reported dimensions replace their token allowances; unknown dimensions retain their allowance. Failed and explicit retried/corrected calls remain accounted for separately. A known completed response with missing usage may continue within the remaining reserved allowance; an uncertain outcome cannot. Usage above a reserved/per-call bound is retained as actual reported usage, exhausts execution and withholds the result. Reservation estimates cannot guarantee Azure billing never exceeds the allowance: remote processing after timeout, model/tokenization differences, external calls, changed prices/taxes and deleting/switching ledgers remain outside this local guard.

`ModelPricing` contains an explicit safe version plus positive integer input/output rates in nanodollars per token. Each complete provider-reported usage pair yields `estimated_cost_nusd`; either missing dimension leaves it null. `reserved_or_estimated_charge_nusd` is the local reservation/estimate, not an invoice. Records carry `currency=USD`, `cost_kind=estimate`, `usage_basis=provider_reported` and `pricing_version`. Cached-input discounts are omitted from the existing conservative Azure snapshot. Price/version changes require an explicit reviewed configuration change and cannot reset an existing run's accounting.

The job ledger and monthly provider journal use the same call/request ID and pricing snapshot. They commit independently. Crash windows preserve a pending ticket/reservation and block automatic continuation, including a crash after the spending journal completes but before the execution ledger finishes. Known no-dispatch failures refund; uncertainty retains allowances. There is no exactly-once billing claim.

## Content-free audit

`execution.call` logs and private `execution_calls.metadata` retain investigation/durable attempt/correlation/call IDs, policy/configuration versions, kind/purpose, approved evidence IDs, model configuration, prompt/tool versions, nullable reported model/operation ID, outcome/dispatched state, per-call/execution/end-to-end duration, counts, token allowance/charge, usage availability and price/currency/estimate basis. Admission/reservation/dispatch phases update one final durable call record. Configured model/version/deployment remains separate from what the provider reports; a bare model name does not verify the owner-reported dated version.

No prompt, response, tool argument/result body, evidence excerpt, evaluator answer or removed redaction value is written. Sensitive provider operation/model identifiers are withheld while numeric usage survives. Redaction provenance stays in the existing private provider journal. Audit failure releases no result. Direct filesystem/application-composition access remains trusted; operational identity, credential/audit retention/deletion and hosted Azure Monitor acceptance are separate gates. Terminal synthetic-job deletion cascades its execution records; the monthly ledger remains independent so spending reservations are not erased by deleting a job.

## Deterministic demonstration and verification

Run the fake-adapter/injected-clock demonstration and actual SQLite state/journal cases:

```sh
uv run --locked python -m unittest tests.unit.test_execution_policy tests.contracts.test_execution tests.integration.test_execution -v
make check lint format-check type-check architecture-check test integration package-check
```

`test_shared_counts_are_durable_and_exhaustion_stops_both_ports` gathers once, receives one response, exhausts the model quota and confirms neither port dispatches again. `test_late_model_reply_is_accounted_and_never_released_or_retried` advances an injected clock, withholds the response and inspects retained token/cost/correlation records. Unknown/partial/zero usage, retries/corrections, sensitive identifier/log redaction, authorization/cancellation/lease revocation and persistence/concurrency/schema migration have independent assertions. The integration cases use actual SQLite, a real read-only tool worker and a fake admitted provider; no network, credentials or paid call is used. Earlier #34's synthetic Azure check remains separate evidence, and no new live check or operational acceptance is claimed.

Local verification on 2026-10-14 passed all required syntax/lint/format/type/import/test/installed-wheel gates with 288 tests (44 unit, 78 contract, 166 integration). No paid call was performed. Owner merge accepts this scoped enabler; #37 workflow and the release/operational gates remain separate.

#37 integrates this session into the [bounded investigator](bounded-investigator.md), including reference validation, optional check/refinement and explicit correction. Each port retains its own last outcome so citation reads cannot disguise a retry or invalidate an eligible correction. Existing execution-state JSON gains those fields conservatively without resetting counts/reservations or granting unknown historical retry eligibility.

## Cloud hosting follow-up — 2026-10-14

[ADR 0015](../adr/0015-azure-aks-cloud-deployment.md) / #57 require shared PostgreSQL job/attempt and provider/execution monetary admission across AKS pods. The local serialized SQLite implementation does not establish distributed clock/lease/transaction safety. Test simultaneous admission, replacement pods, stale attempts and unknown in-flight outcomes before concurrent cloud paid dispatch; preserve current-job checks, protected audit and the independent monthly cap across job deletion. #58/#60 own actual cloud execution and recovery acceptance.
