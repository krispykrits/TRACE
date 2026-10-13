"""Provider-neutral contract checks; fixture output earns no live credit."""

from __future__ import annotations

import json
import unittest
from dataclasses import replace
from typing import Any, cast

from tests.fixtures.model_provider import (
    FAKE_CAPABILITIES,
    FAKE_CONFIGURATION,
    FakeModelTransport,
    fixture_request,
)
from trace_app.investigation.provider import (
    MODEL_CONTRACT_VERSION,
    ModelCallBounds,
    ModelConfiguration,
    ModelErrorCode,
    ModelProviderError,
    ModelReply,
    ModelUsage,
    validate_model_readiness,
    validate_model_reply,
)


class ModelContractTests(unittest.TestCase):
    def test_versioned_structured_result_and_content_free_metadata(self) -> None:
        request = fixture_request(source_context="PRIVATE-SOURCE")
        result = validate_model_reply(request, FakeModelTransport().generate(request))
        self.assertEqual(result.structured_response(), {"fixture": True})
        result.structured_response()["fixture"] = False
        self.assertEqual(result.structured_response(), {"fixture": True})
        metadata = result.metadata()
        self.assertEqual(metadata["contract_version"], MODEL_CONTRACT_VERSION)
        self.assertEqual(metadata["provider_operation_id"], "fixture-operation-1")
        self.assertEqual(metadata["configuration"], FAKE_CONFIGURATION.to_dict())
        self.assertNotIn(
            "PRIVATE-SOURCE", json.dumps(metadata) + repr(request) + repr(result)
        )
        self.assertNotIn('fixture":true', repr(result.reply))

    def test_usage_absence_and_partial_counts_remain_explicit(self) -> None:
        for usage, availability in (
            (ModelUsage(), "unavailable"),
            (ModelUsage(2), "partial"),
            (ModelUsage(None, 3), "partial"),
            (ModelUsage(0, 0), "available"),
        ):
            with self.subTest(availability=availability, usage=usage):
                result = validate_model_reply(
                    fixture_request(), ModelReply("{}", usage=usage)
                )
                self.assertEqual(result.metadata()["usage"], usage.to_dict())
                self.assertEqual(usage.to_dict()["availability"], availability)
                self.assertIsNone(result.metadata()["provider_operation_id"])

    def test_rejects_malformed_nonobject_duplicate_nonfinite_and_deep_json(
        self,
    ) -> None:
        examples = (
            "raw-secret",
            "[]",
            "null",
            '{"x":1,"x":2}',
            '{"x":NaN}',
            '{"x":1e999}',
            '{"x":' + "[" * 1100 + "0" + "]" * 1100 + "}",
            "\ud800",
            '{"x":"\\ud800"}',
        )
        for value in examples:
            with self.subTest(value_length=len(value)):
                with self.assertRaises(ModelProviderError) as failure:
                    validate_model_reply(fixture_request(), ModelReply(value))
                self.assertEqual(
                    failure.exception.code, ModelErrorCode.MALFORMED_RESPONSE
                )
                self.assertNotIn("raw-secret", str(failure.exception))

    def test_byte_and_token_bounds_and_truncation_reject_partial_output(self) -> None:
        request = fixture_request(bounds=ModelCallBounds(1000, 10, 5))
        for reply in (
            ModelReply('{"x":"\u00e9\u00e9\u00e9"}'),
            ModelReply("{}", usage=ModelUsage(1, 6)),
            ModelReply("{}", finish_reason="output_limit"),
        ):
            with self.subTest(reply=reply):
                with self.assertRaises(ModelProviderError) as failure:
                    validate_model_reply(request, reply)
                self.assertEqual(failure.exception.code, ModelErrorCode.OUTPUT_LIMIT)

    def test_unrecognized_finish_and_operation_identifiers_are_safe_failures(
        self,
    ) -> None:
        for reply in (
            ModelReply("{}", finish_reason="refused"),
            ModelReply("{}", "private value\n"),
        ):
            with self.assertRaises(ModelProviderError) as failure:
                validate_model_reply(fixture_request(), reply)
            self.assertEqual(failure.exception.code, ModelErrorCode.MALFORMED_RESPONSE)

    def test_invalid_bounds_and_request_configuration_do_not_echo_values(self) -> None:
        for values in ((True, 10, 10), (0, 10, 10), (1, 1_000_001, 10), (1, 10, -1)):
            with self.assertRaises(ModelProviderError):
                ModelCallBounds(*values)
        for changes in (
            {"request_id": "raw secret\n"},
            {"source_context": " "},
            {"source_context": "x" * 131_073},
            {"contract_version": "unrecognized"},
        ):
            with self.assertRaises(ModelProviderError) as failure:
                fixture_request(**changes)
            self.assertEqual(failure.exception.code, ModelErrorCode.CONFIGURATION)
            self.assertNotIn("raw secret", str(failure.exception))
        config_changes: dict[str, Any]
        for config_changes in (
            {"automatic_retries": 1},
            {"automatic_retries": False},
            {"response_format": "text"},
            {"model_id": ""},
        ):
            with self.assertRaises(ModelProviderError):
                replace(FAKE_CONFIGURATION, **config_changes)

    def test_missing_unknown_and_secret_configuration_fields_are_rejected(self) -> None:
        self.assertEqual(
            ModelConfiguration.from_dict(FAKE_CONFIGURATION.to_dict()),
            FAKE_CONFIGURATION,
        )
        for value in (
            None,
            {},
            {**FAKE_CONFIGURATION.to_dict(), "credential": "PRIVATE"},
        ):
            with self.assertRaises(ModelProviderError) as failure:
                ModelConfiguration.from_dict(value)
            self.assertEqual(failure.exception.code, ModelErrorCode.CONFIGURATION)
            self.assertNotIn("PRIVATE", str(failure.exception))

    def test_offline_fixture_is_explicit_and_cannot_be_selected_as_live(self) -> None:
        self.assertEqual(
            validate_model_readiness(
                FAKE_CONFIGURATION, FAKE_CAPABILITIES, credential_present=False
            ),
            "offline_test_only",
        )
        with self.assertRaises(ModelProviderError) as failure:
            validate_model_readiness(
                replace(FAKE_CONFIGURATION, mode="live"),
                FAKE_CAPABILITIES,
                credential_present=False,
            )
        self.assertEqual(failure.exception.code, ModelErrorCode.CONFIGURATION)

    def test_preflight_reports_missing_credentials_models_and_capabilities(
        self,
    ) -> None:
        config = replace(FAKE_CONFIGURATION, mode="live")
        caps = replace(FAKE_CAPABILITIES, offline_only=False, credentials_required=True)
        for configuration, capabilities, present, code in (
            (config, caps, False, ModelErrorCode.CREDENTIALS_MISSING),
            (
                replace(config, model_id="unsupported"),
                caps,
                True,
                ModelErrorCode.MODEL_UNAVAILABLE,
            ),
            (
                config,
                replace(caps, structured_json=False),
                True,
                ModelErrorCode.CAPABILITY_UNSUPPORTED,
            ),
            (
                config,
                replace(caps, output_token_limit=False),
                True,
                ModelErrorCode.CAPABILITY_UNSUPPORTED,
            ),
            (
                replace(config, adapter_version="wrong"),
                caps,
                True,
                ModelErrorCode.CONFIGURATION,
            ),
        ):
            with self.subTest(code=code):
                with self.assertRaises(ModelProviderError) as failure:
                    validate_model_readiness(
                        configuration, capabilities, credential_present=present
                    )
                self.assertEqual(failure.exception.code, code)
        self.assertEqual(
            validate_model_readiness(config, caps, credential_present=True),
            "live_check_required",
        )

    def test_usage_rejects_negative_and_boolean_counts(self) -> None:
        for value in (-1, True, "1"):
            with self.assertRaises(ModelProviderError):
                ModelUsage(cast(Any, value), None)
