"""Deterministic evaluator checks; citation support requires a separate review."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from typing import Literal, cast

from trace_app.evidence.timeline import order_evidence
from trace_app.investigation.assessment import (
    CandidateReport,
    ReportInputError,
    _object,
    _text,
)
from trace_app.investigation.models import EvidenceSnapshot

SCORER_VERSION = "development-scorer.v1"
ExecutionStatus = Literal["completed", "failed", "cancelled", "expired"]


@dataclass(frozen=True, slots=True)
class ExpectedOutcome:
    case_id: str
    assessment: Literal["supported", "abstained"]
    cause_service: str
    cause_label: str

    @classmethod
    def from_manifest_case(cls, data: dict[str, object]) -> ExpectedOutcome:
        if data.get("role") != "development":
            raise ValueError("Only development cases may be scored by this runner.")
        assessment = data.get("expected_assessment")
        if assessment not in ("supported", "abstained"):
            raise ValueError("expected_assessment is invalid.")
        return cls(
            _text(data.get("case_id"), "case_id"),
            cast(Literal["supported", "abstained"], assessment),
            _text(data.get("cause_service"), "cause_service"),
            _text(data.get("cause_label"), "cause_label"),
        )


@dataclass(frozen=True, slots=True)
class SupportReview:
    claim_id: str
    verdict: Literal["supported", "unsupported", "indeterminate"]
    reviewer_id: str
    rationale: str
    kind: Literal["fixture_expectation", "human_review"]

    @classmethod
    def from_dict(cls, value: object) -> SupportReview:
        data = _object(
            value,
            {"claim_id", "verdict", "reviewer_id", "rationale", "kind"},
            "support_review",
        )
        if data["verdict"] not in ("supported", "unsupported", "indeterminate"):
            raise ValueError("support_review.verdict is invalid.")
        if data["kind"] not in ("fixture_expectation", "human_review"):
            raise ValueError("support_review.kind is invalid.")
        return cls(
            _text(data["claim_id"], "claim_id"),
            cast(Literal["supported", "unsupported", "indeterminate"], data["verdict"]),
            _text(data["reviewer_id"], "reviewer_id"),
            _text(data["rationale"], "rationale"),
            cast(Literal["fixture_expectation", "human_review"], data["kind"]),
        )


@dataclass(frozen=True, slots=True)
class EvaluationAttempt:
    attempt_id: str
    case_id: str
    seed: int
    execution_status: ExecutionStatus
    failure_code: str | None
    report: object
    usage: dict[str, int | float | None]
    support_reviews: tuple[SupportReview, ...]

    @classmethod
    def from_dict(cls, value: object) -> EvaluationAttempt:
        data = _object(
            value,
            {
                "attempt_id",
                "case_id",
                "seed",
                "execution_status",
                "failure_code",
                "report",
                "usage",
                "support_reviews",
            },
            "attempt",
        )
        if type(data["seed"]) is not int or not 0 <= data["seed"] <= 1_000_000_000:
            raise ValueError("attempt.seed is invalid.")
        status = data["execution_status"]
        if status not in ("completed", "failed", "cancelled", "expired"):
            raise ValueError("attempt.execution_status is invalid.")
        failure = (
            None
            if data["failure_code"] is None
            else _text(data["failure_code"], "failure_code")
        )
        if (status == "completed") != (failure is None):
            raise ValueError(
                "attempt.failure_code must distinguish execution failure from completion."
            )
        usage_data = _object(
            data["usage"],
            {"latency_ms", "tokens", "estimated_cost_usd", "tool_calls"},
            "usage",
        )
        usage: dict[str, int | float | None] = {}
        for name, measurement in usage_data.items():
            if measurement is not None:
                if type(measurement) not in (int, float):
                    raise ValueError(
                        f"usage.{name} must be a finite nonnegative number or null."
                    )
                try:
                    numeric = cast(int | float, measurement)
                    valid = math.isfinite(numeric) and numeric >= 0
                except OverflowError:
                    valid = False
                if not valid or (
                    name in ("tokens", "tool_calls") and type(measurement) is not int
                ):
                    raise ValueError(f"usage.{name} is invalid.")
            usage[name] = cast(int | float | None, measurement)
        reviews = data["support_reviews"]
        if not isinstance(reviews, list) or len(reviews) > 1_000:
            raise ValueError("support_reviews must be a bounded list.")
        parsed_reviews = tuple(SupportReview.from_dict(item) for item in reviews)
        keys = [(r.claim_id, r.reviewer_id, r.kind) for r in parsed_reviews]
        if len(set(keys)) != len(keys):
            raise ValueError("Duplicate reviewer/claim/kind decisions are not allowed.")
        return cls(
            _text(data["attempt_id"], "attempt_id"),
            _text(data["case_id"], "case_id"),
            cast(int, data["seed"]),
            cast(ExecutionStatus, status),
            failure,
            data["report"],
            usage,
            parsed_reviews,
        )


@dataclass(frozen=True, slots=True)
class CandidateScore:
    attempt_id: str
    case_id: str
    execution_status: ExecutionStatus
    failure_code: str | None
    report_missing: bool
    schema_valid: bool
    schema_error: str | None
    source_incomplete: bool
    capture_gap_sources: tuple[str, ...]
    cause_correct: bool | None
    service_correct: bool | None
    assessment_correct: bool
    abstention_correct: bool | None
    valid_citation_count: int
    citation_count: int
    invalid_citations: tuple[str, ...]
    invalid_timeline_citations: tuple[str, ...]
    uncited_claim_ids: tuple[str, ...]
    structurally_unsupported_claim_ids: tuple[str, ...]
    human_unsupported_claim_ids: tuple[str, ...]
    human_indeterminate_claim_ids: tuple[str, ...]
    fixture_unsupported_claim_ids: tuple[str, ...]
    disputed_claim_ids: tuple[str, ...]
    human_reviewed_claim_count: int
    unreviewed_claim_ids: tuple[str, ...]
    timeline_order_correct: bool
    timeline_complete_correct: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def score_candidate(
    attempt: EvaluationAttempt,
    evidence: EvidenceSnapshot,
    expected: ExpectedOutcome,
    *,
    valid_citation_ids: frozenset[str] | None = None,
) -> CandidateScore:
    if attempt.case_id != expected.case_id:
        raise ValueError("Attempt and expected case do not match.")
    report: CandidateReport | None = None
    error: str | None = None
    if attempt.execution_status == "completed" and attempt.report is not None:
        try:
            report = CandidateReport.from_dict(attempt.report)
        except ReportInputError as invalid:
            error = str(invalid)
    known_ids = {entry.record.evidence_id for entry in evidence.entries}
    ordered_ids = [
        entry.record.evidence_id for entry in order_evidence(evidence.entries)
    ]
    claims = report.claims() if report is not None else ()
    claim_ids = {claim.claim_id for claim in claims}
    if report is not None and any(
        r.claim_id not in claim_ids for r in attempt.support_reviews
    ):
        raise ValueError("Support review refers to an absent claim.")
    references = [reference for claim in claims for reference in claim.citations]
    valid_references = (
        known_ids if valid_citation_ids is None else set(valid_citation_ids)
    )
    invalid_refs = tuple(sorted(set(references) - valid_references))
    uncited = tuple(claim.claim_id for claim in claims if not claim.citations)
    structural = tuple(
        claim.claim_id
        for claim in claims
        if not claim.citations
        or any(ref not in valid_references for ref in claim.citations)
    )
    human_unsupported, indeterminate, fixture_unsupported, disputed, unreviewed = (
        [],
        [],
        [],
        [],
        [],
    )
    reviewed_count = 0
    for claim in claims:
        human = [
            r
            for r in attempt.support_reviews
            if r.claim_id == claim.claim_id and r.kind == "human_review"
        ]
        fixture = [
            r
            for r in attempt.support_reviews
            if r.claim_id == claim.claim_id and r.kind == "fixture_expectation"
        ]
        if any(r.verdict == "unsupported" for r in fixture):
            fixture_unsupported.append(claim.claim_id)
        if not human:
            unreviewed.append(claim.claim_id)
        else:
            reviewed_count += 1
            verdicts = {r.verdict for r in human}
            if len(verdicts) > 1:
                disputed.append(claim.claim_id)
            elif verdicts == {"unsupported"}:
                human_unsupported.append(claim.claim_id)
            elif verdicts == {"indeterminate"}:
                indeterminate.append(claim.claim_id)
    answerable = expected.assessment == "supported"
    primary = report.primary_hypothesis if report else None
    cause_correct = primary is not None and primary.cause == expected.cause_label
    service_correct = primary is not None and primary.service == expected.cause_service
    unavailable = {
        source.source for source in evidence.sources if source.status != "available"
    }
    abstention = (
        report is not None
        and report.assessment_status == "abstained"
        and bool(report.abstention_reason)
        and bool(report.missing_evidence)
        and set(report.missing_evidence) <= unavailable
    )
    timeline_ids = list(report.timeline_evidence_ids) if report else []
    expected_subset = [identity for identity in ordered_ids if identity in timeline_ids]
    order_correct = (
        report is not None
        and (bool(timeline_ids) or not ordered_ids)
        and timeline_ids == expected_subset
    )
    return CandidateScore(
        attempt_id=attempt.attempt_id,
        case_id=attempt.case_id,
        execution_status=attempt.execution_status,
        failure_code=attempt.failure_code,
        report_missing=attempt.execution_status == "completed"
        and attempt.report is None,
        schema_valid=report is not None,
        schema_error=error,
        source_incomplete=not evidence.sources or bool(unavailable),
        capture_gap_sources=tuple(
            source.source
            for source in evidence.sources
            if source.reason == "capture_gap"
        ),
        cause_correct=cause_correct if answerable else None,
        service_correct=service_correct if answerable else None,
        assessment_correct=report is not None
        and report.assessment_status == expected.assessment,
        abstention_correct=abstention if not answerable else None,
        valid_citation_count=sum(ref in valid_references for ref in references),
        citation_count=len(references),
        invalid_citations=invalid_refs,
        invalid_timeline_citations=tuple(sorted(set(timeline_ids) - known_ids)),
        uncited_claim_ids=uncited,
        structurally_unsupported_claim_ids=structural,
        human_unsupported_claim_ids=tuple(human_unsupported),
        human_indeterminate_claim_ids=tuple(indeterminate),
        fixture_unsupported_claim_ids=tuple(fixture_unsupported),
        disputed_claim_ids=tuple(disputed),
        human_reviewed_claim_count=reviewed_count,
        unreviewed_claim_ids=tuple(unreviewed),
        timeline_order_correct=order_correct,
        timeline_complete_correct=report is not None and timeline_ids == ordered_ids,
    )


def _rate(numerator: int, denominator: int) -> dict[str, int | float | None]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def aggregate_scores(scores: tuple[CandidateScore, ...]) -> dict[str, object]:
    total = len(scores)
    return {
        "attempted": total,
        "execution_counts": {
            status: sum(score.execution_status == status for score in scores)
            for status in ("completed", "failed", "cancelled", "expired")
        },
        "missing_reports": sum(score.report_missing for score in scores),
        "invalid_reports": sum(score.schema_error is not None for score in scores),
        "source_incomplete_attempts": sum(score.source_incomplete for score in scores),
        "capture_gap_attempts": sum(
            bool(score.capture_gap_sources) for score in scores
        ),
        "schema_validity": _rate(sum(score.schema_valid for score in scores), total),
        "cause_accuracy": _rate(
            sum(score.cause_correct is True for score in scores),
            sum(score.cause_correct is not None for score in scores),
        ),
        "service_accuracy": _rate(
            sum(score.service_correct is True for score in scores),
            sum(score.service_correct is not None for score in scores),
        ),
        "assessment_accuracy": _rate(
            sum(score.assessment_correct for score in scores), total
        ),
        "abstention_contract_accuracy": _rate(
            sum(score.abstention_correct is True for score in scores),
            sum(score.abstention_correct is not None for score in scores),
        ),
        "citation_validity": _rate(
            sum(score.valid_citation_count for score in scores),
            sum(score.citation_count for score in scores),
        ),
        "timeline_order_accuracy": _rate(
            sum(score.timeline_order_correct for score in scores), total
        ),
        "timeline_complete_accuracy": _rate(
            sum(score.timeline_complete_correct for score in scores), total
        ),
        "structurally_unsupported_claims": sum(
            len(score.structurally_unsupported_claim_ids) for score in scores
        ),
        "fixture_expected_unsupported_claims": sum(
            len(score.fixture_unsupported_claim_ids) for score in scores
        ),
        "human_unsupported_claim_rate": _rate(
            sum(len(score.human_unsupported_claim_ids) for score in scores),
            sum(
                score.human_reviewed_claim_count
                - len(score.disputed_claim_ids)
                - len(score.human_indeterminate_claim_ids)
                for score in scores
            ),
        ),
        "reviewer_disagreements": sum(
            len(score.disputed_claim_ids) for score in scores
        ),
        "unreviewed_claims": sum(len(score.unreviewed_claim_ids) for score in scores),
    }
