"""Fixed read-only tools; trusted grants and execution bounds are never arguments."""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import asdict, dataclass, replace
from datetime import timedelta
from threading import Lock
from typing import Callable, Literal, Protocol, cast

from trace_app.evidence.queries import EvidenceQuery, TrustedQueryContext
from trace_app.investigation.models import EvidenceKind, _identifier
from trace_app.knowledge.models import CorpusReadContext
from trace_app.knowledge.ports import SearchRequest

TOOL_VERSION = "investigation-tools.v1"
TOOL_NAMES = (
    "logs.query",
    "metrics.query",
    "deployments.query",
    "evidence.get",
    "knowledge.search",
    "knowledge.resolve",
)
ToolStatus = Literal[
    "ok",
    "empty",
    "partial",
    "validation_error",
    "authorization_error",
    "timeout",
    "dependency_failure",
    "budget_exhausted",
]


@dataclass(frozen=True, slots=True)
class ToolPolicy:
    """Local safety limits, not an operational SLA or benchmark threshold."""

    max_attempts: int = 20
    max_duration_ms: int = 120_000
    call_timeout_ms: int = 5_000
    max_results: int = 100
    max_window_seconds: int = 86_400
    max_result_bytes: int = 65_536

    def __post_init__(self) -> None:
        ceilings = (100, 600_000, 10_000, 100, 86_400, 1_000_000)
        for (name, value), ceiling in zip(asdict(self).items(), ceilings, strict=True):
            if type(value) is not int or not 1 <= value <= ceiling:
                raise ValueError(f"{name} is outside its supported bound.")
        if self.max_result_bytes < 512:
            raise ValueError("max_result_bytes must be at least 512.")


@dataclass(frozen=True, slots=True)
class ToolScope:
    """Supplied by authenticated composition; immutable for one tool session."""

    investigation_id: str
    correlation_id: str
    evidence: TrustedQueryContext
    knowledge: CorpusReadContext

    def __post_init__(self) -> None:
        _identifier("investigation_id", self.investigation_id)
        _identifier("correlation_id", self.correlation_id)
        if not isinstance(self.evidence, TrustedQueryContext) or not isinstance(
            self.knowledge, CorpusReadContext
        ):
            raise ValueError("Tool grants require validated trusted contexts.")
        if self.evidence.environment != self.knowledge.environment:
            raise ValueError("Tool contexts must share the trusted environment.")


@dataclass(frozen=True, slots=True)
class EvidenceArguments:
    query: EvidenceQuery
    evidence_id: str | None = None


@dataclass(frozen=True, slots=True)
class CitationArguments:
    generation_id: str
    chunk_id: str
    service: str | None = None


@dataclass(frozen=True, slots=True)
class KnowledgeArguments:
    request: SearchRequest
    max_passages: int


@dataclass(frozen=True, slots=True)
class ToolCall:
    name: str
    arguments: EvidenceArguments | KnowledgeArguments | CitationArguments

    @classmethod
    def parse(cls, name: object, value: object, policy: ToolPolicy) -> ToolCall:
        if not isinstance(name, str) or name not in TOOL_NAMES:
            raise ValueError("Unknown read-only tool.")
        if (
            not isinstance(value, dict)
            or len(value) > 6
            or any(not isinstance(k, str) for k in value)
        ):
            raise ValueError("Tool arguments must be an object.")
        if name in TOOL_NAMES[:4]:
            required = {"window_start", "window_end"}
            optional = {"limit", "service"}
            if name == "evidence.get":
                required.add("evidence_id")
                optional.add("kind")
            _fields(value, required, optional)
            if any(
                not isinstance(value[field], str) or len(value[field]) > 64
                for field in ("window_start", "window_end")
            ):
                raise ValueError("Window timestamps exceed their input bound.")
            kind = {
                "logs.query": "log",
                "metrics.query": "metric",
                "deployments.query": "deployment",
            }.get(name, value.get("kind"))
            query = EvidenceQuery(
                value["window_start"],
                value["window_end"],
                value.get("limit", policy.max_results),
                value.get("service"),
                cast(EvidenceKind | None, kind),
            )
            from trace_app.evidence.models import _parse_utc

            if query.limit > policy.max_results or (
                _parse_utc(query.window_end) - _parse_utc(query.window_start)
                > timedelta(seconds=policy.max_window_seconds)
            ):
                raise ValueError("Evidence result/window bound exceeded.")
            identity = value.get("evidence_id")
            if name == "evidence.get":
                if not isinstance(identity, str):
                    raise ValueError("evidence_id requires an identifier.")
                _identifier("evidence_id", identity)
            return cls(name, EvidenceArguments(query, identity))
        if name == "knowledge.search":
            _fields(value, {"query"}, {"service", "limit"})
            limit = value.get("limit", 5)
            if type(limit) is not int or not 1 <= limit <= min(5, policy.max_results):
                raise ValueError("Knowledge passage limit exceeded.")
            if value.get("service") is not None:
                _identifier("service", value["service"])
            # The measured default and candidate pool are composition decisions.
            return cls(
                name,
                KnowledgeArguments(
                    SearchRequest(
                        value["query"],
                        20,
                        "lexical",
                        value.get("service"),
                        candidate_pool=20,
                        max_chunks_per_document=20,
                    ),
                    limit,
                ),
            )
        _fields(value, {"generation_id", "chunk_id"}, {"service"})
        for field, prefix in (("generation_id", "gen-"), ("chunk_id", "chunk-")):
            if not isinstance(value[field], str) or not re.fullmatch(
                prefix + "[0-9a-f]{64}", value[field]
            ):
                raise ValueError("Invalid generation-bound citation identity.")
        if value.get("service") is not None:
            _identifier("service", value["service"])
        return cls(
            name,
            CitationArguments(
                value["generation_id"], value["chunk_id"], value.get("service")
            ),
        )

    def to_arguments(self) -> dict[str, object]:
        if isinstance(self.arguments, EvidenceArguments):
            values = asdict(self.arguments.query)
            if self.name != "evidence.get":
                values.pop("kind")
            else:
                values["evidence_id"] = self.arguments.evidence_id
            return values
        if isinstance(self.arguments, KnowledgeArguments):
            return {
                "query": self.arguments.request.query,
                "service": self.arguments.request.service,
                "limit": self.arguments.max_passages,
            }
        return asdict(self.arguments)


def _fields(value: dict, required: set[str], optional: set[str]) -> None:
    if not required <= value.keys() or value.keys() - required - optional:
        raise ValueError("Tool fields differ from the closed schema.")


@dataclass(frozen=True, slots=True)
class ToolPayload:
    status: ToolStatus
    data: dict[str, object]
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.status not in (
            "ok",
            "empty",
            "partial",
            "validation_error",
            "authorization_error",
            "timeout",
            "dependency_failure",
            "budget_exhausted",
        ) or not isinstance(self.data, dict):
            raise ValueError("Invalid tool result envelope.")
        if self.reason is not None and (
            not isinstance(self.reason, str)
            or not re.fullmatch("[a-z][a-z0-9_]{0,127}", self.reason)
        ):
            raise ValueError("Tool reason must be a bounded safe error code.")


class ToolBackend(Protocol):
    def execute(
        self, call: ToolCall, scope: ToolScope, policy: ToolPolicy, *, timeout_ms: int
    ) -> ToolPayload: ...


@dataclass(frozen=True, slots=True)
class ToolAudit:
    version: str
    correlation_id: str
    attempt_id: str
    attempt_number: int
    tool: str
    duration_ms: float
    outcome: ToolStatus


class AuditSink(Protocol):
    def emit(self, record: ToolAudit) -> None: ...


@dataclass(frozen=True, slots=True)
class ToolResult:
    audit: ToolAudit
    payload: ToolPayload

    def to_dict(self) -> dict[str, object]:
        return {"audit": asdict(self.audit), **asdict(self.payload)}


class ToolSession:
    """One serialized budget, no retries, no caller-supplied grants or paths."""

    def __init__(
        self,
        backend: ToolBackend,
        scope: ToolScope,
        audit: AuditSink,
        policy: ToolPolicy = ToolPolicy(),
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._backend, self._scope, self._audit = backend, scope, audit
        self._policy, self._clock = policy, clock
        self._started, self._attempts = clock(), 0
        self._lock = Lock()
        self._state_lock = Lock()

    @property
    def investigation_id(self) -> str:
        return self._scope.investigation_id

    def invoke(self, name: object, arguments: object) -> ToolResult:
        started = self._clock()
        # Count all requests atomically, including concurrent denied attempts.
        with self._state_lock:
            self._attempts += 1
            attempt_number = self._attempts
            acquired = self._lock.acquire(blocking=False)
        try:
            remaining = self._policy.max_duration_ms - (started - self._started) * 1000
            safe_name = (
                name if isinstance(name, str) and name in TOOL_NAMES else "unknown"
            )
            if not acquired:
                payload = ToolPayload("budget_exhausted", {}, "session_call_active")
            elif attempt_number > self._policy.max_attempts or remaining < 1:
                payload = ToolPayload(
                    "budget_exhausted", {}, "session_budget_exhausted"
                )
            else:
                try:
                    call = ToolCall.parse(name, arguments, self._policy)
                except (ValueError, TypeError):
                    payload = ToolPayload("validation_error", {}, "invalid_arguments")
                else:
                    service = getattr(call.arguments, "service", None)
                    if isinstance(call.arguments, EvidenceArguments):
                        service = call.arguments.query.service
                    elif isinstance(call.arguments, KnowledgeArguments):
                        service = call.arguments.request.service
                    grants = (
                        self._scope.knowledge
                        if call.name.startswith("knowledge.")
                        else self._scope.evidence
                    )
                    if service is not None and service not in grants.allowed_services:
                        payload = ToolPayload(
                            "authorization_error", {}, "source_not_authorized"
                        )
                    else:
                        remaining = (
                            self._policy.max_duration_ms
                            - (self._clock() - self._started) * 1000
                        )
                        timeout = max(
                            1, int(min(remaining, self._policy.call_timeout_ms))
                        )
                        try:
                            payload = (
                                ToolPayload(
                                    "budget_exhausted", {}, "session_budget_exhausted"
                                )
                                if remaining < 1
                                else self._backend.execute(
                                    call, self._scope, self._policy, timeout_ms=timeout
                                )
                            )
                            if (self._clock() - started) * 1000 > timeout:
                                payload = ToolPayload(
                                    "timeout", {}, "call_deadline_exceeded"
                                )
                            elif (
                                len(
                                    json.dumps(
                                        asdict(payload),
                                        ensure_ascii=False,
                                        allow_nan=False,
                                    ).encode()
                                )
                                > self._policy.max_result_bytes
                            ):
                                payload = ToolPayload(
                                    "dependency_failure", {}, "invalid_backend_result"
                                )
                        except TimeoutError:
                            payload = ToolPayload(
                                "timeout", {}, "call_deadline_exceeded"
                            )
                        except Exception:
                            # No exception text, arguments or retrieved content in audit/errors.
                            payload = ToolPayload(
                                "dependency_failure", {}, "backend_unavailable"
                            )
            record = ToolAudit(
                TOOL_VERSION,
                self._scope.correlation_id,
                str(uuid.uuid4()),
                attempt_number,
                safe_name,
                max(0.0, (self._clock() - started) * 1000),
                payload.status,
            )
            # A failed audit sink fails closed: no evidence result is released.
            try:
                self._audit.emit(record)
            except Exception:
                payload = ToolPayload("dependency_failure", {}, "audit_unavailable")
                record = replace(record, outcome=payload.status)
            return ToolResult(record, payload)
        finally:
            if acquired:
                self._lock.release()
