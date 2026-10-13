"""Bounded quoted knowledge data with currently authorized citation mappings."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from trace_app.evidence.models import format_utc
from trace_app.knowledge.models import (
    CorpusAccessError,
    CorpusDependencyError,
    CorpusReadContext,
    KnowledgeChunk,
    canonical,
    digest,
)
from trace_app.knowledge.ports import MAX_TOP_K, CorpusReader, SearchResponse

CONTEXT_VERSION = "knowledge-context.v1"
_LOG = logging.getLogger("trace_app.knowledge_context")


class ContextInputError(ValueError):
    """Invalid assembly request or a budget too small for the empty envelope."""


@dataclass(frozen=True, slots=True)
class ContextBudget:
    max_bytes: int = 8_192
    max_passages: int = 5

    def __post_init__(self) -> None:
        if type(self.max_bytes) is not int or not 128 <= self.max_bytes <= 1_000_000:
            raise ContextInputError("max_bytes must be an integer from 128 to 1000000.")
        if (
            type(self.max_passages) is not int
            or not 1 <= self.max_passages <= MAX_TOP_K
        ):
            raise ContextInputError("max_passages must be an integer from 1 to 20.")


@dataclass(frozen=True, slots=True)
class OmittedPassage:
    chunk_id: str
    reason: Literal["duplicate", "overlap", "byte_budget", "passage_budget"]


@dataclass(frozen=True, slots=True)
class KnowledgeContext:
    status: Literal[
        "ok", "empty", "retrieval_failed", "source_unavailable", "storage_failure"
    ]
    retrieval_status: str
    budget: ContextBudget
    serialized_data: str
    omitted: tuple[OmittedPassage, ...]

    @property
    def used_bytes(self) -> int:
        return len(self.serialized_data.encode("utf-8"))

    def to_dict(self) -> dict[str, object]:
        # The diagnostic ledger is outside the model-data byte budget.
        import json

        return {
            "version": CONTEXT_VERSION,
            "status": self.status,
            "retrieval_status": self.retrieval_status,
            "budget": {
                "max_bytes": self.budget.max_bytes,
                "max_passages": self.budget.max_passages,
            },
            "used_bytes": self.used_bytes,
            "data": json.loads(self.serialized_data),
            "omitted": [
                {"chunk_id": item.chunk_id, "reason": item.reason}
                for item in self.omitted
            ],
            "incomplete": self.status
            in ("retrieval_failed", "source_unavailable", "storage_failure")
            or any(item.reason != "duplicate" for item in self.omitted),
            "passage_text_truncated": False,
        }


def _data(selected: list[tuple[str, KnowledgeChunk]], generation_id: str) -> str:
    return canonical(
        {
            "schema_version": "1",
            "content_role": "untrusted_source_data",
            "passages": [
                {"citation_id": identity, "text": chunk.text}
                for identity, chunk in selected
            ],
            "citations": {
                identity: {
                    "corpus_generation_id": generation_id,
                    "chunk_id": chunk.chunk_id,
                    "document_sha256": chunk.document_sha256,
                    "section": chunk.section,
                    "start_offset": chunk.start_offset,
                    "end_offset": chunk.end_offset,
                    "metadata": chunk.metadata.to_dict(),
                }
                for identity, chunk in selected
            },
        }
    )


class ContextAssembler:
    """Policy stays outside quoted data; assembly never executes source prose."""

    def __init__(self, reader: CorpusReader) -> None:
        self._reader = reader

    def assemble(
        self,
        response: SearchResponse,
        *,
        context: CorpusReadContext,
        at: datetime,
        budget: ContextBudget,
    ) -> KnowledgeContext:
        format_utc(at)
        if len(response.results) > MAX_TOP_K:
            raise ContextInputError("Retrieved results exceed the context input bound.")
        empty = _data([], response.corpus_generation_id)
        if len(empty.encode("utf-8")) > budget.max_bytes:
            raise ContextInputError("Budget cannot fit the empty context envelope.")

        def finish(status, selected=(), omitted=()):
            result = KnowledgeContext(
                status,
                response.status,
                budget,
                _data(list(selected), response.corpus_generation_id),
                tuple(omitted),
            )
            _LOG.info(
                "Knowledge context assembled.",
                extra={
                    "event": "knowledge_context.completed",
                    "context_status": status,
                    "corpus_generation_id": response.corpus_generation_id,
                    "passage_count": len(selected),
                    "omitted_count": len(omitted),
                    "context_bytes": result.used_bytes,
                },
            )
            return result

        if response.status not in ("ok", "no_results"):
            if response.results:
                raise ContextInputError("Failed retrieval cannot contain passages.")
            return finish("retrieval_failed")
        if response.status == "no_results" and response.results:
            raise ContextInputError("No-results retrieval cannot contain passages.")
        selected: list[tuple[str, KnowledgeChunk]] = []
        omitted: list[OmittedPassage] = []
        seen: set[str] = set()
        try:
            for result in response.results:
                if result.corpus_generation_id != response.corpus_generation_id:
                    raise ContextInputError(
                        "Citation generation differs from retrieval."
                    )
                # Validate provenance, then authorize even candidates that may be omitted.
                chunk = KnowledgeChunk.from_dict(result.chunk.to_dict())
                current = self._reader.resolve(
                    result.corpus_generation_id,
                    chunk.chunk_id,
                    context=context,
                    at=at,
                )
                if current != chunk:
                    return finish("source_unavailable")
                if chunk.chunk_id in seen:
                    omitted.append(OmittedPassage(chunk.chunk_id, "duplicate"))
                    continue
                seen.add(chunk.chunk_id)
                overlapping = any(
                    earlier.metadata == chunk.metadata
                    and earlier.document_sha256 == chunk.document_sha256
                    and max(earlier.start_offset, chunk.start_offset)
                    < min(earlier.end_offset, chunk.end_offset)
                    for _, earlier in selected
                )
                if overlapping:
                    omitted.append(OmittedPassage(chunk.chunk_id, "overlap"))
                    continue
                if len(selected) >= budget.max_passages:
                    omitted.append(OmittedPassage(chunk.chunk_id, "passage_budget"))
                    continue
                identity = "knowledge-" + digest(
                    canonical(
                        {
                            "corpus_generation_id": result.corpus_generation_id,
                            "chunk_id": chunk.chunk_id,
                        }
                    )
                )
                candidate = selected + [(identity, chunk)]
                if (
                    len(_data(candidate, response.corpus_generation_id).encode("utf-8"))
                    > budget.max_bytes
                ):
                    omitted.append(OmittedPassage(chunk.chunk_id, "byte_budget"))
                    continue
                selected = candidate
            # One consistent final read protects earlier passages from later withdrawals.
            if selected:
                current_chunks = {
                    chunk.chunk_id: chunk
                    for chunk in self._reader.read_chunks(
                        context=context,
                        at=at,
                        generation_id=response.corpus_generation_id,
                    )
                }
                if any(
                    current_chunks.get(chunk.chunk_id) != chunk for _, chunk in selected
                ):
                    return finish("source_unavailable")
        except CorpusAccessError:
            return finish("source_unavailable")
        except CorpusDependencyError:
            return finish("storage_failure")
        return finish("ok" if selected else "empty", selected, omitted)
