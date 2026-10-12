"""Fast retrieval contract tests: fixture vectors, never model-quality evidence."""

from __future__ import annotations

import json
import math
import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast
from unittest.mock import Mock, patch

from trace_app.corpus_sources import CuratedFileSource
from trace_app.corpus_store import SQLiteCorpusStore
from trace_app.knowledge import (
    CorpusAccessError,
    CorpusDependencyError,
    CorpusReadContext,
    canonical,
)
from trace_app.retrieval import SearchService
from trace_app.retrieval_backends import (
    LocalSentenceEncoder,
    lexical_scores,
    technical_tokens,
    validate_vectors,
)
from trace_app.retrieval_contracts import (
    EncoderFailure,
    EncoderSpec,
    IndexCompatibilityError,
    SearchInputError,
    SearchRequest,
)
from trace_app.retrieval_index import build_index, load_index

_ROOT = Path(__file__).resolve().parents[1]
_AT = datetime(2026, 10, 12, 12, tzinfo=UTC)
_RETAIN = "2026-10-14T12:00:00Z"
_CONTEXT = CorpusReadContext(
    "local:knowledge-development",
    "test",
    ("order", "payment"),
    "development_reference",
    "2026-10-12T12:00:00Z",
)


class FixtureEncoder:
    """Volume 4 test-style normalized vectors; explicitly evaluator/test-only."""

    def __init__(self) -> None:
        self.spec = EncoderSpec(
            "fixture-encoder", "fixture.v1", 3, 256, "test_fixture", ()
        )
        self.calls: list[list[str]] = []

    def encode(self, texts: list[str]) -> tuple[tuple[float, ...], ...]:
        self.calls.append(texts)
        vectors = []
        for text in texts:
            values = (
                1 + text.lower().count("timeout"),
                1 + text.lower().count("certificate"),
                1,
            )
            norm = math.sqrt(sum(value * value for value in values))
            vectors.append(tuple(value / norm for value in values))
        return tuple(vectors)


class RetrievalTests(unittest.TestCase):
    def test_explicit_candidate_limits_preserve_sections_and_default_diversity(
        self,
    ) -> None:
        legacy = self.service.search(
            SearchRequest("Payment request caller work", 20), context=_CONTEXT, at=_AT
        )
        candidate = self.service.search(
            SearchRequest(
                "Payment request caller work",
                20,
                candidate_pool=20,
                max_chunks_per_document=20,
            ),
            context=_CONTEXT,
            at=_AT,
        )
        self.assertGreater(len(candidate.results), len(legacy.results))
        self.assertEqual(candidate.candidate_pool, 20)
        self.assertEqual(candidate.max_chunks_per_document, 20)
        documents = [result.chunk.metadata.document_id for result in legacy.results]
        self.assertEqual(len(documents), len(set(documents)))
        self.assertLessEqual(len(candidate.results), 20)
        for result in candidate.results:
            self.assertEqual(
                self.service.resolve(result, context=_CONTEXT, at=_AT), result.chunk
            )
        for kwargs in (
            {"candidate_pool": 4},
            {"candidate_pool": 101},
            {"candidate_pool": True},
            {"max_chunks_per_document": 0},
            {"max_chunks_per_document": 21},
            {"max_chunks_per_document": True},
        ):
            with self.assertRaises(SearchInputError):
                SearchRequest("q", **kwargs)

    def test_local_encoder_rejects_actual_token_budget_before_encoding(self) -> None:
        encoder = LocalSentenceEncoder.__new__(LocalSentenceEncoder)
        encoder.spec = EncoderSpec("fixture", "v1", 3, 256, "test_fixture", ())
        model = Mock()
        model.tokenizer.return_value = {"input_ids": list(range(257))}
        encoder._model = model
        with self.assertRaises(SearchInputError):
            encoder.encode(["untrusted passage"])
        model.tokenizer.assert_called_once_with(
            "untrusted passage", add_special_tokens=True, truncation=False
        )
        model.encode.assert_not_called()

    def test_failed_pointer_publication_preserves_prior_index(self) -> None:
        different = FixtureEncoder()
        different.spec = replace(different.spec, revision="fixture.v2")
        with patch(
            "trace_app.retrieval_index.os.replace", side_effect=OSError("fixture")
        ):
            with self.assertRaises(OSError):
                build_index(
                    self.root / "index",
                    self.corpus,
                    self.chunks,
                    at=_AT,
                    encoder=different,
                )
        self.assertEqual(
            load_index(self.root / "index", encoder=self.encoder), self.index
        )
        self.assertFalse(
            any(path.name.startswith(".") for path in (self.root / "index").iterdir())
        )

    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory(prefix="trace-retrieval-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = SQLiteCorpusStore(self.root / "corpus.sqlite3")
        self.addCleanup(self.store.__exit__)
        self.corpus, _ = self.store.ingest(
            CuratedFileSource(_ROOT / "corpus/development"),
            at=_AT,
            retain_until=_RETAIN,
        )
        self.chunks = self.store.read_chunks(context=_CONTEXT, at=_AT)
        self.encoder = FixtureEncoder()
        self.index = build_index(
            self.root / "index", self.corpus, self.chunks, at=_AT, encoder=self.encoder
        )
        self.service = SearchService(self.store, self.index, self.encoder)
        self.encoder.calls.clear()

    def test_known_lexical_query_bound_provenance_and_saved_citation(self) -> None:
        response = self.service.search(
            SearchRequest("TLS certificate expiry error", 3, "lexical"),
            context=_CONTEXT,
            at=_AT,
        )
        self.assertEqual(response.status, "ok")
        self.assertLessEqual(len(response.results), 3)
        self.assertEqual(
            response.results[0].chunk.metadata.document_id,
            "trace-dev-history-certificate",
        )
        self.assertEqual(
            [r.rank for r in response.results],
            list(range(1, len(response.results) + 1)),
        )
        self.assertEqual(
            len({r.chunk.metadata.document_id for r in response.results}),
            len(response.results),
        )
        for result in response.results:
            self.assertEqual(
                self.service.resolve(result, context=_CONTEXT, at=_AT), result.chunk
            )
            self.assertEqual(result.chunk.content_role, "untrusted_source_data")
            citation = result.to_dict()["citation"]
            self.assertTrue(citation)
        self.assertEqual(self.encoder.calls, [])

    def test_semantic_and_rrf_are_exact_bounded_deterministic_fixture_checks(
        self,
    ) -> None:
        for mode in ("semantic", "hybrid"):
            request = SearchRequest("timeout", 2, mode)
            first = self.service.search(request, context=_CONTEXT, at=_AT)
            second = self.service.search(request, context=_CONTEXT, at=_AT)
            self.assertEqual(first, second)
            self.assertEqual(first.status, "ok")
            self.assertEqual(len(first.results), 2)
            self.assertTrue(
                all(math.isfinite(result.score) for result in first.results)
            )
        self.assertIn("not probability", str(first.to_dict()["score_semantics"]))

    def test_request_and_vector_bounds_reject_invalid_values(self) -> None:
        for changes in (
            {"query": " "},
            {"query": "x" * 4_001},
            {"query": "x\x00"},
            {"top_k": 0},
            {"top_k": 21},
            {"top_k": True},
            {"mode": "magic"},
            {"document_type": "email"},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                SearchRequest(**cast(dict[str, Any], {"query": "q", **changes}))
        for vectors in (
            [],
            [[1, 0]],
            [[0, 0, 0]],
            [[True, 0, 0]],
            [[float("nan"), 0, 0]],
            [[float("inf"), 0, 0]],
        ):
            with self.assertRaises(EncoderFailure):
                validate_vectors(vectors, 1, 3)
        self.assertEqual(
            technical_tokens("SQLSTATE 08006 HTTP 503 /v1/orders java.net.Timeout not"),
            [
                "sqlstate",
                "08006",
                "http",
                "503",
                "/v1/orders",
                "java.net.timeout",
                "not",
            ],
        )
        self.assertEqual(lexical_scores(["..."], "q"), (0.0,))

    def test_empty_index_no_overlap_and_missing_semantic_provider_are_explicit(
        self,
    ) -> None:
        empty = build_index(
            self.root / "empty", self.corpus, (), at=_AT, encoder=self.encoder
        )
        self.encoder.calls.clear()
        service = SearchService(self.store, empty, self.encoder)
        context = replace(_CONTEXT, allowed_services=("notification",))
        result = service.search(
            SearchRequest("q", mode="semantic"), context=context, at=_AT
        )
        self.assertEqual(
            (result.status, result.reason),
            ("no_results", "no_authorized_matching_chunks"),
        )
        self.assertFalse(self.encoder.calls)
        no_overlap = self.service.search(
            SearchRequest("XYZ_UNKNOWN_UNIQUE", mode="lexical"),
            context=_CONTEXT,
            at=_AT,
        )
        self.assertEqual(no_overlap.reason, "no_lexical_overlap")
        lexical = build_index(self.root / "lexical", self.corpus, self.chunks, at=_AT)
        service = SearchService(self.store, lexical)
        self.assertEqual(
            service.search(
                SearchRequest("timeout", mode="semantic"), context=_CONTEXT, at=_AT
            ).status,
            "provider_failure",
        )
        self.assertEqual(
            service.search(
                SearchRequest("timeout", mode="lexical"), context=_CONTEXT, at=_AT
            ).status,
            "ok",
        )

    def test_permissions_precede_scoring_and_encoder_filters_cannot_grant_access(
        self,
    ) -> None:
        with patch.object(
            self.store, "read_chunks", wraps=self.store.read_chunks
        ) as read:
            with self.assertRaises(CorpusAccessError):
                self.service.search(
                    SearchRequest("q", service="notification"), context=_CONTEXT, at=_AT
                )
            read.assert_not_called()
        denied = self.service.search(
            SearchRequest("timeout"),
            context=replace(_CONTEXT, access_scope="other"),
            at=_AT,
        )
        self.assertEqual(
            (denied.status, denied.eligible_chunks, denied.candidate_count),
            ("no_results", 0, 0),
        )
        self.assertFalse(self.encoder.calls)
        with patch("trace_app.retrieval.lexical_scores", wraps=lexical_scores) as score:
            result = self.service.search(
                SearchRequest("request", mode="lexical", service="order"),
                context=_CONTEXT,
                at=_AT,
            )
            expected = [
                chunk.normalized_text
                for chunk in self.chunks
                if chunk.metadata.service == "order"
            ]
            self.assertEqual(score.call_args.args[0], expected)
            self.assertTrue(
                all(r.chunk.metadata.service == "order" for r in result.results)
            )

    def test_revocation_changes_candidates_idf_and_resolving_prior_results(
        self,
    ) -> None:
        saved = self.service.search(
            SearchRequest("certificate TLS expiry", mode="lexical"),
            context=_CONTEXT,
            at=_AT,
        ).results[0]
        self.store.withdraw(saved.chunk.metadata.document_id, reason="revoked", at=_AT)
        with self.assertRaises(CorpusAccessError):
            self.service.resolve(saved, context=_CONTEXT, at=_AT)
        with patch("trace_app.retrieval.lexical_scores", wraps=lexical_scores) as score:
            response = self.service.search(
                SearchRequest("certificate TLS expiry", mode="lexical"),
                context=_CONTEXT,
                at=_AT,
            )
            self.assertNotIn(saved.chunk.normalized_text, score.call_args.args[0])
            self.assertTrue(
                all(
                    r.chunk.metadata.document_id != saved.chunk.metadata.document_id
                    for r in response.results
                )
            )
        self.assertEqual(response.status, "no_results")

    def test_changed_source_and_withdrawal_during_candidate_read_return_no_content(
        self,
    ) -> None:
        original = self.store.resolve
        calls = 0
        withdrawn = None

        def resolve(generation, identity, **kwargs):
            nonlocal calls, withdrawn
            calls += 1
            current = original(generation, identity, **kwargs)
            if calls == 1:
                withdrawn = current.chunk_id
            elif calls == 2:
                first = next(
                    chunk for chunk in self.chunks if chunk.chunk_id == withdrawn
                )
                self.store.withdraw(
                    first.metadata.document_id, reason="revoked", at=_AT
                )
            return current

        with patch.object(self.store, "resolve", side_effect=resolve):
            response = self.service.search(
                SearchRequest("request", mode="lexical"), context=_CONTEXT, at=_AT
            )
        self.assertEqual(response.status, "source_unavailable")
        self.assertEqual(response.results, ())
        changed = replace(self.chunks[0], text="different text")
        with patch.object(self.store, "read_chunks", return_value=(changed,)):
            self.assertEqual(
                self.service.search(
                    SearchRequest("q", mode="semantic"), context=_CONTEXT, at=_AT
                ).status,
                "index_incompatible",
            )

    def test_provider_errors_never_turn_into_lexical_fallback(self) -> None:
        with patch.object(
            self.encoder, "encode", side_effect=RuntimeError("secret provider text")
        ):
            response = self.service.search(
                SearchRequest("timeout", mode="hybrid"), context=_CONTEXT, at=_AT
            )
            self.assertEqual(response.status, "provider_failure")
            self.assertEqual(response.results, ())
            self.assertNotIn("secret", canonical(response.to_dict()))
            with self.assertRaises(EncoderFailure):
                build_index(
                    self.root / "failed",
                    self.corpus,
                    self.chunks,
                    at=_AT,
                    encoder=self.encoder,
                )
            self.assertFalse((self.root / "failed").exists())
        with patch.object(self.encoder, "encode", return_value=((0.0, 0.0, 0.0),)):
            self.assertEqual(
                self.service.search(
                    SearchRequest("q", mode="semantic"), context=_CONTEXT, at=_AT
                ).status,
                "provider_failure",
            )
        with patch.object(
            self.encoder, "encode", side_effect=SearchInputError("too long")
        ):
            with self.assertRaises(SearchInputError):
                self.service.search(
                    SearchRequest("q", mode="semantic"), context=_CONTEXT, at=_AT
                )
        with patch(
            "builtins.__import__", side_effect=ImportError("fixture missing dependency")
        ):
            with self.assertRaises(EncoderFailure):
                LocalSentenceEncoder()

    def test_expiry_storage_failures_and_no_fallback_to_old_source(self) -> None:
        with patch.object(
            self.store, "read_chunks", side_effect=CorpusDependencyError("fixture")
        ):
            self.assertEqual(
                self.service.search(
                    SearchRequest("q", mode="semantic"), context=_CONTEXT, at=_AT
                ).status,
                "storage_failure",
            )
        with patch.object(
            self.store, "read_chunks", side_effect=CorpusAccessError("fixture")
        ):
            self.assertEqual(
                self.service.search(
                    SearchRequest("q", mode="semantic"), context=_CONTEXT, at=_AT
                ).status,
                "source_unavailable",
            )
        self.assertEqual(
            self.service.search(
                SearchRequest("q", mode="semantic"),
                context=_CONTEXT,
                at=_AT + timedelta(days=2),
            ).status,
            "source_unavailable",
        )
        stale = self.service.search(
            SearchRequest("q", mode="semantic"),
            context=replace(_CONTEXT, valid_at="2025-01-01T00:00:00Z"),
            at=_AT,
        )
        self.assertEqual(stale.status, "no_results")

    def test_index_reopen_rebuild_and_incompatible_encoder_versions(self) -> None:
        loaded = load_index(self.root / "index", encoder=self.encoder)
        self.assertEqual(loaded, self.index)
        rebuilt = build_index(
            self.root / "index",
            self.corpus,
            tuple(reversed(self.chunks)),
            at=_AT + timedelta(seconds=1),
            encoder=self.encoder,
        )
        self.assertEqual(rebuilt, self.index)
        different = FixtureEncoder()
        different.spec = replace(different.spec, revision="fixture.v2")
        with self.assertRaises(IndexCompatibilityError):
            load_index(self.root / "index", encoder=different)
        response = SearchService(self.store, loaded, different).search(
            SearchRequest("q", mode="semantic"), context=_CONTEXT, at=_AT
        )
        self.assertEqual(response.status, "index_incompatible")
        new = build_index(
            self.root / "index", self.corpus, self.chunks, at=_AT, encoder=different
        )
        self.assertNotEqual(new.index_id, self.index.index_id)
        self.assertEqual(load_index(self.root / "index", encoder=different), new)

    def test_tampered_artifacts_versions_and_pointer_paths_are_rejected(self) -> None:
        generation = self.root / "index" / self.index.index_id
        manifest_path = generation / "manifest.json"
        manifest = json.loads(manifest_path.read_text())
        manifest["versions"]["retriever"] = "future"
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaises(IndexCompatibilityError):
            load_index(self.root / "index")
        # Rebuild never silently trusts or overwrites an incompatible generation.
        with self.assertRaises(IndexCompatibilityError):
            build_index(
                self.root / "index",
                self.corpus,
                self.chunks,
                at=_AT,
                encoder=self.encoder,
            )
        self.assertFalse(
            any(
                path.name.startswith(".staging-")
                for path in (self.root / "index").iterdir()
            )
        )
        (self.root / "index/CURRENT").write_text("../../etc/passwd")
        with self.assertRaises(IndexCompatibilityError):
            load_index(self.root / "index")

    def test_artifact_permissions_corrupt_vectors_and_forged_citations(self) -> None:
        generation = self.root / "index" / self.index.index_id
        self.assertEqual((generation / "records.json").stat().st_mode & 0o777, 0o600)
        self.assertEqual(generation.stat().st_mode & 0o777, 0o700)
        result = self.service.search(
            SearchRequest("TLS expiry", mode="lexical"), context=_CONTEXT, at=_AT
        ).results[0]
        with self.assertRaises(CorpusAccessError):
            self.service.resolve(
                replace(result, chunk=replace(result.chunk, text="forged")),
                context=_CONTEXT,
                at=_AT,
            )
        records = json.loads((generation / "records.json").read_text())
        records["vectors"][0] = [0, 0, 0]
        (generation / "records.json").write_text(json.dumps(records))
        with self.assertRaises(IndexCompatibilityError):
            load_index(self.root / "index")


if __name__ == "__main__":
    unittest.main()
