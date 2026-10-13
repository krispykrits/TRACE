"""TRACE-owned knowledge provenance and Volume 4 adapted section chunking."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from typing import Literal, cast
from urllib.parse import urlsplit

from trace_app.evidence.models import _parse_utc

CORPUS_SCHEMA_VERSION = "1"
CHUNKER_VERSION = "section-words.v1"
MAX_WORDS = 128
OVERLAP_WORDS = 16
MAX_CHUNK_CHARS = 4_096


class CorpusInputError(ValueError):
    """Invalid corpus input; messages name fields without echoing content."""


class CorpusConflictError(RuntimeError):
    """Stable source identity or revision conflicts with prior ingestion."""


class CorpusAccessError(PermissionError):
    """Absent, expired, withdrawn or unauthorized knowledge reference."""


class CorpusDependencyError(RuntimeError):
    """Corpus storage is unavailable or incompatible."""


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _text(value: object, field: str, limit: int = 200) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > limit
        or any(ord(char) < 32 for char in value)
    ):
        raise CorpusInputError(f"{field} requires bounded nonblank text.")
    return value


def _object(value: object, fields: set[str], name: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != fields:
        raise CorpusInputError(f"{name} has missing or forbidden fields.")
    return value


def parse_json(text: str) -> object:
    def pairs(values: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in values:
            if key in result:
                raise CorpusInputError("Duplicate JSON fields are forbidden.")
            result[key] = value
        return result

    def constant(value: str) -> object:
        raise CorpusInputError("Nonfinite JSON values are forbidden.")

    return json.loads(text, object_pairs_hook=pairs, parse_constant=constant)


@dataclass(frozen=True, slots=True)
class DocumentMetadata:
    document_id: str
    document_type: str
    title: str
    service: str
    environment: str
    source_uri: str
    source_record_id: str
    source_revision: str
    version: str
    provenance: str
    access_scope: str
    access_classification: str
    evaluation_role: str
    answer_bearing: bool
    valid_from: str
    valid_until: str | None
    verified_at: str
    fresh_until: str

    def __post_init__(self) -> None:
        for field in (
            "document_id",
            "title",
            "service",
            "source_record_id",
            "source_revision",
            "version",
            "provenance",
            "access_scope",
        ):
            _text(getattr(self, field), field)
        if self.document_type not in (
            "runbook",
            "service",
            "incident",
            "postmortem",
            "architecture",
            "troubleshooting",
        ):
            raise CorpusInputError("document_type is unsupported.")
        if self.environment not in ("test", "development", "production"):
            raise CorpusInputError("environment is unsupported.")
        if self.access_classification not in ("synthetic_public", "restricted"):
            raise CorpusInputError("access_classification is unsupported.")
        uri = urlsplit(_text(self.source_uri, "source_uri", 1_000))
        if (
            uri.scheme not in ("synthetic", "https", "s3")
            or not uri.netloc
            or uri.username
            or uri.password
            or uri.query
            or uri.fragment
            or any(char.isspace() for char in self.source_uri)
        ):
            raise CorpusInputError("source_uri requires a credential-free source link.")
        if (
            self.access_classification == "synthetic_public"
            and uri.scheme != "synthetic"
        ):
            raise CorpusInputError("Real source identities require restricted access.")
        if self.evaluation_role not in ("development_reference", "shared_reference"):
            raise CorpusInputError("Held-out or evaluator-only content is forbidden.")
        if type(self.answer_bearing) is not bool:
            raise CorpusInputError("answer_bearing requires a boolean.")
        if self.answer_bearing and self.evaluation_role != "development_reference":
            raise CorpusInputError(
                "Answer-bearing content requires development isolation."
            )
        start = _parse_utc(self.valid_from)
        if self.valid_until is not None and _parse_utc(self.valid_until) <= start:
            raise CorpusInputError("valid_until must follow valid_from.")
        if _parse_utc(self.fresh_until) <= _parse_utc(self.verified_at):
            raise CorpusInputError("fresh_until must follow verified_at.")

    @classmethod
    def from_dict(cls, value: object) -> DocumentMetadata:
        data = _object(value, set(cls.__dataclass_fields__), "document metadata")
        return cls(**cast(dict, data))

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class KnowledgeDocument:
    metadata: DocumentMetadata
    body: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.metadata, DocumentMetadata)
            or not isinstance(self.body, str)
            or not self.body.strip()
            or len(self.body) > 32_000
            or "\x00" in self.body
        ):
            raise CorpusInputError(
                "Document requires metadata and bounded original text."
            )
        # Defense in depth for known evaluator payloads; semantic exclusion is curated.
        if re.search(
            r"\b(ground_truth|incident_label|cause_label|expected_assessment)\b",
            self.body,
            re.IGNORECASE,
        ):
            raise CorpusInputError(
                "Evaluator label markers are forbidden in corpus text."
            )

    def fingerprint(self) -> str:
        return digest(
            canonical({"metadata": self.metadata.to_dict(), "body": self.body})
        )


@dataclass(frozen=True, slots=True)
class KnowledgeChunk:
    chunk_id: str
    metadata: DocumentMetadata
    document_sha256: str
    section: str
    ordinal: int
    start_offset: int
    end_offset: int
    text: str
    normalized_text: str
    content_role: str = "untrusted_source_data"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: object) -> KnowledgeChunk:
        data = _object(value, set(cls.__dataclass_fields__), "chunk")
        metadata = DocumentMetadata.from_dict(data["metadata"])
        integers = (data["ordinal"], data["start_offset"], data["end_offset"])
        if any(type(value) is not int or value < 0 for value in integers):
            raise CorpusInputError(
                "Chunk offsets/ordinal require nonnegative integers."
            )
        text = data["text"]
        if (
            not isinstance(text, str)
            or not text.strip()
            or len(text) > MAX_CHUNK_CHARS
            or cast(int, data["end_offset"]) - cast(int, data["start_offset"])
            != len(text)
            or data["normalized_text"] != normalize(text)
            or data["content_role"] != "untrusted_source_data"
        ):
            raise CorpusInputError("Chunk text, offsets or content role is invalid.")
        section = _text(data["section"], "section", MAX_CHUNK_CHARS)
        document_hash = data["document_sha256"]
        if not isinstance(document_hash, str) or not re.fullmatch(
            r"[0-9a-f]{64}", document_hash
        ):
            raise CorpusInputError("document_sha256 is invalid.")
        expected_id = _chunk_id(
            metadata,
            document_hash,
            section,
            *cast(tuple[int, int, int], integers),
            text,
        )
        if data["chunk_id"] != expected_id:
            raise CorpusInputError("Chunk identity does not match its provenance.")
        return cls(**{**cast(dict, data), "metadata": metadata})


def normalize(text: str) -> str:
    """Volume 4 whitespace normalization; original text/offsets remain untouched."""
    return re.sub(r"\s+", " ", text).strip()


def _chunk_id(
    metadata: DocumentMetadata,
    document_hash: str,
    section: str,
    ordinal: int,
    start: int,
    end: int,
    text: str,
) -> str:
    return "chunk-" + digest(
        canonical(
            {
                "metadata": metadata.to_dict(),
                "document_sha256": document_hash,
                "chunker": CHUNKER_VERSION,
                "section": section,
                "ordinal": ordinal,
                "start": start,
                "end": end,
                "text": text,
            }
        )
    )


def chunk_document(document: KnowledgeDocument) -> tuple[KnowledgeChunk, ...]:
    """Adapt Volume 4 section spans and overlapping offset windows, without an encoder."""
    original = document.body
    headings = list(re.finditer(r"^#{1,6} +(.+)$", original, re.MULTILINE))
    spans: list[tuple[str, int, int]] = []
    if not headings:
        spans.append(("Document", 0, len(original)))
    else:
        if original[: headings[0].start()].strip():
            spans.append(("Preamble", 0, headings[0].start()))
        for index, heading in enumerate(headings):
            end = (
                headings[index + 1].start()
                if index + 1 < len(headings)
                else len(original)
            )
            spans.append((normalize(heading.group(1)), heading.start(), end))
    chunks: list[KnowledgeChunk] = []
    document_hash = digest(original)
    for section, start, end in spans:
        offsets = [
            (match.start(), match.end())
            for match in re.finditer(r"\S+", original[start:end])
        ]
        lo = 0
        while lo < len(offsets):
            hi = min(lo + MAX_WORDS, len(offsets))
            a = start if lo == 0 else start + offsets[lo][0]
            b = end if hi == len(offsets) else start + offsets[hi - 1][1]
            while b - a > MAX_CHUNK_CHARS and hi > lo:
                hi -= 1
                b = start + offsets[hi - 1][1] if hi > lo else a
            if hi == lo:
                raise CorpusInputError("Source word exceeds the chunk character bound.")
            passage = original[a:b]
            ordinal = len(chunks)
            chunks.append(
                KnowledgeChunk(
                    _chunk_id(
                        document.metadata,
                        document_hash,
                        section,
                        ordinal,
                        a,
                        b,
                        passage,
                    ),
                    document.metadata,
                    document_hash,
                    section,
                    ordinal,
                    a,
                    b,
                    passage,
                    normalize(passage),
                )
            )
            if hi == len(offsets):
                break
            lo = max(lo + 1, hi - OVERLAP_WORDS)
    if not chunks or len(chunks) > 1_000:
        raise CorpusInputError("Document has no chunks or exceeds the chunk bound.")
    return tuple(chunks)


@dataclass(frozen=True, slots=True)
class CorpusReadContext:
    """Trusted grants, never derived from a search filter or document content."""

    access_scope: str
    environment: str
    allowed_services: tuple[str, ...]
    evaluation_role: Literal["development_reference", "shared_reference"]
    valid_at: str

    def __post_init__(self) -> None:
        _text(self.access_scope, "access_scope")
        if self.environment not in ("test", "development", "production"):
            raise CorpusInputError("Context environment is invalid.")
        if self.evaluation_role not in ("development_reference", "shared_reference"):
            raise CorpusInputError("Context evaluation_role is invalid.")
        if (
            not isinstance(self.allowed_services, tuple)
            or not 1 <= len(self.allowed_services) <= 100
            or len(set(self.allowed_services)) != len(self.allowed_services)
        ):
            raise CorpusInputError("Context requires bounded unique service grants.")
        for service in self.allowed_services:
            _text(service, "allowed_services")
        _parse_utc(self.valid_at)
