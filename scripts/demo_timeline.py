"""Offline developer demo: shuffle, persist, order and resolve a synthetic case."""

from __future__ import annotations

import argparse
import json
import random
import sqlite3
import sys
import tempfile
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

from trace_app.evidence import normalize_timestamp
from trace_app.evidence_queries import (
    EvidenceQuery,
    EvidenceQueryService,
    TrustedQueryContext,
)
from trace_app.investigation_state import (
    InvestigationRequest,
    StoreAccessError,
    StoreConflictError,
    StoreDependencyError,
    StoreSchemaError,
)
from trace_app.scenarios import CASE_IDS, ScenarioConfig, ScenarioSession
from trace_app.sqlite_store import SQLiteInvestigationStore
from trace_app.structured_logging import configure_logging
from trace_app.timeline import TimelineService

_CAPTURE = datetime(2026, 10, 12, 12, tzinfo=UTC)
_SCOPE = "local:synthetic"
_CONTEXT = TrustedQueryContext(
    _SCOPE, "test", ("order", "payment", "customer", "notification")
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=CASE_IDS, default="c01")
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--service")
    parser.add_argument("--window-start")
    parser.add_argument("--window-end")
    args = parser.parse_args(argv)
    configure_logging(level="INFO")
    try:
        snapshot = (
            ScenarioSession(ScenarioConfig(args.case, args.seed))
            .replay(collected_at=_CAPTURE)
            .snapshot
        )
        entries = list(snapshot.entries)
        random.Random(args.seed).shuffle(entries)
        snapshot = replace(snapshot, entries=tuple(entries))
        query = EvidenceQuery(
            window_start=normalize_timestamp(
                args.window_start
                if args.window_start is not None
                else snapshot.window_start
            ),
            window_end=normalize_timestamp(
                args.window_end if args.window_end is not None else snapshot.window_end
            ),
            service=args.service,
            limit=args.limit,
        )
        with tempfile.TemporaryDirectory(prefix="trace-timeline-") as directory:
            path = Path(directory) / "state.sqlite3"
            with SQLiteInvestigationStore(path) as store:
                investigation = store.submit(
                    InvestigationRequest(
                        submission_key="demo",
                        service="order",
                        environment="test",
                        access_scope=_SCOPE,
                        window_start=snapshot.window_start,
                        window_end=snapshot.window_end,
                    ),
                    at=_CAPTURE,
                )
                store.ingest_snapshot(
                    investigation.investigation_id,
                    snapshot,
                    access_scope=_SCOPE,
                    at=_CAPTURE,
                )
            with SQLiteInvestigationStore(path) as store:
                service = TimelineService(EvidenceQueryService(store))
                timeline = service.build(
                    investigation.investigation_id, query, context=_CONTEXT
                )
                resolved_ids = [
                    service.resolve(
                        timeline, event.record.evidence_id, context=_CONTEXT
                    ).record.evidence_id
                    for event in timeline.events
                ]
                output = timeline.to_dict()
                output["resolved_evidence_ids"] = resolved_ids
    except (
        ValueError,
        StoreAccessError,
        StoreConflictError,
        StoreDependencyError,
        StoreSchemaError,
        sqlite3.Error,
    ) as error:
        print(json.dumps({"error": str(error)}), file=sys.stderr)
        return 2
    print(json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
