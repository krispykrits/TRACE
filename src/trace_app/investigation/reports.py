"""Current-authority delivery of private saved results; IDs confer no access."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

from trace_app.investigation.assessment_context import AssessmentBoundaryError
from trace_app.investigation.assessment_validation import (
    SupportReviewReader,
    check_claim_support,
)
from trace_app.investigation.models import Attempt, Investigation
from trace_app.investigation.provider_policy import (
    ProviderScope,
    Sensitivity,
    SourceAccessPolicy,
)

REPORT_VERSION = "investigation-cli.v1"


@dataclass(frozen=True, slots=True)
class SavedInvestigation:
    job: Investigation
    attempts: tuple[Attempt, ...]
    artifacts: tuple[dict[str, Any], ...]


class ReportReader(Protocol):
    def load(
        self, investigation_id: str, *, access_scope: str
    ) -> SavedInvestigation: ...


class ReportAccess:
    def __init__(
        self,
        reader: ReportReader,
        policy: SourceAccessPolicy,
        reviews: SupportReviewReader,
        scope: ProviderScope,
        access_scope: str,
        clearance: Sensitivity,
    ) -> None:
        self.reader, self.policy, self.reviews = reader, policy, reviews
        self.scope, self.access_scope, self.clearance = scope, access_scope, clearance

    def read(
        self,
        *,
        export: bool = False,
        artifact_id: str | None = None,
        citation_id: str | None = None,
    ) -> dict[str, Any]:
        saved = self.reader.load(
            self.scope.investigation_id, access_scope=self.access_scope
        )
        artifacts = list(saved.artifacts)
        reports = [a for a in artifacts if a["role"] in ("accepted", "review_required")]
        selected = (
            next((a for a in artifacts if a["artifact_id"] == artifact_id), None)
            if artifact_id
            else (reports[-1] if reports else artifacts[-1] if artifacts else None)
        )
        if artifact_id and selected is None:
            raise AssessmentBoundaryError("access_denied")

        def check() -> None:
            if selected is None:
                return
            metadata = selected["metadata"]
            for name in (
                ("evidence_access", "response_access")
                if selected["role"] != "untrusted_evidence"
                else ("evidence_access",)
            ):
                binding = metadata.get(name)
                if not isinstance(binding, dict):
                    raise AssessmentBoundaryError("access_denied")
                self.policy.check_saved(
                    binding, transmission=export, clearance=self.clearance
                )

        check()
        body = selected["body"] if selected else None
        assessment = (
            body if selected and selected["role"] != "untrusted_evidence" else None
        )
        if selected and selected["role"] == "accepted":
            tasks = selected["metadata"].get("review_tasks")
            if (
                not tasks
                or check_claim_support(self.reviews, self.scope, tasks) != "supported"
            ):
                raise AssessmentBoundaryError("support_not_accepted")
        # A review read may change source permissions.
        check()
        evidence = body["data"] if body and not assessment else None
        timeline = assessment.get("timeline", []) if assessment else []
        if assessment and not timeline:
            timeline = [
                {
                    "citation_id": key,
                    **value["source_mapping"],
                    "causal_status": "observed",
                }
                for key, value in assessment["citations"].items()
                if value["source_mapping"]["kind"] == "evidence"
            ]
        if evidence:
            timeline = [
                {
                    "citation_id": e["evidence_id"],
                    "source_revision": e["record"]["source_revision"],
                    "observed_at": e["record"]["observed_at"],
                    "collected_at": e["record"]["collected_at"],
                    "causal_status": "observed",
                }
                for e in evidence["timeline"]["events"]
            ]
        timeline.sort(key=lambda e: (e["observed_at"], e["citation_id"]))
        metadata = selected["metadata"] if selected else {}
        configuration = metadata.get("configuration") or (
            metadata.get("evidence_access") or {}
        ).get("configuration")
        result = {
            "schema_version": REPORT_VERSION,
            "configuration_version": "local-investigator.v1",
            "investigation_id": saved.job.investigation_id,
            "request": {
                "service": saved.job.request.service,
                "environment": saved.job.request.environment,
                "window_start": saved.job.request.window_start,
                "window_end": saved.job.request.window_end,
            },
            "execution_status": saved.job.status,
            "assessment_status": saved.job.assessment_status,
            "validation_outcome": selected["role"] if selected else "not_performed",
            "failure_code": saved.job.failure_code,
            "configuration": configuration,
            "workflow_version": metadata.get("workflow_version"),
            "content_role": "offline_hand_authored_simulation"
            if configuration and configuration.get("mode") == "offline_test"
            else "local_investigation",
            "actual_human_review": False
            if configuration and configuration.get("mode") == "offline_test"
            else selected is not None and selected["role"] == "accepted",
            "sensitivity": (
                metadata.get("response_access") or metadata.get("evidence_access") or {}
            ).get("sensitivity", "unknown"),
            "usage": metadata.get("usage"),
            "usage_available": (metadata.get("usage") or {}).get("availability")
            == "available",
            "usage_basis": "final_response_only; aggregate call records remain private",
            "timeline": timeline,
            "report": assessment["report"] if assessment else None,
            "citations": assessment["citations"] if assessment else {},
            "artifacts": [
                {"artifact_id": a["artifact_id"], "role": a["role"]} for a in artifacts
            ],
            "attempts": [
                {
                    "attempt_id": a.attempt_id,
                    "outcome": a.outcome,
                    "failure_code": a.failure_code,
                }
                for a in saved.attempts
            ],
            "mutation_authority": False,
        }
        if citation_id:
            if citation_id not in result["citations"]:
                raise AssessmentBoundaryError("access_denied")
            result = {
                "schema_version": REPORT_VERSION,
                "investigation_id": saved.job.investigation_id,
                "citation_id": citation_id,
                "citation": result["citations"][citation_id],
                "mutation_authority": False,
            }
        logging.getLogger("trace_app.reports").info(
            "Saved investigation access completed.",
            extra={
                "event": "report.exported" if export else "report.read",
                "investigation_id": saved.job.investigation_id,
            },
        )
        return result
