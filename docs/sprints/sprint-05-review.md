# Sprint 5 review — first investigator and actual-output scoring

Date: 2026-10-15 (America/New_York). Prepared by Codex. Human reviewer: project owner Christian; guided review recorded below. Owner integration-acceptance decision pending. Scope: [Sprint 5](../planning/capstone-project-plan.md) / [#39](https://github.com/krispykrits/TRACE/issues/39). This review is not a claim of owner integration acceptance, positive claim-support endorsement, Local MVP release or operational usefulness.

## Completion and evidence

Live issue/Project state was verified when #39 began: #19 and #34–#38 were closed/Done, #39 was Ready and then moved to In progress. A merged PR proves its scoped acceptance, not all later integration/release gates.

| Item | Evidence | Limits/open gate |
| --- | --- | --- |
| #34 provider / merged [PR #51](https://github.com/krispykrits/TRACE/pull/51) | [Provider contract/live record](../architecture/model-provider.md#reproduction-and-live-evidence), ADR 0012; native Azure check on 2026-10-13: 143 input / 90 output tokens, 2,400 ms, bounded one-attempt JSON/citation path | Historical synthetic connector health, not the assessment prompt or end-to-end diagnostic quality; dated model version owner-reported |
| #35 assessments / merged [PR #52](https://github.com/krispykrits/TRACE/pull/52) | [Strict v2 schema, current citations and independent support](../architecture/validated-assessments.md), ADR 0013 | A valid citation or scripted support record is not actual evidentiary endorsement |
| #36 admission / merged [PR #53](https://github.com/krispykrits/TRACE/pull/53) | [Durable limits and unknown dispatch](../architecture/investigation-budgets.md), ADR 0014 | Local accounting is not account-wide billing or shared-cloud admission |
| #37 investigator / merged [PR #62](https://github.com/krispykrits/TRACE/pull/62) | [Bounded workflow](../architecture/bounded-investigator.md), ADR 0016 | Hand-authored offline model/reviews are not measured diagnosis |
| #38 CLI / merged [PR #82](https://github.com/krispykrits/TRACE/pull/82), merge `71de366` | [Investigation/display/export/cancellation](../architecture/investigator-cli.md), accepted scoped ADR 0019; 331 deterministic tests and credential-free CI in the PR | Trusted local files/composition, development/test captures; no operational authentication or paid workflow acceptance |
| #39 current implementation | [PR #83](https://github.com/krispykrits/TRACE/pull/83), [actual-output contract](../architecture/investigator-evaluation.md), [predeclared protocol](../../evaluation/investigator_protocol_v1.json), ADR 0020, retained artifacts and human addendum below | Owner integration review pending; ten guided indeterminate judgments supply no positive support evidence; live diagnosis remains gated |

## Demonstration and reproducibility

~~~sh
uv run --locked python -m evaluation.investigator run --output /tmp/trace-sprint-05
uv run --locked python -m evaluation.investigator rescore --run-dir /tmp/trace-sprint-05
~~~

Use a fresh directory. Each planned case executes the public CLI with real SQLite/corpus/index/read-only workers and explicitly fictional provider/support ports. The saved score is reconstructed from hash-bound exported inputs/results/metadata, without model/tool/process dispatch. Protocol, implementation/lock/source revisions, actual/unknown usage, attempts and wall-clock latency remain visible. The fake retains its wrong placeholder cause rather than reading/tuning to labels.

The retained [manifest](../../evaluation/reports/investigator_offline_v1/manifest.json) records clean implementation checkout `578fa6c137c51a278eb354ab1857d08330f02c21`. Its 46 JSON artifacts include [canonical scores](../../evaluation/reports/investigator_offline_v1/scores.json), every case's observed input/result/execution/source revisions, the [ten-claim support sample](../../evaluation/reports/investigator_offline_v1/support_sample.json) and an [empty actual-review envelope](../../evaluation/reports/investigator_offline_v1/human_reviews.json). The recorded run exited 0 and rescoring reproduced the scores byte for byte without provider/tool dispatch. Exploratory runs are separate. Source/version mismatches require the recorded checkout; earlier frozen retrieval/tool reports retain their original bytes/checkouts.

| Recorded result | Development incidents | All attempts including boundary faults |
| --- | --- | --- |
| Mechanical contract | 4/4 | 10/10; no critical boundary failures |
| Execution | 4 completed / 4 attempted | 5 completed, 5 deliberately failed / 10 attempted |
| Schema / candidate assessment | 4/4 each | 5/10 each; failures retained |
| Exact cause / service labels | 0/2 cause; 2/2 service | 0/8 cause; 3/8 service |
| Structural abstention | 2/2 insufficient cases | 2/2 insufficient cases |
| Valid claim citations | 10/10 | 13/13; the separate injected invalid citation was rejected |
| Delivered deterministic timeline | 4/4 | 9/10; source failure has no delivered timeline |
| Full supplied-snapshot timeline | 0/4 | 0/10; bounded-context omissions remain visible |
| Actual human support decisions at original measurement | 0; 10 sampled claims unreviewed | 0; unsupported rate null with denominator 0 |

Required verification passed on this implementation: `make check lint format-check type-check architecture-check test integration package-check` with `UV_CACHE_DIR=/tmp/trace-uv-cache UV_OFFLINE=1`. This includes 46 unit, 105 contract and 195 integration tests (346 total), and built-wheel entry-point/workflow/evaluator-exclusion checks. Relative documentation links and saved-artifact hashes/private-field exclusions also passed. The #39 PR records hosted CI separately.

All ten attempts have incomplete sources because no sanitized export was supplied; two also have the declared Payment capture gap. Boundary results were: malformed response → `malformed_assessment`; timeout → `timeout` with unknown usage; invalid citation → `citation_not_admitted`; answer marker → `policy_rejected` before model invocation; source failure → `execution_failure`. The hostile-instruction case completed with unchanged grants, data/instruction separation and denied disclosure probes; this measures fixture mechanics only. Actual-provider calls and actual model spending were zero; simulated usage/cost and measured local wall time are labeled separately.

The ten cases cover regression, degradation/noncausal deployments, two insufficient/partial captures, malformed output, timeout, invalid/cross-scope citation, hostile source instructions, answer-marker rejection and a source dependency failure. No failed or missing case can disappear. The assembled matrix exposed a category bug: an already rejected malformed assessment was normalized to generic dependency failure. The runtime now preserves `malformed_assessment`, with contract/process regression checks; it does not relax citation or disclosure authority.

The support sample includes every emitted claim from the four base cases, with exact quote/citation/report/input bindings. At original measurement no actual human reviews had been supplied. The original saved review envelope remains empty and its scores retain a zero support-rate denominator/null value. Fixture support ports, fixture unit reviews, AI-generated verdicts and the earlier retrieval endorsement are not counted. Later actual decisions are preserved separately below, using the [review contract](../architecture/investigator-evaluation.md#support-sample-and-independent-review).

## Human review addendum — 2026-10-15

The owner completed the ten-claim sample with **10 indeterminate judgments because all statements were too vague to assess**, after rubric/explanation assistance from Codex. Codex transcribed the owner's explicit instruction to apply that judgment across the sample and preserved the first two explanations already in the packet. This is one guided review with shared reasoning, not blind independent review or ten independently authored rationales.

The [review addendum](../../evaluation/reports/investigator_offline_v1_human_review_v1/README.md) preserves the [actual decisions](../../evaluation/reports/investigator_offline_v1_human_review_v1/actual-human-reviews.json), [completed packet](../../evaluation/reports/investigator_offline_v1_human_review_v1/review-packet.md) and [new scores](../../evaluation/reports/investigator_offline_v1_human_review_v1/reviewed-scores.json). Original run artifacts/hashes remain unchanged. Regeneration from the supplied decisions must reproduce the new score artifact without calls.

Review coverage is 10/10 sampled claims; determinate judgments are 0, so the unsupported-claim rate remains unavailable (0/0, null). All ten sampled claims are reviewed; three additional claims from the hostile-input boundary case remain outside the declared human sample. Zero disagreements with one reviewer does not measure agreement. The fixture's vague wording is a recorded reviewability limitation, not a diagnosis result from Azure. No positive support endorsement, real-model quality or release acceptance follows from recording these judgments.

The missing-Sprint-5-review-input blocker is resolved by the recorded judgments. Owner integration acceptance remains pending. S6 [#63](https://github.com/krispykrits/TRACE/issues/63) must predeclare reviewability/quality criteria and actual-provider review coverage before the applicable comparison/release measurement; retain the current negative finding rather than rewriting the frozen fixture outputs.

## Acceptance classes and owner gates

| Gate | Current evidence or blocker |
| --- | --- |
| Offline assembled contract | Retained 10/10 expected mechanical outcomes, zero critical boundary failures and byte-identical rescore; full check evidence belongs in #39 PR |
| Native live connector | Historical accepted #34 synthetic check, linked above; not rerun by #39 |
| Actual-provider end-to-end diagnosis | Not run. Project owner must supply exact paid run scope, source/transmission approvals, known spending/allowance, predeclared numeric criteria and actual review coverage |
| Actual passage/claim support | One guided owner review recorded: 10/10 sampled claims indeterminate; zero determinate support evidence. Actual-provider support and later study review requirements remain unmeasured |
| Local MVP release/comparison | Pending [#63–#68](../planning/capstone-project-plan.md#backlogs-and-dependencies): #63 predeclared protocol/thresholds, #64 actual reference/integrated comparison, #65 actual human review, #66 recovery, #67 security, #68 clean-environment release |
| Operational Pilot | No accepted representative recordings, explicit source/retention/transmission/shadow authorization or measured operator benefit |
| Cloud / production remediation | Separate Azure/AKS and deterministic executor/staging/production approval/verification gates; no resources applied or operational mutation performed |

All scenarios remain in the single related development group. Final-test data stays ungenerated/unaccessed. No new quality/performance threshold, budget, schedule, capacity, reviewer endorsement or institutional deadline is inferred.

## Review outcome

Prepared recommendation: review the scoped offline assembly/scoring implementation, failure evidence and recorded human reviewability finding; retain live/diagnostic-quality gates and proceed to the separately declared S6 track only after its prerequisites. Recording negative or indeterminate judgments does not require a positive support result for the evaluation implementation to be reviewed. The evaluator does not certify model robustness against injection, human-supported diagnosis, operational usefulness or Local MVP release. Owner integration-acceptance decision/date: pending.
