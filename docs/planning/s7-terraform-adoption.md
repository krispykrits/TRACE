# Terraform adoption plan for existing TRACE development resources

Status: owner selected staged adoption and a private Azure Blob backend. A registry import draft and preliminary plan exist; no resource has been imported. This is the [#55](https://github.com/krispykrits/TRACE/issues/55) handoff, not a claim that Terraform currently manages any Azure resource.

## Observed backend

A development StorageV2 account in North Central US uses Standard LRS. Its `tfstate` blob container was created with private anonymous access. Blob versioning is enabled; blob and container soft delete were already enabled with seven-day retention. Versions are currently retained without an automatic expiry policy; review retention and cost later. The account's public endpoint permits all networks, but anonymous blob access is disabled; public network reachability and data authorization are distinct.

The Terraform backend must be reachable from the selected execution environment. Entra data-plane read/write and lease permissions on the container are required. An Entra-authenticated operator successfully listed the state container after blob data roles were assigned. Review effective role scope and remove redundant broader grants when appropriate. Configure a narrower network path and named principals after checking that the operator can still reach the account. Treat state, state versions, plans, backend configuration and logs as sensitive.

Do not place this backend's storage account or container in the same Terraform state that depends on them for its own operation. Maintain the manually bootstrapped backend separately with its own inventory and recovery procedure; do not delete it during environment teardown. This protects lifecycle independence, not authorization by itself.

## Ownership and order

| Stage | Adopt or configure | Important boundaries |
| --- | --- | --- |
| 0 | Confirm backend/container, Entra operator access, network path, blob versioning, soft delete and state recovery. Verify existing state before initialization. | Access grants require their own reviewed scope. Do not use account keys in code or CI. A storage data role is not equivalent to Azure resource management permission. |
| 1 | Model the existing Basic registry and its resource group ownership. | Preserve existing kubelet pull access. The published sample pull is evidence only for that image and identity. |
| 2 | Model the West US 3 workspace and review Container Insights' actual Azure-managed data collection rule and association. | Import independently only where the provider supports stable ownership and they are not managed by AKS or a solution. The other workspace is out of scope until explicitly selected. |
| 3 | Model the existing PostgreSQL flexible server, target database as appropriate, firewall rules, backup retention and vector allowlist. | PostgreSQL `CREATE EXTENSION vector` and schema changes belong to versioned database migrations. Preserve the existing database, credentials and backup settings. |
| 4 | Model the AKS control plane, existing system node pool and intentional network/identity configuration. | The AKS-managed node resource group, its VM scale sets and Azure-generated dependencies remain AKS-owned unless separately justified. Verify current addon, RBAC, OIDC and workload identity settings. Do not start, stop or resize the cluster as part of import. |
| 5 | Add separately reviewed workload identities, federated credentials, role assignments and deployments when their exact owners and permissions are selected. | Model reader, collector, API, worker, CI/deployment, database and image-pull authority separately. No grant is implied by enabling cluster OIDC. |

Resource groups shared with other assets require explicit ownership decisions; a shared group need not be imported to manage individual resources. Each Azure object may be owned by only one Terraform address/state. The new state account and external services remain outside this workload state until a separately reviewed lifecycle design says otherwise.

## Initial backend configuration

The backend is bootstrapped outside the deployment state. The following remains a **review template**, not an instruction to apply. The registry draft pins AzureRM and includes a provider lock file. Store the account name, resource-group name, container and key in a private, untracked backend configuration supplied at initialization; do not store credentials in it.

```hcl
terraform {
  backend "azurerm" {
    use_azuread_auth = true
    use_cli          = true
  }
}
```

```hcl
# backend.dev.hcl.example: replace placeholders in an untracked local copy.
resource_group_name  = "<state-resource-group>"
storage_account_name = "<state-storage-account>"
container_name       = "tfstate"
key                  = "trace/dev/platform.tfstate"
```

Use a preauthenticated Azure CLI session for the operator, confirm tenant/subscription, and check the target blob is not an unrelated existing state before running `terraform init -backend-config=backend.dev.hcl`. The backend and provider authenticate separately. For subsequent CI use a separately scoped federated identity and its supported OIDC configuration; do not assume the local Azure CLI backend settings authenticate GitHub Actions. Prevent state and plan files, backend configs, credentials and resource IDs from entering public Git history or build artifacts.

## Import review and acceptance

1. Inventory real resource settings and ownership without exporting keys, connection strings or state to the repository. Record supported provider fields, computed/default values, shared resource groups, Azure-managed dependencies and actual grant scope.
2. Write matching provider/resource configuration and explicit Terraform `import` blocks for one batch. Generated configuration is a draft and may contain defaults that propose updates or replacement.
3. Run `terraform fmt -check`, `terraform init`, `terraform validate` and `terraform plan -out=<protected-path>` only in a verified empty intended state and authenticated environment. Inspect the plan and state destination. Initialization can access the backend; plan can read remote data and may acquire a state lock. Keep all artifacts protected.
4. A first import plan should show only the intended imports and no unexpected add, change, replace or destroy actions. Explain any computed attributes or necessary deviations; stop and reconcile before applying. `prevent_destroy` is supplemental and cannot protect an object whose resource block is removed.
5. Apply the exact reviewed, unexpired plan only when authorized, then run a fresh plan and investigate any drift. Record identity, tool/provider versions, plan summary, resource addresses, state location and result without publishing secrets. Repeat for each batch.
6. Test state-version recovery with an isolated test state and retain a documented incident procedure. Restore of stale infrastructure state is a deliberate recovery step: reconcile live resources and sensitive state first. Backup/restore of database data and the model-spending ledger is a separate process.

A private backend and a sample pull do not establish infrastructure-as-code adoption. Cloud Shell initialized the Blob backend using Entra authentication and verified that its state contained zero resources. A preliminary plan for the parameterized registry draft reported one import, zero additions, zero changes and zero deletions; the plan was not saved for apply. The [registry configuration](https://github.com/krispykrits/trace-platform/tree/main/azure/registry) now resides in trace-platform. Review and save a fresh plan before any authorized apply; imports, network restriction, state recovery tests and the other resource batches remain open. The owner accepts the current budget for now and will revisit it; version storage and other charges remain unmeasured.
