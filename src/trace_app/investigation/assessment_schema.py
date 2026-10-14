"""Strict assessment.v2; the frozen evaluation CandidateReport v1 is preserved."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from trace_app.investigation.assessment import (
    CandidateReport,
    ReportInputError,
    _object,
    _text,
)
from trace_app.investigation.tools import ToolCall, ToolPolicy

ASSESSMENT_VERSION = "assessment.v2"
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}\Z")


@dataclass(frozen=True, slots=True)
class AssessmentReport:
    _json: str = field(repr=False)
    candidate: CandidateReport = field(repr=False)
    contradictions: tuple[tuple[str, tuple[str, ...]], ...]
    causal_bases: tuple[tuple[str, str], ...]
    source_gaps: tuple[str, ...]
    next_check: ToolCall = field(repr=False)

    @classmethod
    def from_dict(cls, value: object) -> AssessmentReport:
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
                "source_gaps",
            },
            "assessment",
        )
        try:
            encoded = json.dumps(data, allow_nan=False)
            if (
                len(encoded.encode()) > 65_536
                or data["schema_version"] != ASSESSMENT_VERSION
            ):
                raise ReportInputError("Assessment version or size is invalid.")
            legacy: dict[str, Any] = json.loads(encoded)
            legacy["schema_version"] = "1"
            gaps = legacy.pop("source_gaps")
            if (
                not isinstance(gaps, list)
                or len(gaps) > 100
                or any(
                    not isinstance(item, str) or not _ID.fullmatch(item)
                    for item in gaps
                )
                or len(set(gaps)) != len(gaps)
            ):
                raise ReportInputError(
                    "Source gaps must be bounded unique identifiers."
                )
            check = _object(
                legacy["next_check"], {"tool", "arguments", "reason"}, "next_check"
            )
            legacy["next_check"] = _text(check["reason"], "next_check.reason")
            parsed_check = ToolCall.parse(
                check["tool"], check["arguments"], ToolPolicy()
            )
            contradictions: list[tuple[str, tuple[str, ...]]] = []
            bases: list[tuple[str, str]] = []

            def hypothesis(item: object) -> dict[str, object]:
                h = _object(
                    item,
                    {
                        "claim",
                        "service",
                        "cause",
                        "contradicting_citations",
                        "causal_basis",
                    },
                    "hypothesis",
                )
                contrary = h["contradicting_citations"]
                if (
                    not isinstance(contrary, list)
                    or len(contrary) > 32
                    or any(
                        not isinstance(ref, str) or not _ID.fullmatch(ref)
                        for ref in contrary
                    )
                    or len(set(contrary)) != len(contrary)
                ):
                    raise ReportInputError("Contradicting citations are invalid.")
                claim = _object(
                    h["claim"], {"claim_id", "statement", "citations"}, "claim"
                )
                identity = _text(claim["claim_id"], "claim_id")
                basis = h["causal_basis"]
                if basis not in (
                    "mechanism",
                    "temporal_only",
                    "score_only",
                    "context_only",
                ):
                    raise ReportInputError("Causal basis is invalid.")
                assert isinstance(basis, str)
                citations = claim["citations"]
                if not isinstance(citations, list) or any(
                    ref in citations for ref in contrary
                ):
                    raise ReportInputError(
                        "Supporting and contradicting references must be separate."
                    )
                contradictions.append((identity, tuple(contrary)))
                bases.append((identity, basis))
                return {key: h[key] for key in ("claim", "service", "cause")}

            if legacy["primary_hypothesis"] is not None:
                legacy["primary_hypothesis"] = hypothesis(legacy["primary_hypothesis"])
            alternatives = legacy["alternative_hypotheses"]
            if not isinstance(alternatives, list) or len(alternatives) > 20:
                raise ReportInputError("Alternative hypotheses exceed their bound.")
            legacy["alternative_hypotheses"] = [
                hypothesis(item) for item in alternatives
            ]
            candidate = CandidateReport.from_dict(legacy)
            if len(candidate.claims()) > 100:
                raise ReportInputError("Claim count exceeds its bound.")
            for claim in candidate.claims():
                if (
                    not _ID.fullmatch(claim.claim_id)
                    or not claim.citations
                    or len(claim.citations) > 32
                    or any(not _ID.fullmatch(ref) for ref in claim.citations)
                ):
                    raise ReportInputError(
                        "Every claim requires bounded citation identifiers."
                    )
            for ref in candidate.timeline_evidence_ids:
                if not _ID.fullmatch(ref):
                    raise ReportInputError("Timeline identifiers are invalid.")
            return cls(
                encoded,
                candidate,
                tuple(contradictions),
                tuple(bases),
                tuple(gaps),
                parsed_check,
            )
        except ReportInputError:
            raise
        except (ValueError, TypeError, KeyError, RecursionError, UnicodeError):
            raise ReportInputError("Assessment failed schema validation.") from None

    def to_dict(self) -> dict[str, Any]:
        return json.loads(self._json)

    def references(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                [ref for claim in self.candidate.claims() for ref in claim.citations]
                + [ref for _, refs in self.contradictions for ref in refs]
                + list(self.candidate.timeline_evidence_ids)
            )
        )
