# Sprint 4 review — knowledge, retrieval and controlled tools

Date: 2026-10-13 (America/New_York). Prepared by: Codex. Reviewer: project owner. Scope: [roadmap S4](../planning/capstone-project-plan.md), integration gate [#19](https://github.com/krispykrits/TRACE/issues/19). **Scoped gate accepted through owner merge of [PR #49](https://github.com/krispykrits/TRACE/pull/49) at `a9db329`; live merge/Project Done verified 2026-10-13.** Sprint numbers denote scope increments, not dates or capacity commitments.

## Completion and acceptance evidence

Live GitHub issue/Project status and merges were verified at the start of #19. A merged PR establishes accepted scoped work, not operational usefulness or every release gate.

| Item | Live Project / repository state | Evidence | Remaining scope/gap |
| --- | --- | --- | --- |
| #15 | Done, PR #43 merged | Six curated development documents/18 stable chunks, generation/restart/current source policy; [corpus](../architecture/knowledge-corpus.md), ADR 0008 | Real source permission/adapter and hosted retention/restore are not supplied |
| #16 | Done, PR #44 merged | Lexical/semantic/hybrid exact baseline; real pinned cached CPU encoder comparison and repeat ranks; [retrieval](../architecture/knowledge-retrieval.md), ADR 0009 | Small development corpus; absent-query candidates do not establish answerability |
| #17 | Done, PR #45 merged | Owner's 211 blanket human endorsements with correct provenance; frozen lexical Recall@5 **0.9544**, MRR@5 **0.9137**, Recall@10 **0.9881** on 100 related queries; [acceptance](../../evaluation/reports/retrieval_passage_acceptance_v4.json), [revision record](../../evaluation/retrieval/judgment-revisions.md) | Development-only related variants; no independent held-out or Operational Pilot claim |
| #46 | Done, PR #47 merged | Capability/adapters/composition, import and installed-wheel gates; [layout](../architecture/package-layout.md), ADR 0010 | Structural checks complement source/security review; they are not a sandbox |
| #18 | Done, PR #48 merged at `f1d3923` | Six typed readonly tools, scope/citation checks, budgets/deadlines, read-only DB connections and correlated redacted audit; [catalog](../architecture/investigation-tools.md), ADR 0011 | No real operational adapter/authentication, hosted audit or mutation capability |
| #19 | Done, PR #49 merged at `a9db329` | [Integration contract](../architecture/scripted-evidence-package.md), [saved package](../../evaluation/reports/sprint_04_evidence_package_v1.json), [tool fixture report](../../evaluation/reports/tool_choices_development_v1.json) and actual assembled boundary tests | No LLM investigator implemented; provider/live acceptance remains #34 |

## Demonstration and verification

The prescribed evidence-only run queries logs, raw metrics and deployments, retrieves lexical knowledge, creates an observed timeline/context package and re-resolves all nine timeline events and five knowledge references. It uses actual local SQLite, immutable index artifacts and the #18 process/read-only boundary. Source data hash **`0a1e9530b819c4ce7288ffba489fc77d3d1900797c6bf4640d2cad5d158f1eb2`** repeats across fresh fixture databases. Real investigation IDs, attempt IDs and elapsed audit durations remain outside canonical data and vary normally.

The result is **partial**, not failed or complete: the authorized sanitized operational export is unavailable, and context omissions remain explicit. Nearby Notification deployment stays an observation without a causal label. Missing Payment capture and absent/stale knowledge remain explicit; reference prose cannot manufacture missing observations. Optional ML is not implemented or called, so its absence does not block the evidence-only workflow.

The independent tool fixture smoke executes **21 examples across 18 cases**, including acceptable alternatives and rejected SQL/shell, scope/path/limit/type/time/ID arguments. All scheduled examples pass. Model-selected tool-choice quality is **not run**; fixture proposals are not human-reviewed semantic judgments or an exhaustive choice rubric. Saved hash-verified rescoring reproduces the API result without a model.

Assembled tests prove repeat source data/hash, all-reference resolution, evaluator isolation, scoped failures, source withdrawal between search and resolution, expiry/absent knowledge, count truncation, source changes, actual process timeout, dependency failure, redacted logs and hostile retrieved prose. Failed references/tools return no source package. Historical accepted retrieval reports remain frozen at their recorded checkout; #19 neither rewrites their hashes nor retunes thresholds.

Commands/environment: CPython 3.12/Linux, pinned uv 0.12.17 and unchanged locked dependencies. Run the reproduction commands in the [integration contract](../architecture/scripted-evidence-package.md); `make integration-s4` provides a focused smoke, and fast CI runs the required complete gates. All required local checks pass: syntax, Ruff lint/format, mypy, architecture, 36 unit + 14 contract + 135 integration tests (185 total, including 16 CLI process checks), and installed-wheel verification. The initial package check could not resolve PyPI in the restricted sandbox; the same pinned build/dependencies passed with `UV_OFFLINE=1` from cache. Final-head CI is linked in #19/its PR.

| Evidence class | This gate |
| --- | --- |
| Synthetic/local source and core boundary checks | Run: real local SQLite/read-only workers, lexical scorer and actual fixture references |
| Cached/local embedding model | No new #19 encoder run; #16/#17 retain real pinned cached CPU comparison evidence |
| Generative model/provider and paid checks | Not run; provider/model/account/data handling/spending gates remain open |
| Authorized operational replay/shadow and operator feedback | Not run; no named authorized source/operator access is supplied |
| CloudWatch hosted audit, RDS/pgvector, Terraform/EC2 | Not provisioned/verified by S4; selected direction is retained |
| Production remediation | Not executed; separate deterministic executor and concrete staging/production approval gates remain required |

## Decisions, debt and Sprint 5 handoff

Accepted S4 decisions remain [ADR 0008](../adr/0008-local-corpus-generations-and-source-policy.md), [ADR 0009](../adr/0009-local-exact-knowledge-retrieval.md), [ADR 0010](../adr/0010-capability-packages-and-adapter-boundaries.md) and [ADR 0011](../adr/0011-read-only-tool-execution.md). #19 composes their contracts without a new architectural/dependency decision. Current scopes and clocks come from trusted composition; real deployment must protect sources, authenticate grants and configure audit delivery. Individual reference checks do not promise a simultaneous distributed snapshot or standing authorization.

| Next item/gate | Handoff and owner |
| --- | --- |
| #34 provider contract/adapter | Project owner must supply model spending/account restrictions before provider selection or paid validation, and credentials/permitted prompt-data handling before live acceptance. Offline contracts may proceed; no provider/model/fake fallback is selected here. |
| #35 validated assessment/citations | Reuse observed evidence/quoted context; retain hypotheses, uncertainty, missing information and abstention; revalidate references. Existence is not claim support. |
| #36 bounded execution/usage | Extend actual attempt/deadline records to model/call/retry/token/cost accounting. Tool safety defaults are not approved model or Operational Pilot budgets. |
| #37 evidence-first investigator | Compose provider/report/execution contracts only after the accepted #19 gate; preserve durable outcomes, source gaps and failure propagation. Do not import evaluator expectations or turn source prose into authority. |
| #38 CLI and scoped inspection/export | Preserve authenticated scope and redaction; fixture selectors are not production access grants. |
| #39 end-to-end scoring/review | Compare recorded outcomes with evaluator-only labels; independently evaluate model tool choices and support, keeping validation/final-test groups reserved. |

Real source/data access, independent operator study, hosted logging acceptance, measured operational thresholds, recovery/restore and support ownership remain separate work. University rubric/deadline, weekly capacity/calendar and broader budgets remain charter owner inputs. No dates, permissions or completion evidence are invented. Final capstone still requires the approved real production remediation after its separate gates; synthetic or staging-only evidence is insufficient.

## Review outcome

Prepared recommendation: accept the scoped Sprint 4 integration gate after owner PR review/merge and recorded green final checks; proceed to #34's allowed offline contract work, retaining its explicit live-provider decision blockers. No unresolved critical boundary failure is known in the exercised local integration cases. This is not a Local MVP release or production-usefulness decision.

Owner decision/date: **accepted scoped gate by PR #49 merge on 2026-10-13 at 00:17 America/New_York (`a9db329`)**, with live Project Done verified during the #34 handoff. Human retrieval endorsement in #17 is a distinct recorded event and is not reused as approval of this sprint review. The next allowed offline work is #34 / subtask #50; its live-provider gates remain open.
