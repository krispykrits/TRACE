"""Offline corpus demo: ingest twice, reopen, and resolve every source-linked chunk."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from trace_app.adapters.sources.curated_files import CuratedFileSource
from trace_app.adapters.storage.sqlite.corpus import (
    CorpusReadContext,
    SQLiteCorpusStore,
)
from trace_app.knowledge.models import (
    CorpusAccessError,
    CorpusConflictError,
    CorpusDependencyError,
    CorpusInputError,
)
from trace_app.knowledge.sources import CorpusBatch
from trace_app.runtime.logging import configure_logging

_ROOT = Path(__file__).resolve().parents[1]
_AT = datetime(2026, 10, 12, 12, tzinfo=UTC)
_RETAIN_UNTIL = "2026-10-14T12:00:00Z"
_CONTEXT = CorpusReadContext(
    "local:knowledge-development",
    "test",
    ("order", "payment"),
    "development_reference",
    "2026-10-12T12:00:00Z",
)


@dataclass(frozen=True)
class _CapturedSource:
    batch: CorpusBatch

    def load(self) -> CorpusBatch:
        return self.batch


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=_ROOT / "corpus/development")
    args = parser.parse_args(argv)
    configure_logging(level="INFO")
    try:
        source = CuratedFileSource(args.corpus)
        # Fixed synthetic grants/clock: this command is not a real-source publisher.
        batch = source.load()
        if any(
            doc.metadata.access_classification != "synthetic_public"
            or doc.metadata.environment != "test"
            or doc.metadata.access_scope != _CONTEXT.access_scope
            or doc.metadata.service not in _CONTEXT.allowed_services
            or doc.metadata.evaluation_role != _CONTEXT.evaluation_role
            for doc in batch.documents
        ):
            raise CorpusInputError(
                "Demo accepts only the scoped synthetic development corpus."
            )
        captured = _CapturedSource(batch)
        with tempfile.TemporaryDirectory(prefix="trace-corpus-") as directory:
            path = Path(directory) / "corpus.sqlite3"
            with SQLiteCorpusStore(path) as store:
                first, first_created = store.ingest(
                    captured, at=_AT, retain_until=_RETAIN_UNTIL
                )
            with SQLiteCorpusStore(path) as store:
                second, second_created = store.ingest(
                    captured, at=_AT, retain_until=_RETAIN_UNTIL
                )
                chunks = store.read_chunks(context=_CONTEXT, at=_AT)
                resolved = tuple(
                    store.resolve(
                        second.generation_id, chunk.chunk_id, context=_CONTEXT, at=_AT
                    )
                    for chunk in chunks
                )
            output = {
                "generation": second.to_dict(),
                "first_created": first_created,
                "second_created": second_created,
                "same_generation": first == second,
                "chunks": [chunk.to_dict() for chunk in resolved],
            }
    except (
        ValueError,
        OSError,
        CorpusAccessError,
        CorpusConflictError,
        CorpusDependencyError,
    ) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2
    print(json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
