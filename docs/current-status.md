# TRACE current status

Last refreshed: 2026-09-25

## Direction

The owner-approved MVP-first plan and production-usefulness amendment are recorded in [the roadmap](planning/capstone-project-plan.md). The owner also approved [real production remediation](planning/production-remediation-scope.md) as a final-capstone requirement; only the initial investigation releases are read-only. Sprint numbers describe scope increments, not dated commitments. See [the charter](charter.md) for product gates and unresolved owner inputs.

## Sprint 1

- Sprint 1 charter and scaffold decisions are recorded in [the charter](charter.md), [ADR 0001](adr/0001-repository-runtime-and-local-tooling.md), and [ADR 0002](adr/0002-terraform-and-ec2-cloud-deployment.md). Terraform and EC2 remain the approved Cloud MVP direction; deployment details belong to S7/S8.
- Issue [#1](https://github.com/krispykrits/TRACE/issues/1) is closed. University rubric/deadline, weekly capacity/sprint duration, spending limits, pilot/data-access ownership, and production remediation target/action/approval authority remain open gates.
- Issue [#2](https://github.com/krispykrits/TRACE/issues/2) is closed and scaffold PR [#23](https://github.com/krispykrits/TRACE/pull/23) is merged. Its PR did not run clean-checkout install/build/smoke checks; the two-cycle [Sprint 1 foundation demonstration](sprints/sprint-01-review.md#foundation-demonstration) now verifies them locally.
- Issue [#3](https://github.com/krispykrits/TRACE/issues/3) is closed on GitHub and PR [#24](https://github.com/krispykrits/TRACE/pull/24) is merged. The issue body and deployment notes still lack hosted acceptance evidence: no CloudWatch deployment/delivery is recorded. Issue state does not prove hosted acceptance.
- Issue [#4](https://github.com/krispykrits/TRACE/issues/4) implementation is merged in [PR #25](https://github.com/krispykrits/TRACE/pull/25): documented Makefile tasks, an offline real-process CLI integration test for repeat runs and cleanup after failure, and reviewed environment-gap notes. The two-cycle [Sprint 1 foundation demonstration](sprints/sprint-01-review.md#foundation-demonstration) now supplies local repeat-run and fixture-cleanup evidence.
- Issue [#5](https://github.com/krispykrits/TRACE/issues/5) implementation is merged in [PR #26](https://github.com/krispykrits/TRACE/pull/26). Fast credential-free checks passed locally and in [GitHub Actions run #36182512898](https://github.com/krispykrits/TRACE/actions/runs/36182512898) on Python 3.12.3/uv 0.12.17. An intentional Ruff violation failed the lint step and skipped later steps in [run #36182405598](https://github.com/krispykrits/TRACE/actions/runs/36182405598); the corrected head passed in [run #36182785735](https://github.com/krispykrits/TRACE/actions/runs/36182785735). The opt-in provider gate is not live-provider evidence; no provider tests are configured.
- Issue [#6](https://github.com/krispykrits/TRACE/issues/6) is in review on [PR #27](https://github.com/krispykrits/TRACE/pull/27): the [ADR index](adr/README.md), [architecture view](architecture/README.md), [IaC foundation](../deploy/README.md), [review template](sprints/sprint-review-template.md) and [Sprint 1 evidence draft](sprints/sprint-01-review.md) are available for owner review. The PR fast quality gate passed; no AWS resources were provisioned.
- No model provider or model artifact is implemented in the scaffold. check-config validates only the current environment/log settings; it does not claim provider readiness. The development guide records the required no-fallback behavior for future production capabilities.

## Next checks

1. Review the [Sprint 1 evidence draft](sprints/sprint-01-review.md) and issue #6 foundation artifacts; local two-cycle verification is recorded there.
2. Configure CloudWatch Logs during S8 Cloud MVP deployment and verify hosted delivery, retention, rotation and collector recovery at S9; reconcile #3's closed state with its still-unverified hosted acceptance.
3. Keep owner-dependent charter inputs as open gates until supplied or explicitly deferred; do not assign dates, budgets, pilot permissions, or thresholds.

## Sources of truth

- [Capstone plan and sprint gates](planning/capstone-project-plan.md)
- [Charter and decision gates](charter.md)
- [Repository/runtime ADR](adr/0001-repository-runtime-and-local-tooling.md)
- [Terraform and EC2 Cloud MVP ADR](adr/0002-terraform-and-ec2-cloud-deployment.md)
- [Production-usefulness review](planning/production-usefulness-review.md)
- [Approved production roadmap amendment](planning/production-roadmap-amendment.md)
- [Live roadmap and backlog](https://github.com/krispykrits/TRACE/issues/9)

## Repository workflow

The owner requires feature branches and PRs for repository changes. No direct commits or pushes to main, and no automatic merging. Planning updates were merged via [PR #21](https://github.com/krispykrits/TRACE/pull/21), and scaffold work was merged via [PR #23](https://github.com/krispykrits/TRACE/pull/23). Configuration/logging work is merged via [PR #24](https://github.com/krispykrits/TRACE/pull/24); issue #4 implementation is merged via [PR #25](https://github.com/krispykrits/TRACE/pull/25); issue #5 implementation is merged via [PR #26](https://github.com/krispykrits/TRACE/pull/26). Issue #6 foundation artifacts are under review on [PR #27](https://github.com/krispykrits/TRACE/pull/27). No AWS resources are authorized by the planning selections.

## Hosted logging decision — 2026-09-24

The owner selected Amazon CloudWatch Logs. PR #24 includes [ADR 0003](adr/0003-cloudwatch-hosted-logging.md), an agent collection example and a hosted verification procedure. Account 267653922622, us-east-2, seven-day retention and a $5/month alert are selected. Alert email and target host/environment remain pending. The current aws-app-local identity lacks logs:DescribeLogGroups; an authorized deployment profile/role is required. No CloudWatch deployment or hosted delivery is verified; the issue's closed state does not satisfy hosted acceptance.
