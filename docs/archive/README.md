# Documentation archive

Historical material explains past decisions and evidence. Use [the documentation map](../README.md) for current behavior and requirements.

## Retained records

| Record | Interpretation |
| --- | --- |
| [Educational reuse review](2026-09-23-reuse-review.md) | September 23 static/source review and observed local test limitations; current ML/reuse selection follows ADR 0018 |
| [CloudWatch preparation](cloudwatch-preparation.md) | Superseded AWS instructions; not an Azure runbook or current provisioning authorization |
| [Sprint 1 review](../sprints/sprint-01-review.md) | Dated foundation snapshot; original status/limits retained |
| [Sprint 4 review](../sprints/sprint-04-review.md) | Dated integration/acceptance snapshot; later status is noted separately |
| [ADRs](../adr/README.md) | Scoped decision history, including superseded AWS choices |
| [Evaluation records](../../evaluation/README.md) | Frozen judgments/reports and exact scorer checkout requirements |

## Consolidated guides

The October 15 documentation audit consolidated the following active guides. Original versions are preserved by commit permalink and Git history.

| Retired path | Original text | Current home |
| --- | --- | --- |
| `docs/architecture/interfaces.md` | [Snapshot](https://github.com/krispykrits/TRACE/blob/698c56be84872337aab31ac158c40403df974e56/docs/architecture/interfaces.md) | [Architecture interfaces](../architecture/README.md#interfaces), [current commands](../development.md) and capability contracts |
| `docs/planning/production-roadmap-amendment.md` | [Snapshot](https://github.com/krispykrits/TRACE/blob/698c56be84872337aab31ac158c40403df974e56/docs/planning/production-roadmap-amendment.md) | [Charter](../charter.md), [delivery/acceptance plan](../planning/capstone-project-plan.md), [security](../security/README.md) and [response scope](../planning/production-remediation-scope.md) |
| `docs/planning/production-usefulness-review.md` | [Snapshot](https://github.com/krispykrits/TRACE/blob/698c56be84872337aab31ac158c40403df974e56/docs/planning/production-usefulness-review.md) | [Archived review](2026-09-23-reuse-review.md) |
| `deploy/cloudwatch/README.md` | [Snapshot](https://github.com/krispykrits/TRACE/blob/698c56be84872337aab31ac158c40403df974e56/deploy/cloudwatch/README.md) | [Archived preparation](cloudwatch-preparation.md), [current deployment guide](../../deploy/README.md) |

Current status and the delivery plan are concise current records. Their pre-cleanup narrative snapshots remain in [Git history](https://github.com/krispykrits/TRACE/blob/698c56be84872337aab31ac158c40403df974e56/docs/current-status.md) and [the previous plan](https://github.com/krispykrits/TRACE/blob/698c56be84872337aab31ac158c40403df974e56/docs/planning/capstone-project-plan.md).

Preserve original corpus/evaluator artifact bytes and hashes. Archival Markdown is not permission to ingest reviewer answers, execute old infrastructure commands or assert a historical result as current validation.

## Retired Local MVP comparison versions

On 2026-10-16 the owner requested keeping only the latest Local MVP comparison in the working tree. [Comparison v3](../../evaluation/reports/local_mvp_comparison_offline_v3/README.md) is the current retained run. Earlier measurements remain unchanged in Git history; restore their artifact directories and use each README’s recorded implementation checkout for historical rescoring. This cleanup does not remove the recorded negative results or change acceptance thresholds.

| Retired directory | Original evidence | Replacement |
| --- | --- | --- |
| `evaluation/reports/local_mvp_comparison_offline_v1` | [Original v1](https://github.com/krispykrits/TRACE/tree/ccfc3f49af33ab508b4abe3c5eceaab6a98fa612/evaluation/reports/local_mvp_comparison_offline_v1) | [Latest comparison](../../evaluation/reports/local_mvp_comparison_offline_v3/README.md) |
| `evaluation/reports/local_mvp_comparison_offline_v2` | [Original v2](https://github.com/krispykrits/TRACE/tree/ccfc3f49af33ab508b4abe3c5eceaab6a98fa612/evaluation/reports/local_mvp_comparison_offline_v2) | [Latest comparison](../../evaluation/reports/local_mvp_comparison_offline_v3/README.md) |
