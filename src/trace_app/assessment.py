"""Versioned candidate assessment contract, with no evaluator dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, cast

REPORT_SCHEMA_VERSION = "1"


class ReportInputError(ValueError):
    """Invalid report input; messages identify fields without echoing content."""


def _object(value: object, fields: set[str], name: str) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ReportInputError(
            f"{name}: required fields are missing or unknown fields are present."
        )
    return value


def _text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 2_000:
        raise ReportInputError(
            f"{name}: requires nonempty text of at most 2000 characters."
        )
    return value


def _strings(value: object, name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > 100:
        raise ReportInputError(f"{name}: requires a list of at most 100 strings.")
    result = tuple(_text(item, name) for item in value)
    if len(set(result)) != len(result):
        raise ReportInputError(f"{name}: duplicate values are not allowed.")
    return result


@dataclass(frozen=True, slots=True)
class Claim:
    claim_id: str
    statement: str
    citations: tuple[str, ...]

    @classmethod
    def from_dict(cls, value: object) -> Claim:
        data = _object(value, {"claim_id", "statement", "citations"}, "claim")
        return cls(
            _text(data["claim_id"], "claim_id"),
            _text(data["statement"], "statement"),
            _strings(data["citations"], "citations"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "claim_id": self.claim_id,
            "statement": self.statement,
            "citations": list(self.citations),
        }


@dataclass(frozen=True, slots=True)
class Hypothesis:
    claim: Claim
    service: str
    cause: str

    @classmethod
    def from_dict(cls, value: object) -> Hypothesis:
        data = _object(value, {"claim", "service", "cause"}, "hypothesis")
        return cls(
            Claim.from_dict(data["claim"]),
            _text(data["service"], "service"),
            _text(data["cause"], "cause"),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "claim": self.claim.to_dict(),
            "service": self.service,
            "cause": self.cause,
        }


@dataclass(frozen=True, slots=True)
class CandidateReport:
    assessment_status: Literal["supported", "abstained"]
    observations: tuple[Claim, ...]
    primary_hypothesis: Hypothesis | None
    alternative_hypotheses: tuple[Hypothesis, ...]
    uncertainty: str
    missing_evidence: tuple[str, ...]
    abstention_reason: str | None
    next_check: str
    timeline_evidence_ids: tuple[str, ...]

    @classmethod
    def from_dict(cls, value: object) -> CandidateReport:
        data = _object(
            value,
            {
                "schema_version",
                "assessment_status",
                "observations",
                "primary_hypothesis",
                "alternative_hypotheses",
                "uncertainty",
                "missing_evidence",
                "abstention_reason",
                "next_check",
                "timeline_evidence_ids",
            },
            "report",
        )
        if data["schema_version"] != REPORT_SCHEMA_VERSION:
            raise ReportInputError("schema_version: unsupported report version.")
        status = data["assessment_status"]
        if status not in ("supported", "abstained"):
            raise ReportInputError(
                "assessment_status: requires supported or abstained."
            )
        observations, alternatives = (
            data["observations"],
            data["alternative_hypotheses"],
        )
        if not isinstance(observations, list) or len(observations) > 100:
            raise ReportInputError(
                "observations: requires a list of at most 100 claims."
            )
        if not isinstance(alternatives, list) or len(alternatives) > 100:
            raise ReportInputError(
                "alternative_hypotheses: requires a list of at most 100 hypotheses."
            )
        primary = (
            None
            if data["primary_hypothesis"] is None
            else Hypothesis.from_dict(data["primary_hypothesis"])
        )
        reason = (
            None
            if data["abstention_reason"] is None
            else _text(data["abstention_reason"], "abstention_reason")
        )
        if status == "supported" and (primary is None or reason is not None):
            raise ReportInputError(
                "supported: requires a primary hypothesis and no abstention reason."
            )
        if status == "abstained" and (primary is not None or reason is None):
            raise ReportInputError(
                "abstained: requires a reason and no primary hypothesis."
            )
        result = cls(
            cast(Literal["supported", "abstained"], status),
            tuple(Claim.from_dict(item) for item in observations),
            primary,
            tuple(Hypothesis.from_dict(item) for item in alternatives),
            _text(data["uncertainty"], "uncertainty"),
            _strings(data["missing_evidence"], "missing_evidence"),
            reason,
            _text(data["next_check"], "next_check"),
            _strings(data["timeline_evidence_ids"], "timeline_evidence_ids"),
        )
        claim_ids = [claim.claim_id for claim in result.claims()]
        if len(set(claim_ids)) != len(claim_ids):
            raise ReportInputError(
                "claim_id: must be unique across observations and hypotheses."
            )
        return result

    def claims(self) -> tuple[Claim, ...]:
        primary = (
            (self.primary_hypothesis.claim,)
            if self.primary_hypothesis is not None
            else ()
        )
        return (
            self.observations
            + primary
            + tuple(h.claim for h in self.alternative_hypotheses)
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": REPORT_SCHEMA_VERSION,
            "assessment_status": self.assessment_status,
            "observations": [claim.to_dict() for claim in self.observations],
            "primary_hypothesis": self.primary_hypothesis.to_dict()
            if self.primary_hypothesis
            else None,
            "alternative_hypotheses": [
                h.to_dict() for h in self.alternative_hypotheses
            ],
            "uncertainty": self.uncertainty,
            "missing_evidence": list(self.missing_evidence),
            "abstention_reason": self.abstention_reason,
            "next_check": self.next_check,
            "timeline_evidence_ids": list(self.timeline_evidence_ids),
        }
