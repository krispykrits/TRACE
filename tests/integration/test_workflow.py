"""Real private SQLite/corpus/process reads with explicitly scripted model/reviews."""

from __future__ import annotations

import io
import json
import sqlite3
import unittest
from dataclasses import replace

from scripts.demo_integration import AT, integration_fixture
from scripts.demo_investigator import compose
from trace_app.adapters.storage.sqlite.corpus import SQLiteCorpusStore
from trace_app.adapters.storage.sqlite.investigations import SQLiteInvestigationStore
from trace_app.adapters.storage.sqlite.workflow import SQLiteWorkflowStore
from trace_app.investigation.assessment_context import AssessmentBoundaryError
from trace_app.investigation.models import (
    StoreAccessError,
    StoreInputError,
    StoreStateError,
)
from trace_app.investigation.provider import ModelErrorCode
from trace_app.investigation.workflow import WorkflowOptions
from trace_app.runtime.logging import configure_logging


class WorkflowIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stream = io.StringIO()
        configure_logging(stream=self.stream)

    def test_answerable_insufficient_and_pending_reports_persist_scoped_results(
        self,
    ) -> None:
        for case_id, abstained, reviewed in (
            ("c01", False, True),
            ("c04", True, True),
            ("c01", False, False),
        ):
            with (
                self.subTest(case=case_id, reviewed=reviewed),
                integration_fixture(case_id) as setup,
            ):
                workflow, model, _, _, _ = compose(
                    setup, abstained=abstained, reviewed=reviewed
                )
                self.addCleanup(workflow.close)
                result = workflow.run()
                self.assertIsNone(result.failure_code)
                self.assertEqual(
                    result.validation_outcome,
                    "accepted" if reviewed else "review_required",
                )
                data = result.read(workflow.scope)
                self.assertEqual(
                    data["assessment"]["report"]["assessment_status"],
                    "abstained" if abstained else "supported",
                )
                self.assertEqual(len(model.requests), 1)
                with SQLiteWorkflowStoreForTest(
                    setup.root / "evidence.sqlite3"
                ) as store:
                    saved = store.metadata(
                        workflow.scope.investigation_id,
                        access_scope=setup.scope.evidence.access_scope,
                    )
                    with self.assertRaises(StoreAccessError):
                        store.metadata(
                            workflow.scope.investigation_id, access_scope="wrong-scope"
                        )
                self.assertEqual(saved["execution_status"], "completed")
                self.assertEqual(
                    saved["assessment_status"],
                    "pending"
                    if not reviewed
                    else "abstained"
                    if abstained
                    else "supported",
                )
                self.assertEqual(
                    saved["artifacts"][-1]["configuration"]["mode"], "offline_test"
                )
                self.assertNotIn("synthetic_mechanism", json.dumps(saved))
                with sqlite3.connect(setup.root / "evidence.sqlite3") as connection:
                    private = connection.execute(
                        "SELECT role,sensitivity,body FROM workflow_artifacts WHERE role != 'untrusted_evidence'"
                    ).fetchone()
                    calls = [
                        json.loads(row[0])
                        for row in connection.execute(
                            "SELECT metadata FROM execution_calls"
                        )
                    ]
                self.assertEqual(
                    private[0], "accepted" if reviewed else "review_required"
                )
                self.assertEqual(private[1], data["sensitivity"])
                self.assertTrue(json.loads(private[2])["citations"])
                self.assertTrue(
                    all(
                        row["correlation_id"] == setup.scope.correlation_id
                        for row in calls
                    )
                )

    def test_timeout_keeps_evidence_without_publishing_report_and_blocks_restart_replay(
        self,
    ) -> None:
        with integration_fixture() as setup:
            workflow, model, _, _, _ = compose(setup)
            self.addCleanup(workflow.close)
            model.error = ModelErrorCode.TIMEOUT
            result = workflow.run()
            self.assertEqual(result.failure_code, "timeout")
            self.assertIsNotNone(result.read(workflow.scope)["evidence"])
            with SQLiteWorkflowStoreForTest(setup.root / "evidence.sqlite3") as store:
                state = store.metadata(
                    workflow.scope.investigation_id,
                    access_scope=setup.scope.evidence.access_scope,
                )
            self.assertEqual(state["execution_status"], "failed")
            self.assertEqual(state["assessment_status"], "pending")
            self.assertEqual(
                [a["role"] for a in state["artifacts"]], ["untrusted_evidence"]
            )
            workflow.run()
            self.assertEqual(len(model.requests), 1)

    def test_duplicate_submission_and_attempt_cannot_republish_or_repeat_paid_steps(
        self,
    ) -> None:
        with integration_fixture() as setup:
            workflow, model, _, _, _ = compose(setup, reviewed=True)
            self.addCleanup(workflow.close)
            result = workflow.run()
            with SQLiteInvestigationStore(setup.root / "evidence.sqlite3") as store:
                original = store.get_investigation(
                    workflow.scope.investigation_id,
                    access_scope=setup.scope.evidence.access_scope,
                )
                duplicate = store.submit(original.request, at=AT)
            self.assertEqual(duplicate.investigation_id, original.investigation_id)
            workflow.run()
            self.assertEqual(len(model.requests), 1)
            self.assertEqual(result.validation_outcome, "accepted")
            with sqlite3.connect(setup.root / "evidence.sqlite3") as connection:
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM workflow_artifacts WHERE role='accepted'"
                    ).fetchone()[0],
                    1,
                )

    def test_durable_cancellation_during_model_prevents_accepted_publication(
        self,
    ) -> None:
        with integration_fixture() as setup:
            workflow, model, _, _, _ = compose(setup, reviewed=True)
            self.addCleanup(workflow.close)

            def cancel():
                with SQLiteInvestigationStore(setup.root / "evidence.sqlite3") as store:
                    store.cancel(
                        workflow.scope.investigation_id,
                        access_scope=setup.scope.evidence.access_scope,
                        at=AT,
                    )

            model.after_call = cancel
            result = workflow.run()
            self.assertEqual(result.execution_status, "cancelled")
            self.assertEqual(result.failure_code, "cancelled")
            with sqlite3.connect(setup.root / "evidence.sqlite3") as connection:
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM workflow_artifacts WHERE role='accepted'"
                    ).fetchone()[0],
                    0,
                )
            self.assertEqual(len(model.requests), 1)

    def test_next_check_current_sources_and_history_are_readmitted(self) -> None:
        with integration_fixture() as setup:
            workflow, model, _, _, _ = compose(
                setup, options=WorkflowOptions(next_check=True)
            )
            self.addCleanup(workflow.close)

            def knowledge_check(value, request):
                value["next_check"] = {
                    "tool": "knowledge.search",
                    "arguments": {
                        "query": "downstream degradation timeout evidence",
                        "service": "payment",
                    },
                    "reason": "Read another authorized passage.",
                }

            model.transform = knowledge_check
            result = workflow.run()
            self.assertIsNone(result.failure_code)
            self.assertEqual(result.validation_outcome, "review_required")
            self.assertEqual(len(model.requests), 2)
            later = json.loads(model.requests[1].source_context)
            self.assertEqual(len(later["untrusted_history"]), 1)
            self.assertEqual(later["investigation_context"]["phase"], "after_check")
            self.assertTrue(result.read(workflow.scope)["assessment"]["citations"])

    def test_corpus_revocation_after_delivery_prevents_source_and_report_read(
        self,
    ) -> None:
        with integration_fixture() as setup:
            workflow, _, _, _, _ = compose(setup, reviewed=True)
            self.addCleanup(workflow.close)
            result = workflow.run()
            initial = result.read(workflow.scope)
            citation = next(
                iter(
                    initial["evidence"]["data"]["knowledge"]["context"]["data"][
                        "citations"
                    ].values()
                )
            )
            with SQLiteCorpusStore(setup.root / "corpus.sqlite3") as corpus:
                corpus.withdraw(
                    citation["metadata"]["document_id"], reason="revoked", at=AT
                )
            with self.assertRaises(AssessmentBoundaryError):
                result.read(workflow.scope)

    def test_schema_two_upgrade_preserves_jobs_and_execution_reservations(self) -> None:
        with integration_fixture() as setup:
            workflow, _, _, _, _ = compose(setup)
            workflow.close()
            with sqlite3.connect(setup.root / "evidence.sqlite3") as connection:
                previous = connection.execute(
                    "SELECT state FROM execution_runs"
                ).fetchone()[0]
                connection.execute("DROP TABLE workflow_artifacts")
                connection.execute("DROP TABLE workflow_runs")
                connection.execute("PRAGMA user_version=2")
            with SQLiteInvestigationStore(setup.root / "evidence.sqlite3") as store:
                job = store.get_investigation(
                    setup.scope.investigation_id,
                    access_scope=setup.scope.evidence.access_scope,
                )
            self.assertEqual(job.status, "running")
            with sqlite3.connect(setup.root / "evidence.sqlite3") as connection:
                self.assertEqual(
                    connection.execute("PRAGMA user_version").fetchone()[0], 3
                )
                self.assertEqual(
                    connection.execute("SELECT state FROM execution_runs").fetchone()[
                        0
                    ],
                    previous,
                )
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM workflow_artifacts"
                    ).fetchone()[0],
                    0,
                )

    def test_unissued_clone_and_stale_publication_are_rejected_atomically(self) -> None:
        with integration_fixture() as setup:
            workflow, _, _, _, _ = compose(setup, reviewed=True)
            self.addCleanup(workflow.close)
            result = workflow.run()
            publication = result._publication
            assert publication is not None
            store = workflow.store
            with self.assertRaises(StoreInputError):
                store.publish(replace(publication), at=AT)
            with self.assertRaises(StoreStateError):
                store.publish(publication, at=AT)
            with sqlite3.connect(setup.root / "evidence.sqlite3") as connection:
                self.assertEqual(
                    connection.execute(
                        "SELECT COUNT(*) FROM workflow_artifacts WHERE role='accepted'"
                    ).fetchone()[0],
                    1,
                )


class SQLiteWorkflowStoreForTest(SQLiteWorkflowStore):
    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
