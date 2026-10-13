"""Deadline-isolated local reads; worker receives only trusted configured sources."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Callable

from trace_app.evidence.models import _parse_utc, format_utc
from trace_app.evidence.queries import EvidenceQueryService, TrustedQueryContext
from trace_app.investigation.models import (
    EvidenceEntry,
    StoreAccessError,
    StoreDependencyError,
    StoreInputError,
    StoreSchemaError,
)
from trace_app.investigation.tools import (
    CitationArguments,
    EvidenceArguments,
    KnowledgeArguments,
    ToolAudit,
    ToolCall,
    ToolPayload,
    ToolPolicy,
    ToolScope,
    ToolStatus,
)
from trace_app.knowledge.models import (
    CorpusAccessError,
    CorpusDependencyError,
    CorpusReadContext,
)


@dataclass(frozen=True, slots=True)
class LocalToolSources:
    evidence_db: Path
    corpus_db: Path
    index_root: Path

    def to_dict(self) -> dict[str, str]:
        return {name: str(path.absolute()) for name, path in asdict(self).items()}


class LoggingToolAudit:
    def emit(self, record: ToolAudit) -> None:
        logging.getLogger("trace_app.tools").info(
            "Read-only tool attempt completed.",
            extra={"event": "tools.attempt.completed", **asdict(record)},
        )


def _run_process(
    command: list[str], request: bytes, *, timeout_ms: int, max_bytes: int
) -> bytes:
    # This helper is internal. Neither the command nor environment is tool input.
    environment = {
        "PATH": os.defpath,
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
    }
    with subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=environment,
    ) as process:
        try:
            output, _ = process.communicate(request, timeout=timeout_ms / 1000)
        except subprocess.TimeoutExpired as error:
            process.kill()
            process.communicate()
            raise TimeoutError("Tool deadline exceeded.") from error
        if process.returncode or len(output) > max_bytes:
            raise RuntimeError("Tool worker failed or exceeded its output bound.")
        return output


class LocalToolBackend:
    """No publisher handles are inherited; each worker opens mode=ro databases."""

    def __init__(
        self,
        sources: LocalToolSources,
        *,
        read_clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._sources = sources
        self._read_clock = read_clock

    def execute(
        self, call: ToolCall, scope: ToolScope, policy: ToolPolicy, *, timeout_ms: int
    ) -> ToolPayload:
        request = json.dumps(
            {
                "sources": self._sources.to_dict(),
                "name": call.name,
                "arguments": call.to_arguments(),
                "scope": asdict(scope),
                "policy": asdict(policy),
                "read_at": format_utc(self._read_clock()) if self._read_clock else None,
            },
            allow_nan=False,
        ).encode()
        output = _run_process(
            [sys.executable, "-I", "-m", "trace_app.adapters.tools.local"],
            request,
            timeout_ms=timeout_ms,
            max_bytes=policy.max_result_bytes,
        )
        value = json.loads(output)
        if not isinstance(value, dict) or set(value) != {"status", "data", "reason"}:
            raise ValueError("Invalid worker envelope.")
        if value["status"] not in (
            "ok",
            "empty",
            "partial",
            "authorization_error",
            "dependency_failure",
            "validation_error",
        ) or not isinstance(value["data"], dict):
            raise ValueError("Invalid worker outcome.")
        return ToolPayload(**value)


def _encoded(payload: ToolPayload) -> bytes:
    return json.dumps(asdict(payload), ensure_ascii=False, allow_nan=False).encode()


def _entry_data(entry: EvidenceEntry) -> dict[str, object]:
    return {
        "kind": entry.kind,
        "record": entry.record.to_dict(),
        "payload": asdict(entry.payload),
    }


def _read(
    call: ToolCall,
    scope: ToolScope,
    sources: LocalToolSources,
    policy: ToolPolicy,
    *,
    at: datetime | None = None,
) -> ToolPayload:
    if isinstance(call.arguments, EvidenceArguments):
        from trace_app.adapters.storage.sqlite.investigations import (
            SQLiteInvestigationStore,
        )

        try:
            reader = SQLiteInvestigationStore(sources.evidence_db, read_only=True)
        except StoreInputError as error:
            raise StoreDependencyError(
                "Configured evidence source is unavailable."
            ) from error
        with reader as store:
            service = EvidenceQueryService(store, max_limit=policy.max_results)
            args = call.arguments
            if args.evidence_id is not None:
                entry = service.get_by_id(
                    scope.investigation_id,
                    args.evidence_id,
                    args.query,
                    context=scope.evidence,
                )
                payload = ToolPayload(
                    "ok",
                    {
                        "content_role": "untrusted_source_data",
                        "entries": [_entry_data(entry)],
                        "truncated": False,
                    },
                )
            else:
                result = service.query(
                    scope.investigation_id, args.query, context=scope.evidence
                )
                if result.status in ("snapshot_missing", "storage_failure"):
                    return ToolPayload("dependency_failure", {}, result.failure_code)
                data: dict[str, object] = {
                    "content_role": "untrusted_source_data",
                    "entries": [],
                    "sources": [asdict(source) for source in result.sources],
                    "matching_count": result.matching_count,
                    "truncated": result.truncated,
                    "source_status": result.status,
                }
                entries: list[dict[str, object]] = []
                dropped = 0
                for entry in result.entries:
                    data["entries"] = [*entries, _entry_data(entry)]
                    candidate = ToolPayload("partial", data)
                    if len(_encoded(candidate)) <= policy.max_result_bytes:
                        entries.append(_entry_data(entry))
                    else:
                        dropped += 1
                data["entries"] = entries
                data["byte_budget_omissions"] = dropped
                data["truncated"] = result.truncated or dropped > 0
                status: ToolStatus = (
                    "partial"
                    if result.status == "incomplete" or dropped
                    else "ok"
                    if entries
                    else "empty"
                )
                payload = ToolPayload(status, data)
            return payload

    from trace_app.adapters.retrieval.exact_scoring import LocalExactScorer
    from trace_app.adapters.retrieval.local_index import load_index
    from trace_app.adapters.storage.sqlite.corpus import SQLiteCorpusStore
    from trace_app.knowledge.context import ContextAssembler, ContextBudget
    from trace_app.knowledge.index import chunk_fingerprint
    from trace_app.knowledge.search import SearchService

    at = at or datetime.now(UTC)
    with SQLiteCorpusStore(sources.corpus_db, read_only=True) as corpus:
        index = load_index(sources.index_root)
        if isinstance(call.arguments, CitationArguments):
            citation = call.arguments
            if (
                citation.generation_id != index.corpus_generation_id
                or citation.chunk_id not in index.chunk_ids
            ):
                raise CorpusAccessError("Citation is outside the configured index.")
            chunk = corpus.resolve(
                citation.generation_id,
                citation.chunk_id,
                context=scope.knowledge,
                at=at,
            )
            if (
                citation.service is not None
                and chunk.metadata.service != citation.service
            ):
                raise CorpusAccessError(
                    "Citation does not match the narrowing service."
                )
            if (
                chunk_fingerprint(chunk)
                != index.chunk_fingerprints[index.chunk_ids.index(chunk.chunk_id)]
            ):
                raise CorpusAccessError("Citation provenance changed.")
            return ToolPayload(
                "ok",
                {
                    "content_role": "untrusted_source_data",
                    "corpus_generation_id": citation.generation_id,
                    "chunk": chunk.to_dict(),
                    "truncated": False,
                },
            )
        assert isinstance(call.arguments, KnowledgeArguments)
        response = SearchService(corpus, index, scorer=LocalExactScorer()).search(
            call.arguments.request, context=scope.knowledge, at=at
        )
        context = ContextAssembler(corpus).assemble(
            response,
            context=scope.knowledge,
            at=at,
            budget=ContextBudget(
                min(8192, max(512, policy.max_result_bytes - 2048)),
                call.arguments.max_passages,
            ),
        )
        if context.status == "source_unavailable":
            return ToolPayload("authorization_error", {}, "source_not_authorized")
        if context.status in ("retrieval_failed", "storage_failure"):
            return ToolPayload("dependency_failure", {}, "knowledge_unavailable")
        data = context.to_dict()
        knowledge_status: ToolStatus = (
            "partial"
            if data["incomplete"]
            else "ok"
            if context.status == "ok"
            else "empty"
        )
        return ToolPayload(knowledge_status, data)


def main() -> int:
    """Private worker protocol, selected by bootstrap, never a model tool."""
    try:
        raw = sys.stdin.buffer.read(32_769)
        if len(raw) > 32_768:
            raise ValueError("Worker request exceeds bound.")
        value = json.loads(raw)
        policy = ToolPolicy(**value["policy"])
        grants = value["scope"]
        evidence = {
            **grants["evidence"],
            "allowed_services": tuple(grants["evidence"]["allowed_services"]),
        }
        knowledge = {
            **grants["knowledge"],
            "allowed_services": tuple(grants["knowledge"]["allowed_services"]),
        }
        scope = ToolScope(
            grants["investigation_id"],
            grants["correlation_id"],
            TrustedQueryContext(**evidence),
            CorpusReadContext(**knowledge),
        )
        call = ToolCall.parse(value["name"], value["arguments"], policy)
        sources = LocalToolSources(
            **{key: Path(path) for key, path in value["sources"].items()}
        )
        payload = _read(
            call,
            scope,
            sources,
            policy,
            at=_parse_utc(value["read_at"]) if value["read_at"] else None,
        )
        if len(_encoded(payload)) > policy.max_result_bytes:
            payload = ToolPayload(
                "partial",
                {
                    "content_role": "untrusted_source_data",
                    "truncated": True,
                    "whole_result_omitted": True,
                },
                "result_byte_bound_exceeded",
            )
    except (StoreAccessError, CorpusAccessError):
        payload = ToolPayload("authorization_error", {}, "source_not_authorized")
    except StoreInputError:
        payload = ToolPayload(
            "validation_error", {}, "query_outside_investigation_window"
        )
    except (
        StoreSchemaError,
        StoreDependencyError,
        CorpusDependencyError,
        OSError,
    ):
        payload = ToolPayload("dependency_failure", {}, "source_unavailable")
    except Exception:
        payload = ToolPayload("dependency_failure", {}, "worker_unavailable")
    sys.stdout.buffer.write(_encoded(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
