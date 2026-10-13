"""Explicit nonfunctional HTTP/authority seams; no live credentials or data."""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from trace_app.adapters.models.azure import AzureModelSettings
from trace_app.investigation.provider import (
    AdmissionGuard,
    ModelCallBounds,
    ModelErrorCode,
    ModelProviderError,
    ModelReply,
    ModelRequest,
    ModelResult,
    ModelUsage,
    validate_model_reply,
)
from trace_app.investigation.provider_policy import (
    AuthorizedEvidence,
    EvidenceField,
    EvidenceSelection,
    PolicyModelProvider,
    PromptTemplate,
    ProviderCall,
    ProviderScope,
    Redaction,
    Sensitivity,
    SourceKind,
)

NOW = 2_000_000_000.0
TEST_AUTH_VALUE = "opaque-unit-marker-not-an-api-key"
SCOPE = ProviderScope("fixture-user", "fixture-investigation")
SETTINGS = AzureModelSettings(
    "https://example.services.ai.azure.com/openai/v1/",
    "fixture-deployment",
    "gpt-6-luna",
    "2026-09-22",
    "azure-fixture-v1",
)


@dataclass
class Clock:
    now: float = NOW

    def __call__(self) -> float:
        return self.now


def record(**changes: Any) -> AuthorizedEvidence:
    values: dict[str, Any] = {
        "evidence_id": "evidence-1",
        "source_id": "source-1",
        "revision": "revision-1",
        "kind": SourceKind.SYNTHETIC,
        "fields": (
            EvidenceField(
                "observation", "Synthetic observation.", Sensitivity.INTERNAL, True
            ),
        ),
        "access_allowed": True,
        "transmission_allowed": True,
        "source_owner_allowed": True,
        "identifiers_reviewed": True,
        "expires_at": NOW + 3600,
    }
    values.update(changes)
    return AuthorizedEvidence(**values)


@dataclass
class Authority:
    records: dict[str, AuthorizedEvidence] = field(
        default_factory=lambda: {"evidence-1": record()}
    )
    reads: int = 0

    def resolve(
        self, scope: ProviderScope, evidence_id: str
    ) -> AuthorizedEvidence | None:
        self.reads += 1
        return self.records.get(evidence_id) if scope == SCOPE else None


@dataclass
class MemoryJournal:
    entries: list[dict[str, object]] = field(default_factory=list)
    redactions: list[Redaction] = field(default_factory=list)
    fail_begin: bool = False
    fail_finish: bool = False
    after_begin: Any = None

    def begin(
        self,
        metadata: dict[str, object],
        redactions: tuple[Redaction, ...],
        input_allowance: int,
        output_allowance: int,
        now: float,
    ) -> None:
        if self.fail_begin:
            raise ModelProviderError(ModelErrorCode.AUDIT)
        self.redactions.extend(redactions)
        if self.after_begin is not None:
            self.after_begin()

    def finish(
        self,
        metadata: dict[str, object],
        usage: ModelUsage,
        dispatched: bool,
        now: float,
    ) -> None:
        if self.fail_finish:
            raise RuntimeError("Untrusted audit exception.")
        self.entries.append(copy.deepcopy(metadata))


@dataclass
class RecordingProvider:
    guard: AdmissionGuard
    reply: ModelReply = ModelReply(
        '{"status":"ok"}', "resp_fixture", ModelUsage(23, 24)
    )
    requests: list[ModelRequest] = field(default_factory=list)
    error: ModelErrorCode | None = None

    def generate(self, request: ModelRequest) -> ModelResult:
        self.guard.verify(request)
        self.requests.append(request)
        if self.error is not None:
            raise ModelProviderError(self.error)
        return validate_model_reply(request, self.reply)


def policy_fixture(
    authority: Authority | None = None,
    journal: MemoryJournal | None = None,
    **changes: Any,
) -> tuple[PolicyModelProvider, RecordingProvider, Authority, MemoryJournal]:
    authority = authority or Authority()
    journal = journal or MemoryJournal()
    guard = AdmissionGuard(b"nonfunctional-fixture-capability!" * 2, Clock())
    provider = RecordingProvider(guard)
    values: dict[str, Any] = {
        "known_secrets": (TEST_AUTH_VALUE,),
        "read_clock": Clock(),
    }
    values.update(changes)
    policy = PolicyModelProvider(
        SETTINGS.configuration(),
        provider,
        authority,
        journal,
        guard,
        SCOPE,
        {
            "fixture-prompt-v1": PromptTemplate(
                "Return a synthetic JSON health object.", "health.v1"
            )
        },
        **values,
    )
    return policy, provider, authority, journal


def call(**changes: Any) -> ProviderCall:
    values: dict[str, Any] = {
        "prompt_version": "fixture-prompt-v1",
        "evidence": (EvidenceSelection("evidence-1", "revision-1", ("observation",)),),
        "bounds": ModelCallBounds(5000, 65536, 256),
    }
    values.update(changes)
    return ProviderCall(**values)


def azure_body(**changes: Any) -> bytes:
    value: dict[str, Any] = {
        "id": "resp_fixture",
        "model": "gpt-6-luna",
        "status": "completed",
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": '{"status":"ok"}'}],
            }
        ],
        "usage": {"input_tokens": 23, "output_tokens": 24},
    }
    value.update(changes)
    return json.dumps(value).encode()


class HttpResponse:
    def __init__(self, status: int = 200, body: bytes | None = None) -> None:
        self.status = status
        self._body = azure_body() if body is None else body

    def read(self, maximum: int) -> bytes:
        return self._body[:maximum]


class HttpConnection:
    instances: list[HttpConnection] = []
    response: HttpResponse = HttpResponse()

    def __init__(self, host: str, **kwargs: Any) -> None:
        self.requests: list[dict[str, Any]] = []
        self.closed = False
        self.instances.append(self)

    def connect(self) -> None:
        pass

    def request(self, method: str, path: str, **kwargs: Any) -> None:
        self.requests.append({"method": method, "path": path, **kwargs})

    def getresponse(self) -> HttpResponse:
        return self.response

    def close(self) -> None:
        self.closed = True


class ProcessHttpConnection(HttpConnection):
    def __init__(self, host: str, *, capture: Path, **kwargs: Any) -> None:
        super().__init__(host, **kwargs)
        self.capture = capture

    def request(self, method: str, path: str, **kwargs: Any) -> None:
        with self.capture.open("a") as stream:
            stream.write(
                json.dumps(
                    {
                        "method": method,
                        "path": path,
                        "body": json.loads(kwargs["body"]),
                        "header_names": sorted(kwargs["headers"]),
                    }
                )
                + "\n"
            )
        super().request(method, path, **kwargs)
