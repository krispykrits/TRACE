"""Validated search-index identity and provenance records."""

from __future__ import annotations

from dataclasses import dataclass

from trace_app.knowledge.models import KnowledgeChunk, canonical, digest
from trace_app.knowledge.ports import EncoderSpec


def chunk_fingerprint(chunk: KnowledgeChunk) -> str:
    return digest(canonical(chunk.to_dict()))


@dataclass(frozen=True, slots=True)
class IndexGeneration:
    index_id: str
    corpus_generation_id: str
    corpus_sha256: str
    retain_until: str
    embedding: EncoderSpec | None
    chunk_ids: tuple[str, ...]
    chunk_fingerprints: tuple[str, ...]
    vectors: tuple[tuple[float, ...], ...] | None
