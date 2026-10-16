"""Scripted S4 incident package; publisher setup is separate from reader calls."""

from __future__ import annotations

import argparse
import json
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable, Iterator

from trace_app.adapters.retrieval.local_index import build_index
from trace_app.adapters.sources.curated_files import CuratedFileSource
from trace_app.adapters.storage.sqlite.corpus import SQLiteCorpusStore
from trace_app.adapters.storage.sqlite.investigations import SQLiteInvestigationStore
from trace_app.bootstrap import create_tool_session
from trace_app.demo.scenarios import ScenarioConfig, ScenarioSession
from trace_app.evidence.queries import EvidenceQuery, TrustedQueryContext
from trace_app.investigation.bundle import build_evidence_package
from trace_app.investigation.models import EvidenceSnapshot, InvestigationRequest
from trace_app.investigation.tools import ToolPolicy, ToolScope, ToolSession
from trace_app.knowledge.models import CorpusReadContext
from trace_app.runtime.logging import configure_logging

ROOT = Path(__file__).resolve().parents[1]
AT = datetime(2026, 10, 12, 12, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class IntegrationFixture:
    root: Path
    scope: ToolScope
    query: EvidenceQuery

    def session(
        self,
        *,
        scope: ToolScope | None = None,
        policy: ToolPolicy | None = None,
        at: datetime = AT,
    ) -> ToolSession:
        return create_tool_session(
            evidence_db=self.root / "evidence.sqlite3",
            corpus_db=self.root / "corpus.sqlite3",
            index_root=self.root / "index",
            scope=scope or self.scope,
            policy=policy or ToolPolicy(max_attempts=64, call_timeout_ms=10_000),
            read_clock=lambda: at,
        )


@contextmanager
def integration_fixture(
    case_id: str = "c01",
    *,
    limit: int = 100,
    transform: Callable[[EvidenceSnapshot], EvidenceSnapshot] | None = None,
) -> Iterator[IntegrationFixture]:
    """Explicit synthetic setup; neither evaluator labels nor expected calls loaded."""
    with tempfile.TemporaryDirectory(prefix="trace-s4-integration-") as directory:
        root = Path(directory)
        replay = ScenarioSession(ScenarioConfig(case_id, 17)).replay(collected_at=AT)
        snapshot = transform(replay.snapshot) if transform else replay.snapshot
        with SQLiteInvestigationStore(root / "evidence.sqlite3") as store:
            investigation = store.submit(
                InvestigationRequest(
                    "s4-integration",
                    "order",
                    "test",
                    "local:synthetic",
                    snapshot.window_start,
                    snapshot.window_end,
                ),
                at=AT,
            )
            store.ingest_snapshot(
                investigation.investigation_id,
                snapshot,
                access_scope="local:synthetic",
                at=AT,
            )
        context = CorpusReadContext(
            "local:knowledge-development",
            "test",
            ("order", "payment"),
            "development_reference",
            "2026-01-01T00:00:17Z",
        )
        with SQLiteCorpusStore(root / "corpus.sqlite3") as corpus:
            generation, _ = corpus.ingest(
                CuratedFileSource(ROOT / "corpus/development"),
                at=AT,
                retain_until="2026-10-14T12:00:00Z",
            )
            build_index(
                root / "index",
                generation,
                corpus.read_chunks(context=context, at=AT),
                at=AT,
            )
        scope = ToolScope(
            investigation.investigation_id,
            "s4-integration-17",
            TrustedQueryContext(
                "local:synthetic",
                "test",
                ("order", "payment", "customer", "notification"),
            ),
            context,
        )
        yield IntegrationFixture(
            root,
            scope,
            EvidenceQuery(snapshot.window_start, snapshot.window_end, limit),
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--case", choices=("c01", "c02", "c03", "c04"), default="c01")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    configure_logging()
    with integration_fixture(args.case, limit=args.limit) as fixture:
        result = build_evidence_package(
            fixture.session(),
            investigation_id=fixture.scope.investigation_id,
            query=fixture.query,
            knowledge_query="Payment timeout evidence",
            knowledge_service="payment",
        )
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(
            result.to_dict(), stream, indent=2, ensure_ascii=False, allow_nan=False
        )
        stream.write("\n")
    print(
        json.dumps(
            {
                "status": result.status,
                "data_sha256": result.data_sha256,
                "failure": result.failure,
                "temporary_state_removed": True,
            }
        )
    )
    return int(result.status == "failed")


if __name__ == "__main__":
    raise SystemExit(main())
