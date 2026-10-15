"""Local investigator application commands with explicit trusted composition."""

from __future__ import annotations

import hashlib
import json
import time
from datetime import UTC, datetime, timedelta
from typing import Any, Callable, Protocol

from trace_app.evidence.models import _parse_utc, format_utc
from trace_app.evidence.queries import TrustedQueryContext
from trace_app.investigation.assessment_context import AssessmentBoundaryError
from trace_app.investigation.models import (
    EvidenceSnapshot,
    Investigation,
    InvestigationRequest,
    StoreStateError,
)
from trace_app.investigation.reports import ReportAccess
from trace_app.investigation.workflow import BoundedInvestigation


class LocalJobs(Protocol):
    def submit(
        self, request: InvestigationRequest, *, at: datetime
    ) -> Investigation: ...
    def get_investigation(
        self, investigation_id: str, *, access_scope: str
    ) -> Investigation: ...
    def ingest_snapshot(
        self,
        investigation_id: str,
        snapshot: EvidenceSnapshot,
        *,
        access_scope: str,
        at: datetime,
    ) -> int: ...
    def claim_next(
        self,
        *,
        at: datetime,
        lease_seconds: int,
        investigation_id: str,
        access_scope: str,
    ) -> Investigation | None: ...
    def cancel(
        self, investigation_id: str, *, access_scope: str, at: datetime
    ) -> Investigation: ...
    def close(self) -> None: ...


class LocalInvestigator:
    def __init__(
        self,
        jobs: LocalJobs,
        context: TrustedQueryContext,
        snapshot: Callable[[], EvidenceSnapshot],
        workflow: Callable[[Investigation, str], BoundedInvestigation],
        reports: Callable[[str], ReportAccess],
        check_job: Callable[[Investigation], None],
        *,
        clock: Callable[[], float] = time.time,
        lease_seconds: int = 120,
        allowed_providers: tuple[str, ...] = ("azure", "evidence-only"),
    ) -> None:
        self.jobs, self.context, self.snapshot = jobs, context, snapshot
        self.workflow, self.reports, self.check_job = workflow, reports, check_job
        self.clock, self.lease_seconds = clock, lease_seconds
        self.allowed_providers = allowed_providers

    def close(self) -> None:
        self.jobs.close()

    def read(self, investigation_id: str, **options: Any) -> dict[str, Any]:
        job = self.jobs.get_investigation(
            investigation_id, access_scope=self.context.access_scope
        )
        self.check_job(job)
        return self.reports(investigation_id).read(**options)

    def cancel(self, investigation_id: str) -> dict[str, Any]:
        job = self.jobs.get_investigation(
            investigation_id, access_scope=self.context.access_scope
        )
        self.check_job(job)
        self.jobs.cancel(
            investigation_id,
            access_scope=self.context.access_scope,
            at=datetime.fromtimestamp(self.clock(), UTC),
        )
        return self.read(investigation_id)

    def investigate(
        self,
        *,
        service: str,
        environment: str,
        window_start: str,
        window_end: str,
        provider: str,
    ) -> dict[str, Any]:
        if provider not in self.allowed_providers:
            raise ValueError("Selected provider is unavailable in this composition.")
        start, end = _parse_utc(window_start), _parse_utc(window_end)
        if (
            start > end
            or end - start > timedelta(hours=24)
            or environment not in ("development", "test")
        ):
            raise ValueError("Invalid investigation window or environment.")
        request_values = {
            "service": service,
            "environment": environment,
            "window_start": format_utc(start),
            "window_end": format_utc(end),
        }
        # Stable across processes/provider choices: changing a provider cannot replay a paid job.
        submission_key = (
            "cli-"
            + hashlib.sha256(
                json.dumps(request_values, sort_keys=True).encode()
            ).hexdigest()
        )
        request = InvestigationRequest(
            submission_key,
            service,
            environment,
            self.context.access_scope,
            request_values["window_start"],
            request_values["window_end"],
            max_attempts=1,
        )
        if (
            environment != self.context.environment
            or service not in self.context.allowed_services
        ):
            raise AssessmentBoundaryError("access_denied")
        source = self.snapshot()
        if start < _parse_utc(source.window_start) or end > _parse_utc(
            source.window_end
        ):
            raise ValueError("Window is outside the configured source capture.")
        at = datetime.fromtimestamp(self.clock(), UTC)
        job = self.jobs.submit(request, at=at)
        self.check_job(job)
        if job.attempt_count or job.status != "queued":
            return self.read(job.investigation_id)
        snapshot = EvidenceSnapshot(
            tuple(
                e
                for e in source.entries
                if start <= _parse_utc(e.record.observed_at) <= end
                and e.record.service in self.context.allowed_services
                and e.record.environment == environment
            ),
            request.window_start,
            request.window_end,
            source.sources,
        )
        self.jobs.ingest_snapshot(
            job.investigation_id,
            snapshot,
            access_scope=self.context.access_scope,
            at=at,
        )
        claimed = self.jobs.claim_next(
            at=at,
            lease_seconds=self.lease_seconds,
            investigation_id=job.investigation_id,
            access_scope=self.context.access_scope,
        )
        if claimed is None:
            raise StoreStateError("Investigation is already claimed.")
        try:
            workflow = self.workflow(claimed, provider)
        except BaseException:
            self.jobs.cancel(
                job.investigation_id,
                access_scope=self.context.access_scope,
                at=datetime.fromtimestamp(self.clock(), UTC),
            )
            raise
        try:
            workflow.run()
        finally:
            workflow.close()
        return self.read(job.investigation_id)
