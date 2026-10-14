# ADR 0017: .NET monitored testbed and JSON-first evidence ingestion

- **Status:** Accepted owner direction, 2026-10-14; implementation and testbed usefulness pending
- **Decision owner / service owner / initial investigating engineer:** Project owner (`krispykrits`), explicitly confirmed
- **Planning task:** [#69](https://github.com/krispykrits/TRACE/issues/69)
- **Delivery:** [S7-S9 testbed backlog](../planning/dotnet-testbed-backlog.md), #70-#76
- **Relationship:** Extends the monitored-workload/source direction without replacing ADR 0010's modular Python TRACE runtime, ADR 0015's Azure/AKS target or ADR 0004's accepted in-process synthetic fixture history.

## Context

The owner selected lightweight .NET services to supply independently running monitored workloads, accepted exported JSON before live Azure queries, confirmed ownership/operator roles and requested stories for the controlled Order → Payment latency/timeout example. Existing TRACE evidence, tools, storage, budgets and protected assessments are implemented around local synthetic fixtures; they do not already collect evidence from these planned services.

The independent Operational Pilot requires permitted sources, a named operator, measured usefulness and operating ownership. Naming the owner resolves a role input for this testbed. It does not provide source credentials, completed recordings, retention values, measured thresholds or acceptance evidence.

## Decision

Build two small ASP.NET Core Order and Payment workloads, initially local and subsequently containerized on AKS. Use fictional payment authorization and bounded traffic/fault controls in an explicitly selected test environment. Review and pin the supported .NET LTS SDK and dependencies in #70; no SDK/package version is selected or installed by this record.

The .NET source and its own tests/build settings belong under `testbed/dotnet/` when implemented. Do not add empty scaffolding now. This path is outside `src/trace_app`, the Python wheel and core dependency graph. TRACE remains one modular Python application; the separate workload processes create the network/telemetry boundary being investigated. Customer/Notification expansion, a broker, business database or public TRACE API requires measured need and a separate scoped decision.

| Boundary | Direction | Story |
| --- | --- | --- |
| Monitored workload | Small independently running .NET Order → Payment HTTP path, explicit cancellation/timeouts and synthetic outcomes | #70 |
| Telemetry/export | Structured redacted logs, actual measurements, deployment/configuration revision and distributed correlation; bounded versioned source-owned JSON | #71 |
| Workload/incidents | Finite request schedule, healthy and Payment degradation/timeout, harmless actual deployment distractor, honest partial capture | #72 |
| First TRACE source | Protected JSON file reader/normalizer behind TRACE-owned evidence contracts and bootstrap | #73 |
| Hosted workload | Reviewed immutable .NET images, restricted AKS testbed, actual scoped Azure telemetry and teardown | #74 |
| Later TRACE source | Fixed bounded read-only Azure queries with scoped workload identity and the same evidence/source-policy semantics | #75 |
| Usefulness evidence | Owner-led manual versus TRACE replay, followed by live read-only shadow evaluation | #76 |

## Source and authority boundaries

Preserve source-owned record/revision and resource identity, event versus collection UTC time, service/environment, correlation, units/windows, completeness and stable citations. #71/#73 define the exact wire-to-existing-contract mapping; raw OpenTelemetry JSON is not assumed to be a TRACE envelope. Additional record kinds need a reviewed schema change. Integrity hashes detect alterations relative to a recorded artifact; they do not authenticate a source or grant access.

File paths, imported classifications, caller filters and model text cannot supply source/transmission grants. Independent trusted composition derives current read, field/redaction, revision/expiry and Azure Foundry transmission rights. Apply existing provider policy, spending/execution admission, citation/review and input-derived output sensitivity to both source paths. Missing/partial/late data and dependency errors remain explicit; no silent fixture fallback.

For Azure, separate testbed collection/write, scoped TRACE query/read, deployment, fault-driver and future remediation authority. Use fixed typed queries with finite scope/time/result/byte/deadline/retry limits; expose no arbitrary KQL or source administration to the model. TRACE's own telemetry acceptance in #59 remains distinct from observed .NET workload telemetry in #74/#75.

## Evaluation and operations

Injection schedules, fault selectors, expected causes and reviewer judgments remain evaluator-only, outside telemetry/export/ingestion/retrieval/prompts and runtime images. Use a new versioned controlled-testbed cohort; preserve the existing frozen synthetic reports and source hashes. Genuine execution times and IDs can vary across repetitions; reproducing saved scores requires no new provider call.

The owner is the initial service operator and manual investigator. #76 predeclares task scope, comparison order/repeats, actual review coverage and usefulness/quality/reliability/latency/cost criteria, then records manual findings and TRACE outputs before revealing evaluator answers. Disclose owner familiarity and single-operator bias; independent human review cannot be fabricated or replaced by scripted decisions.

Record field classification/transmission, retention/deletion, support/recovery, SDK/source mapping and resource/cost choices in the scoped implementation. The $20/month model cap remains separate from Azure infrastructure and telemetry/query costs. Missing exact values or actual live evidence remains a blocker for the relevant acceptance, not for this planning refinement.

Generated-incident results establish controlled testbed evidence. Independent Operational Pilot usefulness and real production remediation retain their own gates for representative operational-purpose workloads, access, review and outcomes. Do not induce a production outage to obtain evidence, or treat a testbed fault control as TRACE remediation authority.

## Alternatives and revisit conditions

- Retain only Python in-process fixtures: useful for deterministic Local MVP regression, but does not exercise the selected independent .NET process/network source boundary.
- Begin with live Azure ingestion: adds deployment/identity/collection dependencies before the source mapping can be verified; the owner selected JSON first.
- Split TRACE into .NET/Python microservices or add more workload services: not selected; the two monitored services do not require changing the investigator's modular architecture.

Revisit workload size, transport/retention, source mapping or hosting only from measured scenario/operating needs and a recorded owner decision. No runtime code, dependency, resource, paid request or fault execution is introduced by accepting this direction.

## References

[Charter](../charter.md), [source envelope](../architecture/dependency-replay-evidence.md), [package boundaries](../architecture/package-layout.md), [Azure architecture](../architecture/azure-cloud.md), [development comparison protocol](../architecture/development-evaluation.md), [.NET observability](https://learn.microsoft.com/en-us/dotnet/core/diagnostics/observability-with-otel), [Azure Logs query API](https://learn.microsoft.com/en-us/azure/azure-monitor/logs/api/overview), [query scope/time](https://learn.microsoft.com/en-us/azure/azure-monitor/logs/scope).
