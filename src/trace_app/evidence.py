"""Source-neutral operational evidence envelope and validation."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal

EVIDENCE_SCHEMA_VERSION = "1"


def format_utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("Evidence timestamps must be timezone-aware UTC.")
    return value.isoformat().replace("+00:00", "Z")


def _parse_utc(value: str) -> datetime:
    if not isinstance(value, str) or not re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?Z",
        value,
    ):
        raise ValueError("Evidence timestamps must use RFC 3339 UTC with Z.")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as error:
        raise ValueError("Evidence timestamps must use RFC 3339 UTC with Z.") from error
    if parsed.utcoffset() != timedelta(0):
        raise ValueError("Evidence timestamps must use RFC 3339 UTC with Z.")
    return parsed


@dataclass(frozen=True, slots=True)
class EvidenceRecord:
    """Source-neutral operational record; no evaluator fields are stored here."""

    evidence_id: str
    service: str
    environment: str
    observed_at: str
    collected_at: str
    source_record_id: str
    source_revision: str
    access_classification: str
    redaction_status: str
    correlation_id: str
    event: str
    integrity_sha256: str

    def __post_init__(self) -> None:
        for field in (
            self.evidence_id,
            self.service,
            self.environment,
            self.source_record_id,
            self.source_revision,
            self.access_classification,
            self.redaction_status,
            self.correlation_id,
            self.event,
        ):
            if not isinstance(field, str) or not field:
                raise ValueError(
                    "Evidence identity and provenance fields are required."
                )
        _parse_utc(self.observed_at)
        _parse_utc(self.collected_at)
        if not re.fullmatch(r"[0-9a-f]{64}", self.integrity_sha256):
            raise ValueError("Evidence integrity_sha256 must be a SHA-256 hex digest.")

    def to_dict(self) -> dict[str, str]:
        return {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "evidence_id": self.evidence_id,
            "service": self.service,
            "environment": self.environment,
            "observed_at": self.observed_at,
            "collected_at": self.collected_at,
            "source_record_id": self.source_record_id,
            "source_revision": self.source_revision,
            "access_classification": self.access_classification,
            "redaction_status": self.redaction_status,
            "correlation_id": self.correlation_id,
            "event": self.event,
            "integrity_sha256": self.integrity_sha256,
        }


@dataclass(frozen=True, slots=True)
class SourceAvailability:
    source: str
    status: Literal["available", "unavailable", "truncated"]
    reason: str | None = None

    def __post_init__(self) -> None:
        if not self.source or self.status not in (
            "available",
            "unavailable",
            "truncated",
        ):
            raise ValueError("Source availability requires a source and valid status.")
        if self.status != "available" and not self.reason:
            raise ValueError("Unavailable or truncated source requires a reason.")

    def to_dict(self) -> dict[str, str | None]:
        return {"source": self.source, "status": self.status, "reason": self.reason}


@dataclass(frozen=True, slots=True)
class EvidenceBundle:
    """The only export surface for this replay's investigator-facing evidence."""

    records: tuple[EvidenceRecord, ...]
    window_start: str
    window_end: str
    sources: tuple[SourceAvailability, ...]

    def __post_init__(self) -> None:
        start = _parse_utc(self.window_start)
        end = _parse_utc(self.window_end)
        if start > end:
            raise ValueError("Evidence query window start must not exceed end.")
        if len({record.evidence_id for record in self.records}) != len(self.records):
            raise ValueError("Evidence IDs must be unique within a bundle.")
        if any(
            not start <= _parse_utc(record.observed_at) <= end
            for record in self.records
        ):
            raise ValueError("Evidence observed_at falls outside the query window.")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": EVIDENCE_SCHEMA_VERSION,
            "query_window": {
                "start": self.window_start,
                "end": self.window_end,
            },
            "sources": [source.to_dict() for source in self.sources],
            "records": [record.to_dict() for record in self.records],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    def timeline(self) -> tuple[EvidenceRecord, ...]:
        return tuple(
            sorted(self.records, key=lambda item: (item.observed_at, item.evidence_id))
        )
