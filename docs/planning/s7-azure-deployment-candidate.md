# Azure deployment candidate and cost handoff

Status: **draft for #55 review**. The original candidate and retail scenario below are historical; the observed development resources are recorded separately. They are not a subscription quote or hosted acceptance. The owner's $15/month infrastructure target and separate $20/month model allowance remain unchanged. The [earlier partial scenario](azure-cost-scenario-s7.md) explains 20-hour compute sensitivity; this document adds a more explicit bill of resources and implementation checks. The owner's Azure for Students offer, North Central US preference, on-demand schedule, no HA requirement and approximately 14-day retention are planning inputs, not verified account properties.

## Observed development environment — 2026-11-01

These are development observations, not production sizing or hosted application acceptance. Subscription identifiers, endpoints, usernames and secrets stay outside this repository.

| Area | Observed state and evidence | Remaining work |
| --- | --- | --- |
| AKS | Azure for Students, West US 3, Base/Free tier, Kubernetes 1.36.4, one manually scaled system pool with two D2s v4 Linux nodes. Cluster was stopped after monitoring setup. | Measure application requests, limits and capacity; confirm node disk and upgrade behavior. Stopped compute does not remove all retained-resource charges. |
| AKS authentication | Portal showed Microsoft Entra authentication with Azure RBAC, local accounts disabled, OIDC issuer and Workload Identity enabled. | Bind exact service-account subjects to managed identities; assign narrow scopes and test valid, wrong-subject and revoked access. Cluster settings do not prove a pod can access Foundry, Key Vault, sources or PostgreSQL. |
| Registry | Basic ACR in North Central US; an AKS test pod successfully pulled a published sample image. | Build and verify TRACE images, provenance and immutable digests under #56; a sample image is not a TRACE release. |
| PostgreSQL | Flexible Server in Canada Central, PostgreSQL 18.6, B1ms (1 vCore, 2 GiB), 32 GiB storage, HA disabled; the server was running at last inspection. A TLS-verified AKS connection succeeded. | Measure cross-region latency and transfer, verify app access and roles, migration, storage type, backup/restore and recovery. Avoid logging credentials. |
| pgvector | Server allowlist updated for vector; a dedicated development database created. Owner reports CREATE EXTENSION and query returned vector 0.8.7. | Preserve owner-reported provenance; verify vector operations, compatibility, least-privilege app roles and reproducible migrations under #57. |
| Observability | West US 3 Log Analytics workspace connected to AKS Container Insights for container logs and Kubernetes events; workspace default retention was 30 days. A separate North Central US workspace exists. | Verify ingestion on next cluster run; approve table-specific retention and readers; test redaction and collector recovery under #59. |
| Backups | PostgreSQL automatic backup retention was seven days; portal reports on-demand backups unsupported on the burstable tier. | Test restore and select data-specific recovery/retention requirements; 14 days remains tentative, not an instruction to change settings. |

North Central US remains the preferred original location, but the deployed AKS and PostgreSQL regions differ due to observed availability and quota restrictions. The database was publicly reachable with firewall rules for the connectivity test; private connectivity is a future design objective, not a description of this deployment. Confirm exact firewall scope and suitable application connectivity before hosting.

**Budget direction:** on 2026-11-01 the owner said the budget is fine for now and will be revisited later. This defers further budget decisions; it does not establish an actual monthly bill, erase unknown charges, change the earlier $15 planning target, or change the separate $20 model allowance.

## Historical candidate shape

The table and retail scenario below record the 2026-10-30 proposed scenario, not the deployed SKUs, regions or settings. Use the observed environment above for implementation planning.

| Area | Proposed development/test choice | Review / verification before implementation |
| --- | --- | --- |
| Region and access | North Central US; one development environment, operated by project owner | Confirm region/service/SKU/VM quota availability and actual Foundry resource and processing location. Subscription, tenant and role details stay in restricted configuration, not repository or PR. |
| AKS | Base SKU Free management tier, two Linux system nodes of `Standard_D4ads_v5`, no HA or additional pool in the cost scenario; API/worker use separate service accounts | Microsoft system-pool guidance specifies two nodes and at least 4 vCPUs; B-series are not supported for system pools. A single shared pool is a development compromise, not production isolation. Measure actual resource requests, pod headroom and throughput; reject if workloads do not fit. Pin a region-supported Kubernetes patch and node image at implementation, with a tested upgrade policy. |
| Node OS / state | Evaluate ephemeral OS disks on supported SKU; no durable job, evidence, spending or artifact data on nodes | Verify configured ephemeral placement, image-size fit, start/stop and quota. If managed disks are used, price their provisioned size and retention independently; node disappearance must not delete durable state. |
| Database | PostgreSQL Flexible Server, burstable B1MS, no HA, 32 GiB Premium SSD v2, 14-day backup retention as a candidate | Verify SKU and storage availability/pgvector support in subscription. Measure capacity; check backup size, restore point and storage billing. Initial 14 days is tentative per data category, not a deletion instruction or claim of adequate recovery. |
| Images | Basic ACR retained for 30 days; build component images in CI | Verify included storage, actual image size, supported registry authentication, scan/SBOM/provenance and immutable digests. ACR tasks and excess storage cost extra. |
| Network | TLS API access with authenticated requests, database private connectivity, narrowly defined outbound Foundry/source access; one Standard public IPv4 is an illustrative meter | Decide ingress design, subnet/IP sizing, egress type, TLS, DNS and precise public/private endpoints based on account restrictions and threat model. AKS commonly creates a load balancer/public IP for outbound traffic; price every rule, data-processing and endpoint charge. A public IP is not an API authorization mechanism. |
| Identity and secrets | AKS OIDC + Entra Workload Identity; distinct API and worker service accounts and identities; Key Vault Standard for necessary secrets | Verify federated issuer/subject/audience and token path; give worker only approved model/source access and DB role. API cannot use worker or deployment credentials. Confirm whether keyless Foundry and PostgreSQL authentication are available for this account. |
| Telemetry / recovery | Redacted correlated logs, approximately 14-day intended retention; backups and tested manual stop/restore/teardown | Confirm Log Analytics table plan and minimum retention, ingestion/query charges, actual backup retention and readers. Stopping the DB does not erase its storage charges and it restarts after seven days. Confirm restore and credit-expiration procedures before use. |
| Infrastructure delivery | Initial evaluation candidates: Terraform `1.17.1` and `hashicorp/azurerm` `5.12.0`, pinned via configuration and provider lock file; Blob backend with least-privileged deployment identity and locking; reviewed plan and pinned image digests | These are published versions checked 2026-10-30, not tested selections. Confirm compatibility/security, Kubernetes, PostgreSQL and pgvector versions at implementation; update the candidate if needed. A floating `latest` is not a pin. State access, environment segregation and recovery must be verified before any apply. |

The candidate is an input to #56–#60 and #73–#75, not a claim that those issues are delivered. Separate testbed source-query permission from TRACE's own telemetry. No known region or model-processing location is inferred from resource names. No production SLA, actual account quota or provider feature is assumed.

## Itemized 30-day retail comparison

This is a **bounded illustrative estimate**, not a subscription quote. Prices below are gross USD public consumption retail rates for `northcentralus` obtained from the [Azure Retail Prices API](https://learn.microsoft.com/en-us/rest/api/cost-management/retail-prices/azure-retail-prices) on 2026-10-30 US Eastern. The actual Azure for Students offer, free amounts, credits, service availability, taxes, exchange rates and account-specific billing may differ. All usage quantities below are hypothetical, not user-observed measurements.

| Resource / meter | Rate used | Hypothetical quantity | Gross amount |
| --- | ---: | ---: | ---: |
| AKS Base Free management | $0 management | 30 days | $0.00 |
| Linux D4ads v5 compute | $0.206/node-hour | 2 nodes × 20 active hours | $8.24 |
| PostgreSQL Flexible B1MS compute | $0.017/hour | 20 active hours | $0.34 |
| PostgreSQL Flexible Premium SSD v2 storage | $0.115/GiB-month | 32 GiB × full month | $3.68 |
| Basic ACR registry | $0.1666/day | 30 days | $5.00 |
| Standard static public IPv4 | $0.005/hour | retained all 720 hours | $3.60 |
| Hot LRS block blob storage | $0.0208/GB-month | 10 GB × full month | $0.21 |
| Log Analytics ingestion | $2.76/GB above 5 GB tier | 6 GB total; assume 5 GB free and 1 GB billed | $2.76 |
| Key Vault Standard operations | $0.03/10,000 operations | 10,000 operations | $0.03 |
| **Itemized subtotal** | | | **$23.86** |

Unrounded arithmetic: `8.24 + 0.34 + 3.68 + 4.998 + 3.60 + 0.208 + 2.76 + 0.03 = 23.856`. The prior $13.58 partial amount covered only node/DB compute and ACR; it was never an all-in estimate. This comparison assumes ephemeral OS disks, no extra PostgreSQL backup beyond any included allowance, no paid private endpoints or NAT, and no additional compute. The IPv4 is assumed retained even when stopped; different lifecycle choices alter the result. B1MS availability, 32 GiB storage support, workloads and all rate applicability require account verification.

**Not yet priced:** Standard Load Balancer rules/data processing, network egress, DNS, ingress/TLS components, private connectivity, additional disk or database IOPS/throughput, blob transactions, restore copies and excess backups, Log Analytics retention/query meters, Container Registry tasks/excess storage, certificate/secret renewal, monitoring add-ons, Azure state/storage transactions, extended support, taxes, other users and model inference. The real amount may be higher; credits or eligible free benefits may reduce the account bill. Do not treat omitted items as free or this subtotal as an upper bound.

A 10-hour compute scenario with all the same retained resources and other assumptions gives **$19.57** before the same omissions. For 20 hours, removing the assumed always-retained IP changes the subtotal to **$20.26**, but may require a different egress/access configuration and associated costs. These are comparisons, not proof that deleting an address is safe or supported. To meet $15, evaluate resource lifecycle, usage and architecture tradeoffs with a complete calculator quote; do not silently change the approved AKS direction or raise the target.

**Short-lived demonstration alternative:** assume 10 compute hours, retain PostgreSQL storage for all 30 days, but retain the registry and IP for only three days (72 IP hours), while keeping the same blob, log and vault quantities. This produces an itemized subtotal of `4.12 + 0.17 + 3.68 + (3 × 0.1666) + (72 × 0.005) + 0.208 + 2.76 + 0.03 = $11.8278`, or **$11.83**, before the same omitted charges. The $3.17 remaining under the target is not evidence that omitted costs fit. Recreating a registry or endpoint can change names, networking and release availability; this alternative requires verified image-digest restoration, endpoint/authentication, safe teardown and exact resource-lifecycle behavior. Never delete retained state, evidence or spending ledgers to save cost. No teardown is authorized by this scenario.

## Identity, data and infrastructure boundary

1. Deployment principal: separate GitHub OIDC-federated Terraform identity with subscription/resource-group scope limited to reviewed resources; restricted Blob state container and least-privilege data-plane access. State can contain secrets. Plan and lock state, review diffs and estimated cost; no automatic apply.
2. API identity: validate human JWT signature/issuer/audience/tenant and server-derived grant; use a scoped API DB role. It cannot obtain source, model, secret-admin, node or deployment privileges merely from its service account.
3. Worker identity: distinct namespace/service account and Entra federated credential; read only authorized sources, invoke only approved Foundry deployment, access only needed Key Vault secrets and scoped DB operations. Current source and transmission grants remain independent. Verify wrong subject/namespace, revoked roles and unavailable authority fail closed.
4. Infrastructure roles: node/image pull, DB migration/admin, telemetry writer, telemetry reader and future executor are distinct authority boundaries. Never add broad contributor/owner grants to a workload to solve an authentication failure.

Use dedicated subnet planning for cluster/database, private database access and deliberate DNS; expose only a reviewed authenticated TLS endpoint, with bounded outbound destinations. Pick the precise ingress and network mode after checking regional availability, security needs and costs. The candidate Terraform CLI and provider versions are recorded above against the [HashiCorp releases API](https://api.releases.hashicorp.com/v1/releases/terraform/1.17.1) and [provider registry](https://registry.terraform.io/providers/hashicorp/azurerm/5.12.0); they have not been installed or tested here. Terraform configuration must pin actual tested provider/tool versions and dependency locks, preserve state and specify access/retention, plan review, immutable deployment and rollback. PostgreSQL/pgvector compatibility must be checked against the chosen runtime and region before lock. Current documentation does not establish tested versions or Azure permissions.

## Evidence and gates

Owner deferred budget review on 2026-11-01. A complete subscription-specific estimate, free-service eligibility and actual billing remain unverified and should be revisited later; do not infer a new budget. Review remaining identity, network, retention, recovery, Terraform and access decisions alongside the [hosted implementation contract](../architecture/s7-implementation-contract.md) and [backlog handoff](s7-implementation-handoff.md). #55's existing acceptance criteria remain open until reviewed; deferral is not evidence of a completed cost gate.

This document records the development resources and limited tests described above; it does not itself provision resources, configure alerts, issue paid requests or establish hosted application acceptance. Infrastructure apply, real-source access and paid diagnostic execution retain their own authorization and acceptance gates.
