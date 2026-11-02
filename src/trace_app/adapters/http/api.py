"""Authenticated HTTP operations for asynchronous investigation jobs."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Callable, Protocol

from fastapi import Depends, FastAPI, Header, HTTPException
from psycopg.conninfo import conninfo_to_dict
from pydantic import BaseModel, ConfigDict, Field

from trace_app.adapters.auth.entra import (
    AuthenticationError,
    EntraAuthenticator,
    Principal,
)
from trace_app.adapters.storage.postgres.jobs import PostgresJobs
from trace_app.investigation.assessment_context import AssessmentBoundaryError
from trace_app.investigation.models import (
    Investigation,
    StoreAccessError,
    StoreConflictError,
    StoreDependencyError,
    StoreInputError,
    StoreStateError,
)
from trace_app.investigation.provider import ModelProviderError
from trace_app.investigation.submission import (
    InvestigationGrant,
    InvestigationSubmission,
)


class Authenticator(Protocol):
    def authenticate(self, token: str) -> Principal: ...


class GrantReader(Protocol):
    def grant_for(self, tenant_id: str, object_id: str) -> InvestigationGrant: ...


class SubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    submission_key: str = Field(min_length=1, max_length=128)
    service: str = Field(min_length=1, max_length=128)
    environment: str = Field(min_length=1, max_length=128)
    window_start: str = Field(min_length=1, max_length=64)
    window_end: str = Field(min_length=1, max_length=64)


@dataclass(frozen=True, slots=True)
class APIContext:
    principal: Principal
    grant: InvestigationGrant


def _response(job: Investigation) -> dict[str, object]:
    return {
        "investigation_id": job.investigation_id,
        "status": job.status,
        "assessment_status": job.assessment_status,
        "service": job.request.service,
        "environment": job.request.environment,
        "window_start": job.request.window_start,
        "window_end": job.request.window_end,
        "created_at": job.created_at,
        "finished_at": job.finished_at,
        "failure_code": job.failure_code,
    }


def create_app(
    submission_for: Callable[[Principal], InvestigationSubmission],
    authenticator: Authenticator,
    grants: GrantReader,
    report_for: Callable[[Principal, str, str], object] | None = None,
) -> FastAPI:
    app = FastAPI(title="TRACE API", docs_url=None, redoc_url=None, openapi_url=None)

    def current_context(
        authorization: Annotated[str | None, Header()] = None,
    ) -> APIContext:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                401, "Authentication required.", headers={"WWW-Authenticate": "Bearer"}
            )
        try:
            principal = authenticator.authenticate(authorization[7:])
        except AuthenticationError:
            raise HTTPException(
                401, "Authentication required.", headers={"WWW-Authenticate": "Bearer"}
            ) from None
        try:
            return APIContext(
                principal, grants.grant_for(principal.tenant_id, principal.object_id)
            )
        except StoreAccessError:
            raise HTTPException(403, "Access denied.") from None
        except StoreDependencyError:
            raise HTTPException(503, "Service unavailable.") from None

    @app.get("/healthz")
    def health() -> dict[str, str]:
        return {"status": "alive"}

    @app.post("/investigations", status_code=202)
    def submit(
        body: SubmitRequest, context: APIContext = Depends(current_context)
    ) -> dict[str, object]:
        try:
            job = submission_for(context.principal).submit(
                context.grant, **body.model_dump(), at=datetime.now(UTC)
            )
            return _response(job)
        except StoreAccessError:
            raise HTTPException(403, "Access denied.") from None
        except StoreConflictError:
            raise HTTPException(409, "Submission key conflict.") from None
        except StoreInputError:
            raise HTTPException(400, "Invalid investigation request.") from None
        except StoreDependencyError:
            raise HTTPException(503, "Service unavailable.") from None

    @app.get("/investigations/{investigation_id}")
    def read(
        investigation_id: str, context: APIContext = Depends(current_context)
    ) -> dict[str, object]:
        try:
            return _response(
                submission_for(context.principal).read(context.grant, investigation_id)
            )
        except (StoreAccessError, StoreInputError):
            raise HTTPException(404, "Investigation not found.") from None
        except StoreDependencyError:
            raise HTTPException(503, "Service unavailable.") from None

    @app.post("/investigations/{investigation_id}/cancel")
    def cancel(
        investigation_id: str, context: APIContext = Depends(current_context)
    ) -> dict[str, object]:
        try:
            return _response(
                submission_for(context.principal).cancel(
                    context.grant, investigation_id, at=datetime.now(UTC)
                )
            )
        except (StoreAccessError, StoreInputError):
            raise HTTPException(404, "Investigation not found.") from None
        except StoreStateError:
            raise HTTPException(409, "Investigation cannot be cancelled.") from None
        except StoreDependencyError:
            raise HTTPException(503, "Service unavailable.") from None

    @app.get("/investigations/{investigation_id}/report")
    def report(
        investigation_id: str, context: APIContext = Depends(current_context)
    ) -> dict[str, object]:
        try:
            submission_for(context.principal).read(context.grant, investigation_id)
            if report_for is None:
                raise StoreDependencyError("Report source is unavailable.")
            reader = report_for(
                context.principal, investigation_id, context.grant.access_scope
            )
            return reader.read()  # type: ignore[no-any-return,attr-defined]
        except (
            StoreAccessError,
            StoreInputError,
            AssessmentBoundaryError,
            ModelProviderError,
        ):
            raise HTTPException(404, "Investigation not found.") from None
        except (StoreDependencyError, OSError):
            raise HTTPException(503, "Service unavailable.") from None

    return app


def app_factory() -> FastAPI:
    """Compose the service with operator-provided Entra and PostgreSQL settings."""
    from pathlib import Path

    from trace_app.adapters.hosted import report_access
    from trace_app.adapters.sources.local_investigator import LocalInvestigatorProfile

    if os.environ.get("TRACE_POSTGRES_AUTH") != "entra":
        raise ValueError("Hosted PostgreSQL requires Entra authentication.")
    dsn = os.environ["TRACE_POSTGRES_DSN"]
    settings = conninfo_to_dict(dsn)
    if settings.get("sslmode") != "verify-full" or not settings.get("host"):
        raise ValueError("PostgreSQL must use a hostname and sslmode=verify-full.")
    store = PostgresJobs(dsn)
    profile = LocalInvestigatorProfile(Path(os.environ["TRACE_SOURCE_PROFILE"]))
    auth = EntraAuthenticator(
        os.environ["TRACE_ENTRA_TENANT_ID"],
        os.environ["TRACE_ENTRA_API_CLIENT_ID"],
        os.environ["TRACE_ENTRA_DELEGATED_SCOPE"],
    )
    return create_app(
        lambda principal: InvestigationSubmission(
            PostgresJobs(dsn, principal=(principal.tenant_id, principal.object_id))
        ),
        auth,
        store,
        lambda principal, job_id, access_scope: report_access(
            dsn,
            profile,
            (principal.tenant_id, principal.object_id),
            job_id,
            access_scope,
        ),
    )
