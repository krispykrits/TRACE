# Registry adoption draft

This configuration models one existing development Azure Container Registry. The backend is independently bootstrapped; it is not managed by this state. Import and provider registration are not run by merely committing this file. Review every plan before applying it. Never apply a plan with unexpected creates, updates, replacements, or deletions.

Use Terraform 1.17 or later and the locked AzureRM provider. Authenticate with Azure CLI, verify the tenant and subscription, then set `ARM_SUBSCRIPTION_ID` to the intended subscription. Configure the backend with a private, untracked `backend.dev.hcl` that supplies `resource_group_name`, `storage_account_name`, `container_name`, and `key`. Store no credentials in that file. Verify that the selected state belongs to this deployment before initialization.

Provide `registry_resource_id`, `registry_name`, `resource_group_name`, and `location` through private environment variables or an untracked variable file. The resource ID and resource attributes must identify the same existing registry. Do not commit values, state, plans, provider caches, or backend settings. Files used by Terraform may contain sensitive infrastructure details.

```sh
terraform init -lockfile=readonly -backend-config=backend.dev.hcl
terraform fmt -check
terraform validate
terraform plan -out=registry-import.tfplan
terraform show registry-import.tfplan
```

Treat the saved plan as sensitive, store it outside version control, and review its exact contents and destination state. An operator must approve the exact current plan before applying it; refresh and review a new plan if circumstances change. The initial development check using the parameterized equivalent showed one import and no changes, but it was not saved and does not authorize a later apply. Import does not by itself establish workload deployment or verify image-pull permissions.
