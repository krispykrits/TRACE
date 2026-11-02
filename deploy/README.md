# Azure deployment responsibilities

Status: Azure/container/AKS direction is accepted; deployment implementation and hosted acceptance remain planned. [ADR 0015](../docs/adr/0015-azure-aks-cloud-deployment.md), [cloud design](../docs/architecture/azure-cloud.md) and [#55–#60](../docs/planning/azure-cloud-backlog.md) govern delivery.

## Selected components

| Responsibility | Planned Azure component |
| --- | --- |
| Application runtime | Separate API and persistent investigation worker on AKS from a modular core; shared image allowed |
| Image delivery | Azure Container Registry and reviewed immutable image digests |
| Durable shared state | Azure PostgreSQL Flexible Server/pgvector, behind TRACE adapters |
| Application identity/secrets | Scoped Entra Workload Identity and approved Key Vault access |
| Platform telemetry | Azure Monitor/Log Analytics, with correlation/redaction/access/retention and collector-recovery evidence |
| Infrastructure lifecycle | Terraform with reviewed Azure Blob state/locking/access design |

Independent .NET monitored workloads follow [#70–#76](../docs/planning/dotnet-testbed-backlog.md). Their telemetry/source ingestion is separate from TRACE's own logging.

## End-state delivery update — 2026-10-15

[ADR 0021](../docs/adr/0021-interactive-platform-and-repository-boundaries.md) selects an authenticated API and persistent investigation worker around the modular Python core. The owner has since directed removal of the local CLI. The registry configuration is in [trace-platform](https://github.com/krispykrits/trace-platform/tree/main/azure/registry); other extraction remains in progress. Keep evaluation out of runtime packages/images, and pin compatible image digests for platform deployments. Preserve historical reports and hashes.

PostgreSQL-backed durable work dispatch is the initial choice: transactional submission, atomic claims, leases, cancellation, retries and shared attempt/spending admission. Reconcile uncertain external outcomes before retrying. No separate broker is required; add one only for demonstrated throughput/latency/contention/consumer needs. Use batch Jobs for evaluation, corpus rebuilds, migrations and scenarios.

Flexible capability contracts cover telemetry, knowledge, change/deployment records and workload state. JSON then Azure Monitor are first implementations. Preserve original identity/revision, timestamps, correlation, units, provenance and explicit completeness; enforce source/transmission/report rights independently, with scope/result/deadline/pagination limits. On-demand reads and batch import are initial modes; scheduled/event-driven ingestion and dedicated ingestion workers require a concrete lifecycle/volume/isolation need.

**Required web delivery:** after S8 API stabilization and before S15 pilot, provide submission, progress/cancellation, evidence/timeline and protected cited reports. S14 adds ranked-response comparison, selection and concrete approval UI/API, plus separate deterministic execution with distinct credentials. This is required scope. S7 must size stories and place them within S8-S14 capacity or add an undated increment before S15; do not assume it fits the existing 18 increments unchanged.

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

CloudWatch was superseded by Azure Monitor.

## AKS runtime

The application image is defined by `Dockerfile`; `deploy/aks` defines the internal API and worker. Before applying, set the image to a reviewed ACR digest and replace the worker service-account identity placeholder with the client ID of an identity federated to `system:serviceaccount:trace:trace-worker` and authorized for Foundry. The cluster must have OIDC and workload identity enabled.

The `trace` namespace needs a `trace-runtime` Secret containing `TRACE_POSTGRES_DSN` (TLS `verify-full`), `TRACE_ENTRA_TENANT_ID`, `TRACE_ENTRA_API_CLIENT_ID`, and `TRACE_ENTRA_DELEGATED_SCOPE`. A separately provisioned `trace-source` volume must contain the current authorized `profile.json`, its referenced read-only source databases and knowledge index, and `azure.env` with the Entra model settings. The profile must be owned by UID 10001 with mode 0600. These are prerequisites; the checked-in manifest intentionally does not create credentials, source grants, storage, or a deployable image reference.
