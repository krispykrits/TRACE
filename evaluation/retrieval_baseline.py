"""Evaluator-only offline comparison of adapted Volume 4 retrieval baselines.

This development report measures document ranking, not diagnosis or answerability.
Judgments never enter the corpus, encoder or search request.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

from trace_app.corpus_sources import CuratedFileSource
from trace_app.corpus_store import SQLiteCorpusStore
from trace_app.knowledge import CorpusReadContext, canonical, digest, parse_json
from trace_app.retrieval import SearchService
from trace_app.retrieval_backends import LocalSentenceEncoder
from trace_app.retrieval_contracts import EncoderFailure, SearchMode, SearchRequest
from trace_app.retrieval_index import build_index, implementation_versions, load_index

_ROOT = Path(__file__).resolve().parents[1]
_SUITE = _ROOT / "evaluation/retrieval/queries_v1.json"
_AT = datetime(2026, 10, 12, 12, tzinfo=UTC)
_CONTEXT = CorpusReadContext(
    "local:knowledge-development",
    "test",
    ("order", "payment"),
    "development_reference",
    "2026-10-12T12:00:00Z",
)
_MODES: tuple[SearchMode, ...] = ("lexical", "semantic", "hybrid")


def metrics(suite: dict[str, Any], attempts: list[dict[str, Any]]) -> dict[str, Any]:
    """All scheduled queries count; failed answerable searches receive zero credit."""
    queries = {query["id"]: query for query in suite["queries"]}
    expected = {(mode, identity) for mode in _MODES for identity in queries}
    pairs = [(row["mode"], row["query_id"]) for row in attempts]
    if len(pairs) != len(set(pairs)) or set(pairs) != expected:
        raise ValueError("Report requires exactly one attempt per mode and query.")
    output: dict[str, Any] = {}
    for mode in _MODES:
        recalls, reciprocal, absent, durations, failures = [], [], [], [], 0
        for row in attempts:
            if row["mode"] != mode:
                continue
            ranked = row["document_ids"]
            if len(ranked) > suite["top_k"] or len(set(ranked)) != len(ranked):
                raise ValueError("Report ranks violate top-K/document diversity.")
            relevant = set(queries[row["query_id"]]["relevant_documents"])
            failed = row["status"] not in ("ok", "no_results")
            failures += int(failed)
            ranks = [] if failed else ranked
            durations.append(row["search_ms"])
            if relevant:
                recalls.append(len(set(ranks) & relevant) / len(relevant))
                reciprocal.append(
                    next(
                        (
                            1 / rank
                            for rank, document in enumerate(ranks, 1)
                            if document in relevant
                        ),
                        0.0,
                    )
                )
            else:
                absent.append(len(ranks))
        output[mode] = {
            "attempts": len(queries),
            "failures": failures,
            "answerable_queries": len(recalls),
            "document_recall_at_3": sum(recalls) / len(recalls),
            "mrr_at_3": sum(reciprocal) / len(reciprocal),
            "absent_knowledge_queries": len(absent),
            "absent_queries_returning_candidates": sum(count > 0 for count in absent),
            "mean_search_ms": sum(durations) / len(durations),
        }
    return output


def run() -> dict[str, Any]:
    suite = json.loads(_SUITE.read_text(encoding="utf-8"))
    if suite["cohort"] != "development" or suite["top_k"] != 3:
        raise ValueError("Only the fixed development comparison is supported.")
    started = perf_counter()
    encoder = LocalSentenceEncoder()
    model_load_ms = (perf_counter() - started) * 1000
    attempts = []
    with tempfile.TemporaryDirectory(prefix="trace-retrieval-baseline-") as directory:
        root = Path(directory)
        with SQLiteCorpusStore(root / "corpus.sqlite3") as store:
            corpus, _ = store.ingest(
                CuratedFileSource(_ROOT / "corpus/development"),
                at=_AT,
                retain_until="2026-10-14T12:00:00Z",
            )
            chunks = store.read_chunks(context=_CONTEXT, at=_AT)
            documents = {chunk.metadata.document_id for chunk in chunks}
            if any(
                set(query["relevant_documents"]) - documents
                for query in suite["queries"]
            ):
                raise ValueError("Judgment refers to a document outside the corpus.")
            started = perf_counter()
            build_index(root / "index", corpus, chunks, at=_AT, encoder=encoder)
            index = load_index(root / "index", encoder=encoder)
            build_ms = (perf_counter() - started) * 1000
            service = SearchService(store, index, encoder)
            for mode in _MODES:
                for query in suite["queries"]:
                    started = perf_counter()
                    response = service.search(
                        SearchRequest(query["query"], suite["top_k"], mode),
                        context=_CONTEXT,
                        at=_AT,
                    )
                    duration = (perf_counter() - started) * 1000
                    for result in response.results:
                        service.resolve(result, context=_CONTEXT, at=_AT)
                    attempts.append(
                        {
                            "mode": mode,
                            "query_id": query["id"],
                            "status": response.status,
                            "reason": response.reason,
                            "document_ids": [
                                r.chunk.metadata.document_id for r in response.results
                            ],
                            "chunk_ids": [r.chunk.chunk_id for r in response.results],
                            "scores": [r.score for r in response.results],
                            "search_ms": duration,
                        }
                    )
    sources = [
        "uv.lock",
        "evaluation/retrieval_baseline.py",
        "src/trace_app/retrieval.py",
        "src/trace_app/retrieval_contracts.py",
        "src/trace_app/retrieval_backends.py",
        "src/trace_app/retrieval_index.py",
        "src/trace_app/corpus_store.py",
        "src/trace_app/corpus_sources.py",
        "src/trace_app/knowledge.py",
        "corpus/development/manifest.json",
    ]
    return {
        "schema_version": "1",
        "suite": suite,
        "suite_sha256": digest(canonical(suite)),
        "attempts": attempts,
        "attempts_sha256": digest(canonical(attempts)),
        "metrics": metrics(suite, attempts),
        "configuration": {
            "clock": "2026-10-12T12:00:00Z",
            "corpus_generation_id": corpus.generation_id,
            "corpus_sha256": corpus.corpus_sha256,
            "index_generation_id": index.index_id,
            "document_count": corpus.document_count,
            "chunk_count": corpus.chunk_count,
            "embedding": encoder.spec.to_dict(),
            "versions": implementation_versions(),
            "python": platform.python_version(),
            "platform": "Linux CPU",
            "threads": 4,
            "batch_size": 32,
            "paid_calls": 0,
            "model_load_ms": model_load_ms,
            "index_build_ms": build_ms,
            "source_sha256": {
                path: hashlib.sha256((_ROOT / path).read_bytes()).hexdigest()
                for path in sources
            },
        },
        "limitations": [
            "Ten hand-authored synthetic development queries; not held-out quality or operational acceptance.",
            "Document judgments do not establish passage-level support, diagnosis or answerability.",
            "Dense and hybrid always rank eligible passages; absent-knowledge candidates are not answers.",
            "Single CPU run includes warm-up/order effects; latency is descriptive, not an SLA.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        help="New report file; existing files are never overwritten.",
    )
    parser.add_argument(
        "--rescore", type=Path, help="Recompute saved metrics without loading a model."
    )
    args = parser.parse_args(argv)
    try:
        if args.rescore:
            report = parse_json(args.rescore.read_text(encoding="utf-8"))
            if not isinstance(report, dict):
                raise ValueError("Report must be an object.")
            suite, attempts = report["suite"], report["attempts"]
            if report["suite_sha256"] != digest(canonical(suite)) or report[
                "attempts_sha256"
            ] != digest(canonical(attempts)):
                raise ValueError("Saved inputs changed; report hash mismatch.")
            report["metrics"] = metrics(suite, attempts)
        else:
            report = run()
        if args.output:
            with args.output.open("x", encoding="utf-8") as stream:
                stream.write(json.dumps(report, indent=2, sort_keys=True) + "\n")
        print(json.dumps(report["metrics"], sort_keys=True))
        return 2 if any(row["failures"] for row in report["metrics"].values()) else 0
    except (EncoderFailure, ValueError, OSError, KeyError, TypeError) as error:
        print(json.dumps({"status": "error", "error": str(error)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
