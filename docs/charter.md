# TRACE charter

Scope clarification approved 2026-10-15: [ADR 0018](adr/0018-flexible-ml-and-ranked-response-options.md) records flexible ML selection and ranked incident-response options. Initial read-only releases and independent pilot/production-remediation gates are retained.

Status: Sprint 1 decision record, 2026-09-23  
Repository: [krispykrits/TRACE](https://github.com/krispykrits/TRACE)

## Purpose

TRACE is an incident intelligence and controlled-response platform that helps an engineer investigate incidents and carry out explicitly approved remediation. Its first useful workflow accepts a service and incident window, builds an auditable timeline, presents supported and competing hypotheses, identifies missing evidence, and suggests the next useful check. The completed product ranks applicable rollback, corrective code/configuration, mitigation, further-investigation and observe/escalate options, clearly marks the recommended response and explains evidence, uncertainty, benefit, risks, prerequisites, verification and recovery. The initial Local/Cloud MVP investigation workflow remains read-only. Final capstone completion also requires at least one real, explicitly approved and verified production remediation through a separate deterministic executor. Temporal correlation alone is not root-cause proof; unsupported or insufficient evidence must produce uncertainty or abstention.

## Users and workflow

- **First product user:** on-call/investigating engineer.
- **MVP workflow:** Order → Payment; Customer and Notification are deterministic fixtures, not separately deployed services.
- **First interaction:** CLI. A web UI is deferred unless later evidence shows it is needed.
- **Monitored .NET testbed:** on 2026-10-14 the owner selected lightweight independently running Order and Payment services, exported JSON first and later live Azure queries. The project owner (`krispykrits`) is the confirmed service owner and initial investigating engineer; [ADR 0017](adr/0017-dotnet-testbed-and-json-first-evidence.md) and [#69-#76](planning/dotnet-testbed-backlog.md) record the S7-S9 direction. Existing Local MVP fixtures remain a separate accepted baseline.
- **Operational pilot:** replay followed by read-only shadow use with named ownership and permitted sources. Owner/operator roles are settled for the planned .NET testbed; exact dataset/field transmission, retention, resources, thresholds and actual usefulness evidence remain open. Generated testbed incidents establish controlled evidence; broader operational-purpose pilot and production-remediation gates remain separate.

## Scope and completion gates

| Gate | Completion evidence |
| --- | --- |
| **Local MVP (S1–S6)** | Reproducible synthetic incidents, SQLite-backed investigation/evidence state, small measured retrieval corpus, bounded read-only tools, explicit investigator workflow, cited structured assessment, deterministic timeline, abstention, automated development scoring and documented setup. |
| **Cloud MVP (S7–S9)** | The same workflow containerized on Azure AKS through Terraform, with PostgreSQL/pgvector shared state, scoped workload identity, intentional release/rollback, observability, independent cost controls, recovery and verified teardown/recreation. |
| **Full capstone (S10–S18)** | All 15 master-prompt capabilities, broader scenario coverage, evaluated use-case-appropriate ML and retrieval, ranked response options with a clearly recommended action, five comparison arms, hardened operations/security, frozen-protocol study, final defense, and verified authorized production remediation after staging validation. |
| **Operational Pilot (independent)** | Authorized historical replay and read-only shadow use with a named operator/team; comparison to their current workflow and a deterministic evidence bundle; operator-reviewed utility, quality, reliability, latency and cost evidence; access isolation, recovery, support ownership and feedback. |

Passing a synthetic evaluation, deploying to Azure AKS or finishing the capstone does not itself satisfy the Operational Pilot gate. The [production remediation scope](planning/production-remediation-scope.md) separately requires execution on an authorized workload serving a real operational purpose; simulation or staging-only execution does not satisfy that requirement. A missing production target/access remains a final acceptance blocker, not a reason to invent or force a production incident.

## Approved product and architecture constraints

- Use this TRACE repository for one modular Python application with TRACE-owned contracts.
- Treat Volumes 1–4 as educational reference implementations. Reuse selected components only through versioned, installable boundaries; do not depend on editable sibling directories.
- Volume 1 triage supplies vocabulary and fixtures; Volumes 2 and 3 supply candidate ML components; Volume 4 retrieval is adapted behind TRACE contracts. Select ML for a justified incident-analysis use case using measured quality, reliability, latency, cost and operational complexity against appropriate baselines. Classical ML, deep learning, pretrained models and other suitable ML methods are candidates; no algorithm family or educational implementation is mandatory. See [ADR 0018](adr/0018-flexible-ml-and-ranked-response-options.md).
- Volumes 5 and 6 are design inputs. Their capabilities will be implemented within TRACE; they are not existing dependencies.
- Preserve source provenance, event/collection times, authorization scope, stable identifiers, redaction, bounded read-only operations, and separation between investigator-visible evidence and evaluator-only labels.
- Keep ML and the full five-arm study as final requirements, but outside the Local MVP critical path.
- **Cloud deployment direction:** on 2026-10-14 the owner selected Azure instead of AWS, deploying containers on AKS. Retain Terraform and the modular application; [ADR 0015](adr/0015-azure-aks-cloud-deployment.md) supersedes the EC2/CloudWatch hosting direction. ACR, Azure PostgreSQL Flexible Server/pgvector, Key Vault, Entra Workload Identity and Azure Monitor/Log Analytics are the planning baseline. Exact resource/runtime shape, budget, region, identity, networking and deployment acceptance remain #55-#60 gates; no resources are provisioned by this choice.
- **Persistence direction:** retain SQLite for Local MVP investigation/evidence state; Cloud MVP shared state moves to Azure Database for PostgreSQL Flexible Server under [ADR 0015](adr/0015-azure-aks-cloud-deployment.md). [ADR 0005](adr/0005-sqlite-local-postgresql-rds-cloud.md) retains the Local SQLite/PostgreSQL semantics with RDS hosting superseded. #57 must preserve evidence/job/corpus/review state and shared monetary reservations through migration, concurrent pods and recovery.
- **Vector storage direction:** preserve PostgreSQL/pgvector and the small exact-search Local MVP baseline. Cloud hosting uses the selected Azure PostgreSQL baseline; [ADR 0006](adr/0006-pgvector-cloud-retrieval-storage.md) is amended by ADR 0015 for the hosting change. Engine/vector compatibility, source/citation/revocation preservation, index rebuild and #57 migration acceptance remain gates.
- **Model provider and spending:** on 2026-10-13 the owner selected Azure AI Foundry / GPT-6 Luna, deployment `gpt-6-luna`, a $20/month TRACE model cap and explicit resource API-key fallback after Entra error 53003. Resource details and credentials remain private. [ADR 0012](adr/0012-model-provider-contract-and-bounded-call.md) and [PR #51](https://github.com/krispykrits/TRACE/pull/51) record the implemented connector/private spending journal and actual synthetic TRACE live check (143 input / 90 output tokens, 2,400 ms). Selected model version remains owner-reported; operational credential/account/processing/retention and real-source rights remain open. The local shared journal enforces conservative estimates/reservations at most $20; it is not Azure account-wide billed spending.
- **Provider data policy:** the owner approved [the transmission table](architecture/model-provider.md#owner-approved-transmission-policy--2026-10-13): synthetic evidence, scoped metadata and sanitized excerpts; internal runbooks/configuration/code require source-owner Azure transmission permission; customer/employee data is blocked; credentials and evaluator answers never enter context. Specific source rights remain independent. Stateless `store=false`/no-upload requests are implemented; provider service retention and Operational Pilot acceptance remain separate.
- **Production provider enforcement:** [the five mandatory controls](architecture/model-provider.md#required-production-enforcement--2026-10-13), `trace-provider-data-policy.v1`, are implemented in the reference-based gate with current independent source/transmission checks, bounded fail-closed redaction, preserved citations/local provenance, content-free audit and protected responses inheriting original input sensitivity. Deterministic negative/bypass tests and SQLite/process workflows verify those mechanisms. #35–#38 must retain them through assessment, investigation-wide budgets, workflow, storage and inspection; authenticated operational grant derivation/source permission/retention remain gates.
- Keep investigation read-only and isolate remediation authority in a deterministic executor. Bind approval to the exact resource/environment, versioned action, parameters, expected state, expiry and recovery plan; revalidate before execution, reconcile uncertain outcomes before retries, verify health and retain audit evidence. Scope approval never authorizes an unspecified mutation.
- Validate a real action in staging before owner-supervised production promotion. S14-S18 incorporate implementation, readiness and production evidence under the approved scope; resize increments against actual capacity.
- Use feature branches and PRs for repository changes; no direct commits/pushes to main or automatic merges. Owner review precedes merging.
- AKS/container deployment is owner-selected; use ADR 0015 and [the cloud backlog](planning/azure-cloud-backlog.md). Do not add Kafka, a separate vector service, multi-agent orchestration, a dashboard, microservices or additional cloud resources without measured need and an ADR. Cloud apply still requires explicit account/budget/design authorization.

## Minimum scaffold decisions

- **Runtime:** CPython 3.12, Linux as the first supported development/CI environment. Revisit only for a demonstrated dependency, deployment or course-platform constraint.
- **Package:** one installable project configured in `pyproject.toml`, with application code under `src/trace_app`. Follow [ADR 0010](adr/0010-capability-packages-and-adapter-boundaries.md) for capability placement and adapter composition; keep one modular deployable application.
- **Environment and dependency locking:** use `uv` with a committed `uv.lock`; separate runtime and development dependency groups. Keep runtime dependencies empty until a real application boundary needs one. Any dependency added later must have a stated purpose.
- **Local tasks:** provide a small Makefile or equivalent documented commands for sync, run, lint/format, type-check, test and cleanup; avoid Docker/Compose until a real external dependency needs it.
- **Quality checks:** deterministic, credential-free tests and lint/format/type checks run locally and in GitHub Actions on Linux. CI must fail on a failing check and use minimal workflow permissions. Live provider checks are separate and explicitly identified.
- **Initial package contents:** importable CLI entry point that reports version/help and exits successfully; one meaningful smoke test; no Order/Payment logic, provider integrations, RAG, model calls or cloud code yet.

The package manager choice (`uv`) is a Sprint 1 default to make environment recreation and lock updates explicit. The lockfile records resolved versions; it does not imply an unrestricted or costly runtime dependency budget.

## Success measures and threshold gates

Definitions are agreed now; numeric targets are set with the relevant reviewer/operator before each acceptance run and then frozen for that run.

- **Evidence usefulness:** time to first useful evidence and time to a defensible next check, compared with the current workflow and a deterministic evidence bundle.
- **Diagnostic quality:** correct identification where answerable, supporting-citation quality, unsupported-claim rate, disclosure of missing evidence, and justified abstention. Final response evaluation also reviews alternative applicability, ranking and recommended-action rationale, risks/prerequisites and verification/recovery; human selection never substitutes for action-specific execution approval.
- **Remediation quality:** evidence of actual resource change and intended health outcome; unauthorized/stale approval rejection, duplicate/crash reconciliation, failure/recovery handling and complete proposal-to-verification audit trail. Set numeric limits for the chosen action before acceptance.
- **Operational quality:** successful/recoverable investigations, access-boundary regressions, latency and cost per investigation.
- **Retrieval and ML:** retrieval Recall@K/MRR; task-appropriate ML quality/reliability/latency/cost and downstream diagnostic or tool-use benefit against suitable baselines. Detection use cases additionally measure precision/recall/F1, false alerts per service-day and delay; these are not universal metrics for every ML task.
- **Study quality:** paired results, explicit failed-run accounting, uncertainty/repeatability, separate unseen variants and unseen-family cohorts, and untouched final-test data until protocol freeze.

Thresholds must be written before the related acceptance run. Full-study thresholds, configurations, cohort definitions and analysis freeze before final-test access.

## Open charter inputs and gates

These values cannot be inferred from the repository and are deliberately not invented.

| Input | Owner | Decision gate | Current effect |
| --- | --- | --- | --- |
| University rubric, required capabilities and final deadline | Project owner | Before committing the Local MVP calendar/scope; reconcile with the 15-capability checklist | Keep sprint numbers as scope increments, not dates |
| Weekly capacity and sprint duration | Project owner | Before sizing S1–S6 or assigning dates | No duration or delivery date is committed |
| Azure infrastructure spending limit and account restrictions; model account/retention inputs | Project owner | Before Azure provisioning or newly authorized live validation | Azure/AKS is selected; the $20/month model cap remains separate. Infrastructure budget, exact account/identity/processing/retention and source-specific rights remain open. |
| Pilot team/service, source owner and permitted/sanitized data | Project owner is the confirmed .NET service owner and initial investigator; external data owners remain independent | Before ingestion/replay or live shadow use, record exact source/field/transmission and retention authority | #69/ADR 0017 selects Order/Payment and JSON-first integration; actual resources/recordings, representative operational evidence and usefulness remain unvalidated |
| Measured workload and numeric acceptance thresholds | Project team with course reviewer; pilot owner for operational gate | Before each acceptance run, with final study thresholds frozen before final-test access | Do not state numeric performance promises yet |
| AKS mode/tier/version/node pools, ACR/PostgreSQL sizing, Azure network, Terraform state/backend, shared-state migration and application rollout | Project team; account owner for access/cost constraints | S7 design after Local MVP/workload/budget review; S8 release implementation | Terraform/Azure/AKS and PostgreSQL/pgvector are the selected direction. #55-#60 record identity, concurrency/spending, migration/restore, telemetry and teardown gates; exact resources and provisioning remain open. |
| Production workload/action, service owner, approver and change/access policy | Project owner with production service owner | Before action-specific design is finalized; staging validation and explicit execution approval before production rollout | Track candidates during S1; no selected target or standing mutation permission is implied; unavailable access blocks final production-remediation acceptance |
| Packaging/runtime exception request | Project team | Revisit only if CI, selected dependencies or deployment demonstrate incompatibility | CPython 3.12 and `uv` remain the working default |

## Sprint 1 exit gate

A fresh checkout can recreate the locked development environment, import and run the minimal CLI, execute the documented checks and tests, and demonstrate that CI rejects an intentional failing check. Charter decisions and ADRs are linked; unresolved owner inputs have explicit gates. No cloud resources or domain behavior are part of this gate.
