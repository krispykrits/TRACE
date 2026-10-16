# ADR 0022: Separate S6 local readiness from S7 diagnostic acceptance

- **Status:** Accepted owner delivery/dependency direction; implementation and acceptance pending
- **Date:** 2026-10-16
- **Decision owner:** TRACE project owner (`krispykrits`)

## Context

The S6 backlog required actual Azure diagnosis and human quality acceptance before S7, while the owner intends live diagnostic integration in S7. A connector already exists under ADR 0012; it is not an executable live comparison, AKS hosting or proof of diagnostic usefulness. S7 currently designs the Azure platform; hosted implementation remains S8 and Cloud MVP acceptance S9. Conflating these scopes creates an artificial S6 blocker and risks counting scripted outputs as model-quality evidence.

The [40-call comparison](../../evaluation/reports/local_mvp_comparison_offline_v2/README.md) completes 12/12 integrated proposals but retains 0/6 scripted cause accuracy, 0/12 full timeline completeness and no actual human support. Full timeline completeness is a local implementation defect; placeholder-model quality is unmeasured for a real model. Recovery/security and actual review tooling also need their own evidence. A sprint goal alone cannot settle these dependencies.

## Decision

S6 ends in an explicit **local-readiness and S7 handoff decision**, not Local MVP diagnostic acceptance. Require complete authorized deterministic timelines, protected local CLI/report/review-packet paths, reproducible three-arm offline contract comparisons and rescores, real local storage/process recovery and security evidence, installed-wheel/setup/runbook checks and an owner readiness review. Report scripted diagnosis/support values as descriptive/unmeasured for actual-model quality. Actual owner walkthrough of the local review flow supplies readiness evidence, not fictional model-quality support.

[The timeline fix #88](https://github.com/krispykrits/TRACE/issues/88) stays in S6 before #68. #64 owns the offline comparison harness; #66/#67 own local recovery/security. #68 owns the clean-environment readiness package and recorded owner handoff decision. #63 and its original protocol/decisions remain historical inputs, not proof of either gate.

[S7 actual-provider comparisons #87](https://github.com/krispykrits/TRACE/issues/87) wire the existing Azure adapter into a gated local comparison runner, then #65 supplies actual owner quality review. #65 records the final Local MVP diagnostic decision after actual judgments and applicable threshold assessment; it depends on #87 artifacts, avoiding a circular issue-closure dependency. Freeze a new applicable protocol/decision/source snapshot before actual measurement; preserve approved numeric targets and the 40-call setting unless a separately recorded owner revision changes them. Missing provider/spending/source/run facts remain explicit dispatch/diagnostic gates; this sequencing approval supplies none of them and authorizes no paid call.

S7 architecture #55 can proceed after the S6 readiness handoff or in parallel where independent. S8 hosted implementation acceptance requires the S7 diagnostic decision and reviewed S7 contracts/design. Do not make S7 diagnostics depend on S8 AKS deployment, or require completed S7 diagnostics before starting #55 design. Preserve S8 hosting/S9 cloud acceptance, the independent Operational Pilot, full study and production-remediation gates. Resize or split S7's added work against capacity; no dates or infrastructure apply are authorized.

## Alternatives

| Option | Disposition |
| --- | --- |
| Keep actual-provider acceptance in S6 | Rejected by the owner's explicit S7 sequencing choice; would retain the conflicting dependency. |
| Count fake model accuracy/support as Local MVP acceptance | Rejected: contract fixtures cannot establish diagnostic quality or actual human support. |
| S6 local readiness, S7 actual diagnostics and quality review | Selected: makes prerequisites executable while preserving a separate, unweakened diagnostic acceptance gate. |
| Wait for AKS before any model comparison | Rejected: a local runner can use Azure Foundry; it would create an unnecessary S7/S8 dependency cycle. |

## Consequences and evidence

The Local MVP now has two named gates: S6 local readiness and S7 diagnostic acceptance. Only the first can proceed without a live model. #65 moves to S7; #87 adds explicit live composition/measurement; #88 addresses the measured local timeline gap. Native milestones, issue dependencies, charter, plan and current status must agree. No issue is completed, score changed or release approved by this record.

In the owner conversation on 2026-10-16, the owner asked to adjust S6 rather than rely only on the sprint goal, noting Azure integration belongs later. When explicitly asked whether live diagnostic comparisons should move to S7 with S6 ending in local readiness rather than model-quality acceptance, the owner selected: **“Defer live diagnostics to S7 (Recommended)”**. Codex transcribed the choice; no exact timestamp, capacity, permissions or quality endorsement is inferred. ADRs 0012/0015/0021 retain their provider/cloud/architecture decisions; this ADR revises delivery dependencies only.

## Revisit conditions

The owner revisits sequencing if S7 capacity cannot hold diagnostics, review and architecture, if real provider/source/budget prerequisites remain unavailable, or if local readiness tests reveal a prerequisite change. Add an explicitly named undated increment or revised gate; do not silently drop quality thresholds, call a deferred gate passed, or move implementation into a sprint merely to match its title.
