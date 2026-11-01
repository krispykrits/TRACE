# TRACE hosted implementation contract

Status: proposed design for [#55](https://github.com/krispykrits/TRACE/issues/55); no hosted service or source adapter is established by this document. Read with the [platform design](s7-platform-design.md), [model policy](model-provider.md) and [S8 handoff](../planning/s7-implementation-handoff.md). Exact field schemas, version pins and test evidence are implementation gates, not claims of existing behavior.

## Runtime boundary

TRACE builds a single versioned Python distribution with three entry points: API, persistent worker and CLI. API and worker may use the same immutable image, with distinct configuration, Kubernetes service accounts, database roles and identities. The domain owns contracts; bootstrap selects adapters. `trace-web` depends on the published API schema, not Python internals. Evaluation inputs are not installed in runtime images. Independent testbed services and the later executor never share TRACE's runtime credentials.

### API contract candidate: `/v1`

| Operation | Input and output | Required invariant |
| --- | --- | --- |
| `POST /v1/investigations` | Validated service, environment, UTC start/end, idempotency key and declared bounded options; returns investigation ID and status | Verify principal first; derive authorized scope server-side. Within `(tenant, principal, key)`, canonical equivalent requests return the same ID; a changed body returns a conflict. Create job and idempotency binding atomically; no model call in request handling. |
| `GET /v1/investigations/{id}` | State, safe failure code, attempt and timestamps | Authenticate and authorize every request; do not disclose another scope's existence. Never include protected content by default. |
| `POST /v1/investigations/{id}/cancel` | No mutation target other than the investigation; returns current cancellation state | Cancel before a queued claim; persist the request for running work; repeated calls are idempotent. Already dispatched external calls may complete and remain accounted for. |
| `GET /v1/investigations/{id}/report` | Protected assessment, citations, timeline and independent review/uncertainty fields | Recheck current access, classification, source revision and review bindings at each read/export; revoked or unavailable source is not converted into an empty success. |

Use stable versioned JSON schemas, bounded input size/depth, UTC timestamps, generated IDs and an opaque correlation ID. Proposed errors: 400 invalid input, 401 unauthenticated, 404 absent or unauthorized resource, 409 idempotency conflict, 429 rate limit, 503 unavailable dependency. Do not include provider exceptions, secrets, source text, evaluator answers or unauthorized existence in errors. Pin actual response schema/status semantics in an OpenAPI contract with client compatibility tests under #58 before implementation. Status, assessment and human review are separate; completion is not an approval of claims.

Authentication must validate token signature, issuer, audience, expiration and accepted tenant; derive a stable issuer/tenant/subject principal and access scope from a server-controlled grant source. Never trust caller-provided role, service or tenant claims without validation and authorization. Exact identity provider, app registration, tenant restrictions, grant administration, token lifetime and revocation mechanism are not verified. Initial access must fail closed when the grant source is unavailable. Use TLS for client traffic; CORS allows only the explicitly configured web origin. API keys in browser code are prohibited.

## Work dispatch and admission

| State | Entry / permitted transition | Invariant |
| --- | --- | --- |
| `queued` | Atomic submission; claim or cancel | A request can have one active attempt; expire without dispatch if deadline passes. |
| `running` | Atomic claim writes attempt ID, lease deadline and monotonically changing fencing token using database time | Worker renews only while owner, within deadline and not cancelled. All publications and state changes compare the active fence. |
| `cancel_requested` | Authorized cancellation while running | Prevent new tool/model dispatch; reconcile already dispatched calls before final accounting. |
| `completed`, `failed`, `cancelled`, `expired` | Atomic terminal state and permitted artifacts | Do not infer source completeness, model success or human endorsement from job state. Preserve structured failure and uncertainty. |
| `reconciliation_required` | Dispatch or accounting outcome unknown | Retain reservation; stop paid retries and dependent publication until a reviewed reconciliation establishes outcome. |

States are proposed hosted vocabulary; migration must map existing local states explicitly rather than silently rewriting them. A transaction claims one eligible job using a lock/atomic compare-and-set, establishes lease and creates execution state. A stale lease may permit recovery only after checking original deadline, attempt/retry limits and outstanding external operations. A lease expiry never releases a possibly dispatched monetary reservation or grants a new paid call. Persist cancellation before acknowledging it; worker observes it at every bounded tool/model admission.

Before each model call, atomically reserve maximum allowable cost against **both** shared monthly and applicable run/attempt caps, persist the call ID and verify active attempt/fence. Recheck current source and transmission rights immediately before dispatch. A single SQL transaction cannot make a network call exactly once. Record dispatch intent and state; treat crash/timeout/unknown usage as uncertain and stop without automatic paid replay. Settle actual known usage or retain conservative reservation under an explicit reconciliation. Concurrent transactions, replica restarts and clock changes must not oversubscribe the cap. The model ledger is application-scoped, not an Azure billing hard cap.

## Source adapter contract

A trusted composition supplies principal, allowed service/environment, source identity, field selection, time window, byte/result/page/deadline bounds and separate access/transmission grants. An adapter advertises supported filters; validates original IDs, revision, UTC event and collection times, units and provenance; and returns `complete`, `partial`, `empty`, `unavailable` or `denied` with safe reasons. `empty` means a successful bounded read, not timeout or denial. Continuation tokens are opaque, scoped, expiring and cannot widen a query. Duplicate IDs/revision conflicts are explicit errors.

The JSON adapter validates schema, sizes, paths, hash and evaluator isolation, importing idempotently without trusting content as a grant. The Azure Monitor adapter uses fixed parameterized queries and field allowlists, a read-only identity and independent source-owner authorization. No LLM-generated query language, credentials or unrestricted source response becomes authority. Every selected item and previously retained context is rechecked for current source revision, transmission permission and sensitivity before each call and before disclosure. Follow #73/#75; neither adapter is implemented by this design.

## Storage and migration contract

Map existing SQLite investigation/attempt IDs, request hashes, evidence/source revisions, corpus generations and index metadata, execution calls, workflow artifacts, support decisions, protected response bindings and provider reservations into versioned PostgreSQL tables. Preserve source ordering, scope and original times; use foreign keys and scope-aware uniqueness. Separate roles for migration/admin, API and worker; enforce server-side scope at each query and prove isolation rather than relying solely on filters. Vector dimensions, distance function, extension version and index generation are explicit; fail on incompatible models/indexes rather than silently regenerating different results.

Migration requires all writers stopped and a consistent latest SQLite backup set, including the shared journal and matching corpus/index. Inventory hashes, schema versions, policy/config, latest accounting and unresolved reservations. Restore into isolated PostgreSQL, validate record counts, relational integrity, IDs, revisions, permissions, review and accounting. Compare representative protected reads and a no-dispatch evaluation before cutover. There is no rollback by restoring an earlier spending ledger: freeze dispatch, preserve newer accounting, reconcile every later call, then use a tested compatible rollback or restore. Unknown ledger freshness blocks paid dispatch.

## Verification to implement

- API: idempotent duplicate/conflicting requests; cross-scope denial; revoked and expired grants; bounded requests; repeated cancellation; report/export reauthorization; safe errors and redacted logs.
- Worker/DB: simultaneous claims and reservations; stale fence; lease loss; original deadline; quota exhaustion; crash before and after dispatch; unknown usage; cancellation at each boundary; DB outage; restore and no automatic paid replay.
- Source: wrong scope, pagination and byte bounds, revision change, partial/empty/unavailable/denied distinction; revoke transmission between read and provider call; reject evaluator fields.
- Release: installed wheel and non-root image, no evaluator answers/secrets in runtime image, pinned dependency and image hashes, versioned schema compatibility, migration/rollback rehearsal and preserved CLI reproduction.
- Acceptance: no real provider call, cloud apply, source access or mutation is implied. #57/#58 own implementations and tests; #60 owns hosted failure and recovery evidence; #87/#65 retain actual diagnostic and human-review gates.
