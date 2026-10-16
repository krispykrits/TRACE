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
| [0016](0016-bounded-investigation-and-private-publication.md) | Fixed evidence-first workflow, complete repeated admission and private atomic publication | Accepted in #37 / merged PR #62; local inspection added in #38 / PR #82 |
| [0017](0017-dotnet-testbed-and-json-first-evidence.md) | Independent .NET Order/Payment testbed, JSON-first then live Azure source ingestion and owner-led investigation | Accepted owner direction; #69-#76 implementation/usefulness pending |
| [0018](0018-flexible-ml-and-ranked-response-options.md) | Use-case-appropriate evaluated ML and ranked incident-response options with an explicit recommendation | Accepted owner direction, 2026-10-15; ML/response implementation and acceptance pending |
| [0019](0019-local-cli-and-saved-report-access.md) | Local CLI, durable dependency bindings and current-authority saved disclosure | Accepted for #38 through merged PR #82; operational identity remains gated |
| [0020](0020-investigator-evaluation-and-artifact-isolation.md) | Actual-output scoring, observed-only child and frozen private review artifacts | Proposed in #39; owner review pending |
| [0021](0021-interactive-platform-and-repository-boundaries.md) | API/worker, repository ownership, PostgreSQL dispatch and flexible source adapters | Accepted owner direction, 2026-10-15; S7 refinement and implementation pending; supersedes prior single-repository/CLI-first hosted direction |
| [0022](0022-sprint-06-readiness-and-sprint-07-diagnostics.md) | S6 local readiness/handoff, S7 actual Azure diagnostics and owner quality acceptance | Accepted owner delivery direction; implementation/acceptance pending |

## Reading and maintaining ADRs

An ADR records a scoped decision and its rationale. Its original context, alternatives and measurements may describe an earlier implementation. Current capability/status belongs in [architecture](../architecture/README.md) and [current status](../current-status.md).

Use [the template](template.md) for a consequential decision. Update acceptance/supersession metadata when evidence changes; retain the original decision text and link a replacement for changed direction. A selection ADR can be accepted while implementation remains pending.

The [charter input register](../charter.md#open-inputs-and-decision-gates) owns unresolved owner/resource/threshold/permission decisions. The [delivery plan](../planning/capstone-project-plan.md) owns release gates; avoid duplicating those registers here. [Archived source reviews](../archive/README.md) retain historical context.
