# Sprint 6 local readiness review — draft

Scope: [#68](https://github.com/krispykrits/TRACE/issues/68) and [ADR 0022](../adr/0022-sprint-06-readiness-and-sprint-07-diagnostics.md). Status: **draft; owner-reported demonstration needs details and handoff decision is pending**. Live [Project Status](https://github.com/users/krispykrits/projects/2) governs work status. This document does not declare a Local MVP diagnostic or release decision.

## Pre-existing evidence

- [Offline comparison v3](../../evaluation/reports/local_mvp_comparison_offline_v3/README.md): 36 scripted attempts; 12/12 integrated captured timelines complete, while candidate full-snapshot completeness was 0/12. No actual provider calls or new actual human support judgments.
- [Local recovery](../../evaluation/reports/local_recovery_v1/README.md): recorded crash, duplicate and restore checks, with the exact original validation history and local limits.
- [Local security](../../evaluation/reports/local_security_v1/README.md): canary and disclosure checks; [PR #92](https://github.com/krispykrits/TRACE/pull/92) merged on 2026-10-21. Scripted tests do not prove real-model resistance or operational authentication.
- [S5 owner review](../../evaluation/reports/investigator_offline_v1_human_review_v1/README.md): a separate earlier guided review, not review of a new Azure run.

The fully reviewed scripted publication path exhausted the retained 40-tool-call policy in the recovery/security evidence. Measure that path before S7; no budget increase is implied.

## Current readiness verification

On 2026-10-30, a clean Linux checkout of main `61db246e945a5b2d9a4d8f22f3d5aa73e08deb11` was prepared with CPython 3.12.14, `uv` 0.12.17 and `uv sync --locked`. The `uv.lock` SHA-256 is `139dbf8a72d42fa297b5800e7b036a1180b60ad1d92fee5ed98d3a668e94657c`. `make package-check` passed in a separately created wheel environment. A synthetic unreviewed CLI investigation exited 7; saved JSON export also exited 7 and citation resolution exited 0. These used the checkout's fixed-clock fixture script, not the installed wheel. After that run, the owner participated in an assisted chat walkthrough of one synthetic claim and reported, “I have performed demonstration.” The owner did not specify which commands, screens or artifacts were used for the reported demonstration; the report is not independent verification of those details.

The fresh comparison ran against that code checkout with documentation edits present. Its privately retained synthetic evidence bundle contains evaluator-only ground truth and must remain outside investigator inputs. Manifest SHA-256: `ac7f690c680fd132f5fbe3648b0aca8be97d37e38ad3715089de4b12730da838`; scores SHA-256: `2cc4f3075bb688ea07168233a4b554d17781504d9ffe18aed0c3450782b2c5d9`. Keep the bundle's complete bytes and use its source bindings for reproduction.

The bundle's `readiness/` directory also retains a synthetic setup script, installed-wheel reproduction notes and output. With a refreshed synthetic corpus and fictional grants valid at the actual system clock, an isolated wheel's service/window evidence-only CLI completed with exit 0; saved JSON report and artifact inspection also exited 0. This run supplied no model assessment, citation or human support. Separately, copied development scripts and corpus outside the checkout injected the fixed-clock scripted provider while `trace_app` resolved from the installed wheel. The pending investigation and saved export exited 7; citation resolution exited 0. Revoking one fictional source grant denied the saved report with exit 4 and no stdout; the profile was then restored. These are synthetic fixture outcomes, not actual model or human review. The scripts are outside the wheel; evaluator labels were not supplied to the installed process.

All 36 scheduled attempts completed, 12 in each arm. All 12 integrated attempts remained review-required; their captured timeline completeness was 12/12 and candidate full-snapshot completeness 0/12. All 12 integrated captures reported incomplete sources; six had capture gaps. Citation validity was 30/30, but the frozen scores record all 30 integrated claims as unreviewed and support as unmeasured. After scoring, the owner reviewed one claim in chat and revised the initial judgment from supported to indeterminate because the claim was vague. Codex presented and explained the citation and suggested indeterminate as an option. The separate owner revision does not alter the frozen scores or establish model quality. Scripted cause accuracy was 0/6; no critical boundary failures were observed. These are synthetic results, not Azure diagnostic quality. Rescore matched the saved score bytes without dispatch; actual provider calls and new human decisions were zero.

Remaining checks are recorded below only when finished. Retain failed and incomplete outcomes. Installed-wheel investigation and protected inspection must be demonstrated separately from wheel packaging and synthetic fixture scripts.

The complete local command `make check lint format-check type-check architecture-check test integration package-check` passed in this environment: 46 unit, 119 contract and 221 integration tests, plus the installed-wheel check. The integration suite took 751.213 seconds. No live-provider suite was run.

| Readiness boundary | Result | Evidence or remaining work |
| --- | --- | --- |
| Clean checkout, Python 3.12, locked dependencies | Passed setup | Checkout and lock binding above; `uv sync --locked` succeeded |
| 36 planned attempts and complete authorized captured timelines | Passed for the captured offline inputs | 36/36 completed; integrated delivered timeline 12/12; source gaps and candidate omissions remain explicit above |
| Saved deterministic rescore | Passed | Saved and regenerated score bytes matched; no dispatch |
| Applicable critical local checks, recovery and security | Passed current offline suite | Full required command passed with counts above; original recovery/security evidence and its limits remain linked above |
| Installed-wheel service/window investigation and protected inspection | Partial | Installed CLI evidence-only investigation/report/artifact passed; installed-wheel scripted pending report and citation passed through injected fixture composition. Owner review-packet walkthrough is partially documented; demonstration details remain to be confirmed |
| Owner review-packet walkthrough and binding/decision/revision | Partial | The owner reviewed and revised one bound synthetic claim with Codex assistance and reported performing a demonstration; the exact display, commands and other demonstrated steps need clarification |
| Owner local-readiness/handoff decision | Pending | Record only after reviewable evidence and owner decision |

## S7 handoff and unresolved gates

Actual model quality, owner support, latency and cost are unmeasured and move to [#87](https://github.com/krispykrits/TRACE/issues/87) and [#65](https://github.com/krispykrits/TRACE/issues/65). [#55](https://github.com/krispykrits/TRACE/issues/55) may proceed in parallel. Actual deployment/model/API and configuration, permitted sources/transmission/retention, current spending and unresolved reservations, journal and cleanup ownership, stop contact, run scope and final approval bound to the run remain prerequisites to live dispatch. Infrastructure budget, provisioning, hosted identity and operational source access remain separate gates.

## Owner decision

Pending. An owner walkthrough is not itself a diagnostic-quality judgment, and this document does not authorize a paid call, cloud apply, new source access or remediation.
