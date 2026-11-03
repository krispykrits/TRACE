"""Owner-managed local grants and current SQLite originals, never query-derived grants."""

from __future__ import annotations

import json
import os
import stat
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from trace_app.adapters.retrieval.local_index import load_index
from trace_app.adapters.sources.authority import (
    LocalEvidenceAuthority as LocalEvidenceAuthority,
)
from trace_app.adapters.sources.authority import (
    LocalSupportReviews as LocalSupportReviews,
)
from trace_app.adapters.storage.sqlite.corpus import SQLiteCorpusStore
from trace_app.adapters.storage.sqlite.investigations import SQLiteInvestigationStore
from trace_app.evidence.models import _parse_utc
from trace_app.evidence.queries import TrustedQueryContext
from trace_app.investigation.assessment_context import AssessmentBoundaryError
from trace_app.investigation.execution import ExecutionPolicy
from trace_app.investigation.models import Investigation, _identifier
from trace_app.investigation.provider_policy import (
    ProviderScope,
    Sensitivity,
    SourceKind,
)
from trace_app.knowledge.models import CorpusReadContext, canonical, digest

PROFILE_VERSION = "local-investigator.v1"


def read_private_json(path: Path) -> dict[str, Any]:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor) as stream:
        info = os.fstat(stream.fileno())
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or stat.S_IMODE(info.st_mode) != 0o600
            or info.st_size > 1_000_000
        ):
            raise AssessmentBoundaryError("access_denied")
        value = json.load(stream)
    if not isinstance(value, dict):
        raise ValueError("Invalid local configuration.")
    return value


class LocalInvestigatorProfile:
    """Trusted local composition only; file ownership is not operational authentication."""

    def __init__(self, path: Path, *, clock: Callable[[], float] = time.time) -> None:
        self.path, self.clock = path, clock
        data = read_private_json(path)
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
        for name in ("evidence_db", "corpus_db", "index_root"):
            if not Path(data[name]).is_absolute():
                raise ValueError("Local source paths must be absolute.")
            setattr(self, name, Path(data[name]))
        self.evidence_db: Path
        self.corpus_db: Path
        self.index_root: Path
        # Identity, source paths and grants cannot be swapped during a composed operation.
        self._identity = {
            k: data[k]
            for k in (
                "principal_id",
                "evidence_scope",
                "knowledge_scope",
                "evidence_db",
                "corpus_db",
                "index_root",
                "source_investigation_id",
                "clearance",
            )
        }
        self.current()

    def current(self) -> dict[str, Any]:
        data = read_private_json(self.path)
        if (
            data.get("schema_version") != PROFILE_VERSION
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

    def source_content(self) -> dict[str, tuple[str, str, SourceKind]]:
        at = datetime.fromtimestamp(self.clock(), UTC)
        with SQLiteInvestigationStore(self.evidence_db, read_only=True) as store:
            job = store.get_investigation(
                self.source_investigation_id, access_scope=self.evidence.access_scope
            )
            self.check_job(job)
            snapshot = store.get_snapshot(
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
        index = load_index(self.index_root)
        with SQLiteCorpusStore(self.corpus_db, read_only=True) as corpus:
            chunks = corpus.read_chunks(
                context=self.knowledge, at=at, generation_id=index.corpus_generation_id
            )
        for chunk in chunks:
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
