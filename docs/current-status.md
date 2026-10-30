# TRACE current status

Updated: 2026-10-30 against main `5c51f61`: #68 / PR #93 is merged and #68 is closed. The Sprint 6 review still records the owner's handoff decision and demonstration details as pending. [Project Status](https://github.com/users/krispykrits/projects/2) remains authoritative for work status.

## Implemented

| Capability | Current evidence and limits |
| --- | --- |
| Local CLI and synthetic evidence | Configuration, Order–Payment demo and seeded replay commands; development/test fixtures only |
| Durable local state | SQLite schema 3: evidence, jobs/attempts, execution admission and private workflow artifacts |
| Knowledge and tools | Authorized corpus, lexical/semantic/hybrid retrieval, bounded quoted context, read-only tools and deterministic timelines |
| Model boundary | Azure connector, per-request data policy, protected responses and private spending journal; accepted synthetic connector check recorded in ADR 0012 |
| Assessment and execution | Strict cited assessments/support review, durable model/tool/token/deadline budgets and conservative uncertain-dispatch handling |
| Investigation use case | Bounded workflow and atomic private publication merged in [PR #62](https://github.com/krispykrits/TRACE/pull/62); offline demonstrations use hand-authored model/review records |
| Planning decisions | Azure/AKS, independent .NET testbed/JSON-first ingestion and flexible ML/ranked responses accepted as direction in ADRs 0015, 0017 and 0018 |

Merged [PR #82](https://github.com/krispykrits/TRACE/pull/82) provides captured-window CLI investigation, protected saved display/citation/export and cancellation with original dependency/clearance/retention and current support checks. Merged [PR #83](https://github.com/krispykrits/TRACE/pull/83) adds actual-output scoring, saved-artifact rescoring and bound review samples. Its [retained run](../evaluation/reports/investigator_offline_v1/manifest.json) passed 10/10 expected offline checks with zero critical boundary failures. The [Sprint 5 review](sprints/sprint-05-review.md) preserves the wrong fixture cause scores and a separate [guided owner review](../evaluation/reports/investigator_offline_v1_human_review_v1/README.md): all ten sampled claims indeterminate because their wording was too vague to assess; no determinate support rate. Paid end-to-end diagnosis and positive human support remain unmeasured.

#63 / [PR #85](https://github.com/krispykrits/TRACE/pull/85) records [owner-approved Local MVP settings](planning/local-mvp-owner-decisions-2026-10-16.md): three repeats, 36 attempts, $1 planning allowance, full integrated-output review by the owner alone and resource/retention expectations. Protocol/decisions v2 preserve the original v1 artifacts and label single-owner provenance. Actual provider/spending/source/run metadata, cleanup ownership and final run bindings remain gates. The [S6 review](sprints/sprint-06-review.md) records a later assisted synthetic walkthrough; no paid diagnostic run or actual-provider quality verdict is recorded.

#64 / [PR #86](https://github.com/krispykrits/TRACE/pull/86) executes and rescores all 36 offline attempts. After the owner [approved 40 tool calls](planning/local-mvp-tool-budget-adjustment-2026-10-16.md), the [fresh v2 comparison](https://github.com/krispykrits/TRACE/blob/ccfc3f49af33ab508b4abe3c5eceaab6a98fa612/evaluation/reports/local_mvp_comparison_offline_v2/README.md) completed all 12 integrated attempts as review-required, using 23–30 calls; both reference arms also completed 12/12. Saved rescoring is byte-identical without dispatch. The [original 20-call failures](https://github.com/krispykrits/TRACE/blob/ccfc3f49af33ab508b4abe3c5eceaab6a98fa612/evaluation/reports/local_mvp_comparison_offline_v1/README.md) remain unchanged.

The [#88 implementation and fresh v3 comparison](../evaluation/reports/local_mvp_comparison_offline_v3/README.md) deliver the full captured timeline independently of admitted model context: 12/12 integrated attempts complete under 40 calls, with 12/12 timeline completeness and zero observed critical boundary failures. Candidate full-snapshot completeness remains 0/12 because model selection is still bounded. Saved rescoring is byte-identical without dispatch. The original reports retain their failures in pinned Git history; only the latest comparison is kept in the working tree at the owner’s request. Cause accuracy remains 0/6 for the scripted placeholder mechanism; actual provider calls/human judgments remain zero and support is unmeasured. The owner reported reviewing the report on 2026-10-16; no bound per-claim support judgments were supplied. PR #90 is merged; local recovery/security/handoff and S7 actual diagnostic acceptance remain gates.

#66 / PR #91 is merged with [SIGKILL/restore evidence](../evaluation/reports/local_recovery_v1/README.md) and the [local recovery runbook](operations/local-recovery.md). Its original validation/corrected lease assumption remain recorded; recovery checks also pass in the successful #67 full run. The fully reviewed scripted path still exhausts 40 calls. The owner retained 40 for S6; measuring accepted-path requirements remains before S7.

#67 adds the [local security matrix](security/local-mvp-matrix.md) and [canary/disclosure evidence](../evaluation/reports/local_security_v1/README.md). The full required command passes 46 unit, 119 contract and 220 integration cases plus installed-wheel checks. Hardened canary cases and one added negative control pass focused checks; all 221 current integration cases have passing results across those runs. No runtime authority/budget change, paid call or human support judgment was introduced. Local trusted composition and scripted tests do not establish operational authentication or real-model resistance.

## Next work

The owner [selected the S6/S7 gate split](adr/0022-sprint-06-readiness-and-sprint-07-diagnostics.md): S6 local readiness/handoff, S7 actual-provider diagnostic acceptance, S8 hosted delivery and S9 Cloud MVP acceptance. This is sequencing, not a release approval or a passing fake-provider quality result.

1. Record the unresolved details and owner handoff decision in the [Sprint 6 review](sprints/sprint-06-review.md); a closed issue and merged documentation do not supply them.
2. In S7, [#87 actual Azure comparisons](https://github.com/krispykrits/TRACE/issues/87) provide the artifacts for #65 actual owner quality review and the Local MVP diagnostic decision. The [read-only preflight](../evaluation/README.md#azure-comparison-preflight) inspects local accounting but always blocks live dispatch; the live composition and its use of shared run-level enforcement remain unimplemented. Verify actual provider/spending/source/transmission/run facts before separately authorized dispatch. #55 architecture/design can proceed in parallel; resize the added S7 scope rather than inventing capacity.
3. S8–S9 [#55–#60 cloud delivery](planning/azure-cloud-backlog.md) and [#70–#76 monitored services](planning/dotnet-testbed-backlog.md) retain their contracts, hosted-acceptance and independent-usefulness gates.

## Acceptance still pending

- **S6 local readiness:** completed local security, review workflow/setup/runbook evidence and explicit owner handoff.
- **Local MVP diagnostic acceptance (S7):** live comparison composition, actual authorized model measurements, actual owner support review and applicable quality/latency/cost decision.
- **Cloud MVP:** Azure/AKS resources, shared PostgreSQL/admission, pod identity, hosted telemetry, restore and teardown.
- **Operational Pilot:** permitted representative sources, historical replay/read-only shadow use and measured operator benefit.
- **Full capstone:** justified evaluated ML, five-arm study, ranked response contract, hardened operations and defense.
- **Production remediation:** concrete authorized workload/action, staging validation and explicitly approved verified production execution.

The owner is the planned .NET service owner and initial investigator. Exact source/field/transmission/retention policy, infrastructure budget/resources, remaining review/release/study thresholds, university rubric/deadline and capacity remain [charter inputs](charter.md#open-inputs-and-decision-gates). The $20/month application model cap is separate from Azure infrastructure/account billing.

## Read next

[Documentation map](README.md) · [Charter](charter.md) · [Delivery plan](planning/capstone-project-plan.md) · [Current architecture](architecture/README.md) · [ADR index](adr/README.md)

Historical merge/test details belong in their PRs, capability guides, ADRs and dated sprint snapshots. A synthetic demonstration, green CI or accepted planning record does not establish operational or release acceptance.
