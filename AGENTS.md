# TRACE project context

Use repository records as the durable source of project context across Codex tasks; do not depend on another chat's history.

## Core direction

TRACE is an incident intelligence and controlled-response platform. The initial Local/Cloud MVP investigation workflow is read-only; final capstone completion requires at least one real, explicitly approved and verified production remediation through a separate deterministic executor. Diagnosis preserves provenance, competing hypotheses, missing information, uncertainty and abstention. Time correlation alone does not prove root cause.

- The approved delivery plan is [the capstone roadmap](docs/planning/capstone-project-plan.md).
- The current charter, settled constraints and owner-dependent decision gates are in [docs/charter.md](docs/charter.md).
- Current work and blockers are summarized in [docs/current-status.md](docs/current-status.md); verify live issue/Project state before acting on status.
- Consult the [production-usefulness review](docs/planning/production-usefulness-review.md) and [approved amendment](docs/planning/production-roadmap-amendment.md) when changing reuse boundaries, production-readiness claims, operational-pilot scope, or reliability/security requirements.
- GitHub [issue #9](https://github.com/krispykrits/TRACE/issues/9) is the roadmap tracker; [issue #1](https://github.com/krispykrits/TRACE/issues/1) tracks charter resolution. GitHub Project Status is authoritative for work status.
- The [approved production remediation scope](docs/planning/production-remediation-scope.md) defines the final action requirement, staging-to-production gates, approval binding and verification. Simulation or staging alone cannot satisfy production remediation acceptance.

## Working rules

- Keep Local MVP, Cloud MVP, Full Capstone and the independent Operational Pilot gates separate; real production remediation is an additional final-capstone acceptance requirement. Synthetic evaluation or cloud deployment does not prove operational usefulness.
- Work in the TRACE repository as one modular Python application. Current scaffold decisions are Python 3.12/Linux-first, `pyproject.toml`, `uv.lock`, and an empty runtime dependency set until needed; see ADR 0001. Terraform and EC2 are the approved Cloud MVP deployment direction; see ADR 0002 for deferred design choices.
- Treat Volumes 1–4 as educational references to adapt behind TRACE-owned contracts. Volumes 5–6 are designs to implement within TRACE. Never add sibling-directory runtime dependencies.
- Keep operational evidence and interfaces separate from evaluator-only labels. Preserve provenance and access scope. Investigation tools stay read-only; production mutations belong to the separate executor with concrete target/action approval, state revalidation, bounded execution, outcome verification and recovery/escalation. Scope approval is not standing execution authorization.
- Do not invent course deadlines, capacity, budgets, pilot permissions, performance thresholds or completion evidence. Record owner-dependent inputs as open gates until supplied.
- Use the roadmap and scoped issue acceptance criteria for work. Update [current status](docs/current-status.md) when a material decision, blocker, milestone or acceptance result changes; keep it brief and dated. Update the source-of-truth plan/ADR/issue as well when a decision itself changes.
- Read detailed planning/review documents when they apply to the task, rather than loading every project document for unrelated edits.

## Git and pull-request workflow

- Use feature branches and pull requests for every repository change. Never commit directly to or push directly to main.
- Update the existing task PR when one exists; merge/rebase main into the feature branch as needed and validate the resulting diff.
- Leave PRs open for the owner's review. Do not merge a PR or enable automatic merging unless the owner explicitly asks.
- Record scope/status accurately: a documentation approval or green check does not mark implementation complete.
