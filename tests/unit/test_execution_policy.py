"""Reject unbounded configuration before any invocation or monetary reservation."""

import unittest
from typing import Any, cast

from trace_app.investigation.execution import ExecutionIdentity, ExecutionPolicy
from trace_app.investigation.provider import ModelPricing, ModelProviderError


class ExecutionPolicyTests(unittest.TestCase):
    def test_all_limits_require_finite_supported_integers(self) -> None:
        for name in ExecutionPolicy.__dataclass_fields__:
            if name == "configuration_id":
                continue
            for value in (True, float("inf"), None, -1, 10_000_001):
                with (
                    self.subTest(name=name, value=value),
                    self.assertRaises(ValueError),
                ):
                    ExecutionPolicy(**cast(dict[str, Any], {name: value}))
            if name not in ("max_retries", "max_corrections"):
                with self.subTest(name=name), self.assertRaises(ValueError):
                    ExecutionPolicy(**cast(dict[str, Any], {name: 0}))
        with self.assertRaises(ValueError):
            ExecutionPolicy(max_tool_result_bytes=511)

    def test_safe_identity_and_versioned_positive_pricing(self) -> None:
        with self.assertRaises(ValueError):
            ExecutionIdentity("inv", True, "corr", "scope")
        with self.assertRaises(ValueError):
            ExecutionIdentity("inv", 1, "person@example.invalid", "scope")
        for values in (("invalid price", 1, 1), ("v1", 0, 1), ("v1", 1, True)):
            with self.assertRaises(ModelProviderError):
                ModelPricing(*values)
        self.assertEqual(ModelPricing("v1", 2, 3).estimate(5, 7), 31)
