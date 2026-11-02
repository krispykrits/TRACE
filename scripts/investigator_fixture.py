"""Synthetic source setup for investigation evaluation."""

from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from scripts.demo_integration import integration_fixture
from scripts.demo_investigator import DEMO_POLICY, Clock
from trace_app.adapters.sources.local_investigator import LocalInvestigatorProfile
from trace_app.investigation.models import EvidenceSnapshot
from trace_app.knowledge.models import digest


def prepare(
    root: Path,
    *,
    case: str = "c01",
    reviewed: bool = True,
    failure: str | None = None,
    transform: Callable[[EvidenceSnapshot], EvidenceSnapshot] | None = None,
) -> Path:
    root.mkdir(mode=0o700)
    with integration_fixture(case, transform=transform) as fixture:
        for path in fixture.root.iterdir():
            target = root / path.name
            if path.is_dir():
                shutil.copytree(path, target)
            else:
                shutil.copy2(path, target)
        data: dict[str, Any] = {
            "schema_version": "local-investigator.v1",
            "principal_id": "synthetic-cli-operator",
            "evidence_db": str(root / "evidence.sqlite3"),
            "corpus_db": str(root / "corpus.sqlite3"),
            "index_root": str(root / "index"),
            "source_investigation_id": fixture.scope.investigation_id,
            "evidence_scope": asdict(fixture.scope.evidence),
            "knowledge_scope": asdict(fixture.scope.knowledge),
            "execution_policy": asdict(DEMO_POLICY),
            "clearance": "restricted",
            "expires_at": "2026-10-12T13:00:00Z",
            "grants": {},
            "reviews": [],
            "fixture": {
                "case": case,
                "reviewed": reviewed,
                "failure": failure,
                "window_start": fixture.query.window_start,
                "window_end": fixture.query.window_end,
            },
        }
    profile_path = root / "profile.json"
    profile_path.write_text(json.dumps(data))
    profile_path.chmod(0o600)
    profile = LocalInvestigatorProfile(profile_path, clock=Clock())
    for identity, (revision, content, kind) in profile.source_content().items():
        data["grants"][identity] = {
            "revision": revision,
            "content_sha256": digest(content),
            "source_id": "synthetic-cli-source",
            "kind": kind.value,
            "sensitivity": "internal",
            "access_allowed": True,
            "transmission_allowed": True,
            "source_owner_allowed": True,
            "identifiers_reviewed": True,
            "fields_reviewed": True,
            "expires_at": data["expires_at"],
        }
    profile_path.write_text(json.dumps(data))
    return profile_path
