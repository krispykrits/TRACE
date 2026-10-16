# TRACE current status

Updated: 2026-10-16 against main `2679d52` and live Project Status: #39 / PR #83 is merged and Done; #63 protocol preparation is proposed for owner review. [Project Status](https://github.com/users/krispykrits/projects/2) remains authoritative for work status.

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

#63 prepares the [Local MVP acceptance protocol](planning/local-mvp-acceptance.md), explicit pending owner decisions and a private hash-bound cost/schedule dry run. No provider calls or acceptance measurements are made. Numeric release thresholds, repeats/review coverage, resources/retention, current provider/spending and separately approved live-run scope remain blockers before acceptance execution.

## Next work

1. Review [#63 protocol preparation](https://github.com/krispykrits/TRACE/issues/63) and obtain the missing owner decisions before acceptance measurement.
2. Continue Sprint 6 [#64–#68](planning/capstone-project-plan.md#backlogs-and-dependencies): comparisons, actual independent review, recovery/security evidence and release decision.
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
