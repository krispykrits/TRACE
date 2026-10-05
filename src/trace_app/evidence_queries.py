"""Bounded, scope-aware reads of persisted operational evidence."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Literal, Protocol

from trace_app.evidence import SourceAvailability, _parse_utc
from trace_app.investigation_state import (
    EvidenceEntry,
    EvidenceKind,
    EvidenceSnapshot,
    Investigation,
    StoreAccessError,
    StoreDependencyError,
    StoreInputError,
    StoreSchemaError,
    _identifier,
)

QueryStatus = Literal[
    "complete", "empty", "incomplete", "snapshot_missing", "storage_failure"
]
_LOG = logging.getLogger("trace_app.evidence_query")


@dataclass(frozen=True, slots=True)
class TrustedQueryContext:
    """Identity and service grants supplied by a trusted application boundary."""

    access_scope: str
    environment: str
    allowed_services: tuple[str, ...]

    def __post_init__(self) -> None:
        _identifier("access_scope", self.access_scope)
        _identifier("environment", self.environment)
        if not isinstance(self.allowed_services, tuple) or not self.allowed_services:
            raise StoreInputError("allowed_services must be a nonempty tuple.")
        for service in self.allowed_services:
            _identifier("allowed_services", service)
        if len(set(self.allowed_services)) != len(self.allowed_services):
            raise StoreInputError("allowed_services must be unique.")


@dataclass(frozen=True, slots=True)
class EvidenceQuery:
    """Caller-selected narrowing filters; contains no authority or SQL."""

    window_start: str
    window_end: str
    limit: int = 100
    service: str | None = None
    kind: EvidenceKind | None = None

    def __post_init__(self) -> None:
        try:
            start = _parse_utc(self.window_start)
        except ValueError as error:
            raise StoreInputError(f"window_start: {error}") from error
        try:
            end = _parse_utc(self.window_end)
        except ValueError as error:
            raise StoreInputError(f"window_end: {error}") from error
        if start > end:
            raise StoreInputError("window_start must not exceed window_end.")
        if type(self.limit) is not int or self.limit <= 0:
            raise StoreInputError("limit must be a positive integer.")
        if self.service is not None:
            _identifier("service", self.service)
        if self.kind is not None and self.kind not in (
            "log",
            "metric",
            "deployment",
        ):
            raise StoreInputError("kind must be log, metric or deployment.")


@dataclass(frozen=True, slots=True)
class EvidenceQueryResult:
    status: QueryStatus
    entries: tuple[EvidenceEntry, ...]
    sources: tuple[SourceAvailability, ...]
    matching_count: int
    truncated: bool
    failure_code: str | None = None


class EvidenceReader(Protocol):
    def get_investigation(
        self, investigation_id: str, *, access_scope: str
    ) -> Investigation: ...

    def get_snapshot(
        self, investigation_id: str, *, access_scope: str
    ) -> EvidenceSnapshot: ...


class EvidenceQueryService:
    """Read one bounded snapshot with caller identity kept separate from filters."""

    def __init__(
        self,
        reader: EvidenceReader,
        *,
        max_window: timedelta = timedelta(hours=24),
        max_limit: int = 100,
    ) -> None:
        if not isinstance(max_window, timedelta) or max_window <= timedelta(0):
            raise StoreInputError("max_window must be a positive timedelta.")
        if type(max_limit) is not int or max_limit <= 0:
            raise StoreInputError("max_limit must be a positive integer.")
        self._reader = reader
        self.max_window = max_window
        self.max_limit = max_limit

    def _read(
        self,
        investigation_id: str,
        query: EvidenceQuery,
        *,
        context: TrustedQueryContext,
    ) -> EvidenceSnapshot | EvidenceQueryResult:
        _identifier("investigation_id", investigation_id)
        if query.limit > self.max_limit:
            raise StoreInputError("limit exceeds max_limit.")
        start = _parse_utc(query.window_start)
        end = _parse_utc(query.window_end)
        if end - start > self.max_window:
            raise StoreInputError("query window exceeds max_window.")
        if query.service is not None and query.service not in context.allowed_services:
            raise StoreAccessError("Service is outside the caller's access scope.")
        try:
            investigation = self._reader.get_investigation(
                investigation_id, access_scope=context.access_scope
            )
            if investigation.request.environment != context.environment:
                raise StoreAccessError(
                    "Investigation is absent or outside the access scope."
                )
            if start < _parse_utc(
                investigation.request.window_start
            ) or end > _parse_utc(investigation.request.window_end):
                raise StoreInputError(
                    "query window falls outside investigation window."
                )
            try:
                return self._reader.get_snapshot(
                    investigation_id, access_scope=context.access_scope
                )
            except StoreAccessError:
                return EvidenceQueryResult(
                    "snapshot_missing", (), (), 0, False, "snapshot_missing"
                )
        except StoreSchemaError:
            return EvidenceQueryResult(
                "storage_failure", (), (), 0, False, "schema_incompatible"
            )
        except StoreDependencyError:
            return EvidenceQueryResult(
                "storage_failure", (), (), 0, False, "storage_failure"
            )

    def query(
        self,
        investigation_id: str,
        query: EvidenceQuery,
        *,
        context: TrustedQueryContext,
    ) -> EvidenceQueryResult:
        snapshot = self._read(investigation_id, query, context=context)
        if isinstance(snapshot, EvidenceQueryResult):
            self._log_result(investigation_id, snapshot)
            return snapshot
        start = _parse_utc(query.window_start)
        end = _parse_utc(query.window_end)
        matches = sorted(
            (
                entry
                for entry in snapshot.entries
                if entry.record.environment == context.environment
                and entry.record.service in context.allowed_services
                and (query.service is None or entry.record.service == query.service)
                and (query.kind is None or entry.kind == query.kind)
                and start <= _parse_utc(entry.record.observed_at) <= end
            ),
            key=lambda entry: (
                _parse_utc(entry.record.observed_at),
                entry.record.evidence_id,
            ),
        )
        truncated = len(matches) > query.limit
        incomplete = (
            truncated
            or not snapshot.sources
            or any(source.status != "available" for source in snapshot.sources)
        )
        status: QueryStatus = (
            "incomplete" if incomplete else "complete" if matches else "empty"
        )
        result = EvidenceQueryResult(
            status=status,
            entries=tuple(matches[: query.limit]),
            sources=snapshot.sources,
            matching_count=len(matches),
            truncated=truncated,
        )
        self._log_result(investigation_id, result)
        return result

    @staticmethod
    def _log_result(investigation_id: str, result: EvidenceQueryResult) -> None:
        _LOG.info(
            "Evidence query completed.",
            extra={
                "event": "evidence.query.completed",
                "investigation_id": investigation_id,
                "status": result.status,
                "matching_count": result.matching_count,
                "returned_count": len(result.entries),
                "truncated": result.truncated,
            },
        )

    def get_by_id(
        self,
        investigation_id: str,
        evidence_id: str,
        query: EvidenceQuery,
        *,
        context: TrustedQueryContext,
    ) -> EvidenceEntry:
        """Resolve an ID under the same scope, service and window as list reads."""
        _identifier("evidence_id", evidence_id)
        snapshot = self._read(investigation_id, query, context=context)
        if isinstance(snapshot, EvidenceQueryResult):
            if snapshot.status == "storage_failure":
                raise StoreDependencyError("Evidence storage is unavailable.")
            raise StoreAccessError("Evidence is absent or outside the access scope.")
        start = _parse_utc(query.window_start)
        end = _parse_utc(query.window_end)
        for entry in snapshot.entries:
            record = entry.record
            if record.evidence_id != evidence_id:
                continue
            if (
                record.environment == context.environment
                and record.service in context.allowed_services
                and (query.service is None or record.service == query.service)
                and (query.kind is None or entry.kind == query.kind)
                and start <= _parse_utc(record.observed_at) <= end
            ):
                return entry
        raise StoreAccessError("Evidence is absent or outside the access scope.")
