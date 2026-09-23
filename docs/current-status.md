# TRACE current status

Last refreshed: 2026-09-23

## Direction

The owner-approved MVP-first plan and production-usefulness amendment are recorded in [the roadmap](planning/capstone-project-plan.md). The owner also approved [real production remediation](planning/production-remediation-scope.md) as a final-capstone requirement; only the initial investigation releases are read-only. A real authorized production action, verified after staging promotion, is required. Sprint numbers describe scope increments, not dated commitments. See [the charter](charter.md) for the product promise, release gates, success measures and unresolved owner inputs.

## Sprint 1

- Sprint 1 charter and scaffold decisions are recorded in [the charter](charter.md), [ADR 0001](adr/0001-repository-runtime-and-local-tooling.md), and [ADR 0002](adr/0002-terraform-and-ec2-cloud-deployment.md). The owner selected Terraform and EC2 as the Cloud MVP infrastructure/compute direction; exact topology and app rollout remain S7/S8 design.
- GitHub issue [#1](https://github.com/krispykrits/TRACE/issues/1) remains open. University rubric/deadline, weekly capacity/sprint duration, spending limits, pilot/data-access ownership, and production remediation target/action/approval authority are still unknown and are explicitly gated.
- Sprint 1 implementation issues #2–#6 remain planned. No application scaffold, cloud resources, or domain behavior has been implemented in this work.

## Next checks

1. [PR #20](https://github.com/krispykrits/TRACE/pull/20) merged the persistent project context. Review [PR #21](https://github.com/krispykrits/TRACE/pull/21), which records the Terraform/EC2 direction.
2. Supply or explicitly defer the owner-dependent charter inputs; keep schedule and spending commitments unassigned until then.
3. Start the skeleton from ADR 0001 and issue #2 once Sprint 1 implementation is authorized; keep issue status aligned with actual evidence.

## Sources of truth

- [Capstone plan and sprint gates](planning/capstone-project-plan.md)
- [Charter and decision gates](charter.md)
- [Repository/runtime ADR](adr/0001-repository-runtime-and-local-tooling.md)\n- [Terraform and EC2 Cloud MVP ADR](adr/0002-terraform-and-ec2-cloud-deployment.md)
- [Production-usefulness review](planning/production-usefulness-review.md)
- [Approved production roadmap amendment](planning/production-roadmap-amendment.md)
- [Live roadmap and backlog](https://github.com/krispykrits/TRACE/issues/9)

## Repository workflow

The owner requires feature branches and PRs for repository changes. No direct commits or pushes to main, and no automatic merging. Terraform and EC2 are planning selections only. No AWS provisioning is authorized. This planning update is on branch `terraform-ec2-cloud-mvp` in [PR #21](https://github.com/krispykrits/TRACE/pull/21).
