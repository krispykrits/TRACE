"""Investigation submission and lifecycle operations for an authenticated caller.

Authentication and the durable store are supplied by the hosting application.
This module does not authenticate identities or execute investigations.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from trace_app.evidence.models import _parse_utc
from trace_app.investigation.models import (
    Investigation,
    InvestigationRequest,
    StoreAccessError,
    StoreInputError,
)


@dataclass(frozen=True, slots=True)
class InvestigationGrant:
    """Scope supplied by the trusted authentication and authorization boundary."""

    access_scope: str
    environment: str
    services: frozenset[str]
    actions: frozenset[str]


class InvestigationStore(Protocol):
    def submit(
        self, request: InvestigationRequest, *, at: datetime
    ) -> Investigation: ...
    def get_investigation(
        self, investigation_id: str, *, access_scope: str
    ) -> Investigation: ...
    def cancel(
        self, investigation_id: str, *, access_scope: str, at: datetime
    ) -> Investigation: ...


class InvestigationSubmission:
    """Submit, inspect and cancel jobs without running provider or source code."""

    def __init__(self, store: InvestigationStore) -> None:
        self._store = store

    @staticmethod
    def _authorize(
        grant: InvestigationGrant, service: str, environment: str, action: str
    ) -> None:
        if (
            action not in grant.actions
            or environment != grant.environment
            or service not in grant.services
        ):
            raise StoreAccessError("Investigation is not accessible.")

    def submit(
        self,
        grant: InvestigationGrant,
        *,
        submission_key: str,
        service: str,
        environment: str,
        window_start: str,
        window_end: str,
        at: datetime,
    ) -> Investigation:
        self._authorize(grant, service, environment, "submit")
        request = InvestigationRequest(
            submission_key=submission_key,
            service=service,
            environment=environment,
            access_scope=grant.access_scope,
            window_start=window_start,
            window_end=window_end,
            max_attempts=1,
        )
        if _parse_utc(window_end) - _parse_utc(window_start) > timedelta(hours=24):
            raise StoreInputError("Investigation window exceeds 24 hours.")
        return self._store.submit(request, at=at)

    def read(self, grant: InvestigationGrant, investigation_id: str) -> Investigation:
        return self._load(grant, investigation_id, "read")

    def _load(
        self, grant: InvestigationGrant, investigation_id: str, action: str
    ) -> Investigation:
        if action not in grant.actions:
            raise StoreAccessError("Investigation is not accessible.")
        job = self._store.get_investigation(
            investigation_id, access_scope=grant.access_scope
        )
        self._authorize(grant, job.request.service, job.request.environment, action)
        return job

    def cancel(
        self, grant: InvestigationGrant, investigation_id: str, *, at: datetime
    ) -> Investigation:
        self._load(grant, investigation_id, "cancel")
        return self._store.cancel(
            investigation_id, access_scope=grant.access_scope, at=at
        )
