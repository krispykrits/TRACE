"""Evaluator-only known-score exports; never application/provider inputs."""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evaluation.runner import _expected
from trace_app.demo.scenarios import ScenarioConfig, ScenarioSession
from trace_app.knowledge.models import canonical, digest


def score_fixture() -> tuple[dict, dict, dict, dict, list, Any]:
    root = Path(__file__).resolve().parents[2]
    candidate = json.loads(
        (root / "evaluation/fixtures/candidates_v1.json").read_text()
    )["attempts"][0]["report"]
    snapshot = (
        ScenarioSession(ScenarioConfig("c01", 17))
        .replay(collected_at=datetime(2026, 10, 12, 12, tzinfo=UTC))
        .snapshot
    )
    observed: dict[str, Any] = {
        "schema_version": "1",
        "query_window": {"start": snapshot.window_start, "end": snapshot.window_end},
        "sources": [asdict(s) for s in snapshot.sources],
        "entries": [
            {"kind": e.kind, "record": e.record.to_dict(), "payload": asdict(e.payload)}
            for e in snapshot.entries
        ],
    }
    candidate["schema_version"] = "assessment.v2"
    candidate["next_check"] = {
        "tool": "logs.query",
        "arguments": {
            "window_start": snapshot.window_start,
            "window_end": snapshot.window_end,
            "limit": 5,
        },
        "reason": "Inspect authorized observations.",
    }
    candidate["source_gaps"] = [
        f"{s.source}:{s.status}" for s in snapshot.sources if s.status != "available"
    ]
    for hypothesis in [
        candidate["primary_hypothesis"],
        *candidate["alternative_hypotheses"],
    ]:
        if hypothesis:
            hypothesis.update(contradicting_citations=[], causal_basis="mechanism")
    citations: dict[str, Any] = {}
    sources: list[dict[str, Any]] = []
    for entry in observed["entries"]:
        record = entry["record"]
        content = canonical(entry)
        identity = record["evidence_id"]
        sources.append(
            {
                "citation_id": identity,
                "revision": record["source_revision"],
                "kind": "synthetic",
                "content_sha256": digest(content),
            }
        )
        citations[identity] = {
            "citation_id": identity,
            "source_revision": record["source_revision"],
            "fields": {"content": content},
            "redactions": [],
            "source_mapping": {
                "kind": "evidence",
                "source_revision": record["source_revision"],
                "observed_at": record["observed_at"],
                "collected_at": record["collected_at"],
            },
        }
    result = {
        "schema_version": "investigation-cli.v1",
        "investigation_id": "known-job",
        "execution_status": "completed",
        "failure_code": None,
        "assessment_status": "supported",
        "validation_outcome": "accepted",
        "report": candidate,
        "citations": citations,
        "timeline": [
            {
                "citation_id": identity,
                **citations[identity]["source_mapping"],
                "causal_status": "observed",
            }
            for identity in candidate["timeline_evidence_ids"]
        ],
        "configuration": {"mode": "offline_test"},
        "attempts": [{"attempt_id": 1, "outcome": "completed"}],
        "mutation_authority": False,
    }
    execution = {
        "jobs": [
            {
                "investigation_id": "known-job",
                "execution_status": "completed",
                "failure_code": None,
            }
        ],
        "calls": [
            {
                "kind": "model",
                "usage": {"input_tokens": 5, "output_tokens": 3},
                "estimated_cost_nusd": 8,
            },
            {"kind": "tool"},
        ],
        "latency_ms": 12.0,
        "guard_checks": {
            "narrow_audience": True,
            "wrong_actor": True,
            "transmission_revoked": True,
        },
        "evaluation_modules_loaded": [],
        "authority_changed": False,
        "model_invocations": 1,
        "actual_provider_calls": 0,
        "harness_exit_code": 0,
        "exit_code": 0,
    }
    case = {
        "id": "d01",
        "case_id": "c01",
        "seed": 17,
        "fault": "none",
        "role": "development_incident",
    }
    expected = _expected(
        json.loads((root / "evaluation/ground_truth/mvp_suite_v1.json").read_text())
    )["c01"]
    return case, observed, result, execution, sources, expected
