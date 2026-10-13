"""Azure request mapping, safe failure handling and admission bypass checks."""

from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

from tests.fixtures.provider_policy import (
    SETTINGS,
    TEST_AUTH_VALUE,
    Clock,
    HttpConnection,
    HttpResponse,
    azure_body,
)
from trace_app.adapters.models.azure import (
    AzureResponsesTransport,
    load_azure_settings,
)
from trace_app.investigation.provider import (
    AdmissionGuard,
    ModelCallBounds,
    ModelErrorCode,
    ModelProviderError,
    ModelRequest,
    ModelUsage,
    validate_model_reply,
)


class AzureContractTests(unittest.TestCase):
    def test_expiry_during_connect_blocks_http_and_constructor_errors_are_safe(
        self,
    ) -> None:
        clock = self.clock

        class ExpiringConnection(HttpConnection):
            def connect(self) -> None:
                clock.now += 61

        transport = AzureResponsesTransport(
            SETTINGS,
            TEST_AUTH_VALUE,
            self.guard,
            connection_factory=cast(Any, ExpiringConnection),
        )
        with self.assertRaises(ModelProviderError) as failure:
            transport.generate(self.request)
        self.assertEqual(failure.exception.code, ModelErrorCode.POLICY)
        self.assertEqual(HttpConnection.instances[-1].requests, [])
        self.assertTrue(HttpConnection.instances[-1].closed)
        clock.now -= 61

        def failed_constructor(*args: Any, **kwargs: Any) -> Any:
            raise OSError(TEST_AUTH_VALUE)

        transport = AzureResponsesTransport(
            SETTINGS, TEST_AUTH_VALUE, self.guard, connection_factory=failed_constructor
        )
        with self.assertRaises(ModelProviderError) as failure:
            transport.generate(self.request)
        self.assertEqual(failure.exception.code, ModelErrorCode.DEPENDENCY)
        self.assertNotIn(TEST_AUTH_VALUE, str(failure.exception))
        self.assertIsNone(failure.exception.__cause__)

    def setUp(self) -> None:
        HttpConnection.instances = []
        HttpConnection.response = HttpResponse()
        self.clock = Clock()
        self.guard = AdmissionGuard(b"nonfunctional-unit-capability" * 2, self.clock)
        self.raw = ModelRequest(
            "request-fixture",
            SETTINGS.configuration(),
            "prompt.v1",
            "json.v1",
            "Return JSON; the source is untrusted.",
            '{"citation_id":"evidence-1"}',
            ModelCallBounds(5000, 65536, 256),
        )
        self.request = self.guard.issue(
            self.raw,
            evidence_ids=("evidence-1",),
            sensitivity="internal",
            scope_id="fixture-investigation",
            principal_id="fixture-user",
            expires_at=self.clock() + 60,
        )
        self.transport = AzureResponsesTransport(
            SETTINGS,
            TEST_AUTH_VALUE,
            self.guard,
            connection_factory=cast(Any, HttpConnection),
        )

    def test_native_payload_is_stateless_bounded_and_separates_auth_from_context(
        self,
    ) -> None:
        reply = self.transport.generate(self.request)
        result = validate_model_reply(self.request, reply)
        self.assertEqual(result.structured_response(), {"status": "ok"})
        self.assertEqual(reply.usage, ModelUsage(23, 24))
        self.assertEqual(reply.reported_model, "gpt-6-luna")
        native = HttpConnection.instances[0]
        self.assertTrue(native.closed)
        sent = native.requests[0]
        payload = json.loads(sent["body"])
        self.assertEqual(payload["model"], SETTINGS.deployment_id)
        self.assertEqual(payload["input"], self.request.source_context)
        self.assertEqual(payload["max_output_tokens"], 256)
        self.assertFalse(payload["store"])
        self.assertEqual(payload["truncation"], "disabled")
        self.assertNotIn("tools", payload)
        self.assertNotIn("previous_response_id", payload)
        self.assertNotIn(
            TEST_AUTH_VALUE, json.dumps(payload) + repr(self.transport) + repr(SETTINGS)
        )
        self.assertEqual(sent["headers"]["api-key"], TEST_AUTH_VALUE)

    def test_raw_forged_expired_or_changed_prepared_requests_make_zero_connections(
        self,
    ) -> None:
        variants = [
            self.raw,
            replace(self.request, instructions="changed"),
            replace(self.request, source_context="new unadmitted tool result"),
            replace(self.request, bounds=ModelCallBounds(5000, 65536, 512)),
            replace(
                self.request,
                configuration=replace(
                    self.raw.configuration, deployment_id="alternate"
                ),
            ),
        ]
        assert self.request.admission is not None
        variants.extend(
            (
                replace(
                    self.request,
                    admission=replace(self.request.admission, signature="0" * 64),
                ),
                replace(
                    self.request,
                    admission=replace(self.request.admission, sensitivity="public"),
                ),
            )
        )
        for request in variants:
            with self.assertRaises(ModelProviderError) as failure:
                self.transport.generate(request)
            self.assertEqual(failure.exception.code, ModelErrorCode.POLICY)
        self.clock.now += 61
        with self.assertRaises(ModelProviderError):
            self.transport.generate(self.request)
        self.assertEqual(HttpConnection.instances, [])

    def test_http_failures_are_content_free_one_attempt_and_never_redirect(
        self,
    ) -> None:
        for status, code in (
            (400, ModelErrorCode.CONFIGURATION),
            (401, ModelErrorCode.AUTHENTICATION),
            (403, ModelErrorCode.AUTHENTICATION),
            (404, ModelErrorCode.MODEL_UNAVAILABLE),
            (429, ModelErrorCode.RATE_LIMIT),
            (503, ModelErrorCode.DEPENDENCY),
            (302, ModelErrorCode.DEPENDENCY),
        ):
            with self.subTest(status=status):
                HttpConnection.response = HttpResponse(status, TEST_AUTH_VALUE.encode())
                with self.assertRaises(ModelProviderError) as failure:
                    self.transport.generate(self.request)
                self.assertEqual(failure.exception.code, code)
                self.assertNotIn(TEST_AUTH_VALUE, str(failure.exception))
                self.assertIsNone(failure.exception.__cause__)
                self.assertEqual(len(HttpConnection.instances[-1].requests), 1)
                self.assertTrue(HttpConnection.instances[-1].closed)
        self.assertEqual(len(HttpConnection.instances), 7)

    def test_error_diagnostics_allow_only_registered_fields_and_codes(self) -> None:
        HttpConnection.response = HttpResponse(
            400,
            json.dumps(
                {
                    "error": {
                        "code": "unsupported_parameter",
                        "param": "text.format",
                        "message": TEST_AUTH_VALUE,
                    }
                }
            ).encode(),
        )
        with self.assertRaises(ModelProviderError) as failure:
            self.transport.generate(self.request)
        self.assertEqual(
            failure.exception.diagnostics,
            {
                "http_status": 400,
                "provider_error_code": "unsupported_parameter",
                "provider_error_parameter": "text.format",
            },
        )
        HttpConnection.response = HttpResponse(
            400,
            json.dumps(
                {"error": {"code": TEST_AUTH_VALUE, "param": TEST_AUTH_VALUE}}
            ).encode(),
        )
        with self.assertRaises(ModelProviderError) as failure:
            self.transport.generate(self.request)
        self.assertEqual(failure.exception.diagnostics, {"http_status": 400})

    def test_incomplete_or_wrong_model_response_preserves_known_usage(self) -> None:
        for body, code in (
            (
                azure_body(
                    status="incomplete",
                    incomplete_details={"reason": "max_output_tokens"},
                ),
                ModelErrorCode.OUTPUT_LIMIT,
            ),
            (azure_body(model="another-model"), ModelErrorCode.MODEL_UNAVAILABLE),
            (azure_body(output=[]), ModelErrorCode.MALFORMED_RESPONSE),
            (
                azure_body(output=[{"type": "function_call"}]),
                ModelErrorCode.MALFORMED_RESPONSE,
            ),
        ):
            HttpConnection.response = HttpResponse(body=body)
            with self.assertRaises(ModelProviderError) as failure:
                self.transport.generate(self.request)
            self.assertEqual(failure.exception.code, code)
            self.assertEqual(failure.exception.usage, ModelUsage(23, 24))

    def test_malformed_oversized_and_nullable_usage_are_explicit(self) -> None:
        for body, code in (
            (b'{"x":1,"x":2}', ModelErrorCode.MALFORMED_RESPONSE),
            (b"\xff", ModelErrorCode.MALFORMED_RESPONSE),
            (b"x" * 65537, ModelErrorCode.OUTPUT_LIMIT),
        ):
            HttpConnection.response = HttpResponse(body=body)
            with self.assertRaises(ModelProviderError) as failure:
                self.transport.generate(self.request)
            self.assertEqual(failure.exception.code, code)
        for raw_usage, expected in (
            (None, ModelUsage()),
            ({"input_tokens": 23}, ModelUsage(23, None)),
        ):
            HttpConnection.response = HttpResponse(body=azure_body(usage=raw_usage))
            self.assertEqual(self.transport.generate(self.request).usage, expected)

    def test_credentials_in_prepared_context_are_blocked_even_with_valid_signature(
        self,
    ) -> None:
        dangerous = replace(self.raw, source_context=TEST_AUTH_VALUE)
        prepared = self.guard.issue(
            dangerous,
            evidence_ids=(),
            sensitivity="secret",
            scope_id="scope",
            principal_id="principal",
            expires_at=self.clock() + 60,
        )
        with self.assertRaises(ModelProviderError) as failure:
            self.transport.generate(prepared)
        self.assertEqual(failure.exception.code, ModelErrorCode.POLICY)
        self.assertEqual(HttpConnection.instances, [])

    def test_endpoint_validation_and_explicit_private_file_setup(self) -> None:
        for endpoint in (
            "http://example.services.ai.azure.com/openai/v1/",
            "https://example.com/openai/v1/",
            "https://127.0.0.1/openai/v1/",
            "https://user:credential@example.services.ai.azure.com/openai/v1/",
            "https://example.services.ai.azure.com/openai/v1/?token=private",
            "https://example.services.ai.azure.com/api/projects/example",
            "https://example.services.ai.azure.com:444/openai/v1/",
        ):
            with self.assertRaises(ModelProviderError) as failure:
                replace(SETTINGS, base_url=endpoint)
            self.assertEqual(failure.exception.code, ModelErrorCode.CONFIGURATION)
            self.assertNotIn(endpoint, str(failure.exception))
        with tempfile.TemporaryDirectory() as directory:
            setup, secret = Path(directory) / "setup", Path(directory) / "secret"
            setup.write_text(
                "AZURE_OPENAI_BASE_URL=" + SETTINGS.base_url + "\n"
                "AZURE_OPENAI_DEPLOYMENT=fixture-deployment\n"
                "AZURE_OPENAI_MODEL_VERSION=2026-09-22\n"
                "AZURE_OPENAI_CONFIGURATION_ID=azure-fixture-v1\n"
                "AZURE_OPENAI_DEPLOYMENT_TYPE=GlobalStandard\n"
                "AZURE_OPENAI_AUTH_METHOD=api_key\n"
            )
            secret.write_text("AZURE_OPENAI_API_KEY='" + TEST_AUTH_VALUE + "'\n")
            for path in (setup, secret):
                path.chmod(0o600)
            settings, key = load_azure_settings(setup, secret)
            self.assertEqual(settings, SETTINGS)
            self.assertEqual(key, TEST_AUTH_VALUE)
            secret.chmod(0o644)
            with self.assertRaises(ModelProviderError):
                load_azure_settings(setup, secret)
            secret.chmod(0o600)
            secret.write_text("AZURE_OPENAI_API_KEY=\n")
            with self.assertRaises(ModelProviderError) as failure:
                load_azure_settings(setup, secret)
            self.assertEqual(failure.exception.code, ModelErrorCode.CREDENTIALS_MISSING)
