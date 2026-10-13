# Scripted Sprint 4 evidence package

Proposed integration gate for [#19](https://github.com/krispykrits/TRACE/issues/19), 2026-10-13. The [Sprint 4 review](../sprints/sprint-04-review.md) records evidence and the Sprint 5 handoff. This uses the accepted [tool catalog](investigation-tools.md), [timeline](incident-timelines.md), [retrieval/context](retrieval-evaluation-context.md) and [capability boundaries](package-layout.md).

## Fixed read sequence

`investigation.bundle.build_evidence_package` depends only on the `ToolInvoker` port and core contracts. Trusted composition supplies a scoped tool session, investigation binding, validated event window and reference query. It performs three operational list reads (`logs.query`, `metrics.query`, `deployments.query`), one lexical knowledge/context read, then `evidence.get` for every timeline event and `knowledge.resolve` for every emitted passage. The operational and knowledge grants stay independently enforced by #18. Source setup/publishing is separate from those read-only calls.

This is a prescribed integration demonstration, not model-selected orchestration. It produces no diagnosis, causal hypothesis, confidence, generated claim or action. The returned `assessment` is `not_performed`. No provider or ML capability is required; unimplemented optional ML never replaces, blocks or invents evidence. Sprint 5 will introduce its scoped provider, report, execution-budget and investigator contracts.

## Output, consistency and determinism

The `scripted-evidence-bundle.v1` result contains:

| Field | Contract |
| --- | --- |
| `status` | `complete`, `partial`, or `failed` |
| `data` | Source-only canonical package, or null on any failed reference/tool/consistency check |
| `data_sha256` | SHA-256 of canonical UTF-8 JSON data, or null on failure |
| `execution` | Actual investigation ID and real versioned correlation/attempt/duration/outcome audit metadata |
| `failure` | Safe tool/status/reason, or null |

The stable `data` includes an observed timeline, source coverage, matching/truncated counts, original records/payloads, knowledge context/omission diagnostics and explicit reference lists. Event ordering uses parsed UTC instants plus evidence-ID tie breaking, preserving event/collection times. Deployment proximity never becomes a causal link. The timeline's transient database investigation ID is in the separate execution binding; its source IDs and timestamps remain intact. Audit attempt IDs and elapsed durations are not rewritten into fake deterministic values. Repeated identical source input gives identical data and hash while execution metadata changes.

List results must use the expected kinds and coherent matching/truncation accounting. Source manifests must agree across the three list reads. Duplicate record/source identities, invalid timestamps/payloads and undisclosed source loss reject the package. Each current direct read must exactly equal its selected record/payload. Knowledge quote/citation IDs, exact canonical byte counts, source revision/metadata, generation, document hash, section and original offsets must agree with the resolved full chunk. Changed or denied references reject the entire package; no partially verified package escapes.

The final canonical data is bounded to 262,144 bytes. This is a local implementation safety limit, not a model context/token budget or operational SLA. Individual reads retain #18's bounds. The fixture harness explicitly uses 64 attempts/10,000 ms per call within existing supported ceilings to cover list and reference reads; no retries or model spending are implied. Exhaustion, timeout, dependency/access failure, or inconsistent output yields `failed`, null data/hash and the safe failure metadata. A returned whole-result-omission envelope that lacks timeline/context metadata cannot masquerade as a complete package.

References are revalidated through current tool policy at their individual read times. This does not create a simultaneous distributed snapshot or standing authorization after return. Source grants/clock must come from trusted composition, and future consumers must revalidate saved citations again. The scripted fixture pins source time explicitly; real source composition keeps the real clock.

Source gaps and ordinary count/context truncation remain `partial`, with diagnostics. Complete empty retrieval means there is no eligible matching passage, not that policy metadata is globally unanswerable. Absent/stale knowledge preserves the evidence-only timeline with `missing_knowledge: true`; expired source passages are excluded. Missing Payment capture is not reconstructed from reference prose. The normal development replay remains partial because its authorized operational export is explicitly unavailable.

## Runtime/evaluator isolation

The runtime builder imports no evaluator, script, demo, adapter or model SDK. The developer harness uses `ScenarioSession` and approved corpus fixtures through separate administration handles; it never reads causal ground truth or tool-choice expectations. Its output omits case/seed/cause/sufficient-evidence/split/expected-choice fields. A source's legitimate reference evaluation role is provenance, not evaluator ground truth. Runtime wheel/import checks preserve this boundary.

[Tool-choice fixtures](../../evaluation/fixtures/tool_choices_v1.json) are evaluator-only, agent-authored development proposals: 18 questions/cases and 21 examples, with declared acceptable alternatives and rejected argument/capability attempts. Context tokens are substituted only from supplied event windows, evidence IDs and emitted generation/chunk IDs. They never use causal ground truth. `choice_matches` evaluates an external selected call against the declared exact alternatives independently of whether the API legally executes it; these examples are not an exhaustive semantic rubric.

The [tool-evaluation report](../../evaluation/reports/tool_choices_development_v1.json) executes all scheduled examples through actual local readers and records outcomes, source/input hashes, counters and safe audit. Duplicate, missing, unscheduled and tampered attempts are rejected by saved rescoring. Unexpected outcomes remain failures, not successful empty results. This proves the API fixture schedule and boundary handling; **model tool-choice evaluation is `not_run`**. There are no paid calls, model-selected choices, generated-answer judgments or held-out measurements. Review/refine acceptable alternatives before a later independent model study and version changes explicitly.

## Reproduction and checks

From the repository root, using fresh output paths:

```sh
uv run --locked python scripts/demo_integration.py --output /tmp/trace-s4-package.json
uv run --locked python scripts/demo_integration.py --case c03 --output /tmp/trace-s4-missing.json
uv run --locked python scripts/demo_integration.py --limit 1 --output /tmp/trace-s4-truncated.json
uv run --locked python -m evaluation.tool_evaluation --output /tmp/trace-s4-tool-checks.json
uv run --locked python -m evaluation.tool_evaluation --rescore evaluation/reports/tool_choices_development_v1.json
make integration-s4
make check lint format-check type-check architecture-check test integration package-check
```

The script exits 0 for usable complete/partial packages and 1 for explicit package failure; output paths are exclusive, and temporary stores/indexes are removed before return. CLI/source fixtures use fixed collection/read time 2026-10-12T12:00:00Z and seed 17. Audit metadata remains real. The [saved package](../../evaluation/reports/sprint_04_evidence_package_v1.json) preserves the actual execution envelope alongside reproducible data.

Fast CI executes credential-free deterministic contracts and actual SQLite/artifact/process/evaluator integration checks, including the assembled smoke. Scope denial, revocation after selection, stale/absent knowledge, whole-source/count/context gaps, real worker timeout, dependency failure, source inconsistency, redacted source material and hostile log/reference text are exercised. Source text stays quoted data; a rejected shell attempt cannot add a catalog capability. These are code/data/authority checks, not proof that an unimplemented model will resist every injection.

Semantic/cached-encoder comparisons remain explicit under `make integration-semantic`/`make retrieval-evaluate`; live provider checks remain separately opted in. #19 runs lexical local fixtures, with no cached encoder, live provider, operational source, CloudWatch delivery, cloud resource or remediation. Existing historical reports retain their recorded implementation checkout; do not rewrite them to claim new acceptance. Local MVP release, Cloud MVP, independent Operational Pilot and final production remediation remain separate gates.
