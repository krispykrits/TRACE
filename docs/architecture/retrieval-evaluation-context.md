# Passage evaluation and bounded knowledge context

Status: proposed implementation for [#17](https://github.com/krispykrits/TRACE/issues/17), in draft [PR #45](https://github.com/krispykrits/TRACE/pull/45), 2026-10-12. The owner selected the thresholds below and reported corrections to the prepared judgments. The [revision record](../../evaluation/retrieval/judgment-revisions.md) traces the applied corrections; human sign-off on the revised bundle and the acceptance run remain pending. This increment builds on merged [#16 / PR #44](https://github.com/krispykrits/TRACE/pull/44), [authorized search](knowledge-retrieval.md) and [corpus policy](knowledge-corpus.md).

## Frozen protocol and development evidence

The [protocol](../../evaluation/retrieval/acceptance_v2.json) preserves the owner's threshold approval before the first #17 measurement and rebinds the revised suite hash after corrective review; the approval timestamp does not endorse the revised labels. Candidate K is **20**, final context passage limit (`rerank_top_k`) **5**, primary evaluation K **5**, secondary K **10**, minimum query count **100**. Required macro passage Recall@5 is **0.90**, MRR@5 **0.80**, and Recall@10 **0.95**. Lexical remains the previously selected default. The field `rerank_top_k` currently caps context passages; **no reranker is implemented or selected**.

The [version 3 suite](../../evaluation/retrieval/queries_v3.json) contains 100 distinct questions in 15 related development families over six documents/18 chunks: 84 proposed answerable queries and 16 with no relevant eligible passage. Relevance means eligible passage content directly addressing the question, including a substantive part of it; supporting an unrelated probe is insufficient. It covers exact codes, negation, service ambiguity, misleading claims, absent knowledge and source expiry. These variants are not 100 independent incidents. Gold and probe claims are revised proposals incorporating owner feedback until the owner endorses them; no held-out data is used. The entire family set stays in development.

The [review bundle](../../evaluation/retrieval/review_bundle_v3.md) quotes original passages and metadata and identifies 211 decisions: 100 complete relevance-set reviews (including empty sets) and 111 passage/claim-support reviews. [Review records](../../evaluation/retrieval/reviews_v3.json) reuse #14's `SupportReview`: target ID, verdict, named reviewer, rationale and `human_review` or `fixture_expectation` kind. Fixture expectations never satisfy the human gate. Missing reviews, disagreement or rejected relevance sets block acceptance before model loading. A relevance verdict of `supported` endorses the entire proposed gold set. A claim verdict checks the question-specific probe, which can intentionally be unsupported; it does not measure a generated answer. Agreed determinate human claim verdicts have an explicit unsupported-count denominator; without reviews it is null. Human claim verdicts need not equal the proposal.

Rank metrics use exact passage IDs, independently of generated answers. For every query with a nonempty gold set, Recall@K is the number of unique gold passages in the first K results divided by the number of gold passages. MRR@K is `1 / first relevant rank` within K, or zero. Reported values are macro means over all 84 scheduled answerable queries, with summed fractions/reciprocals and denominators retained. A failed answerable attempt contributes zero and stays in the denominator. Queries with no relevant eligible passage are excluded from these two denominators and reported separately with candidate-return counts. No answerable queries gives a null rate, not a perfect score. Duplicate ranks, missing/duplicate attempts and excessive ranks are rejected.

The real cached CPU comparison evaluates lexical, semantic and hybrid on identical source selections, 100 requests per branch. The candidate comparison changes the explicit per-document cap from 1 to 20 while holding candidate pool 20 fixed. The one-passage-per-document setting discarded relevant sections before assembly:

| Configuration / mode | Passage Recall@5 | MRR@5 | Recall@10 |
| --- | --- | --- | --- |
| One passage per document / lexical | 0.8095 | 0.8671 | 0.8095 |
| Up to 20 passages per document / lexical | 0.9544 | 0.9137 | 0.9881 |
| Up to 20 passages per document / semantic | 0.9534 | 0.8978 | 0.9911 |
| Up to 20 passages per document / hybrid | 0.9603 | 0.9325 | 1.0000 |

All 300 attempts succeeded in each configuration; six expected freshness exclusions verified in every mode. All modes returned candidates for all 16 no-relevant queries. These are exploratory results on proposed labels, **not an acceptance result** or proof of answerability. [Baseline report](../../evaluation/reports/retrieval_passage_baseline_v3.json) and [passage-candidate report](../../evaluation/reports/retrieval_passage_candidates_v3.json) retain ranks, omissions, source/index generations, package/model configuration and source/input hashes. The lexical candidate configuration meets the numeric thresholds on these proposals without an encoder or reranker. Semantic/hybrid remain explicit comparison options; the small difference does not establish a new default or operational usefulness.

Volume 4 already supports configurable candidate/document limits. TRACE exposes validated `SearchRequest.candidate_pool` (top-K through 100) and `max_chunks_per_document` (1–20). Existing callers retain pool 100 and one passage per document; #17 explicitly requests pool 20, top-K 20 and per-document cap 20 to retain sections before assembly. The retriever version is now `exact-retrieval.v2`; old v1 indexes must be explicitly rebuilt from authorized source chunks. No source/chunker/embedding/dependency changes are introduced.

## Context contract

[ContextAssembler](../../src/trace_app/knowledge_context.py) accepts a bounded search response, trusted read context, UTC read time and `ContextBudget`. It depends on the reader port, not SQLite or evaluator labels. Input has at most 20 candidates. Defaults are five passages and 8,192 UTF-8 bytes; supported limits are 1–20 passages and 128–1,000,000 bytes. These are implementation bounds, not an operational SLA or owner spending commitment.

The byte bound covers the exact canonical JSON `serialized_data`: quoted original text, citation IDs, complete citation metadata and envelope, including JSON escaping. It excludes the caller's diagnostic wrapper, system policy and eventual model prompt. This is not an LLM token budget; future generation must separately account for the selected model's full context. A response cannot exceed this data byte bound. Whole passages are omitted when they do not fit; smaller later passages can still fit. No source quotation is cut or rewritten.

Every candidate is validated and resolved against its original corpus generation and current access, retention, revision, freshness and withdrawal policy, including candidates destined for the omission ledger. Repeated chunk IDs are deduplicated. Lower-ranked overlapping windows from the same exact source metadata/document hash are omitted whole, preserving original offsets; distinct disjoint sections can remain. A consistent final batch read revalidates selected passages so withdrawal during a later resolution cannot expose an earlier passage. Later saved-citation reads must revalidate again; local checks do not promise distributed revocation after return.

The `knowledge-context.v1` data contains `content_role: untrusted_source_data`, `passages` with citation IDs and original quotations, and a separate `citations` map. Each mapping retains corpus generation, chunk ID, document hash, section, start/end offsets and full metadata: source identity/URI/revision, snapshot version, source timestamps, service/environment/access/evaluation scope and freshness. No incident observation timestamp is invented for a reference. Citation IDs bind generation and chunk ID, and resolve through the scoped corpus reader. Retrieved text never becomes policy, grants, configuration or an executed command. JSON separation provides a data boundary; a future model consumer must still enforce its own policy and grounding checks.

The diagnostic wrapper reports budget, exact used bytes, omissions by chunk ID/reason (`duplicate`, `overlap`, `byte_budget`, `passage_budget`), `incomplete`, and `passage_text_truncated: false`. Duplicate removal alone is not incomplete; overlap or budget drops are. Keep this ledger available to the investigator/reporting consumer so context loss cannot become an unsupported claim of completeness.

| Context status | Behavior |
| --- | --- |
| `ok` | At least one currently authorized passage fits |
| `empty` | Successful empty retrieval or no whole passage fits; budget omissions remain visible |
| `retrieval_failed` | Failed search remains failed, with no passages |
| `source_unavailable` | Denied, changed, expired or withdrawn source; no partial passages or omission IDs leak |
| `storage_failure` | Source dependency read failed; no fabricated context |
| Invalid input | `ContextInputError` for incoherent generation/results or invalid budgets |

Correlated `knowledge_context.completed` records contain status, generation, passage/omission counts and bytes, without queries or quoted text. Assembly is read-only; publishers manage corpus/index state separately.

## Reproduction and acceptance

From the repository root, with a fresh output path:

```sh
uv run --locked python scripts/demo_context.py --query 'PAYMENT_TIMEOUT evidence' --max-passages 5 --max-bytes 8192
uv run --locked python -m evaluation.retrieval_quality --modes lexical --output /tmp/trace-passage-lexical.json
uv run --locked python -m evaluation.retrieval_quality --rescore evaluation/reports/retrieval_passage_candidates_v3.json
make retrieval-evaluate
uv run --locked --extra semantic python -m evaluation.retrieval_quality --max-chunks-per-document 1 --output /tmp/trace-passage-baseline.json
```

`make retrieval-evaluate` uses the actual pinned cached encoder for all three branches; prepare the semantic extra/model as described in the [search setup](knowledge-retrieval.md). Missing packages/cache become explicit failures, never fixture embeddings or a silent mode fallback. The evaluator may run the explicitly requested lexical comparison even when dense initialization fails; dense attempts stay failed in their denominators. There are no paid/provider/AWS calls. The demo uses temporary synthetic state and resolves every emitted citation; valid empty results exit 0, invalid/dependency outcomes exit 2.

Original proposal artifacts remain archived; the exact original scorer checkout is identified in the [revision record](../../evaluation/retrieval/judgment-revisions.md). Current commands rescore the v3 reports with scorer v2. Saved reports snapshot suite, reviews, protocol, configuration and attempts with hashes; scorer/code/lock/source hashes identify the measured implementation. Model-free rescoring requires the exact scorer and verifies snapshot hashes, metrics, reviews and acceptance state. Reports are evaluator artifacts, not source-read authorization or runtime inputs. Changing source/configuration requires another measured run. Existing output paths are refused.

After the owner actually reviews the bundle, record the decisions with identity/rationale in `reviews_v3.json`, then run:

```sh
uv run --locked python -m evaluation.retrieval_quality --modes lexical --acceptance --output /tmp/trace-passage-acceptance.json
```

Stale cases separately record actual before-expiry eligibility, the freshness deadline, query-time exclusion and saved-citation denial. They check policy correctness rather than inventing relevant expired passage gold. Empty eligible-passage sets do not claim that metadata cannot answer a freshness question. Failed policy checks remain failures and block acceptance.

Acceptance requires all human decisions complete, agreed relevance sets, at least 100 queries, selected lexical mode and the predeclared protocol. Exploration reports always say `acceptance_status: not_run`, even when numeric thresholds are met. Keep an actual failed run and investigate rather than changing thresholds after observation. Revision of development judgments must be explicit, rehashed and reviewed; thresholds remain owner-controlled. No final-test tuning is permitted.

Fast CI exercises hand-computed metrics, failure denominators, stale-source eligibility, pre-model acceptance blocking, tampered reports, exact byte/Unicode budgets, dedup/overlap, citation metadata/resolution and scope/withdrawal/storage failures. Real-model measurements are separate from CI. This work supplies local synthetic/development evidence; Cloud MVP deployment, independent Operational Pilot usefulness, held-out study and final production remediation remain distinct gates.
