"""Owner-approved source grants and support decisions."""

from trace_app.evidence.models import _parse_utc
from trace_app.investigation.assessment_context import AssessmentBoundaryError
from trace_app.investigation.assessment_validation import SupportDecision
from trace_app.investigation.provider_policy import (
    AuthorizedEvidence,
    EvidenceField,
    ProviderScope,
    Sensitivity,
)
from trace_app.knowledge.models import digest


class LocalEvidenceAuthority:
    def __init__(self, profile, scope: ProviderScope) -> None:
        self.profile, self.scope = profile, scope

    def resolve(
        self, scope: ProviderScope, evidence_id: str
    ) -> AuthorizedEvidence | None:
        if scope != self.scope:
            return None
        data = self.profile.current()
        grant = data["grants"].get(evidence_id)
        if not grant:
            return None
        current = self.profile.source_content().get(evidence_id)
        if current is None:
            return None
        revision, content, kind = current
        # Classification and permission come from a separate exact-content owner grant.
        if (
            grant["revision"] != revision
            or grant["content_sha256"] != digest(content)
            or grant["kind"] != kind.value
        ):
            return None
        for flag in (
            "access_allowed",
            "transmission_allowed",
            "source_owner_allowed",
            "identifiers_reviewed",
            "fields_reviewed",
        ):
            if type(grant[flag]) is not bool:
                raise AssessmentBoundaryError("access_denied")
        return AuthorizedEvidence(
            evidence_id,
            grant["source_id"],
            revision,
            kind,
            (
                EvidenceField(
                    "content",
                    content,
                    Sensitivity[grant["sensitivity"].upper()],
                    grant["fields_reviewed"],
                ),
            ),
            grant["access_allowed"],
            grant["transmission_allowed"],
            grant["source_owner_allowed"],
            grant["identifiers_reviewed"],
            min(
                _parse_utc(grant["expires_at"]).timestamp(),
                _parse_utc(data["expires_at"]).timestamp(),
            ),
        )


class LocalSupportReviews:
    def __init__(self, profile) -> None:
        self.profile = profile

    def read(
        self, scope: ProviderScope, binding_id: str
    ) -> tuple[SupportDecision, ...]:
        data = self.profile.current()
        if scope.principal_id != self.profile.principal_id:
            raise AssessmentBoundaryError("access_denied")
        return tuple(
            SupportDecision(**row["decision"])
            for row in data["reviews"]
            if row["principal_id"] == scope.principal_id
            and row["investigation_id"] == scope.investigation_id
            and row["decision"]["binding_id"] == binding_id
        )
