"""Source adapter seam and bounded curated-file ingestion; no source fetching."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from trace_app.knowledge.models import (
    CorpusInputError,
    KnowledgeDocument,
    _text,
)


@dataclass(frozen=True, slots=True)
class CorpusBatch:
    corpus_version: str
    documents: tuple[KnowledgeDocument, ...]

    def __post_init__(self) -> None:
        _text(self.corpus_version, "corpus_version")
        if not isinstance(self.documents, tuple) or not 1 <= len(self.documents) <= 100:
            raise CorpusInputError("Corpus requires 1–100 documents.")
        if any(not isinstance(doc, KnowledgeDocument) for doc in self.documents):
            raise CorpusInputError("Corpus requires validated documents.")
        ids = [doc.metadata.document_id for doc in self.documents]
        sources = [
            (doc.metadata.source_uri, doc.metadata.source_record_id)
            for doc in self.documents
        ]
        if len(set(ids)) != len(ids) or len(set(sources)) != len(sources):
            raise CorpusInputError("Duplicate document or source record identities.")


class CorpusSource(Protocol):
    """Trusted adapters supply curated content plus source-owned opaque revisions."""

    def load(self) -> CorpusBatch: ...
