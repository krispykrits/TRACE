# Sprint 7 implementation and verification handoff

Status: proposed handoff for [#55](https://github.com/krispykrits/TRACE/issues/55), coordinated with [#89](https://github.com/krispykrits/TRACE/issues/89). The [hosted contract](../architecture/s7-implementation-contract.md) and [Azure candidate](s7-azure-deployment-candidate.md) define design inputs, not completed cloud capabilities. Owner review and the account-specific gates below remain required. The live comparison runner remains on hold until the redesign is complete.

## Repository extraction and release sequence

| Step | Work and dependency | Completion evidence and rollback |
| --- | --- | --- |
| 1. Baseline | Freeze source commit, existing CLI commands, wheel contents, locked dependencies, existing CI, local SQLite schemas, known synthetic reports and the staged inventory under #89. Separate unmerged #94 work from `main`. | Record artifact hashes and commands; run current tests and no-call rescoring at the recorded checkout. Do not rewrite frozen inputs or history. |
| 2. Contracts | Publish versioned API and event/source schema plus compatibility rules; establish ownership, security labels and release manifest. Keep core, API, worker and evaluation in TRACE. | Consumer/provider compatibility and evaluator-exclusion checks pass. Old contract stays available until consumers are migrated. |
| 3. Testbed and platform | Extract only the independently owned .NET testbed and infrastructure when implementations and target repositories exist. Keep build scripts, tests, Dockerfiles and CI beside each component; platform pins source/release/image digest and schema versions. | Clean checkouts build independently, each release is traceable, historic report hashes and source remain reproducible. Restore previous manifest/consumer if checks fail; do not delete original copies first. |
| 4. Web | Deliver required interactive web separately after the API is stable and before S15. Pin API compatibility and provide scoped authentication, submission, status/cancel and protected reports. | Versioned client contract tests, accessible flows, denied/expired auth tests and rollback to compatible web/API pair. Response approval/execution is later S14 scope. |
| 5. Executor | Introduce trace-executor at S14 with separate credentials, exact-target approval, idempotency/reconciliation, verification and recovery. | Staging evidence and authorization boundaries pass before any operational action; recommendations confer no authority. |

No new repository, secrets store, live source or infrastructure has been created. Extraction requires verified access, release conventions and a reviewed migration PR; retaining old history does not require rewriting Git history. Each migration must map every moved file to its replacement, compare hashes and update inbound links/CI/tests before removing any tracked copy. [#89 inventory](s7-repository-and-evidence-inventory.md) is the starting grouped inventory; item-level decisions and adviser OneDrive access remain to be verified.

## Existing story mapping

Sizes are relative delivery complexity, not dates or promised capacity: S = small isolated change, M = multiple coordinated components, L = implementation and failure/security evidence. Split any L story into independently reviewable increments once capacity is known.

| Work | Existing issue / size | Design dependency and evidence |
| --- | --- | --- |
| Architecture, identity, release, migration and bill | [#55](https://github.com/krispykrits/TRACE/issues/55), L | Review #95 design plus this contract/candidate. Verify actual subscription restrictions, model location and a complete estimate; leave unresolved gates explicit. |
| Docs and artifacts | [#89](https://github.com/krispykrits/TRACE/issues/89), M | File-level destination/reader/retention inventory, actual OneDrive adviser access, verified moves and S8 Blob handoff. |
| Reproducible image | [#56](https://github.com/krispykrits/TRACE/issues/56), M | Locked build, non-root process, private data/evaluator exclusion, SBOM/scan evidence, immutable digest, registry permissions and rollback. |
| Shared DB and spending | [#57](https://github.com/krispykrits/TRACE/issues/57), L | PostgreSQL migration with stable IDs and protected reports; atomic shared budgets/leases; uncertain-call reconciliation; backup/restore and pgvector checks. |
| API/worker | [#58](https://github.com/krispykrits/TRACE/issues/58), L | Versioned authenticated API/worker contracts, distinct identities, access revalidation, idempotency, cancellation, leases, failed dependencies and protected delivery. Depends on #56/#57; hosted acceptance retains #87/#65 decision. |
| TRACE telemetry | [#59](https://github.com/krispykrits/TRACE/issues/59), M | Correlated metadata-only/redacted logs, restricted readers, retention, collector failure and recovery; not testbed telemetry authorization. |
| Hosted acceptance | [#60](https://github.com/krispykrits/TRACE/issues/60), L | Account-specific infrastructure, actual identity, concurrent jobs, fault/restart/restore, budget/cost, telemetry and teardown evidence. |
| Testbed | [#70](https://github.com/krispykrits/TRACE/issues/70)–[#76](https://github.com/krispykrits/TRACE/issues/76), L across releases | Independent .NET workloads, declared exports and bounded scenarios; protected JSON import before live Azure queries and separate owner-led assessment. |
| Actual comparison | [#87](https://github.com/krispykrits/TRACE/issues/87) then [#65](https://github.com/krispykrits/TRACE/issues/65), L | On hold pending redesign completion by owner direction. Later require exact sources, approved run and separate paid execution; do not treat fixture output as diagnostic acceptance. |
| Web investigation | [#97](https://github.com/krispykrits/TRACE/issues/97), L | API contract and auth first; required before S15. No sprint capacity/date inferred. |
| Private artifact storage | [#98](https://github.com/krispykrits/TRACE/issues/98), M | S8 handoff for Blob identity, manifests, retention and checksum-verified reproduction. No storage migration until destination and access are verified. |

[#97](https://github.com/krispykrits/TRACE/issues/97) and [#98](https://github.com/krispykrits/TRACE/issues/98) supply detailed acceptance criteria for the new web and artifact-storage work. This table does not alter GitHub Project Status or close existing issues. S8/S9 contain multiple L efforts in addition to testbed work; assess actual capacity and split or add an undated increment before assigning dates. Do not require a message broker, independent ingestion worker, model microservice or new documentation repository without a measured need and reviewed decision.

## Verification matrix

| Gate | Required demonstration | Owner / issue |
| --- | --- | --- |
| Contracts and boundary | Versioned API/source schema; unauthorized/expired/cross-scope inputs; no untrusted authority; no evaluator input in runtime | #58, #73, #75 |
| Concurrency and money | Simultaneous claims and reservations, exhausted cap, duplicate submissions, lease/fence expiry, crash after provider dispatch, unknown usage, no paid replay | #57, #58, #60 |
| Data and review | SQLite-to-PostgreSQL ID/revision mapping, source revocation, citation/current-permission checks, partial source state, review-required and unreviewed claims | #57, #58 |
| Recovery and delivery | Scoped identity, non-root image, digest promotion, DB backup/restore, current spending ledger, cancellation, rollback, redacted telemetry, retained-cost teardown | #56, #59, #60 |
| Documentation / artifact preservation | File-level inventory, verified OneDrive destination/adviser access, copied hashes, valid links, reproducible frozen evaluation and restricted labels | #89 and artifact story |
| Model quality | Actual separately approved Azure run and actual sole-owner review; denominator/unknown/failure evidence | #87 and #65, after redesign |

## #55 acceptance and remaining external gates

The platform and contract documents propose API/worker boundaries, source capabilities, ownership, atomic admission, identities and migration tests. The cost candidate supplies a published-rate example rather than a subscription quote. The owner selected Azure for Students, North Central US preference, on-demand operation, a $15/month infrastructure target, OneDrive knowledge space, adviser access and private Blob for suitable artifacts; 14-day retention is tentative. These are recorded inputs, not proof of actual permissions or remaining credits.

Remaining facts that cannot be established from public repository contents: actual subscription restrictions/quotas/credit, region and Foundry processing location, supported resource SKUs/versions in the account, current offer rates, OneDrive account/access policy and resource-specific retention. The subscription-specific complete cost estimate must include all selected resources and missing charges; if it exceeds $15, present alternatives for owner decision. #55 issue acceptance also calls for a reviewed bill of resources and infrastructure design. Link the design PR and evidence through the issue's Development section; preserve live project status and issue history. Do not claim these gates complete because a design PR merged or this table exists.
