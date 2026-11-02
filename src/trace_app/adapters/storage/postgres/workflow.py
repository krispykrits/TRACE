"""Persist workflow phases and publish artifacts with PostgreSQL attempt fencing."""

from __future__ import annotations

import json
import uuid
from datetime import datetime
from typing import Any

from trace_app.adapters.storage.postgres.jobs import PostgresJobs, _job
from trace_app.investigation.bundle import BUNDLE_VERSION, EvidencePackage
from trace_app.investigation.execution import ExecutionIdentity
from trace_app.investigation.models import (
    Investigation,
    StoreInputError,
    StoreStateError,
)
from trace_app.investigation.workflow import (
    ARTIFACT_VERSION,
    WORKFLOW_TRANSITIONS,
    WORKFLOW_VERSION,
    WorkflowPublication,
)


class PostgresWorkflowStore:
    """Use short transactions and the database clock to fence every write."""

    def __init__(self, dsn: str) -> None:
        self._jobs = PostgresJobs(dsn)

    def close(self) -> None:
        pass

    @staticmethod
    def _active(connection: Any, identity: ExecutionIdentity) -> dict[str, Any]:
        row = connection.execute(
            """SELECT *, clock_timestamp() AS database_now FROM trace_jobs
            WHERE investigation_id=%s AND access_scope=%s FOR UPDATE""",
            (identity.investigation_id, identity.access_scope),
        ).fetchone()
        if (
            row is None
            or row["status"] != "running"
            or row["active_attempt_id"] != identity.attempt_id
            or row["lease_until"] is None
            or row["lease_until"] <= row["database_now"]
        ):
            raise StoreStateError("Workflow attempt is no longer active.")
        grant = connection.execute(
            """SELECT * FROM trace_principal_grants
            WHERE tenant_id=%s AND object_id=%s FOR SHARE""",
            (row["submitted_tenant"], row["submitted_object"]),
        ).fetchone()
        if (
            grant is None
            or grant["access_scope"] != row["access_scope"]
            or grant["environment"] != row["environment"]
            or row["service"] not in grant["services"]
            or "submit" not in grant["actions"]
        ):
            raise StoreStateError("Workflow authority is no longer active.")
        return row

    def get_investigation(self, identity: ExecutionIdentity) -> Investigation:
        with self._jobs._connection() as connection:
            return _job(self._active(connection, identity))

    def start(self, identity: ExecutionIdentity, *, at: datetime) -> None:
        with self._jobs._connection() as connection:
            self._active(connection, identity)
            row = connection.execute(
                """INSERT INTO trace_workflow_runs (investigation_id,attempt_id,phase)
                VALUES (%s,%s,'started') ON CONFLICT (investigation_id) DO NOTHING RETURNING investigation_id""",
                (identity.investigation_id, identity.attempt_id),
            ).fetchone()
            if row is None:
                raise StoreStateError(
                    "Workflow already started; replay is not permitted."
                )

    @staticmethod
    def _phase(connection: Any, identity: ExecutionIdentity) -> str:
        row = connection.execute(
            "SELECT phase FROM trace_workflow_runs WHERE investigation_id=%s AND attempt_id=%s",
            (identity.investigation_id, identity.attempt_id),
        ).fetchone()
        if row is None:
            raise StoreStateError("Workflow attempt is no longer active.")
        return str(row["phase"])

    @staticmethod
    def _complete(
        connection: Any, identity: ExecutionIdentity, assessment: str
    ) -> None:
        row = connection.execute(
            """UPDATE trace_jobs SET status='completed', assessment_status=%s, review_status='unreviewed',
            active_attempt_id=NULL, lease_until=NULL, finished_at=clock_timestamp(), failure_code=NULL
            WHERE investigation_id=%s AND status='running' AND active_attempt_id=%s
            AND lease_until > clock_timestamp() RETURNING investigation_id""",
            (assessment, identity.investigation_id, identity.attempt_id),
        ).fetchone()
        if row is None:
            raise StoreStateError("Workflow attempt is no longer active.")
        connection.execute(
            "UPDATE trace_job_attempts SET outcome='completed',finished_at=clock_timestamp() WHERE attempt_id=%s",
            (identity.attempt_id,),
        )

    def phase(self, identity: ExecutionIdentity, name: str, *, at: datetime) -> None:
        with self._jobs._connection() as connection:
            self._active(connection, identity)
            if name not in WORKFLOW_TRANSITIONS.get(
                self._phase(connection, identity), set()
            ):
                raise StoreStateError("Workflow phase transition is not permitted.")
            connection.execute(
                "UPDATE trace_workflow_runs SET phase=%s WHERE investigation_id=%s",
                (name, identity.investigation_id),
            )
            if name == "evidence_only":
                self._complete(connection, identity, "pending")
                connection.execute(
                    "UPDATE trace_workflow_runs SET outcome='evidence_only' WHERE investigation_id=%s",
                    (identity.investigation_id,),
                )

    def retain(
        self,
        identity: ExecutionIdentity,
        package: EvidencePackage,
        *,
        at: datetime,
        access_binding: dict[str, object] | None = None,
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
            "evidence_access": access_binding,
            "mutation_authority": False,
        }
        with self._jobs._connection() as connection:
            self._active(connection, identity)
            if self._phase(connection, identity) not in ("gathering", "regathering"):
                raise StoreStateError(
                    "Evidence retention is outside the gathering phase."
                )
            self._insert(
                connection,
                identity,
                artifact_id,
                "untrusted_evidence",
                BUNDLE_VERSION,
                "unknown",
                metadata,
                body,
            )
        return artifact_id

    @staticmethod
    def _insert(
        connection: Any,
        identity: ExecutionIdentity,
        artifact_id: str,
        role: str,
        version: str,
        sensitivity: str,
        metadata: dict[str, Any],
        body: str,
    ) -> None:
        connection.execute(
            "INSERT INTO trace_workflow_artifacts VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
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
        with self._jobs._connection() as connection:
            self._active(connection, identity)
            if self._phase(connection, identity) != "publishing":
                raise StoreStateError("Publication is outside its permitted phase.")
            if (
                connection.execute(
                    "SELECT 1 FROM trace_snapshots WHERE investigation_id=%s",
                    (identity.investigation_id,),
                ).fetchone()
                is None
            ):
                raise StoreStateError(
                    "Publication requires a retained evidence snapshot."
                )
            self._insert(
                connection,
                identity,
                publication.artifact_id,
                publication.outcome,
                ARTIFACT_VERSION,
                publication.sensitivity,
                publication.metadata(),
                body,
            )
            self._complete(connection, identity, publication.assessment_status)
            connection.execute(
                "UPDATE trace_workflow_runs SET outcome=%s WHERE investigation_id=%s",
                (publication.outcome, identity.investigation_id),
            )

    def fail(self, identity: ExecutionIdentity, code: str, *, at: datetime) -> str:
        from trace_app.investigation.models import _identifier

        _identifier("failure_code", code)
        with self._jobs._connection() as connection:
            row = connection.execute(
                "SELECT status,active_attempt_id,lease_until,clock_timestamp() AS database_now FROM trace_jobs WHERE investigation_id=%s AND access_scope=%s FOR UPDATE",
                (identity.investigation_id, identity.access_scope),
            ).fetchone()
            if row is None:
                raise StoreStateError("Workflow attempt is no longer active.")
            if row["status"] in ("cancelled", "expired"):
                return str(row["status"])
            if (
                row["status"] != "running"
                or row["active_attempt_id"] != identity.attempt_id
            ):
                raise StoreStateError("A stale attempt cannot fail the job.")
            status = (
                "expired" if row["lease_until"] <= row["database_now"] else "failed"
            )
            if code == "cancelled":
                status = "cancelled"
            outcome = "interrupted" if status == "expired" else status
            connection.execute(
                "UPDATE trace_job_attempts SET outcome=%s,finished_at=clock_timestamp() WHERE attempt_id=%s",
                (outcome, identity.attempt_id),
            )
            connection.execute(
                "UPDATE trace_jobs SET status=%s,active_attempt_id=NULL,lease_until=NULL,finished_at=clock_timestamp(),failure_code=%s WHERE investigation_id=%s",
                (status, code, identity.investigation_id),
            )
            connection.execute(
                "UPDATE trace_workflow_runs SET phase='failed',outcome=%s,failure_code=%s WHERE investigation_id=%s AND attempt_id=%s",
                (status, code, identity.investigation_id, identity.attempt_id),
            )
            return status
