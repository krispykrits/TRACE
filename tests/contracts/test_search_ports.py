"""Search orchestration works with ports alone, without storage/scoring SDKs."""

from __future__ import annotations

import unittest
from datetime import UTC, datetime

from trace_app.knowledge.index import IndexGeneration, chunk_fingerprint
from trace_app.knowledge.models import (
    CorpusReadContext,
    DocumentMetadata,
    KnowledgeDocument,
    chunk_document,
)
from trace_app.knowledge.ports import SearchRequest
from trace_app.knowledge.search import SearchService


class SearchPortTests(unittest.TestCase):
    def test_injected_scorer_receives_only_authorized_passages(self) -> None:
        at = datetime(2026, 10, 12, 12, tzinfo=UTC)
        context = CorpusReadContext(
            "local:test",
            "test",
            ("payment",),
            "development_reference",
            "2026-10-12T12:00:00Z",
        )
        metadata = DocumentMetadata(
            document_id="reference",
            document_type="runbook",
            title="Example",
            service="payment",
            environment="test",
            source_uri="synthetic://example/reference",
            source_record_id="reference",
            source_revision="v1",
            version="v1",
            provenance="Contract fixture",
            access_scope="local:test",
            access_classification="synthetic_public",
            evaluation_role="development_reference",
            answer_bearing=False,
            valid_from="2026-01-01T00:00:00Z",
            valid_until=None,
            verified_at="2026-10-12T12:00:00Z",
            fresh_until="2026-10-14T12:00:00Z",
        )
        chunks = chunk_document(
            KnowledgeDocument(metadata, "Payment duration evidence.")
        )
        index = IndexGeneration(
            "index-fixture",
            "generation-fixture",
            "a" * 64,
            "2026-10-14T12:00:00Z",
            None,
            tuple(c.chunk_id for c in chunks),
            tuple(chunk_fingerprint(c) for c in chunks),
            None,
        )
        calls: list[tuple[list[str], str]] = []

        class Reader:
            def read_chunks(self, **kwargs):
                return chunks

            def resolve(self, generation_id, chunk_id, **kwargs):
                return next(c for c in chunks if c.chunk_id == chunk_id)

        class Scorer:
            def lexical_scores(self, texts, query):
                calls.append((texts, query))
                return (0.75,)

            def dense_scores(self, vectors, query):
                raise AssertionError("Lexical mode must not invoke dense scoring.")

        service = SearchService(Reader(), index, scorer=Scorer())
        response = service.search(SearchRequest("duration"), context=context, at=at)
        self.assertEqual(response.status, "ok")
        self.assertEqual(calls, [([chunks[0].normalized_text], "duration")])
        self.assertEqual(
            service.resolve(response.results[0], context=context, at=at), chunks[0]
        )
