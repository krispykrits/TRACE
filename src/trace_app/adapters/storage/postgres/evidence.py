"""Persist and reauthorize the evidence snapshot used by a running investigation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict

from trace_app.adapters.storage.postgres.workflow import PostgresWorkflowStore
from trace_app.evidence.models import (
    EVIDENCE_SCHEMA_VERSION,
    EvidenceRecord,
    SourceAvailability,
)
from trace_app.investigation.execution import ExecutionIdentity
from trace_app.investigation.models import (
    DeploymentPayload,
    EvidenceEntry,
    EvidenceSnapshot,
    Investigation,
    LogPayload,
    MetricPayload,
    StoreAccessError,
    StoreConflictError,
    StoreDependencyError,
    StoreInputError,
)
from trace_app.investigation.provider_policy import (
    EvidenceSelection,
    Sensitivity,
    SourceAccessPolicy,
)
from trace_app.knowledge.models import canonical


class PostgresEvidenceStore:
    """Keep bounded snapshots private and recheck their current source permissions."""

    def __init__(
        self,
        workflow: PostgresWorkflowStore,
        identity: ExecutionIdentity,
        policy: SourceAccessPolicy,
        *,
        clearance: Sensitivity,
    ) -> None:
        self._workflow, self._identity, self._policy, self._clearance = (
            workflow,
            identity,
            policy,
            clearance,
        )

    def get_investigation(
        self, investigation_id: str, *, access_scope: str
    ) -> Investigation:
        if (
            investigation_id != self._identity.investigation_id
            or access_scope != self._identity.access_scope
        ):
            raise StoreAccessError("Investigation is not accessible.")
        return self._workflow.get_investigation(self._identity)

    @staticmethod
    def _data(snapshot: EvidenceSnapshot) -> dict[str, object]:
        return {
            "window_start": snapshot.window_start,
            "window_end": snapshot.window_end,
            "sources": [source.to_dict() for source in snapshot.sources],
            "entries": [
                {
                    "kind": entry.kind,
                    "record": entry.record.to_dict(),
                    "payload": asdict(entry.payload),
                }
                for entry in snapshot.entries
            ],
        }

    def ingest_snapshot(self, snapshot: EvidenceSnapshot) -> int:
        if not snapshot.entries or len(snapshot.entries) > 256:
            raise StoreInputError("Evidence snapshot must contain 1–256 records.")
        data = self._data(snapshot)
        serialized = canonical(data)
        if len(serialized.encode()) > 1_000_000:
            raise StoreInputError("Evidence snapshot exceeds its byte limit.")
        selections = tuple(
            EvidenceSelection(
                entry.record.evidence_id, entry.record.source_revision, ("content",)
            )
            for entry in snapshot.entries
        )
        contents = {
            entry.record.evidence_id: canonical(
                {
                    "kind": entry.kind,
                    "record": entry.record.to_dict(),
                    "payload": asdict(entry.payload),
                }
            )
            for entry in snapshot.entries
        }
        binding = self._policy.bind(selections, expected_content=contents)
        self._policy.check_saved(binding, transmission=False, clearance=self._clearance)
        fingerprint = hashlib.sha256(serialized.encode()).hexdigest()
        body = json.dumps(
            {"data": data, "binding": binding},
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        with self._workflow._jobs._connection() as connection:
            job = self._workflow._active(connection, self._identity)
            principal = f"entra:{job['submitted_tenant']}:{job['submitted_object']}"
            if (
                binding.get("principal_id") != principal
                or binding.get("investigation_id") != self._identity.investigation_id
            ):
                raise StoreAccessError(
                    "Evidence authority does not match the submitter."
                )
            if (
                snapshot.window_start != job["window_start"]
                or snapshot.window_end != job["window_end"]
            ):
                raise StoreInputError(
                    "Evidence window does not match the investigation."
                )
            grant = connection.execute(
                "SELECT services FROM trace_principal_grants WHERE tenant_id=%s AND object_id=%s FOR SHARE",
                (job["submitted_tenant"], job["submitted_object"]),
            ).fetchone()
            if grant is None or any(
                entry.record.environment != job["environment"]
                or entry.record.service not in grant["services"]
                for entry in snapshot.entries
            ):
                raise StoreAccessError("Evidence is outside the authorized scope.")
            self._policy.check_saved(
                binding, transmission=False, clearance=self._clearance
            )
            row = connection.execute(
                "INSERT INTO trace_snapshots VALUES (%s,%s,%s,%s) ON CONFLICT (investigation_id) DO NOTHING RETURNING investigation_id",
                (
                    self._identity.investigation_id,
                    EVIDENCE_SCHEMA_VERSION,
                    fingerprint,
                    body,
                ),
            ).fetchone()
            if row is None:
                previous = connection.execute(
                    "SELECT fingerprint,body FROM trace_snapshots WHERE investigation_id=%s",
                    (self._identity.investigation_id,),
                ).fetchone()
                if (
                    previous is None
                    or previous["fingerprint"] != fingerprint
                    or json.loads(previous["body"])["binding"] != binding
                ):
                    raise StoreConflictError(
                        "Evidence snapshot conflicts with the existing snapshot."
                    )
                return 0
            return len(snapshot.entries)

    def get_snapshot(
        self, investigation_id: str, *, access_scope: str
    ) -> EvidenceSnapshot:
        self.get_investigation(investigation_id, access_scope=access_scope)
        with self._workflow._jobs._connection() as connection:
            job = self._workflow._active(connection, self._identity)
            row = connection.execute(
                "SELECT * FROM trace_snapshots WHERE investigation_id=%s",
                (investigation_id,),
            ).fetchone()
            if row is None:
                raise StoreAccessError("Evidence snapshot is unavailable.")
            try:
                if (
                    row["schema_version"] != EVIDENCE_SCHEMA_VERSION
                    or len(row["body"].encode()) > 1_200_000
                ):
                    raise ValueError("Invalid snapshot.")
                stored = json.loads(row["body"])
                data = stored["data"]
                principal = f"entra:{job['submitted_tenant']}:{job['submitted_object']}"
                if (
                    stored["binding"].get("principal_id") != principal
                    or stored["binding"].get("investigation_id") != investigation_id
                ):
                    raise StoreAccessError(
                        "Evidence authority does not match the submitter."
                    )
                if (
                    hashlib.sha256(canonical(data).encode()).hexdigest()
                    != row["fingerprint"]
                ):
                    raise ValueError("Invalid snapshot fingerprint.")
                entries = tuple(
                    EvidenceEntry(
                        item["kind"],
                        EvidenceRecord.from_dict(item["record"]),
                        {
                            "log": LogPayload,
                            "metric": MetricPayload,
                            "deployment": DeploymentPayload,
                        }[item["kind"]](**item["payload"]),
                    )
                    for item in data["entries"]
                )
                snapshot = EvidenceSnapshot(
                    entries,
                    data["window_start"],
                    data["window_end"],
                    tuple(SourceAvailability(**value) for value in data["sources"]),
                )
                if not snapshot.entries or len(snapshot.entries) > 256:
                    raise ValueError("Invalid snapshot size.")
                self._policy.check_saved(
                    stored["binding"], transmission=False, clearance=self._clearance
                )
                return snapshot
            except (KeyError, TypeError, ValueError):
                raise StoreDependencyError("Stored evidence is invalid.") from None
