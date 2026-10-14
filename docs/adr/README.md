# Architecture decision records

Use [the template](template.md) for a consequential decision. Record the owner, evidence, alternatives and a concrete condition for revisiting it. Implementation notes belong near the code they describe.

| ADR | Decision | Status |
| --- | --- | --- |
| [0001](0001-repository-runtime-and-local-tooling.md) | One modular TRACE repository, CPython 3.12/Linux and locked uv environment | Accepted foundation; dependency and integration choices remain gated |
| [0002](0002-terraform-and-ec2-cloud-deployment.md) | Terraform and EC2 for the original Cloud MVP target | Superseded cloud target by ADR 0015; Terraform retained |
| [0003](0003-cloudwatch-hosted-logging.md) | CloudWatch Logs for original hosted application logging | Superseded platform by ADR 0015; historical example retained |
| [0004](0004-synchronous-synthetic-order-workflow.md) | Synchronous in-process Order–Payment demo with fixture boundaries | Accepted for scoped synthetic Sprint 2 path |
| [0005](0005-sqlite-local-postgresql-rds-cloud.md) | Local SQLite then managed PostgreSQL state | RDS hosting superseded by ADR 0015; Local SQLite/PostgreSQL semantics retained |
| [0006](0006-pgvector-cloud-retrieval-storage.md) | PostgreSQL/pgvector for cloud vector storage | RDS hosting superseded by ADR 0015; retrieval/authorization gates retained |
| [0007](0007-synthetic-evidence-identity-and-isolation.md) | Stable synthetic evidence identity and evaluator isolation | Accepted with merged issue #8 implementation |
| [0008](0008-local-corpus-generations-and-source-policy.md) | Local corpus generations, adapted chunk provenance and current source policy | Accepted with merged issue #15 implementation |
| [0009](0009-local-exact-knowledge-retrieval.md) | Pinned optional CPU embeddings, exact retrieval and development-selected lexical default | Accepted with merged issue #16 implementation |
| [0010](0010-capability-packages-and-adapter-boundaries.md) | Capability packages, adapters/composition and automatic import/wheel verification | Accepted in #46 / PR #47 |
| [0011](0011-read-only-tool-execution.md) | Fixed read-only tool catalog, readonly sources and deadline-isolated execution | Accepted in #18 / PR #48 |
| [0012](0012-model-provider-contract-and-bounded-call.md) | Provider-neutral model contract and bounded execution; Azure AI Foundry / GPT-6 Luna and per-request transmission controls | Accepted for Local MVP synthetic provider use after #34 closure / merged PR #51; operational source/identity/retention gates remain separate |
| [0013](0013-assessment-validation-and-support-review.md) | Strict v2 assessments, current citations and independent protected support review | Accepted in #35 / merged PR #52 for Local MVP; frozen v1 scoring remains unchanged |
| [0014](0014-durable-investigation-budgets.md) | Shared durable model/tool admission, usage reservations and content-free cost estimates | Accepted in #36 / merged PR #53 for the Local MVP enabler; distributed cloud admission remains #57 acceptance |
| [0015](0015-azure-aks-cloud-deployment.md) | Azure/containers/AKS, shared PostgreSQL/pgvector, Workload Identity and Azure telemetry | Owner-selected direction; #55-#60 design/implementation/acceptance pending |
| [0016](0016-bounded-investigation-and-private-publication.md) | Fixed evidence-first workflow, complete repeated admission and private atomic publication | Proposed in #37; operational inspection remains #38 |

## Open decision register

[ADR 0010](0010-capability-packages-and-adapter-boundaries.md) records the owner-authorized capability layout, adapter composition, test categories and automated import/package checks; implementation is merged in #46 / PR #47.

These are gates, not inferred decisions. The [charter](../charter.md) is the full owner/input register; update the relevant ADR when a design choice is made.

| Input | Owner and gate | Current effect |
| --- | --- | --- |
| University rubric/deadline and weekly capacity/sprint length | Project owner, before calendar or scope commitment | Sprint numbers are increments, not dates |
| Pilot operator/team, service, data-access owner and source permission | Project owner and source owner, before replay or shadow use | Operational Pilot remains unvalidated |
| Runtime additions, model/provider and source adapters | Project team, when a specific capability is designed and evaluated | Numerical/lexical dependencies and optional local encoder accepted in [ADR 0009](0009-local-exact-knowledge-retrieval.md); Azure AI Foundry / GPT-6 Luna and $20/month model cap selected in [ADR 0012](0012-model-provider-contract-and-bounded-call.md); Azure adapter/live synthetic contract accepted in #34; operational source/identity/retention gates remain open |
| Shared Azure PostgreSQL sizing/migration/roles/admission | Project team and account owner, S7–S9/#55/#57 | Local SQLite is implemented under ADR 0005; [ADR 0015](0015-azure-aks-cloud-deployment.md) selects the Azure hosting baseline; shared migration/concurrency/restore acceptance remains pending |
| Vector index, embedding versions and retrieval limits | Project team and owner, #16 then S7–S9 | ADR 0006 retains PostgreSQL/pgvector semantics with Azure hosting in [ADR 0015](0015-azure-aks-cloud-deployment.md); [ADR 0009](0009-local-exact-knowledge-retrieval.md) records the accepted local baseline; cloud extension/rebuild/citation acceptance remains #57 |
| Azure infrastructure/model spending constraints and measured workload | Project owner and relevant reviewer, before paid evaluation or provisioning | Model cap is $20/month through Azure AI Foundry; TRACE-local model reservations/usage estimates and a synthetic live contract are accepted in #34; account-wide billing, operational retention and Azure infrastructure budget remain separate |
| AKS topology, identity, Terraform state and application release/recovery | Project team and account owner, S7/S8 after budget/workload inputs | [ADR 0015](0015-azure-aks-cloud-deployment.md) and #55-#58; exact resources/account/budget and apply remain gated |
| Azure telemetry collection/workspace, permitted readers, retention/ingestion and alerts | Project owner/account owner, before hosted collection | [ADR 0015](0015-azure-aks-cloud-deployment.md) and #59; no old CloudWatch retention or $5 threshold selects Azure values |
| Production action/target, service owner and approver | Project owner and service owner, before action-specific design and execution | No standing mutation permission; see [approved scope](../planning/production-remediation-scope.md) |

The [implementation review](../planning/production-usefulness-review.md) and [approved amendment](../planning/production-roadmap-amendment.md) define the reuse and Operational Pilot constraints behind these gates.
