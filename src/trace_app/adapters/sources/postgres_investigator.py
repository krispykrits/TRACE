"""Owner-managed hosted evidence and knowledge held in PostgreSQL."""

import json
import time
from contextlib import nullcontext
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any, Callable

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from trace_app.adapters.retrieval.local_index import _validate
from trace_app.adapters.storage.postgres.connection import connect
from trace_app.evidence.models import EvidenceRecord, SourceAvailability, _parse_utc
from trace_app.evidence.queries import TrustedQueryContext
from trace_app.investigation.assessment_context import AssessmentBoundaryError
from trace_app.investigation.execution import ExecutionPolicy
from trace_app.investigation.models import (
    DeploymentPayload,
    EvidenceEntry,
    EvidenceSnapshot,
    Investigation,
    InvestigationRequest,
    LogPayload,
    MetricPayload,
    StoreAccessError,
    _identifier,
)
from trace_app.investigation.provider_policy import (
    ProviderScope,
    Sensitivity,
    SourceKind,
)
from trace_app.knowledge.generations import CorpusGeneration
from trace_app.knowledge.models import (
    CorpusAccessError,
    CorpusReadContext,
    DocumentMetadata,
    KnowledgeChunk,
    canonical,
    digest,
    parse_json,
)


class PostgresInvestigatorProfile:
    """Read current owner grants and source content on each operation."""

    def __init__(
        self,
        dsn: str,
        source_id: str,
        *,
        clock: Callable[[], float] = time.time,
        source_loader: Callable[[], dict[str, Any]] | None = None,
        connection: Any = None,
    ):
        _identifier("source_id", source_id)
        self.dsn, self.source_id, self.clock = dsn, source_id, clock
        self._source_loader = source_loader
        self._connection = connection
        data = self._package()["profile"]
        if data.get("schema_version") != "postgres-investigator.v1":
            raise AssessmentBoundaryError("access_denied")
        self.principal_id = data["principal_id"]
        _identifier("principal_id", self.principal_id)
        self.evidence = TrustedQueryContext(
            **{
                **data["evidence_scope"],
                "allowed_services": tuple(data["evidence_scope"]["allowed_services"]),
            }
        )
        self.knowledge = CorpusReadContext(
            **{
                **data["knowledge_scope"],
                "allowed_services": tuple(data["knowledge_scope"]["allowed_services"]),
            }
        )
        self.policy = ExecutionPolicy(**data["execution_policy"])
        self.clearance = Sensitivity[data["clearance"].upper()]
        if (
            self.clearance >= Sensitivity.SECRET
            or self.evidence.environment != self.knowledge.environment
        ):
            raise AssessmentBoundaryError("access_denied")
        self.source_investigation_id = data["source_investigation_id"]
        self._identity = {
            key: data[key]
            for key in (
                "principal_id",
                "evidence_scope",
                "knowledge_scope",
                "source_investigation_id",
                "clearance",
            )
        }
        self.current()

    def _package(self) -> dict[str, Any]:
        if self._source_loader is not None:
            return self._source_loader()
        manager = (
            nullcontext(self._connection)
            if self._connection is not None
            else connect(self.dsn, row_factory=dict_row, connect_timeout=5)
        )
        with manager as connection:
            row = connection.execute(
                "SELECT profile, capture, knowledge FROM trace_source_packages WHERE source_id=%s",
                (self.source_id,),
            ).fetchone()
        if row is None or len(json.dumps(row).encode()) > 20_000_000:
            raise AssessmentBoundaryError("access_denied")
        return dict(row)

    def current(self) -> dict[str, Any]:
        data = self._package()["profile"]
        if (
            data.get("schema_version") != "postgres-investigator.v1"
            or any(data.get(k) != v for k, v in self._identity.items())
            or _parse_utc(data["expires_at"]).timestamp() <= self.clock()
        ):
            raise AssessmentBoundaryError("access_denied")
        return data

    def scope(self, investigation_id: str) -> ProviderScope:
        self.current()
        return ProviderScope(self.principal_id, investigation_id)

    def check_job(self, job: Investigation) -> None:
        self.current()
        if (
            job.request.environment != self.evidence.environment
            or job.request.service not in self.evidence.allowed_services
            or (
                job.request.expires_at
                and _parse_utc(job.request.expires_at).timestamp() <= self.clock()
            )
        ):
            raise AssessmentBoundaryError("access_denied")

    def allowed_for_job(self, investigation_id: str) -> tuple[str, ...]:
        """Recheck the submitter's current service grant for an active job."""
        manager = (
            nullcontext(self._connection)
            if self._connection is not None
            else connect(self.dsn, row_factory=dict_row, connect_timeout=5)
        )
        with manager as connection:
            row = connection.execute(
                """SELECT j.submitted_tenant, j.submitted_object, j.access_scope,
                          j.environment, j.service, g.services, g.actions,
                          g.access_scope AS grant_scope, g.environment AS grant_environment
                   FROM trace_jobs j JOIN trace_principal_grants g
                     ON g.tenant_id=j.submitted_tenant AND g.object_id=j.submitted_object
                   WHERE j.investigation_id=%s AND j.status='running'
                     AND j.lease_until > clock_timestamp()""",
                (investigation_id,),
            ).fetchone()
        if (
            row is None
            or self.principal_id
            != f"entra:{row['submitted_tenant']}:{row['submitted_object']}"
            or row["access_scope"] != self.evidence.access_scope
            or row["environment"] != self.evidence.environment
            or row["grant_scope"] != row["access_scope"]
            or row["grant_environment"] != row["environment"]
            or row["service"] not in row["services"]
            or "submit" not in row["actions"]
        ):
            raise StoreAccessError("Investigation authority is no longer active.")
        return tuple(row["services"])

    def get_investigation(
        self, investigation_id: str, *, access_scope: str
    ) -> Investigation:
        capture = self._package()["capture"]
        data = dict(capture["investigation"])
        data["request"] = InvestigationRequest(**data["request"])
        job = Investigation(**data)
        if (
            job.investigation_id != investigation_id
            or job.investigation_id != self.source_investigation_id
            or job.request.access_scope != access_scope
        ):
            raise StoreAccessError("Source is not accessible.")
        self.check_job(job)
        return job

    def get_snapshot(
        self, investigation_id: str, *, access_scope: str
    ) -> EvidenceSnapshot:
        self.get_investigation(investigation_id, access_scope=access_scope)
        data = self._package()["capture"]["snapshot"]
        entries = tuple(
            EvidenceEntry(
                e["kind"],
                EvidenceRecord.from_dict(e["record"]),
                {
                    "log": LogPayload,
                    "metric": MetricPayload,
                    "deployment": DeploymentPayload,
                }[e["kind"]](**e["payload"]),
            )
            for e in data["entries"]
        )
        if (
            not entries
            or len(entries) > 256
            or any(
                entry.record.access_classification != "synthetic_public"
                for entry in entries
            )
        ):
            raise StoreAccessError("Only bounded synthetic evidence is supported.")
        return EvidenceSnapshot(
            entries,
            data["window_start"],
            data["window_end"],
            tuple(SourceAvailability(**s) for s in data["sources"]),
        )

    def index(self):
        knowledge = self._package()["knowledge"]
        return _validate(knowledge["index_manifest"], knowledge["index_records"])

    @staticmethod
    def _permitted(
        metadata: DocumentMetadata, context: CorpusReadContext, at: datetime
    ) -> bool:
        valid_at = _parse_utc(context.valid_at)
        return (
            metadata.access_scope == context.access_scope
            and metadata.environment == context.environment
            and metadata.service in context.allowed_services
            and metadata.evaluation_role == context.evaluation_role
            and _parse_utc(metadata.verified_at)
            <= at
            < _parse_utc(metadata.fresh_until)
            and _parse_utc(metadata.valid_from) <= valid_at
            and (
                metadata.valid_until is None
                or valid_at < _parse_utc(metadata.valid_until)
            )
        )

    def read_chunks(
        self,
        *,
        context: CorpusReadContext,
        at: datetime,
        generation_id: str | None = None,
    ) -> tuple[KnowledgeChunk, ...]:
        self.current()
        data = self._package()["knowledge"]
        generation = CorpusGeneration.from_dict(data["manifest"])
        if generation_id != generation.generation_id or not _parse_utc(
            generation.created_at
        ) <= at < _parse_utc(generation.retain_until):
            raise CorpusAccessError("Corpus generation is unavailable.")
        result = []
        for item in data["chunks"]:
            current = DocumentMetadata.from_dict(item["current_metadata"])
            chunk = KnowledgeChunk.from_dict(item["chunk"])
            if (
                item["status"] == "active"
                and current.document_id == chunk.metadata.document_id
                and self._permitted(current, context, at)
                and self._permitted(chunk.metadata, context, at)
            ):
                result.append(chunk)
        return tuple(sorted(result, key=lambda c: (c.metadata.document_id, c.ordinal)))

    def resolve(
        self,
        generation_id: str,
        chunk_id: str,
        *,
        context: CorpusReadContext,
        at: datetime,
    ) -> KnowledgeChunk:
        for chunk in self.read_chunks(
            context=context, at=at, generation_id=generation_id
        ):
            if chunk.chunk_id == chunk_id:
                return chunk
        raise CorpusAccessError("Chunk is not accessible.")

    def source_content(self) -> dict[str, tuple[str, str, SourceKind]]:
        snapshot = self.get_snapshot(
            self.source_investigation_id, access_scope=self.evidence.access_scope
        )
        result = {
            e.record.evidence_id: (
                e.record.source_revision,
                canonical(
                    {
                        "kind": e.kind,
                        "record": e.record.to_dict(),
                        "payload": asdict(e.payload),
                    }
                ),
                SourceKind.SYNTHETIC,
            )
            for e in snapshot.entries
            if e.record.environment == self.evidence.environment
            and e.record.service in self.evidence.allowed_services
        }
        index = self.index()
        for chunk in self.read_chunks(
            context=self.knowledge,
            at=datetime.fromtimestamp(self.clock(), UTC),
            generation_id=index.corpus_generation_id,
        ):
            identity = "knowledge-" + digest(
                canonical(
                    {
                        "corpus_generation_id": index.corpus_generation_id,
                        "chunk_id": chunk.chunk_id,
                    }
                )
            )
            mapping = {
                "corpus_generation_id": index.corpus_generation_id,
                "chunk_id": chunk.chunk_id,
                "document_sha256": chunk.document_sha256,
                "section": chunk.section,
                "start_offset": chunk.start_offset,
                "end_offset": chunk.end_offset,
                "metadata": chunk.metadata.to_dict(),
            }
            result[identity] = (
                chunk.metadata.source_revision,
                canonical(
                    {
                        "passage": {"citation_id": identity, "text": chunk.text},
                        "citation": mapping,
                    }
                ),
                SourceKind.RUNBOOK,
            )
        return result


def import_synthetic_package(dsn: str, source_id: str, document: str) -> None:
    """Import a separately authorized synthetic JSON package, without overwriting one."""
    if len(document.encode()) > 20_000_000:
        raise ValueError("Source package exceeds the size limit.")
    package = parse_json(document)
    if not isinstance(package, dict) or set(package) != {
        "profile",
        "capture",
        "knowledge",
    }:
        raise ValueError("Invalid source package.")
    profile = PostgresInvestigatorProfile(dsn, source_id, source_loader=lambda: package)
    profile.get_snapshot(
        profile.source_investigation_id, access_scope=profile.evidence.access_scope
    )
    profile.source_content()
    if any(
        item["chunk"]["metadata"]["access_classification"] != "synthetic_public"
        for item in package["knowledge"]["chunks"]
    ):
        raise ValueError("Only synthetic knowledge may be imported here.")
    with connect(dsn) as connection:
        connection.execute(
            "INSERT INTO trace_source_packages(source_id, profile, capture, knowledge) VALUES (%s,%s,%s,%s)",
            (
                source_id,
                Jsonb(package["profile"]),
                Jsonb(package["capture"]),
                Jsonb(package["knowledge"]),
            ),
        )
