"""Read-only developer search plus bounded, source-resolvable knowledge context."""

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
from trace_app.knowledge.context import ContextAssembler, ContextBudget
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
        "--query", default="HTTP 504 /v1/orders configuration and work duration"
    )
    parser.add_argument(
        "--mode", choices=("lexical", "semantic", "hybrid"), default="lexical"
    )
    parser.add_argument("--candidate-k", type=int, default=20)
    parser.add_argument("--max-passages", type=int, default=5)
    parser.add_argument("--max-bytes", type=int, default=8_192)
    parser.add_argument("--service")
    args = parser.parse_args(argv)
    configure_logging()
    try:
        request = SearchRequest(
            args.query,
            args.candidate_k,
            args.mode,
            args.service,
            candidate_pool=args.candidate_k,
            max_chunks_per_document=args.candidate_k,
        )
        budget = ContextBudget(args.max_bytes, args.max_passages)
        if (
            request.service is not None
            and request.service not in _CONTEXT.allowed_services
        ):
            raise CorpusAccessError("Requested service is outside demo grants.")
        encoder = None if request.mode == "lexical" else LocalSentenceEncoder()
        with tempfile.TemporaryDirectory(prefix="trace-context-demo-") as directory:
            root = Path(directory)
            with SQLiteCorpusStore(root / "corpus.sqlite3") as store:
                corpus, _ = store.ingest(
                    CuratedFileSource(_ROOT / "corpus/development"),
                    at=_AT,
                    retain_until="2026-10-14T12:00:00Z",
                )
                chunks = store.read_chunks(context=_CONTEXT, at=_AT)
                build_index(root / "index", corpus, chunks, at=_AT, encoder=encoder)
                service = SearchService(
                    store, load_index(root / "index", encoder=encoder), encoder
                )
                response = service.search(request, context=_CONTEXT, at=_AT)
                assembled = ContextAssembler(store).assemble(
                    response, context=_CONTEXT, at=_AT, budget=budget
                )
                data = json.loads(assembled.serialized_data)
                resolved = [
                    store.resolve(
                        citation["corpus_generation_id"],
                        citation["chunk_id"],
                        context=_CONTEXT,
                        at=_AT,
                    ).chunk_id
                    for citation in data["citations"].values()
                ]
                output = {
                    "context": assembled.to_dict(),
                    "resolved_chunk_ids": resolved,
                }
    except (
        ValueError,
        OSError,
        EncoderFailure,
        IndexCompatibilityError,
        CorpusAccessError,
        CorpusConflictError,
        CorpusDependencyError,
    ) as error:
        print(json.dumps({"status": "error", "error": str(error)}), file=sys.stderr)
        return 2
    print(json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0 if assembled.status in ("ok", "empty") else 2


if __name__ == "__main__":
    raise SystemExit(main())
