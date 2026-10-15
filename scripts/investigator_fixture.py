"""Explicit, durable CLI simulation. No live provider or human endorsement."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import signal
import sqlite3
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Callable
from unittest.mock import patch

from scripts.demo_integration import integration_fixture
from scripts.demo_investigator import DEMO_POLICY, Clock, ScriptedModel, ScriptedReviews
from trace_app.adapters.models.journal import SqliteProviderJournal
from trace_app.adapters.sources.local_investigator import (
    LocalInvestigatorProfile,
    LocalSupportReviews,
)
from trace_app.bootstrap import create_local_investigator
from trace_app.cli import main as cli_main
from trace_app.investigation.models import EvidenceSnapshot
from trace_app.investigation.provider import (
    AdmissionGuard,
    ModelConfiguration,
    ModelErrorCode,
)
from trace_app.investigation.provider_policy import PolicyModelProvider
from trace_app.investigation.workflow import WORKFLOW_PROMPT
from trace_app.investigation.workflow_prompt import ASSESSMENT_PROMPT
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
        data = {
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


def invoke(profile_path: Path, arguments: list[str]) -> int:
    clock = Clock()
    data = json.loads(profile_path.read_text())
    config = data["fixture"]
    os.environ["TRACE_INVESTIGATOR_PROFILE"] = str(profile_path)

    def provider(scope, authority, execution):
        guard = AdmissionGuard(b"nonfunctional-cli-simulation-capability" * 2, clock)
        model = ScriptedModel(guard, config["case"] == "c04")
        if config["failure"] in ("timeout", "dependency_failure"):
            model.error = ModelErrorCode(config["failure"])
        if config["failure"] == "cancelled":

            def interrupt():
                os.kill(os.getpid(), signal.SIGTERM)

            model.after_call = interrupt
        return PolicyModelProvider(
            ModelConfiguration(
                "offline-simulation",
                "hand-authored-fixture",
                "offline-cli.v1",
                "scripted-cli.v1",
                mode="offline_test",
            ),
            model,
            authority,
            SqliteProviderJournal(
                profile_path.parent / "provider.sqlite3",
                execution.pricing,
                monthly_limit_nusd=20_000_000_000,
                initial_spend_nusd=0,
                now=clock(),
            ),
            guard,
            scope,
            {WORKFLOW_PROMPT: ASSESSMENT_PROMPT},
            execution=execution,
            read_clock=clock,
            duration_clock=clock,
        )

    def reviews(reader, scope, binding_id):
        current = json.loads(profile_path.read_text())
        rows = LocalSupportReviewsOriginal(reader, scope, binding_id)
        if rows or not config["reviewed"]:
            return rows
        # Explicit fictional decisions persist to exercise saved current-review checks.
        scripted = review_readers.setdefault(
            scope.investigation_id,
            ScriptedReviews(
                scope,
                True,
                claim_ids=("observation", "alternative", "assessment-outcome")
                if config["case"] == "c04"
                else ("observation", "primary", "alternative", "assessment-outcome"),
            ),
        )
        decisions = scripted.read(scope, binding_id)
        current["reviews"].extend(
            {
                "principal_id": scope.principal_id,
                "investigation_id": scope.investigation_id,
                "decision": asdict(d),
            }
            for d in decisions
        )
        profile_path.write_text(json.dumps(current))
        return decisions

    LocalSupportReviewsOriginal = LocalSupportReviews.read
    review_readers: dict = {}
    # Only manufacture synthetic decisions during the initial run. Saved inspection
    # must honor removed/changed decisions rather than recreate them.
    with sqlite3.connect(profile_path.parent / "evidence.sqlite3") as database:
        fresh = database.execute("SELECT COUNT(*) FROM attempts").fetchone()[0] == 0
    initial_run = arguments and arguments[0] == "investigate" and fresh
    with patch(
        "trace_app.cli.investigator.create_local_investigator",
        lambda path: create_local_investigator(
            path, clock=clock, fixture_provider=provider
        ),
    ):
        if initial_run and config["reviewed"]:
            with patch.object(LocalSupportReviews, "read", reviews):
                return cli_main(arguments)
        return cli_main(arguments)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--case", choices=("c01", "c04"), default="c01")
    parser.add_argument("--unreviewed", action="store_true")
    parser.add_argument(
        "--failure", choices=("timeout", "dependency_failure", "cancelled")
    )
    parser.add_argument("arguments", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    root = args.directory.absolute()
    profile_path = root / "profile.json"
    if not root.exists():
        prepare(
            root, case=args.case, reviewed=not args.unreviewed, failure=args.failure
        )
    data = json.loads(profile_path.read_text())
    arguments = args.arguments
    if arguments[:1] == ["--"]:
        arguments = arguments[1:]
    if not arguments:
        arguments = [
            "investigate",
            "--service",
            "order",
            "--environment",
            "test",
            "--window-start",
            data["fixture"]["window_start"],
            "--window-end",
            data["fixture"]["window_end"],
            "--provider",
            "offline-fixture",
            "--format",
            "json",
        ]
    return invoke(profile_path, arguments)


if __name__ == "__main__":
    sys.exit(main())
