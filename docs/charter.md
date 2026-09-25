# TRACE charter

Status: Sprint 1 decision record, 2026-09-23  
Repository: [krispykrits/TRACE](https://github.com/krispykrits/TRACE)

## Purpose

TRACE is an incident intelligence and controlled-response platform that helps an engineer investigate incidents and carry out explicitly approved remediation. Its first useful workflow accepts a service and incident window, builds an auditable timeline, presents supported and competing hypotheses, identifies missing evidence, and suggests the next useful check. The initial Local/Cloud MVP investigation workflow remains read-only. Final capstone completion also requires at least one real, explicitly approved and verified production remediation through a separate deterministic executor. Temporal correlation alone is not root-cause proof; unsupported or insufficient evidence must produce uncertainty or abstention.

## Users and workflow

- **First product user:** on-call/investigating engineer.
- **MVP workflow:** Order → Payment; Customer and Notification are deterministic fixtures, not separately deployed services.
- **First interaction:** CLI. A web UI is deferred unless later evidence shows it is needed.
- **Operational pilot:** one named team/service and authorized source, starting with sanitized historical replay and then read-only shadow use. The pilot user and data-access owner are not yet identified; pilot claims remain blocked until they are.

## Scope and completion gates

| Gate | Completion evidence |
| --- | --- |
| **Local MVP (S1–S6)** | Reproducible synthetic incidents, SQLite-backed investigation/evidence state, small measured retrieval corpus, bounded read-only tools, explicit investigator workflow, cited structured assessment, deterministic timeline, abstention, automated development scoring and documented setup. |
| **Cloud MVP (S7–S9)** | The same workflow deployed repeatably to an initial EC2 target provisioned with Terraform and migrated to PostgreSQL on Amazon RDS, with access controls, workload identity/secrets, observability, cost controls, recovery and verified teardown/recreation. |
| **Full capstone (S10–S18)** | All 15 master-prompt capabilities, broader scenario coverage, evaluated classical ML and retrieval, five comparison arms, hardened operations/security, frozen-protocol study, final defense, and verified authorized production remediation after staging validation. |
| **Operational Pilot (independent)** | Authorized historical replay and read-only shadow use with a named operator/team; comparison to their current workflow and a deterministic evidence bundle; operator-reviewed utility, quality, reliability, latency and cost evidence; access isolation, recovery, support ownership and feedback. |

Passing a synthetic evaluation, deploying to AWS or finishing the capstone does not itself satisfy the Operational Pilot gate. The [production remediation scope](planning/production-remediation-scope.md) separately requires execution on an authorized workload serving a real operational purpose; simulation or staging-only execution does not satisfy that requirement. A missing production target/access remains a final acceptance blocker, not a reason to invent or force a production incident.

## Approved product and architecture constraints

- Use this TRACE repository for one modular Python application with TRACE-owned contracts.
- Treat Volumes 1–4 as educational reference implementations. Reuse selected components only through versioned, installable boundaries; do not depend on editable sibling directories.
- Volume 1 triage supplies vocabulary and fixtures; the Volume 2 classical detector is a later evaluated candidate; Volume 3 deep learning is conditional on measured benefit; Volume 4 retrieval is adapted behind TRACE contracts.
- Volumes 5 and 6 are design inputs. Their capabilities will be implemented within TRACE; they are not existing dependencies.
- Preserve source provenance, event/collection times, authorization scope, stable identifiers, redaction, bounded read-only operations, and separation between investigator-visible evidence and evaluator-only labels.
- Keep ML and the full five-arm study as final requirements, but outside the Local MVP critical path.
- **Cloud deployment direction:** use Terraform to provision an EC2-based initial AWS deployment target. This selects the IaC tool and first compute target, not instance size, region, network topology or application rollout mechanism.
- **Persistence direction:** use SQLite for Local MVP investigation/evidence state in S3, then migrate to PostgreSQL on Amazon RDS during the Cloud MVP. [ADR 0005](adr/0005-sqlite-local-postgresql-rds-cloud.md) records the owner choice; database schema, RDS sizing, access and migration evidence remain future gates.
- **Vector storage direction:** the owner requested a vector database. [ADR 0006](adr/0006-pgvector-cloud-retrieval-storage.md) proposes pgvector on the selected RDS database for Cloud MVP; product choice awaits owner review and #16 retrieval evidence. Keep the small exact-search Local MVP baseline and authorization/citation contracts.
- Keep investigation read-only and isolate remediation authority in a deterministic executor. Bind approval to the exact resource/environment, versioned action, parameters, expected state, expiry and recovery plan; revalidate before execution, reconcile uncertain outcomes before retries, verify health and retain audit evidence. Scope approval never authorizes an unspecified mutation.
- Validate a real action in staging before owner-supervised production promotion. S14-S18 incorporate implementation, readiness and production evidence under the approved scope; resize increments against actual capacity.
- Use feature branches and PRs for repository changes; no direct commits/pushes to main or automatic merges. Owner review precedes merging.
- Do not add Kubernetes, Kafka, a separate vector database, multi-agent orchestration, a dashboard, or cloud resources without measured need and an ADR.

## Minimum scaffold decisions

- **Runtime:** CPython 3.12, Linux as the first supported development/CI environment. Revisit only for a demonstrated dependency, deployment or course-platform constraint.
- **Package:** one installable project configured in `pyproject.toml`, with application code under `src/trace`. Do not create multiple deployable services in Sprint 1.
- **Environment and dependency locking:** use `uv` with a committed `uv.lock`; separate runtime and development dependency groups. Keep runtime dependencies empty until a real application boundary needs one. Any dependency added later must have a stated purpose.
- **Local tasks:** provide a small Makefile or equivalent documented commands for sync, run, lint/format, type-check, test and cleanup; avoid Docker/Compose until a real external dependency needs it.
- **Quality checks:** deterministic, credential-free tests and lint/format/type checks run locally and in GitHub Actions on Linux. CI must fail on a failing check and use minimal workflow permissions. Live provider checks are separate and explicitly identified.
- **Initial package contents:** importable CLI entry point that reports version/help and exits successfully; one meaningful smoke test; no Order/Payment logic, provider integrations, RAG, model calls or cloud code yet.

The package manager choice (`uv`) is a Sprint 1 default to make environment recreation and lock updates explicit. The lockfile records resolved versions; it does not imply an unrestricted or costly runtime dependency budget.

## Success measures and threshold gates

Definitions are agreed now; numeric targets are set with the relevant reviewer/operator before each acceptance run and then frozen for that run.

- **Evidence usefulness:** time to first useful evidence and time to a defensible next check, compared with the current workflow and a deterministic evidence bundle.
- **Diagnostic quality:** correct identification where answerable, supporting-citation quality, unsupported-claim rate, disclosure of missing evidence, and justified abstention.
- **Remediation quality:** evidence of actual resource change and intended health outcome; unauthorized/stale approval rejection, duplicate/crash reconciliation, failure/recovery handling and complete proposal-to-verification audit trail. Set numeric limits for the chosen action before acceptance.
- **Operational quality:** successful/recoverable investigations, access-boundary regressions, latency and cost per investigation.
- **Retrieval and ML:** retrieval Recall@K/MRR; detector precision/recall/F1, false alerts per service-day and detection delay; downstream diagnostic or tool-use benefit over simpler baselines.
- **Study quality:** paired results, explicit failed-run accounting, uncertainty/repeatability, separate unseen variants and unseen-family cohorts, and untouched final-test data until protocol freeze.

Thresholds must be written before the related acceptance run. Full-study thresholds, configurations, cohort definitions and analysis freeze before final-test access.

## Open charter inputs and gates

These values cannot be inferred from the repository and are deliberately not invented.

| Input | Owner | Decision gate | Current effect |
| --- | --- | --- | --- |
| University rubric, required capabilities and final deadline | Project owner | Before committing the Local MVP calendar/scope; reconcile with the 15-capability checklist | Keep sprint numbers as scope increments, not dates |
| Weekly capacity and sprint duration | Project owner | Before sizing S1–S6 or assigning dates | No duration or delivery date is committed |
| AWS/model spending limit and any account restrictions | Project owner | Before provider selection, paid evaluation or AWS provisioning | Sprint 1 and offline work remain credential-free; no cloud is provisioned |
| Pilot team/service, source owner and permitted/sanitized data | Project owner plus pilot data owner | Before operational replay; before shadow use obtain the source owner's approval | Operational usefulness remains unvalidated until access is authorized |
| Measured workload and numeric acceptance thresholds | Project team with course reviewer; pilot owner for operational gate | Before each acceptance run, with final study thresholds frozen before final-test access | Do not state numeric performance promises yet |
| EC2/RDS topology, region/AMI/instance and database sizing, network, Terraform state/backend, SQLite migration, and application rollout mechanism | Project team; account owner for access/cost constraints | S7 design after MVP workload and budget constraints are known; CI/CD rollout detail in S8 | Terraform, EC2 and PostgreSQL on RDS are selected directions; exact AWS resources, migration and deployment mechanics remain open; no provisioning is authorized by this plan |
| Production workload/action, service owner, approver and change/access policy | Project owner with production service owner | Before action-specific design is finalized; staging validation and explicit execution approval before production rollout | Track candidates during S1; no selected target or standing mutation permission is implied; unavailable access blocks final production-remediation acceptance |
| Packaging/runtime exception request | Project team | Revisit only if CI, selected dependencies or deployment demonstrate incompatibility | CPython 3.12 and `uv` remain the working default |

## Sprint 1 exit gate

A fresh checkout can recreate the locked development environment, import and run the minimal CLI, execute the documented checks and tests, and demonstrate that CI rejects an intentional failing check. Charter decisions and ADRs are linked; unresolved owner inputs have explicit gates. No AWS resources or domain behavior are part of this gate.
