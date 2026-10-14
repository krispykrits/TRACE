"""TRACE-owned model contract; provider payloads are never default artifacts."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
import time
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Protocol

MODEL_CONTRACT_VERSION = "model-provider.v1"
PROVIDER_POLICY_VERSION = "trace-provider-data-policy.v1"
_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z")


class ModelErrorCode(StrEnum):
    CONFIGURATION = "configuration_error"
    CREDENTIALS_MISSING = "credentials_missing"
    MODEL_UNAVAILABLE = "model_unavailable"
    CAPABILITY_UNSUPPORTED = "capability_unsupported"
    AUTHENTICATION = "authentication_error"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    DEPENDENCY = "dependency_failure"
    MALFORMED_RESPONSE = "malformed_response"
    OUTPUT_LIMIT = "output_limit"
    POLICY = "policy_rejected"
    AUDIT = "audit_unavailable"
    BUDGET = "budget_exhausted"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    TERMINAL = "execution_stopped"


_ERROR_MESSAGES = {
    ModelErrorCode.CONFIGURATION: "Model configuration is missing or incompatible.",
    ModelErrorCode.CREDENTIALS_MISSING: "Required model credentials are missing.",
    ModelErrorCode.MODEL_UNAVAILABLE: "The configured model is unavailable or unsupported.",
    ModelErrorCode.CAPABILITY_UNSUPPORTED: "The required model capability is unsupported.",
    ModelErrorCode.AUTHENTICATION: "Model authentication failed; check authorized credentials.",
    ModelErrorCode.RATE_LIMIT: "The model provider rate limit was reached.",
    ModelErrorCode.TIMEOUT: "The model call deadline was exceeded.",
    ModelErrorCode.DEPENDENCY: "The required model dependency failed.",
    ModelErrorCode.MALFORMED_RESPONSE: "The model response failed contract validation.",
    ModelErrorCode.OUTPUT_LIMIT: "The model response exceeded its configured output bound.",
    ModelErrorCode.POLICY: "Provider transmission or response access failed policy checks.",
    ModelErrorCode.AUDIT: "Provider audit is unavailable; reconcile the attempt before continuing.",
    ModelErrorCode.BUDGET: "Investigation or local spending allowance is exhausted; inspect the correlated budget record.",
    ModelErrorCode.CANCELLED: "Investigation was cancelled; no further calls are permitted.",
    ModelErrorCode.EXPIRED: "Investigation deadline or active attempt lease has expired.",
    ModelErrorCode.TERMINAL: "Investigation execution stopped; inspect its correlated audit before continuing.",
}


class ModelProviderError(Exception):
    """Fixed messages cannot contain SDK exception text, prompts or credentials."""

    def __init__(
        self,
        code: ModelErrorCode,
        *,
        usage: ModelUsage | None = None,
        diagnostics: dict[str, object] | None = None,
    ) -> None:
        self.code = ModelErrorCode(code)
        self.usage = usage
        self.diagnostics: dict[str, object] = {}
        for name, value in (diagnostics or {}).items():
            if (
                name == "http_status"
                and type(value) is int
                and 100 <= value <= 599
                or name == "provider_error_code"
                and value
                in (
                    "unsupported_parameter",
                    "unsupported_value",
                    "invalid_request_error",
                    "invalid_value",
                    "invalid_parameter",
                    "model_not_found",
                    "content_policy_violation",
                    "missing_required_parameter",
                    "unknown_parameter",
                )
                or name == "provider_error_parameter"
                and value
                in (
                    "model",
                    "instructions",
                    "input",
                    "text",
                    "text.format",
                    "text.format.type",
                    "max_output_tokens",
                    "store",
                    "truncation",
                )
            ):
                self.diagnostics[name] = value
        super().__init__(_ERROR_MESSAGES[self.code])


def _identifier(value: object) -> None:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ModelProviderError(ModelErrorCode.CONFIGURATION)


def _bounded_integer(value: object, maximum: int) -> None:
    if type(value) is not int or not 1 <= value <= maximum:
        raise ModelProviderError(ModelErrorCode.CONFIGURATION)


@dataclass(frozen=True, slots=True)
class ModelConfiguration:
    """Selected by trusted composition, never by retrieved text or model output."""

    provider_id: str
    model_id: str
    configuration_id: str
    adapter_version: str
    mode: str = "live"
    response_format: str = "json_object"
    automatic_retries: int = 0
    deployment_id: str | None = None
    model_version: str | None = None

    def __post_init__(self) -> None:
        for value in (
            self.provider_id,
            self.model_id,
            self.configuration_id,
            self.adapter_version,
        ):
            _identifier(value)
        for optional_value in (self.deployment_id, self.model_version):
            if optional_value is not None:
                _identifier(optional_value)
        if (
            self.mode not in ("live", "offline_test")
            or self.response_format != "json_object"
            or type(self.automatic_retries) is not int
            or self.automatic_retries != 0
        ):
            raise ModelProviderError(ModelErrorCode.CONFIGURATION)

    def to_dict(self) -> dict[str, object]:
        result: dict[str, object] = {
            "provider_id": self.provider_id,
            "model_id": self.model_id,
            "configuration_id": self.configuration_id,
            "adapter_version": self.adapter_version,
            "mode": self.mode,
            "response_format": self.response_format,
            "automatic_retries": self.automatic_retries,
        }
        if self.deployment_id is not None:
            result["deployment_id"] = self.deployment_id
        if self.model_version is not None:
            result["model_version"] = self.model_version
        return result

    @classmethod
    def from_dict(cls, value: object) -> ModelConfiguration:
        required = {"provider_id", "model_id", "configuration_id", "adapter_version"}
        optional = {
            "mode",
            "response_format",
            "automatic_retries",
            "deployment_id",
            "model_version",
        }
        if (
            not isinstance(value, dict)
            or not required <= value.keys()
            or not value.keys() <= required | optional
        ):
            raise ModelProviderError(ModelErrorCode.CONFIGURATION)
        return cls(**value)


@dataclass(frozen=True, slots=True)
class ModelCapabilities:
    """An adapter's declared compatibility, not proof of live readiness."""

    provider_id: str
    adapter_version: str
    model_ids: tuple[str, ...]
    structured_json: bool
    output_token_limit: bool
    credentials_required: bool
    offline_only: bool = False

    def __post_init__(self) -> None:
        _identifier(self.provider_id)
        _identifier(self.adapter_version)
        if not isinstance(self.model_ids, tuple) or not self.model_ids:
            raise ModelProviderError(ModelErrorCode.CONFIGURATION)
        for value in self.model_ids:
            _identifier(value)
        if len(set(self.model_ids)) != len(self.model_ids) or any(
            type(value) is not bool
            for value in (
                self.structured_json,
                self.output_token_limit,
                self.credentials_required,
                self.offline_only,
            )
        ):
            raise ModelProviderError(ModelErrorCode.CONFIGURATION)


def validate_model_readiness(
    configuration: ModelConfiguration,
    capabilities: ModelCapabilities,
    *,
    credential_present: bool,
) -> str:
    """Local preflight only; live acceptance needs a separate actual invocation."""
    if (
        not isinstance(configuration, ModelConfiguration)
        or not isinstance(capabilities, ModelCapabilities)
        or type(credential_present) is not bool
    ):
        raise ModelProviderError(ModelErrorCode.CONFIGURATION)
    if (
        configuration.provider_id != capabilities.provider_id
        or configuration.adapter_version != capabilities.adapter_version
        or (configuration.mode == "offline_test") != capabilities.offline_only
    ):
        raise ModelProviderError(ModelErrorCode.CONFIGURATION)
    if configuration.model_id not in capabilities.model_ids:
        raise ModelProviderError(ModelErrorCode.MODEL_UNAVAILABLE)
    if not capabilities.structured_json or not capabilities.output_token_limit:
        raise ModelProviderError(ModelErrorCode.CAPABILITY_UNSUPPORTED)
    if capabilities.credentials_required and not credential_present:
        raise ModelProviderError(ModelErrorCode.CREDENTIALS_MISSING)
    return "offline_test_only" if capabilities.offline_only else "live_check_required"


@dataclass(frozen=True, slots=True)
class ModelCallBounds:
    """Explicit implementation bounds; no spending limit or operational SLA."""

    timeout_ms: int
    max_response_bytes: int
    max_output_tokens: int

    def __post_init__(self) -> None:
        _bounded_integer(self.timeout_ms, 600_000)
        _bounded_integer(self.max_response_bytes, 1_000_000)
        _bounded_integer(self.max_output_tokens, 100_000)


@dataclass(frozen=True, slots=True)
class ModelAdmission:
    """A short-lived receipt bound to every byte of a prepared request."""

    policy_version: str
    evidence_ids: tuple[str, ...]
    sensitivity: str
    scope_id: str
    principal_id: str = field(repr=False)
    expires_at: float
    signature: str = field(repr=False)

    def metadata(self) -> dict[str, object]:
        return {
            "policy_version": self.policy_version,
            "evidence_ids": list(self.evidence_ids),
            "sensitivity": self.sensitivity,
            "scope_id": self.scope_id,
        }


@dataclass(frozen=True, slots=True)
class ModelRequest:
    request_id: str
    configuration: ModelConfiguration
    prompt_version: str
    response_schema_id: str
    instructions: str = field(repr=False)
    source_context: str = field(repr=False)
    bounds: ModelCallBounds
    contract_version: str = MODEL_CONTRACT_VERSION
    admission: ModelAdmission | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        for value in (self.request_id, self.prompt_version, self.response_schema_id):
            _identifier(value)
        if (
            self.contract_version != MODEL_CONTRACT_VERSION
            or not isinstance(self.configuration, ModelConfiguration)
            or not isinstance(self.bounds, ModelCallBounds)
        ):
            raise ModelProviderError(ModelErrorCode.CONFIGURATION)
        for value in (self.instructions, self.source_context):
            try:
                valid = (
                    isinstance(value, str)
                    and bool(value.strip())
                    and len(value.encode()) <= 131_072
                )
            except UnicodeError:
                valid = False
            if not valid:
                raise ModelProviderError(ModelErrorCode.CONFIGURATION)

    def metadata(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "request_id": self.request_id,
            "configuration": self.configuration.to_dict(),
            "prompt_version": self.prompt_version,
            "response_schema_id": self.response_schema_id,
            **(self.admission.metadata() if self.admission is not None else {}),
        }


class AdmissionGuard:
    """Private composition capability; evidence cannot mint transport authority."""

    def __init__(self, key: bytes, read_clock: Callable[[], float] = time.time) -> None:
        if not isinstance(key, bytes) or len(key) < 32:
            raise ModelProviderError(ModelErrorCode.CONFIGURATION)
        self._key = key
        self._read_clock = read_clock

    def _signature(self, request: ModelRequest, receipt: ModelAdmission) -> str:
        value = {
            "request": {
                **request.metadata(),
                "instructions": request.instructions,
                "source_context": request.source_context,
                "bounds": [
                    request.bounds.timeout_ms,
                    request.bounds.max_response_bytes,
                    request.bounds.max_output_tokens,
                ],
            },
            "receipt": {
                **receipt.metadata(),
                "principal_id": receipt.principal_id,
                "expires_at": receipt.expires_at,
            },
        }
        payload = json.dumps(value, sort_keys=True, allow_nan=False).encode()
        return hmac.new(self._key, payload, hashlib.sha256).hexdigest()

    def issue(
        self,
        request: ModelRequest,
        *,
        evidence_ids: tuple[str, ...],
        sensitivity: str,
        scope_id: str,
        principal_id: str,
        expires_at: float,
    ) -> ModelRequest:
        receipt = ModelAdmission(
            PROVIDER_POLICY_VERSION,
            evidence_ids,
            sensitivity,
            scope_id,
            principal_id,
            expires_at,
            "",
        )
        prepared = replace(request, admission=receipt)
        receipt = replace(receipt, signature=self._signature(prepared, receipt))
        return replace(prepared, admission=receipt)

    def verify(self, request: ModelRequest) -> None:
        if not isinstance(request, ModelRequest):
            raise ModelProviderError(ModelErrorCode.POLICY)
        receipt = request.admission
        try:
            valid = (
                isinstance(receipt, ModelAdmission)
                and receipt.policy_version == PROVIDER_POLICY_VERSION
                and math.isfinite(receipt.expires_at)
                and receipt.expires_at > self._read_clock()
                and hmac.compare_digest(
                    receipt.signature, self._signature(request, receipt)
                )
            )
        except (TypeError, ValueError, UnicodeError):
            valid = False
        if not valid:
            raise ModelProviderError(ModelErrorCode.POLICY)


@dataclass(frozen=True, slots=True)
class ModelPricing:
    """Versioned upper-rate snapshot; estimates are never settled provider billing."""

    version: str
    input_nusd_per_token: int
    output_nusd_per_token: int

    def __post_init__(self) -> None:
        _identifier(self.version)
        if any(
            type(value) is not int or value <= 0
            for value in (self.input_nusd_per_token, self.output_nusd_per_token)
        ):
            raise ModelProviderError(ModelErrorCode.CONFIGURATION)

    def estimate(self, input_tokens: int, output_tokens: int) -> int:
        if any(
            type(value) is not int or value < 0
            for value in (input_tokens, output_tokens)
        ):
            raise ModelProviderError(ModelErrorCode.CONFIGURATION)
        return (
            input_tokens * self.input_nusd_per_token
            + output_tokens * self.output_nusd_per_token
        )


@dataclass(frozen=True, slots=True)
class ModelUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None

    def __post_init__(self) -> None:
        for value in (self.input_tokens, self.output_tokens):
            if value is not None and (type(value) is not int or value < 0):
                raise ModelProviderError(ModelErrorCode.MALFORMED_RESPONSE)

    def to_dict(self) -> dict[str, object]:
        counts = (self.input_tokens, self.output_tokens)
        availability = (
            "unavailable"
            if all(value is None for value in counts)
            else "available"
            if all(value is not None for value in counts)
            else "partial"
        )
        return {
            "availability": availability,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
        }


@dataclass(frozen=True, slots=True)
class ModelReply:
    """Adapter reply before boundary validation; raw content stays in memory."""

    structured_json: str = field(repr=False)
    operation_id: str | None = None
    usage: ModelUsage = ModelUsage()
    finish_reason: str = "completed"
    reported_model: str | None = None


@dataclass(frozen=True, slots=True)
class ModelResult:
    request: ModelRequest = field(repr=False)
    reply: ModelReply = field(repr=False)

    def metadata(self) -> dict[str, object]:
        return {
            **self.request.metadata(),
            "provider_operation_id": self.reply.operation_id,
            "usage": self.reply.usage.to_dict(),
            "reported_model": self.reply.reported_model,
            "status": "structured_response_received",
        }

    def structured_response(self) -> dict[str, object]:
        # A fresh object prevents mutation of the validated retained JSON.
        return json.loads(self.reply.structured_json)


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON field.")
        result[key] = value
    return result


def _reject_constant(value: str) -> object:
    raise ValueError("Nonfinite JSON value.")


def _validate_json_tree(value: dict[str, object]) -> None:
    pending: list[tuple[object, int]] = [(value, 0)]
    nodes = 0
    while pending:
        child, depth = pending.pop()
        nodes += 1
        if depth > 32 or nodes > 10_000:
            raise ValueError("JSON structure bound exceeded.")
        if isinstance(child, dict):
            pending.extend((key, depth + 1) for key in child)
            pending.extend((item, depth + 1) for item in child.values())
        elif isinstance(child, list):
            pending.extend((item, depth + 1) for item in child)
        elif isinstance(child, str):
            child.encode("utf-8")


def validate_model_reply(request: ModelRequest, reply: ModelReply) -> ModelResult:
    """JSON validity precedes #35's separate assessment/citation validation."""
    if not isinstance(reply, ModelReply) or not isinstance(reply.usage, ModelUsage):
        raise ModelProviderError(ModelErrorCode.MALFORMED_RESPONSE)
    if reply.operation_id is not None:
        if not isinstance(reply.operation_id, str) or not _IDENTIFIER.fullmatch(
            reply.operation_id
        ):
            raise ModelProviderError(ModelErrorCode.MALFORMED_RESPONSE)
    if reply.reported_model is not None:
        _identifier(reply.reported_model)
    if reply.finish_reason == "output_limit" or (
        reply.usage.output_tokens is not None
        and reply.usage.output_tokens > request.bounds.max_output_tokens
    ):
        raise ModelProviderError(ModelErrorCode.OUTPUT_LIMIT, usage=reply.usage)
    if reply.finish_reason != "completed" or not isinstance(reply.structured_json, str):
        raise ModelProviderError(ModelErrorCode.MALFORMED_RESPONSE, usage=reply.usage)
    try:
        if len(reply.structured_json.encode()) > request.bounds.max_response_bytes:
            raise ModelProviderError(ModelErrorCode.OUTPUT_LIMIT, usage=reply.usage)
        value = json.loads(
            reply.structured_json,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_constant,
        )
        if not isinstance(value, dict):
            raise ValueError("Object required.")
        _validate_json_tree(value)
        # json.loads also accepts overflowing finite literals such as 1e999.
        json.dumps(value, allow_nan=False)
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ModelProviderError(
            ModelErrorCode.MALFORMED_RESPONSE, usage=reply.usage
        ) from None
    return ModelResult(request, reply)


class ModelTransport(Protocol):
    """One call only; adapter disables SDK retries and obeys all supplied bounds."""

    def generate(self, request: ModelRequest) -> ModelReply: ...


class ModelProvider(Protocol):
    def generate(self, request: ModelRequest) -> ModelResult: ...
