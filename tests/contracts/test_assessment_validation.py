"""Support stays separate from current citations and protected content access."""

from __future__ import annotations

import io
import json
import logging
import unittest
from dataclasses import replace

from tests.fixtures.assessments import SCOPE, fixture, package, report
from trace_app.investigation.assessment_context import (
    AssessmentBoundaryError,
    AssessmentContext,
)
from trace_app.investigation.provider import ModelProviderError
from trace_app.investigation.provider_policy import ProviderScope, Sensitivity
from trace_app.runtime.logging import configure_logging


class AssessmentValidationTests(unittest.TestCase):
    def test_valid_ids_remain_unreviewed_and_prepare_a_sampled_packet(self) -> None:
        validator, response, _, _, _ = fixture()
        result = validator.validate(response, SCOPE)
        self.assertEqual(
            (result.outcome, result.citation_validity, result.claim_support),
            ("review_required", "valid", "unreviewed"),
        )
        handle = result.assessment
        assert handle is not None
        packet = handle.review_packet(SCOPE, ("hypothesis-1",))
        self.assertEqual(len(packet["tasks"]), 1)
        self.assertEqual(packet["tasks"][0]["contradicting_citations"], ["evidence-2"])
        self.assertFalse(packet["mutation_authority"])
        with self.assertRaises(AssessmentBoundaryError):
            handle.read(SCOPE)
        with self.assertRaises(AssessmentBoundaryError):
            handle.review_packet(SCOPE, ("invented",))

    def test_reviewed_answerable_and_insufficient_assessments_preserve_timeline(
        self,
    ) -> None:
        for abstained in (False, True):
            validator, response, _, reviews, _ = fixture(report(abstained))
            pending = validator.validate(response, SCOPE)
            assert pending.assessment is not None
            reviews.endorse(pending.assessment)
            accepted = validator.validate(response, SCOPE)
            self.assertEqual(accepted.outcome, "accepted")
            assert accepted.assessment is not None
            body = accepted.assessment.read(SCOPE)
            self.assertEqual(
                body["report"]["assessment_status"],
                "abstained" if abstained else "supported",
            )
            self.assertTrue(
                all(
                    "collected_at" in e and e["causal_status"] == "observed"
                    for e in body["timeline"]
                )
            )
            self.assertFalse(body["mutation_authority"])

    def test_valid_but_nonsupporting_or_disputed_citation_never_becomes_accepted(
        self,
    ) -> None:
        for verdict, expected in (
            ("unsupported", "rejected"),
            ("indeterminate", "review_required"),
        ):
            validator, response, _, reviews, _ = fixture()
            pending = validator.validate(response, SCOPE)
            assert pending.assessment is not None
            reviews.endorse(pending.assessment, verdict=verdict)
            result = validator.validate(response, SCOPE)
            self.assertEqual(
                (result.outcome, result.citation_validity, result.claim_support),
                (expected, "valid", verdict),
            )
            with self.assertRaises(AssessmentBoundaryError):
                pending.assessment.read(SCOPE)
        validator, response, _, reviews, _ = fixture()
        pending = validator.validate(response, SCOPE)
        assert pending.assessment is not None
        reviews.endorse(pending.assessment)
        key = next(iter(reviews.decisions))
        original = reviews.decisions[key][0]
        reviews.decisions[key] += (
            replace(
                original, verdict="unsupported", reviewer_id="second-synthetic-reviewer"
            ),
        )
        self.assertEqual(validator.validate(response, SCOPE).claim_support, "disputed")

    def test_fixture_expectations_and_model_declared_reviews_cannot_grant_support(
        self,
    ) -> None:
        validator, response, _, reviews, _ = fixture()
        pending = validator.validate(response, SCOPE)
        assert pending.assessment is not None
        reviews.endorse(pending.assessment, kind="fixture_expectation")
        rejected = validator.validate(response, SCOPE)
        self.assertEqual(rejected.reason, "invalid_review")
        self.assertEqual(rejected.citation_validity, "valid")
        value = report()
        value["support_reviews"] = [{"verdict": "supported"}]
        validator, response, _, _, _ = fixture(value)
        self.assertEqual(
            validator.validate(response, SCOPE).reason, "malformed_assessment"
        )

    def test_invented_denied_changed_and_out_of_context_citations_reject(self) -> None:
        value = report()
        value["observations"][0]["citations"] = ["invented-id"]
        validator, response, _, _, _ = fixture(value)
        self.assertEqual(
            validator.validate(response, SCOPE).reason, "citation_not_admitted"
        )
        validator, response, _, _, resolver = fixture()
        resolver.denied.add("evidence-2")
        self.assertEqual(validator.validate(response, SCOPE).reason, "citation_denied")
        resolver.denied.clear()
        resolver.revision = "changed"
        self.assertEqual(
            validator.validate(response, SCOPE).reason, "citation_mismatch"
        )

    def test_temporal_or_score_only_primary_and_omitted_gaps_reject(self) -> None:
        for basis in ("temporal_only", "score_only", "context_only"):
            value = report()
            value["primary_hypothesis"]["causal_basis"] = basis
            validator, response, _, _, _ = fixture(value)
            self.assertEqual(
                validator.validate(response, SCOPE).reason, "unsupported_causal_basis"
            )
        variants: tuple[dict[str, list[str]], ...] = (
            {"source_gaps": []},
            {"missing_evidence": []},
            {"timeline_evidence_ids": ["evidence-2", "evidence-1"]},
        )
        for changes in variants:
            value = report()
            value.update(changes)
            validator, response, _, _, _ = fixture(value)
            self.assertIn(
                validator.validate(response, SCOPE).reason,
                ("source_gaps_missing", "timeline_mismatch"),
            )
        value = report()
        value["next_check"]["arguments"]["window_end"] = "2026-10-12T12:11:00Z"
        validator, response, _, _, _ = fixture(value)
        self.assertEqual(
            validator.validate(response, SCOPE).reason, "next_check_outside_window"
        )

    def test_generated_and_review_artifacts_inherit_sensitivity_without_wider_access(
        self,
    ) -> None:
        validator, response, authority, reviews, _ = fixture(
            sensitivity=Sensitivity.SECRET
        )
        pending = validator.validate(response, SCOPE)
        assert pending.assessment is not None
        handle = pending.assessment
        reviews.endorse(handle)
        body = handle.read(SCOPE)
        self.assertEqual(body["sensitivity"], "secret")
        self.assertEqual(
            body["citations"]["evidence-1"]["fields"]["observation"], "[REDACTED]"
        )
        self.assertTrue(body["citations"]["evidence-1"]["redactions"])
        for forbidden in (
            ProviderScope("different-user", SCOPE.investigation_id),
            ProviderScope(SCOPE.principal_id, "other-investigation"),
        ):
            with self.assertRaises(AssessmentBoundaryError):
                handle.read(forbidden)
        clone = replace(handle, _response=response)
        # An identical frozen clone is equivalent; changing the backing response is not.
        other = fixture()[1]
        with self.assertRaises(AssessmentBoundaryError):
            replace(clone, _response=other).read(SCOPE)
        authority.records["evidence-1"] = replace(
            authority.records["evidence-1"], transmission_allowed=False
        )
        self.assertEqual(handle.read(SCOPE)["sensitivity"], "secret")
        with self.assertRaises(ModelProviderError):
            handle.export(SCOPE)
        authority.records["evidence-1"] = replace(
            authority.records["evidence-1"], access_allowed=False
        )
        with self.assertRaises(ModelProviderError):
            handle.read(SCOPE)

    def test_changed_or_withdrawn_review_requires_new_acceptance(self) -> None:
        validator, response, _, reviews, _ = fixture()
        pending = validator.validate(response, SCOPE)
        assert pending.assessment is not None
        reviews.endorse(pending.assessment)
        original_decisions = dict(reviews.decisions)
        self.assertEqual(pending.assessment.read(SCOPE)["citation_validity"], "valid")
        reviews.decisions.clear()
        with self.assertRaises(AssessmentBoundaryError):
            pending.assessment.read(SCOPE)
        value = report()
        value["uncertainty"] = "A materially different uncertainty statement."
        other, other_response, _, other_reviews, _ = fixture(value)
        other_reviews.decisions = original_decisions
        self.assertEqual(
            other.validate(other_response, SCOPE).outcome, "review_required"
        )

    def test_execution_failures_remain_failures_and_audit_is_content_free(self) -> None:
        validator, response, _, _, resolver = fixture(report(True))
        resolver.failure = True
        self.assertEqual(
            validator.validate(response, SCOPE).outcome, "execution_failed"
        )
        failed = replace(package(), status="failed", data=None, data_sha256=None)
        with self.assertRaises(AssessmentBoundaryError) as failure:
            AssessmentContext.from_package(failed, SCOPE)
        self.assertEqual(failure.exception.code, "execution_failure")
        stream = io.StringIO()
        configure_logging(stream=stream, correlation_id="assessment-contract")
        self.addCleanup(logging.getLogger("trace_app").handlers.clear)
        resolver.failure = False
        validator.validate(response, SCOPE)
        record = json.loads(stream.getvalue())
        self.assertEqual(record["correlation_id"], "assessment-contract")
        self.assertTrue(record["provider_request_id"])
        self.assertNotIn(report(True)["abstention_reason"], stream.getvalue())
        self.assertNotIn("statement", stream.getvalue())

    def test_review_side_effect_cannot_release_revoked_response(self) -> None:
        validator, response, authority, reviews, _ = fixture()
        pending = validator.validate(response, SCOPE)
        assert pending.assessment is not None
        reviews.endorse(pending.assessment)
        original = reviews.read

        def read(scope, binding):
            decisions = original(scope, binding)
            authority.records["evidence-1"] = replace(
                authority.records["evidence-1"], access_allowed=False
            )
            return decisions

        reviews.read = read
        self.assertEqual(validator.validate(response, SCOPE).reason, "access_denied")

    def test_component_failure_is_not_a_source_gap_or_abstention(self) -> None:
        from trace_app.knowledge.models import canonical, digest

        value = package().data
        assert value is not None
        value["timeline"]["status"] = "storage_failure"
        invalid = replace(package(), data=value, data_sha256=digest(canonical(value)))
        with self.assertRaises(AssessmentBoundaryError) as failure:
            AssessmentContext.from_package(invalid, SCOPE)
        self.assertEqual(failure.exception.code, "execution_failure")

    def test_dependency_code_does_not_echo_arbitrary_adapter_content(self) -> None:
        self.assertEqual(
            AssessmentBoundaryError("opaque-untrusted-error-content").code,
            "dependency_failure",
        )


if __name__ == "__main__":
    unittest.main()
