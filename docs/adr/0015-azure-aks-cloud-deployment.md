# ADR 0015: Azure, containers and AKS for the Cloud MVP

- **Status:** Accepted owner cloud direction, 2026-10-14; resource design, implementation and hosted acceptance pending
- **Date:** 2026-10-14
- **Decision owner:** Project owner
- **Planning task:** [#54](https://github.com/krispykrits/TRACE/issues/54)
- **Supersedes:** ADR 0002's EC2/AWS target and ADR 0003's CloudWatch platform; replaces the RDS hosting portions of ADRs 0005/0006. Terraform, Local SQLite, PostgreSQL and pgvector semantics remain.

## Context

The owner selected Azure instead of AWS and containerized deployment on AKS, then requested document and user-story updates. The existing charter, cloud roadmap and deployment guidance still pointed to EC2, RDS and CloudWatch. Those were planning directions; no EC2 application runtime, RDS migration or CloudWatch hosted-delivery acceptance was established. Preserve the earlier decision history and local acceptance evidence while replacing future cloud work.

TRACE remains one modular Python application. The existing Local MVP uses a CLI, SQLite evidence/job/corpus state and private provider/execution journals. Azure AI Foundry / GPT-6 Luna is the accepted synthetic provider boundary, with a $20/month application model cap and owner-approved transmission policy. AKS does not supply shared application transactions, monetary admission, source permission or production usefulness by itself.

## Decision

Use Terraform for Azure infrastructure and deploy the existing application as an immutable container on AKS during S7-S9. Use the following Azure planning baseline; exact resource shape remains the S7 design gate.

| Boundary | Cloud direction | Acceptance ownership |
| --- | --- | --- |
| Compute | AKS with the same modular TRACE application | #55 design, #58 deployment, #60 acceptance |
| Artifact | Azure Container Registry; promote a reviewed image digest | #56 image/registry |
| Shared durable state | Azure Database for PostgreSQL Flexible Server; pgvector for cloud retrieval | #57 migration, concurrency and recovery |
| Model inference | Existing Azure AI Foundry / GPT-6 Luna deployment through the TRACE provider boundary | #58 cloud identity/capability check; #34 local acceptance retained |
| Application identity/secrets | Entra Workload Identity bound to the AKS service account; scoped Foundry/Key Vault access | #55 authority design, #58 implementation |
| Telemetry | Structured redacted stdout/stderr through platform-managed collection to Azure Monitor / Log Analytics | #59 hosted acceptance |
| Infrastructure lifecycle | Terraform Azure providers and a reviewed Azure Blob state/locking/access design | #55; plan/apply and app promotion remain separate |

Cloud design evaluates AKS mode/tier/version/node pools, networking/egress, ACR and database shape, retention, availability and owner costs from measured needs. These values are not selected by this ADR. CLI execution as a bounded Kubernetes Job is the first shape to review; a long-running worker/API requires explicit contracts and justification. Containerization does not authorize a microservice split, public HTTP API, UI, broker, service mesh or new autonomous loop.

## Required boundaries

- Preserve source-neutral contracts, evaluator exclusion from the runtime image, independent source/transmission authorization, citation/revision integrity, protected responses/reviews, and read-only investigation. Azure hosting does not authorize real operational data or remediation.
- Separate CI/Terraform deployment authority, cluster/node/image-pull identity, app workload identity, database migration/admin roles and log reader/collector permissions. A Foundry resource identity or human portal role is not the pod's caller identity. Cloud Workload Identity must be implemented and verified; local resource-key fallback is not evidence of cloud keyless readiness.
- Keep durable evidence, job leases/attempts, corpus/policy generations, review bindings and provider/execution spending reservations in shared storage. An independent SQLite file or $20 journal in each pod cannot enforce a shared cap. Prove atomic admission and conservative reconciliation across simultaneous jobs and pod replacement before enabling concurrent paid investigations.
- Kubernetes restart/backoff must obey application retry, deadline and spending admission. A killed worker or lost response is an uncertain attempt; do not blindly replay an already dispatched model request or duplicate an operational action.
- Use reproducible non-root images, image provenance/SBOM/scan evidence, appropriate pod security/resources, controlled secret delivery/rotation and health/lifecycle checks matched to the chosen Job or long-running runtime. Publish/promote by immutable digest and retain a tested rollback path.
- Application JSON/redaction precedes collection. Do not enable raw prompt/response capture in SDK tracing, container logs or audit. Verify known correlated records, collector interruption/recovery, permitted readers and configured retention. TRACE telemetry is distinct from authorized incident evidence.

## Cost and apply gates

The $20/month limit remains TRACE model usage, including live checks/evaluation. Azure infrastructure needs a separate owner-approved budget for AKS management/nodes/disks/network, ACR, PostgreSQL/backups, Key Vault, telemetry and Terraform state. Do not transplant the old AWS account, us-east-2 region, seven-day CloudWatch retention or $5 CloudWatch alert. AKS Free means free cluster management, not free resources or a production uptime SLA. Cloud mode/tier and reliability claims require a reviewed workload/cost decision.

Before any apply, record subscription/tenant/account restrictions, region/model processing location, exact identities/permissions, measured sizing, network exposure, retention/deletion, restore/rollback, estimated cost and reviewed Terraform plan. Budget alerts are notifications, not a model or infrastructure hard cap. All callers/in-flight reservations must be accounted for within the application's admitted scope; account-wide Azure billing remains a separate measurement.

No cluster, registry, database, Key Vault, workspace or state backend is created by accepting this direction. The existing native Foundry model deployment/check does not prove AKS delivery. S9 requires restore, failure/access/monetary-admission evidence and verified teardown/recreation with explicit handling of retained state, backups/logs and residual billable resources.

## Alternatives

| Option | Disposition and tradeoff |
| --- | --- |
| Azure + containers + AKS | Owner-selected target; aligns cloud workload identity with the Azure model platform and provides an inspectable container/orchestration deployment. Adds cluster lifecycle, shared-state/concurrency and infrastructure cost work. |
| Existing Terraform + EC2/RDS/CloudWatch | Superseded by the owner's platform change; keep earlier ADRs/examples as historical records, not current deployment instructions. |
| Azure VM or Azure Container Apps | Lower orchestration burden for a small application, but not the selected target. Revisit only with a documented owner decision if measured AKS cost/operations fail the gates. |
| Split services, self-hosted PostgreSQL or separate vector service | Not selected. AKS does not justify extra application boundaries or moving database recovery into pods; require measured need and an ADR. |

## Evidence and limits

Owner statements on 2026-10-14 select Azure/AKS and authorize records/backlog updates. [Roadmap #9](https://github.com/krispykrits/TRACE/issues/9), [charter](../charter.md), [cloud architecture](../architecture/azure-cloud.md) and [refined cloud backlog](../planning/azure-cloud-backlog.md) carry the decision. #55-#60 are planned implementation/acceptance work, not completed delivery. Local MVP, Cloud MVP, independent Operational Pilot and final production-remediation acceptance remain separate.

Official references: [AKS Workload Identity](https://learn.microsoft.com/en-us/azure/aks/workload-identity-deploy-cluster), [AKS modes](https://learn.microsoft.com/en-us/azure/aks/core-aks-concepts), [AKS pricing tiers](https://learn.microsoft.com/en-us/azure/aks/free-standard-pricing-tiers), [Flexible Server pgvector](https://learn.microsoft.com/en-us/azure/postgresql/extensions/how-to-use-pgvector), [Container insights](https://learn.microsoft.com/en-us/azure/azure-monitor/containers/container-insights-overview), [GitHub-to-Azure OIDC](https://learn.microsoft.com/en-us/azure/developer/github/connect-from-azure-openid-connect), [Terraform Azure Blob backend](https://developer.hashicorp.com/terraform/language/backend/azurerm).

## Revisit conditions

The owner reviews this direction if measured cost/quota, database/vector compatibility, authorization/retention/residency, recovery or operating capacity cannot meet the declared Cloud MVP gates. Document evidence and obtain a revised direction rather than silently reverting to AWS or adding infrastructure. Any runtime/SDK/entry-point change remains a scoped implementation PR with appropriate tests and updated locked dependencies.
