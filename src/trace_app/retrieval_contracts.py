"""Bounded retrieval contracts; ranking never establishes causal support."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Literal, Protocol

from trace_app.knowledge import CorpusReadContext, KnowledgeChunk, _text

SearchMode = Literal["lexical", "semantic", "hybrid"]
RETRIEVAL_VERSION = "exact-retrieval.v2"
MAX_TOP_K = 20
CANDIDATE_POOL = 100
RRF_K = 60


class SearchInputError(ValueError):
    """Invalid request, including text outside the encoder's context budget."""


class EncoderFailure(RuntimeError):
    """Unavailable encoder or failed embedding operation; no fallback."""


class IndexCompatibilityError(RuntimeError):
    """Rejected index/configuration; rebuild with the selected source and encoder."""


@dataclass(frozen=True, slots=True)
class EncoderSpec:
    model_id: str
    revision: str
    dimension: int
    max_sequence_length: int
    provider: str
    packages: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        for name in ("model_id", "revision", "provider"):
            _text(getattr(self, name), name)
        if type(self.dimension) is not int or not 1 <= self.dimension <= 4_096:
            raise SearchInputError("Encoder dimension is invalid.")
        if (
            type(self.max_sequence_length) is not int
            or not 4 <= self.max_sequence_length <= 8_192
        ):
            raise SearchInputError("Encoder context length is invalid.")
        if not isinstance(self.packages, tuple) or len(self.packages) > 20:
            raise SearchInputError("Encoder package versions are invalid.")
        for name, version in self.packages:
            _text(name, "package")
            _text(version, "package_version")
        if len({name for name, _ in self.packages}) != len(self.packages):
            raise SearchInputError("Encoder package versions must be unique.")
        object.__setattr__(self, "packages", tuple(sorted(self.packages)))

    def to_dict(self) -> dict[str, object]:
        return {
            **asdict(self),
            "packages": dict(self.packages),
            "normalized": True,
            "dtype": "float32",
        }


class Encoder(Protocol):
    @property
    def spec(self) -> EncoderSpec: ...

    def encode(self, texts: list[str]) -> tuple[tuple[float, ...], ...]: ...


class CorpusReader(Protocol):
    def read_chunks(
        self,
        *,
        context: CorpusReadContext,
        at: datetime,
        generation_id: str | None = None,
    ) -> tuple[KnowledgeChunk, ...]: ...

    def resolve(
        self,
        generation_id: str,
        chunk_id: str,
        *,
        context: CorpusReadContext,
        at: datetime,
    ) -> KnowledgeChunk: ...


@dataclass(frozen=True, slots=True)
class SearchRequest:
    query: str
    top_k: int = 5
    mode: SearchMode = "lexical"
    service: str | None = None
    document_type: str | None = None
    candidate_pool: int = CANDIDATE_POOL
    max_chunks_per_document: int = 1

    def __post_init__(self) -> None:
        if (
            not isinstance(self.query, str)
            or not self.query.strip()
            or len(self.query) > 4_000
            or "\x00" in self.query
        ):
            raise SearchInputError(
                "query requires 1–4,000 nonblank characters without NUL."
            )
        if type(self.top_k) is not int or not 1 <= self.top_k <= MAX_TOP_K:
            raise SearchInputError("top_k must be an integer from 1 through 20.")
        if (
            type(self.candidate_pool) is not int
            or not self.top_k <= self.candidate_pool <= CANDIDATE_POOL
        ):
            raise SearchInputError(
                "candidate_pool must be an integer from top_k through 100."
            )
        if (
            type(self.max_chunks_per_document) is not int
            or not 1 <= self.max_chunks_per_document <= MAX_TOP_K
        ):
            raise SearchInputError(
                "max_chunks_per_document must be an integer from 1 through 20."
            )
        if self.mode not in ("lexical", "semantic", "hybrid"):
            raise SearchInputError("mode requires lexical, semantic or hybrid.")
        if self.service is not None:
            _text(self.service, "service")
        if self.document_type is not None and self.document_type not in (
            "runbook",
            "service",
            "incident",
            "postmortem",
            "architecture",
            "troubleshooting",
        ):
            raise SearchInputError("document_type is unsupported.")


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    rank: int
    score: float
    chunk: KnowledgeChunk
    corpus_generation_id: str

    def to_dict(self) -> dict[str, object]:
        return {
            "rank": self.rank,
            "score": self.score,
            "chunk": self.chunk.to_dict(),
            "citation": {
                "corpus_generation_id": self.corpus_generation_id,
                "chunk_id": self.chunk.chunk_id,
                "source_uri": self.chunk.metadata.source_uri,
                "source_revision": self.chunk.metadata.source_revision,
                "start_offset": self.chunk.start_offset,
                "end_offset": self.chunk.end_offset,
            },
        }


@dataclass(frozen=True, slots=True)
class SearchResponse:
    status: Literal[
        "ok",
        "no_results",
        "provider_failure",
        "index_incompatible",
        "source_unavailable",
        "storage_failure",
    ]
    reason: str | None
    mode: SearchMode
    index_generation_id: str
    corpus_generation_id: str
    eligible_chunks: int
    candidate_count: int
    results: tuple[RetrievalResult, ...]
    candidate_pool: int = CANDIDATE_POOL
    max_chunks_per_document: int = 1

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1",
            "status": self.status,
            "reason": self.reason,
            "mode": self.mode,
            "index_generation_id": self.index_generation_id,
            "corpus_generation_id": self.corpus_generation_id,
            "eligible_chunks": self.eligible_chunks,
            "candidate_count": self.candidate_count,
            "candidate_pool": self.candidate_pool,
            "max_chunks_per_document": self.max_chunks_per_document,
            "score_semantics": "Within-retriever ranking only; not probability, answerability or causal support.",
            "results": [result.to_dict() for result in self.results],
        }
