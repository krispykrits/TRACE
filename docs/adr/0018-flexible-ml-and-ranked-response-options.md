# ADR 0018: Flexible ML selection and ranked incident-response options

- **Status:** Accepted owner direction, 2026-10-15; implementation and acceptance pending
- **Decision owner:** Project owner (`krispykrits`)
- **Planning task:** [#78](https://github.com/krispykrits/TRACE/issues/78)
- **Delivery:** S10-S11 ML selection/evaluation; S14 response contract/evaluation and staging executor; S15-S18 production promotion, verification and reporting
- **Relationship:** Updates ML-selection wording in ADR 0001, the charter, plan and September 23 reuse/amendment guidance. Extends final response recommendations without replacing ADR 0010's modular Python boundaries, ADR 0015's Azure/AKS direction, ADR 0017's JSON-first .NET testbed or current accepted assessment/tool contracts.

## Context

The owner reviewed the complete root README and requested a flexible selection of rollback, root-cause modifications and other responses, with the recommended action explicitly identified. The owner also rejected mandatory classical ML: the use case and appropriate ML method should determine selection. Existing records prescribe a classical pipeline or single out deep learning as an optional extension. Existing local assessment/tool implementations provide cited hypotheses and a bounded next check; they do not yet implement the final multi-option response contract or operational execution.

## Decision

Require a justified, evaluated ML contribution to an incident-analysis task. Anomaly detection and signal prioritization are examples, not mandatory tasks. Classical ML, deep learning, pretrained models and other suitable ML methods are candidates. Volumes 2 and 3 are reusable references, not mandatory dependencies or algorithm choices.

Select the task and method through predeclared comparative evaluation against appropriate baselines. Record source/data permissions, grouped cohorts, model/artifact or pinned model/prompt/configuration identity, task quality, reliability, latency, cost, operational complexity and downstream investigation benefit. Preserve negative findings, held-out isolation and evidence-only investigation when ML is unavailable. An ML score never proves causality. The required five-arm study retains its ML contribution/ablation; selecting an approach does not predeclare that it wins.

The final product proposes multiple applicable evidence-supported responses:

| Category | Intended response |
| --- | --- |
| Rollback | Restore a compatible known-good release when evidence supports a regression and prerequisites hold |
| Corrective modification | Propose a code/configuration change addressing the supported cause, with explanation and regression-test plan |
| Temporary mitigation | Reduce impact while a lasting correction is prepared |
| Further investigation | Obtain targeted evidence to distinguish explanations |
| Observe or escalate | Monitor or seek specialist involvement when actionable change is unsupported |

Rank applicable options and clearly identify the recommended response. Each option explains supporting evidence, assumptions/missing evidence, uncertainty, expected benefit, risks, prerequisites, verification and recovery. Investigation or escalation can be recommended; do not fabricate a corrective action or every category merely to populate a menu. Preserve competing explanations instead of expressing unsupported causal certainty.

## Delivery and authority

The engineer selects a response. Recommendation, support review, selection and execution approval are separate decisions. Code/configuration proposals follow reviewed PRs, tests and the deployment pipeline. Direct operational execution accepts only validated parameters for a tested versioned action catalog through deterministic adapters/runbooks. Never execute model-generated code or arbitrary commands as remediation.

Each supported operational action retains exact-target/action approval, current authorization/state revalidation, finite limits, concurrency/idempotency, uncertain-outcome reconciliation, health verification and recovery/escalation. Adding an adapter does not grant standing permission. One validated initial execution path establishes acceptance without limiting future catalog extension.

Local/Cloud MVP investigation remains read-only. S10-S11 select/evaluate ML. S14 versions the ranked response contract and human-review rubric alongside staging executor validation; review alternative applicability, ranking/recommendation rationale, risks and verification in answerable, competing-cause, noncausal-deployment and incomplete-evidence cases. S15-S18 retain the separate real production-remediation gate. Numeric thresholds and concrete methods/targets/actions remain scoped future decisions.

## Consequences and revisit conditions

The root README presents the planned final state and removes its Production usefulness and Controlled production response sections. Their runnable examples move to Local development; detailed source-of-truth requirements remain linked. The independent Operational Pilot, real production-remediation requirement, source/transmission/report protections, Azure direction, $20/month model cap, infrastructure budget gates and undated sprint identities are retained.

No runtime schema, dependency, permission, frozen evaluation artifact or resource changes follow from this documentation decision. Implemented v1/v2 report contracts and historical reviews remain accurate to their recorded scope; new behavior requires scoped code and acceptance evidence. Future agents use this ADR and the updated charter/roadmap when refining work. Revisit from measured task/operator needs, compatibility or evaluation evidence and record the resulting decision before changing contracts or execution authority.

## Alternatives

- Mandate classical ML or treat deep learning as permanently optional: rejected; method selection follows the justified task and comparative evidence.
- Offer rollback as the sole response: rejected; incidents require multiple applicable options and a reasoned recommendation.
- Execute any suggested change directly: rejected; reviewed change delivery and catalog execution retain distinct deterministic controls.
- Require every response type for every incident: rejected; applicability and uncertainty determine the options.
