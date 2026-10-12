# Authorized knowledge retrieval

Status: accepted implementation for [#16](https://github.com/krispykrits/TRACE/issues/16), merged via [PR #44](https://github.com/krispykrits/TRACE/pull/44), 2026-10-12. [ADR 0009](../adr/0009-local-exact-knowledge-retrieval.md) records the embedding, dependency and storage decision. This read-only use case searches the [versioned corpus](knowledge-corpus.md); it does not diagnose an incident or authorize an action.

## Contract and bounds

[SearchService](../../src/trace_app/knowledge/search.py) depends on TRACE-owned `CorpusReader` and `Encoder` ports. The local adapters use SQLite source policy, technical TF-IDF, a pinned optional CPU sentence encoder and exact float32 dot products. Volume 4's lexical, dense and reciprocal-rank-fusion algorithms are adapted within TRACE; no sibling application or separate vector database is required.

`SearchRequest` requires 1–4,000 nonblank characters without NUL and integer `top_k` from 1 through 20. Modes are `lexical` (development-selected default), `semantic` and `hybrid`. Optional service/document-type filters narrow eligibility. Each branch sorts by descending score then stable chunk ID, retaining at most `candidate_pool` candidates (default 100, validated from top-K through 100). Hybrid sums `1 / (60 + rank)` from both branches. Final results contain at most `max_chunks_per_document` passages per document (default 1, validated 1–20), and at most `top_k` passages total. Scores describe within-mode ranking, not probabilities, answerability or causal support. Dense/hybrid search has no unmeasured similarity cutoff; it can return candidates even when the answer is absent.

The response records mode, index/corpus generation IDs, authorized eligible count, candidate count, status/reason and results. Each result includes rank/score, original and normalized passage, document/source/version/time/access metadata, section/offsets, `untrusted_source_data` role and a structured citation. Citations preserve the source URI without inventing a remotely resolvable anchor. `resolve(result, context=..., at=...)` returns the authorized original chunk; synthetic source URIs refer to local references, not an operational archive. Retrieved prose is data, never executed or used to modify grants/configuration.

| Outcome | Behavior |
| --- | --- |
| `ok` | Bounded ranked passages with currently resolvable citations |
| `no_results` | No eligible matching passages, or no positive lexical overlap |
| Invalid request | `SearchInputError`; invalid service grant raises `CorpusAccessError` before scoring/encoding |
| `provider_failure` | Missing semantic encoder/vectors or failed query embedding; hybrid never silently becomes lexical |
| `index_incompatible` | Encoder specification, source coverage/fingerprint or citation changed; rebuild explicitly |
| `source_unavailable` | Expired/missing corpus/index or source withdrawn during result packaging |
| `storage_failure` | Source/citation read failed; no result is manufactured |

Invalid serialized artifacts raise `IndexCompatibilityError` at loading, before search. Encoder initialization/publication failures raise `EncoderFailure`; a text beyond the actual token budget raises `SearchInputError`, without truncation. Correlated completion logs contain mode, status, generation ID and result count, without query or passage text.

## Authorization and withdrawal

A trusted `CorpusReadContext` supplies scope, environment, service grants, allowed reference cohort and validity time. The source reader checks original metadata and current source policy before either candidate scoring or query encoding. Lexical IDF is fitted only on the currently authorized, filtered passages; denied or withdrawn text cannot affect its statistics. Dense scoring selects only eligible vector rows before ranking. Empty eligibility avoids query encoding. A filter cannot create a grant or reveal a denied document count.

Coverage/fingerprints are checked against authorized source chunks before ranking. An index built for narrower grants cannot silently serve a wider source selection: missing coverage requires rebuilding. Citation resolution repeats current access/freshness/validity/retention checks. A final batch read rechecks all packaged candidates, including a source withdrawn while a later candidate was being read; a changed batch yields no passages. Saved result resolution checks index membership, generation, fingerprints and the current source policy. These are local policy checks, not remote identity/authentication or distributed concurrency acceptance. Permission can change after return; every later citation read must revalidate.

## Encoder and artifacts

The semantic extra pins Sentence Transformers and CPU PyTorch in `uv.lock`. The adapter loads only cached `sentence-transformers/all-MiniLM-L6-v2` revision `ee8519ce6a28a61c9190da0a16e199d262197a1b`, with remote code disabled, no token and no automatic download. Configuration is CPU, four threads, batch size 32, 384 dimensions, unit normalization and float32. The actual tokenizer includes special tokens when checking the 256-token budget for every passage and query. The corpus's 128-word limit is not substituted for that token check.

A private index directory holds immutable `idx-<hash>` generations, `manifest.json`, `records.json` and an atomic `CURRENT` pointer. Records contain stable IDs, full-chunk fingerprints and optional vectors; original source text stays in SQLite. Manifest schema/retriever/chunker/numerical-package versions, corpus ID/hash, model ID/revision/provider/package versions, dimension/context/normalization/dtype and records hash are validated. Generation identity binds these fields. Files are mode 0600 and directories 0700; loading rejects symbolic links, traversal, malformed JSON, hash/configuration mismatches and invalid vectors. No pickle or executable model-source code is deserialized by the index loader. Artifact hashes establish consistency, not authenticity; model cache/source provenance still requires trusted preparation.

The baseline accepts at most 1,000 unique chunks and 20 MB per artifact. Empty and lexical-only indexes are supported explicitly. Semantic/hybrid requests against a lexical-only index fail rather than changing modes. Publication validates every serialized record before renaming the generation and replacing `CURRENT`. A failed build leaves the prior pointer unchanged and removes its staging files.

For an intentional source/configuration update, ingest the new authorized corpus selection and call `build_index(root, generation, authorized_chunks, at=..., encoder=...)`, then `load_index(..., encoder=...)`. New compatible content/configuration creates a new immutable generation. Existing identical builds reuse it. Corrupt artifacts are rejected, not repaired in place: rebuild into a new private directory from the trusted source and selected encoder. Do not resolve old citations by substituting a new generation. Retained generations obey current withdrawal policy. The publisher must retire old index directories at retention/deletion deadlines; derived vectors and backups need the same source-owner controls as other retained artifacts. This increment's demos delete all temporary artifacts; hosted cleanup/restoration is not implemented.

## Demonstration and comparison

Offline lexical search needs only the default locked environment:

```sh
uv run --locked python scripts/demo_search.py --query 'TLS certificate expiry' --top-k 3
```

The fixed developer grants cover Order/Payment in the synthetic test corpus at `2026-10-12T12:00:00Z`. The demo ingests, indexes, reopens and resolves every returned citation, using temporary state and example two-day retention. Stdout is JSON; stderr contains correlated logs. Valid searches including no-results exit 0; invalid requests and dependencies exit 2. Repeated lexical runs produce identical stdout. These grants and times are fixture configuration, not production permissions or retention policy.

Prepare the real local model explicitly when semantic search is wanted:

```sh
uv sync --locked --extra semantic
uv run --locked --extra semantic python -c 'from huggingface_hub import snapshot_download; snapshot_download("sentence-transformers/all-MiniLM-L6-v2", revision="ee8519ce6a28a61c9190da0a16e199d262197a1b", token=False)'
uv run --locked --extra semantic python scripts/demo_search.py --mode semantic --query 'Which timestamp should be used when logs arrive late?'
make integration-semantic
uv run --locked --extra semantic python -m evaluation.retrieval_baseline --output /tmp/trace-retrieval-review.json
uv run --locked python -m evaluation.retrieval_baseline --rescore evaluation/reports/retrieval_development_v1.json
```

The explicit preparation command downloads public model files; the search/comparison never downloads a missing model. Existing report paths are rejected. `uv run --locked` without the extra may remove optional packages; include `--extra semantic` for each real-model invocation. The cached model used for the recorded comparison was already available; no paid provider or AWS call was made.

The [development query suite](../../evaluation/retrieval/queries_v1.json) and [actual CPU report](../../evaluation/reports/retrieval_development_v1.json) are evaluator-only, excluded from corpus manifests and runtime imports. All modes use the same six documents/18 passages and 10 requests at K=3. Eight queries have hand-authored document judgments; two explicitly lack relevant knowledge. Failed answerable attempts receive zero credit and remain in denominators. Saved suite/attempt hashes permit model-free rescoring; source/lock hashes and model/package configuration identify the measured implementation. This is a small development comparison, not held-out evidence or passage-level human support review.

| Mode | Document Recall@3 (8 queries) | MRR@3 (8 queries) | Failed attempts (10) | Absent queries returning candidates (2) |
| --- | --- | --- | --- | --- |
| Lexical | 1.0000 | 1.0000 | 0 | 2 |
| Semantic | 0.9375 | 1.0000 | 0 | 2 |
| Hybrid | 1.0000 | 1.0000 | 0 | 2 |

Lexical is the default: hybrid added no document-ranking benefit and requires an encoder invocation. Semantic and hybrid remain measured comparison options. A repeated CPU run confirmed the same ranks/metrics; single-run latency includes warm-up/order effects and is descriptive only. No threshold, causal conclusion, pilot usefulness or deployment acceptance follows from these values. The [#17 passage evaluation and context contract](retrieval-evaluation-context.md) records explicit candidate limits, owner thresholds and pending human review; cloud pgvector migration remains gated by ADR 0006. Reranking/ANN/storage changes require measured need.

Fast checks use deterministic fixture vectors only for algorithm/error contracts, plus real lexical process checks; they do not claim encoder quality. The opt-in semantic comparison loads the actual cached model in TRACE's own locked environment. `make integration-live` remains the separate, unconfigured live-provider gate.

The #17 request configuration increments the retriever version to `exact-retrieval.v2`; rebuild v1 indexes explicitly. Existing default request behavior is retained. Broader passage metrics are separate from the v1 document-level report above.
