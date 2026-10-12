"""Source adapter seam and bounded curated-file ingestion; no source fetching."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Protocol

from trace_app.knowledge import (
    CORPUS_SCHEMA_VERSION,
    CorpusInputError,
    DocumentMetadata,
    KnowledgeDocument,
    _object,
    _text,
    digest,
    parse_json,
)


@dataclass(frozen=True, slots=True)
class CorpusBatch:
    corpus_version: str
    documents: tuple[KnowledgeDocument, ...]

    def __post_init__(self) -> None:
        _text(self.corpus_version, "corpus_version")
        if not isinstance(self.documents, tuple) or not 1 <= len(self.documents) <= 100:
            raise CorpusInputError("Corpus requires 1–100 documents.")
        if any(not isinstance(doc, KnowledgeDocument) for doc in self.documents):
            raise CorpusInputError("Corpus requires validated documents.")
        ids = [doc.metadata.document_id for doc in self.documents]
        sources = [
            (doc.metadata.source_uri, doc.metadata.source_record_id)
            for doc in self.documents
        ]
        if len(set(ids)) != len(ids) or len(set(sources)) != len(sources):
            raise CorpusInputError("Duplicate document or source record identities.")


class CorpusSource(Protocol):
    """Trusted adapters supply curated content plus source-owned opaque revisions."""

    def load(self) -> CorpusBatch: ...


def _read(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise CorpusInputError("Corpus files must be regular files, without symlinks.")
    with path.open("rb") as stream:
        data = stream.read(2_000_001)
    if len(data) > 2_000_000:
        raise CorpusInputError("Corpus file exceeds the byte bound.")
    return data.decode("utf-8")


class CuratedFileSource:
    """Read only explicitly hashed Markdown files under a corpus's documents/ folder."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def load(self) -> CorpusBatch:
        if self.root.is_symlink() or (self.root / "documents").is_symlink():
            raise CorpusInputError("Corpus directories must not be symbolic links.")
        manifest = _object(
            parse_json(_read(self.root / "manifest.json")),
            {"schema_version", "corpus_version", "documents"},
            "corpus manifest",
        )
        if manifest["schema_version"] != CORPUS_SCHEMA_VERSION:
            raise CorpusInputError("Corpus manifest schema is unsupported.")
        entries = manifest["documents"]
        if not isinstance(entries, list) or not 1 <= len(entries) <= 100:
            raise CorpusInputError("Manifest requires 1–100 documents.")
        documents: list[KnowledgeDocument] = []
        paths: set[str] = set()
        for value in entries:
            entry = _object(
                value, {"metadata", "path", "content_sha256"}, "manifest entry"
            )
            path = _text(entry["path"], "path")
            relative = PurePosixPath(path)
            if (
                len(relative.parts) != 2
                or relative.parts[0] != "documents"
                or relative.suffix != ".md"
                or "\\" in path
                or path in paths
                or relative.as_posix() != path
            ):
                raise CorpusInputError(
                    "Only unique documents/*.md paths are permitted."
                )
            paths.add(path)
            body = _read(self.root / path)
            if digest(body) != entry["content_sha256"]:
                raise CorpusInputError("Document hash does not match its manifest.")
            documents.append(
                KnowledgeDocument(DocumentMetadata.from_dict(entry["metadata"]), body)
            )
        return CorpusBatch(
            _text(manifest["corpus_version"], "corpus_version"), tuple(documents)
        )
