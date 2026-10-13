"""Offline developer search demo with fixed corpus grants and explicit retrieval mode."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from trace_app.adapters.embeddings.sentence_transformers import LocalSentenceEncoder
from trace_app.adapters.retrieval.local_index import build_index, load_index
from trace_app.adapters.sources.curated_files import CuratedFileSource
from trace_app.adapters.storage.sqlite.corpus import SQLiteCorpusStore
from trace_app.bootstrap import create_search_service as SearchService
from trace_app.knowledge.models import (
    CorpusAccessError,
    CorpusConflictError,
    CorpusDependencyError,
    CorpusReadContext,
)
from trace_app.knowledge.ports import (
    EncoderFailure,
    IndexCompatibilityError,
    SearchRequest,
)
from trace_app.runtime.logging import configure_logging

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--query",
        default="HTTP 504 Payment timeout: compare the configured deadline and work duration",
    )
    parser.add_argument(
        "--mode", choices=("lexical", "semantic", "hybrid"), default="lexical"
    )
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--service")
    args = parser.parse_args(argv)
    configure_logging(level="INFO")
    try:
        request = SearchRequest(args.query, args.top_k, args.mode, args.service)
        if (
            request.service is not None
            and request.service not in _CONTEXT.allowed_services
        ):
            raise CorpusAccessError("Requested service is outside demo grants.")
        encoder = None if request.mode == "lexical" else LocalSentenceEncoder()
        with tempfile.TemporaryDirectory(prefix="trace-search-") as directory:
            root = Path(directory)
            with SQLiteCorpusStore(root / "corpus.sqlite3") as store:
                corpus, _ = store.ingest(
                    CuratedFileSource(_ROOT / "corpus/development"),
                    at=_AT,
                    retain_until=_RETAIN,
                )
                chunks = store.read_chunks(context=_CONTEXT, at=_AT)
                build_index(root / "index", corpus, chunks, at=_AT, encoder=encoder)
                index = load_index(root / "index", encoder=encoder)
                service = SearchService(store, index, encoder)
                response = service.search(request, context=_CONTEXT, at=_AT)
                resolved = [
                    service.resolve(result, context=_CONTEXT, at=_AT).chunk_id
                    for result in response.results
                ]
                output = {
                    "search": response.to_dict(),
                    "embedding": index.embedding.to_dict() if index.embedding else None,
                    "resolved_chunk_ids": resolved,
                }
    except (
        ValueError,
        OSError,
        CorpusAccessError,
        CorpusConflictError,
        CorpusDependencyError,
        EncoderFailure,
        IndexCompatibilityError,
    ) as error:
        print(
            json.dumps(
                {
                    "status": "provider_failure"
                    if isinstance(error, EncoderFailure)
                    else "error",
                    "error": str(error),
                }
            ),
            file=sys.stderr,
        )
        return 2
    print(json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0 if response.status in ("ok", "no_results") else 2


if __name__ == "__main__":
    raise SystemExit(main())
