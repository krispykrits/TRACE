"""Saved dependencies retain authority independently of text, IDs and schema validity."""

from __future__ import annotations

import json
import unittest
from dataclasses import replace

from tests.fixtures.provider_policy import SCOPE, policy_fixture, record
from trace_app.investigation.provider import ModelProviderError
from trace_app.investigation.provider_policy import (
    EvidenceField,
    EvidenceSelection,
    ProviderScope,
    Sensitivity,
    SourceAccessPolicy,
)


class SavedSourceAccessTests(unittest.TestCase):
    def test_redacted_response_keeps_original_sensitivity_after_restoration(
        self,
    ) -> None:
        from tests.fixtures.provider_policy import call

        policy, _, authority, _ = policy_fixture()
        authority.records["evidence-1"] = record(
            fields=(
                EvidenceField(
                    "observation",
                    "contact investigator@example.invalid",
                    Sensitivity.RESTRICTED,
                    True,
                ),
            )
        )
        response = policy.generate(call())
        binding = json.loads(json.dumps(response.storage_binding(SCOPE)))
        access = SourceAccessPolicy(authority, SCOPE, clock=policy._clock)
        access.check_saved(
            binding, transmission=False, clearance=Sensitivity.RESTRICTED
        )
        self.assertNotIn(
            "investigator@example.invalid",
            json.dumps(response.citation_views(SCOPE)[0].to_dict()),
        )
        with self.assertRaises(ModelProviderError):
            access.check_saved(
                binding, transmission=False, clearance=Sensitivity.PUBLIC
            )
        # A malformed stored classification cannot declassify original dependencies.
        binding["sensitivity"] = "public"
        with self.assertRaises(ModelProviderError):
            access.check_saved(
                binding, transmission=False, clearance=Sensitivity.PUBLIC
            )

    def test_saved_actor_revisions_review_expiry_and_transmission_remain_current(
        self,
    ) -> None:
        from tests.fixtures.provider_policy import NOW, call

        policy, _, authority, _ = policy_fixture()
        response = policy.generate(call())
        binding = response.storage_binding(SCOPE)
        access = SourceAccessPolicy(authority, SCOPE, clock=lambda: NOW)
        original = authority.records["evidence-1"]
        for changes in (
            {"access_allowed": False},
            {"revision": "revision-2"},
            {"identifiers_reviewed": False},
            {"expires_at": NOW - 1},
        ):
            with self.subTest(changes=changes):
                authority.records["evidence-1"] = replace(original, **changes)
                with self.assertRaises(ModelProviderError):
                    access.check_saved(
                        binding, transmission=False, clearance=Sensitivity.RESTRICTED
                    )
        authority.records["evidence-1"] = replace(original, transmission_allowed=False)
        access.check_saved(
            binding, transmission=False, clearance=Sensitivity.RESTRICTED
        )
        with self.assertRaises(ModelProviderError):
            access.check_saved(
                binding, transmission=True, clearance=Sensitivity.RESTRICTED
            )
        with self.assertRaises(ModelProviderError):
            SourceAccessPolicy(
                authority,
                ProviderScope("different-actor", SCOPE.investigation_id),
                clock=lambda: NOW,
            ).check_saved(binding, transmission=False, clearance=Sensitivity.RESTRICTED)

    def test_unbound_or_unknown_sensitivity_never_restores(self) -> None:
        _, _, authority, _ = policy_fixture()
        from tests.fixtures.provider_policy import NOW

        access = SourceAccessPolicy(authority, SCOPE, clock=lambda: NOW)
        with self.assertRaises(ModelProviderError):
            access.check_saved({}, transmission=False, clearance=Sensitivity.RESTRICTED)
        authority.records["evidence-1"] = record(
            fields=(
                EvidenceField(
                    "observation", "Unclassified text", Sensitivity.UNKNOWN, True
                ),
            )
        )
        binding = access.bind(
            (EvidenceSelection("evidence-1", "revision-1", ("observation",)),)
        )
        with self.assertRaises(ModelProviderError):
            access.check_saved(
                binding, transmission=False, clearance=Sensitivity.RESTRICTED
            )

    def test_package_binding_rejects_a_source_changed_between_access_and_retention(
        self,
    ) -> None:
        from tests.fixtures.provider_policy import NOW

        _, _, authority, _ = policy_fixture()
        authority.records["evidence-1"] = record(
            fields=(
                EvidenceField(
                    "content", "Current original", Sensitivity.INTERNAL, True
                ),
            )
        )
        policy = SourceAccessPolicy(authority, SCOPE, clock=lambda: NOW)
        with self.assertRaises(ModelProviderError):
            policy.bind(
                (EvidenceSelection("evidence-1", "revision-1", ("content",)),),
                expected_content={"evidence-1": "Earlier package content"},
            )
