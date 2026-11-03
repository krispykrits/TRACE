import threading
import unittest
from unittest.mock import Mock

from trace_app.adapters.tools.local import LoggingToolAudit
from trace_app.investigation.tools import ToolAudit
from trace_app.investigation.worker import InvestigationWorker


class WorkerLoggingTests(unittest.TestCase):
    def test_worker_logs_safe_failure_details(self) -> None:
        queue = Mock()
        queue.claim.return_value.investigation_id = "investigation-1"
        queue.claim.return_value.active_attempt_id = 2
        process = Mock(side_effect=ValueError("secret evidence"))
        worker = InvestigationWorker(queue, process, lease_seconds=30)
        with self.assertLogs("trace_app.worker", level="INFO") as captured:
            worker.run_once()
            stop = threading.Event()
            stop.set()
            worker.run(stop)
        output = "\n".join(captured.output)
        self.assertIn("worker_started", output)
        self.assertIn("job_started investigation_id=investigation-1", output)
        self.assertIn("failure_code=executor_failed error_type=ValueError", output)
        self.assertIn("Traceback (most recent call last)", output)
        self.assertIn('File "worker.py"', output)
        self.assertNotIn("secret evidence", output)

    def test_tool_log_contains_outcome_and_duration(self) -> None:
        audit = ToolAudit(
            "v1", "worker-investigation-1", "call-1", 1, "logs.query", 120.0, "timeout"
        )
        with self.assertLogs("trace_app.tools", level="INFO") as captured:
            LoggingToolAudit().emit(audit)
        self.assertIn(
            "tool=logs.query outcome=timeout duration_ms=120", captured.output[0]
        )


if __name__ == "__main__":
    unittest.main()
