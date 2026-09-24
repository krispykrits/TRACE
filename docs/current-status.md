# TRACE current status

Last refreshed: 2026-09-24

## Direction

The owner-approved MVP-first plan and production-usefulness amendment are recorded in [the roadmap](planning/capstone-project-plan.md). The owner also approved [real production remediation](planning/production-remediation-scope.md) as a final-capstone requirement; only the initial investigation releases are read-only. Sprint numbers describe scope increments, not dated commitments. See [the charter](charter.md) for product gates and unresolved owner inputs.

## Sprint 1

- Sprint 1 charter and scaffold decisions are recorded in [the charter](charter.md), [ADR 0001](adr/0001-repository-runtime-and-local-tooling.md), and [ADR 0002](adr/0002-terraform-and-ec2-cloud-deployment.md). Terraform and EC2 remain the approved Cloud MVP direction; deployment details belong to S7/S8.
- Issue [#1](https://github.com/krispykrits/TRACE/issues/1) is closed. University rubric/deadline, weekly capacity/sprint duration, spending limits, pilot/data-access ownership, and production remediation target/action/approval authority remain open gates.
- Issue [#2](https://github.com/krispykrits/TRACE/issues/2) is closed and its scaffold PR [#23](https://github.com/krispykrits/TRACE/pull/23) is merged. The PR reports that clean-checkout install, build, and smoke checks were not run; no new verification evidence is recorded here.
- Issue [#3](https://github.com/krispykrits/TRACE/issues/3) is implemented on draft [PR #24](https://github.com/krispykrits/TRACE/pull/24): validated configuration, JSON logs with correlation and redaction, a check-config CLI path, documentation, and deterministic tests. The local shell launcher failed before starting PowerShell/WSL, so package checks and tests remain unrun. Keep #3 open pending verification and review.
- No model provider or model artifact is implemented in the scaffold. check-config validates only the current environment/log settings; it does not claim provider readiness. The development guide records the required no-fallback behavior for future production capabilities.

## Next checks

1. From a clean checkout, run `uv sync --locked`, the unittest suite, package build, and `trace-app check-config` for valid and invalid settings; address any failures before closing #3.
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

The owner requires feature branches and PRs for repository changes. No direct commits or pushes to main, and no automatic merging. Planning updates were merged via [PR #21](https://github.com/krispykrits/TRACE/pull/21), and scaffold work was merged via [PR #23](https://github.com/krispykrits/TRACE/pull/23). Issue #3 remains open on draft [PR #24](https://github.com/krispykrits/TRACE/pull/24). No AWS resources are authorized by the planning selections.
