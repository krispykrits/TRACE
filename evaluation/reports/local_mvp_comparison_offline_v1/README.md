# Local MVP offline three-arm comparison v1

Recorded 2026-10-16 for [#64](https://github.com/krispykrits/TRACE/issues/64). This is scripted contract evidence, not Azure diagnostic measurement, human endorsement or Local MVP acceptance.

The implementation/source inventory is reproduced at checkout `821f62136de29da848a18fd5e2eb6d27a0e6b02d`. From that checkout run:

```sh
uv run --locked python -m evaluation.local_mvp_comparison run --output /tmp/trace-local-mvp-comparison-v1
uv run --locked python -m evaluation.local_mvp_comparison rescore --run-dir evaluation/reports/local_mvp_comparison_offline_v1
```

The output path for a fresh run must not exist. New execution IDs/latencies can differ; saved rescoring is byte-identical and makes zero new model/tool/process calls. Both the public rescore command and an in-process probe with network/subprocess dispatch forbidden reproduced `scores.json` exactly. Historical runs require their recorded source/protocol/guide bytes. This directory was copied byte-for-byte from the frozen run; this README is explanatory and outside the immutable manifest inventory.

## Recorded result

| Arm | Scheduled | Completed | What is measured |
| --- | --- | --- | --- |
| LLM-only | 12 | 12 | Scripted brief-only abstentions, no tools; descriptive label/citation/usage metrics |
| Evidence bundle | 12 | 12 | Authorized operational reads, 12/12 full deterministic timelines; no knowledge calls or model diagnosis |
| Integrated RAG/tools | 12 | 0 | Actual protected CLI execution; all attempts fail after exhausting the approved tool ceiling |

Every integrated attempt records one scripted model call and 21 tool attempt records: 20 admitted calls followed by `budget_exhausted`. Denied attempts remain visible rather than being presented as extra authorized calls. The CLI reports `execution_failure` and retains the untrusted evidence timeline; it publishes no completed diagnostic report. Its deterministic timeline validity can therefore pass while completion/schema/diagnostic gates fail. All twelve failures remain in the relevant scheduled denominators. The runner keeps the approved cap of 20; it does not substitute the demonstration's 100-call policy, rerun failures or create runtime support decisions to obtain completion.

There are **zero actual provider calls**, **zero actual human review decisions**, 12 paired case/seed/repeat groups and 103 bound source files. Twenty-four reference-arm claim tasks remain unreviewed and descriptive. There are no completed integrated reports for #65 to endorse. Human support and integrated citation rates have empty denominators and remain unmeasured; neither passes. Reported zero token/cost values come from explicitly scripted ports, not actual Azure usage or billing. Wall-time latency is descriptive for this local contract run and does not establish model latency.

The manifest SHA-256 is `3b43542d8dc02e225777c39e874917b8061890db922a70dcca058fd1710fc416`. Exact protocol/decision/plan/policy bytes, full delivered reference `assessment.v2`/citation mappings, captured synthetic source inputs, all attempt execution records, scores and source hashes are retained under the manifest. Only the scoring parent reads development truth; child execution records show no evaluator imports. Protected response dependency bindings are retained as provenance; evaluator artifacts confer no runtime grants.

## Remaining gates and negative finding

The current workflow and approved 20-call ceiling do not yield completed integrated reports on any of these four related development cases. This blocks Local MVP acceptance. A separately reviewed workflow optimization or explicit revised owner limit/protocol decision would require fresh frozen execution; these failed records must remain unchanged.

Actual Azure diagnostics are blocked on the plan's 19 missing factual/authority/run bindings, including actual provider/version/configuration, current shared-journal spending, source/transmission/run scope, cleanup owner, stop contact and final approval. This version exposes no live executor: `--mode live` is a fail-closed guard, not a provider-wired runner. Verified bindings and a separately reviewed live composition are required before Azure measurement. Live mode rejects before creating outputs or dispatching; no paid run is implied by these offline fixtures. Actual owner review, reliability/security evidence and the release decision remain #65–#68 gates. Four related development cases and their repeats do not establish statistical generalization, held-out ML benefit or Operational Pilot usefulness.

[Acceptance protocol and commands](../../../docs/planning/local-mvp-acceptance.md) · [Manifest](manifest.json) · [Scores](scores.json)
