# TRACE current status

Updated: 2026-10-15 against #38 merge `71de366` / PR #82 and live Project Done; #39 has a verified offline run; implementation/support review is pending. [Project Status](https://github.com/users/krispykrits/projects/2) remains authoritative for work status.

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

Merged [PR #82](https://github.com/krispykrits/TRACE/pull/82) provides captured-window CLI investigation, protected saved display/citation/export and cancellation with original dependency/clearance/retention and current support checks. #39 adds actual-output scoring, saved-artifact rescoring and bound review samples. Its [retained run](../evaluation/reports/investigator_offline_v1/manifest.json) passed 10/10 expected offline checks with zero critical boundary failures; the [Sprint 5 review](sprints/sprint-05-review.md) retains the wrong fixture cause scores and ten unreviewed sampled claims. The scoped PR remains open for implementation/support review. No paid end-to-end diagnosis or actual human support is claimed.

## Next work

1. Review/complete [#39 actual-output scoring/integration](https://github.com/krispykrits/TRACE/issues/39), retaining explicit live-diagnosis and actual human-review blockers.
2. Execute the separate Sprint 6 acceptance track [#63–#68](planning/capstone-project-plan.md#backlogs-and-dependencies), after declaring thresholds, authorized run scope and actual review coverage.
3. Follow [#55–#60](planning/azure-cloud-backlog.md) and [#70–#76](planning/dotnet-testbed-backlog.md) for cloud delivery and monitored services, in their recorded dependency order.

## Acceptance still pending

- **Local MVP:** #39 handoff and the S6 protocol, comparisons, human support review, reliability/security checks and release decision.
- **Cloud MVP:** Azure/AKS resources, shared PostgreSQL/admission, pod identity, hosted telemetry, restore and teardown.
- **Operational Pilot:** permitted representative sources, historical replay/read-only shadow use and measured operator benefit.
- **Full capstone:** justified evaluated ML, five-arm study, ranked response contract, hardened operations and defense.
- **Production remediation:** concrete authorized workload/action, staging validation and explicitly approved verified production execution.

The owner is the planned .NET service owner and initial investigator. Exact source/field/transmission/retention policy, infrastructure budget/resources, remaining review/release/study thresholds, university rubric/deadline and capacity remain [charter inputs](charter.md#open-inputs-and-decision-gates). The $20/month application model cap is separate from Azure infrastructure/account billing.

## Read next

[Documentation map](README.md) · [Charter](charter.md) · [Delivery plan](planning/capstone-project-plan.md) · [Current architecture](architecture/README.md) · [ADR index](adr/README.md)

Historical merge/test details belong in their PRs, capability guides, ADRs and dated sprint snapshots. A synthetic demonstration, green CI or accepted planning record does not establish operational or release acceptance.
