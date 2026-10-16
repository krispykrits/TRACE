# TRACE architecture

This guide describes the current modular application. The [root end-state diagram](../../README.md#end-state-architecture) shows the planned final product; [current status](../current-status.md) records implementation/release progress.

## Current implementation

~~~mermaid
flowchart TD
    CLI["Public CLI"] --> Demo["Configuration and synthetic replay"]
    CLI --> Composition["Explicit bootstrap composition"]
    Script["Developer workflow demo"] --> Composition
    Composition --> Saved["Current-authority saved inspection/export"]
    Saved --> Evidence
    Composition --> Investigation["Bounded investigation"]
    Investigation --> Tools["Read-only tool catalog"]
    Tools --> Evidence["SQLite evidence and job adapters"]
    Tools --> Knowledge["Authorized retrieval and quoted context"]
    Knowledge --> Corpus["SQLite corpus and local index adapters"]
    Investigation --> Policy["Policy-admitted model provider"]
    Policy --> Azure["Azure transport and private spending journal"]
    Investigation --> Publication["Protected assessment and private publication"]
    Publication --> Evidence
~~~

The investigation use case is merged in [PR #62](https://github.com/krispykrits/TRACE/pull/62). Its offline demo uses actual local storage/tool boundaries with hand-authored model/review records. The separate synthetic Azure connector check establishes its native contract, not end-to-end diagnostic quality.

The runtime is one Python package, not independently deployed TRACE microservices. Core contracts/use cases are independent of frameworks and concrete systems; bootstrap selects adapters. [Package layout](package-layout.md) and [ADR 0010](../adr/0010-capability-packages-and-adapter-boundaries.md) define and enforce dependency direction.

## Interfaces

| Surface | Current boundary |
| --- | --- |
| Public `trace-app` CLI | Help/version, configuration, synthetic replay, captured-window investigation, protected report access and cancellation; [development guide](../development.md#public-cli) |
| Developer scripts | Local persistence/search/context/tools/integration/investigator demonstrations with fixed synthetic grants; outside the runtime wheel |
| Internal Python application | Scoped evidence/query/timeline/retrieval/tool/provider/assessment/execution/workflow contracts composed explicitly |
| Local investigation/inspection/export | [CLI contract](investigator-cli.md): trusted local profile, original dependency/clearance and current source/transmission/support checks; operational authentication remains gated |
| Operational sources | Planned protected JSON import, then bounded live Azure queries under [the .NET backlog](../planning/dotnet-testbed-backlog.md) |
| Network API/UI | No public HTTP service or dashboard selected; requires measured need and an ADR |
| Operational response | Planned ranked options and explicitly approved deterministic catalog execution; [ADR 0018](../adr/0018-flexible-ml-and-ranked-response-options.md) |

Corpus publication, withdrawal and retention purge are trusted administration, not model tools. CLI filters or file paths never supply authorization. Current next-check proposals cannot execute writes or grant remediation authority.

## Capability contracts

| Capability | Detailed guides |
| --- | --- |
| Evidence and scenarios | [Data contracts](data-contracts.md), [Order workflow](order-payment-workflow.md), [replay envelope](dependency-replay-evidence.md), [development scenarios](development-scenarios.md) |
| Persistence and observation | [SQLite state](sqlite-investigation-store.md), [bounded queries](bounded-evidence-queries.md), [timelines](incident-timelines.md) |
| Knowledge | [Corpus](knowledge-corpus.md), [retrieval](knowledge-retrieval.md), [passage evaluation/context](retrieval-evaluation-context.md) |
| Tools and integration | [Read-only catalog](investigation-tools.md), [scripted cited package](scripted-evidence-package.md) |
| AI investigation | [Provider/data policy](model-provider.md), [validated assessments](validated-assessments.md), [shared execution budgets](investigation-budgets.md), [bounded investigator](bounded-investigator.md) |
| Evaluation | [Actual investigator outputs](investigator-evaluation.md), [Development contracts](development-evaluation.md), [artifact/reproduction guide](../../evaluation/README.md) |
| Hosting and operation | [Azure cloud design](azure-cloud.md), [deployment](../../deploy/README.md), [operations](../operations/README.md), [security](../security/README.md) |

## Planned boundaries

Azure/containers/AKS, shared PostgreSQL/pgvector and hosted telemetry follow [ADR 0015](../adr/0015-azure-aks-cloud-deployment.md). Resources, migration/shared admission, pod identity, restore and hosted acceptance remain #55–#60.

Independent .NET Order/Payment workloads follow [ADR 0017](../adr/0017-dotnet-testbed-and-json-first-evidence.md). Exported JSON precedes scoped live Azure evidence queries. The monitored services are separate from TRACE's Python runtime and its own application logs.

A justified evaluated ML capability can use classical ML, deep learning, pretrained or other suitable methods. The final product ranks applicable responses and marks the recommendation with evidence/uncertainty, benefit, risks, prerequisites and verification/recovery. Recommendations, engineer selection, reviewed code delivery and approved operational execution remain distinct.

The initial investigator remains read-only. A separate deterministic executor retains concrete approval, state revalidation, finite execution, reconciliation, outcome verification and audit under [the remediation scope](../planning/production-remediation-scope.md).

## Decisions and history

[ADR index](../adr/README.md) · [Delivery plan](../planning/capstone-project-plan.md) · [Historical reviews](../archive/README.md)

The [local investigator CLI and saved access contract](investigator-cli.md) covers captured-window commands, trusted profile configuration, private exports and restart/cancellation behavior.
