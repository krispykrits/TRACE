"""Deterministic observations from bounded authorized evidence; no causal inference."""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass

from trace_app.evidence import SourceAvailability, _parse_utc
from trace_app.evidence_queries import (
    EvidenceQuery,
    EvidenceQueryService,
    QueryStatus,
    TrustedQueryContext,
)
from trace_app.investigation_state import (
    EvidenceEntry,
    StoreAccessError,
    StoreConflictError,
    StoreInputError,
)

TIMELINE_SCHEMA_VERSION = "1"
_LOG = logging.getLogger("trace_app.timeline")


def order_evidence(entries: tuple[EvidenceEntry, ...]) -> tuple[EvidenceEntry, ...]:
    """Reject duplicate identities within an input batch, as snapshots do."""
    evidence_ids: set[str] = set()
    source_keys: set[tuple[str, str]] = set()
    for entry in entries:
        record = entry.record
        source_key = (record.source_record_id, record.source_revision)
        if record.evidence_id in evidence_ids:
            raise StoreInputError("evidence_id must be unique in a timeline input.")
        if source_key in source_keys:
            raise StoreInputError("source_record_id/source_revision must be unique.")
        evidence_ids.add(record.evidence_id)
        source_keys.add(source_key)
    return tuple(
        sorted(
            entries,
            key=lambda entry: (
                _parse_utc(entry.record.observed_at),
                entry.record.evidence_id,
            ),
        )
    )


@dataclass(frozen=True, slots=True)
class IncidentTimeline:
    """Saved observations are not current authorization to read their citations."""

    investigation_id: str
    query: EvidenceQuery
    status: QueryStatus
    events: tuple[EvidenceEntry, ...]
    sources: tuple[SourceAvailability, ...]
    matching_count: int
    truncated: bool
    failure_code: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": TIMELINE_SCHEMA_VERSION,
            "investigation_id": self.investigation_id,
            "query": asdict(self.query),
            "status": self.status,
            "matching_count": self.matching_count,
            "truncated": self.truncated,
            "failure_code": self.failure_code,
            "sources": [source.to_dict() for source in self.sources],
            "events": [
                {
                    "causal_status": "observed",
                    "evidence_id": entry.record.evidence_id,
                    "kind": entry.kind,
                    "record": entry.record.to_dict(),
                    "payload": asdict(entry.payload),
                }
                for entry in self.events
            ],
        }


class TimelineService:
    """Build and resolve timelines through the same scoped read boundary."""

    def __init__(self, evidence: EvidenceQueryService) -> None:
        self._evidence = evidence

    def build(
        self,
        investigation_id: str,
        query: EvidenceQuery,
        *,
        context: TrustedQueryContext,
    ) -> IncidentTimeline:
        result = self._evidence.query(investigation_id, query, context=context)
        timeline = IncidentTimeline(
            investigation_id=investigation_id,
            query=query,
            status=result.status,
            events=order_evidence(result.entries),
            sources=result.sources,
            matching_count=result.matching_count,
            truncated=result.truncated,
            failure_code=result.failure_code,
        )
        _LOG.info(
            "Incident timeline constructed.",
            extra={
                "event": "timeline.constructed",
                "investigation_id": investigation_id,
                "status": timeline.status,
                "returned_count": len(timeline.events),
                "truncated": timeline.truncated,
            },
        )
        return timeline

    def resolve(
        self,
        timeline: IncidentTimeline,
        evidence_id: str,
        *,
        context: TrustedQueryContext,
    ) -> EvidenceEntry:
        """Recheck scope and current evidence; a saved ID cannot grant access."""
        event = next(
            (
                entry
                for entry in timeline.events
                if entry.record.evidence_id == evidence_id
            ),
            None,
        )
        if event is None:
            raise StoreAccessError("Evidence is absent from the timeline.")
        current = self._evidence.get_by_id(
            timeline.investigation_id, evidence_id, timeline.query, context=context
        )
        if current != event:
            raise StoreConflictError(
                "Timeline citation no longer matches source evidence."
            )
        return current
