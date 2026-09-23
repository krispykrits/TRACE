# TRACE current status

Last refreshed: 2026-09-23

## Direction

The owner-approved MVP-first plan and production-usefulness amendment are recorded in [the roadmap](planning/capstone-project-plan.md). The owner also approved [real production remediation](planning/production-remediation-scope.md) as a final-capstone requirement; only the initial investigation releases are read-only. A real authorized production action, verified after staging promotion, is required. Sprint numbers describe scope increments, not dated commitments. See [the charter](charter.md) for the product promise, release gates, success measures and unresolved owner inputs.

## Sprint 1

- Sprint 1 charter and scaffold decisions are recorded in [the charter](charter.md), [ADR 0001](adr/0001-repository-runtime-and-local-tooling.md), and [ADR 0002](adr/0002-terraform-and-ec2-cloud-deployment.md). The owner selected Terraform and EC2 as the Cloud MVP infrastructure/compute direction; exact topology and app rollout remain S7/S8 design.
- GitHub issue [#1](https://github.com/krispykrits/TRACE/issues/1) is closed. University rubric/deadline, weekly capacity/sprint duration, spending limits, pilot/data-access ownership, and production remediation target/action/approval authority remain unknown and explicitly gated.
- A minimal Python CLI scaffold for issue #2 is proposed in [draft PR #23](https://github.com/krispykrits/TRACE/pull/23). It has no domain behavior or cloud code. Clean install, build, and smoke-test checks have not been run because the local shell failed during process startup; the scaffold is not yet verified.
- Sprint 1 implementation issues #3–#6 remain planned.

## Next checks

1. Run `uv sync --locked`, build the package, and execute the CLI smoke tests from a clean checkout; address any failures before marking issue #2 complete.
2. Keep owner-dependent charter inputs as open gates until supplied or explicitly deferred; do not assign dates, budgets, pilot permissions, or thresholds.
3. Keep GitHub issue and Project status aligned with verified evidence.

## Sources of truth

- [Capstone plan and sprint gates](planning/capstone-project-plan.md)
- [Charter and decision gates](charter.md)
- [Repository/runtime ADR](adr/0001-repository-runtime-and-local-tooling.md)
- [Terraform and EC2 Cloud MVP ADR](adr/0002-terraform-and-ec2-cloud-deployment.md)
- [Production-usefulness review](planning/production-usefulness-review.md)
- [Approved production roadmap amendment](planning/production-roadmap-amendment.md)
- [Live roadmap and backlog](https://github.com/krispykrits/TRACE/issues/9)

## Repository workflow

The owner requires feature branches and PRs for repository changes. No direct commits or pushes to main, and no automatic merging. Terraform and EC2 are planning selections only. No AWS provisioning is authorized. Planning updates were merged via [PR #21](https://github.com/krispykrits/TRACE/pull/21); issue #2 work remains on the reviewable feature branch in [PR #23](https://github.com/krispykrits/TRACE/pull/23).
