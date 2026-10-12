"""Authorized exact lexical/semantic retrieval and Volume 4 reciprocal-rank fusion."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import datetime

from trace_app.evidence import _parse_utc, format_utc
from trace_app.knowledge import (
    CorpusAccessError,
    CorpusDependencyError,
    CorpusReadContext,
    KnowledgeChunk,
)
from trace_app.retrieval_backends import dense_scores, lexical_scores, validate_vectors
from trace_app.retrieval_contracts import (
    CANDIDATE_POOL,
    RRF_K,
    CorpusReader,
    Encoder,
    RetrievalResult,
    SearchInputError,
    SearchRequest,
    SearchResponse,
)
from trace_app.retrieval_index import IndexGeneration, chunk_fingerprint

_LOG = logging.getLogger("trace_app.retrieval")


class SearchService:
    def __init__(
        self,
        reader: CorpusReader,
        index: IndexGeneration,
        encoder: Encoder | None = None,
    ) -> None:
        self._reader, self.index, self._encoder = reader, index, encoder

    def search(
        self, request: SearchRequest, *, context: CorpusReadContext, at: datetime
    ) -> SearchResponse:
        format_utc(at)
        if (
            request.service is not None
            and request.service not in context.allowed_services
        ):
            raise CorpusAccessError(
                "Requested service is outside trusted access grants."
            )

        def response(status, reason=None, eligible=0, candidates=0, results=()):
            result = SearchResponse(
                status,
                reason,
                request.mode,
                self.index.index_id,
                self.index.corpus_generation_id,
                eligible,
                candidates,
                results,
            )
            _LOG.info(
                "Knowledge search completed.",
                extra={
                    "event": "retrieval.completed",
                    "retrieval_status": status,
                    "retrieval_mode": request.mode,
                    "index_generation_id": self.index.index_id,
                    "result_count": len(results),
                },
            )
            return result

        if at >= _parse_utc(self.index.retain_until):
            return response("source_unavailable", "index_retention_expired")
        try:
            # This must precede every branch and any query encoder invocation.
            authorized = self._reader.read_chunks(
                context=context, at=at, generation_id=self.index.corpus_generation_id
            )
        except CorpusAccessError:
            return response("source_unavailable", "corpus_generation_unavailable")
        except CorpusDependencyError:
            return response("storage_failure", "corpus_read_failed")
        positions = {
            identity: ordinal for ordinal, identity in enumerate(self.index.chunk_ids)
        }
        for chunk in authorized:
            position = positions.get(chunk.chunk_id)
            if (
                position is None
                or chunk_fingerprint(chunk) != self.index.chunk_fingerprints[position]
            ):
                return response(
                    "index_incompatible",
                    "source_coverage_or_provenance_changed_rebuild",
                )
        eligible = tuple(
            chunk
            for chunk in authorized
            if (request.service is None or chunk.metadata.service == request.service)
            and (
                request.document_type is None
                or chunk.metadata.document_type == request.document_type
            )
        )
        if not eligible:
            return response("no_results", "no_authorized_matching_chunks")

        def ordered(
            scores: tuple[float, ...], *, positive: bool = False
        ) -> list[tuple[str, float]]:
            pairs = [
                (chunk.chunk_id, score)
                for chunk, score in zip(eligible, scores, strict=True)
                if not positive or score > 0
            ]
            return sorted(pairs, key=lambda pair: (-pair[1], pair[0]))[:CANDIDATE_POOL]

        lexical: list[tuple[str, float]] = []
        dense: list[tuple[str, float]] = []
        if request.mode in ("lexical", "hybrid"):
            lexical = ordered(
                lexical_scores(
                    [chunk.normalized_text for chunk in eligible], request.query
                ),
                positive=True,
            )
        if request.mode in ("semantic", "hybrid"):
            if (
                self._encoder is None
                or self.index.embedding is None
                or self.index.vectors is None
            ):
                return response(
                    "provider_failure", "semantic_encoder_or_vectors_unavailable"
                )
            if self._encoder.spec != self.index.embedding:
                return response("index_incompatible", "query_encoder_differs_rebuild")
            try:
                query = validate_vectors(
                    self._encoder.encode([request.query]),
                    1,
                    self._encoder.spec.dimension,
                )[0]
                vectors = tuple(
                    self.index.vectors[positions[chunk.chunk_id]] for chunk in eligible
                )
                dense = ordered(dense_scores(vectors, query))
            except SearchInputError:
                raise
            except Exception:
                return response("provider_failure", "query_embedding_failed")
        if request.mode == "lexical":
            ranked = lexical
        elif request.mode == "semantic":
            ranked = dense
        else:
            fused: dict[str, float] = {}
            for branch in (lexical, dense):
                for rank, (identity, _) in enumerate(branch, 1):
                    fused[identity] = fused.get(identity, 0.0) + 1 / (RRF_K + rank)
            ranked = sorted(fused.items(), key=lambda pair: (-pair[1], pair[0]))
        if not ranked:
            return response("no_results", "no_lexical_overlap", len(eligible))
        lookup = {chunk.chunk_id: chunk for chunk in eligible}
        results: list[RetrievalResult] = []
        counts: Counter[str] = Counter()
        try:
            for identity, score in ranked:
                chunk = lookup[identity]
                if counts[chunk.metadata.document_id] >= 1:
                    continue
                # Repeat source authorization immediately before exposing a candidate.
                resolved = self._reader.resolve(
                    self.index.corpus_generation_id, identity, context=context, at=at
                )
                if resolved != chunk:
                    return response("index_incompatible", "citation_changed_rebuild")
                counts[chunk.metadata.document_id] += 1
                results.append(
                    RetrievalResult(
                        len(results) + 1,
                        score,
                        resolved,
                        self.index.corpus_generation_id,
                    )
                )
                if len(results) == request.top_k:
                    break
            # A later candidate read must not let an earlier, now-withdrawn result escape.
            final = {
                chunk.chunk_id: chunk
                for chunk in self._reader.read_chunks(
                    context=context,
                    at=at,
                    generation_id=self.index.corpus_generation_id,
                )
            }
            if any(
                final.get(result.chunk.chunk_id) != result.chunk for result in results
            ):
                return response(
                    "source_unavailable", "candidate_withdrawn_during_search"
                )
        except CorpusAccessError:
            return response("source_unavailable", "candidate_withdrawn_during_search")
        except CorpusDependencyError:
            return response("storage_failure", "citation_read_failed")
        return response("ok", None, len(eligible), len(ranked), tuple(results))

    def resolve(
        self, result: RetrievalResult, *, context: CorpusReadContext, at: datetime
    ) -> KnowledgeChunk:
        if (
            result.corpus_generation_id != self.index.corpus_generation_id
            or result.chunk.chunk_id not in self.index.chunk_ids
        ):
            raise CorpusAccessError("Citation is outside this index generation.")
        current = self._reader.resolve(
            result.corpus_generation_id, result.chunk.chunk_id, context=context, at=at
        )
        position = self.index.chunk_ids.index(current.chunk_id)
        if (
            chunk_fingerprint(current) != self.index.chunk_fingerprints[position]
            or current != result.chunk
        ):
            raise CorpusAccessError("Citation source has changed.")
        return current
