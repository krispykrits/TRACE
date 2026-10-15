# TRACE current status

Verified: 2026-10-15 against main `698c56b`, repository source, merged PR history and open issues. [Project Status](https://github.com/users/krispykrits/projects/2) remains authoritative for work status.

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

The public CLI currently exposes configuration and synthetic workflow/replay commands. The investigation use case is an internal Python composition with a developer demonstration. Investigator-facing inspection/export and end-to-end actual-output scoring remain open.

## Next work

1. Complete Sprint 5 [#38 CLI and protected report access](https://github.com/krispykrits/TRACE/issues/38) and [#39 actual-output scoring/integration](https://github.com/krispykrits/TRACE/issues/39).
2. Execute the separate Sprint 6 acceptance track [#63–#68](planning/capstone-project-plan.md#backlogs-and-dependencies), after declaring thresholds, authorized run scope and actual review coverage.
3. Follow [#55–#60](planning/azure-cloud-backlog.md) and [#70–#76](planning/dotnet-testbed-backlog.md) for cloud delivery and monitored services, in their recorded dependency order.

## Acceptance still pending

- **Local MVP:** #38/#39 handoff and the S6 protocol, comparisons, human support review, reliability/security checks and release decision.
- **Cloud MVP:** Azure/AKS resources, shared PostgreSQL/admission, pod identity, hosted telemetry, restore and teardown.
- **Operational Pilot:** permitted representative sources, historical replay/read-only shadow use and measured operator benefit.
- **Full capstone:** justified evaluated ML, five-arm study, ranked response contract, hardened operations and defense.
- **Production remediation:** concrete authorized workload/action, staging validation and explicitly approved verified production execution.

The owner is the planned .NET service owner and initial investigator. Exact source/field/transmission/retention policy, infrastructure budget/resources, remaining review/release/study thresholds, university rubric/deadline and capacity remain [charter inputs](charter.md#open-inputs-and-decision-gates). The $20/month application model cap is separate from Azure infrastructure/account billing.

## Read next

[Documentation map](README.md) · [Charter](charter.md) · [Delivery plan](planning/capstone-project-plan.md) · [Current architecture](architecture/README.md) · [ADR index](adr/README.md)

Historical merge/test details belong in their PRs, capability guides, ADRs and dated sprint snapshots. A synthetic demonstration, green CI or accepted planning record does not establish operational or release acceptance.
