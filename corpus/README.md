# Curated knowledge sources

`development/manifest.json` selects six TRACE-authored development references: two runbooks, two service documents and two fictional historical incident notes. Each source is pinned by a content hash and explicit provenance, source revision, service/environment, access, permitted evaluation use and time metadata. Fictional histories are development-only answer-bearing material, independent of replay answers. No authorized operational history or held-out corpus is supplied.

Run `uv run --locked python scripts/demo_corpus.py` from the repository root to ingest twice across a restart and resolve all 18 chunks to their sources. The demo uses temporary SQLite state and a fixed synthetic clock. See the [corpus contract and contamination checklist](../docs/architecture/knowledge-corpus.md) and [adaptation/storage ADR](../docs/adr/0008-local-corpus-generations-and-source-policy.md).

Do not place evaluator manifests, labels, final-test/validation answers, credentials or unreviewed operational exports here. Update the document snapshot version and hash for changes; preserve source-owned content revisions, and introduce a new snapshot version for source policy changes. Real ingestion requires source-owner permission and an independently reviewed cohort, freshness and retention policy.
