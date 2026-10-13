# Architecture decision records

Use [the template](template.md) for a consequential decision. Record the owner, evidence, alternatives and a concrete condition for revisiting it. Implementation notes belong near the code they describe.

| ADR | Decision | Status |
| --- | --- | --- |
| [0001](0001-repository-runtime-and-local-tooling.md) | One modular TRACE repository, CPython 3.12/Linux and locked uv environment | Accepted foundation; dependency and integration choices remain gated |
| [0002](0002-terraform-and-ec2-cloud-deployment.md) | Terraform and EC2 for the first Cloud MVP target | Accepted direction; topology and release design pending S7/S8 |
| [0003](0003-cloudwatch-hosted-logging.md) | CloudWatch Logs for hosted application logs | Platform selected; deployment and hosted acceptance pending |
| [0004](0004-synchronous-synthetic-order-workflow.md) | Synchronous in-process Order–Payment demo with fixture boundaries | Accepted for scoped synthetic Sprint 2 path |
| [0005](0005-sqlite-local-postgresql-rds-cloud.md) | SQLite Local MVP state, then PostgreSQL on RDS for Cloud MVP | Accepted direction; implementation/migration pending |
| [0006](0006-pgvector-cloud-retrieval-storage.md) | pgvector on RDS for cloud vector storage | Accepted direction; implementation and retrieval evidence pending |
| [0007](0007-synthetic-evidence-identity-and-isolation.md) | Stable synthetic evidence identity and evaluator isolation | Accepted with merged issue #8 implementation |
| [0008](0008-local-corpus-generations-and-source-policy.md) | Local corpus generations, adapted chunk provenance and current source policy | Accepted with merged issue #15 implementation |
| [0009](0009-local-exact-knowledge-retrieval.md) | Pinned optional CPU embeddings, exact retrieval and development-selected lexical default | Accepted with merged issue #16 implementation |
| [0010](0010-capability-packages-and-adapter-boundaries.md) | Capability packages, adapters/composition and automatic import/wheel verification | Accepted in #46 / PR #47 |
| [0011](0011-read-only-tool-execution.md) | Fixed read-only tool catalog, readonly sources and deadline-isolated execution | Accepted in #18 / PR #48 |
| [0012](0012-model-provider-contract-and-bounded-call.md) | Provider-neutral model contract, test-only fake and bounded single-call execution; Azure AI Foundry / GPT-6 Luna direction | Process boundary proposed in #34/#50; owner selected model/platform and $20/month cap; deployment configuration and live acceptance pending |

## Open decision register

[ADR 0010](0010-capability-packages-and-adapter-boundaries.md) records the owner-authorized capability layout, adapter composition, test categories and automated import/package checks; implementation is merged in #46 / PR #47.

These are gates, not inferred decisions. The [charter](../charter.md) is the full owner/input register; update the relevant ADR when a design choice is made.

| Input | Owner and gate | Current effect |
| --- | --- | --- |
| University rubric/deadline and weekly capacity/sprint length | Project owner, before calendar or scope commitment | Sprint numbers are increments, not dates |
| Pilot operator/team, service, data-access owner and source permission | Project owner and source owner, before replay or shadow use | Operational Pilot remains unvalidated |
| Runtime additions, model/provider and source adapters | Project team, when a specific capability is designed and evaluated | Numerical/lexical dependencies and optional local encoder accepted in [ADR 0009](0009-local-exact-knowledge-retrieval.md); Azure AI Foundry / GPT-6 Luna and $20/month model cap selected in [ADR 0012](0012-model-provider-contract-and-bounded-call.md); API/adapter and deployment configuration pending |
| SQLite schema and RDS sizing/migration/roles | Project team and account owner, #10 then S7–S9 | Products selected in [ADR 0005](0005-sqlite-local-postgresql-rds-cloud.md); implementation and acceptance pending |
| Vector index, embedding versions and retrieval limits | Project team and owner, #16 then S7–S9 | [ADR 0006](0006-pgvector-cloud-retrieval-storage.md) selects pgvector on RDS; [ADR 0009](0009-local-exact-knowledge-retrieval.md) records the accepted measured local baseline and embedding/index details; cloud migration remains gated |
| AWS/model spending constraints and measured workload | Project owner and relevant reviewer, before paid evaluation or provisioning | Model cap is $20/month through Azure AI Foundry; AWS budget and remaining model access/data-handling/spend controls are open; no deployment or paid experiment is evidenced |
| EC2 topology, identity, Terraform state and application release/recovery | Project team and account owner, S7/S8 after budget/workload inputs | See [ADR 0002](0002-terraform-and-ec2-cloud-deployment.md) |
| CloudWatch alert recipient, target host and deployment role | Project owner/account owner, before hosted logging deployment | See [ADR 0003](0003-cloudwatch-hosted-logging.md) |
| Production action/target, service owner and approver | Project owner and service owner, before action-specific design and execution | No standing mutation permission; see [approved scope](../planning/production-remediation-scope.md) |

The [implementation review](../planning/production-usefulness-review.md) and [approved amendment](../planning/production-roadmap-amendment.md) define the reuse and Operational Pilot constraints behind these gates.
