"""One prescribed read-only investigation; model text cannot select its authority."""

from __future__ import annotations

import json
import logging
import math
import time
import uuid
import weakref
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Protocol

from trace_app.evidence.models import _parse_utc
from trace_app.evidence.queries import EvidenceQuery
from trace_app.investigation.assessment import ReportInputError
from trace_app.investigation.assessment_context import (
    AssessmentBoundaryError,
    AssessmentContext,
    ToolCitationResolver,
)
from trace_app.investigation.assessment_schema import (
    AssessmentReport,
)
from trace_app.investigation.assessment_validation import (
    AssessmentValidation,
    AssessmentValidator,
    SupportReviewReader,
)
from trace_app.investigation.bundle import (
    BUNDLE_VERSION,
    EvidencePackage,
    build_evidence_package,
)
from trace_app.investigation.execution import (
    ExecutionIdentity,
    ExecutionRejected,
    ExecutionSession,
)
from trace_app.investigation.models import Investigation, StoreStateError
from trace_app.investigation.provider import (
    ModelCallBounds,
    ModelErrorCode,
    ModelProviderError,
)
from trace_app.investigation.provider_policy import (
    AuthorizedEvidence,
    EvidenceAuthority,
    EvidenceSelection,
    InvestigationFrame,
    PolicyModelProvider,
    ProtectedModelResponse,
    ProviderCall,
    ProviderScope,
    Sensitivity,
    SourceAccessPolicy,
    SourceKind,
)
from trace_app.investigation.tools import (
    EvidenceArguments,
    KnowledgeArguments,
    ToolSession,
)
from trace_app.knowledge.models import canonical, digest

WORKFLOW_VERSION = "bounded-investigator.v1"
WORKFLOW_PROMPT = "investigation-assessment.v1"
ARTIFACT_VERSION = "investigation-result.v2"
WORKFLOW_TRANSITIONS = {
    "started": {"gathering"},
    "gathering": {"model", "evidence_only"},
    "model": {"checking", "validating"},
    "checking": {"regathering"},
    "regathering": {"refining"},
    "refining": {"validating"},
    "validating": {"correcting", "publishing"},
    "correcting": {"validating"},
    "publishing": set(),
    "evidence_only": set(),
    "failed": set(),
}
_ISSUED: weakref.WeakSet[WorkflowPublication] = weakref.WeakSet()


@dataclass(frozen=True, slots=True)
class WorkflowOptions:
    next_check: bool = False
    correction: bool = False
    evidence_only: bool = False

    def __post_init__(self) -> None:
        if any(
            type(value) is not bool
            for value in (self.next_check, self.correction, self.evidence_only)
        ):
            raise ValueError("Workflow options require explicit booleans.")


@dataclass(frozen=True, slots=True, weakref_slot=True, eq=False)
class WorkflowPublication:
    identity: ExecutionIdentity
    artifact_id: str
    outcome: str
    assessment_status: str
    sensitivity: str
    _body_json: str = field(repr=False)
    _metadata_json: str = field(repr=False)

    def metadata(self) -> dict[str, Any]:
        return json.loads(self._metadata_json)

    def is_issued(self) -> bool:
        return self in _ISSUED

    def storage_body(self) -> str:
        """Private storage-port payload, never telemetry or an inspection API."""
        if not self.is_issued():
            raise StoreStateError("Workflow publication is not issued.")
        return self._body_json


class WorkflowStore(Protocol):
    def close(self) -> None: ...
    def get_investigation(self, identity: ExecutionIdentity) -> Investigation: ...
    def start(self, identity: ExecutionIdentity, *, at: datetime) -> None: ...
    def phase(
        self, identity: ExecutionIdentity, name: str, *, at: datetime
    ) -> None: ...
    def retain(
        self,
        identity: ExecutionIdentity,
        package: EvidencePackage,
        *,
        at: datetime,
        access_binding: dict[str, object] | None = None,
    ) -> str: ...
    def publish(self, publication: WorkflowPublication, *, at: datetime) -> None: ...
    def fail(self, identity: ExecutionIdentity, code: str, *, at: datetime) -> str: ...


def source_content(package: EvidencePackage) -> dict[str, tuple[str, str]]:
    """Exact local projections; independent authorities must resolve current originals."""
    if package.data is None:
        return {}
    data = package.data
    result = {
        event["evidence_id"]: (
            event["record"]["source_revision"],
            canonical({key: event[key] for key in ("kind", "record", "payload")}),
        )
        for event in data["timeline"]["events"]
    }
    context = data["knowledge"]["context"]["data"]
    result.update(
        {
            p["citation_id"]: (
                context["citations"][p["citation_id"]]["metadata"]["source_revision"],
                canonical(
                    {"passage": p, "citation": context["citations"][p["citation_id"]]}
                ),
            )
            for p in context["passages"]
        }
    )
    return result


def select_context(
    package: EvidencePackage,
    scope: ProviderScope,
    history: tuple[ProtectedModelResponse, ...] = (),
) -> tuple[EvidencePackage, tuple[EvidenceSelection, ...]]:
    """Keep bounded representatives; disclose every model-context omission locally."""
    data = json.loads(canonical(package.data))
    events = data["timeline"]["events"]
    chosen: set[str] = set()
    for kind, count in (("log", 2), ("metric", 1), ("deployment", 1)):
        chosen.update(
            e["evidence_id"] for e in [e for e in events if e["kind"] == kind][-count:]
        )
    passages = data["knowledge"]["context"]["data"]["passages"]
    knowledge_ids = [p["citation_id"] for p in passages[:2]]
    retained = {v.citation_id for prior in history for v in prior.citation_views(scope)}
    data["model_context_omissions"] = {
        "evidence": [
            e["evidence_id"]
            for e in events
            if e["evidence_id"] not in chosen | retained
        ],
        "knowledge": [
            p["citation_id"] for p in passages[2:] if p["citation_id"] not in retained
        ],
    }
    prepared = EvidencePackage(
        package.status,
        data,
        digest(canonical(data)),
        scope.investigation_id,
        package.audits,
        None,
    )
    content = source_content(prepared)
    ids = [
        e["evidence_id"] for e in events if e["evidence_id"] in chosen
    ] + knowledge_ids
    selections = tuple(
        EvidenceSelection(identity, content[identity][0], ("content",))
        for identity in ids
    )
    return prepared, selections


def merge_packages(
    previous: EvidencePackage, current: EvidencePackage
) -> EvidencePackage:
    """Retain history mappings, with finite whole quotes and changed sources rejected."""
    if previous.data is None or current.data is None:
        raise AssessmentBoundaryError("invalid_context")
    if previous.data["timeline"] != current.data["timeline"]:
        raise AssessmentBoundaryError("citation_mismatch")
    data = json.loads(canonical(current.data))
    old = previous.data["knowledge"]["context"]["data"]
    new = data["knowledge"]["context"]["data"]
    passages = {p["citation_id"]: p for p in new["passages"]}
    citations = dict(new["citations"])
    for p in old["passages"]:
        identity = p["citation_id"]
        mapping = old["citations"][identity]
        if identity in passages and (
            passages[identity] != p or citations[identity] != mapping
        ):
            raise AssessmentBoundaryError("citation_mismatch")
        passages[identity], citations[identity] = p, mapping
    if len(passages) > 10:
        raise AssessmentBoundaryError("invalid_context")
    new.update(passages=list(passages.values()), citations=citations)
    knowledge = data["knowledge"]["context"]
    knowledge["used_bytes"] = len(canonical(new).encode())
    knowledge["budget"] = {"max_bytes": 16_384, "max_passages": 10}
    if knowledge["used_bytes"] > 16_384:
        raise AssessmentBoundaryError("invalid_context")
    knowledge["incomplete"] |= previous.data["knowledge"]["context"]["incomplete"]
    knowledge["omitted"] += previous.data["knowledge"]["context"]["omitted"]
    data["references"]["knowledge"] = sorted(citations)
    data["missing_knowledge"] = not passages
    data["incomplete"] |= previous.data["incomplete"]
    return EvidencePackage(
        "partial" if data["incomplete"] else "complete",
        data,
        digest(canonical(data)),
        current.investigation_id,
        previous.audits + current.audits,
        None,
    )


@dataclass(frozen=True, slots=True)
class WorkflowResult:
    _owner: BoundedInvestigation = field(repr=False)
    _package: EvidencePackage | None = field(repr=False)
    _publication: WorkflowPublication | None = field(repr=False)
    _response: ProtectedModelResponse | None = field(repr=False)
    _validator: AssessmentValidator | None = field(repr=False)
    _tasks_json: str = field(repr=False)
    execution_status: str
    validation_outcome: str
    failure_code: str | None
    artifact_ids: tuple[str, ...]

    def metadata(self) -> dict[str, object]:
        return {
            "workflow_version": WORKFLOW_VERSION,
            "investigation_id": self._owner.execution.identity.investigation_id,
            "attempt_id": self._owner.execution.identity.attempt_id,
            "correlation_id": self._owner.execution.identity.correlation_id,
            "execution_status": self.execution_status,
            "validation_outcome": self.validation_outcome,
            "failure_code": self.failure_code,
            "artifact_ids": list(self.artifact_ids),
            "evidence_available": self._package is not None
            and self._package.data is not None,
            "mutation_authority": False,
        }

    def read(self, scope: ProviderScope) -> dict[str, Any]:
        """Local delivery, with fresh source/review grants and no resumed tool dispatch."""
        if scope != self._owner.scope:
            raise AssessmentBoundaryError("access_denied")
        if self._package is not None:
            self._owner.check_source_access(self._package)
        if self._response is not None:
            self._response.structured_response(scope)
        if self.validation_outcome == "accepted":
            try:
                support = (
                    self._validator.recheck_support(scope, json.loads(self._tasks_json))
                    if self._validator
                    else "unreviewed"
                )
            except Exception:
                raise AssessmentBoundaryError("execution_failure") from None
            if support != "supported":
                raise AssessmentBoundaryError("support_not_accepted")
        # Recheck after reviews, since the reader may have revoked source permission.
        if self._package is not None:
            self._owner.check_source_access(self._package)
        if self._response is not None:
            self._response.structured_response(scope)
        return {
            **self.metadata(),
            "sensitivity": self._publication.sensitivity
            if self._publication
            else "unknown",
            "evidence": self._package.to_dict() if self._package is not None else None,
            "assessment": json.loads(self._publication.storage_body())
            if self._publication
            else None,
        }


class BoundedInvestigation:
    def __init__(
        self,
        store: WorkflowStore,
        tools: ToolSession,
        provider: PolicyModelProvider | None,
        authority: EvidenceAuthority,
        reviews: SupportReviewReader,
        execution: ExecutionSession,
        scope: ProviderScope,
        *,
        options: WorkflowOptions = WorkflowOptions(),
        clock: Callable[[], float] = time.time,
    ) -> None:
        if (
            tools.execution is not execution
            or tools.investigation_id != scope.investigation_id
            or execution.identity.investigation_id != scope.investigation_id
            or execution.identity.access_scope != tools.scope.evidence.access_scope
            or provider is not None
            and (provider.execution is not execution or provider.scope != scope)
            or options.correction
            and execution.policy.max_corrections < 1
        ):
            raise ValueError(
                "Workflow requires matching scope and one shared execution policy."
            )
        self.store, self.tools, self.provider = store, tools, provider
        self.authority, self.reviews, self.execution, self.scope = (
            authority,
            reviews,
            execution,
            scope,
        )
        self.options, self._clock = options, clock

    def _at(self) -> datetime:
        return datetime.fromtimestamp(self._clock(), timezone.utc)

    def close(self) -> None:
        self.store.close()

    def check_source_access(self, package: EvidencePackage) -> None:
        for identity, (revision, content) in source_content(package).items():
            try:
                record = self.authority.resolve(self.scope, identity)
            except Exception:
                raise AssessmentBoundaryError("execution_failure") from None
            if (
                not isinstance(record, AuthorizedEvidence)
                or record.evidence_id != identity
                or record.revision != revision
                or record.access_allowed is not True
                or record.identifiers_reviewed is not True
                or not math.isfinite(record.expires_at)
                or record.expires_at <= self._clock()
                or record.kind == SourceKind.EVALUATOR
                or not any(
                    f.name == "content" and f.value == content for f in record.fields
                )
            ):
                raise AssessmentBoundaryError("access_denied")

    def _phase(self, phase: str) -> None:
        self.execution.checkpoint()
        self.store.phase(self.execution.identity, phase, at=self._at())
        logging.getLogger("trace_app.workflow").info(
            "Investigation phase entered.",
            extra={
                "event": "workflow.phase",
                "phase": phase,
                "workflow_version": WORKFLOW_VERSION,
                "investigation_id": self.scope.investigation_id,
                "attempt_id": self.execution.identity.attempt_id,
                "correlation_id": self.execution.identity.correlation_id,
            },
        )

    def run(self) -> WorkflowResult:
        package: EvidencePackage | None = None
        response: ProtectedModelResponse | None = None
        validator: AssessmentValidator | None = None
        publication: WorkflowPublication | None = None
        artifacts: list[str] = []
        tasks: list[dict[str, Any]] = []
        validation = AssessmentValidation(
            "not_performed", None, "unchecked", "unchecked"
        )
        started = False
        status, failure = "failed", None
        try:
            job = self.store.get_investigation(self.execution.identity)
            if (
                job.request.service not in self.tools.scope.evidence.allowed_services
                or job.request.environment != self.tools.scope.evidence.environment
            ):
                raise AssessmentBoundaryError("scope_mismatch")
            self.execution.checkpoint()
            self.store.start(self.execution.identity, at=self._at())
            started = True
            self._phase("gathering")
            query = EvidenceQuery(job.request.window_start, job.request.window_end, 20)
            knowledge_query = (
                f"{job.request.service} incident errors latency deployments"
            )
            package = self._gather(query, knowledge_query)
            artifacts.append(self._retain(package))
            self.check_source_access(package)
            if self.options.evidence_only:
                self.execution.stop("completed")
                self.store.phase(
                    self.execution.identity, "evidence_only", at=self._at()
                )
                status = "completed"
            else:
                if self.provider is None:
                    raise ModelProviderError(ModelErrorCode.MODEL_UNAVAILABLE)
                package, selections = select_context(package, self.scope)
                self._phase("model")
                response = self._generate(package, selections, job, "draft")
                if self.options.next_check:
                    draft = AssessmentReport.from_dict(
                        response.structured_response(self.scope)
                    )
                    self._check_proposal(draft, package, response)
                    self._phase("checking")
                    result = self.tools.invoke(
                        draft.next_check.name, draft.next_check.to_arguments()
                    )
                    if result.payload.status not in ("ok", "empty", "partial"):
                        raise ExecutionRejected(result.payload.status)
                    if isinstance(draft.next_check.arguments, KnowledgeArguments):
                        knowledge_query = draft.next_check.arguments.request.query
                    self._phase("regathering")
                    package = merge_packages(
                        package, self._gather(query, knowledge_query)
                    )
                    artifacts.append(self._retain(package))
                    package, selections = select_context(
                        package, self.scope, (response,)
                    )
                    self._phase("refining")
                    response = self._generate(
                        package, selections, job, "after_check", history=(response,)
                    )
                self._phase("validating")
                validator = AssessmentValidator(
                    AssessmentContext.from_package(package, self.scope),
                    ToolCitationResolver(
                        self.tools, AssessmentContext.from_package(package, self.scope)
                    ),
                    self.reviews,
                )
                validation = validator.validate(response, self.scope)
                if (
                    validation.outcome == "rejected"
                    and self.options.correction
                    and validation.reason
                    not in ("access_denied", "citation_denied", "invalid_review")
                ):
                    self._phase("correcting")
                    response = self._generate(
                        package,
                        selections,
                        job,
                        "correction",
                        history=(response,),
                        reason=validation.reason,
                    )
                    self._phase("validating")
                    validation = validator.validate(response, self.scope)
                if (
                    validation.outcome not in ("accepted", "review_required")
                    or validation.assessment is None
                ):
                    raise AssessmentBoundaryError(
                        validation.reason or "execution_failure"
                    )
                packet = validation.assessment.review_packet(self.scope)
                tasks = packet["tasks"]
                body = (
                    validation.assessment.read(self.scope)
                    if validation.outcome == "accepted"
                    else packet
                )
                if package.data is None:
                    raise AssessmentBoundaryError("execution_failure")
                body["captured_timeline"] = package.data["timeline"]
                body["model_context_omissions"] = package.data.get(
                    "model_context_omissions", {}
                )
                self._phase("publishing")
                self.check_source_access(package)
                report = AssessmentReport.from_dict(body["report"])
                evidence_binding = self._binding(package)
                metadata = {
                    **validation.metadata(),
                    **response.metadata(),
                    "workflow_version": WORKFLOW_VERSION,
                    "artifact_version": ARTIFACT_VERSION,
                    "bundle_version": BUNDLE_VERSION,
                    "artifact_id": uuid.uuid4().hex,
                    "citation_ids": list(report.references()),
                    "response_access": response.storage_binding(self.scope),
                    "evidence_access": evidence_binding,
                    "review_tasks": [
                        {"binding_id": t["binding_id"], "claim_id": t["claim_id"]}
                        for t in tasks
                    ],
                    "evidence_artifact_ids": list(artifacts),
                    "mutation_authority": False,
                }
                publication = WorkflowPublication(
                    self.execution.identity,
                    str(metadata["artifact_id"]),
                    validation.outcome,
                    report.candidate.assessment_status
                    if validation.outcome == "accepted"
                    else "pending",
                    max(
                        response.sensitivity,
                        Sensitivity[str(evidence_binding["sensitivity"]).upper()],
                    ).name.lower(),
                    canonical(body),
                    canonical(metadata),
                )
                _ISSUED.add(publication)
                self.execution.stop("completed")
                self.store.publish(publication, at=self._at())
                artifacts.append(publication.artifact_id)
                status = "completed"
        except KeyboardInterrupt:
            failure = "cancelled"
        except ModelProviderError as error:
            failure = error.code.value
        except ExecutionRejected as error:
            failure = (
                error.outcome
                if error.outcome
                in (
                    "cancelled",
                    "expired",
                    "timeout",
                    "budget_exhausted",
                    "audit_unavailable",
                )
                else "execution_stopped"
            )
        except ReportInputError:
            failure = "malformed_assessment"
        except AssessmentBoundaryError as error:
            failure = error.code
        except StoreStateError:
            failure = "attempt_not_active"
        except Exception:
            failure = "dependency_failure"
        if failure is not None:
            publication = None
            if started:
                try:
                    status = self.store.fail(
                        self.execution.identity, failure, at=self._at()
                    )
                except Exception:
                    failure = "audit_unavailable"
                try:
                    self.execution.stop(
                        "cancelled" if status == "cancelled" else "failed"
                    )
                except ExecutionRejected:
                    pass
        logging.getLogger("trace_app.workflow").info(
            "Investigation workflow finished.",
            extra={
                "event": "workflow.finished",
                "workflow_version": WORKFLOW_VERSION,
                "investigation_id": self.scope.investigation_id,
                "attempt_id": self.execution.identity.attempt_id,
                "correlation_id": self.execution.identity.correlation_id,
                "execution_status": status,
                "validation_outcome": validation.outcome,
                "failure_code": failure,
            },
        )
        return WorkflowResult(
            self,
            package,
            publication,
            response,
            validator,
            canonical(tasks),
            status,
            validation.outcome,
            failure,
            tuple(artifacts),
        )

    def _binding(self, package: EvidencePackage) -> dict[str, object]:
        content = source_content(package)
        return SourceAccessPolicy(self.authority, self.scope, clock=self._clock).bind(
            tuple(
                EvidenceSelection(identity, revision, ("content",))
                for identity, (revision, _) in content.items()
            ),
            expected_content={
                identity: value for identity, (_, value) in content.items()
            },
        )

    def _retain(self, package: EvidencePackage) -> str:
        # Retain failed/denied evidence privately too, but never disclose an unbound artifact.
        try:
            binding = self._binding(package)
            binding["configuration"] = (
                self.provider.configuration_metadata()
                if self.provider
                else {"provider": "none", "mode": "evidence_only"}
            )
        except Exception:
            binding = None
        return self.store.retain(
            self.execution.identity, package, at=self._at(), access_binding=binding
        )

    def _gather(self, query: EvidenceQuery, knowledge_query: str) -> EvidencePackage:
        package = build_evidence_package(
            self.tools,
            investigation_id=self.scope.investigation_id,
            query=query,
            knowledge_query=knowledge_query,
        )
        if package.status == "failed":
            raise AssessmentBoundaryError("execution_failure")
        return package

    def _generate(
        self,
        package: EvidencePackage,
        selections: tuple[EvidenceSelection, ...],
        job: Investigation,
        phase: str,
        *,
        history: tuple[ProtectedModelResponse, ...] = (),
        reason: str | None = None,
    ) -> ProtectedModelResponse:
        assert self.provider is not None and package.data is not None
        self.execution.checkpoint()
        admitted = {s.evidence_id for s in selections}
        for prior in history:
            admitted.update(v.citation_id for v in prior.citation_views(self.scope))
        frame = InvestigationFrame(
            job.request.service,
            job.request.environment,
            job.request.window_start,
            job.request.window_end,
            tuple(
                e["evidence_id"]
                for e in package.data["timeline"]["events"]
                if e["evidence_id"] in admitted
            ),
            AssessmentContext.from_package(package, self.scope).gaps(),
            phase,
            reason,
        )
        return self.provider.generate(
            ProviderCall(
                WORKFLOW_PROMPT,
                selections,
                ModelCallBounds(
                    self.execution.policy.model_timeout_ms,
                    self.execution.policy.max_model_response_bytes,
                    self.execution.policy.max_output_tokens,
                ),
                history,
                "correction" if phase == "correction" else "initial",
                frame,
            )
        )

    def _check_proposal(
        self,
        report: AssessmentReport,
        package: EvidencePackage,
        response: ProtectedModelResponse,
    ) -> None:
        assert package.data is not None
        admitted = {v.citation_id for v in response.citation_views(self.scope)}
        if (
            not set(report.references()) <= admitted
            or report.source_gaps
            != AssessmentContext.from_package(package, self.scope).gaps()
            or report.candidate.timeline_evidence_ids
            != tuple(
                e["evidence_id"]
                for e in package.data["timeline"]["events"]
                if e["evidence_id"] in admitted
            )
        ):
            raise AssessmentBoundaryError("citation_not_admitted")
        if isinstance(report.next_check.arguments, EvidenceArguments):
            proposed = report.next_check.arguments.query
            window = package.data["timeline"]["query"]
            if not (
                _parse_utc(window["window_start"])
                <= _parse_utc(proposed.window_start)
                <= _parse_utc(proposed.window_end)
                <= _parse_utc(window["window_end"])
            ):
                raise AssessmentBoundaryError("next_check_outside_window")
