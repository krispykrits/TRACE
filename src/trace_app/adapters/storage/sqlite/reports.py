"""Read-only private artifact port; application policy controls disclosure."""

from __future__ import annotations

import json
from pathlib import Path

from trace_app.adapters.storage.sqlite.investigations import SQLiteInvestigationStore
from trace_app.investigation.reports import SavedInvestigation


class SQLiteReportReader:
    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self, investigation_id: str, *, access_scope: str) -> SavedInvestigation:
        with SQLiteInvestigationStore(self.path, read_only=True) as store:
            job = store.get_investigation(investigation_id, access_scope=access_scope)
            attempts = store.list_attempts(investigation_id, access_scope=access_scope)
            rows = store._db.execute(
                "SELECT artifact_id,role,metadata,body FROM workflow_artifacts WHERE investigation_id=? ORDER BY rowid",
                (investigation_id,),
            ).fetchall()
            if len(rows) > 10 or any(
                len(row[2]) + len(row[3]) > 1_000_000 for row in rows
            ):
                raise ValueError("Stored artifacts exceed their bounds.")
            return SavedInvestigation(
                job,
                attempts,
                tuple(
                    {
                        "artifact_id": row[0],
                        "role": row[1],
                        "metadata": json.loads(row[2]),
                        "body": json.loads(row[3]),
                    }
                    for row in rows
                ),
            )
