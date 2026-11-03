"""Deadline-isolated PostgreSQL reads for hosted investigation tools."""

import json
import os
import sys
from dataclasses import asdict, replace
from datetime import UTC, datetime
from typing import Any

from psycopg.rows import dict_row

from trace_app.adapters.sources.postgres_investigator import PostgresInvestigatorProfile
from trace_app.adapters.storage.postgres.connection import connect
from trace_app.adapters.tools.local import _encoded, _read, _run_process
from trace_app.evidence.models import _parse_utc, format_utc
from trace_app.evidence.queries import TrustedQueryContext
from trace_app.investigation.tools import (
    EvidenceArguments,
    ToolCall,
    ToolPayload,
    ToolPolicy,
    ToolScope,
)
from trace_app.knowledge.models import CorpusReadContext


class PostgresToolBackend:
    def __init__(self, profile: PostgresInvestigatorProfile):
        self.profile = profile

    def execute(
        self, call: ToolCall, scope: ToolScope, policy: ToolPolicy, *, timeout_ms: int
    ) -> ToolPayload:
        self.profile.current()
        source_scope = replace(
            scope, investigation_id=self.profile.source_investigation_id
        )
        request = json.dumps(
            {
                "name": call.name,
                "job_id": scope.investigation_id,
                "arguments": call.to_arguments(),
                "scope": asdict(source_scope),
                "policy": asdict(policy),
                "read_at": format_utc(
                    datetime.fromtimestamp(self.profile.clock(), UTC)
                ),
            },
            allow_nan=False,
        ).encode()
        names = (
            "AZURE_CLIENT_ID",
            "AZURE_TENANT_ID",
            "AZURE_FEDERATED_TOKEN_FILE",
            "AZURE_AUTHORITY_HOST",
            "SSL_CERT_FILE",
            "TRACE_POSTGRES_AUTH",
        )
        env = {key: os.environ[key] for key in names if key in os.environ}
        env.update(
            TRACE_POSTGRES_DSN=self.profile.dsn, TRACE_SOURCE_ID=self.profile.source_id
        )
        output = _run_process(
            [sys.executable, "-I", "-m", "trace_app.adapters.tools.postgres"],
            request,
            timeout_ms=timeout_ms,
            max_bytes=policy.max_result_bytes,
            extra_environment=env,
        )
        value = json.loads(output)
        if (
            not isinstance(value, dict)
            or set(value) != {"status", "data", "reason"}
            or value["status"]
            not in (
                "ok",
                "empty",
                "partial",
                "authorization_error",
                "dependency_failure",
                "validation_error",
            )
            or not isinstance(value["data"], dict)
        ):
            raise ValueError("Invalid worker outcome.")
        return ToolPayload(**value)


def main() -> int:
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
        with connect(
            os.environ["TRACE_POSTGRES_DSN"],
            row_factory=dict_row,
            connect_timeout=5,
            autocommit=True,
        ) as connection:
            payload = _execute(value, scope, call, policy, connection)
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
    except PermissionError:
        payload = ToolPayload("authorization_error", {}, "source_not_authorized")
    except Exception:
        payload = ToolPayload("dependency_failure", {}, "source_unavailable")
    sys.stdout.buffer.write(_encoded(payload))
    return 0


def _execute(
    value: dict[str, Any],
    scope: ToolScope,
    call: ToolCall,
    policy: ToolPolicy,
    connection: Any,
) -> ToolPayload:
    profile = PostgresInvestigatorProfile(
        os.environ["TRACE_POSTGRES_DSN"],
        os.environ["TRACE_SOURCE_ID"],
        connection=connection,
    )
    allowed = set(profile.allowed_for_job(value["job_id"]))
    # The database profile, rather than tool arguments, supplies authority.
    if (
        replace(scope.evidence, allowed_services=profile.evidence.allowed_services)
        != profile.evidence
        or replace(scope.knowledge, allowed_services=profile.knowledge.allowed_services)
        != profile.knowledge
        or not set(scope.evidence.allowed_services)
        <= allowed.intersection(profile.evidence.allowed_services)
        or not set(scope.knowledge.allowed_services)
        <= allowed.intersection(profile.knowledge.allowed_services)
        or scope.investigation_id != profile.source_investigation_id
    ):
        raise PermissionError("Source scope changed.")
    return _read(
        call,
        scope,
        None,
        policy,
        at=_parse_utc(value["read_at"]),
        reader=profile,
        corpus_reader=profile,
        index_generation=None
        if isinstance(call.arguments, EvidenceArguments)
        else profile.index(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
