# ADR 0008: Local corpus generations and current source policy

- **Status:** Accepted with merged [PR #43](https://github.com/krispykrits/TRACE/pull/43) for issue #15
- **Date:** 2026-10-12
- **Decision owner:** Project owner, through the scoped implementation review
- **Scope:** Local knowledge ingestion and saved chunk access; embeddings/retrieval remain #16

## Context

The approved amendment requires adaptation of Volume 4 provenance/chunking/generation contracts, with real source identity, updates/deletions, freshness and revocation. Volume 4 preserves original passages and offsets, normalizes separate ranking text, hashes stable chunk identities and publishes validated generations atomically. Its source schema requires synthetic IDs/URIs and its storage does not enforce source withdrawals across generations. TRACE must add those controls while keeping one modular application and no sibling runtime dependency.

SQLite is already the Local MVP persistence direction. The cloud direction is Azure PostgreSQL with pgvector under ADR 0015; the Local SQLite/PostgreSQL contract decisions in ADRs 0005/0006 are retained. No embedding model, runtime dependency or authorized operational corpus has been selected for this story.

## Decision

Adapt Volume 4 section spans, whitespace normalization, offset-window chunking, provenance fields, stable hashes and validate-before-publication semantics into TRACE-owned contracts. Use a source adapter that accepts opaque record/revision identifiers and credential-free source links. Keep text untrusted and permitted evaluation use explicit. Use a small standard-library word-window chunker until #16 selects and measures encoder/tokenization details; the ingestion word limit is not a model token budget.

Persist bounded local generations and the current source/tombstone ledger in a separate private SQLite corpus database. A single transaction publishes the complete generation and current pointer. Immutable chunk records preserve original source metadata, while every read/citation also checks current policy. Permission changes can introduce a new document snapshot version without inventing a new source content revision. Superseded snapshots cannot overwrite current policy. Explicit withdrawals affect all retained generations, with payload deletion for deleted sources and mandatory per-generation retention deadlines.

Investigation tools receive read operations and trusted grants. Corpus ingestion/withdrawal/purge are source-owner administration, not model tools. No HTTP authentication or real-source permission is claimed by a typed context. The adapter and policy invariants must carry forward to retrieval and cloud storage.

## Adaptation record

The local Volume 4 source folder is `incident-search`; it has no Git metadata. The source files inspected for this adaptation are pinned by SHA-256:

| Volume 4 path under `src/incident_search/` | SHA-256 |
| --- | --- |
| `domain.py` | `ad7cbac91db4df2caef63de5c0f2e925dfef35de2129a7ba2152084d25c3c96b` |
| `chunking/__init__.py` | `c6fa472fa50303c71043d02df860c726be22b1676f436a026ecff9af4d07caa6` |
| `ingestion/__init__.py` | `86d416634ada404a66bb8348601ec9d3dd26ab397896e7b299f18f8db7ff6872` |
| `indexing/__init__.py` | `8495f6964b29ff8df449ee1c48b8489c6e08833b05c3112c447d05d8b3cd17c0` |

TRACE keeps the provenance/generation principles and adapts the standard-library section/window algorithm. Pydantic, model tokenization, lexical/vector artifacts and unsafe deserialization are not imported into ingestion. Encoder-specific contracts and retrieval reuse belong to #16. Original Volume 4 tests informed offset/coverage/revision assertions; TRACE's tests run in its own locked environment without sibling imports.

## Alternatives and tradeoffs

| Option | Disposition |
| --- | --- |
| Import the Volume 4 application unchanged | Rejected: synthetic-only identities, new dependency set and absent revocation boundary |
| Copy its generation directories and add a separate mutable policy file | Deferred: coordinating pointer/policy updates adds an unnecessary local atomicity boundary |
| SQLite generations plus current policy | Selected for the bounded local corpus; transactional publication and withdrawals, with serialized reads/writes |
| Provision cloud PostgreSQL/pgvector now | Deferred to the approved cloud gates; no access, workload or cost acceptance is provided; current hosting follows ADR 0015 |

The generation manifests record original counts; deletion can intentionally remove content without changing historical generation identity. A current policy check can make retained chunks unavailable. Retention purge is explicit administration, with scheduled execution, backups, exports and recovery left to hosted design. This implementation does not establish retrieval quality, pilot usefulness or production erasure guarantees.

## Revisit conditions

Revisit the chunker when #16 evaluates encoder tokenization and retrieval quality. Revisit serialized SQLite access with measured concurrency/scale or S7 migration design. Before authorized real-source ingestion, settle source authentication, curation/cohort review, freshness, retention/deletion and restoration authority. Any new index/cache/export must prove current-policy and tombstone enforcement before it can resolve saved citations.
