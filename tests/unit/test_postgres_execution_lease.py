"""Check attempt lease initialization without a live database."""

import unittest
from contextlib import nullcontext
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from trace_app.adapters.storage.postgres.execution import PostgresExecutionLedger
from trace_app.investigation.execution import (
    ExecutionIdentity,
    ExecutionPolicy,
    ExecutionRejected,
)


class LeaseTest(unittest.TestCase):
    def test_execution_extends_only_a_live_attempt(self):
        now = datetime.now(UTC)
        identity = ExecutionIdentity("job", 1, "correlation", "scope")
        policy = ExecutionPolicy()
        for expired in (False, True):
            with self.subTest(expired=expired):
                connection = MagicMock()
                job = {
                    "status": "running",
                    "active_attempt_id": 1,
                    "lease_until": now + timedelta(seconds=-1 if expired else 1),
                    "created_at": now,
                    "database_now": now,
                    "submitted_tenant": "tenant",
                    "submitted_object": "user",
                    "access_scope": "scope",
                    "service": "order",
                    "environment": "test",
                }
                grant = {
                    "access_scope": "scope",
                    "environment": "test",
                    "services": ["order"],
                    "actions": ["submit"],
                }
                responses = [job, grant, None]
                if not expired:
                    responses.append({"lease_until": now + timedelta(seconds=130)})
                connection.execute.return_value.fetchone.side_effect = responses
                ledger = PostgresExecutionLedger("unused")
                with patch.object(
                    ledger, "_transaction", return_value=nullcontext(connection)
                ):
                    if expired:
                        with self.assertRaises(ExecutionRejected):
                            ledger.apply(
                                identity, policy, now.timestamp(), lambda _: None
                            )
                        self.assertEqual(connection.execute.call_count, 3)
                    else:
                        ledger.apply(identity, policy, now.timestamp(), lambda _: None)
                        statements = [
                            call.args[0] for call in connection.execute.call_args_list
                        ]
                        self.assertTrue(
                            any(
                                "UPDATE trace_jobs SET lease_until" in s
                                for s in statements
                            )
                        )
                        self.assertTrue(
                            any(
                                "UPDATE trace_job_attempts SET lease_until" in s
                                for s in statements
                            )
                        )


if __name__ == "__main__":
    unittest.main()
