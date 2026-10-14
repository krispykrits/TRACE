"""Strict schema and frozen evaluator compatibility, without provider services."""

from __future__ import annotations

import copy
import unittest

from tests.fixtures.assessments import report
from trace_app.investigation.assessment import CandidateReport, ReportInputError
from trace_app.investigation.assessment_schema import AssessmentReport


class AssessmentSchemaTests(unittest.TestCase):
    def test_v2_supported_abstaining_and_v1_projection(self) -> None:
        for abstained in (False, True):
            value = report(abstained)
            parsed = AssessmentReport.from_dict(value)
            self.assertEqual(parsed.to_dict(), value)
            self.assertEqual(
                CandidateReport.from_dict(parsed.candidate.to_dict()), parsed.candidate
            )
            value["uncertainty"] = "changed after parsing"
            self.assertNotEqual(parsed.to_dict()["uncertainty"], value["uncertainty"])

    def test_unknown_fields_limits_mutation_and_status_mismatches_reject(self) -> None:
        mutations = (
            lambda v: v.update(confidence=0.99),
            lambda v: v.update(schema_version="1"),
            lambda v: v.pop("uncertainty"),
            lambda v: v.update(uncertainty="x" * 2001),
            lambda v: v.update(source_gaps=["knowledge:missing"] * 2),
            lambda v: v["observations"][0].update(citations=[]),
            lambda v: v["observations"][0].update(claim_id="hypothesis-1"),
            lambda v: v["primary_hypothesis"].update(
                contradicting_citations=["evidence-1"]
            ),
            lambda v: v["primary_hypothesis"].update(
                causal_basis="calibrated_probability"
            ),
            lambda v: v.update(assessment_status="failed"),
            lambda v: v.update(assessment_status="abstained"),
            lambda v: v["next_check"].update(tool="production.restart"),
            lambda v: v["next_check"]["arguments"].update(limit=101),
            lambda v: v["next_check"]["arguments"].update(command="restart"),
            lambda v: v["next_check"]["arguments"].update(access_scope="forged"),
        )
        for mutation in mutations:
            value = copy.deepcopy(report())
            mutation(value)
            with self.assertRaises(ReportInputError):
                AssessmentReport.from_dict(value)

    def test_duplicate_contradiction_and_excessive_context_are_explicit(self) -> None:
        value = report()
        value["primary_hypothesis"]["contradicting_citations"] = ["evidence-2"] * 2
        with self.assertRaises(ReportInputError):
            AssessmentReport.from_dict(value)
        value = report()
        value["missing_evidence"] = ["large" * 2000] * 100
        with self.assertRaises(ReportInputError):
            AssessmentReport.from_dict(value)


if __name__ == "__main__":
    unittest.main()
