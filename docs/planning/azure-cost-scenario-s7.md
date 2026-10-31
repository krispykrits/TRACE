# Azure cost scenario for Sprint 7 design

Status: **illustrative partial retail-price scenario, not a deployable sizing, subscription quote or approval to incur cost.** This documents the #55 cost work against the owner's $15/month infrastructure planning target; the separately bounded $20/month TRACE model allowance is excluded. Assumptions and gaps require review before any deployment.

## Why this matters

The owner prefers North Central US, an Azure for Students subscription, on-demand operation, no high-availability requirement and approximately 14-day retention. Actual remaining credit, subscription eligibility and quotas, desired hours, resource sizing, private networking and retention by data type have not been verified. A monthly budget alert does not stop usage. Azure for Students credit is finite, not a recurring monthly allowance; Microsoft describes $100 of credit for 12 months for the offer, but the actual account balance and dates must be checked. See [Azure for Students FAQ](https://learn.microsoft.com/en-us/azure/education-hub/faq) and [budget alerts](https://learn.microsoft.com/en-us/azure/cost-management-billing/costs/tutorial-acm-create-budgets).

## Scenario and published prices

Illustrative assumptions: one AKS cluster with a two-node system pool, two Linux `Standard_D4ads_v5` VMs running for the **same 20 hours in a 30-day month**, AKS Free cluster management, one PostgreSQL Flexible Server `B1MS` running for those same 20 hours, and one Basic ACR retained for all 30 days. No uptime SLA, HA, user node pool, additional VM or extra ACR build/storage usage is assumed. This is a **hypothetical comparison**, not measured usage, approved SKU selection, or a claim that the workload fits or these SKUs are available to this account.

For this optimistic partial calculation, the cluster's OS disks are assumed ephemeral with no separately billed managed OS disks. Microsoft lists the chosen VM series as supporting ephemeral OS disks; actual AKS compatibility, configuration and regional/subscription availability must be verified. Durable data cannot live on ephemeral disks. [AKS system-pool guidance](https://learn.microsoft.com/en-us/azure/aks/use-system-pools) describes at least two nodes, four vCPUs and no B-series VMs for system pools; [VM specifications](https://learn.microsoft.com/en-us/azure/virtual-machines/sizes/general-purpose/dadsv5-series) list this example as having local temporary storage and ephemeral OS support. The [AKS Free tier](https://learn.microsoft.com/en-us/azure/aks/free-standard-pricing-tiers) has no cluster-management charge but underlying resources are billed.

Rates below are USD **public consumption retail rates**, retrieved 2026-10-30 US Eastern using the [Azure Retail Prices API](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices) filtered to `northcentralus`, consumption pricing, product and meter. Prices, offers and tax may differ; credits affect the account bill but not these gross estimates. Record a fresh calculator estimate using the actual subscription before selecting resources.

| Meter | Retail rate | Assumption | Partial amount |
| --- | ---: | ---: | ---: |
| Linux VM `Standard_D4ads_v5` | $0.206/hour per VM | 2 × 20 hours | $8.24 |
| PostgreSQL Flexible Server `B1MS` compute | $0.017/hour | 20 hours | $0.34 |
| Basic ACR registry unit | $0.1666/day | 30 days | $5.00 |
| **Partial gross amount** | | | **$13.58** |

Calculation before display rounding: `(2 × 20 × 0.206) + (20 × 0.017) + (30 × 0.1666) = $13.578`. The calculation assumes billed VM and PostgreSQL compute hours match; startup, shutdown, minimum billing increments or unexpected restarts can increase them. The registry is counted all month, including while the cluster is stopped. These meter results establish an illustrative retail calculation, not eligibility or a complete monthly total.

### Hours sensitivity

Holding every other assumption above fixed, including 30 days of ACR and the optimistic ephemeral-OS assumption:

| Monthly AKS and database compute hours | Partial gross amount | Remaining of $15 target before omitted costs |
| ---: | ---: | ---: |
| 10 | $9.29 | $5.71 |
| 20 | $13.58 | $1.42 |
| 24 | $15.29 | Already $0.29 over target |
| 40 | $22.16 | Already $7.16 over target |

Formula: `30 × 0.1666 + hours × (2 × 0.206 + 0.017)`. No recommendation is made to use 20 hours; the actual operating schedule is still to be measured. Even 20 hours leaves only $1.42 for everything below. This does not demonstrate that the architecture fits $15.

## Costs not included

A complete subscription-specific estimate must include PostgreSQL provisioned storage and any excess backup charges; persistent application/artifact/Terraform-state storage; log ingestion and 14-day retention behavior; network egress, public IPs, load balancers, private endpoints/NAT if selected; DNS; registry build and excess storage; disk transactions; image and network transfers; Key Vault operations; taxes and any other selected resources. Model inference and other account users are also outside the partial infrastructure calculation. Validate default resource creation and free entitlements in the actual region/account. Do not assume any of these is free or that student credit remains available.

**Managed-disk sensitivity:** The same retail API returned a North Central US Premium SSD P10 LRS disk rate of $19.71 per disk-month. If a selected configuration used two such managed OS disks retained all 30 days, adding only those base disk charges to the 20-hour scenario gives `$13.578 + (2 × $19.71) = $52.998`, or **$53.00**, before the other omitted costs. This is a different hypothetical configuration, not a statement that P10 disks are required. [AKS storage guidance](https://learn.microsoft.com/en-us/azure/aks/concepts-storage) explains the conditions under which default ephemeral and managed disks are used; verify the actual configuration and any additional disk meters. Storage can remain billable while compute is stopped.

## Operating implications and next decisions

1. Estimate actual active hours and measure whether the selected node pool can support the TRACE and testbed workloads. Check AKS SKU/quota eligibility, ephemeral disk support, PostgreSQL/pgvector availability and Foundry processing location in the subscription. Do not infer them from public prices.
2. Price all chosen resources in the [Azure Pricing Calculator](https://azure.microsoft.com/en-us/pricing/calculator/) for North Central US using the real offer and consumption assumptions. Retain a dated breakdown and compare against the $15 target; if it exceeds the target, review operating hours, resource lifecycle or budget with the owner before provisioning. Do not present this partial scenario as the final bill of resources.
3. Design and test explicit cluster/database stop, restart, restore and teardown procedures, including retained billable resources. Microsoft documents that stopped PostgreSQL Flexible Server instances [automatically restart after seven days](https://learn.microsoft.com/en-us/azure/postgresql/configure-maintain/concepts-limits) and that storage/backup charges can continue while stopped. Cluster stop can release capacity and restart is not guaranteed when regional capacity is constrained. Protect backups, spending ledgers and artifact manifests before any deletion or recreation.
4. Plan $7.50, $12 and $15 infrastructure alerts, with a separate view of model and subscription-wide costs. Alert thresholds are monitoring, not hard limits. Confirm actual billing scope, credit balance and expiration; validate any automation separately before relying on it.

No resource creation, paid model call, account access, alert configuration or changes to the budget are performed by this analysis. The diagnostic run still requires its separately bound authorization.
