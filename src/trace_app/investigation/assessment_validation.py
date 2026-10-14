"""Current citation validity and independently supplied human support decisions."""

from __future__ import annotations

import logging
import re
import weakref
from dataclasses import dataclass, field
from typing import Any, Protocol

from trace_app.evidence.models import _parse_utc
from trace_app.investigation.assessment import ReportInputError
from trace_app.investigation.assessment_context import (
    AssessmentBoundaryError,
    AssessmentContext,
)
from trace_app.investigation.assessment_schema import (
    ASSESSMENT_VERSION,
    AssessmentReport,
)
from trace_app.investigation.provider import ModelProviderError
from trace_app.investigation.provider_policy import (
    ProtectedModelResponse,
    ProviderScope,
)
from trace_app.investigation.tools import EvidenceArguments
from trace_app.knowledge.models import canonical, digest

RUBRIC_VERSION = "trace-claim-support.v1"
_OUTCOME = "assessment-outcome"


class CitationResolver(Protocol):
    def resolve(self, scope: ProviderScope, identity: str) -> dict[str, object]: ...


@dataclass(frozen=True, slots=True)
class SupportDecision:
    binding_id: str
    claim_id: str
    verdict: str
    reviewer_id: str = field(repr=False)
    rationale: str = field(repr=False)
    kind: str = "human_review"
    rubric_version: str = RUBRIC_VERSION


class SupportReviewReader(Protocol):
    """Trusted human decisions, never model output or evaluator expectations."""

    def read(
        self, scope: ProviderScope, binding_id: str
    ) -> tuple[SupportDecision, ...]: ...


@dataclass(frozen=True, slots=True)
class AssessmentValidation:
    outcome: str
    reason: str | None
    citation_validity: str
    claim_support: str
    assessment: ProtectedAssessment | None = field(default=None, repr=False)

    def metadata(self) -> dict[str, object]:
        return {
            "schema_version": ASSESSMENT_VERSION,
            "outcome": self.outcome,
            "reason": self.reason,
            "citation_validity": self.citation_validity,
            "claim_support": self.claim_support,
        }


@dataclass(frozen=True, slots=True, weakref_slot=True)
class ProtectedAssessment:
    _response: ProtectedModelResponse = field(repr=False)
    _owner: AssessmentValidator = field(repr=False)

    def metadata(self) -> dict[str, object]:
        return {
            "schema_version": ASSESSMENT_VERSION,
            "sensitivity": self._response.sensitivity.name.lower(),
            "provider_request_id": self._response.metadata()["request_id"],
        }

    def review_packet(
        self, scope: ProviderScope, claim_ids: tuple[str, ...] | None = None
    ) -> dict[str, Any]:
        report, citations, tasks = self._owner._inspect(self, scope)
        if claim_ids is not None:
            if len(set(claim_ids)) != len(claim_ids) or not set(claim_ids) <= {
                t["claim_id"] for t in tasks
            }:
                raise AssessmentBoundaryError("invalid_review_sample")
            tasks = [t for t in tasks if t["claim_id"] in claim_ids]
        return {
            **self.metadata(),
            "artifact_role": "untrusted_support_review",
            "rubric_version": RUBRIC_VERSION,
            "report": report.to_dict(),
            "citations": citations,
            "tasks": tasks,
            "mutation_authority": False,
        }

    def read(self, scope: ProviderScope) -> dict[str, Any]:
        report, citations, tasks = self._owner._inspect(self, scope)
        support = self._owner._support(scope, tasks)
        if support != "supported":
            raise AssessmentBoundaryError("support_not_accepted")
        report, citations, _ = self._owner._inspect(self, scope)
        data = self._owner._context.data()
        events = [
            event
            for event in data["timeline"]["events"]
            if event["evidence_id"] in report.candidate.timeline_evidence_ids
        ]
        timeline = [
            {
                "citation_id": event["evidence_id"],
                "source_id": citations[event["evidence_id"]]["source_id"],
                "source_revision": event["record"]["source_revision"],
                "observed_at": event["record"]["observed_at"],
                "collected_at": event["record"]["collected_at"],
                "causal_status": "observed",
            }
            for event in events
        ]
        return {
            **self.metadata(),
            "report": report.to_dict(),
            "citations": citations,
            "timeline": timeline,
            "citation_validity": "valid",
            "claim_support": "human_reviewed_supported",
            "mutation_authority": False,
        }

    def export(self, scope: ProviderScope) -> dict[str, Any]:
        self._response.export(scope)
        return self.read(scope)


class AssessmentValidator:
    def __init__(
        self,
        context: AssessmentContext,
        resolver: CitationResolver,
        reviews: SupportReviewReader,
    ) -> None:
        self._context = context
        self._resolver = resolver
        self._reviews = reviews
        self._issued: weakref.WeakSet[ProtectedAssessment] = weakref.WeakSet()

    def _inspect(
        self, assessment: ProtectedAssessment, scope: ProviderScope
    ) -> tuple[AssessmentReport, dict[str, Any], list[dict[str, Any]]]:
        if scope != self._context.scope or assessment not in self._issued:
            raise AssessmentBoundaryError("access_denied")
        response = assessment._response
        if response.metadata()["response_schema_id"] != ASSESSMENT_VERSION:
            raise AssessmentBoundaryError("response_schema_mismatch")
        report = AssessmentReport.from_dict(response.structured_response(scope))
        context = self._context.data()
        views = {
            view.citation_id: view.to_dict() for view in response.citation_views(scope)
        }
        admitted_ids = set(views)
        timeline = tuple(
            e["evidence_id"]
            for e in context["timeline"]["events"]
            if e["evidence_id"] in admitted_ids
        )
        if report.candidate.timeline_evidence_ids != timeline:
            raise AssessmentBoundaryError("timeline_mismatch")
        if tuple(sorted(report.source_gaps)) != self._context.gaps() or (
            report.source_gaps and not report.candidate.missing_evidence
        ):
            raise AssessmentBoundaryError("source_gaps_missing")
        primary = report.candidate.primary_hypothesis
        if (
            primary is not None
            and dict(report.causal_bases)[primary.claim.claim_id] != "mechanism"
        ):
            raise AssessmentBoundaryError("unsupported_causal_basis")
        if any(claim.claim_id == _OUTCOME for claim in report.candidate.claims()):
            raise AssessmentBoundaryError("reserved_claim_id")
        if isinstance(report.next_check.arguments, EvidenceArguments):
            check = report.next_check.arguments.query
            window = context["timeline"]["query"]
            if not (
                _parse_utc(window["window_start"])
                <= _parse_utc(check.window_start)
                <= _parse_utc(check.window_end)
                <= _parse_utc(window["window_end"])
            ):
                raise AssessmentBoundaryError("next_check_outside_window")
        citations: dict[str, Any] = {}
        # Revalidate all admitted inputs, even those omitted from the candidate prose.
        for identity, view in views.items():
            current = self._resolver.resolve(scope, identity)
            kind = current.get("kind")
            expected_fields = (
                {"kind", "source_revision", "observed_at", "collected_at"}
                if kind == "evidence"
                else {
                    "kind",
                    "source_revision",
                    "corpus_generation_id",
                    "chunk_id",
                    "section",
                    "start_offset",
                    "end_offset",
                }
                if kind == "knowledge"
                else set()
            )
            if not expected_fields or set(current) != expected_fields:
                raise AssessmentBoundaryError("citation_mismatch")
            if kind == "evidence":
                observed, collected = current["observed_at"], current["collected_at"]
                if not isinstance(observed, str) or not isinstance(collected, str):
                    raise AssessmentBoundaryError("citation_mismatch")
                try:
                    _parse_utc(observed)
                    _parse_utc(collected)
                except ValueError:
                    raise AssessmentBoundaryError("citation_mismatch") from None
            elif current["section"] != "[WITHHELD]":
                raise AssessmentBoundaryError("citation_mismatch")
            if kind == "knowledge":
                for name, prefix in (
                    ("corpus_generation_id", "gen-"),
                    ("chunk_id", "chunk-"),
                ):
                    value = current[name]
                    if not isinstance(value, str) or not re.fullmatch(
                        prefix + "[0-9a-f]{64}", value
                    ):
                        raise AssessmentBoundaryError("citation_mismatch")
                start, end = current["start_offset"], current["end_offset"]
                if (
                    type(start) is not int
                    or type(end) is not int
                    or not 0 <= start < end
                ):
                    raise AssessmentBoundaryError("citation_mismatch")
            if current.get("source_revision") != view["source_revision"]:
                raise AssessmentBoundaryError("citation_mismatch")
            citations[identity] = {**view, "source_mapping": current}
        if not set(report.references()) <= admitted_ids:
            raise AssessmentBoundaryError("citation_not_admitted")
        basis = {
            "scope_id": scope.investigation_id,
            "principal_id": scope.principal_id,
            "report": report.to_dict(),
            "citations": citations,
            "context": {
                "source_gaps": list(self._context.gaps()),
                "timeline_ids": list(timeline),
            },
            "rubric_version": RUBRIC_VERSION,
        }
        tasks: list[dict[str, Any]] = []
        for claim in report.candidate.claims():
            binding = digest(canonical({**basis, "claim_id": claim.claim_id}))
            tasks.append(
                {
                    "claim_id": claim.claim_id,
                    "statement": claim.statement,
                    "citations": list(claim.citations),
                    "contradicting_citations": list(
                        dict(report.contradictions).get(claim.claim_id, ())
                    ),
                    "binding_id": binding,
                }
            )
        tasks.append(
            {
                "claim_id": _OUTCOME,
                "statement": report.candidate.abstention_reason
                or report.candidate.uncertainty,
                "citations": list(report.references()),
                "contradicting_citations": [],
                "binding_id": digest(canonical({**basis, "claim_id": _OUTCOME})),
            }
        )
        return report, citations, tasks

    def _support(self, scope: ProviderScope, tasks: list[dict[str, Any]]) -> str:
        verdicts: list[str] = []
        for task in tasks:
            decisions = self._reviews.read(scope, task["binding_id"])
            if not isinstance(decisions, tuple) or len(decisions) > 10:
                raise AssessmentBoundaryError("invalid_review")
            reviewers: set[str] = set()
            current: set[str] = set()
            for decision in decisions:
                if (
                    not isinstance(decision, SupportDecision)
                    or decision.binding_id != task["binding_id"]
                    or decision.claim_id != task["claim_id"]
                    or decision.kind != "human_review"
                    or decision.rubric_version != RUBRIC_VERSION
                    or decision.verdict
                    not in ("supported", "unsupported", "indeterminate")
                    or not isinstance(decision.reviewer_id, str)
                    or not decision.reviewer_id
                    or len(decision.reviewer_id) > 128
                    or decision.reviewer_id in reviewers
                    or not isinstance(decision.rationale, str)
                    or not decision.rationale.strip()
                    or len(decision.rationale) > 2000
                ):
                    raise AssessmentBoundaryError("invalid_review")
                reviewers.add(decision.reviewer_id)
                current.add(decision.verdict)
            verdicts.append(
                "unreviewed"
                if not current
                else "disputed"
                if len(current) > 1
                else next(iter(current))
            )
        if "unsupported" in verdicts:
            return "unsupported"
        for pending in ("disputed", "indeterminate", "unreviewed"):
            if pending in verdicts:
                return pending
        return "supported"

    def validate(
        self, response: ProtectedModelResponse, scope: ProviderScope
    ) -> AssessmentValidation:
        result = AssessmentValidation(
            "rejected", "invalid_response", "unchecked", "unchecked"
        )
        citation_validity = "unchecked"
        try:
            if not isinstance(response, ProtectedModelResponse):
                raise AssessmentBoundaryError("invalid_response")
            handle = ProtectedAssessment(response, self)
            self._issued.add(handle)
            _, _, tasks = self._inspect(handle, scope)
            citation_validity = "valid"
            support = self._support(scope, tasks)
            if support == "supported":
                self._inspect(handle, scope)
            result = AssessmentValidation(
                "accepted"
                if support == "supported"
                else "rejected"
                if support == "unsupported"
                else "review_required",
                None if support == "supported" else "claim_support_" + support,
                "valid",
                support,
                handle,
            )
        except ReportInputError:
            result = AssessmentValidation(
                "rejected", "malformed_assessment", "unchecked", "unchecked"
            )
        except ModelProviderError:
            result = AssessmentValidation(
                "rejected", "access_denied", "invalid", "unchecked"
            )
        except AssessmentBoundaryError as error:
            result = AssessmentValidation(
                "execution_failed"
                if error.code in ("execution_failure", "dependency_failure")
                else "rejected",
                error.code,
                "invalid"
                if error.code.startswith("citation_") or error.code == "access_denied"
                else citation_validity,
                "unchecked",
            )
        except Exception:
            result = AssessmentValidation(
                "execution_failed", "dependency_failure", "unchecked", "unchecked"
            )
        logging.getLogger("trace_app.assessment").info(
            "Assessment validation completed.",
            extra={
                "event": "assessment.validated",
                "scope_id": self._context.scope.investigation_id,
                "provider_request_id": response.metadata()["request_id"]
                if isinstance(response, ProtectedModelResponse)
                else None,
                **result.metadata(),
            },
        )
        return result
