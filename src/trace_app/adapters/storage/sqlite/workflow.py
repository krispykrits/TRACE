"""Private workflow artifacts and atomic publication under current attempt ownership."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from trace_app.adapters.storage.sqlite.investigations import (
    SQLiteInvestigationStore,
    _at,
)
from trace_app.investigation.bundle import BUNDLE_VERSION, EvidencePackage
from trace_app.investigation.execution import ExecutionIdentity
from trace_app.investigation.models import (
    Investigation,
    StoreAccessError,
    StoreInputError,
    StoreStateError,
)
from trace_app.investigation.workflow import (
    ARTIFACT_VERSION,
    WORKFLOW_TRANSITIONS,
    WORKFLOW_VERSION,
    WorkflowPublication,
)


class SQLiteWorkflowStore:
    """Raw artifact bodies have no public getter; #38 must add current source/review access."""

    def __init__(self, path: Path) -> None:
        self._store = SQLiteInvestigationStore(path)

    def close(self) -> None:
        self._store.close()

    def get_investigation(self, identity: ExecutionIdentity) -> Investigation:
        return self._store.get_investigation(
            identity.investigation_id, access_scope=identity.access_scope
        )

    def _active(self, identity: ExecutionIdentity, at: datetime) -> None:
        self._store._active(
            identity.investigation_id,
            identity.access_scope,
            identity.attempt_id,
            _at(at),
        )

    def start(self, identity: ExecutionIdentity, *, at: datetime) -> None:
        with self._store._transaction():
            self._active(identity, at)
            try:
                self._store._db.execute(
                    "INSERT INTO workflow_runs VALUES(?,?,'started',NULL,NULL)",
                    (identity.investigation_id, identity.attempt_id),
                )
            except sqlite3.IntegrityError:
                raise StoreStateError(
                    "Workflow already started; no implicit replay is permitted."
                ) from None

    def _phase(self, identity: ExecutionIdentity) -> str:
        row = self._store._db.execute(
            "SELECT phase,attempt_id FROM workflow_runs WHERE investigation_id=?",
            (identity.investigation_id,),
        ).fetchone()
        if row is None or row[1] != identity.attempt_id:
            raise StoreStateError("Workflow attempt is no longer active.")
        return str(row[0])

    def phase(self, identity: ExecutionIdentity, name: str, *, at: datetime) -> None:
        with self._store._transaction():
            self._active(identity, at)
            previous = self._phase(identity)
            if name not in WORKFLOW_TRANSITIONS.get(previous, set()):
                raise StoreStateError("Workflow phase transition is not permitted.")
            self._store._db.execute(
                "UPDATE workflow_runs SET phase=? WHERE investigation_id=?",
                (name, identity.investigation_id),
            )
            if name == "evidence_only":
                self._complete(identity, "pending", at)
                self._store._db.execute(
                    "UPDATE workflow_runs SET outcome='evidence_only' WHERE investigation_id=?",
                    (identity.investigation_id,),
                )

    def retain(
        self, identity: ExecutionIdentity, package: EvidencePackage, *, at: datetime
    ) -> str:
        if (
            package.investigation_id != identity.investigation_id
            or package.data is None
            or package.status not in ("complete", "partial")
        ):
            raise StoreInputError("Only a scoped gathered package can be retained.")
        body = json.dumps(package.to_dict(), allow_nan=False)
        if len(body.encode()) > 350_000:
            raise StoreInputError("Evidence artifact exceeds its bound.")
        artifact_id = uuid.uuid4().hex
        metadata = {
            "artifact_id": artifact_id,
            "role": "untrusted_evidence",
            "version": BUNDLE_VERSION,
            "workflow_version": WORKFLOW_VERSION,
            "package_status": package.status,
            "sensitivity": "unknown",
            "mutation_authority": False,
        }
        with self._store._transaction():
            self._active(identity, at)
            if self._phase(identity) not in ("gathering", "regathering"):
                raise StoreStateError(
                    "Evidence retention is outside the gathering phase."
                )
            self._insert(
                artifact_id,
                identity,
                "untrusted_evidence",
                BUNDLE_VERSION,
                "unknown",
                metadata,
                body,
            )
        return artifact_id

    def _insert(
        self,
        artifact_id: str,
        identity: ExecutionIdentity,
        role: str,
        version: str,
        sensitivity: str,
        metadata: dict[str, Any],
        body: str,
    ) -> None:
        self._store._db.execute(
            "INSERT INTO workflow_artifacts VALUES(?,?,?,?,?,?,?,?)",
            (
                artifact_id,
                identity.investigation_id,
                identity.attempt_id,
                role,
                version,
                sensitivity,
                json.dumps(metadata, allow_nan=False),
                body,
            ),
        )

    def publish(self, publication: WorkflowPublication, *, at: datetime) -> None:
        if (
            not isinstance(publication, WorkflowPublication)
            or not publication.is_issued()
        ):
            raise StoreInputError(
                "Assessment publication must be issued by the workflow."
            )
        if (
            publication.outcome not in ("accepted", "review_required")
            or publication.assessment_status
            not in ("supported", "abstained", "pending")
            or (publication.outcome == "review_required")
            != (publication.assessment_status == "pending")
        ):
            raise StoreInputError("Publication outcome is inconsistent.")
        body = publication.storage_body()
        if len(body.encode()) > 262_144:
            raise StoreInputError("Assessment artifact exceeds its bound.")
        identity = publication.identity
        with self._store._transaction():
            self._active(identity, at)
            if self._phase(identity) != "publishing":
                raise StoreStateError("Publication is outside its permitted phase.")
            snapshot = self._store._db.execute(
                "SELECT 1 FROM snapshots WHERE investigation_id=?",
                (identity.investigation_id,),
            ).fetchone()
            if snapshot is None:
                raise StoreStateError(
                    "Publication requires a retained evidence snapshot."
                )
            self._insert(
                publication.artifact_id,
                identity,
                publication.outcome,
                ARTIFACT_VERSION,
                publication.sensitivity,
                publication.metadata(),
                body,
            )
            self._complete(identity, publication.assessment_status, at)
            self._store._db.execute(
                "UPDATE workflow_runs SET outcome=? WHERE investigation_id=?",
                (publication.outcome, identity.investigation_id),
            )

    def _complete(
        self, identity: ExecutionIdentity, assessment_status: str, at: datetime
    ) -> None:
        timestamp = _at(at)
        self._store._db.execute(
            "UPDATE attempts SET outcome='completed',finished_at=? WHERE attempt_id=?",
            (timestamp, identity.attempt_id),
        )
        self._store._db.execute(
            """UPDATE investigations SET status='completed',assessment_status=?,
            review_status='unreviewed',active_attempt_id=NULL,lease_until=NULL,finished_at=?,failure_code=NULL
            WHERE investigation_id=?""",
            (assessment_status, timestamp, identity.investigation_id),
        )

    def fail(self, identity: ExecutionIdentity, code: str, *, at: datetime) -> str:
        from trace_app.investigation.models import _identifier

        _identifier("failure_code", code)
        timestamp = _at(at)
        with self._store._transaction():
            row = self._store._scoped_row(
                identity.investigation_id, identity.access_scope
            )
            if row["status"] in ("cancelled", "expired"):
                return str(row["status"])
            if (
                row["status"] != "running"
                or row["active_attempt_id"] != identity.attempt_id
            ):
                raise StoreStateError(
                    "A stale attempt cannot fail or publish the current job."
                )
            status = (
                "expired"
                if row["lease_until"] <= timestamp
                or row["expires_at"] is not None
                and row["expires_at"] <= timestamp
                else "failed"
            )
            self._store._db.execute(
                "UPDATE attempts SET outcome=?,finished_at=?,failure_code=? WHERE attempt_id=?",
                (status, timestamp, code, identity.attempt_id),
            )
            self._store._db.execute(
                """UPDATE investigations SET status=?,active_attempt_id=NULL,lease_until=NULL,
                finished_at=?,failure_code=? WHERE investigation_id=?""",
                (status, timestamp, code, identity.investigation_id),
            )
            self._store._db.execute(
                "UPDATE workflow_runs SET phase='failed',outcome=?,failure_code=? WHERE investigation_id=? AND attempt_id=?",
                (status, code, identity.investigation_id, identity.attempt_id),
            )
        return status

    def metadata(self, investigation_id: str, *, access_scope: str) -> dict[str, Any]:
        """Scope-checked content-free records only; direct DB/file access is trusted."""
        job = self._store.get_investigation(investigation_id, access_scope=access_scope)
        run = self._store._db.execute(
            "SELECT phase,outcome,failure_code FROM workflow_runs WHERE investigation_id=?",
            (investigation_id,),
        ).fetchone()
        if run is None:
            raise StoreAccessError(
                "Workflow result is absent or outside the supplied scope."
            )
        artifacts = [
            json.loads(row[0])
            for row in self._store._db.execute(
                "SELECT metadata FROM workflow_artifacts WHERE investigation_id=?",
                (investigation_id,),
            )
        ]
        return {
            "investigation_id": investigation_id,
            "execution_status": job.status,
            "assessment_status": job.assessment_status,
            "phase": run[0],
            "outcome": run[1],
            "failure_code": run[2],
            "artifacts": artifacts,
        }
