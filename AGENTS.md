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
- Work in TRACE as one modular `trace_app` application, Python 3.12/Linux-first with pyproject.toml/uv.lock. Follow [ADR 0010](docs/adr/0010-capability-packages-and-adapter-boundaries.md) and [package boundaries](docs/architecture/package-layout.md). SQLite and local exact retrieval are implemented. The owner selected Azure, containers and AKS on 2026-10-14; [ADR 0015](docs/adr/0015-azure-aks-cloud-deployment.md) supersedes the EC2/RDS/CloudWatch hosting direction while retaining Terraform, PostgreSQL/pgvector and local behavior. [Cloud stories](docs/planning/azure-cloud-backlog.md) govern implementation; no AKS deployment/migration acceptance is implied. Numerical/encoder dependencies remain locked under ADR 0009.
- Treat Volumes 1–4 as educational references to adapt behind TRACE-owned contracts. Volumes 5–6 are designs to implement within TRACE. Never add sibling-directory runtime dependencies.
- Keep operational evidence and interfaces separate from evaluator-only labels. Preserve provenance and access scope. Investigation tools stay read-only; production mutations belong to the separate executor with concrete target/action approval, state revalidation, bounded execution, outcome verification and recovery/escalation. Scope approval is not standing execution authorization.
- Do not invent course deadlines, capacity, budgets, pilot permissions, performance thresholds or completion evidence. Record owner-dependent inputs as open gates until supplied.
- Use the roadmap and scoped issue acceptance criteria for work. Update [current status](docs/current-status.md) when a material decision, blocker, milestone or acceptance result changes; keep it brief and dated. Update the source-of-truth plan/ADR/issue as well when a decision itself changes.
- Read detailed planning/review documents when they apply to the task, rather than loading every project document for unrelated edits.
- For future cloud work use [Azure architecture](docs/architecture/azure-cloud.md), ADR 0015 and #55-#60. Keep the modular application; containerization does not authorize microservices, public API/UI, a broker or autonomous loops. Use scoped pod Workload Identity, shared durable state/spending reservations and intentional image-digest promotion; pod retries cannot bypass application admission. Preserve source/transmission/citation/review boundaries and keep infrastructure cost separate from the $20/month model cap. Require measured design, owner inputs and reviewed Terraform plan before any apply.

- The owner approved the [independent .NET testbed](docs/adr/0017-dotnet-testbed-and-json-first-evidence.md), JSON-first then live Azure source queries, and the project owner as service owner/initial investigator on 2026-10-14. Follow [#69-#76](docs/planning/dotnet-testbed-backlog.md): monitored workload source under `testbed/dotnet/` when implemented, separate .NET CI, no Python runtime dependency or wheel content. Preserve evaluator isolation, current source/transmission/citation/review protections, bounded fault/workload/query controls and honest controlled-testbed claims; role confirmation does not imply completed access/retention/threshold gates.

## Coding and design practices

- Place source-neutral evidence, knowledge and investigation contracts/use cases in their capability packages. Core code may depend on the standard library and other core contracts, never adapters, SDKs, CLI/bootstrap, demos or evaluator code. Implement external systems under adapters and select them through bootstrap; CLI handlers use application/composition boundaries, not concrete adapters.
- Keep configuration/logging under runtime, synthetic fixtures/replay under demo, and evaluator labels/judgments under evaluation outside the runtime wheel. Do not restore old flat module paths, add empty packages or a generic common/utils dumping ground. New capability/boundary decisions update the ADR, package guide and import checker together.
- Put isolated checks in tests/unit, port requirements in tests/contracts, actual SQLite/artifact/process/evaluator workflows in tests/integration and separately authorized live checks in tests/live. An empty live suite cannot count as verification. Runtime code cannot import test fixtures or evaluator material.
- Before every code PR, run make check lint format-check type-check architecture-check test integration package-check. Architecture checks and installed-wheel verification are required fast CI gates. Add negative dependency/boundary cases when changing authority or adapters. Preserve frozen evaluation reports and use their recorded checkout for historical rescoring; new source manifests include nested implementation modules.

- Start from the scoped issue, acceptance criteria, and existing decisions. Prefer the smallest complete change that fits them; do not add speculative features, abstractions, services, or dependencies.
- Use Clean Architecture as a dependency-direction guide: keep domain rules independent of frameworks and infrastructure, put use-case orchestration behind clear application boundaries, and isolate external systems in adapters at the edges. Organize code around responsibilities and stable boundaries; introduce layers only when they protect a real boundary in the current scope. Use explicit adapters for external systems and test seams. Avoid empty layers, generic frameworks, and premature microservices.
- Keep functions and modules cohesive, name concepts clearly, and make control flow and failure behavior explicit. Use Python 3.12 type annotations for public interfaces. Prefer standard-library or already-approved components; justify each new dependency and update `pyproject.toml` and `uv.lock` together.
- Validate untrusted input at boundaries. Return actionable errors and propagate dependency failures; do not hide failures with silent fallbacks or claim confidence unsupported by evidence. Keep secrets out of source, logs, errors, and test fixtures.
- Preserve least privilege, provenance, timestamps, authorization scope, and redaction. Investigation paths remain read-only. Keep any production mutation in the separate approved executor boundary.
- Add deterministic tests for changed behavior and important failure cases. Keep tests independent of live services, credentials, time, and network unless the issue explicitly requires an isolated integration check. Run the relevant documented checks when the environment permits and report checks that could not run.
- Add structured, correlated logging at meaningful boundaries without logging secrets or unnecessary sensitive content. Document configuration, setup, and operational behavior where contributors need it.
- Record consequential architecture or dependency decisions in an ADR with context, alternatives, tradeoffs, and revisit conditions. Do not create an ADR for routine implementation details; keep existing decisions and source-of-truth documents aligned when a decision changes.

## Local command execution and recovery

The TRACE repository is the primary source folder for this project. New Codex tasks should start with the repository root as their working directory; use that root directly for commands and `AGENTS.md` discovery. Confirm the actual Git root before editing.

The local environment uses WSL Ubuntu 24.04. If a task starts in Windows PowerShell outside the repo, run Linux project commands through WSL and navigate to the checkout only as a fallback:
  ```powershell
  wsl.exe -d Ubuntu-24.04 -- bash -lc 'cd ~/projects/applied-ai/TRACE && git status --short && git branch --show-current'
  ```
If the active shell is already Linux and starts at the repo root, do not add another `cd`; run the command directly.
- Before editing, confirm the repository root, current branch and `git status --short`. Preserve existing branch and uncommitted changes. Never clean, reset, stash, or overwrite user changes just to make a command work.
- If command startup returns `helper_unknown_error: setup refresh had errors` or fails during process creation, the command did not run. Do not report it as a failing project command or test. Try one simple command using an explicit shell and WSL invocation. Avoid repeating the same failed launch.
- If the local shell bridge remains unavailable, continue useful work that does not require it. Check repository files, issues and PR state through available GitHub tools; make any remote edits on a feature branch with a PR, using current file versions. Do not assume the local checkout is clean or synchronized with GitHub.
- For code changes made without local execution, state that tests/builds could not be run; do not claim the implementation is verified. If a required check depends on the local checkout, finish other useful review/preparation first, then tell the owner exactly which check is blocked and why.
- Do not ask the owner to restore the shell after one launch error. Ask only when the remaining required work truly depends on local execution and no available route can complete it.

## Git and pull-request workflow

- Use feature branches and pull requests for every repository change. Never commit directly to or push directly to main.
- Update the existing task PR when one exists; merge/rebase main into the feature branch as needed and validate the resulting diff.
- Attach every task PR to its scoped GitHub user story or issue in GitHub’s Development/Linked pull requests relationship, and verify the link before handoff. Use a closing keyword in the PR description when merging should close the issue; otherwise link it without automatic closure. A branch name or plain issue mention alone is insufficient.
- Leave PRs open for the owner's review. Do not merge a PR or enable automatic merging unless the owner explicitly asks.
- Record scope/status accurately: a documentation approval or green check does not mark implementation complete.

## Hosted logging

Azure Monitor / Log Analytics is the cloud logging baseline under [ADR 0015](docs/adr/0015-azure-aks-cloud-deployment.md). Keep application JSON/redaction separate from platform-managed AKS collection and raw prompt/response capture disabled. [#59](https://github.com/krispykrits/TRACE/issues/59) requires real hosted correlation, privacy/access, retention and collector recovery evidence. [ADR 0003](docs/adr/0003-cloudwatch-hosted-logging.md) and deploy/cloudwatch are superseded historical preparation. Historical #3 local acceptance is retained; its closed state never proved hosted delivery. Azure account/region, collection shape, retention and infrastructure spending inputs remain gated.

## Owner scope clarification — 2026-10-15

Follow [ADR 0018](docs/adr/0018-flexible-ml-and-ranked-response-options.md) for future work. The owner approved a use-case-appropriate evaluated ML contribution; classical ML, deep learning, pretrained models and other suitable ML methods are candidates. No algorithm family or educational implementation is mandatory. Select the task/method with measured quality, reliability, latency, cost and operational complexity against appropriate baselines; preserve five-arm evaluation, leakage isolation and evidence-only operation if the ML capability fails.

The final product proposes multiple applicable responses: rollback, corrective code/configuration modification, temporary mitigation, further investigation and observe/escalate. Rank supported options, identify the recommended response and explain evidence, uncertainty, benefits, risks, prerequisites, verification and recovery. Further investigation can be recommended; do not invent a corrective action to fill the menu. Engineer selection and action-specific execution approval remain separate. Code changes follow reviewed PR/tests/release; operational actions use tested versioned catalog adapters and the deterministic executor. This is a planned final capability, not an extension of current read-only tool authority or accepted assessment schemas. Preserve historical implementation/review evidence; record new scope and acceptance explicitly.
