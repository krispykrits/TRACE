"""Versioned exact-search artifacts: validated JSON, atomic generations, no pickle."""

from __future__ import annotations

import importlib.metadata
import os
import re
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import cast

from trace_app.evidence.models import _parse_utc, format_utc
from trace_app.knowledge.generations import CorpusGeneration
from trace_app.knowledge.index import IndexGeneration, chunk_fingerprint
from trace_app.knowledge.models import (
    CHUNKER_VERSION,
    KnowledgeChunk,
    _object,
    canonical,
    digest,
    parse_json,
)
from trace_app.knowledge.ports import (
    RETRIEVAL_VERSION,
    Encoder,
    EncoderFailure,
    EncoderSpec,
    IndexCompatibilityError,
)
from trace_app.knowledge.vectors import validate_vectors

MAX_INDEX_CHUNKS = 1_000
_MAX_BYTES = 20_000_000


def implementation_versions() -> dict[str, str]:
    return {
        "retriever": RETRIEVAL_VERSION,
        "chunker": CHUNKER_VERSION,
        **{
            name: importlib.metadata.version(name)
            for name in ("numpy", "scikit-learn", "scipy")
        },
    }


def _write(path: Path, text: str) -> None:
    with os.fdopen(
        os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600), "w"
    ) as stream:
        stream.write(text + "\n")


def _read(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise IndexCompatibilityError(
            "Index artifact is missing or a symbolic link; rebuild."
        )
    with path.open("rb") as stream:
        data = stream.read(_MAX_BYTES + 1)
    if len(data) > _MAX_BYTES:
        raise IndexCompatibilityError("Index artifact exceeds its byte bound; rebuild.")
    return data.decode("utf-8")


def _spec(value: object) -> EncoderSpec | None:
    if value is None:
        return None
    data = dict(
        _object(
            value,
            {
                "model_id",
                "revision",
                "dimension",
                "max_sequence_length",
                "provider",
                "packages",
                "normalized",
                "dtype",
            },
            "embedding",
        )
    )
    if (
        data.pop("normalized") is not True
        or data.pop("dtype") != "float32"
        or not isinstance(data["packages"], dict)
    ):
        raise IndexCompatibilityError(
            "Embedding normalization/dtype/configuration is incompatible."
        )
    data["packages"] = tuple(sorted(data["packages"].items()))
    return EncoderSpec(**cast(dict, data))


def _validate(manifest_value: object, records_value: object) -> IndexGeneration:
    manifest = _object(
        manifest_value,
        {
            "schema_version",
            "index_id",
            "corpus_generation_id",
            "corpus_sha256",
            "created_at",
            "retain_until",
            "embedding",
            "versions",
            "records_sha256",
        },
        "index manifest",
    )
    records = _object(
        records_value, {"chunk_ids", "chunk_fingerprints", "vectors"}, "index records"
    )
    if (
        manifest["schema_version"] != "1"
        or manifest["versions"] != implementation_versions()
    ):
        raise IndexCompatibilityError(
            "Index schema or implementation versions differ; rebuild."
        )
    for name, pattern in (
        ("index_id", r"idx-[0-9a-f]{64}"),
        ("corpus_generation_id", r"gen-[0-9a-f]{64}"),
        ("corpus_sha256", r"[0-9a-f]{64}"),
    ):
        if not isinstance(manifest[name], str) or not re.fullmatch(
            pattern, cast(str, manifest[name])
        ):
            raise IndexCompatibilityError("Index generation identity is invalid.")
    created = _parse_utc(cast(str, manifest["created_at"]))
    if _parse_utc(cast(str, manifest["retain_until"])) <= created:
        raise IndexCompatibilityError("Index retention interval is invalid.")
    if manifest["records_sha256"] != digest(canonical(records)):
        raise IndexCompatibilityError("Index records hash differs; rebuild.")
    identity = {
        key: value
        for key, value in manifest.items()
        if key not in ("index_id", "created_at")
    }
    if manifest["index_id"] != "idx-" + digest(canonical(identity)):
        raise IndexCompatibilityError("Index manifest identity differs; rebuild.")
    ids, fingerprints = records["chunk_ids"], records["chunk_fingerprints"]
    if (
        not isinstance(ids, list)
        or len(ids) > MAX_INDEX_CHUNKS
        or len(set(cast(list[str], ids))) != len(ids)
    ):
        raise IndexCompatibilityError("Index chunk count or uniqueness is invalid.")
    if not isinstance(fingerprints, list) or len(fingerprints) != len(ids):
        raise IndexCompatibilityError("Index provenance count is invalid.")
    if any(
        not isinstance(value, str) or not re.fullmatch(r"chunk-[0-9a-f]{64}", value)
        for value in ids
    ):
        raise IndexCompatibilityError("Index chunk IDs are invalid.")
    if any(
        not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value)
        for value in fingerprints
    ):
        raise IndexCompatibilityError("Index provenance hashes are invalid.")
    spec = _spec(manifest["embedding"])
    vectors = (
        validate_vectors(records["vectors"], len(ids), spec.dimension) if spec else None
    )
    if spec is None and records["vectors"] is not None:
        raise IndexCompatibilityError(
            "Lexical-only index must not contain unnamed vectors."
        )
    return IndexGeneration(
        cast(str, manifest["index_id"]),
        cast(str, manifest["corpus_generation_id"]),
        cast(str, manifest["corpus_sha256"]),
        cast(str, manifest["retain_until"]),
        spec,
        tuple(cast(list[str], ids)),
        tuple(cast(list[str], fingerprints)),
        vectors,
    )


def load_index(root: Path, *, encoder: Encoder | None = None) -> IndexGeneration:
    try:
        if root.is_symlink():
            raise IndexCompatibilityError("Index root cannot be a symbolic link.")
        pointer = _read(root / "CURRENT").strip()
        if (
            not re.fullmatch(r"idx-[0-9a-f]{64}", pointer)
            or (root / pointer).is_symlink()
        ):
            raise IndexCompatibilityError("Index pointer is invalid; rebuild.")
        manifest = parse_json(_read(root / pointer / "manifest.json"))
        records = parse_json(_read(root / pointer / "records.json"))
        index = _validate(manifest, records)
        if index.index_id != pointer or (
            encoder is not None and index.embedding != encoder.spec
        ):
            raise IndexCompatibilityError(
                "Index encoder/pointer differs; rebuild with the selected encoder."
            )
        return index
    except IndexCompatibilityError:
        raise
    except (ValueError, TypeError, OSError, EncoderFailure) as error:
        raise IndexCompatibilityError(
            "Index artifacts are invalid or unavailable; rebuild."
        ) from error


def build_index(
    root: Path,
    corpus: CorpusGeneration,
    chunks: tuple[KnowledgeChunk, ...],
    *,
    at: datetime,
    encoder: Encoder | None = None,
) -> IndexGeneration:
    """Trusted publication from already authorized passages; query uses source rechecks."""
    format_utc(at)
    if not _parse_utc(corpus.created_at) <= at < _parse_utc(corpus.retain_until):
        raise IndexCompatibilityError(
            "Corpus generation is outside its publication interval."
        )
    if len(chunks) > MAX_INDEX_CHUNKS or len(
        {chunk.chunk_id for chunk in chunks}
    ) != len(chunks):
        raise IndexCompatibilityError(
            "Index requires unique chunks within the 1,000-chunk bound."
        )
    ordered = tuple(sorted(chunks, key=lambda chunk: chunk.chunk_id))
    vectors = None
    if encoder is not None:
        try:
            values = (
                encoder.encode([chunk.normalized_text for chunk in ordered])
                if ordered
                else ()
            )
            vectors = validate_vectors(values, len(ordered), encoder.spec.dimension)
        except (EncoderFailure, ValueError):
            raise
        except Exception as error:
            raise EncoderFailure("Embedding index publication failed.") from error
    records = {
        "chunk_ids": [chunk.chunk_id for chunk in ordered],
        "chunk_fingerprints": [chunk_fingerprint(chunk) for chunk in ordered],
        "vectors": vectors,
    }
    manifest = {
        "schema_version": "1",
        "corpus_generation_id": corpus.generation_id,
        "corpus_sha256": corpus.corpus_sha256,
        "retain_until": corpus.retain_until,
        "embedding": encoder.spec.to_dict() if encoder else None,
        "versions": implementation_versions(),
        "records_sha256": digest(canonical(records)),
    }
    index_id = "idx-" + digest(canonical(manifest))
    manifest.update(
        {"index_id": index_id, "created_at": at.strftime("%Y-%m-%dT%H:%M:%S.%fZ")}
    )
    index = _validate(manifest, parse_json(canonical(records)))
    if root.is_symlink() or (
        root.exists() and (not root.is_dir() or root.stat().st_mode & 0o077)
    ):
        raise IndexCompatibilityError(
            "Index root must be a private directory without symlinks."
        )
    root.mkdir(mode=0o700, exist_ok=True)
    stage = root / (".staging-" + uuid.uuid4().hex)
    stage.mkdir(mode=0o700)
    temporary_pointer = root / (".CURRENT-" + uuid.uuid4().hex)
    try:
        _write(stage / "records.json", canonical(records))
        _write(stage / "manifest.json", canonical(manifest))
        # Validate complete serialized records before making the generation visible.
        _validate(
            parse_json(_read(stage / "manifest.json")),
            parse_json(_read(stage / "records.json")),
        )
        destination = root / index_id
        if destination.exists():
            if destination.is_symlink():
                raise IndexCompatibilityError("Existing generation is a symbolic link.")
            existing = _validate(
                parse_json(_read(destination / "manifest.json")),
                parse_json(_read(destination / "records.json")),
            )
            if existing != index:
                raise IndexCompatibilityError(
                    "Existing generation differs; choose a clean rebuild directory."
                )
        else:
            stage.rename(destination)
        _write(temporary_pointer, index_id)
        os.replace(temporary_pointer, root / "CURRENT")
    finally:
        if stage.exists():
            shutil.rmtree(stage)
        if temporary_pointer.exists():
            temporary_pointer.unlink()
    return index
