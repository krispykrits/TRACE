# Versioned knowledge corpus

Status: proposed implementation for [#15](https://github.com/krispykrits/TRACE/issues/15), 2026-10-12. The small development corpus contains two runbooks, two service references and two explicitly fictional historical notes. Six documents produce 18 chunks. No authorized operational archive, retrieval index, embedding model or investigator is supplied by this increment. [ADR 0008](../adr/0008-local-corpus-generations-and-source-policy.md) records the Local MVP storage and adaptation boundary.

## Curated inputs and source adapters

The [manifest](../../corpus/development/manifest.json) pins document paths and SHA-256 content hashes. Each entry records document ID/type/title/version, service/environment, source URI, source-owned record ID/revision, provenance, access scope/classification, permitted evaluation role, whether historical content bears an answer, validity interval, verification time and freshness deadline. The two historical explanations concern independent fictional certificate/queue examples, rather than answers to the seeded replay cases. They are development material, not operational historical evidence.

[CorpusSource](../../src/trace_app/corpus_sources.py) is the TRACE-owned adapter seam: `load()` supplies a validated `CorpusBatch`. Source record IDs and revisions are opaque; an authorized adapter may preserve a wiki page ID, ETag or object revision without fabricating a synthetic identity or semantic version. HTTPS/S3 links are accepted with restricted classification; no URI is fetched here. Credentials, query strings and fragments are rejected in source links. Permissions and provenance must come from trusted source-owner administration, never from the document's prose or a caller filter.

`CuratedFileSource` reads only unique, explicitly listed `documents/*.md` files from its supplied corpus directory. It verifies their hashes, reads at most 2 MB per file, rejects symbolic-link files/directories, malformed/duplicate JSON fields and unknown metadata. It does not scan repository documentation, evaluator material or arbitrary paths. A batch has 1–100 unique document/source identities, with original text bounded to 32,000 characters per document. The adapter does not silently substitute fixtures after an error.

The checked-in corpus uses `synthetic_public`, `test`, `local:knowledge-development` and `development_reference`. Its fixed November freshness date is fixture configuration, not an operational freshness SLA. A real corpus still requires a named source/data owner, approved access and sanitization, revision semantics, freshness expectations, retention/deletion rules and independent cohort review.

## Normalization and chunking

[KnowledgeChunk](../../src/trace_app/knowledge.py) adapts Volume 4's original-offset, section and overlapping-window contract. Markdown headings identify sections; text before the first heading is a preamble. Whitespace normalization affects `normalized_text` only. Original passage text, character offsets, section, ordinal and the whole document's text hash remain available. Offsets are Python Unicode character offsets, not byte offsets.

The named `section-words.v1` policy uses at most 128 whitespace-delimited words and 4,096 characters per chunk, with up to 16 overlapping words. Character bounds can shrink a window; forward progress and coverage are preserved. An indivisible oversized word fails explicitly. This is a deterministic ingestion policy, not a model token budget. #16 must check actual encoder tokenization before indexing and must not silently truncate passages.

Chunk IDs hash the metadata, document hash, chunker version, section, ordinal, offsets and original passage. Same inputs give the same IDs; content/revision/version/policy changes are distinguishable. Every chunk carries its document/source link, source revision, document version, service/environment, validity, access and evaluation metadata. Stored chunks are validated against their identity, offsets and normalization when read. Hashes establish internal consistency, not source authenticity.

Document text always has `content_role: untrusted_source_data`. Injection-like prose is retained as quoted source data; it cannot change source policy, caller grants or application configuration. No prompt/template execution is implemented. A future investigator must preserve this separation when packaging passages for a model; a data-role marker alone cannot prove model-level injection resistance.

## Atomic ingestion and version identity

[SQLiteCorpusStore](../../src/trace_app/corpus_store.py) uses a separate private local database for corpus state, leaving the investigation schema intact. It publishes source/version records, chunks, the generation manifest and current pointer in one transaction. A conflict or failed insert rolls back the entire publication, including source-policy updates. Reads and citation resolution observe a consistent transaction. This serialized small-corpus adapter is not hosted concurrency acceptance.

Generations record schema/corpus/chunker versions, a canonical corpus fingerprint, creation time, explicit retention deadline and original document/chunk counts. Their IDs derive from the corpus fingerprint and retention deadline. Document ordering does not change identity. Repeating the same ingestion while it remains current reuses its generation, chunks and original creation time, including after restart. A changed corpus or retention policy produces a different generation.

Source content revisions and TRACE document snapshot versions are distinct. Reusing a source revision with different original text fails. Reusing a document version with different content/metadata fails. A source-owner access/freshness update can keep the content revision and introduce a new document snapshot version. Superseded known revisions/versions and older verification times cannot roll back current policy. Document IDs cannot be reassigned to different source identities; the same source record cannot be aliased under another document ID.

Ingestion is a trusted publisher operation, not an investigator tool or a remote API. #15 defines and tests the boundary; source authentication, live fetching and distributed dispatch remain later work. The SQLite file is mode 0600. Correlated ingestion/withdrawal/purge logs include generation IDs and counts without document text, source URLs or credentials. Database/schema failures propagate as `CorpusDependencyError`.

## Access, freshness and saved citations

`CorpusReadContext` supplies trusted scope, environment, allowed services, permitted evaluation role and the time at which content must be valid. A caller-selected service filter cannot grant these capabilities. Both original chunk metadata and the current source policy must permit a read, including a citation from an older generation. Freshness is checked at the supplied current time; validity is checked at the context's incident/reference time. Validity intervals are start-inclusive/end-exclusive; freshness and retention deadlines are exclusive, including fractional timestamps.

`read_chunks(context=..., at=..., generation_id=...)` exposes only eligible content. No eligible chunks returns an empty tuple, without disclosing denied source counts. Missing/expired generations raise `CorpusAccessError`; storage or malformed stored data raises `CorpusDependencyError`. `resolve(generation_id, chunk_id, ...)` repeats the same current-policy checks and raises an unavailable/access error for an unresolved ID. A new principal cannot gain old snapshot content merely because the current scope changed. #16 must use this boundary before candidate ranking and again for citations; caches/indexes cannot replace these checks.

Current validity/freshness restrictions are conservative: an old snapshot cannot be used to bypass a stricter current source policy. Revalidation of current content does not renew an old snapshot's own freshness deadline. Retention does not imply freshness or permission.

## Updates, tombstones and retention

Ingestion describes the new current corpus selection. Omitting a document removes it from that selection; it does not imply source deletion and does not revoke a still-permitted historical snapshot. An actual source deletion/revocation must use the explicit trusted administration operation:

- `withdraw(document_id, reason="revoked", at=...)` creates a sticky current tombstone denying every retained generation/citation. Historical passages remain until their retention deadline for approved audit needs.
- `withdraw(document_id, reason="deleted", at=...)` denies every generation and removes that document's chunk payloads across all generations. The non-passage source/version/tombstone ledger remains to prevent accidental resurrection. Deletion cannot be downgraded to revocation.
- `purge_expired(at=...)` deletes expired generations and their chunk payloads transactionally and clears an expired current pointer. There is no fallback to an older generation.

Old generations keep their original identity/count metadata; withdrawals can remove payloads, and counts are not claims about current authorized availability. Tombstoned documents cannot be restored by re-ingestion; a future source-owner restoration policy would need explicit design and tests. Every publication requires an explicit `retain_until`; no operational duration is invented. Expired content is denied immediately even before purge. The local publisher must call purge; a scheduled hosted retention job is not implemented.

SQLite secure deletion is enabled for the live database. Backup copies, journals, exports and forensic media erasure need operational retention controls before real-source use. This local test does not certify backup deletion or cloud recovery. Content already exported outside the adapter cannot be remotely revoked; future caches/exports must retain scope/version/expiry and enforce source withdrawals.

## Contamination checklist

Before admitting a source, the curator/source owner must establish identity and permission, then check:

1. No evaluator manifest, label payload, validation/final-test document or answer-bearing held-out postmortem is included. Allowed roles are `development_reference` and `shared_reference`; answer-bearing content is restricted to development. Do not allocate related incident variants to an independent held-out cohort.
2. References are generally useful procedures/topology or independently selected permitted history, without held-out IDs, scenario answer keys or case-specific supporting ordinals. Explicitly record fictional versus real provenance. Do not claim that selecting a tiny reference set establishes retrieval quality.
3. No credentials or unnecessary sensitive content remain. Access classification/scope, time validity, freshness and retention reflect actual source-owner policy before real ingestion.
4. Treat source prose as untrusted data. It cannot grant permissions, modify instructions or authorize remediation. Preserve source links and original passages for review.

The strict schemas reject extra evaluator fields, held-out roles and known label markers (`ground_truth`, `incident_label`, `cause_label`, `expected_assessment`) in text. This is defense in depth; a parser cannot identify every paraphrased answer or secret. Curatorial review and cohort isolation remain necessary. Development answer-bearing notes must never enter a held-out study through a shared-reference role.

## Demonstration and checks

From the repository root:

```sh
uv run --locked python scripts/demo_corpus.py
make check lint format-check type-check test integration
```

The demo uses a fixed synthetic clock, two-day example retention, a temporary database and fixed development grants. It ingests twice with a restart, reports first-created/second-reused flags, and resolves all 18 chunk IDs to source metadata and original passages. Two complete invocations produce identical stdout; temporary state is removed after completion/failure. `--corpus PATH` accepts only a compatible synthetic development selection, not production source publishing.

Tests cover metadata, Unicode/original offsets, long overlapping sections, stable IDs, idempotency/restart, real-shaped source identities, content versus policy revisions, failed-transaction rollback, older-policy rejection, scope/environment/service/cohort denial, saved-citation revocation across generations, deletion, validity/freshness/retention, tampered chunks and forbidden paths/labels. These offline checks supply contract evidence only. Semantic/lexical/hybrid retrieval and measured corpus usefulness belong to #16 and later acceptance.
