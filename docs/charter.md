# TRACE charter

Current scope: owner decisions through 2026-10-16. Delivery is defined in the [capstone plan](planning/capstone-project-plan.md); current progress is in [current status](current-status.md).

## Purpose

TRACE helps an investigating engineer assemble evidence, understand an incident and compare responses. Reports distinguish observations, supported and competing hypotheses, missing information, uncertainty and abstention. Time correlation and anomaly scores alone do not establish root cause.

The completed product ranks applicable rollback, corrective code/configuration modification, mitigation, further-investigation and observe/escalate options. It clearly identifies the recommended response and explains evidence, uncertainty, expected benefit, risks, prerequisites, verification and recovery.

## Users and ownership

| Role or boundary | Recorded direction |
| --- | --- |
| First product user | Investigating/on-call engineer; CLI first |
| Service owner and initial investigator | Project owner (`krispykrits`) for the planned independent .NET Order/Payment testbed |
| Local fixtures | Synthetic in-process Order → Payment; lightweight Customer/Notification fixtures |
| Monitored testbed | Independent .NET services; exported JSON first, scoped live Azure queries later; [ADR 0017](adr/0017-dotnet-testbed-and-json-first-evidence.md) |
| External sources and production target | Source owners, exact access/transmission rights and action-specific approval remain independent decisions |

Generated testbed incidents provide controlled evidence. Representative operational-purpose data and real production-remediation acceptance retain separate gates.

## Completion gates

| Gate | Required outcome |
| --- | --- |
| Local readiness, S1–S6 | Reproducible read-only CLI/evidence, full authorized timeline, bounded tools, protected assessment/review mechanics, local recovery/security and an owner readiness/handoff decision; no real-model quality claim |
| Local MVP diagnostic acceptance, S7 | Actual authorized Azure comparisons and sole-owner quality review against applicable predeclared thresholds; explicit diagnostic decision before hosted implementation acceptance |
| Cloud MVP, S7–S9 | Repeatable Azure/AKS delivery with shared state/admission, workload identity, observability, recovery and teardown |
| Full capstone, S10–S18 | Full capability checklist, justified evaluated ML, five-arm study, ranked responses, hardening, defense and verified authorized production remediation |
| Independent Operational Pilot | Authorized replay and read-only shadow use, comparison to the operator's workflow and a deterministic evidence bundle, predeclared utility/quality/reliability/latency/cost criteria, support ownership and feedback |

The [delivery plan](planning/capstone-project-plan.md#releases-and-acceptance) and [ADR 0022](adr/0022-sprint-06-readiness-and-sprint-07-diagnostics.md) define the owner-selected S6/S7 gate split. Synthetic scores, cloud deployment and academic completion do not independently establish operational usefulness.

Final production remediation requires an authorized workload serving a real operational purpose, staging validation and a concrete approved action with verified resource/health outcomes. A missing target/access is a recorded blocker. See [response/remediation scope](planning/production-remediation-scope.md).

## Settled product and architecture decisions

| Area | Decision |
| --- | --- |
| Repository/runtime | One modular Python `trace_app` package in this repository; CPython 3.12/Linux, `pyproject.toml` and locked `uv` environment |
| Dependency direction | Capability-owned contracts/use cases; concrete systems behind adapters selected by bootstrap; [ADR 0010](adr/0010-capability-packages-and-adapter-boundaries.md) |
| Reuse | Volumes 1–4 are references/candidates adapted behind TRACE contracts; Volumes 5–6 are designs implemented within TRACE; no editable sibling runtime dependencies |
| Local/cloud storage | Local SQLite; planned Azure PostgreSQL Flexible Server and pgvector with tested state/admission migration |
| Cloud | Azure, containers and Terraform-managed AKS; ACR, Entra Workload Identity, Key Vault and Azure Monitor/Log Analytics are the planning baseline; [ADR 0015](adr/0015-azure-aks-cloud-deployment.md) |
| Model provider | Owner-selected Azure AI Foundry / GPT-6 Luna, deployment `gpt-6-luna`; configured dated version remains owner-reported; [ADR 0012](adr/0012-model-provider-contract-and-bounded-call.md) |
| Model spending | At most $20/month in TRACE's local reservation/estimate controls; separate from account-wide billing and Azure infrastructure |
| ML | A justified evaluated contribution, with task/method selected through quality, reliability, latency, cost and operational complexity against appropriate baselines |
| Eligible ML methods | Classical ML, deep learning, pretrained models and other suitable ML methods; no required algorithm family or educational implementation |
| Response delivery | Engineer selection; code/configuration proposals through reviewed PR/tests/release; supported operational actions through a tested versioned deterministic catalog with exact-action approval |
| Interface and expansion | CLI first; a public API, dashboard, broker, service split or other infrastructure requires measured need and an ADR |

[ADR 0018](adr/0018-flexible-ml-and-ranked-response-options.md) governs ML and response selection. ML and the five-arm study remain final requirements beyond the initial MVP critical path. The evidence-only workflow must remain available when ML fails.

## Data and authority

- Preserve stable source/evidence identity, revisions, event/collection time, provenance, access scope and explicit incomplete/failure results.
- Keep investigator-visible evidence separate from evaluator labels, hidden fault schedules and expected answers.
- Check source access and model-transmission permission independently for every selection, history/retry and protected response. Internal code/runbooks require source-owner transmission approval.
- Permit only scoped metadata and reviewed/sanitized excerpts under [provider data policy](architecture/model-provider.md#owner-approved-transmission-policy--2026-10-13). Customer/employee data is blocked in the current implementation; credentials and evaluator answers never enter context.
- Preserve input-derived report sensitivity, current citation/source checks, independent support review and content-free audit. `store=false` does not establish zero service retention.
- Initial Local/Cloud MVP investigation remains read-only. Recommendation or assessment review does not authorize mutation. Every supported action retains exact-target approval, state revalidation, finite execution, reconciliation, health verification and recovery/escalation.

Current local composition assumes trusted callers/filesystem. Authenticated operational grant derivation, real-source/retention acceptance and cloud identity remain implementation gates; see [security](security/README.md).

## Success measures

Set and record numerical thresholds before the applicable acceptance run. Preserve existing frozen retrieval thresholds and separate them from unselected release/study/operator thresholds.

- **Investigation utility:** time to useful evidence and a defensible next check versus current workflow and a deterministic bundle.
- **Diagnosis/report quality:** identification where answerable, supporting citations, unsupported claims, timeline correctness, missing evidence and justified abstention.
- **Response quality:** applicable alternatives, recommended-action rationale, risks/prerequisites and verification/recovery.
- **Operational quality:** completed/recoverable investigations, isolation regressions, latency, actual/unknown usage and cost.
- **Retrieval/ML:** Recall@K/MRR and task-appropriate quality/downstream benefit; detection additionally measures alert burden and delay.
- **Remediation:** actual resource change and health outcome, denied/stale approvals, duplicate/crash reconciliation and auditable recovery.
- **Study quality:** paired comparisons, failure accounting, repeatability/uncertainty, grouped cohorts and untouched final-test data until freeze.

## Open inputs and decision gates

| Input | Owner and gate | Current effect |
| --- | --- | --- |
| University rubric, final deadline and full capability reconciliation | Project owner, before calendar/scope commitments | No academic deadline is inferred |
| Weekly capacity and sprint duration | Project owner, before sizing/dating increments | Sprints remain provisional scope divisions |
| Azure subscription/region, resources/network, infrastructure budget, retention and account restrictions | Project/account owner, #55 before a reviewed Terraform plan/apply or hosted acceptance | Cloud direction is selected; resources/spending are not implicitly authorized |
| Model/credential processing, rotation/retention and native pod token path | Project/account owner, before relevant operational/live acceptance | Local API-key connector evidence does not prove AKS Workload Identity |
| Exact source/field/transmission/retention rights and representative recordings | Owner for .NET testbed; independent owners for external sources, before ingestion/shadow use | Roles are settled; source permission and evidence remain gated |
| ML task/method and remaining release/study/operator thresholds/review coverage | Project team with owner/reviewer, before measurement; freeze before final-test access | Local MVP planning settings/sole owner review recorded in [the owner decision](planning/local-mvp-owner-decisions-2026-10-16.md); actual review, remaining study/operator thresholds and appropriate baselines remain required |
| Production workload, supported action/runbook, service owner, approver and change policy | Project/production owner, before action-specific design and staged promotion | No selected target or standing mutation permission |

## Working agreement

Use scoped issues, feature branches and linked PRs; owner review precedes merge. Tests, security, observability and documentation accompany implementation. Update the canonical records under the [documentation maintenance rules](README.md#keep-documentation-current); do not turn this charter into a merge log.
