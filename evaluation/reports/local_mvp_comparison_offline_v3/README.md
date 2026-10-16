# Local MVP offline comparison v3 — complete captured timeline delivery

Recorded 2026-10-16 for [#88](https://github.com/krispykrits/TRACE/issues/88). All 36 offline attempts completed: 12 brief-only, 12 deterministic bundles and 12 integrated review-required reports. Actual provider calls and actual human judgments remain zero. This verifies local mechanics, not real-model diagnostic acceptance.

## Reproduction

Use implementation checkout `897caecdd1a54e14f0d7f9bbf46ef0423e5abb22`. The unchanged approved decision revision v3 retains the 40-call ceiling and all model/token/deadline/retry/spending/quality/review settings. The new comparison and score schemas are v2; the delivered CLI and output scorer are v2. Protocol/decision schemas remain v2.

```sh
uv run --locked python -m evaluation.local_mvp_comparison run --output /tmp/trace-local-mvp-comparison-v3
uv run --locked python -m evaluation.local_mvp_comparison rescore --run-dir evaluation/reports/local_mvp_comparison_offline_v3
```

Fresh output must not exist. Saved rescoring reproduces exact score bytes without dispatch; both the command and an in-process check forbidding subprocess/network dispatch passed. This folder preserves the original output bytes. This README is outside the immutable inventory. Manifest SHA-256: `049a75f23f3bf14fe4e6d2cf9b3cda649cb535bb307bad193ff47cccacde837d`; 151 artifacts and 104 source files are bound.

## Results and interpretation

| Measure | Integrated result |
| --- | --- |
| Completion | 12/12; all review-required |
| Full captured timeline completeness | 12/12 |
| Deterministic timeline validity | 12/12 |
| Candidate full-snapshot completeness | 0/12; the admitted model subset remains smaller |
| Scripted cause accuracy | 0/6; unchanged placeholder mechanism |
| Claim citation validity | 30/30; does not establish support |
| Actual human support | Unmeasured; denominator zero, 30 integrated claim tasks unreviewed |
| Critical boundary failures | None observed |
| Tool calls | Six attempts use 30, six use 23; no ceiling increase or exhausted attempt |

Full delivery includes each captured event’s identity, source revision, original provenance record, observed/collected UTC timestamps and noncausal status. Capture metadata retains unavailable sources, matching counts and truncation. All 12 snapshots have an unavailable source; a complete delivered captured timeline does not imply complete real-world evidence. Missing-payment cases retain their missing capture rather than inventing observations. Model-context omissions remain explicit, and timeline-only entries do not become admitted model citations.

The assessment.v1 projection and its candidate metric are preserved. The versioned delivery metric counts every applicable planned attempt and checks full observed-input identity/order, revisions, timestamps and records separately from admitted candidate references. This fixes delivery rather than relabeling the subset complete or removing denominator events.

Integrated p95 measured CLI latency was 18,721.45 ms. Scripted tokens/estimated costs are synthetic-port measurements; they do not establish Azure usage/billing or comparable provider latency. Brief-only setup and integrated CLI timing retain the original instrumentation asymmetry. Fifty-four total claim tasks (30 integrated, 24 reference) remain unreviewed.

The [20-call failures](../local_mvp_comparison_offline_v1/README.md), [40-call comparison with 0/12 completeness](../local_mvp_comparison_offline_v2/README.md) and capacity probe remain unchanged and require their own pinned checkout. S6 recovery/security/owner handoff and S7 actual Azure comparisons/owner quality review remain separate gates.

[Manifest](manifest.json) · [Scores](scores.json) · [CLI contract](../../../docs/architecture/investigator-cli.md)
