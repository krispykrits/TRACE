# Architecture decision records

Use [the template](template.md) for a consequential decision. Record the owner, evidence, alternatives and a concrete condition for revisiting it. Implementation notes belong near the code they describe.

| ADR | Decision | Status |
| --- | --- | --- |
| [0001](0001-repository-runtime-and-local-tooling.md) | One modular TRACE repository, CPython 3.12/Linux and locked uv environment | Accepted foundation; dependency and integration choices remain gated |
| [0002](0002-terraform-and-ec2-cloud-deployment.md) | Terraform and EC2 for the first Cloud MVP target | Accepted direction; topology and release design pending S7/S8 |
| [0003](0003-cloudwatch-hosted-logging.md) | CloudWatch Logs for hosted application logs | Platform selected; deployment and hosted acceptance pending |

## Open decision register

These are gates, not inferred decisions. The [charter](../charter.md) is the full owner/input register; update the relevant ADR when a design choice is made.

| Input | Owner and gate | Current effect |
| --- | --- | --- |
| University rubric/deadline and weekly capacity/sprint length | Project owner, before calendar or scope commitment | Sprint numbers are increments, not dates |
| Pilot operator/team, service, data-access owner and source permission | Project owner and source owner, before replay or shadow use | Operational Pilot remains unvalidated |
| Runtime additions, model/provider, persistence and source adapters | Project team, when a specific capability is designed and evaluated | No dependency or API is implied by the scaffold; see [ADR 0001](0001-repository-runtime-and-local-tooling.md) |
| AWS/model spending constraints and measured workload | Project owner and relevant reviewer, before paid evaluation or provisioning | No AWS apply or paid experiment is authorized by the current foundation |
| EC2 topology, identity, Terraform state and application release/recovery | Project team and account owner, S7/S8 after budget/workload inputs | See [ADR 0002](0002-terraform-and-ec2-cloud-deployment.md) |
| CloudWatch alert recipient, target host and deployment role | Project owner/account owner, before hosted logging deployment | See [ADR 0003](0003-cloudwatch-hosted-logging.md) |
| Production action/target, service owner and approver | Project owner and service owner, before action-specific design and execution | No standing mutation permission; see [approved scope](../planning/production-remediation-scope.md) |

The [implementation review](../planning/production-usefulness-review.md) and [approved amendment](../planning/production-roadmap-amendment.md) define the reuse and Operational Pilot constraints behind these gates.
