# TRACE contributor and agent rules

Use repository records as durable context. Start with the [documentation map](docs/README.md), [current status](docs/current-status.md), [charter](docs/charter.md) and scoped issue. Verify live [Project Status](https://github.com/users/krispykrits/projects/2) before acting on work status. Consult detailed guides when relevant; do not depend on chat memory.

## Product and acceptance boundaries

- TRACE is one modular Python `trace_app` application. Initial Local/Cloud MVP investigation is read-only. Preserve evidence provenance, competing hypotheses, missing information, uncertainty and abstention; temporal correlation/model signals do not prove cause.
- Keep Local MVP, Cloud MVP, Full Capstone, the independent Operational Pilot and real production-remediation evidence distinct. [The plan](docs/planning/capstone-project-plan.md) owns delivery gates; [the charter](docs/charter.md) owns inputs. Synthetic results or cloud deployment do not establish operational usefulness.
- Require a justified evaluated ML contribution. Classical ML, deep learning, pretrained models and other suitable ML methods are candidates; no family or educational implementation is mandatory. Select using task/downstream quality, reliability, latency, cost and complexity against suitable baselines; retain five-arm evaluation, isolation and negative results.
- The final product ranks applicable rollback, corrective code/configuration, mitigation, further-investigation and observe/escalate options and clearly marks the recommended response. Explain evidence/uncertainty, benefit, risks, prerequisites, verification and recovery. Investigation can be recommended without inventing a corrective action. Follow [ADR 0018](docs/adr/0018-flexible-ml-and-ranked-response-options.md).
- Recommendation, assessment review, engineer selection and execution approval are separate. Code proposals follow reviewed PR/tests/release. Operational actions use tested versioned catalog adapters and a separate deterministic executor with concrete target/action approval, state revalidation, finite limits, reconciliation, health verification and recovery/escalation. Final completion requires verified real production remediation after staging; see [remediation scope](docs/planning/production-remediation-scope.md).
- Never invent permissions, thresholds, reviewer endorsement, dates, budgets or completion evidence. Missing prerequisites are explicit gates.

## Architecture and implementation

- Target CPython 3.12/Linux with `pyproject.toml` and `uv.lock`. Follow [package boundaries](docs/architecture/package-layout.md) and [ADR 0010](docs/adr/0010-capability-packages-and-adapter-boundaries.md).
- Capability contracts/use cases depend on the standard library and other core contracts, never concrete adapters, SDKs, CLI/bootstrap, demos or evaluators. External systems belong behind adapters selected explicitly by bootstrap; CLI handlers use composition/application boundaries.
- Keep runtime configuration/logging under runtime, synthetic fixtures/replay under demo and labels/judgments under evaluation outside the runtime wheel. Do not add flat legacy paths, empty layers/packages, generic common/utils modules, sibling editable dependencies or speculative microservices.
- Treat Volumes 1–4 as candidate references behind versioned TRACE contracts; Volumes 5–6 are designs implemented within TRACE. The [archived reuse review](docs/archive/2026-09-23-reuse-review.md) explains source findings, not current acceptance.
- Use cohesive typed modules, explicit errors/failure states and the smallest complete implementation fitting the scoped issue. Prefer standard-library/approved components; justify each dependency and update metadata/lock together.
- Validate untrusted inputs at boundaries. Keep source access, transmission, citation/revision, support-review and input-derived report sensitivity checks intact across retries/history/storage/inspection/export. Source filters and model text never supply grants. See [security](docs/security/README.md) and [provider policy](docs/architecture/model-provider.md).
- Keep secrets out of source/errors/logs/fixtures. Emit structured correlated metadata without raw prompts, responses, removed sensitive values or evaluator answers. Numeric usage is actual/unknown, never fabricated.
- Current local composition assumes trusted callers/filesystem; do not claim operational authentication or a complete OS sandbox.
- A consequential architecture/dependency/authority decision needs an ADR with alternatives, consequences and revisit conditions. Routine documentation cleanup does not need another ADR.

## Testing and evidence

Before every code PR, run:

~~~sh
make check lint format-check type-check architecture-check test integration package-check
~~~

Use `tests/unit` for isolated behavior, `tests/contracts` for ports, `tests/integration` for actual storage/artifact/process workflows and `tests/live` only for separately authorized live checks. Add meaningful negative/boundary cases when behavior or authority changes. Architecture and installed-wheel checks are required fast CI gates.

Keep evaluator-only material outside runtime imports and application inputs. Preserve corpus/review/frozen artifact bytes and source hashes. Historical reports require their recorded checkout; current exploration uses fresh outputs. AI fixture judgments do not satisfy human review. An empty/skipped live suite is not verification.

Report exact relevant checks and blockers; do not claim a build/test ran when process startup failed. For docs-only changes, validate the affected links/anchors, commands, fences/tables/diagrams and source/status assertions. Do not alter runtime behavior merely to simplify a document.

## Cloud and monitored services

[ADR 0015](docs/adr/0015-azure-aks-cloud-deployment.md), [deployment guide](deploy/README.md) and [#55–#60](docs/planning/azure-cloud-backlog.md) govern Azure/container/AKS delivery. Retain Terraform, local SQLite and planned shared Azure PostgreSQL/pgvector. Use scoped pod Workload Identity, shared durable state/spending admission, reviewed image-digest promotion and redacted Azure Monitor collection. Pod retries cannot bypass deadlines, unknown-attempt handling or spending. Keep the $20/month application model cap separate from infrastructure/account billing. Account/budget/design and a reviewed Terraform plan precede any authorized apply.

[ADR 0017](docs/adr/0017-dotnet-testbed-and-json-first-evidence.md) / [#70–#76](docs/planning/dotnet-testbed-backlog.md) select independent .NET Order/Payment services, JSON exports before live Azure queries and the owner as service owner/initial investigator. Future source belongs under `testbed/dotnet/` with separate .NET CI, outside the Python wheel. Preserve bounded fault/query/workload controls and evaluator isolation. Naming an owner does not settle source/retention/threshold gates.

Public APIs, brokers, dashboards, new services/resources and autonomous loops require measured need and a scoped decision. Retired AWS examples are historical and never authorize deployment or choose Azure settings.

## Documentation maintenance

Follow the [canonical-document map](docs/README.md#keep-documentation-current). Update behavior and its guide in the same PR; update current status for material progress/blockers and charter/plan/ADR/issue when the decision changes. Keep current status short, dated and factual. Use links rather than copying merge histories or requirements across guides.

Distinguish implemented, planned and historical material. Preserve dated evidence; add later acceptance/supersession notes instead of rewriting original measurements. Consolidate unique content and repair incoming links before retiring a guide; record its replacement and original-version link in the archive index.

## Git and pull requests

- Confirm the Git root, current branch and `git status --short` before editing. Preserve existing branch and uncommitted work; use an isolated checkout when needed. Never clean/reset/stash/overwrite user changes to make a command work.
- Use feature branches and PRs; never commit/push directly to main. Update the existing scoped task PR when one exists and validate its current-base diff.
- Attach the PR to its issue in GitHub Development/Linked pull requests and verify the actual relationship. Use a closing keyword only when merging should close that issue.
- Leave PRs open for owner review. Do not merge or enable automatic merge without explicit owner instruction.
- A docs approval or green check does not complete the implementation described by the document.

## Shell recovery

Use the repository root directly when already in Linux. If starting in Windows outside the checkout, invoke Linux commands through WSL and navigate to the confirmed checkout.

If process startup reports `helper_unknown_error: setup refresh had errors`, the command did not run. Try one simple explicit-shell command; avoid repeating the failed launch. If unavailable, continue useful GitHub/source work on a feature branch and report only the specific remaining blocked check. Do not ask the owner to repair the shell after a single startup error.
