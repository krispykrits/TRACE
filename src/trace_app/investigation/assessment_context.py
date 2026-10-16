"""Snapshot-bound current citation checks through the existing read-only tools."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from trace_app.evidence.models import _parse_utc
from trace_app.investigation.bundle import EvidencePackage, ToolInvoker
from trace_app.investigation.provider_policy import ProviderScope
from trace_app.knowledge.models import KnowledgeChunk, canonical, digest


class AssessmentBoundaryError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = (
            code
            if isinstance(code, str)
            and code
            in {
                "execution_failure",
                "invalid_context",
                "citation_denied",
                "citation_not_in_context",
                "citation_mismatch",
                "invalid_review_sample",
                "support_not_accepted",
                "access_denied",
                "response_schema_mismatch",
                "timeline_mismatch",
                "source_gaps_missing",
                "unsupported_causal_basis",
                "reserved_claim_id",
                "next_check_outside_window",
                "citation_not_admitted",
                "invalid_review",
                "invalid_response",
                "malformed_assessment",
                "scope_mismatch",
                "review_denied",
            }
            else "dependency_failure"
        )
        super().__init__("Assessment boundary validation failed.")


@dataclass(frozen=True, slots=True)
class AssessmentContext:
    scope: ProviderScope = field(repr=False)
    _data_json: str = field(repr=False)

    @classmethod
    def from_package(
        cls, package: EvidencePackage, scope: ProviderScope
    ) -> AssessmentContext:
        if package.status == "failed":
            raise AssessmentBoundaryError("execution_failure")
        try:
            if (
                package.investigation_id != scope.investigation_id
                or package.data is None
            ):
                raise ValueError
            data = canonical(package.data)
            if len(data.encode()) > 262_144 or digest(data) != package.data_sha256:
                raise ValueError
            value = json.loads(data)
            if (
                value["timeline"].get("status")
                not in ("complete", "incomplete", "empty")
                or value["timeline"].get("failure_code") is not None
                or value["knowledge"]["context"].get("status") not in ("ok", "empty")
            ):
                raise AssessmentBoundaryError("execution_failure")
            if (
                value["references"]["all_resolved"] is not True
                or value["content_role"] != "untrusted_source_data"
            ):
                raise ValueError
            events = value["timeline"]["events"]
            if len(events) > 100 or len({e["evidence_id"] for e in events}) != len(
                events
            ):
                raise ValueError
            if events != sorted(
                events,
                key=lambda e: (
                    _parse_utc(e["record"]["observed_at"]),
                    e["evidence_id"],
                ),
            ):
                raise ValueError
            if [e["evidence_id"] for e in events] != value["references"]["evidence"]:
                raise ValueError
            for event in events:
                _parse_utc(event["record"]["collected_at"])
                if (
                    event["evidence_id"] != event["record"]["evidence_id"]
                    or event["causal_status"] != "observed"
                ):
                    raise ValueError
            citations = value["knowledge"]["context"]["data"]["citations"]
            if (
                sorted(citations) != value["references"]["knowledge"]
                or len(citations) > 20
            ):
                raise ValueError
            return cls(scope, data)
        except AssessmentBoundaryError:
            raise
        except (
            ValueError,
            TypeError,
            KeyError,
            UnicodeError,
            AttributeError,
            RecursionError,
        ):
            raise AssessmentBoundaryError("invalid_context") from None

    def data(self) -> dict[str, Any]:
        return json.loads(self._data_json)

    def gaps(self) -> tuple[str, ...]:
        value = self.data()
        timeline = value["timeline"]
        result = [
            f"{s['source']}:{s['status']}"
            for s in timeline["sources"]
            if s["status"] != "available"
        ]
        if not timeline["sources"]:
            result.append("evidence:inventory_unknown")
        if timeline["truncated"]:
            result.append("evidence:truncated")
        knowledge = value["knowledge"]["context"]
        if value["missing_knowledge"]:
            result.append("knowledge:missing")
        if knowledge["incomplete"]:
            result.append("knowledge:incomplete")
        if knowledge["omitted"]:
            result.append("knowledge:omitted")
        omitted = value.get("model_context_omissions", {})
        if omitted.get("evidence"):
            result.append("evidence:context_omitted")
        if omitted.get("knowledge"):
            result.append("knowledge:context_omitted")
        return tuple(sorted(set(result)))


class ToolCitationResolver:
    """Composition supplies the fixed tool session; model text cannot pick one."""

    def __init__(self, invoker: ToolInvoker, context: AssessmentContext) -> None:
        self._invoker = invoker
        self._context = context

    def resolve(self, scope: ProviderScope, identity: str) -> dict[str, object]:
        if scope != self._context.scope:
            raise AssessmentBoundaryError("citation_denied")
        data = self._context.data()
        event = next(
            (e for e in data["timeline"]["events"] if e["evidence_id"] == identity),
            None,
        )
        if event is not None:
            query = data["timeline"]["query"]
            name = "evidence.get"
            arguments = {**query, "kind": event["kind"], "evidence_id": identity}
        else:
            citation = data["knowledge"]["context"]["data"]["citations"].get(identity)
            if citation is None:
                raise AssessmentBoundaryError("citation_not_in_context")
            name = "knowledge.resolve"
            arguments = {
                "generation_id": citation["corpus_generation_id"],
                "chunk_id": citation["chunk_id"],
            }
        try:
            payload = self._invoker.invoke(name, arguments).payload
        except Exception:
            raise AssessmentBoundaryError("execution_failure") from None
        if payload.status in ("timeout", "dependency_failure", "budget_exhausted"):
            raise AssessmentBoundaryError("execution_failure")
        if payload.status != "ok":
            raise AssessmentBoundaryError("citation_denied")
        try:
            if event is not None:
                expected = {key: event[key] for key in ("kind", "record", "payload")}
                if payload.data["entries"] != [expected]:
                    raise ValueError
                record = event["record"]
                return {
                    "kind": "evidence",
                    "source_revision": record["source_revision"],
                    "observed_at": record["observed_at"],
                    "collected_at": record["collected_at"],
                }
            chunk = KnowledgeChunk.from_dict(payload.data["chunk"])
            mapping = {
                "corpus_generation_id": payload.data["corpus_generation_id"],
                "chunk_id": chunk.chunk_id,
                "document_sha256": chunk.document_sha256,
                "section": chunk.section,
                "start_offset": chunk.start_offset,
                "end_offset": chunk.end_offset,
                "metadata": chunk.metadata.to_dict(),
            }
            passage = next(
                p
                for p in data["knowledge"]["context"]["data"]["passages"]
                if p["citation_id"] == identity
            )
            if mapping != citation or chunk.text != passage["text"]:
                raise ValueError
            return {
                "kind": "knowledge",
                "source_revision": chunk.metadata.source_revision,
                **{
                    key: mapping[key]
                    for key in (
                        "corpus_generation_id",
                        "chunk_id",
                        "start_offset",
                        "end_offset",
                    )
                },
                "section": "[WITHHELD]",
            }
        except (ValueError, TypeError, KeyError, StopIteration):
            raise AssessmentBoundaryError("citation_mismatch") from None
