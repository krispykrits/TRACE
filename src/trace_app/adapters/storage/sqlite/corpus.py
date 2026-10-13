"""Atomic SQLite corpus generations with current policy checks on every read."""

from __future__ import annotations

import logging
import os
import sqlite3
import stat
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator, Literal

from trace_app.evidence.models import _parse_utc, format_utc
from trace_app.knowledge.generations import CorpusGeneration
from trace_app.knowledge.models import (
    CHUNKER_VERSION,
    CorpusAccessError,
    CorpusConflictError,
    CorpusDependencyError,
    CorpusInputError,
    DocumentMetadata,
    KnowledgeChunk,
    _text,
    canonical,
    chunk_document,
    digest,
    parse_json,
)
from trace_app.knowledge.models import CorpusReadContext as CorpusReadContext
from trace_app.knowledge.sources import CorpusBatch, CorpusSource

_LOG = logging.getLogger("trace_app.corpus")
_SCHEMA = (
    "CREATE TABLE generations (id TEXT PRIMARY KEY, manifest TEXT NOT NULL)",
    """CREATE TABLE chunks (generation_id TEXT REFERENCES generations(id) ON DELETE CASCADE,
        chunk_id TEXT NOT NULL, document_id TEXT NOT NULL, payload TEXT NOT NULL,
        PRIMARY KEY(generation_id, chunk_id))""",
    """CREATE TABLE sources (document_id TEXT PRIMARY KEY, metadata TEXT NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('active','deleted','revoked')), withdrawn_at TEXT)""",
    """CREATE TABLE revisions (document_id TEXT NOT NULL, source_revision TEXT NOT NULL,
        content_sha256 TEXT NOT NULL, PRIMARY KEY(document_id, source_revision))""",
    """CREATE TABLE versions (document_id TEXT NOT NULL, version TEXT NOT NULL,
        fingerprint TEXT NOT NULL, PRIMARY KEY(document_id, version))""",
    "CREATE TABLE current_generation (singleton INTEGER PRIMARY KEY CHECK(singleton=1), id TEXT NOT NULL)",
    "CREATE INDEX chunks_document ON chunks(document_id)",
)


def _at(value: datetime) -> str:
    # Preserve microseconds: expiry checks compare parsed UTC instants, not strings.
    format_utc(value)
    return value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


class SQLiteCorpusStore:
    """Trusted local publisher plus scoped read adapter; no investigator mutations."""

    def __init__(self, path: Path, *, read_only: bool = False) -> None:
        if type(read_only) is not bool:
            raise CorpusInputError("read_only requires a boolean.")
        self._read_only = read_only
        if path.is_symlink() or not path.parent.is_dir():
            raise CorpusInputError(
                "Corpus database requires a nonsymlink path and existing parent."
            )
        if path.exists():
            mode = path.stat().st_mode
            if not stat.S_ISREG(mode) or mode & 0o077:
                raise CorpusInputError(
                    "Corpus database must be a private regular file."
                )
        else:
            if read_only:
                raise CorpusInputError("Read-only corpus database must exist.")
            descriptor = os.open(
                path, os.O_CREAT | os.O_EXCL | os.O_RDWR | os.O_NOFOLLOW, 0o600
            )
            os.close(descriptor)
        try:
            target = path.resolve().as_uri() + "?mode=ro" if read_only else str(path)
            self._connection = sqlite3.connect(
                target, uri=read_only, isolation_level=None
            )
            self._connection.row_factory = sqlite3.Row
            self._connection.execute("PRAGMA foreign_keys=ON")
            if read_only:
                self._connection.execute("PRAGMA query_only=ON")
            else:
                self._connection.execute("PRAGMA secure_delete=ON")
            version = self._connection.execute("PRAGMA user_version").fetchone()[0]
            tables = {
                row["name"]
                for row in self._connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            required = {
                "generations",
                "chunks",
                "sources",
                "revisions",
                "versions",
                "current_generation",
            }
            if (version == 0 and tables) or (version == 1 and tables != required):
                raise CorpusDependencyError(
                    "Database is not the expected corpus schema."
                )
            if read_only:
                if version != 1:
                    raise CorpusDependencyError(
                        "Read-only corpus schema is incompatible."
                    )
                return
            with self._transaction():
                if version == 0:
                    for statement in _SCHEMA:
                        self._connection.execute(statement)
                    self._connection.execute("PRAGMA user_version=1")
                elif version != 1:
                    raise CorpusDependencyError("Unsupported corpus database schema.")
        except (sqlite3.Error, CorpusDependencyError) as error:
            if hasattr(self, "_connection"):
                self._connection.close()
            raise CorpusDependencyError("Corpus database setup failed.") from error

    def __enter__(self) -> SQLiteCorpusStore:
        return self

    def __exit__(self, *args: object) -> None:
        self._connection.close()

    @contextmanager
    def _transaction(self) -> Iterator[None]:
        try:
            self._connection.execute("BEGIN" if self._read_only else "BEGIN IMMEDIATE")
            yield
            self._connection.execute("COMMIT")
        except BaseException as error:
            try:
                if self._connection.in_transaction:
                    self._connection.execute("ROLLBACK")
            except sqlite3.Error:
                pass  # Preserve the original failure when the connection itself failed.
            if isinstance(error, sqlite3.Error):
                raise CorpusDependencyError(
                    "Corpus storage operation failed."
                ) from error
            raise

    def ingest(
        self, source: CorpusSource, *, at: datetime, retain_until: str
    ) -> tuple[CorpusGeneration, bool]:
        """Publish a fully validated generation and its policies in one transaction."""
        batch: CorpusBatch = source.load()
        at_text = _at(at)
        if _parse_utc(retain_until) <= at:
            raise CorpusInputError("retain_until must follow ingestion time.")
        docs = sorted(batch.documents, key=lambda doc: doc.metadata.document_id)
        if any(_parse_utc(doc.metadata.verified_at) > at for doc in docs):
            raise CorpusInputError("Source verification must not be in the future.")
        if any(_parse_utc(doc.metadata.fresh_until) <= at for doc in docs):
            raise CorpusInputError("Source verification is stale.")
        chunks = tuple(chunk for doc in docs for chunk in chunk_document(doc))
        if len(chunks) > 10_000:
            raise CorpusInputError("Corpus generation exceeds the chunk bound.")
        fingerprint = digest(
            canonical(
                {
                    "corpus_version": batch.corpus_version,
                    "chunker_version": CHUNKER_VERSION,
                    "documents": [doc.fingerprint() for doc in docs],
                }
            )
        )
        generation_id = "gen-" + digest(canonical([fingerprint, retain_until]))
        generation = CorpusGeneration(
            generation_id,
            "1",
            batch.corpus_version,
            CHUNKER_VERSION,
            fingerprint,
            at_text,
            retain_until,
            len(docs),
            len(chunks),
        )
        with self._transaction():
            for doc in docs:
                metadata = doc.metadata
                current = self._connection.execute(
                    "SELECT * FROM sources WHERE document_id=?", (metadata.document_id,)
                ).fetchone()
                if current is not None:
                    prior = DocumentMetadata.from_dict(parse_json(current["metadata"]))
                    if current["status"] != "active":
                        raise CorpusConflictError(
                            "Withdrawn documents require an explicit future restoration policy."
                        )
                    if (prior.source_uri, prior.source_record_id) != (
                        metadata.source_uri,
                        metadata.source_record_id,
                    ):
                        raise CorpusConflictError(
                            "Document source identity cannot be reassigned."
                        )
                    if _parse_utc(metadata.verified_at) < _parse_utc(prior.verified_at):
                        raise CorpusConflictError(
                            "Stale source updates cannot roll back current policy."
                        )
                for row in self._connection.execute(
                    "SELECT metadata FROM sources WHERE document_id<>?",
                    (metadata.document_id,),
                ):
                    other = DocumentMetadata.from_dict(parse_json(row["metadata"]))
                    if (other.source_uri, other.source_record_id) == (
                        metadata.source_uri,
                        metadata.source_record_id,
                    ):
                        raise CorpusConflictError(
                            "Source record is already assigned to another document."
                        )
                revision = self._connection.execute(
                    "SELECT * FROM revisions WHERE document_id=? AND source_revision=?",
                    (metadata.document_id, metadata.source_revision),
                ).fetchone()
                version = self._connection.execute(
                    "SELECT * FROM versions WHERE document_id=? AND version=?",
                    (metadata.document_id, metadata.version),
                ).fetchone()
                if revision and revision["content_sha256"] != digest(doc.body):
                    raise CorpusConflictError(
                        "Source revision has conflicting original content."
                    )
                if version and version["fingerprint"] != doc.fingerprint():
                    raise CorpusConflictError(
                        "Document version has conflicting content/policy."
                    )
                if current is not None:
                    if (version and metadata.version != prior.version) or (
                        revision and metadata.source_revision != prior.source_revision
                    ):
                        raise CorpusConflictError(
                            "Superseded source/version cannot roll back current policy."
                        )
                self._connection.execute(
                    "INSERT OR IGNORE INTO revisions VALUES (?,?,?)",
                    (
                        metadata.document_id,
                        metadata.source_revision,
                        digest(doc.body),
                    ),
                )
                self._connection.execute(
                    "INSERT OR IGNORE INTO versions VALUES (?,?,?)",
                    (metadata.document_id, metadata.version, doc.fingerprint()),
                )
                self._connection.execute(
                    "INSERT INTO sources VALUES (?,?,'active',NULL) ON CONFLICT(document_id) DO UPDATE SET metadata=excluded.metadata",
                    (metadata.document_id, canonical(metadata.to_dict())),
                )
            existing = self._connection.execute(
                "SELECT manifest FROM generations WHERE id=?", (generation_id,)
            ).fetchone()
            if existing:
                generation = CorpusGeneration.from_dict(
                    parse_json(existing["manifest"])
                )
            else:
                self._connection.execute(
                    "INSERT INTO generations VALUES (?,?)",
                    (generation_id, canonical(generation.to_dict())),
                )
                self._connection.executemany(
                    "INSERT INTO chunks VALUES (?,?,?,?)",
                    (
                        (
                            generation_id,
                            chunk.chunk_id,
                            chunk.metadata.document_id,
                            canonical(chunk.to_dict()),
                        )
                        for chunk in chunks
                    ),
                )
            self._connection.execute(
                "INSERT INTO current_generation VALUES (1,?) ON CONFLICT(singleton) DO UPDATE SET id=excluded.id",
                (generation_id,),
            )
        _LOG.info(
            "Corpus generation published.",
            extra={
                "event": "corpus.ingested",
                "generation_id": generation_id,
                "document_count": len(docs),
                "chunk_count": len(chunks),
                "reused": bool(existing),
            },
        )
        return generation, not bool(existing)

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
        """Apply original AND current grants/freshness, even to an old generation."""
        _at(at)
        try:
            # One read snapshot prevents publication/revocation between policy and content reads.
            with self._transaction():
                if generation_id is None:
                    pointer = self._connection.execute(
                        "SELECT id FROM current_generation WHERE singleton=1"
                    ).fetchone()
                    generation_id = pointer["id"] if pointer else None
                row = self._connection.execute(
                    "SELECT manifest FROM generations WHERE id=?", (generation_id,)
                ).fetchone()
                if row is None:
                    raise CorpusAccessError(
                        "Corpus generation is absent or unavailable."
                    )
                manifest = parse_json(row["manifest"])
                generation = CorpusGeneration.from_dict(manifest)
                if (
                    not _parse_utc(generation.created_at)
                    <= at
                    < _parse_utc(generation.retain_until)
                ):
                    raise CorpusAccessError(
                        "Corpus generation is absent or unavailable."
                    )
                result = []
                rows = self._connection.execute(
                    """SELECT c.payload,s.metadata,s.status FROM chunks c
                    JOIN sources s ON c.document_id=s.document_id WHERE c.generation_id=?
                    ORDER BY c.document_id,c.chunk_id""",
                    (generation_id,),
                )
                for entry in rows:
                    current = DocumentMetadata.from_dict(parse_json(entry["metadata"]))
                    if entry["status"] != "active" or not self._permitted(
                        current, context, at
                    ):
                        continue
                    chunk = KnowledgeChunk.from_dict(parse_json(entry["payload"]))
                    if self._permitted(chunk.metadata, context, at):
                        result.append(chunk)
                return tuple(
                    sorted(result, key=lambda c: (c.metadata.document_id, c.ordinal))
                )
        except (sqlite3.Error, ValueError, TypeError) as error:
            raise CorpusDependencyError(
                "Corpus generation validation/read failed."
            ) from error

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
        raise CorpusAccessError(
            "Chunk is absent or outside current access/freshness policy."
        )

    def withdraw(
        self, document_id: str, *, reason: Literal["deleted", "revoked"], at: datetime
    ) -> None:
        """Trusted source-owner administration; sticky across retained generations."""
        _text(document_id, "document_id")
        at_text = _at(at)
        if reason not in ("deleted", "revoked"):
            raise CorpusInputError("Withdrawal reason is invalid.")
        with self._transaction():
            row = self._connection.execute(
                "SELECT status FROM sources WHERE document_id=?", (document_id,)
            ).fetchone()
            if row is None:
                raise CorpusAccessError("Document is absent.")
            # Deletion cannot later be downgraded to a retained revocation.
            if row["status"] == "deleted":
                reason = "deleted"
            self._connection.execute(
                "UPDATE sources SET status=?,withdrawn_at=? WHERE document_id=?",
                (reason, at_text, document_id),
            )
            if reason == "deleted":
                self._connection.execute(
                    "DELETE FROM chunks WHERE document_id=?", (document_id,)
                )
        _LOG.info(
            "Corpus source withdrawn.",
            extra={"event": "corpus.withdrawn", "withdrawal_reason": reason},
        )

    def purge_expired(self, *, at: datetime) -> int:
        _at(at)
        with self._transaction():
            expired = []
            for row in self._connection.execute("SELECT id,manifest FROM generations"):
                generation = CorpusGeneration.from_dict(parse_json(row["manifest"]))
                if at >= _parse_utc(generation.retain_until):
                    expired.append(row["id"])
            self._connection.executemany(
                "DELETE FROM generations WHERE id=?", ((value,) for value in expired)
            )
            self._connection.execute(
                "DELETE FROM current_generation WHERE id NOT IN (SELECT id FROM generations)"
            )
        _LOG.info(
            "Expired corpus generations purged.",
            extra={
                "event": "corpus.retention.purged",
                "generation_count": len(expired),
            },
        )
        return len(expired)
