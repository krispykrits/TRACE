"""Prescribed Sprint 4 reads and fully resolved evidence; no model or diagnosis."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal, Protocol

from trace_app.evidence.models import EvidenceRecord, SourceAvailability
from trace_app.evidence.queries import EvidenceQuery
from trace_app.evidence.timeline import IncidentTimeline, order_evidence
from trace_app.investigation.models import (
    DeploymentPayload,
    EvidenceEntry,
    EvidenceSnapshot,
    LogPayload,
    MetricPayload,
    _identifier,
)
from trace_app.investigation.tools import ToolResult
from trace_app.knowledge.context import CONTEXT_VERSION
from trace_app.knowledge.models import KnowledgeChunk, canonical, digest

BUNDLE_VERSION = "scripted-evidence-bundle.v1"
MAX_PACKAGE_BYTES = 262_144


class ToolInvoker(Protocol):
    def invoke(self, name: object, arguments: object) -> ToolResult: ...


@dataclass(frozen=True, slots=True)
class EvidencePackage:
    status: Literal["complete", "partial", "failed"]
    data: dict[str, Any] | None
    data_sha256: str | None
    investigation_id: str
    audits: tuple[dict[str, object], ...]
    failure: dict[str, str | None] | None

    def to_dict(self) -> dict[str, object]:
        return {
            "version": BUNDLE_VERSION,
            "status": self.status,
            "data": self.data,
            "data_sha256": self.data_sha256,
            "execution": {
                "investigation_id": self.investigation_id,
                "audits": list(self.audits),
            },
            "failure": self.failure,
        }


class _ToolFailure(Exception):
    def __init__(self, tool: str, status: str, reason: str | None) -> None:
        self.details = {"tool": tool, "status": status, "reason": reason}


def _entry(value: dict[str, Any]) -> EvidenceEntry:
    if set(value) != {"kind", "record", "payload"}:
        raise ValueError("Invalid tool evidence envelope.")
    constructors = {
        "log": LogPayload,
        "metric": MetricPayload,
        "deployment": DeploymentPayload,
    }
    return EvidenceEntry(
        value["kind"],
        EvidenceRecord.from_dict(value["record"]),
        constructors[value["kind"]](**value["payload"]),
    )


def build_evidence_package(
    invoker: ToolInvoker,
    *,
    investigation_id: str,
    query: EvidenceQuery,
    knowledge_query: str,
    knowledge_service: str | None = None,
) -> EvidencePackage:
    """All knowledge and timeline references resolve before any package escapes."""
    _identifier("investigation_id", investigation_id)
    audits: list[dict[str, object]] = []
    current_tool = "logs.query"

    def call(name: str, arguments: dict[str, object]) -> dict[str, Any]:
        nonlocal current_tool
        current_tool = name
        try:
            result = invoker.invoke(name, arguments)
        except Exception as error:
            raise _ToolFailure(
                name, "dependency_failure", "tool_boundary_unavailable"
            ) from error
        audits.append(asdict(result.audit))
        if result.payload.status not in ("ok", "empty", "partial"):
            raise _ToolFailure(name, result.payload.status, result.payload.reason)
        return {"tool_status": result.payload.status, **result.payload.data}

    try:
        query_arguments: dict[str, object] = {
            "window_start": query.window_start,
            "window_end": query.window_end,
            "limit": query.limit,
            "service": query.service,
        }
        if query.kind is not None:
            raise ValueError("The bundle reads all three operational kinds.")
        entries: list[EvidenceEntry] = []
        sources: tuple[SourceAvailability, ...] | None = None
        matching_count = 0
        truncated = False
        for name, kind in (
            ("logs.query", "log"),
            ("metrics.query", "metric"),
            ("deployments.query", "deployment"),
        ):
            result = call(name, query_arguments)
            if (
                result.get("content_role") != "untrusted_source_data"
                or "entries" not in result
            ):
                raise ValueError("Operational result cannot supply a timeline.")
            current_sources = tuple(
                SourceAvailability(**source) for source in result["sources"]
            )
            if sources is not None and sources != current_sources:
                raise ValueError("Source availability changed between reads.")
            sources = current_sources
            batch = tuple(_entry(value) for value in result["entries"])
            if any(entry.kind != kind for entry in batch):
                raise ValueError("Tool returned the wrong evidence kind.")
            count = result["matching_count"]
            if (
                type(count) is not int
                or count < len(batch)
                or type(result["truncated"]) is not bool
            ):
                raise ValueError("Invalid source completeness accounting.")
            if count > len(batch) and not result["truncated"]:
                raise ValueError("Source loss must be disclosed.")
            entries.extend(batch)
            matching_count += count
            truncated |= result["truncated"]
        ordered = order_evidence(tuple(entries))
        snapshot = EvidenceSnapshot(
            ordered, query.window_start, query.window_end, sources or ()
        )
        incomplete = (
            truncated
            or not snapshot.sources
            or any(source.status != "available" for source in snapshot.sources)
        )
        timeline = IncidentTimeline(
            investigation_id,
            query,
            "incomplete" if incomplete else "complete" if ordered else "empty",
            ordered,
            snapshot.sources,
            matching_count,
            truncated,
        )

        knowledge = call(
            "knowledge.search", {"query": knowledge_query, "service": knowledge_service}
        )
        # The context's status is separate from the outer tool outcome.
        context_status = knowledge["status"]
        knowledge_tool_status = knowledge.pop("tool_status")
        if knowledge.get("version") != CONTEXT_VERSION or "data" not in knowledge:
            raise ValueError("Knowledge result cannot supply cited context.")
        context = knowledge["data"]
        if context.get("content_role") != "untrusted_source_data":
            raise ValueError("Knowledge is not untrusted source data.")
        if (
            len(canonical(context).encode()) != knowledge["used_bytes"]
            or knowledge["used_bytes"] > knowledge["budget"]["max_bytes"]
        ):
            raise ValueError("Context byte accounting differs.")
        citations = context["citations"]
        passages = context["passages"]
        if (
            len(passages) > 5
            or len({item["citation_id"] for item in passages}) != len(passages)
            or set(citations) != {item["citation_id"] for item in passages}
        ):
            raise ValueError("Context references differ from passage IDs.")

        # Finish list/search reads before resolving any references, so assembly
        # cannot accidentally rely on list authorization as standing ID access.
        for entry in ordered:
            result = call(
                "evidence.get",
                {
                    **query_arguments,
                    "kind": entry.kind,
                    "evidence_id": entry.record.evidence_id,
                },
            )
            if (
                result["tool_status"] != "ok"
                or len(result.get("entries", ())) != 1
                or _entry(result["entries"][0]) != entry
            ):
                raise _ToolFailure(
                    "evidence.get", "dependency_failure", "evidence_reference_changed"
                )
        for passage in passages:
            citation = citations[passage["citation_id"]]
            result = call(
                "knowledge.resolve",
                {
                    "generation_id": citation["corpus_generation_id"],
                    "chunk_id": citation["chunk_id"],
                    "service": knowledge_service,
                },
            )
            if result["tool_status"] != "ok":
                raise ValueError("Knowledge reference did not resolve fully.")
            chunk = KnowledgeChunk.from_dict(result["chunk"])
            mapping = {
                "corpus_generation_id": result["corpus_generation_id"],
                "chunk_id": chunk.chunk_id,
                "document_sha256": chunk.document_sha256,
                "section": chunk.section,
                "start_offset": chunk.start_offset,
                "end_offset": chunk.end_offset,
                "metadata": chunk.metadata.to_dict(),
            }
            if mapping != citation or chunk.text != passage["text"]:
                raise _ToolFailure(
                    "knowledge.resolve",
                    "dependency_failure",
                    "knowledge_reference_changed",
                )

        stable_timeline = timeline.to_dict()
        stable_timeline.pop("investigation_id")
        partial = incomplete or knowledge["incomplete"] or not passages
        data = {
            "version": BUNDLE_VERSION,
            "content_role": "untrusted_source_data",
            "timeline": stable_timeline,
            "knowledge": {
                "status": context_status,
                "tool_status": knowledge_tool_status,
                "context": knowledge,
            },
            "references": {
                "evidence": [entry.record.evidence_id for entry in ordered],
                "knowledge": sorted(citations),
                "all_resolved": True,
            },
            "missing_knowledge": not passages,
            "incomplete": partial,
            "assessment": "not_performed",
        }
        if len(canonical(data).encode()) > MAX_PACKAGE_BYTES:
            raise _ToolFailure(
                current_tool, "dependency_failure", "package_byte_bound_exceeded"
            )
        # Only source data is canonical. Real audit/IDs remain in execution.
        return EvidencePackage(
            "partial" if partial else "complete",
            data,
            digest(canonical(data)),
            investigation_id,
            tuple(audits),
            None,
        )
    except _ToolFailure as error:
        return EvidencePackage(
            "failed", None, None, investigation_id, tuple(audits), error.details
        )
    except (ValueError, TypeError, KeyError):
        return EvidencePackage(
            "failed",
            None,
            None,
            investigation_id,
            tuple(audits),
            {
                "tool": current_tool,
                "status": "dependency_failure",
                "reason": "inconsistent_evidence_package",
            },
        )
