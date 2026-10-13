"""Azure Responses v1, one HTTPS operation, admitted input only, no SDK retries."""

from __future__ import annotations

import http.client
import json
import ssl
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from trace_app.investigation.provider import (
    AdmissionGuard,
    ModelCapabilities,
    ModelConfiguration,
    ModelErrorCode,
    ModelProviderError,
    ModelReply,
    ModelRequest,
    ModelUsage,
    validate_model_reply,
)

AZURE_ADAPTER_VERSION = "azure-responses.v1"
AZURE_PROVIDER_ID = "azure_foundry"


@dataclass(frozen=True, slots=True)
class AzureModelSettings:
    base_url: str = field(repr=False)
    deployment_id: str
    model_id: str
    model_version: str
    configuration_id: str
    deployment_type: str = "GlobalStandard"

    def __post_init__(self) -> None:
        try:
            endpoint = urlsplit(self.base_url)
            valid = (
                endpoint.scheme == "https"
                and endpoint.hostname is not None
                and endpoint.hostname.endswith(
                    (".services.ai.azure.com", ".openai.azure.com")
                )
                and endpoint.port in (None, 443)
                and not endpoint.username
                and not endpoint.password
                and not endpoint.query
                and not endpoint.fragment
                and endpoint.path.rstrip("/") == "/openai/v1"
            )
        except (ValueError, TypeError, AttributeError):
            valid = False
        if (
            not valid
            or self.model_id != "gpt-6-luna"
            or self.deployment_type != "GlobalStandard"
        ):
            raise ModelProviderError(ModelErrorCode.CONFIGURATION)
        self.configuration()

    def configuration(self) -> ModelConfiguration:
        return ModelConfiguration(
            AZURE_PROVIDER_ID,
            self.model_id,
            self.configuration_id,
            AZURE_ADAPTER_VERSION,
            deployment_id=self.deployment_id,
            model_version=self.model_version,
        )

    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            AZURE_PROVIDER_ID,
            AZURE_ADAPTER_VERSION,
            (self.model_id,),
            structured_json=True,
            output_token_limit=True,
            credentials_required=True,
        )


def _private_values(path: Path) -> dict[str, str]:
    try:
        if not path.is_file() or path.stat().st_mode & 0o077:
            raise ValueError("Private configuration required.")
        if path.stat().st_size > 16_384:
            raise ValueError("Configuration bound exceeded.")
        values: dict[str, str] = {}
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name, separator, value = line.partition("=")
            if not separator or name in values:
                raise ValueError("Invalid local configuration.")
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            values[name] = value
        return values
    except (OSError, ValueError, UnicodeError):
        raise ModelProviderError(ModelErrorCode.CONFIGURATION) from None


def load_azure_settings(setup: Path, secrets: Path) -> tuple[AzureModelSettings, str]:
    """Explicit files only; no shell evaluation, env fallback or implicit sign-in."""
    values = _private_values(setup)
    credentials = _private_values(secrets)
    try:
        if values["AZURE_OPENAI_AUTH_METHOD"] != "api_key":
            raise ValueError("Unsupported authentication selection.")
        settings = AzureModelSettings(
            values["AZURE_OPENAI_BASE_URL"],
            values["AZURE_OPENAI_DEPLOYMENT"],
            values.get("AZURE_OPENAI_MODEL_ID", "gpt-6-luna"),
            values["AZURE_OPENAI_MODEL_VERSION"],
            values.get("AZURE_OPENAI_CONFIGURATION_ID", "azure-luna-config.v1"),
            values["AZURE_OPENAI_DEPLOYMENT_TYPE"],
        )
        key = credentials.get("AZURE_OPENAI_API_KEY", "")
        if not key or not key.isascii() or not key.isprintable() or len(key) > 4096:
            raise ModelProviderError(ModelErrorCode.CREDENTIALS_MISSING)
        return settings, key
    except (KeyError, ValueError):
        raise ModelProviderError(ModelErrorCode.CONFIGURATION) from None


class AzureResponsesTransport:
    """Only prepared text reaches this edge; no evidence or policy-store handles."""

    def __init__(
        self,
        settings: AzureModelSettings,
        api_key: str,
        guard: AdmissionGuard,
        *,
        connection_factory: Callable[
            ..., http.client.HTTPSConnection
        ] = http.client.HTTPSConnection,
    ) -> None:
        if (
            not api_key
            or not api_key.isascii()
            or not api_key.isprintable()
            or len(api_key) > 4096
        ):
            raise ModelProviderError(ModelErrorCode.CREDENTIALS_MISSING)
        self._settings = settings
        self._key = api_key
        self._guard = guard
        self._connection_factory = connection_factory

    def generate(self, request: ModelRequest) -> ModelReply:
        self._guard.verify(request)
        if (
            request.configuration != self._settings.configuration()
            or request.bounds.max_output_tokens < 16
        ):
            raise ModelProviderError(ModelErrorCode.CONFIGURATION)
        # Defense in depth for credential-bearing metadata or trusted templates.
        if (
            self._key in request.instructions
            or self._key in request.source_context
            or self._key in json.dumps(request.metadata())
        ):
            raise ModelProviderError(ModelErrorCode.POLICY)
        endpoint = urlsplit(self._settings.base_url)
        connection = None
        try:
            connection = self._connection_factory(
                endpoint.hostname,
                timeout=request.bounds.timeout_ms / 1000,
                context=ssl.create_default_context(),
            )
            connection.connect()
            self._guard.verify(request)
            connection.request(
                "POST",
                endpoint.path.rstrip("/") + "/responses",
                body=json.dumps(
                    {
                        "model": self._settings.deployment_id,
                        "instructions": request.instructions,
                        "input": request.source_context,
                        "text": {"format": {"type": "json_object"}},
                        "max_output_tokens": request.bounds.max_output_tokens,
                        "store": False,
                        "truncation": "disabled",
                    }
                ).encode(),
                headers={"Content-Type": "application/json", "api-key": self._key},
            )
            response = connection.getresponse()
            if response.status != 200:
                code = {
                    400: ModelErrorCode.CONFIGURATION,
                    401: ModelErrorCode.AUTHENTICATION,
                    403: ModelErrorCode.AUTHENTICATION,
                    404: ModelErrorCode.MODEL_UNAVAILABLE,
                    429: ModelErrorCode.RATE_LIMIT,
                }.get(response.status, ModelErrorCode.DEPENDENCY)
                diagnostics: dict[str, object] = {"http_status": response.status}
                # Keep only contract-allowlisted codes/parameter names; never body text.
                try:
                    error_body = response.read(
                        min(request.bounds.max_response_bytes, 16_384)
                    )
                    error = json.loads(error_body).get("error")
                    if isinstance(error, dict):
                        diagnostics["provider_error_code"] = error.get("code")
                        diagnostics["provider_error_parameter"] = error.get("param")
                except Exception:
                    pass
                raise ModelProviderError(code, diagnostics=diagnostics)
            body = response.read(request.bounds.max_response_bytes + 1)
            if len(body) > request.bounds.max_response_bytes:
                raise ModelProviderError(ModelErrorCode.OUTPUT_LIMIT)
            envelope = validate_model_reply(
                request, ModelReply(body.decode("utf-8"))
            ).structured_response()
            usage_value = envelope.get("usage")
            usage = (
                ModelUsage(
                    usage_value.get("input_tokens"), usage_value.get("output_tokens")
                )
                if isinstance(usage_value, dict)
                else ModelUsage()
            )
            reported_model = envelope.get("model")
            if not isinstance(reported_model, str) or reported_model not in (
                self._settings.model_id,
                self._settings.model_id + "-" + self._settings.model_version,
            ):
                raise ModelProviderError(ModelErrorCode.MODEL_UNAVAILABLE, usage=usage)
            if envelope.get("status") != "completed":
                detail = envelope.get("incomplete_details")
                reason = detail.get("reason") if isinstance(detail, dict) else None
                raise ModelProviderError(
                    ModelErrorCode.OUTPUT_LIMIT
                    if reason == "max_output_tokens"
                    else ModelErrorCode.MALFORMED_RESPONSE,
                    usage=usage,
                )
            output = envelope.get("output")
            if not isinstance(output, list):
                raise ModelProviderError(ModelErrorCode.MALFORMED_RESPONSE, usage=usage)
            texts: list[str] = []
            for item in output:
                if not isinstance(item, dict):
                    raise ModelProviderError(
                        ModelErrorCode.MALFORMED_RESPONSE, usage=usage
                    )
                if item.get("type") == "reasoning":
                    continue
                if (
                    item.get("type") != "message"
                    or item.get("role") != "assistant"
                    or not isinstance(item.get("content"), list)
                ):
                    raise ModelProviderError(
                        ModelErrorCode.MALFORMED_RESPONSE, usage=usage
                    )
                for part in item["content"]:
                    if (
                        not isinstance(part, dict)
                        or part.get("type") != "output_text"
                        or not isinstance(part.get("text"), str)
                    ):
                        raise ModelProviderError(
                            ModelErrorCode.MALFORMED_RESPONSE, usage=usage
                        )
                    texts.append(part["text"])
            operation_id = envelope.get("id")
            if (
                len(texts) != 1
                or not isinstance(operation_id, str)
                or self._key in operation_id
            ):
                raise ModelProviderError(ModelErrorCode.MALFORMED_RESPONSE, usage=usage)
            return ModelReply(
                texts[0], operation_id, usage, reported_model=reported_model
            )
        except ModelProviderError:
            raise
        except TimeoutError:
            raise ModelProviderError(ModelErrorCode.TIMEOUT) from None
        except (OSError, http.client.HTTPException):
            raise ModelProviderError(ModelErrorCode.DEPENDENCY) from None
        except (ValueError, TypeError, UnicodeError, KeyError):
            raise ModelProviderError(ModelErrorCode.MALFORMED_RESPONSE) from None
        except Exception:
            raise ModelProviderError(ModelErrorCode.DEPENDENCY) from None
        finally:
            if connection is not None:
                try:
                    connection.close()
                except Exception:
                    pass  # Closing must not expose dependency text or hide known usage.
