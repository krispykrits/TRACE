"""Exercise the fixed read-only catalog over temporary, explicitly synthetic state."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from dataclasses import asdict, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trace_app.adapters.retrieval.local_index import build_index
from trace_app.adapters.sources.curated_files import CuratedFileSource
from trace_app.adapters.storage.sqlite.corpus import SQLiteCorpusStore
from trace_app.adapters.storage.sqlite.investigations import SQLiteInvestigationStore
from trace_app.bootstrap import create_tool_session
from trace_app.demo.replay import ReplayConfig, ReplaySession
from trace_app.evidence.models import SourceAvailability
from trace_app.evidence.queries import TrustedQueryContext
from trace_app.investigation.models import (
    DeploymentPayload,
    EvidenceEntry,
    EvidenceSnapshot,
    InvestigationRequest,
    LogPayload,
    MetricPayload,
)
from trace_app.investigation.tools import ToolScope
from trace_app.knowledge.models import CorpusReadContext
from trace_app.runtime.logging import configure_logging

_ROOT = Path(__file__).resolve().parents[1]
_AT = datetime(2026, 10, 12, 12, tzinfo=UTC)


def demonstration() -> dict[str, Any]:
    """Publish fixtures through separate handles, then compose only readers."""
    with tempfile.TemporaryDirectory(prefix="trace-tools-demo-") as directory:
        root = Path(directory)
        replay = ReplaySession(ReplayConfig(17, "failure")).replay().evidence
        query = {"window_start": replay.window_start, "window_end": replay.window_end}
        # These payloads are demonstration fixtures, not observations of real telemetry.
        payloads = (
            LogPayload("Synthetic Order failure."),
            MetricPayload("fixture_duration", 12.5, "ms"),
            DeploymentPayload("fixture-v1", "started"),
        )
        entries = tuple(
            EvidenceEntry(
                kind,
                replace(
                    replay.records[ordinal],
                    evidence_id=f"tool-{kind}",
                    source_record_id=f"synthetic:tool-{kind}",
                    source_revision="tools-fixture.v1",
                    event=f"{kind}.observed",
                    integrity_sha256=hashlib.sha256(
                        json.dumps(asdict(payload), sort_keys=True).encode()
                    ).hexdigest(),
                ),
                payload,
            )
            for ordinal, (kind, payload) in enumerate(
                zip(("log", "metric", "deployment"), payloads, strict=True)
            )
        )
        sources = (
            SourceAvailability("synthetic_tool_fixture", "available"),
            SourceAvailability(
                "sanitized_export",
                "unavailable",
                "No authorized operational source supplied.",
            ),
        )
        with SQLiteInvestigationStore(root / "evidence.sqlite3") as store:
            investigation = store.submit(
                InvestigationRequest(
                    "tool-demo",
                    "order",
                    "test",
                    "local:synthetic",
                    replay.window_start,
                    replay.window_end,
                ),
                at=_AT,
            )
            store.ingest_snapshot(
                investigation.investigation_id,
                EvidenceSnapshot(
                    entries, replay.window_start, replay.window_end, sources
                ),
                access_scope="local:synthetic",
                at=_AT,
            )
        knowledge = CorpusReadContext(
            "local:knowledge-development",
            "test",
            ("order", "payment"),
            "development_reference",
            "2026-10-12T12:00:00Z",
        )
        with SQLiteCorpusStore(root / "corpus.sqlite3") as corpus:
            generation, _ = corpus.ingest(
                CuratedFileSource(_ROOT / "corpus/development"),
                at=_AT,
                retain_until="2026-10-14T12:00:00Z",
            )
            build_index(
                root / "index",
                generation,
                corpus.read_chunks(context=knowledge, at=_AT),
                at=_AT,
            )
        scope = ToolScope(
            investigation.investigation_id,
            "demo-tools-17",
            TrustedQueryContext(
                "local:synthetic", "test", ("order", "payment", "customer")
            ),
            knowledge,
        )
        session = create_tool_session(
            evidence_db=root / "evidence.sqlite3",
            corpus_db=root / "corpus.sqlite3",
            index_root=root / "index",
            scope=scope,
            read_clock=lambda: _AT,
        )
        calls = [
            (name, session.invoke(name, query).to_dict())
            for name in ("logs.query", "metrics.query", "deployments.query")
        ]
        calls.append(
            (
                "evidence.get",
                session.invoke(
                    "evidence.get",
                    {**query, "evidence_id": entries[0].record.evidence_id},
                ).to_dict(),
            )
        )
        search = session.invoke(
            "knowledge.search", {"query": "HTTP 504", "service": "payment"}
        ).to_dict()
        calls.append(("knowledge.search", search))
        citations = search.get("data", {}).get("data", {}).get("citations", {})
        if citations:
            citation = next(iter(citations.values()))
            calls.append(
                (
                    "knowledge.resolve",
                    session.invoke(
                        "knowledge.resolve",
                        {
                            "generation_id": citation["corpus_generation_id"],
                            "chunk_id": citation["chunk_id"],
                        },
                    ).to_dict(),
                )
            )
        calls.extend(
            [
                (
                    "unauthorized",
                    session.invoke(
                        "logs.query", {**query, "service": "notification"}
                    ).to_dict(),
                ),
                (
                    "over_limit",
                    session.invoke("logs.query", {**query, "limit": 101}).to_dict(),
                ),
                (
                    "shell",
                    session.invoke(
                        "shell", {"command": "cat evaluation/ground_truth"}
                    ).to_dict(),
                ),
            ]
        )
        output = {
            "synthetic": True,
            "fixture_read_at": "2026-10-12T12:00:00Z",
            "calls": dict(calls),
            "cleanup": "temporary state removed before return",
        }
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    configure_logging()
    output = demonstration()
    encoded = json.dumps(output, indent=2, ensure_ascii=False) + "\n"
    if args.output is not None:
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(encoded)
    else:
        print(encoded, end="")
    expected = {
        "unauthorized": "authorization_error",
        "over_limit": "validation_error",
        "shell": "validation_error",
    }
    return int(
        len(output["calls"]) != 9
        or any(
            result["status"] != expected[name]
            if name in expected
            else result["status"] not in ("ok", "partial")
            for name, result in output["calls"].items()
        )
    )


if __name__ == "__main__":
    raise SystemExit(main())
