# Azure deployment responsibilities

Status: Azure/container/AKS direction is accepted; deployment implementation and hosted acceptance remain planned. [ADR 0015](../docs/adr/0015-azure-aks-cloud-deployment.md), [cloud design](../docs/architecture/azure-cloud.md) and [#55–#60](../docs/planning/azure-cloud-backlog.md) govern delivery.

## Selected components

| Responsibility | Planned Azure component |
| --- | --- |
| Application runtime | One modular TRACE container on AKS; review bounded CLI execution as a Job before selecting a persistent worker/API |
| Image delivery | Azure Container Registry and reviewed immutable image digests |
| Durable shared state | Azure PostgreSQL Flexible Server/pgvector, behind TRACE adapters |
| Application identity/secrets | Scoped Entra Workload Identity and approved Key Vault access |
| Platform telemetry | Azure Monitor/Log Analytics, with correlation/redaction/access/retention and collector-recovery evidence |
| Infrastructure lifecycle | Terraform with reviewed Azure Blob state/locking/access design |

Independent .NET monitored workloads follow [#70–#76](../docs/planning/dotnet-testbed-backlog.md). Their telemetry/source ingestion is separate from TRACE's own logging.

## Delivery and acceptance

1. **#55 design:** record measured workloads, subscription/tenant/account restrictions, region/model-processing location, runtime/node/network/resource shapes, owners, retention, recovery/teardown and an explicit infrastructure budget. Review a Terraform plan before any authorized apply.
2. **#56 image:** reproducible non-root image, locked inputs, provenance/SBOM/scanning, runtime-wheel/evaluator/credential exclusion and authorized ACR publication.
3. **#57 state:** migrate evidence/job/corpus/policy/review/provider and execution ledgers without losing IDs/provenance. Verify shared admission, concurrent/restarted jobs, restore and vector rebuild.
4. **#58 runtime:** prove the exact pod service-account identity/token path, intentional image/config promotion, lifecycle bounds and release rollback. Cluster/node pull credentials do not grant investigation administration.
5. **#59 telemetry:** prove actual hosted correlation, privacy, permitted readers, retention and collector recovery. Disable raw prompt/response capture.
6. **#60 cloud gate:** verify security/fault/cost/retention, state/recovery, restore, operations and teardown/recreation with residual-resource accounting.

The $20/month application model cap is separate from infrastructure and account-wide billing. Pod-local journal copies and Kubernetes retries cannot bypass shared monetary, attempt, deadline or unknown-outcome controls.

## Operating handoff

[Operations](../docs/operations/README.md) owns implemented procedures. Each hosted runbook must name release/environment, owner, prerequisites, exact commands, expected outcomes and verification. Include identity/secret rotation, migration, backup/restore, retention/deletion, termination, uncertain-call reconciliation, rollback, audit access and retained billable resources.

No resource/account/permission or paid request is authorized by this guide. The current implementation and open gates are recorded in [current status](../docs/current-status.md).

## Superseded AWS material

The `cloudwatch/` Terraform and agent files remain unmodified historical preparation. Their old settings and commands select no Azure resources or budget and establish no hosted acceptance. The [archived runbook](../docs/archive/cloudwatch-preparation.md) and superseded ADRs 0002/0003 preserve context; use the Azure path above for future work.
