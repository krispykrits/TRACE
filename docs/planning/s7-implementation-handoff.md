# Sprint 7 implementation and verification handoff

Status: proposed handoff for [#55](https://github.com/krispykrits/TRACE/issues/55), coordinated with [#89](https://github.com/krispykrits/TRACE/issues/89). The [hosted contract](../architecture/s7-implementation-contract.md) and [Azure candidate](s7-azure-deployment-candidate.md) define design inputs, not completed cloud capabilities. Owner review and the account-specific gates below remain required. The live comparison runner remains on hold until the redesign is complete.

The [Terraform adoption plan](s7-terraform-adoption.md) records the selected staged import approach, bootstrapped private state container, recovery settings, ownership boundaries, backend template and review gates. The backend was initialized and a preliminary registry plan was checked; no resource has been imported.

## Repository extraction and release sequence

### Extraction baseline and copy verification (#100)

The starting point for the first extraction increment is main commit `3be2f5e99e06ba69622c27c41b39b9722f01fbde`, before any files are moved. TRACE owns the Python core, CLI, planned API/worker and evaluation; independently owned infrastructure and testbed components can move only when their destination and release path exist. The existing `trace-app` entry point is declared in `pyproject.toml`; the standard credential-free CI runs `make check lint format-check type-check architecture-check test integration package-check`. The locked dependency file has SHA-256 `139dbf8a72d42fa297b5800e7b036a1180b60ad1d92fee5ed98d3a668e94657c`. The existing v3 comparison manifest has SHA-256 `049a75f23f3bf14fe4e6d2cf9b3cda649cb535bb307bad193ff47cccacde837d`; its README identifies its historical implementation checkout and artifact inventory. A baseline is not proof of a successful clean build, migration or hosted implementation.

For an actual copy, maintain a private JSON file containing `version: 1` and a nonempty `files` array. Each entry has a source-relative `source`, destination-relative `destination` and independently recorded lowercase `sha256`. Paths must use POSIX separators and cannot contain dot segments or symlinks. For example, with values chosen by the operator:

```json
{"version": 1, "files": [{"source": "old/path", "destination": "new/path", "sha256": "<64 lowercase hexadecimal characters>"}]}
```

```sh
uv run --locked python scripts/verify_extraction.py --source-root SOURCE --destination-root DESTINATION --manifest MANIFEST
```

The command compares both copies with the recorded digest and fails on missing, changed, duplicate or invalid mappings. It does not copy, delete, verify provenance or permissions, create an atomic snapshot, or prove runtime compatibility; keep the inputs stable during verification and perform independent clean-checkout builds, link checks and evidence reproduction before removal. Do not commit private manifests. The `trace-platform` destination is not currently verified; no repository or extraction is implied by this tool.

In the initial #100 increment, the existing v3 comparison was rescored successfully at its recorded `897caec` implementation checkout with no provider dispatch, and a temporary renamed copy of its manifest passed the verifier. The installed wheel/CLI and evaluator-exclusion check passed in the clean baseline worktree. These checks do not verify a future destination or complete extraction.

| Step | Work and dependency | Completion evidence and rollback |
| --- | --- | --- |
| 1. Baseline | Freeze source commit, existing CLI commands, wheel contents, locked dependencies, existing CI, local SQLite schemas, known synthetic reports and the staged inventory under #89. Separate unmerged #94 work from `main`. | Record artifact hashes and commands; run current tests and no-call rescoring at the recorded checkout. Do not rewrite frozen inputs or history. |
| 2. Contracts | Publish versioned API and event/source schema plus compatibility rules; establish ownership, security labels and release manifest. Keep core, API, worker and evaluation in TRACE. | Consumer/provider compatibility and evaluator-exclusion checks pass. Old contract stays available until consumers are migrated. |
| 3. Testbed and platform | Extract only the independently owned .NET testbed and infrastructure when implementations and target repositories exist. Keep build scripts, tests, Dockerfiles and CI beside each component; platform pins source/release/image digest and schema versions. | Clean checkouts build independently, each release is traceable, historic report hashes and source remain reproducible. Restore previous manifest/consumer if checks fail; do not delete original copies first. |
| 4. Web | Deliver required interactive web separately after the API is stable and before S15. Pin API compatibility and provide scoped authentication, submission, status/cancel and protected reports. | Versioned client contract tests, accessible flows, denied/expired auth tests and rollback to compatible web/API pair. Response approval/execution is later S14 scope. |
| 5. Executor | Introduce trace-executor at S14 with separate credentials, exact-target approval, idempotency/reconciliation, verification and recovery. | Staging evidence and authorization boundaries pass before any operational action; recommendations confer no authority. |

Development Azure infrastructure has been created as recorded in the [Azure handoff](s7-azure-deployment-candidate.md); this does not establish a TRACE hosted release, live operational source or completed repository extraction. Extraction requires verified access, release conventions and a reviewed migration PR; retaining old history does not require rewriting Git history. Each migration must map every moved file to its replacement, compare hashes and update inbound links/CI/tests before removing any tracked copy. [#89 inventory](s7-repository-and-evidence-inventory.md) and its [file-level list](s7-file-inventory.md) are starting inventories; item-level decisions and adviser OneDrive access remain to be verified.

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

The [observed development configuration](s7-azure-deployment-candidate.md#observed-development-environment--2026-11-01) supplies actual regions, selected SKUs, identity prerequisites, backup retention and limited connectivity evidence. Remaining facts include Foundry processing location, broader subscription restrictions/credit, current offer rates, OneDrive adviser access, approved data-specific retention, app identity grants and tested recovery. The owner considers the budget acceptable for now and will revisit it; a complete estimate and actual costs remain unverified and the cost criterion remains open rather than being silently waived. #55 issue acceptance also calls for a reviewed bill of resources and infrastructure design. Link the design PR and evidence through the issue's Development section; preserve live project status and issue history. Do not claim these gates complete because a design PR merged or this table exists.
