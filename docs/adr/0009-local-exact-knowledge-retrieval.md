# ADR 0009: Pinned local embedding and exact knowledge retrieval

- **Status:** Accepted through merged [PR #44](https://github.com/krispykrits/TRACE/pull/44) for issue #16
- **Date:** 2026-10-12
- **Decision owner:** Project owner, through scoped implementation review
- **Scope:** Local MVP read-only retrieval; cloud direction remains ADR 0006

## Context

Issue #16 and the approved amendment require adapting Volume 4 lexical/semantic/hybrid baselines, measuring development evidence, enforcing source authorization before ranking and citations, and retaining exact search as a correctness baseline. Issue #15 provides six source-linked development documents, 18 stable passages and current source policy. No authorized operational corpus, provider budget, hosted workload or pilot acceptance is supplied.

Volume 4 already implements technical TF-IDF, normalized MiniLM embeddings, exact similarity and reciprocal-rank fusion. TRACE needs its own contracts and reproducible environment, with source-policy checks absent from that educational application. A separate vector service or reranker has no measured need at this scale.

## Decision

Adapt these algorithms into TRACE-owned encoder/reader ports and a bounded `SearchService`. Select exact normalized float32 dot products and JSON index records for the small local baseline. Source text/current policy remain in the existing SQLite corpus adapter. Do not deserialize Volume 4's serialized Python/lexical artifacts; fit TF-IDF only on currently authorized passages, so withdrawals also remove influence on IDF. Authorize before scoring/encoding, resolve candidates under current policy and recheck the complete result batch. Treat all passage text as untrusted source data.

Add pinned runtime NumPy 2.5.3 and scikit-learn 1.9.1 to reuse the numerical and lexical algorithms, rather than writing replacement numerical/TF-IDF machinery. Their transitive versions are locked. The optional `semantic` extra pins Sentence Transformers 5.7.0 and CPU-only PyTorch 2.14.0+cpu, through uv's explicit PyTorch CPU index. Default CI installs neither model packages nor weights; deterministic fixture vectors cover algorithms/failure paths. Actual model acceptance is a separate cached/offline invocation in TRACE's environment.

Use `sentence-transformers/all-MiniLM-L6-v2` at immutable revision `ee8519ce6a28a61c9190da0a16e199d262197a1b`, 384 dimensions, normalized float32, CPU/four threads, batch 32 and 256-token context including special tokens. Reject over-budget input instead of truncating. Disable remote code, authentication tokens and implicit downloads; missing cache/package errors have no fixture or lexical fallback. The [Sentence Transformers interface](https://sbert.net/docs/package_reference/sentence_transformer/model.html) supports revision, local-only loading and normalization; the [model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) documents the embedding model. The [uv PyTorch guide](https://docs.astral.sh/uv/guides/integration/pytorch/) describes explicit CPU index configuration. Model caches must be prepared from a trusted pinned source; revision/hashes are not proof of cache authenticity.

Bind immutable artifact identity to corpus generation/hash, chunk IDs/full-provenance fingerprints, vector records hash, named schema/retriever/chunker and numerical-package versions, model/provider/revision/package versions and encoder configuration. Reject incompatible or corrupt artifacts with explicit rebuild instructions. Private validated JSON generations and atomic pointer publication preserve the prior index after a failed build. Retention/source withdrawals still govern reads and saved citations; derived artifacts require publisher cleanup. This is local visibility atomicity, not distributed/crash-durability or backup-erasure acceptance.

## Development evidence and default

The [report](../../evaluation/reports/retrieval_development_v1.json) runs all three adapted modes on the same six documents/18 passages and ten evaluator-only development queries with the real cached model. Eight answerable document judgments yield Recall@3/MRR@3 of 1.0/1.0 for lexical, 0.9375/1.0 for semantic and 1.0/1.0 for hybrid, with zero failures in 30 attempts. A repeat run produced the same ranks/metrics. Choose **lexical as the default** because hybrid added no measured ranking benefit and requires embedding work; keep semantic/hybrid explicit options for comparison.

All modes returned candidates on both absent-knowledge queries. Do not infer answerability from returned ranks, select an arbitrary similarity cutoff or claim causal evidence. These hand-authored development judgments do not establish general retrieval quality, passage-level support or operational usefulness. #17 owns broader retrieval evaluation and bounded evidence context. Configuration/latency/package/source hashes and raw ranks are recorded; failed attempts remain in metric denominators. No paid calls were made.

## Adaptation record

The local educational `incident-search` folder has no Git metadata. Inspected Volume 4 files are pinned by SHA-256; no runtime import or environment is inherited:

| Path under `src/incident_search/` | SHA-256 |
| --- | --- |
| `indexing/embedding.py` | `845c066f8005fcce8fc189c3d66ff309bde0acaba3504a8072cae0f9ef64ba5b` |
| `indexing/lexical.py` | `61500ea8ac490fa112681cce946295632e3645bb6f44898618196f513b46359b` |
| `retrieval/__init__.py` | `ebaaaee463a0fb34c861cd6a47e72bdc80d6f67981fbbec1a99c8e9b671d0424` |

TRACE retains technical tokens (including paths/codes/dotted identifiers and negation), sublinear TF-IDF uni/bigrams, exact scores, stable ID tie-breaking, 100 candidates per branch, RRF constant 60 and one passage per document. It adds current scope/cohort/time/freshness/revocation controls, explicit no-fallback errors, actual token-budget checks and safe versioned artifacts. No new reranker is introduced.

## Alternatives and tradeoffs

| Option | Disposition |
| --- | --- |
| Exact local JSON vectors + existing SQLite corpus | Selected for the bounded correctness baseline; simple validation, no service, linear scans and rebuilds |
| Import Volume 4 unchanged | Rejected: sibling dependency, synthetic-only assumptions and missing current-policy enforcement |
| Implement replacement pure-Python TF-IDF/embeddings | Rejected: rebuilds educational algorithms rather than adapting them; no measured benefit |
| Hosted embedding API | Deferred: no approved provider/budget, requires credentials/network and paid acceptance |
| Dense or hybrid by default | Deferred: measured development ranking did not beat lexical; options remain explicit |
| RDS/pgvector or ANN now | Deferred to approved Cloud MVP gates/scale evidence; no database, extension or vector service provisioned |
| Reranking or a separate vector database | Deferred until measured need and preserved source/citation contracts |

The 1,000-chunk/20 MB artifact and top-K bounds are implementation limits, not operational capacity/SLA commitments. Package/configuration changes reject old indexes and require rebuilds; conservative compatibility trades reuse for traceability. Exact search and current authorization checks must remain available as a migration correctness reference.

## Revisit conditions

Revisit defaults/token-window policy on broader independently reviewed development queries and actual encoder-budget failures. Revisit linear scans or serialized local policy reads with measured workload/concurrency and cloud migration evidence. Preserve version, citation, source-policy and no-fallback contracts through pgvector migration. Before real-source use, settle source identity/access, freshness, retention/derived-artifact deletion, cache provenance and independent cohort review. Do not treat synthetic ranking or local model execution as Operational Pilot acceptance.

## #17 candidate configuration extension — 2026-10-12

The [passage evaluation/context contract](../architecture/retrieval-evaluation-context.md) records a measured section-recall gap with the one-passage-per-document baseline. Adapt Volume 4's existing configurable limits behind `SearchRequest`: defaults remain candidate pool 100 and one passage per document; #17 explicitly retains pool 20 and up to 20 passages per document before a five-passage/byte-bounded context. The owner supplied primary/secondary K, minimum 100 queries and thresholds before measurement. Lexical remains the existing default; no reranker or new dependency is selected. Human judgment review and acceptance remain pending. Version `exact-retrieval.v2` requires explicit index rebuilding; chunk/source/embedding identities remain unchanged.
