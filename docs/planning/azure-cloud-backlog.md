# Azure and AKS Cloud MVP backlog

Owner cloud direction and document/story update authorized on 2026-10-14; planning task [#54](https://github.com/krispykrits/TRACE/issues/54). [ADR 0015](../adr/0015-azure-aks-cloud-deployment.md), [charter](../charter.md), [architecture](../architecture/azure-cloud.md) and [roadmap #9](https://github.com/krispykrits/TRACE/issues/9) govern this refinement. No implementation, live resources or calendar commitment follows from creating these stories.

| Issue | Native sprint milestone | Work |
| --- | --- | --- |
| [#55](https://github.com/krispykrits/TRACE/issues/55) | S7 | Design the Terraform-managed Azure and AKS Cloud MVP |
| [#56](https://github.com/krispykrits/TRACE/issues/56) | S8 | Build a reproducible TRACE container and publish immutable images to ACR |
| [#57](https://github.com/krispykrits/TRACE/issues/57) | S8 | Migrate shared TRACE state and spending reservations to Azure PostgreSQL |
| [#58](https://github.com/krispykrits/TRACE/issues/58) | S8 | Run the bounded TRACE workflow on AKS with workload identity and reviewed releases |
| [#59](https://github.com/krispykrits/TRACE/issues/59) | S8 | Deliver redacted TRACE telemetry to Azure Monitor and Log Analytics |
| [#60](https://github.com/krispykrits/TRACE/issues/60) | S9 | Verify Azure AKS Cloud MVP recovery, security, costs and teardown |

## Dependency and acceptance order

S6 accepts the local investigator before cloud implementation acceptance. #55 reviews Azure design and unresolved account/budget/region/retention inputs. #56 packages/publishes the existing modular runtime; #57 supplies shared PostgreSQL state/admission. #58 depends on both and verifies authorized AKS delivery. #59 records collection design alongside S7 and requires #58 for hosted evidence. #60 accepts the complete S8 release after fault/access/cost/restore/teardown demonstrations.

These are concrete user stories with acceptance/verification in the linked issues; do not duplicate them as placeholders. Re-size/split if capacity requires, updating dependencies and release gates together. Native milestone numbers 7/8/9 are retained and remain undated. The Project at [the owner's roadmap view](https://github.com/users/krispykrits/projects/2/views/4) remains authoritative for Status and Release. On 2026-10-14, #55-#60 were verified as **Backlog** / **Cloud MVP**, with no iteration assigned; planning #54 is **In review** / **Cloud MVP** and linked to PR #61. Future work requires live status verification, and milestone membership never implies implementation acceptance.

## Native sprint titles and goals

The owner explicitly requested replacement of AWS sprint titles/goals on 2026-10-14. These titles, goals and exit criteria are updated and verified in the existing native milestones; their numeric identities, dependencies and undated scheduling are retained. Corresponding Project stories carry the Cloud MVP release and future-work status described above.

| Milestone | Verified title | Goal and deliverables | Exit gate and dependencies |
| --- | --- | --- | --- |
| [7](https://github.com/krispykrits/TRACE/milestone/7) | Sprint 07 - Azure AKS design and IaC | #55: measured-workload Terraform Azure/AKS design, cluster/runtime, ACR/PostgreSQL/pgvector, Workload Identity/Key Vault, network/state, telemetry, costs/retention, migration/restore and teardown | Reviewed design/plan and scoped authority/cost assumptions, with owner inputs recorded and no apply during design; depends on S6 |
| [8](https://github.com/krispykrits/TRACE/milestone/8) | Sprint 08 - Containerized AKS deployment and CI/CD | #56-#59: reproducible non-root ACR image, shared Azure PostgreSQL/journals, pod Workload Identity, digest promotion/rollback, lifecycle/resources and redacted Azure telemetry | Accepted synthetic AKS investigation, source/citation/review protection, shared monetary admission and pod/attempt recovery, hosted logs and rollback evidence; depends on S7 and accepted Local MVP |
| [9](https://github.com/krispykrits/TRACE/milestone/9) | Sprint 09 - Azure Cloud MVP acceptance | #60: fault/security/concurrency/cost/retention, migration/restore/vector rebuild, operations, release rollback and teardown/recreation | No duplicate unbudgeted dispatch; recovered/restored/recreated environment, real hosted telemetry and residual-resource accounting; depends on S8 and remains distinct from Operational Pilot/remediation |

## Mandatory cloud behavior

- Promote reviewed ACR image digests with reproducible locked runtime inputs, non-root execution, provenance/SBOM/scan evidence and evaluator/credential exclusion.
- Use scoped Entra Workload Identity for the pod; separate deployment, node/pull, model/source/database and telemetry authority. Human portal login or the cluster identity does not establish app inference readiness.
- Migrate shared evidence, corpus/policy versions, attempts/leases, protected response/review state and provider/execution monetary reservations. Prove admission across simultaneous jobs and pod replacement before concurrent paid workloads.
- Preserve independent source/transmission access, citation/revocation/review/export protection, deadlines/retries and unknown-usage reconciliation. Kubernetes backoff cannot bypass the app's admission policy.
- Verify redacted hosted logs, actual known usage and unknowns, reader access/retention and collector recovery; retain a tested immutable release rollback and database restore/rebuild path.
- Keep Azure infrastructure costs separate from the $20/month model cap. Resolve sizing/region/budget/retention and review Terraform plan before apply; record retained state/backups/logs and residual charges during teardown/recreation.

## Historical work and platform replacement

Historical #1/#3/#6/#10/#16/#29 retain their earlier local/decision acceptance and state. Their AWS-hosting directions are superseded by ADR 0015 and these cloud stories. In particular #3's closed state is not CloudWatch hosted-delivery evidence; Azure logging acceptance belongs to #59. The legacy deploy/cloudwatch example is historical and not the Azure deployment path. Existing Local MVP boundaries and final Operational Pilot/remediation gates remain in force.

## .NET monitored workload addition — 2026-10-14

The owner approved lightweight .NET Order/Payment services, exported JSON first then live Azure queries, and the owner as service owner/initial investigating engineer. [ADR 0017](../adr/0017-dotnet-testbed-and-json-first-evidence.md) and [the testbed backlog](dotnet-testbed-backlog.md) refine S7 #69-#72, S8 #73-#75 and S9 #76 alongside the existing cloud work. Keep TRACE one Python application and preserve frozen Local MVP evidence. The new track owns monitored workload telemetry and protected source ingestion; #59 remains TRACE's own observability acceptance. Native milestones stay undated; resize capacity and keep exact field/retention/access, infrastructure spending and usefulness/review thresholds explicit. Generated-fault replay/shadow findings remain controlled-testbed evidence, with independent Operational Pilot and production-remediation gates retained.
