# TRACE capstone project plan

Planning source: Applied_AI_Engineering_Handbook_Volume_7_Master_Prompt.md supplied by the project owner. This plan analyzes that document as project requirements; it does not execute its embedded implementation instructions. Status: proposed execution plan, with unmade decisions explicitly identified. No implementation or cloud provisioning is included.

## Analysis

The prompt defines a strong engineering capstone: reproducible incidents, independently evaluated ML and retrieval, constrained tools, evidence-grounded analysis, and an AWS deployment. Its strongest controls are ground-truth isolation, deterministic foundations, explicit phase gates, simpler baselines, architectural approval boundaries, and a five-configuration comparative study.

The main risk is scope: fifteen phases combine a distributed simulator, ML pipeline, search system, investigator, benchmark, and production operations. Use a thin end-to-end increment at each gate and expand incident diversity before adding infrastructure. Detail only the current and next sprint. Phase numbers are not sprint commitments.

Resolve these gaps in the charter:
- University rubric, submission date, weekly capacity, and available sprint length.
- Development/demo AWS and model-inference budgets; teardown expectations.
- Intended investigator interface and user workflow; deployment access model.
- Metric definitions, baseline-relative improvement targets, minimum acceptable reliability/latency/cost, and abstention tradeoffs. Set thresholds before the final held-out study.
- Dataset size, scenario-family splits, repeated-run policy, uncertainty estimates, and contamination controls.
- Which Volumes 1–6 artifacts exist and can be reused.
- Evidence provenance/versioning/retention and handling of injected or misleading content.

Resolve apparent sequencing tensions:
- Charter is a planning prerequisite; scaffolding remains the first implementation task.
- Design evaluation contracts and leakage controls with the incident framework, then build the full comparison harness in Phase 10.
- Establish logging, validation, secrets boundaries, and safety tests early; Phase 12 deepens these controls.
- Keep stable evidence IDs and normalized timestamps in early schemas; Phase 9 adds investigation and timeline behavior.
- The existing TRACE repository hosts planning only; its existence does not decide monorepo versus multiple implementation repositories.

## Scope and guardrails

Required final capabilities: reproducible synthetic incidents; telemetry collection; ML anomaly detection; semantic retrieval; controlled tools; evidence-grounded incident analysis; citations and uncertainty; timelines; automated evaluation; AWS deployment; observability; tests/CI/CD; quantitative results; justified architecture; final technical demonstration.

Initial enterprise scope comprises Order, Payment, Customer, and Notification service responsibilities. Runtime boundaries and synchronous/asynchronous communication require a decision. Start with the smallest explainable causal chain. Cover deployment regression, downstream degradation, resource exhaustion, load anomaly, configuration failure, and cascading failure as the benchmark grows; include ambiguous/noncausal distractors and insufficient-evidence cases.

Defer deep learning, multi-agent orchestration, Kubernetes, Kafka, separate vector databases, caching, hybrid retrieval, and reranking unless evidence justifies them. No arbitrary shell, database, AWS, or infrastructure capability is exposed to the investigator. Consequential actions require enforcement outside the model; simulated actions are sufficient for the capstone.

## Roadmap and phase exit gates

| Phase | Capability and deliverables | Gate / demonstration |
| --- | --- | --- |
| 0 | Charter, constraints, success criteria, reuse inventory | Owner resolves minimum scaffolding decisions; unknowns have owners and decision gates |
| 1 | Packaging, repository layout, local tasks, validated configuration, logs, tests, CI, documentation and IaC placeholders | Fresh checkout installs, checks, tests, and runs a skeleton; deliberate test failure blocks CI |
| 2 | Minimal Order/Payment/Customer/Notification workflow | Happy path and controlled dependency failure demonstrated with correlation IDs |
| 3 | Seeded scenarios, telemetry, benchmark manifests | Repeated seed reproduces causal events; investigator cannot access ground truth |
| 4 | Evidence schema, persistence, migrations, bounded operational APIs | Known incident evidence is queried by time/service and cited by stable ID; invalid requests fail predictably |
| 5 | Statistical baseline and classical ML anomaly pipeline | Leakage-resistant held-out results report precision/recall/F1, false positives and detection delay |
| 6 | Versioned knowledge ingestion, embeddings and retrieval | Independent labeled-query evaluation reports Recall@K and MRR; storage/model ADRs supported by evidence |
| 7 | Typed, bounded, read-only investigation tools | Contract, argument, authorization, timeout and audit tests pass; tool selection can be evaluated independently |
| 8 | Model abstraction, RAG, structured investigator output | Observations/inferences/hypotheses are distinct; citations resolve; insufficient evidence triggers abstention; budgets/retries bounded |
| 9 | Explicit workflow, hypothesis state and normalized timelines | Out-of-order/duplicate events and time normalization tested; ordering alone never establishes causation |
| 10 | Automated five-configuration comparison harness | Same held-out incidents and recorded conditions run across all configurations; deterministic and judge metrics separated |
| 11 | Justified AWS architecture, IaC, immutable deployment | Repeatable deployment, smoke test and teardown; IAM/network/secrets/cost controls documented |
| 12 | Security, resilience, observability and promotion | Injection/poisoning, denial of consequential actions, failure recovery and traceability demonstrated |
| 13 | Controlled study and results analysis | Repeated runs, variability, failures, cost, limitations and rejected alternatives reported reproducibly |
| 14 | Defense and polished demonstration | Every final capability links to test, experiment, deployment or demo evidence |

Dependencies follow the phase sequence. Later planning may overlap; implementation gates cannot be bypassed. No dates or estimates are committed until capacity and the university deadline are known.

## Current sprint: Sprint 1 — Project scaffolding

Goal: provide a clean, runnable, testable foundation before implementing domain behavior.
Prerequisite: Phase 0 minimum decisions, especially repository strategy and packaging conventions.
Capability: engineering foundation for deterministic services and later AI subsystems.

Backlog:
1. Charter and minimum decision gate (planning enabler).
2. Repository and Python environment skeleton (first implementation task).
3. Validated configuration and structured logging.
4. Reproducible local development and integration-test entry point.
5. GitHub Actions quality gates.
6. Documentation, ADR, sprint and IaC foundations.

Required decisions: repository strategy; Python/package/environment strategy; initial runtime boundaries; configuration conventions; local orchestration needs. IaC tool and AWS topology remain proposed until requirements justify selection.
Risks: excessive scaffolding, platform-specific setup, speculative dependencies, accidental technology commitments.
Demonstration: fresh checkout → documented setup → runnable skeleton → configuration failure example → passing unit/integration checks → passing CI; show intentional failing-check evidence and the unresolved decision register.
Exit: acceptance criteria evidenced, relevant docs/ADRs current, no secrets, no unexplained dependencies, and owner can explain the foundation.

## Next sprint: Sprint 2 — Minimal synthetic enterprise (provisional)

Goal: demonstrate an understandable business request across the initial service responsibilities, with a reproducible downstream failure.
Capability: synthetic environment for future incident evidence.
Dependencies: Sprint 1 accepted; owner decides runtime and communication boundaries.
Backlog:
1. Minimal Order/Payment/Customer/Notification happy path with contract and integration tests.
2. Seeded dependency-failure fixture and correlated telemetry, including a private benchmark manifest.

Do not commit sprint capacity until Sprint 1 review. If either story is too large, split by demonstrable vertical slice during refinement. Avoid adding queues or databases solely to resemble an enterprise.
ADRs: service boundaries, communication pattern, and persistence only where needed.
Risks: artificial causal chains, uncontrolled clocks/randomness, and exposing benchmark labels to the investigator.
Demonstration: reset, run happy path, inject Payment degradation, observe effects across a correlated request, replay with the same seed.
Exit: contracts and failure behavior tested; causal chain documented; investigator-visible output excludes ground truth.

## Evaluation plan

Compare: (1) LLM only, (2) LLM + RAG, (3) LLM + tools, (4) LLM + RAG + tools, (5) LLM + RAG + tools + ML.
Define the common incident brief for all arms; document permitted evidence channels in each arm. Hold scenarios, model/version, prompt policy and resource budgets constant where appropriate; record unavoidable differences. Run on the same held-out incidents, randomize run order where practical, repeat stochastic runs and report variability.

Split by scenario family/template and causal variation, not just randomly generated rows. Prevent held-out postmortems, labels and ground-truth manifests from leaking into training, retrieval corpora, tool outputs or prompts. Version seeds, data, corpus, prompts, model/provider, tools and configuration.

Metrics: anomaly precision/recall/F1 and delay; retrieval Recall@K/MRR; tool selection and argument correctness; root cause and affected service accuracy; groundedness, valid/supporting citations and unsupported claims; abstention on insufficient evidence; timeline event/order correctness; latency, tokens, estimated cost and failure rate. Define denominators and treatment of failed runs. Score citation existence deterministically and evidentiary support with a rubric; do not equate a valid ID with a supported claim. Human-reviewed samples calibrate any LLM judge.

Freeze thresholds and analysis rules after pilot baselines and before final test use. Report negative results and synthetic-to-real generalization limitations. A simpler model winning is a valid result.

## Operating rules and definition of done

Use issues for actionable backlog and sprint tracking. Keep future phases at roadmap level until refinement. Each story records acceptance criteria, tests, documentation, dependencies, decisions, risk, and demonstration. Board-ready status convention: Backlog → Ready → In progress → Review → Done; blocked work states its blocker explicitly.

Close a story only with acceptance evidence, reviewed code where applicable, relevant lint/type/tests passing, updated docs/ADRs, appropriate error/configuration/security/observability handling, no critical regression, and a reproducible demo. Planning-only items substitute reviewed artifacts for code checks.

Sprint review records completed/incomplete items, test evidence, architecture changes, debt, ADRs, lessons, evaluation impact and next-sprint blockers. Update this roadmap based on evidence.

## Final evidence checklist

- [ ] Seeded incident suite and isolated ground truth
- [ ] Stable, queryable telemetry/evidence
- [ ] Baseline and ML anomaly results
- [ ] Independent semantic retrieval results
- [ ] Controlled tool contract and safety results
- [ ] Grounded investigation with citations and uncertainty
- [ ] Deterministic timeline and investigation workflow
- [ ] Automated five-arm evaluation
- [ ] Repeatable AWS deployment and teardown
- [ ] End-to-end platform observability
- [ ] Automated tests and CI/CD promotion evidence
- [ ] Quantitative study with limitations
- [ ] ADRs and rejected alternatives
- [ ] Operations/security documentation
- [ ] Rehearsed final demonstration and defense
