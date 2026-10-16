# TRACE capstone delivery plan

Current owner decisions through 2026-10-15. The MVP-first direction was adopted on 2026-09-22 and refined through ADRs 0015, 0017 and 0018. This plan is the canonical delivery and acceptance record; [current status](../current-status.md) owns progress, and [the charter](../charter.md) owns stable scope and unresolved inputs.

## Delivery policy

Build an evidence-first investigation slice before expanding subsystems: deterministic evidence → bounded queries/retrieval/tools → cited assessment → evaluation. Reports distinguish observations, supported/competing hypotheses, missing evidence, uncertainty and next checks.

Use a modular Python core with API and persistent worker deployments under ADR 0021; retain the CLI for local execution and evaluation. Adapt educational components through TRACE-owned contracts; Volumes 5/6 are design inputs. Choose a justified evaluated ML contribution from suitable methods, preserving appropriate baselines and negative findings. [ADR 0018](../adr/0018-flexible-ml-and-ranked-response-options.md) requires ranked applicable response options with a clearly recommended action.

## Releases and acceptance

| Release | Target | Required scope and acceptance evidence |
| --- | --- | --- |
| **Local MVP** | End of S6 | Reproducible Order → Payment incidents; small semantic corpus; bounded read-only tools; explicit workflow; cited structured diagnosis; deterministic timeline; abstention; automated end-to-end development scoring; passing tests and documented setup. |
| **Cloud MVP** | End of S9 | The same workflow containerized on Terraform-managed Azure AKS, with shared Azure PostgreSQL/pgvector state after tested SQLite/journal migration, intentional image-digest promotion, scoped workload identity, secrets, observability, independent cost controls, recovery and verified teardown/recreation. |
| **Full capstone** | End of S18 | Broader benchmark, evaluated use-case-appropriate ML and retrieval, ranked response options with a clearly recommended action, all five comparison arms, hardened operations/security, frozen-protocol quantitative study, architectural justification and final defense; all 15 final capabilities retained, plus verified authorized production remediation. |

Quality/reliability/latency/cost thresholds and actual review coverage must be declared before each applicable acceptance run. The owner's frozen retrieval thresholds apply only to their recorded protocol. The $20/month model cap is separate from Azure infrastructure/account spending.

The independent Operational Pilot and real production-remediation requirement below retain separate evidence. Planning approval, synthetic demonstrations and green CI are not release or operational acceptance.

## Scope by release

| Area | Local/cloud MVP | Full capstone or conditional expansion |
| --- | --- | --- |
| Enterprise | Order → Payment runtime path; Customer/Notification lightweight fixtures | Expand service behavior or independent deployment only if scenario requirements justify it |
| Incidents | Deployment regression, dependency degradation, insufficient evidence; include unrelated deployment distractor | Six families: regression, degradation, exhaustion, load anomaly, configuration failure, cascading failure; ambiguous and adversarial cases |
| Evidence | Structured logs, latency/error metrics, deployments, stable IDs, provenance and UTC timestamps | Queue/resource signals and richer dependency graph as needed |
| Retrieval | Small curated versioned corpus, labeled queries, embeddings and measured semantic search | Broader ingestion; hybrid/reranking only if measured benefit |
| Tools | Bounded log, metric, deployment and knowledge queries | Dependency/version tools only for identified investigation gaps |
| Investigator | Explicit bounded workflow, structured report, deterministic timeline, CLI default | Required interactive web workflow before S15; richer state/hypotheses when justified |
| ML | Deferred from MVP; statistical summaries may support evidence inspection | Justified incident-analysis task and suitable ML method; reproducible comparison with appropriate baselines and downstream ablation; no mandatory algorithm family |
| Actions | Read-only investigation and recommendations; no operational execution tool | Rank applicable rollback, corrective modification, mitigation, further-investigation and observe/escalate options; mark the recommended response. Code fixes follow reviewed PR/tests/release. At least one real explicitly approved production remediation uses the separate deterministic executor after staging validation |
| Azure / AKS | Owner-selected containers on Terraform-managed AKS, shared PostgreSQL/pgvector, workload identity, cost/access controls and teardown | Review exact cluster/runtime, region/network, resource sizing/state and release design from measured requirements under ADR 0015; add services only with evidence |

Keep Customer/Notification lightweight until scenarios justify expansion. Azure/AKS, Terraform, PostgreSQL/pgvector and the modular runtime are selected; exact resources, identity, migration and operating acceptance remain cloud gates. API/worker and repository separation follow ADR 0021. Additional service extraction or a broker requires demonstrated need.

## End-state delivery update — 2026-10-15

[ADR 0021](../adr/0021-interactive-platform-and-repository-boundaries.md) selects an authenticated API and persistent investigation worker around the modular Python core. Retain CLI reproduction and keep evaluation in TRACE, excluded from runtime packages/images. Planned repositories: TRACE core/API/worker, trace-web, trace-testbed, trace-platform and trace-executor introduced with S14 remediation. Component CI/Dockerfiles stay with source; platform deployments pin compatible image digests. Repository extraction preserves historical reports/hashes and versioned contracts.

PostgreSQL-backed durable work dispatch is the initial choice: transactional submission, atomic claims, leases, cancellation, retries and shared attempt/spending admission. Reconcile uncertain external outcomes before retrying. No separate broker is required; add one only for demonstrated throughput/latency/contention/consumer needs. Use batch Jobs for evaluation, corpus rebuilds, migrations and scenarios.

Flexible capability contracts cover telemetry, knowledge, change/deployment records and workload state. JSON then Azure Monitor are first implementations. Preserve original identity/revision, timestamps, correlation, units, provenance and explicit completeness; enforce source/transmission/report rights independently, with scope/result/deadline/pagination limits. On-demand reads and batch import are initial modes; scheduled/event-driven ingestion and dedicated ingestion workers require a concrete lifecycle/volume/isolation need.

**Required web delivery:** after S8 API stabilization and before S15 pilot, provide submission, progress/cancellation, evidence/timeline and protected cited reports. S14 adds ranked-response comparison, selection and concrete approval UI/API, plus separate deterministic execution with distinct credentials. This is required scope. S7 must size stories and place them within S8-S14 capacity or add an undated increment before S15; do not assume it fits the existing 18 increments unchanged.

## Full delivery path

These 18 increments divide scope, not calendar time. Refine and resize work against capacity; dependencies and gates must change together.

| Sprint | Goal | Principal deliverables | Demo / exit gate | Dependencies |
| --- | --- | --- | --- | --- |
| 1 | Foundation | Charter, reuse inventory, package/runtime decisions, skeleton, configuration/logging, local tests and CI; #1–#6. | Clean checkout runs; checks fail correctly; decisions and setup documented. | Charter before implementation |
| 2 | Minimal synthetic workflow | Order → Payment runtime path; Customer/Notification fixtures; first seeded degradation; evidence IDs and evaluator-only ground truth; #7–#8. | Replay happy/failure paths; validate contracts, correlation and ground-truth isolation. | S1 |
| 3 | Reliable evidence and early scoring | Bounded log/metric/deployment queries and SQLite persistence for investigation/evidence state; regression/degradation/insufficient-evidence fixtures; noncausal deployment distractor; UTC timeline; development scoring runner. | Query evidence by ID/window/service; reproducible manifests; deterministic timeline and scorer fixtures pass; reserve final-test data. | S2 |
| 4 | Small retrieval corpus and controlled tools | Curated versioned knowledge, labeled retrieval queries and Recall@K/MRR; preserve exact search as the Local MVP baseline and record cloud pgvector compatibility requirements; typed bounded log/metric/deployment/knowledge tools; timeout/audit/authorization contracts. | Known queries retrieve supporting documents; invalid tool calls rejected; no operational write capability. | S3 |
| 5 | First complete investigator | Provider ADR, explicit bounded workflow, structured report, citations, alternatives, missing evidence, abstention, deterministic timeline; CLI by default; automated end-to-end scoring begins now. | Run an incident from evidence to scored report; validate citation IDs and sampled support; test timeout, malformed output and insufficient evidence; record usage/cost. | S4 |
| 6 | Local MVP acceptance | Stabilize development suite, LLM-only reference versus integrated RAG/tools, scoring rubrics and failure accounting; document minimum release thresholds before acceptance runs. | One command reproduces suite and reports diagnosis, unsupported claims, citations, abstention, timeline, latency/cost/failures; meet documented thresholds; critical boundary tests pass. | S5 |
| 7 | End-state redesign, repository boundaries and Azure design | #55 owns API/worker, PostgreSQL dispatch, source contracts, repository extraction/release and identity design under ADR 0021; Terraform/resources/budget/recovery retained. #69-#72 supply independent .NET testbed and recordings. Size required web/extraction work. | Reviewed architecture/contracts, repository ownership/migration and resized backlog; reviewed infrastructure plan and authority/cost assumptions; no apply. | Local MVP gate; design refinement may proceed in parallel |
| 8 | API/worker implementation and AKS delivery | #56-#59 deliver API/worker entry points/images, shared PostgreSQL dispatch/admission, authenticated API, persistent worker, scoped identities, releases and telemetry. #73-#75 deliver protected JSON import then first live Azure implementation. | Submit/status/cancel/protected-report flow on AKS; atomic claims and bounded execution preserve budgets, source/citation/review protection; CLI remains reproducible. | S7 contracts and accepted S6; size/split added scope |
| 9 | API/worker Cloud MVP acceptance | #60 validates remote API authorization/idempotency, worker concurrency/lease/restart/cancellation, uncertain outcomes, shared budgets, restore/rollback/teardown. #76 retains separate testbed replay/shadow comparison. | Versioned hosted evidence, no duplicate unbudgeted dispatch, protected reports, recovery/telemetry and residual-cost accounting; explicit blockers. | S8; independent Operational Pilot/remediation gates retained |
| 10 | Benchmark breadth and statistical baseline | All six incident families, matched symptoms with different causes, noncausal distractors, missing telemetry; versioned splits; threshold/statistical detector. | Validate scenarios/leakage; report detection precision/recall/F1, false positives and delay on development/validation data. | Cloud MVP gate |
| 11 | ML contribution | Select a justified incident-analysis task and suitable ML method; reproducible data/features/model artifacts or pinned model/configuration; compare against appropriate baselines. | Measure task quality, reliability, latency/cost, complexity and downstream investigation benefit; retain negative results and justify selection without requiring classical ML; model signals are not causal proof. | S10 |
| 12 | Retrieval and tool refinement | Broader curated corpus and labeled queries; independent tool selection/argument evaluation; justify retrieval changes; expand tools only for measured gaps. | Reproduce retrieval and tool reports; regression suite passes; optional hybrid search/reranking earns inclusion experimentally. | S11 baseline; technical prerequisites S4–S6 |
| 13 | Full five-arm comparison harness | LLM only; RAG; tools; RAG+tools; RAG+tools+ML. Shared incident briefs, budgets, recorded conditions, deterministic scoring and calibrated judge/human rubric. | Run all five arms on common development incidents; account for failed runs and reproduce scores from artifacts. | S11–S12 |
| 14 | Response workflow, executor and hardening | Ranked options and recommended action; response selection/concrete approval UI/API; separate trace-executor identity/deployment, supported deterministic actions and staging adapter; security/resilience/operations. | Review response rationale; verify staging mutation and stale/unauthorized/duplicate/crash defenses. Recommendation and selection grant no execution authority. | S13 and required web investigation workflow |
| 15 | Pilot and protocol preparation | Validation-only AI pilot and rubric calibration; separate production-remediation readiness review and owner-supervised rollout; identify remaining completeness gaps. | Five-arm pilot is reproducible; sample scoring reviewed; final test set untouched; planned report tables and comparisons defined. | S14 |
| 16 | Protocol freeze and readiness gate | Freeze datasets, corpus, model/prompt/tool/config versions, budgets, thresholds and statistical analysis; complete final capability evidence review. | Every required capability, including verified authorized production remediation, has evidence or a blocking item; protocol approved before final test access; no unresolved critical blockers. | S15 |
| 17 | Controlled experimental study | Run frozen five-arm study; analyze paired results/variability, failures, quality/latency/cost tradeoffs and ML benefit. | Reproduce tables from saved artifacts; separate unseen-variant and unseen-family results; disclose negative results and synthetic limitations. | S16 |
| 18 | Final demonstration and defense | Report, architecture/ADRs, evidence index, operations guide, demo recording/fallback and defense rehearsal. | All 15 final capabilities evidenced; selected results reproduced; decisions, limitations and teardown explained. | S17 |

## Backlogs and dependencies

| Track | Scoped work and order |
| --- | --- |
| Sprint 5 handoff | [#34–#37](https://github.com/krispykrits/TRACE/issues/37) establish provider/assessment/budget/workflow contracts; [#38](https://github.com/krispykrits/TRACE/issues/38) exposes protected CLI/report access; [#39](https://github.com/krispykrits/TRACE/issues/39) scores actual output and verifies integration |
| Sprint 6 acceptance | [#63](https://github.com/krispykrits/TRACE/issues/63) [protocol/thresholds and dry-run preparation](local-mvp-acceptance.md) before measurement; #64 comparisons → #65 actual human review; #66 recovery and #67 security; #68 clean-environment release after #63–#67 and S5 |
| Azure Cloud MVP | [#55–#60](azure-cloud-backlog.md): measured design, immutable image, shared state/admission, pod identity/releases, hosted telemetry and cloud acceptance |
| Monitored .NET services | [#70–#76](dotnet-testbed-backlog.md): local services → telemetry/JSON → controlled recordings → protected import → AKS telemetry → bounded live queries → owner-led replay/shadow comparison |
| Full capstone | Refine S10–S18 issues when capacity and prerequisites are known; preserve the ML/response and study gates rather than creating placeholder implementation stories |

The project owner is the planned .NET service owner and initial investigating engineer. Testbed source belongs in planned trace-testbed after S7 repository refinement, with independent .NET CI and no Python wheel dependency. Exported JSON precedes live Azure queries. Generated incident evidence remains separate from broader operational-purpose validation.

## Cross-cutting acceptance

These requirements apply throughout implementation:

- Source-neutral evidence preserves identity/revision, event/collection UTC time, service/environment, correlation, units/windows, provenance and completeness. Missing telemetry never becomes an observation.
- Trusted grants are independent of caller filters; authorization/freshness/revocation apply to tools, search, direct evidence reads and saved citations.
- Keep evaluation labels, fault schedules and held-out answers outside runtime inputs, retrieval, prompts and images.
- Bound model/tool calls, context/results, retries/corrections, tokens, deadlines and spending. Preserve actual/unknown usage and failures; do not invent successful results or cost.
- Persist evidence/jobs/attempts and protected reports. Prove idempotency, recoverable dispatch, cancellation, duplicate/crash/unknown-outcome handling, restore, retention/deletion and rollout rollback for the relevant runtime.
- Hosted execution uses scoped identities and shared durable admission; pod retries or independent local journals cannot bypass the model cap. Include queue wait in end-to-end latency where applicable.
- Apply the [provider policy](../architecture/model-provider.md#required-production-enforcement--2026-10-13) on every request/history/result: independent source/transmission checks, bounded reviewed redaction, citations/private provenance, content-free audit and input-sensitive protected responses.
- Record tests, adversarial/failure evidence, operating ownership and blocked prerequisites. A skipped/fake live check or synthetic reviewer cannot satisfy a required actual-provider/human gate.

## Evaluation

- S3 defines the result/ground-truth contract, scorer fixtures and split policy; S5 scores the first end-to-end investigator automatically. Do not postpone evaluation until the full comparison harness.
- S6 compares an LLM-only reference with integrated RAG/tools on the development suite. This is an MVP diagnostic comparison, not the final ablation study.
- S13 runs all five required arms: LLM only; LLM + RAG; LLM + tools; LLM + RAG + tools; LLM + RAG + tools + ML.
- Give each arm the same common incident brief. Document allowed evidence channels, model/version, prompt policy, budgets and unavoidable differences. Record tool calls, tokens, latency, cost and failed runs; do not silently drop failures.
- Use separate train/development/validation/final-test artifacts. Group related templates and near-duplicate causal variants to prevent leakage. Report **unseen variants of known families** separately from **entirely unseen families**; decide cohort allocations before the study rather than forcing one split to answer both questions.
- Keep held-out ground truth, answer-bearing postmortems and labels out of investigator tools, retrieval, prompts and training. Version corpus, data, seeds, model, prompt, configuration and run artifacts.
- Score root-cause/service identification, groundedness, supporting citations, unsupported claims, abstention, timeline correctness, tool selection/arguments, reliability, latency and cost. Use independent retrieval Recall@K/MRR and anomaly precision/recall/F1, false-positive rate and delay.
- Citation ID existence is not citation support: validate IDs deterministically and review evidentiary support with a documented rubric. Calibrate any LLM judge against human-reviewed samples; never use it as the sole evaluator of critical claims.
- Select a justified ML task, such as anomaly detection or signal prioritization, and evaluate suitable candidate methods against appropriate baselines. Measure task quality, reliability, latency, cost, operational complexity and downstream diagnosis/tool-use benefit. Classical ML, deep learning, pretrained models and other suitable ML methods are eligible; model signals are not causal proof. Negative results and choosing simpler methods are valid outcomes.
- Include successful/unrelated deployments near incidents, similar symptoms with different causes, and incomplete telemetry. Reward justified uncertainty instead of forcing one root-cause answer.
- Pilot on development/validation data, freeze thresholds/configurations/analysis in S16, then access final test data in S17. Repeat stochastic runs and report uncertainty. Document synthetic-to-real generalization limitations.

For the selected ML task, use task-specific metrics; detection additionally needs realistic alert burden and delay. S14 versions/reviews response alternatives, ranking and recommendation rationale, including incomplete evidence and noncausal deployments. A recommended investigation/escalation is valid when corrective action is unsupported. Runtime/evaluator mechanics are defined in [development evaluation](../architecture/development-evaluation.md) and [the evaluation guide](../../evaluation/README.md).

## Independent Operational Pilot

Require authorized real or sanitized historical replay followed by read-only shadow use with a named operator/team. Compare against the operator's current workflow and a deterministic evidence bundle. Predeclare usefulness, quality, reliability, latency and cost criteria, review coverage and permitted source/transmission/retention policy.

Acceptance includes operator feedback, access isolation, recovery/restore and support ownership. Missing representative access/evidence remains an explicit blocker. This gate is separate from Local/Cloud MVP, Full Capstone and S15's validation-only experimental pilot; it may overlap releases when ready.

## Response and production-remediation gate

The final product ranks applicable rollback, corrective modification, mitigation, further-investigation and observe/escalate options and identifies the recommended response. Code/configuration proposals follow reviewed PR/tests/release. Supported operational actions use the separate deterministic catalog/executor and concrete action-specific approval.

Final completion requires at least one verified, explicitly authorized remediation on an operational-purpose production workload after staging validation. Preserve proposal-bound approval, state revalidation, bounded/idempotent/reconciled execution, actual resource and health verification, recovery/escalation and audit. A simulated/staging-only action does not satisfy production acceptance. [The remediation scope](production-remediation-scope.md) owns the detailed controls and S14–S18 evidence requirements.

## Full-capstone evidence checklist

- [ ] Seeded incident suite and isolated ground truth
- [ ] Stable, queryable telemetry/evidence
- [ ] Appropriate baselines and use-case-specific ML evaluation
- [ ] Independent semantic retrieval evaluation
- [ ] Controlled tool contracts and boundary evidence
- [ ] Interactive submission/progress/cancellation and protected cited-report views
- [ ] Versioned cross-repository releases and flexible source-adapter contracts
- [ ] Cited investigation, uncertainty and ranked recommended responses
- [ ] Deterministic timeline and bounded workflow
- [ ] Automated five-arm evaluation
- [ ] Repeatable Azure AKS deployment and teardown
- [ ] End-to-end observability
- [ ] Tests and CI/CD promotion evidence
- [ ] Frozen quantitative study with limitations
- [ ] ADRs and justified alternatives
- [ ] Operations/security documentation
- [ ] Reproducible final demonstration and defense

The real production-remediation requirement and independent Operational Pilot retain the separate gates above.

## Planning and review rules

[Project Status](https://github.com/users/krispykrits/projects/2) is authoritative for work status. Milestones are provisional sprints; future dates, capacity, infrastructure budget, rubric and remaining thresholds are [owner inputs](../charter.md#open-inputs-and-decision-gates).

Use scoped stories with acceptance criteria, dependencies, tests, documentation, risks and demonstration. Close implementation only with reviewed code, relevant checks, reproducible evidence and no unresolved critical blocker. Record incomplete work and lessons using the [sprint review template](../sprints/sprint-review-template.md). Keep historical review snapshots and merge details outside this active plan.
