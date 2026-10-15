# Sprint 5 human review addendum v1

Date: 2026-10-15 (America/New_York). Reviewer: project owner Christian (`christian`). Scope: the ten predeclared sampled claims from the four base incidents in [investigator_offline_v1](../investigator_offline_v1/manifest.json), issue [#39](https://github.com/krispykrits/TRACE/issues/39), [PR #83](https://github.com/krispykrits/TRACE/pull/83).

The owner found the statements too vague to assess. After discussing the rubric and first two examples with Codex, the owner explicitly extended that judgment to the remaining claims and instructed Codex to fill the records and packet. Codex transcribed `indeterminate` with that shared rationale; it did not independently decide ten human verdicts. This is one guided reviewer with a shared judgment across the sample, not blind independent review, two-reviewer agreement or measured actual-provider quality. The first two explanations already entered in the packet are preserved.

| Measure | Recorded result |
| --- | --- |
| Predeclared sampled claims / recorded decisions | 10 / 10 |
| Supported / unsupported / indeterminate | 0 / 0 / 10 |
| Determinate support-rate denominator | 0; rate is null |
| Unreviewed claims in the development sample | 0 |
| Reviewer disagreements | 0 recorded; only one reviewer |

The separate hostile-input boundary case has three claims outside the predeclared human sample; they remain unreviewed. The original offline mechanical result stays 10/10 expected outcomes with no critical boundary failures. Human feedback exposes a reviewability limitation of the hand-authored provider's claims. It supplies no positive support endorsement or diagnostic-quality acceptance. Real-provider diagnosis, separately authorized run scope and S6 release criteria/review coverage remain gated.

## Preserved records

- [actual-human-reviews.json](actual-human-reviews.json): the owner's transcribed decisions, exact claim bindings and original sample hash.
- [review-packet.md](review-packet.md): readable claim/citation packet with the completed judgments; the first two rationale texts are more detailed than the shared transcription in the JSON file.
- [reviewed-scores.json](reviewed-scores.json): regenerated scores, binding the review-file and original run-manifest hashes.

These files were copied byte for byte from the completed local review at the owner's request. Original run inputs, outputs, scores, empty review envelope and manifest remain unchanged. The new scores' `human_support=recorded_sample_only` means decisions were recorded; it does not mean the claims passed support review.

## Reproduce without model calls

Use the original manifest's implementation checkout (`578fa6c137c51a278eb354ab1857d08330f02c21`) or a checkout with identical implementation hashes. From the repository root, choose a fresh output path:

~~~sh
uv run --locked python -m evaluation.investigator review --run-dir evaluation/reports/investigator_offline_v1 --reviews evaluation/reports/investigator_offline_v1_human_review_v1/actual-human-reviews.json --output /tmp/trace-sprint-05-human-reproduced.json
cmp evaluation/reports/investigator_offline_v1_human_review_v1/reviewed-scores.json /tmp/trace-sprint-05-human-reproduced.json
~~~

This verifies the frozen run and sample bindings and scores the supplied decisions without dispatching models, tools or child processes. Keep this review addendum outside runtime inputs, corpus and prompts. Subsequent judgments or reruns need separate artifacts; preserve these originals.
