"""Developer-only process demonstration of issue #10 SQLite evidence persistence."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from trace_app.investigation_state import (
    EvidenceEntry,
    EvidenceSnapshot,
    InvestigationRequest,
    LogPayload,
    StoreAccessError,
    StoreConflictError,
    StoreInputError,
    StoreSchemaError,
    StoreStateError,
)
from trace_app.replay import ReplayConfig, ReplaySession
from trace_app.sqlite_store import SQLiteInvestigationStore

_SCOPE = "local:synthetic"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local synthetic evidence store demo.")
    commands = parser.add_subparsers(dest="command", required=True)
    ingest = commands.add_parser(
        "ingest", help="replay and persist a synthetic incident"
    )
    ingest.add_argument("--db", required=True, type=Path)
    ingest.add_argument("--seed", required=True, type=int)
    ingest.add_argument("--mode", required=True, choices=("normal", "failure"))
    ingest.add_argument("--submission-key", required=True)
    show = commands.add_parser("show", help="read persisted evidence in a new process")
    show.add_argument("--db", required=True, type=Path)
    show.add_argument("--investigation-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        config = None
        if args.command == "ingest":
            config = ReplayConfig(seed=args.seed, mode=args.mode)
        elif not args.db.is_file():
            raise StoreInputError("db must exist for show.")
        with SQLiteInvestigationStore(args.db) as store:
            if config is not None:
                replay = ReplaySession(config).replay()
                bundle = replay.evidence
                request = InvestigationRequest(
                    submission_key=args.submission_key,
                    service="order",
                    environment="test",
                    access_scope=_SCOPE,
                    window_start=bundle.window_start,
                    window_end=bundle.window_end,
                )
                investigation = store.submit(request, at=datetime.now(UTC))
                snapshot = EvidenceSnapshot(
                    entries=tuple(
                        EvidenceEntry("log", record, LogPayload(record.event))
                        for record in bundle.records
                    ),
                    window_start=bundle.window_start,
                    window_end=bundle.window_end,
                    sources=bundle.sources,
                )
                count = store.ingest_snapshot(
                    investigation.investigation_id,
                    snapshot,
                    access_scope=_SCOPE,
                    at=datetime.now(UTC),
                )
                result = {
                    "investigation_id": investigation.investigation_id,
                    "status": investigation.status,
                    "ingested": count,
                    "evidence_ids": [
                        entry.record.evidence_id for entry in snapshot.entries
                    ],
                }
            else:
                investigation = store.get_investigation(
                    args.investigation_id, access_scope=_SCOPE
                )
                snapshot = store.get_snapshot(
                    args.investigation_id, access_scope=_SCOPE
                )
                result = {
                    "investigation_id": investigation.investigation_id,
                    "status": investigation.status,
                    "assessment_status": investigation.assessment_status,
                    "review_status": investigation.review_status,
                    "evidence": [
                        {
                            "kind": entry.kind,
                            "record": entry.record.to_dict(),
                            "payload": asdict(entry.payload),
                        }
                        for entry in snapshot.entries
                    ],
                    "sources": [source.to_dict() for source in snapshot.sources],
                }
    except (
        ValueError,
        StoreAccessError,
        StoreConflictError,
        StoreInputError,
        StoreSchemaError,
        StoreStateError,
        sqlite3.Error,
    ) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
