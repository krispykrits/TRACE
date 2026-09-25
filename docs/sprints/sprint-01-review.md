# Sprint 1 foundation review

Date: 2026-09-25. Status: evidence draft for owner review. Scope: [Sprint 1 in the capstone plan](../planning/capstone-project-plan.md#sprint-1--foundation), [issue #6](https://github.com/krispykrits/TRACE/issues/6). The live TRACE Project lists #1–#5 as Done and #6 as In progress on this date. A Project state or closed issue does not replace a missing acceptance check.

## Completed work and acceptance evidence

| Issue | Project state | Evidence and what it proves | Incomplete acceptance or decision gate |
| --- | --- | --- | --- |
| [#1 Charter](https://github.com/krispykrits/TRACE/issues/1) | Done | [Charter](../charter.md), [ADR 0001](../adr/0001-repository-runtime-and-local-tooling.md), [ADR 0002](../adr/0002-terraform-and-ec2-cloud-deployment.md) and merged [PR #20](https://github.com/krispykrits/TRACE/pull/20)/[PR #21](https://github.com/krispykrits/TRACE/pull/21) record MVP/capstone/pilot gates, repository/runtime and Terraform/EC2 direction, metric definitions and open inputs. | Owner has not supplied rubric/deadline, capacity, overall spending limit, pilot source/access owner or production target/approver. These remain explicit charter gates. |
| [#2 Scaffold](https://github.com/krispykrits/TRACE/issues/2) | Done | Merged [PR #23](https://github.com/krispykrits/TRACE/pull/23) contains package/CLI/smoke tests. The clean-worktree demonstration below verifies locked install, help/version, wheel/sdist build and tests twice; `git status` in the temporary checkout showed no tracked source changes. | PR #23 merged without its requested command run; this review supplies the later local verification. No domain, provider or cloud behavior is claimed. |
| [#3 Configuration/logging](https://github.com/krispykrits/TRACE/issues/3) | Done | Merged [PR #24](https://github.com/krispykrits/TRACE/pull/24), [development guide](../development.md) and the demonstration below verify configuration validation/precedence, correlated JSON and secret redaction in offline tests and a CLI sample. [ADR 0003](../adr/0003-cloudwatch-hosted-logging.md) records the selected hosted platform. | Hosted acceptance added to #3 is **not verified**: no Terraform plan/apply, approved host/collector, CloudWatch delivery/search, rotation or outage recovery evidence. Notification email and authorized deployment role are pending. The closed issue/Done state should be reconciled with that acceptance gap. |
| [#4 Local tasks](https://github.com/krispykrits/TRACE/issues/4) | Done | Merged [PR #25](https://github.com/krispykrits/TRACE/pull/25), [development guide](../development.md) and the two clean-worktree runs below verify documented tasks and repeatability. Both runs pass the process-boundary tests, including fixture cleanup after a deliberately failing CLI process. | The fixture is offline and does not establish live-provider or Operational Pilot behavior. |
| [#5 CI](https://github.com/krispykrits/TRACE/issues/5) | Done | Merged [PR #26](https://github.com/krispykrits/TRACE/pull/26); [passing corrected-head workflow](https://github.com/krispykrits/TRACE/actions/runs/36182785735); [intentional Ruff failure](https://github.com/krispykrits/TRACE/actions/runs/36182405598). The workflow has read-only contents permission and the fast job uses no provider secrets or paid calls. | The manual provider job has no live tests and is not live-provider evidence. |
| [#6 Docs/IaC foundations](https://github.com/krispykrits/TRACE/issues/6) | In progress | [ADR index/template](../adr/README.md), [architecture view](../architecture/README.md), [IaC responsibilities](../../deploy/README.md) and [review template](sprint-review-template.md) are ready for review. The demonstration and open decision register are below. | Owner review and PR checks are pending; no AWS resource is provisioned by this issue. |

## Foundation demonstration

A separate detached Git worktree at merged main commit `d034214` provided a fresh checkout, with CPython 3.12.3 and uv 0.12.17. For **each of two cycles**, the following commands exited successfully in order:

```sh
make clean
make sync
make check
make lint
make format-check
make type-check
make test
make integration
make run
uv run --locked trace-app --version
uv run --locked trace-app check-config --environment test
uv build
uv lock --check
```

Each cycle reported 19 passing unit tests and 2 passing process tests, Ruff clean, mypy clean for 9 source files, CLI help/version 0.1.0, a parseable correlated configuration log, and successfully built wheel/sdist. The process tests include a failed-run cleanup assertion and two isolated successful subprocess runs. The sequence began with `make clean` each time and required no production credentials, AWS action or paid model call. A preliminary extra `uv build --locked` command stopped because uv 0.12.17 does not accept that option; the supported `uv build` command and the entire sequence then passed twice. [PR #26's corrected-head run](https://github.com/krispykrits/TRACE/actions/runs/36182785735) supplies remote CI evidence; the current issue #6 PR check is pending.

This demonstrates the **synthetic/offline foundation**. It does not verify CloudWatch hosted delivery, a live provider, a real incident source, the independent Operational Pilot, or production remediation. No cloud resources were provisioned for this review.

## Decisions, architecture and debt

- [ADR 0001](../adr/0001-repository-runtime-and-local-tooling.md) and [the implementation review](../planning/production-usefulness-review.md)/[approved amendment](../planning/production-roadmap-amendment.md) set one modular TRACE package and selective educational reuse behind TRACE-owned contracts. V1 supplies triage vocabulary/fixtures; V2 classical ML is a later evaluated candidate; V3 deep learning is conditional; V4 retrieval is adapted; V5/V6 are design inputs. The new [architecture view](../architecture/README.md) distinguishes implemented CLI/config/logging from planned investigation, data/API and executor boundaries.
- [ADR 0002](../adr/0002-terraform-and-ec2-cloud-deployment.md) selects Terraform/EC2, while topology, Terraform state/access, cost, identity, release, rollback and teardown remain S7/S8 design gates. [ADR 0003](../adr/0003-cloudwatch-hosted-logging.md) selects hosted logs; delivery remains unverified.
- Debt: reconcile #3's closed/Done status with its hosted acceptance gap. Keep provider/artifact readiness and source APIs unclaimed until implemented. No numeric quality, latency or cost target is frozen without the relevant owner/reviewer.

## Operational Pilot and access gates

No pilot operator/team, service/source owner, authorized real or sanitized source, replay approval, or shadow approval has been recorded. There is no comparison to an operator's current workflow. Before real data is accepted, decide source retention/deletion/revocation, redaction, evidence snapshot access, recovery/restore, support ownership, and quality/latency/cost thresholds with the responsible owners. The [charter](../charter.md) records owners and gates. Offline tests and the capstone demo cannot satisfy Operational Pilot acceptance.

The final production-remediation requirement is also separate: no production target, action, service owner or approver is selected. [Approved scope](../planning/production-remediation-scope.md) requires staging validation and explicit proposal-bound production approval before execution.

## Lessons and next dependencies

The scaffold can be recreated without inherited educational environments, and the CI failure gate has direct evidence. Sprint 2's synthetic workflow can proceed within the charter, but source-neutral provenance and access contracts must be designed before real-source use. Owner-supplied rubric/capacity, spending, pilot access and production target inputs remain open; no dates or budget are inferred. Review outcome: pending owner review of this issue #6 PR and follow-up on the #3 hosted acceptance discrepancy.
