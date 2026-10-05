"""TRACE-owned investigation and snapshot contracts, independent of SQLite."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Literal

from trace_app.evidence import (
    EvidenceBundle,
    EvidenceRecord,
    SourceAvailability,
    _parse_utc,
)

EvidenceKind = Literal["log", "metric", "deployment"]
ExecutionStatus = Literal[
    "queued", "running", "completed", "failed", "cancelled", "expired"
]
AssessmentStatus = Literal["pending", "supported", "abstained"]
ReviewStatus = Literal["pending", "unreviewed", "approved", "rejected"]
AttemptOutcome = Literal[
    "running", "completed", "failed", "interrupted", "cancelled", "expired"
]


class StoreInputError(ValueError):
    """Invalid application input; error text names the field."""


class StoreConflictError(RuntimeError):
    """An idempotency key or stable evidence identity has conflicting content."""


class StoreAccessError(PermissionError):
    """The requested record is absent or outside the supplied access scope."""


class StoreStateError(RuntimeError):
    """A requested transition conflicts with durable execution state."""


class StoreSchemaError(RuntimeError):
    """The on-disk schema is newer or incompatible with this application."""


class StoreDependencyError(RuntimeError):
    """Evidence storage failed; callers may report a structured failure."""


def _identifier(name: str, value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_:/.-]{0,127}", value
    ):
        raise StoreInputError(f"{name} must be 1–128 safe ASCII characters.")


@dataclass(frozen=True, slots=True)
class InvestigationRequest:
    submission_key: str
    service: str
    environment: str
    access_scope: str
    window_start: str
    window_end: str
    expires_at: str | None = None
    max_attempts: int = 3

    def __post_init__(self) -> None:
        for name in ("submission_key", "service", "environment", "access_scope"):
            _identifier(name, getattr(self, name))
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
        if type(self.max_attempts) is not int or self.max_attempts <= 0:
            raise StoreInputError("max_attempts must be a positive integer.")
        if self.expires_at is not None:
            try:
                expiry = _parse_utc(self.expires_at)
            except ValueError as error:
                raise StoreInputError(f"expires_at: {error}") from error
            if expiry < end:
                raise StoreInputError("expires_at must not precede window_end.")
            object.__setattr__(
                self, "expires_at", expiry.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            )


@dataclass(frozen=True, slots=True)
class LogPayload:
    message: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.message, str)
            or not self.message
            or len(self.message) > 512
        ):
            raise StoreInputError(
                "message must be a nonempty string of at most 512 characters."
            )
        if "\x00" in self.message:
            raise StoreInputError("message must not contain NUL.")


@dataclass(frozen=True, slots=True)
class MetricPayload:
    name: str
    value: float
    unit: str

    def __post_init__(self) -> None:
        _identifier("name", self.name)
        _identifier("unit", self.unit)
        if type(self.value) not in (int, float):
            raise StoreInputError("value must be a finite number.")
        try:
            finite = math.isfinite(self.value)
        except OverflowError:
            finite = False
        if not finite:
            raise StoreInputError("value must be a finite number.")


@dataclass(frozen=True, slots=True)
class DeploymentPayload:
    revision: str
    phase: str

    def __post_init__(self) -> None:
        _identifier("revision", self.revision)
        _identifier("phase", self.phase)


EvidencePayload = LogPayload | MetricPayload | DeploymentPayload


@dataclass(frozen=True, slots=True)
class EvidenceEntry:
    kind: EvidenceKind
    record: EvidenceRecord
    payload: EvidencePayload

    def __post_init__(self) -> None:
        expected = {
            "log": LogPayload,
            "metric": MetricPayload,
            "deployment": DeploymentPayload,
        }.get(self.kind)
        if expected is None:
            raise StoreInputError("kind must be log, metric or deployment.")
        if not isinstance(self.payload, expected):
            raise StoreInputError("payload does not match kind.")


@dataclass(frozen=True, slots=True)
class EvidenceSnapshot:
    entries: tuple[EvidenceEntry, ...]
    window_start: str
    window_end: str
    sources: tuple[SourceAvailability, ...]

    def __post_init__(self) -> None:
        try:
            self.to_bundle()
        except ValueError as error:
            raise StoreInputError(str(error)) from error
        source_keys = {
            (entry.record.source_record_id, entry.record.source_revision)
            for entry in self.entries
        }
        if len(source_keys) != len(self.entries):
            raise StoreInputError("source_record_id/source_revision must be unique.")

    def to_bundle(self) -> EvidenceBundle:
        return EvidenceBundle(
            records=tuple(entry.record for entry in self.entries),
            window_start=self.window_start,
            window_end=self.window_end,
            sources=self.sources,
        )


@dataclass(frozen=True, slots=True)
class Investigation:
    investigation_id: str
    request: InvestigationRequest
    created_at: str
    status: ExecutionStatus
    assessment_status: AssessmentStatus
    review_status: ReviewStatus
    attempt_count: int
    active_attempt_id: int | None
    lease_until: str | None
    finished_at: str | None
    failure_code: str | None


@dataclass(frozen=True, slots=True)
class Attempt:
    attempt_id: int
    investigation_id: str
    attempt_number: int
    started_at: str
    lease_until: str
    finished_at: str | None
    outcome: AttemptOutcome
    failure_code: str | None
