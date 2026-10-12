"""Immutable corpus-generation contract, independent of storage."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import cast

from trace_app.evidence.models import _parse_utc
from trace_app.knowledge.models import CHUNKER_VERSION, CorpusInputError, _object, _text


@dataclass(frozen=True, slots=True)
class CorpusGeneration:
    generation_id: str
    schema_version: str
    corpus_version: str
    chunker_version: str
    corpus_sha256: str
    created_at: str
    retain_until: str
    document_count: int
    chunk_count: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: object) -> CorpusGeneration:
        data = _object(value, set(cls.__dataclass_fields__), "generation")
        if data["schema_version"] != "1" or data["chunker_version"] != CHUNKER_VERSION:
            raise CorpusInputError("Generation schema/chunker is incompatible.")
        if not isinstance(data["generation_id"], str) or not re.fullmatch(
            r"gen-[0-9a-f]{64}", data["generation_id"]
        ):
            raise CorpusInputError("Generation ID is invalid.")
        if not isinstance(data["corpus_sha256"], str) or not re.fullmatch(
            r"[0-9a-f]{64}", data["corpus_sha256"]
        ):
            raise CorpusInputError("Generation fingerprint is invalid.")
        _text(data["corpus_version"], "corpus_version")
        for name in ("document_count", "chunk_count"):
            if type(data[name]) is not int or not 1 <= cast(int, data[name]) <= 10_000:
                raise CorpusInputError("Generation counts are invalid.")
        if _parse_utc(_text(data["retain_until"], "retain_until")) <= _parse_utc(
            _text(data["created_at"], "created_at")
        ):
            raise CorpusInputError("Generation retention interval is invalid.")
        return cls(**cast(dict, data))
