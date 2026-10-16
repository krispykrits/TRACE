# TRACE current status

Updated: 2026-10-16 against main `e45186d` and live Project Status: #63 / PR #85 is merged and Done; #64 comparisons are In review. [Project Status](https://github.com/users/krispykrits/projects/2) remains authoritative for work status.

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

#63 / [PR #85](https://github.com/krispykrits/TRACE/pull/85) records [owner-approved Local MVP settings](planning/local-mvp-owner-decisions-2026-10-16.md): three repeats, 36 attempts, $1 planning allowance, full integrated-output review by the owner alone and resource/retention expectations. Protocol/decisions v2 preserve the original v1 artifacts and label single-owner provenance. Actual provider/spending/source/run metadata, cleanup ownership, final run bindings and #64–#68 implementation/evidence remain gates. No paid run or new human verdict is recorded.

#64's comparison implementation now executes and rescores all 36 offline attempts under exact bound inputs. The [retained comparison](../evaluation/reports/local_mvp_comparison_offline_v1/README.md) records 12/12 completed brief-only references, 12/12 completed deterministic bundles and 0/12 completed integrated attempts: all exhaust the approved 20-call tool ceiling. Saved rescoring is byte-identical with no dispatch. This is a negative contract finding, not Azure diagnosis or release acceptance; paid calls and new human verdicts remain zero.

The owner [approved 40 tool calls](planning/local-mvp-tool-budget-adjustment-2026-10-16.md) after capacity probes measured 23–30 calls. Decision revision v3 preserves all other limits and gates; a fresh 36-attempt offline comparison is being prepared. Original v2 inputs and the failed frozen comparison remain unchanged.

## Next work

1. Review [#64 comparisons](https://github.com/krispykrits/TRACE/issues/64), retaining offline contract results and named live-measurement blockers. Complete the remaining factual/authority/freeze gates before paid acceptance measurement.
2. Continue Sprint 6 [#64–#68](planning/capstone-project-plan.md#backlogs-and-dependencies): comparisons, actual owner review, recovery/security evidence and release decision.
3. Follow [#55–#60](planning/azure-cloud-backlog.md) and [#70–#76](planning/dotnet-testbed-backlog.md) for cloud delivery and monitored services, in their recorded dependency order.

## Acceptance still pending

- **Local MVP:** approved S6 protocol/owner inputs, comparisons, human support review, reliability/security checks and release decision.
- **Cloud MVP:** Azure/AKS resources, shared PostgreSQL/admission, pod identity, hosted telemetry, restore and teardown.
- **Operational Pilot:** permitted representative sources, historical replay/read-only shadow use and measured operator benefit.
- **Full capstone:** justified evaluated ML, five-arm study, ranked response contract, hardened operations and defense.
- **Production remediation:** concrete authorized workload/action, staging validation and explicitly approved verified production execution.

The owner is the planned .NET service owner and initial investigator. Exact source/field/transmission/retention policy, infrastructure budget/resources, remaining review/release/study thresholds, university rubric/deadline and capacity remain [charter inputs](charter.md#open-inputs-and-decision-gates). The $20/month application model cap is separate from Azure infrastructure/account billing.

## Read next

[Documentation map](README.md) · [Charter](charter.md) · [Delivery plan](planning/capstone-project-plan.md) · [Current architecture](architecture/README.md) · [ADR index](adr/README.md)

Historical merge/test details belong in their PRs, capability guides, ADRs and dated sprint snapshots. A synthetic demonstration, green CI or accepted planning record does not establish operational or release acceptance.
