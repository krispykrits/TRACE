"""Persistent investigation consumption with fail-closed attempt handling."""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from typing import Protocol

from trace_app.investigation.diagnostics import safe_traceback
from trace_app.investigation.models import Investigation, StoreStateError

_LOG = logging.getLogger("trace_app.worker")


class WorkQueue(Protocol):
    def claim(self, *, lease_seconds: int) -> Investigation | None: ...
    def fail(self, job: Investigation, *, failure_code: str) -> None: ...


class InvestigationWorker:
    """Run an explicitly composed investigation processor for each claimed job.

    The processor must atomically publish a terminal result using the active
    attempt. A return without publication is treated as a failure.
    """

    def __init__(
        self,
        queue: WorkQueue,
        process: Callable[[Investigation], None],
        *,
        lease_seconds: int,
        poll_seconds: float = 1.0,
    ) -> None:
        if type(lease_seconds) is not int or not 1 <= lease_seconds <= 3600:
            raise ValueError("Invalid lease duration.")
        if type(poll_seconds) not in (float, int) or not 0.1 <= poll_seconds <= 60:
            raise ValueError("Invalid poll interval.")
        self._queue, self._process = queue, process
        self._lease_seconds, self._poll_seconds = lease_seconds, float(poll_seconds)

    def run_once(self) -> bool:
        job = self._queue.claim(lease_seconds=self._lease_seconds)
        if job is None:
            return False
        _LOG.info(
            "job_started investigation_id=%s attempt=%s",
            job.investigation_id,
            job.active_attempt_id,
        )
        try:
            self._process(job)
        except Exception as error:
            failure = "executor_failed"
            _LOG.error(
                "job_failed investigation_id=%s failure_code=%s error_type=%s\n%s",
                job.investigation_id,
                failure,
                type(error).__name__,
                safe_traceback(error),
                extra={"event": "worker.job.failed"},
            )
        else:
            failure = "executor_incomplete"
        try:
            # A completed, cancelled or expired attempt cannot be overwritten.
            self._queue.fail(job, failure_code=failure)
            if failure == "executor_incomplete":
                _LOG.error(
                    "job_failed investigation_id=%s failure_code=%s",
                    job.investigation_id,
                    failure,
                )
        except StoreStateError:
            pass
        return True

    def run(self, stop: threading.Event) -> None:
        _LOG.info("worker_started")
        while not stop.is_set():
            if not self.run_once():
                stop.wait(self._poll_seconds)
