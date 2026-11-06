"""Check hosted PostgreSQL sources preserve the existing evidence boundaries."""

import copy
import json
import unittest
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from scripts.demo_investigator import Clock
from scripts.investigator_fixture import prepare
from trace_app.adapters.sources.authority import LocalEvidenceAuthority
from trace_app.adapters.sources.local_investigator import LocalInvestigatorProfile
from trace_app.adapters.sources.postgres_investigator import PostgresInvestigatorProfile
from trace_app.adapters.storage.postgres.evidence import PostgresEvidenceStore
from trace_app.adapters.storage.sqlite.corpus import SQLiteCorpusStore
from trace_app.adapters.storage.sqlite.investigations import SQLiteInvestigationStore
from trace_app.adapters.tools.local import _read
from trace_app.investigation.models import StoreAccessError
from trace_app.investigation.provider import ModelProviderError
from trace_app.investigation.provider_policy import (
    EvidenceSelection,
    SourceAccessPolicy,
)
from trace_app.investigation.tools import ToolCall, ToolPolicy, ToolScope


def synthetic_package(path):
    old = LocalInvestigatorProfile(path, clock=Clock())
    profile = json.loads(path.read_text())
    profile["schema_version"] = "postgres-investigator.v1"
    for key in ("evidence_db", "corpus_db", "index_root"):
        profile.pop(key)
    with SQLiteInvestigationStore(old.evidence_db, read_only=True) as source:
        job = source.get_investigation(
            old.source_investigation_id, access_scope=old.evidence.access_scope
        )
        snapshot = source.get_snapshot(
            old.source_investigation_id, access_scope=old.evidence.access_scope
        )
    root = old.index_root / (old.index_root / "CURRENT").read_text().strip()
    manifest = json.loads((root / "manifest.json").read_text())
    with SQLiteCorpusStore(old.corpus_db, read_only=True) as corpus:
        generation = json.loads(
            corpus._connection.execute(
                "SELECT manifest FROM generations WHERE id=?",
                (manifest["corpus_generation_id"],),
            ).fetchone()[0]
        )
        rows = corpus._connection.execute(
            "SELECT c.payload, s.metadata, s.status FROM chunks c JOIN sources s ON c.document_id=s.document_id WHERE c.generation_id=?",
            (manifest["corpus_generation_id"],),
        ).fetchall()
        chunks = [
            {
                "chunk": json.loads(r[0]),
                "current_metadata": json.loads(r[1]),
                "status": r[2],
            }
            for r in rows
        ]
    package = {
        "profile": profile,
        "capture": {
            "investigation": asdict(job),
            "snapshot": PostgresEvidenceStore._data(snapshot),
        },
        "knowledge": {
            "manifest": generation,
            "index_manifest": manifest,
            "index_records": json.loads((root / "records.json").read_text()),
            "chunks": chunks,
        },
    }
    return old, package, job, snapshot


class PostgresSourceTest(unittest.TestCase):
    def test_authority_checks_use_one_fresh_source_read(self):
        with TemporaryDirectory() as temp:
            path = prepare(Path(temp) / "source")
            _, package, _, _ = synthetic_package(path)
            loader = MagicMock(side_effect=lambda: copy.deepcopy(package))
            profile = PostgresInvestigatorProfile(
                "unused", "synthetic", clock=Clock(), source_loader=loader
            )
            scope = profile.scope("job-1")
            authority = LocalEvidenceAuthority(profile, scope)
            identities = tuple(profile.source_content())[:2]
            loader.reset_mock()
            records = authority.resolve_many(scope, identities)
            self.assertTrue(all(records.values()))
            self.assertEqual(loader.call_count, 1)
            selections = []
            for identity in identities:
                record = records[identity]
                assert record is not None
                selections.append(
                    EvidenceSelection(identity, record.revision, ("content",))
                )
            SourceAccessPolicy(authority, scope, clock=Clock()).bind(tuple(selections))
            self.assertEqual(loader.call_count, 2)
            package["profile"]["grants"].pop(identities[0])
            self.assertIsNone(authority.resolve(scope, identities[0]))
            self.assertEqual(loader.call_count, 3)
            with self.assertRaises(ModelProviderError):
                SourceAccessPolicy(authority, scope, clock=Clock()).bind(
                    tuple(selections)
                )

    def test_active_job_service_grants_are_rechecked(self):
        profile = object.__new__(PostgresInvestigatorProfile)
        profile.dsn = "unused"
        profile._connection = None
        profile.principal_id = "entra:tenant:user"
        profile.evidence = MagicMock(access_scope="scope", environment="test")
        row = {
            "submitted_tenant": "tenant",
            "submitted_object": "user",
            "access_scope": "scope",
            "environment": "test",
            "grant_scope": "scope",
            "grant_environment": "test",
            "service": "order",
            "services": ["order"],
            "actions": ["submit"],
        }
        with patch(
            "trace_app.adapters.sources.postgres_investigator.connect"
        ) as connect:
            connection = connect.return_value.__enter__.return_value
            connection.execute.return_value.fetchone.return_value = row
            self.assertEqual(profile.allowed_for_job("job"), ("order",))
            row["actions"] = []
            with self.assertRaises(StoreAccessError):
                profile.allowed_for_job("job")

    def test_tool_reads_share_connection_but_recheck_source(self):
        profile = object.__new__(PostgresInvestigatorProfile)
        profile.dsn = "unused"
        profile.source_id = "synthetic"
        profile._source_loader = None
        connection = MagicMock()
        profile._connection = connection
        connection.execute.return_value.fetchone.side_effect = [
            {"profile": {"version": 1}, "capture": {}, "knowledge": {}},
            {"profile": {"version": 2}, "capture": {}, "knowledge": {}},
        ]
        with patch(
            "trace_app.adapters.sources.postgres_investigator.connect"
        ) as connect:
            self.assertEqual(profile._package()["profile"]["version"], 1)
            self.assertEqual(profile._package()["profile"]["version"], 2)
            connect.assert_not_called()
            self.assertEqual(connection.execute.call_count, 2)

    def test_tool_package_is_loaded_once_per_call(self):
        connection = MagicMock()
        connection.execute.return_value.fetchone.side_effect = [
            {"profile": {"version": 1}, "capture": {}, "knowledge": {}},
            {"profile": {"version": 2}, "capture": {}, "knowledge": {}},
        ]
        profiles = []
        for _ in range(2):
            profile = object.__new__(PostgresInvestigatorProfile)
            profile.source_id = "synthetic"
            profile._source_loader = None
            profile._connection = connection
            profile._cache_package = True
            profile._cached_package = None
            profiles.append(profile)
        self.assertEqual(profiles[0]._package()["profile"]["version"], 1)
        self.assertEqual(profiles[0]._package()["profile"]["version"], 1)
        self.assertEqual(profiles[1]._package()["profile"]["version"], 2)
        self.assertEqual(connection.execute.call_count, 2)

    def test_evidence_and_knowledge_are_read_and_rechecked(self):
        with TemporaryDirectory() as temp:
            path = prepare(Path(temp) / "source")
            old, package, job, snapshot = synthetic_package(path)
            with patch.object(
                PostgresInvestigatorProfile, "_package", return_value=package
            ):
                new = PostgresInvestigatorProfile("unused", "synthetic", clock=Clock())
                self.assertEqual(
                    new.get_snapshot(
                        job.investigation_id, access_scope=old.evidence.access_scope
                    ),
                    snapshot,
                )
                self.assertEqual(new.source_content(), old.source_content())
                scope = ToolScope(
                    job.investigation_id, "test", new.evidence, new.knowledge
                )
                policy = ToolPolicy()
                call = ToolCall.parse(
                    "logs.query",
                    {
                        "window_start": snapshot.window_start,
                        "window_end": snapshot.window_end,
                    },
                    policy,
                )
                result = _read(
                    call,
                    scope,
                    None,
                    policy,
                    reader=new,
                    corpus_reader=new,
                    index_generation=new.index(),
                )
                self.assertIn(result.status, ("ok", "partial", "empty"))
                search = ToolCall.parse(
                    "knowledge.search",
                    {"query": "HTTP 504", "service": "payment"},
                    policy,
                )
                result = _read(
                    search,
                    scope,
                    None,
                    policy,
                    reader=new,
                    corpus_reader=new,
                    index_generation=new.index(),
                    at=datetime.fromtimestamp(Clock()(), UTC),
                )
                self.assertIn(result.status, ("ok", "partial"))
                authority = LocalEvidenceAuthority(new, new.scope("job-1"))
                identity = next(iter(new.source_content()))
                self.assertIsNotNone(authority.resolve(new.scope("job-1"), identity))
                package["profile"]["grants"].pop(identity)
                self.assertIsNone(authority.resolve(new.scope("job-1"), identity))


if __name__ == "__main__":
    unittest.main()
