# .NET monitored testbed and source-integration backlog

Owner direction approved on 2026-10-14: lightweight .NET Order and Payment services; exported JSON first, then live Azure queries; project owner (`krispykrits`) is service owner and initial investigating engineer. [Planning #69](https://github.com/krispykrits/TRACE/issues/69) and [ADR 0017](../adr/0017-dotnet-testbed-and-json-first-evidence.md) record the decision. TRACE remains one Python application; these are the workloads it monitors.

| Issue | Existing milestone | Deliverable |
| --- | --- | --- |
| [#69](https://github.com/krispykrits/TRACE/issues/69) | S7 | Record direction, ownership, boundaries and refinement |
| [#70](https://github.com/krispykrits/TRACE/issues/70) | S7 | Local independently running .NET Order → Payment services |
| [#71](https://github.com/krispykrits/TRACE/issues/71) | S7 | Correlated logs/measurements/revisions and versioned JSON exports |
| [#72](https://github.com/krispykrits/TRACE/issues/72) | S7 | Bounded workloads and controlled Payment incident recordings |
| [#73](https://github.com/krispykrits/TRACE/issues/73) | S8 | Protected source-neutral JSON import into TRACE |
| [#74](https://github.com/krispykrits/TRACE/issues/74) | S8 | Reviewed .NET containers/AKS delivery and actual Azure workload telemetry |
| [#75](https://github.com/krispykrits/TRACE/issues/75) | S8 | Bounded read-only Azure evidence queries after JSON acceptance |
| [#76](https://github.com/krispykrits/TRACE/issues/76) | S9 | Manual versus TRACE replay and live read-only shadow comparison |

All use existing Cloud MVP/sprint/type labels and native milestone identities. [Project Status/Release](https://github.com/users/krispykrits/projects/2/views/4) remains authoritative; no iteration/date/estimate or implementation acceptance is implied. Resize against capacity rather than assuming these additions fit unchanged sprint estimates.

## Dependency and delivery order

Issue #70 follows #69's direction and supplies two genuine process/network boundaries. #71 adds observed telemetry and source-owned export identity; #72 produces versioned healthy, delayed/timeout, harmless deployment-distractor and partial-capture recordings. #73 imports those artifacts behind current TRACE contracts and source/transmission protections. Existing #38/#39 complete the CLI/scoring handoff; #63-#68 retain the separate Local MVP gate.

Issue #55 reviews Azure account/budget/resource/network/identity design and incorporates the measured .NET workload before hosting. #74 deploys the accepted testbed and verifies its telemetry, coordinating existing #56/#58/#59 platform/release conventions. #75 adds scoped live read queries after #73's JSON source semantics and #74's hosted source are accepted. #76 can prepare/perform declared JSON replay once its prerequisites exist, then completes the live shadow phase after #74/#75; its S9 grouping is a scope target, not a committed date.

Existing #55-#60 still own TRACE's cloud design, shared state/admission, runtime deployment, own telemetry and cloud acceptance. This testbed track supplies an additional monitored workload and usefulness evidence; #59's application logs are not themselves the .NET incident source. #76, #60, the independent Operational Pilot and final production-remediation gate remain distinct acceptance claims.

## Placement and behavior

- Place future .NET source/tests/build settings under `testbed/dotnet/`; pin a supported SDK/dependencies and use a separate .NET CI lane. Keep it outside the Python wheel; add no empty scaffold in this planning PR.
- Begin with two services and fictional payment authorization. Use bounded HTTP timeouts/cancellation/workloads and fault controls disabled by default in explicit test environments. No real money/customer data or additional business platform is required.
- Export genuine observations, measurements, deployment revisions and missing-data status. Preserve original record/revision, event/collection time, environment/correlation and declared units/window. Preserve actual variation across executions; saved artifacts remain immutable/rescorable.
- Keep injected cause/schedule/expected answers and evaluator judgments separate from service/export manifests, runtime images, corpus, tool results and model prompts. Use a new controlled cohort and preserve frozen Local MVP reports.
- Authorize file/source reads independently, then retain current source/transmission/revocation/redaction/citation/review/output protection across both JSON and Azure adapters. Imports/query filters never grant authority and failures never silently use fixtures.
- Keep collection/write, deployment, scoped investigation-read, fault control and final remediation permissions separate. Fixed bounded Azure queries expose no arbitrary KQL/workspace selection or administration to the model.
- Preserve the $20/month model cap and shared admission across hosted jobs. Infrastructure and telemetry/query spending, retention, subscription/region/resource shape and live access remain separately recorded gates.

## Ownership and claim limits

The project owner runs the services and acts as the first manual investigator. Before measurements, #76 records the manual workflow, incident briefs/order/repeats, comparison/review coverage and applicable owner-approved thresholds. Save both findings before revealing expected causes; preserve support/disagreement/unknown-usage/failure denominators and disclose single-operator/familiarity bias.

The runbook names responsibility for field/transmission policy, credentials, cost stops, retention/deletion, support, source/collector interruption and recovery. Actual recording permissions and exact policy values are established during implementation; the role decision is not a blanket grant to external data or Azure administration.

Generated faults prove controlled testbed behavior. Broader Operational Pilot usefulness requires representative authorized operational evidence, operator-reviewed benefit and declared access/reliability/cost/support gates. Real production remediation additionally requires an operational-purpose workload, staging validation and exact action approval; testbed fault controls do not satisfy that requirement.
