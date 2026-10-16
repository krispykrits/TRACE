"""Observed-only reference arms. Explicit synthetic grants; never imports evaluation."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path

from scripts.demo_integration import integration_fixture
from scripts.demo_investigator import Clock, ScriptedModel, SyntheticAuthority
from scripts.investigator_suite import COMPARISON_SYMPTOM, write_private
from trace_app.adapters.models.journal import SqliteProviderJournal
from trace_app.adapters.storage.sqlite.investigations import SQLiteInvestigationStore
from trace_app.bootstrap import create_execution_session, create_tool_session
from trace_app.investigation.assessment_schema import AssessmentReport
from trace_app.investigation.execution import ExecutionIdentity, ExecutionPolicy
from trace_app.investigation.provider import (
    AdmissionGuard,
    ModelCallBounds,
    ModelConfiguration,
    ModelPricing,
)
from trace_app.investigation.provider_policy import (
    AuthorizedEvidence,
    EvidenceField,
    EvidenceSelection,
    InvestigationFrame,
    PolicyModelProvider,
    PromptTemplate,
    ProviderCall,
    ProviderScope,
    Sensitivity,
    SourceAccessPolicy,
    SourceKind,
)
from trace_app.investigation.tools import ToolPolicy
from trace_app.investigation.workflow_prompt import ASSESSMENT_PROMPT
from trace_app.knowledge.models import canonical, digest

PROMPT_ID = "local-mvp-brief-assessment.v1"
PROMPT = PromptTemplate(
    ASSESSMENT_PROMPT.instructions
    + "\nIncident brief: "
    + COMPARISON_SYMPTOM
    + "\nOnly an incident brief is available. No operational evidence or retrieval is available. Preserve uncertainty and abstain when the mechanism cannot be established. Cite only the incident brief; do not invent timeline evidence.",
    ASSESSMENT_PROMPT.response_schema_id,
)
CONFIGURATION = ModelConfiguration(
    "offline-simulation",
    "hand-authored-fixture",
    "offline-s5.v1",
    "investigator-suite-harness.v1",
    mode="offline_test",
)


def execute(root: Path, case: str, arm: str, policy: ExecutionPolicy) -> None:
    root.mkdir(mode=0o700)
    started = time.perf_counter()
    clock = Clock()
    with integration_fixture(case, limit=20) as fixture:
        with SQLiteInvestigationStore(fixture.root / "evidence.sqlite3") as store:
            job = store.claim_next(
                at=datetime.fromtimestamp(clock(), UTC), lease_seconds=125
            )
            assert job is not None and job.active_attempt_id is not None
            snapshot = store.get_snapshot(
                job.investigation_id, access_scope=fixture.scope.evidence.access_scope
            )
        scope = ProviderScope("synthetic-workflow-operator", job.investigation_id)
        execution = create_execution_session(
            evidence_db=fixture.root / "evidence.sqlite3",
            identity=ExecutionIdentity(
                job.investigation_id,
                job.active_attempt_id,
                fixture.scope.correlation_id,
                fixture.scope.evidence.access_scope,
            ),
            pricing=ModelPricing("azure-luna-global-ceiling-2026-09-22.v1", 250, 750),
            policy=policy,
            clock=clock,
        )
        observed = {
            "schema_version": "1",
            "query_window": {
                "start": snapshot.window_start,
                "end": snapshot.window_end,
            },
            "sources": [asdict(s) for s in snapshot.sources],
            "entries": [
                {
                    "kind": e.kind,
                    "record": e.record.to_dict(),
                    "payload": asdict(e.payload),
                }
                for e in snapshot.entries
            ],
        }
        brief = {
            "service": "order",
            "environment": "test",
            "window_start": snapshot.window_start,
            "window_end": snapshot.window_end,
            "symptom": COMPARISON_SYMPTOM,
        }
        result = {
            "schema_version": "local-mvp-reference.v1",
            "arm": arm,
            "brief": brief,
            "execution_status": "failed",
            "failure_code": None,
            "report": None,
            "citations": {},
            "timeline": [],
            "mutation_authority": False,
        }
        metadata = {}
        bindings = []
        sources = []
        try:
            if arm == "llm_only":
                record = AuthorizedEvidence(
                    "incident-brief",
                    "synthetic-incident-brief",
                    "brief.v1",
                    SourceKind.SYNTHETIC,
                    (
                        EvidenceField(
                            "content", canonical(brief), Sensitivity.INTERNAL, True
                        ),
                    ),
                    access_allowed=True,
                    transmission_allowed=True,
                    source_owner_allowed=True,
                    identifiers_reviewed=True,
                    expires_at=clock() + 120,
                )

                class BriefAuthority:
                    def resolve(self, current_scope, identity):
                        return (
                            record
                            if current_scope == scope and identity == "incident-brief"
                            else None
                        )

                authority = BriefAuthority()
                guard = AdmissionGuard(b"nonfunctional-local-mvp-reference" * 2, clock)
                provider = PolicyModelProvider(
                    CONFIGURATION,
                    ScriptedModel(guard, abstained=True),
                    authority,
                    SqliteProviderJournal(
                        fixture.root / "provider.sqlite3",
                        execution.pricing,
                        monthly_limit_nusd=20_000_000_000,
                        initial_spend_nusd=0,
                        now=clock(),
                    ),
                    guard,
                    scope,
                    {PROMPT_ID: PROMPT},
                    execution=execution,
                    read_clock=clock,
                    duration_clock=clock,
                )
                response = provider.generate(
                    ProviderCall(
                        PROMPT_ID,
                        (
                            EvidenceSelection(
                                "incident-brief", "brief.v1", ("content",)
                            ),
                        ),
                        ModelCallBounds(
                            timeout_ms=policy.model_timeout_ms,
                            max_output_tokens=policy.max_output_tokens,
                            max_response_bytes=policy.max_model_response_bytes,
                        ),
                        frame=InvestigationFrame(
                            "order",
                            "test",
                            snapshot.window_start,
                            snapshot.window_end,
                            (),
                            ("operational-evidence:unavailable",),
                        ),
                    )
                )
                candidate = response.structured_response(scope)
                parsed = AssessmentReport.from_dict(candidate)
                if parsed.candidate.timeline_evidence_ids or any(
                    set(claim.citations) != {"incident-brief"}
                    for claim in parsed.candidate.claims()
                ):
                    raise ValueError("reference_citation_not_admitted")
                result["report"] = candidate
                result["validation_outcome"] = "review_required"
                result["citations"] = {
                    v.citation_id: v.to_dict() for v in response.citation_views(scope)
                }
                bindings = [response.storage_binding(scope)]
                metadata = response.metadata()
                sources = [
                    {
                        "citation_id": record.evidence_id,
                        "revision": record.revision,
                        "kind": "synthetic",
                        "content_sha256": digest(canonical(brief)),
                    }
                ]
                # Keep source-derived access checks active through private capture.
                response.structured_response(scope)
            else:
                tools = create_tool_session(
                    evidence_db=fixture.root / "evidence.sqlite3",
                    corpus_db=fixture.root / "corpus.sqlite3",
                    index_root=fixture.root / "index",
                    scope=fixture.scope,
                    policy=ToolPolicy(max_attempts=policy.max_tool_calls),
                    execution=execution,
                    read_clock=lambda: datetime.fromtimestamp(clock(), UTC),
                )
                authority = SyntheticAuthority(fixture, scope, clock)
                access = SourceAccessPolicy(authority, scope, clock=clock)
                arguments = {
                    "window_start": snapshot.window_start,
                    "window_end": snapshot.window_end,
                    "limit": 20,
                }
                entries = []
                gaps = None
                for name in ("logs.query", "metrics.query", "deployments.query"):
                    payload = tools.invoke(name, arguments).payload
                    if payload.status not in ("ok", "empty", "partial"):
                        raise ValueError("reference_source_failure")
                    if gaps is not None and gaps != payload.data["sources"]:
                        raise ValueError("reference_source_changed")
                    gaps = payload.data["sources"]
                    entries.extend(payload.data["entries"])
                for entry in sorted(
                    entries,
                    key=lambda e: (
                        e["record"]["observed_at"],
                        e["record"]["evidence_id"],
                    ),
                ):
                    r = entry["record"]
                    identity = r["evidence_id"]
                    payload = tools.invoke(
                        "evidence.get",
                        {**arguments, "kind": entry["kind"], "evidence_id": identity},
                    ).payload
                    if payload.status != "ok" or payload.data["entries"] != [entry]:
                        raise ValueError("reference_source_changed")
                    bindings.append(
                        access.bind(
                            (
                                EvidenceSelection(
                                    identity, r["source_revision"], ("content",)
                                ),
                            ),
                            expected_content={identity: canonical(entry)},
                        )
                    )
                    result["timeline"].append(
                        {
                            "citation_id": identity,
                            "source_revision": r["source_revision"],
                            "observed_at": r["observed_at"],
                            "collected_at": r["collected_at"],
                            "causal_status": "observed",
                        }
                    )
                result["source_gaps"] = gaps
                for binding in bindings:
                    access.check_saved(
                        binding, transmission=False, clearance=Sensitivity.RESTRICTED
                    )
            result["execution_status"] = "completed"
        except Exception:
            # No untrusted dependency exception text or partial report is disclosed.
            result.update(
                execution_status="failed",
                failure_code="reference_execution_failure",
                report=None,
                citations={},
                timeline=[],
            )
        with sqlite3.connect(fixture.root / "evidence.sqlite3") as db:
            calls = [
                json.loads(r[0])
                for r in db.execute(
                    "SELECT metadata FROM execution_calls ORDER BY rowid"
                )
            ]
        for name, value in (
            ("observed.json", observed),
            ("result.json", result),
            ("sources.json", sources),
            (
                "execution.json",
                {
                    "jobs": [
                        {
                            "investigation_id": job.investigation_id,
                            "execution_status": result["execution_status"],
                            "failure_code": result["failure_code"],
                        }
                    ],
                    "calls": calls,
                    "latency_ms": (time.perf_counter() - started) * 1000,
                    "actual_provider_calls": 0,
                    "actual_human_review": False,
                    "response_metadata": metadata,
                    "access_bindings": bindings,
                    "execution_policies": [asdict(policy)],
                    "selected_configuration": CONFIGURATION.to_dict()
                    if arm == "llm_only"
                    else None,
                    "prompt_version": PROMPT_ID if arm == "llm_only" else None,
                    "prompt_sha256": digest(PROMPT.instructions)
                    if arm == "llm_only"
                    else None,
                    "evaluation_modules_loaded": sorted(
                        n
                        for n in sys.modules
                        if n == "evaluation" or n.startswith("evaluation.")
                    ),
                    "authority_changed": False,
                },
            ),
        ):
            write_private(root / name, value)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--case", choices=("c01", "c02", "c03", "c04"), required=True)
    parser.add_argument("--arm", choices=("llm_only", "evidence_bundle"), required=True)
    parser.add_argument("--policy", type=Path, required=True)
    args = parser.parse_args()
    execute(
        args.directory,
        args.case,
        args.arm,
        ExecutionPolicy(**json.loads(args.policy.read_text())),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
