# Local MVP offline comparison v2 — approved 40-call ceiling

Recorded 2026-10-16 for [#64 / PR #86](https://github.com/krispykrits/TRACE/pull/86), after the owner explicitly chose 40. This is a fresh scripted contract comparison, not Azure diagnosis, human endorsement or release acceptance. The [original failed comparison](../local_mvp_comparison_offline_v1/README.md), its v2 decisions and all capacity-probe artifacts remain unchanged.

## Reproduction

Use the recorded implementation checkout `4dde400f8d008ea093b37c75b7d171d73f13e3a3`. Decision revision v3 uses the unchanged v2 decision schema/protocol; the comparison artifact schema remains v1 because its structure did not change.

```sh
uv run --locked python -m evaluation.local_mvp_comparison run --output /tmp/trace-local-mvp-comparison-v2
uv run --locked python -m evaluation.local_mvp_comparison rescore --run-dir evaluation/reports/local_mvp_comparison_offline_v2
```

Fresh output must not exist. New execution IDs/latencies may differ. Saved rescoring reproduces exact score bytes, with no model/tool/process dispatch. Both the public command and an in-process probe forbidding subprocess/network dispatch reproduced the report byte-for-byte. The original run directory was copied without changing its bytes. This explanatory README is outside the immutable inventory. Manifest SHA-256: `0cb2f4abe32b230c0549e471523c958e32a5a43508e7630f7715daf1d5521fde`; 151 input/output artifacts and 104 source files are bound.

## Results and limits

| Arm | Scheduled | Completed | Result |
| --- | --- | --- | --- |
| LLM-only | 12 | 12 | Scripted brief-only abstentions; no tools |
| Evidence bundle | 12 | 12 | Full valid deterministic timelines; no model diagnosis or knowledge calls |
| Integrated RAG/tools | 12 | 12 | Protected assessment.v2 delivered as review-required, never human-endorsed |

All integrated attempts fit 40: six use 30 tool calls and six use 23. They retain fresh source/citation checks and make one scripted model call each. There are no budget-exhausted attempts, zero actual provider calls and zero actual human review decisions. Fifty-four claim tasks remain unreviewed: 30 integrated and 24 descriptive reference claims. The owner-review and final hash-bound live-run approval gates remain unset.

The tool-budget execution blocker is removed for this declared cohort/options. Schema, service/assessment/abstention labels, citation validity, deterministic timeline validity and completion pass their fixture checks. **Cause accuracy remains 0/6**, because the hand-authored model proposes a placeholder mechanism. **Full timeline completeness remains 0/12**: delivered assessment timelines cover selected admitted model context rather than every captured input event. The model-context omissions remain explicit; valid chronological ordering and citation existence do not establish completeness or evidentiary support. Neither negative result is hidden or repaired by changing thresholds. Human support remains unmeasured with denominator zero.

Token/cost measurements are explicitly scripted, not Azure usage or billing. Per-arm wall times use existing harness instrumentation (reference setup is included; integrated time measures the CLI phase); they are descriptive and do not establish comparable provider or operational latency. Four related development cases and their repeats do not establish generalization, ML benefit or Operational Pilot usefulness.

## Approved change and remaining gates

[The owner approval record](../../../docs/planning/local-mvp-tool-budget-adjustment-2026-10-16.md) binds the numeric choice. Only the tool ceiling, decision revision/provenance and derived execution-policy configuration changed; model/token/spending/deadline/retry/quality/review settings remain unchanged. The model reservation ceiling remains $0.405504, not measured spend. The earlier capacity summary retains its original pending-proposal status at measurement time; the later approval is recorded separately.

This version still has no live executor: `--mode live` rejects before dispatch. Actual provider/source/transmission/spending bindings, live composition/approval, real diagnostic measurement, timeline completeness, actual owner support judgments, recovery/security evidence and release review remain gates. Completing scripted proposals is not Local MVP acceptance.

[Manifest](manifest.json) · [Scores](scores.json) · [Acceptance guide](../../../docs/planning/local-mvp-acceptance.md)
