# Sprint 5 review — first investigator and actual-output scoring

Date: 2026-10-15 (America/New_York). Prepared by Codex. Reviewer: project owner, decision pending. Scope: [Sprint 5](../planning/capstone-project-plan.md) / [#39](https://github.com/krispykrits/TRACE/issues/39). This review is a draft, not a claim of owner acceptance, actual human endorsement, Local MVP release or operational usefulness.

## Completion and evidence

Live issue/Project state was verified when #39 began: #19 and #34–#38 were closed/Done, #39 was Ready and then moved to In progress. A merged PR proves its scoped acceptance, not all later integration/release gates.

| Item | Evidence | Limits/open gate |
| --- | --- | --- |
| #34 provider / merged [PR #51](https://github.com/krispykrits/TRACE/pull/51) | [Provider contract/live record](../architecture/model-provider.md#reproduction-and-live-evidence), ADR 0012; native Azure check on 2026-10-13: 143 input / 90 output tokens, 2,400 ms, bounded one-attempt JSON/citation path | Historical synthetic connector health, not the assessment prompt or end-to-end diagnostic quality; dated model version owner-reported |
| #35 assessments / merged [PR #52](https://github.com/krispykrits/TRACE/pull/52) | [Strict v2 schema, current citations and independent support](../architecture/validated-assessments.md), ADR 0013 | A valid citation or scripted support record is not actual evidentiary endorsement |
| #36 admission / merged [PR #53](https://github.com/krispykrits/TRACE/pull/53) | [Durable limits and unknown dispatch](../architecture/investigation-budgets.md), ADR 0014 | Local accounting is not account-wide billing or shared-cloud admission |
| #37 investigator / merged [PR #62](https://github.com/krispykrits/TRACE/pull/62) | [Bounded workflow](../architecture/bounded-investigator.md), ADR 0016 | Hand-authored offline model/reviews are not measured diagnosis |
| #38 CLI / merged [PR #82](https://github.com/krispykrits/TRACE/pull/82), merge `71de366` | [Investigation/display/export/cancellation](../architecture/investigator-cli.md), accepted scoped ADR 0019; 331 deterministic tests and credential-free CI in the PR | Trusted local files/composition, development/test captures; no operational authentication or paid workflow acceptance |
| #39 current implementation | [Actual-output contract](../architecture/investigator-evaluation.md), [predeclared protocol](../../evaluation/investigator_protocol_v1.json), ADR 0020 and scoped PR | Owner review pending; actual sampled human decisions and live diagnosis remain explicit gates |

## Demonstration and reproducibility

~~~sh
uv run --locked python -m evaluation.investigator run --output /tmp/trace-sprint-05
uv run --locked python -m evaluation.investigator rescore --run-dir /tmp/trace-sprint-05
~~~

Use a fresh directory. Each planned case executes the public CLI with real SQLite/corpus/index/read-only workers and explicitly fictional provider/support ports. The saved score is reconstructed from hash-bound exported inputs/results/metadata, without model/tool/process dispatch. Protocol, implementation/lock/source revisions, actual/unknown usage, attempts and wall-clock latency remain visible. The fake retains its wrong placeholder cause rather than reading/tuning to labels.

The final measured offline bundle and exact results/checks are recorded in the #39 implementation PR and the linked artifact added before handoff. Any exploratory run is distinct from the final retained bundle. Source/version mismatches require the recorded checkout; earlier frozen retrieval/tool reports retain their original bytes/checkouts.

The ten cases cover regression, degradation/noncausal deployments, two insufficient/partial captures, malformed output, timeout, invalid/cross-scope citation, hostile source instructions, answer-marker rejection and a source dependency failure. No failed or missing case can disappear. The assembled matrix exposed a category bug: an already rejected malformed assessment was normalized to generic dependency failure. The runtime now preserves `malformed_assessment`, with contract/process regression checks; it does not relax citation or disclosure authority.

The support sample includes every emitted claim from the four base cases, with exact quote/citation/report/input bindings. **Actual human reviews: none supplied.** The saved review envelope is empty; unsupported-claim rates have a zero denominator/null value, rather than an invented zero-error result. Fixture support ports, fixture unit reviews, AI-generated verdicts and the earlier retrieval endorsement are not counted. [Review instructions](../architecture/investigator-evaluation.md#support-sample-and-independent-review) define how the owner/reviewer can add actual decisions and preserve disagreements in a new score artifact.

## Acceptance classes and owner gates

| Gate | Current evidence or blocker |
| --- | --- |
| Offline assembled contract | Deterministic case/scorer and current source/citation/label/disclosure checks; final run/check evidence belongs in #39 PR |
| Native live connector | Historical accepted #34 synthetic check, linked above; not rerun by #39 |
| Actual-provider end-to-end diagnosis | Not run. Project owner must supply exact paid run scope, source/transmission approvals, known spending/allowance, predeclared numeric criteria and actual review coverage |
| Actual passage/claim support | Not run. Owner/independent reviewer must return bound sample judgments; authored fixtures cannot substitute |
| Local MVP release/comparison | Pending [#63–#68](../planning/capstone-project-plan.md#backlogs-and-dependencies): #63 predeclared protocol/thresholds, #64 actual reference/integrated comparison, #65 actual human review, #66 recovery, #67 security, #68 clean-environment release |
| Operational Pilot | No accepted representative recordings, explicit source/retention/transmission/shadow authorization or measured operator benefit |
| Cloud / production remediation | Separate Azure/AKS and deterministic executor/staging/production approval/verification gates; no resources applied or operational mutation performed |

All scenarios remain in the single related development group. Final-test data stays ungenerated/unaccessed. No new quality/performance threshold, budget, schedule, capacity, reviewer endorsement or institutional deadline is inferred.

## Review outcome

Prepared recommendation: review the scoped offline assembly/scoring implementation and its failure evidence, retain the live/human blockers, and proceed to the separately declared S6 track only after its prerequisites. The evaluator does not certify model robustness against injection, human-supported diagnosis, operational usefulness or Local MVP release. Owner decision/date: pending.
