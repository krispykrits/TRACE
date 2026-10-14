# ADR 0012: Model provider, Azure connector and deterministic admission

- **Status:** Accepted for the Local MVP synthetic provider workflow after owner merge of [PR #51](https://github.com/krispykrits/TRACE/pull/51) and closure of #34; operational source/identity/retention gates remain separate
- **Date:** 2026-10-13 (America/New_York)
- **Owner:** Project owner
- **Scope:** #34 / implementation subtask #50; one read-only model call and per-request provider policy, not the investigation workflow or Operational Pilot

## Context and owner decisions

Sprint 4 #19 / PR #49 is accepted/merged. The owner selected Azure AI Foundry, GPT-6 Luna, deployment `gpt-6-luna`, a $20/month model cap, and supplied resource configuration privately. Following Entra error 53003, the owner explicitly selected a resource API key; credentials remain in a separate private local file. No automatic authentication fallback or tenant-policy change is authorized. The owner approved the category-based transmission policy and five mandatory per-request controls in the [provider guide](../architecture/model-provider.md), identified as `trace-provider-data-policy.v1`. Access alone does not grant Azure transmission permission; operational sources remain unapproved.

Core investigation needs explicit provider identity, usage absence, safe failures and enforced bounds without vendor/source authority. Raw requests and initial-only redaction would permit later tool results/history to bypass the owner's policy. The model cap requires a conservative admission reservation before even synthetic live checks.

## Decision

Keep provider-neutral contracts in `investigation.provider`; put reference-based admission, independent source-authority/journal ports and protected response handles in `investigation.provider_policy`. Bootstrap alone composes an independent source authority, trusted scope, registered prompt catalog, guard, process adapter, Azure transport and private journal. Missing grants/classification/audit/budget reject before dispatch. Preserve citation IDs and source revisions with local value-free redaction provenance. Recheck current dependencies immediately before dispatch and on response reads/exports/reuse. Generated responses retain the most sensitive original input classification; no automatic declassification exists.

Bind prepared request bytes, policy/scope/evidence/sensitivity and bounds to a short-lived private HMAC receipt. The process and transport require this receipt; source text cannot mint it or change provider/settings. Recheck expiry after TLS connection. Trusted application composition and controlled local filesystem remain assumptions, not operator authentication, an arbitrary-Python sandbox or instantaneous distributed revocation.

Use the Azure Responses v1 REST API through standard-library verified HTTPS, not a new SDK. Read explicit mode-0600 setup/secret files; credentials appear only in auth headers. Separate configured deployment/version from the provider-reported model. Send stateless text/JSON-object requests with native output caps, no uploads/tools/history/redirects/retries, and bounded native response reads. JSON mode's required format marker is part of admitted input. A spawned process enforces the total deadline including stalled IPC, suppresses raw worker output and validates output on both sides. Errors are fixed categories plus allowlisted HTTP code/parameter metadata and nullable measured usage. Local termination does not prove remote cancellation.

Persist private SQLite provenance and content-free attempt accounting with atomic reservations shared by all instances. The versioned conservative Global Standard Luna price ceiling reserves input bytes plus framing and native output cap, reconciles complete usage estimates and retains reservations for unknown usage. Explicit initial known spending and an allowance at most $20 are required. Pending/timeouts/uncertain dependency outcomes prevent same-scope replay. This is TRACE-local estimated spending, not an Azure invoice/account-wide cutoff; #36/#37 retain investigation budgets and recovery. No new dependency or lock change is required.

Model adapters may import only provider/policy contracts and runtime within TRACE, not sources/tools/storage access. Network execution belongs to adapters; core URL parsing remains permitted. Update ADR 0010, package guide, checker/negative cases and wheel verification together. Fakes, synthetic authorities and live test instructions remain test-only and outside the wheel.

## Alternatives and tradeoffs

An Azure/OpenAI SDK would add dependencies, credential/retry defaults and response logging paths; the narrow selected text contract is supported by bounded standard-library REST. Revisit an SDK only for a demonstrated capability need. A raw-string application interface or caller-supplied permission object cannot enforce independent source permission; use references resolved by the trusted authority. Pattern-only redaction misses unlabelled sensitive prose, so reviewed source classifications are mandatory and unknowns rejected. Evidence-controlled prompts/grants are unsafe; registered templates and isolated untrusted data preserve authority.

Threads cannot terminate stalled synchronous calls. Processes add startup/serialization cost but enforce local deadlines and suppress raw dependency failures. A separate policy service or general framework would exceed current scope; the current core rules and adapter ports protect a concrete boundary. A fixed private SQLite journal fits local execution; authenticated multi-host/database audit ownership and retention remain production gates. Estimates deliberately exceed discounted billing; unknown results are conservative and may require manual reconciliation.

## Verification and revisit conditions

Deterministic contracts cover missing/denied/revoked transmission/access, internal-owner permission, unreviewed/evaluator/customer/employee rejection, secret/PII/quoted-cookie redaction, bounded later selections/history, preserved citations/value-free provenance, protected output reads/exports and forged/expired/tampered requests. Actual process/SQLite integration checks cover native payloads, safe failures, usage, concurrency-safe reservations, uncertain replay and private files. Architecture negatives and installed-wheel tests protect source/evaluator/SDK separation.

The separately opted-in **actual TRACE synthetic live check passed on 2026-10-13**, with valid JSON/citation, 143 input / 90 output tokens and 2,400 ms. Three prior configuration rejections remain accounted for with unknown-usage reservations; no automatic retries occurred. The reported model lacks a dated version, which remains owner-reported. The guide records bounds, metadata-only artifacts and reproduction. All required local code gates must pass before PR handoff; owner merge/#34 closure accepts the Local MVP provider scope; operational identity/source/processing/retention and pilot gates remain separate.

Revisit for changed model/pricing/deployment/auth requirements, measured process overhead, streaming need, real-source authenticated grant derivation, multi-host accounting or response persistence/export. #35 owns assessment support; #36 investigation-wide budgets; #37 workflow/recovery; #38 inspection/export. No diagnostic-quality, cloud, pilot or remediation acceptance follows from synthetic provider checks.
