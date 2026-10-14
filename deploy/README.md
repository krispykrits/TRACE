# Infrastructure and environment responsibilities

Status: Azure/containers/AKS direction selected by the owner on 2026-10-14; design, provisioning and hosted acceptance pending. [ADR 0015](../docs/adr/0015-azure-aks-cloud-deployment.md) supersedes EC2, RDS hosting and CloudWatch. Retain Terraform, one modular application, Local SQLite and PostgreSQL/pgvector contracts. [Cloud architecture](../docs/architecture/azure-cloud.md) and [#55-#60](../docs/planning/azure-cloud-backlog.md) govern future work.

| Environment | Purpose and owner | Current infrastructure boundary |
| --- | --- | --- |
| Local development | Contributor runs the CLI and deterministic Python/uv checks | Existing SQLite/private journals; no cluster/cloud credentials are required by fast CI. Paid/synthetic provider checks stay separately opted in. |
| Development cloud | S7/S8 reviewed integration target, with account owner | Design AKS, ACR, Azure PostgreSQL/pgvector, Entra Workload Identity, Key Vault, Monitor/Log Analytics and Blob state; no target resources are created by this documentation. |
| Demo / Cloud MVP | S8 release and S9 verified hosted acceptance | Run the accepted workflow in an immutable container; migrate shared state/admission, prove workload identity, synthetic smoke checks, rollback, restore, cost and teardown/recreation. |
| Operational Pilot | Separately authorized historical replay and read-only shadow use | Named operator/source owner, permitted data, retention/deletion, access isolation, support/recovery and usefulness evidence; cloud demo acceptance cannot substitute. |

## Design and apply gates

1. #55 records measured workload, subscription/tenant/account restrictions, region/model processing location, resource owners and an owner-approved Azure infrastructure budget. The $20/month model cap is separate. Include AKS management/nodes/disks/network, registry, database/backups, secrets, telemetry and Terraform state; no old AWS retention/alert setting transfers automatically.
2. Review AKS mode/tier/version/node pools, resources/network exposure/egress, registry/database shape, shared-state migration, recovery, retention/deletion and billable-resource teardown. The current interface is a CLI; review a bounded Kubernetes Job first. A worker/API/ingress or extra service needs explicit contracts/justification.
3. Use Terraform with reviewed Azure provider versions and a scoped Azure Blob state/locking/access design. Keep state/secrets outside Git. Review plans before apply; infrastructure lifecycle and application promotion are separate operations, not Terraform remote-exec app deployment.
4. Separate CI/Terraform deployment, cluster/node/image pull, application Workload Identity, source/model/database grants, database migration/admin and collector/reader permissions. Implement/verify the service-account federation and SDK token path in #58; a cluster identity or local Foundry key/portal session is not workload-authentication acceptance.
5. Require shared transactional evidence/jobs/corpus/reviews and model/execution reservations under #57. Per-pod SQLite files/journals cannot enforce a shared $20 cap. Test concurrent admission, stale claims, pod replacement and unknown in-flight provider outcomes before permitting concurrent paid jobs.
6. Approve immutable release/rollback, non-root/pod security and resources, secret rotation, startup/health/termination appropriate to the selected runtime, raw-content-free collection, retention and responsible operators. Kubernetes backoff/restarts must obey application retry/deadline/cost policy.
7. Rehearse authorized database restore, vector rebuild/citation preservation and teardown/recreation; record retained/deleted databases, backups, logs, registry artifacts, state, identities, disks/network resources and residual bills. Alerts are notifications, not spending enforcement or deletion evidence.

## Implementation and acceptance

- **S7 / #55:** justified Azure design and reviewable Terraform plan/migration/authority/cost assumptions; design alone does not apply resources.
- **S8 / #56-#59:** reproducible image and authorized ACR publication; PostgreSQL shared-state migration/admission; scoped Workload Identity and digest-based AKS promotion/rollback; redacted hosted telemetry with actual correlation/access/retention/recovery evidence.
- **S9 / #60:** accepted cloud investigation, migration/restore, concurrent/restarted worker and uncertain-provider recovery, source/privacy/injection/access boundaries, cost accounting and teardown/recreation.

The initial investigator remains read-only. Deployment permission does not authorize an operational remediation, public API, new source integration or paid request. Missing infrastructure/budget/access remains a named blocker; local logs, a Terraform plan or the existing synthetic Foundry check never count as AKS/hosted-delivery acceptance.

## Historical AWS preparation

[ADR 0002](../docs/adr/0002-terraform-and-ec2-cloud-deployment.md), [ADR 0003](../docs/adr/0003-cloudwatch-hosted-logging.md) and the RDS-hosting portions of ADRs 0005/0006 are superseded. The [legacy CloudWatch example](cloudwatch/README.md) is retained only as historical preparation, not the active deployment path. No cloud provisioning or migration is performed by this records update.
