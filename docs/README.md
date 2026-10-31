# TRACE documentation

Start with the [product overview and target diagram](../README.md). Use the guide below for current implementation, development and delivery decisions.

## Find the right document

| Need | Source of truth |
| --- | --- |
| What works now, next work and current blockers | [Current status](current-status.md) |
| Product scope, ownership, settled choices and unresolved inputs | [Charter](charter.md) |
| Release gates, sprint sequence and evaluation requirements | [Capstone delivery plan](planning/capstone-project-plan.md) |
| Local readiness, S7 diagnostic applicability, owner decisions and dry run | [Local MVP gates](planning/local-mvp-acceptance.md) |
| Current components, interfaces and capability contracts | [Architecture](architecture/README.md) |
| Setup, supported commands, demos and quality checks | [Development](development.md) |
| Local operations and future hosted runbook requirements | [Operations](operations/README.md) |
| Trust, data transmission, protected reports and authority | [Security](security/README.md) |
| Why an architecture decision was made | [ADR index](adr/README.md) |
| Azure infrastructure and release responsibilities | [Deployment](../deploy/README.md), [cloud design](architecture/azure-cloud.md), [cloud backlog](planning/azure-cloud-backlog.md) |
| S7 platform design, repository boundaries and evidence migration review | [Platform design proposal](architecture/s7-platform-design.md), [migration inventory](planning/s7-repository-and-evidence-inventory.md) |
| S7 Azure budget scenario and missing cost inputs | [Azure cost scenario](planning/azure-cost-scenario-s7.md) |
| Independent .NET services and JSON-first source integration | [.NET testbed backlog](planning/dotnet-testbed-backlog.md) |
| Recommended responses and approved operational execution | [Response/remediation scope](planning/production-remediation-scope.md), [ADR 0018](adr/0018-flexible-ml-and-ranked-response-options.md) |
| Reproduce or interpret evaluation artifacts | [Evaluation guide](../evaluation/README.md) |
| Curated development knowledge inputs | [Corpus guide](../corpus/README.md) |
| Sprint reviews and superseded material | [Sprint 6 readiness review](sprints/sprint-06-review.md), [Archive](archive/README.md), [Sprint 1 snapshot](sprints/sprint-01-review.md), [Sprint 4 snapshot](sprints/sprint-04-review.md), [Sprint 5 review](sprints/sprint-05-review.md) |
| Prepare a sprint review or work with an agent | [Review template](sprints/sprint-review-template.md), [contributor/agent rules](../AGENTS.md) |

GitHub [Project Status](https://github.com/users/krispykrits/projects/2) is authoritative for work status. [Issues](https://github.com/krispykrits/TRACE/issues) own story acceptance criteria; [milestones](https://github.com/krispykrits/TRACE/milestones) group provisional sprints.

## Keep documentation current

Update the canonical document in the same PR as the behavior or decision:

| Change | Update |
| --- | --- |
| Code/interface/schema behavior | Its capability contract and affected development commands |
| Material progress or blocker | Current status; keep one dated snapshot rather than appending a changelog |
| Product scope or owner input | Charter; plan/issue acceptance criteria when delivery changes |
| Release or sprint dependency | Delivery plan and the affected GitHub issue/milestone |
| Consequential architecture decision | New ADR or explicit supersession/acceptance note, plus the ADR index |
| Deployment, security or operating procedure | Relevant guide with implementation status, prerequisites and verification evidence |

Keep current implementation, planned capability and historical evidence explicit. Link to authoritative detail instead of copying it into several guides. Use relative repository links so a PR previews its own documentation. Keep paragraphs focused and tables contiguous.

Review affected links, anchors, commands and status claims before handoff. Verify a current claim against source or live GitHub state; identify an unresolved acceptance gate instead of inferring completion from a closed issue or a green test.

## Preserve evidence while retiring documents

ADRs and dated sprint reviews preserve decision/acceptance history. Add a clear later-status note when needed; retain the original scope and measurements. Historical commands that require an old checkout must name it.

Corpus documents and evaluator review bundles are application/evaluation inputs, even when stored as Markdown. Preserve their bytes, identities and frozen report hashes. The [evaluation guide](../evaluation/README.md) explains exact historical rescoring.

Consolidate duplicate active guides before deleting them, update incoming links and record their replacement in the [archive index](archive/README.md). Archive source reviews or superseded instructions that still explain a decision. Git history and pinned original-version links preserve retired text without leaving competing active requirements.
