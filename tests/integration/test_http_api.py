"""Exercise HTTP authorization and persistence with real signed tokens."""

from __future__ import annotations

import json
import tempfile
import time
import unittest
from datetime import datetime
from pathlib import Path
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from trace_app.adapters.auth.entra import EntraAuthenticator
from trace_app.adapters.http.api import create_app
from trace_app.adapters.storage.sqlite.investigations import SQLiteInvestigationStore
from trace_app.investigation.models import Investigation, InvestigationRequest
from trace_app.investigation.submission import (
    InvestigationGrant,
    InvestigationSubmission,
)

TENANT = "00000000-0000-0000-0000-000000000001"
AUDIENCE = "00000000-0000-0000-0000-000000000002"
OBJECT = "00000000-0000-0000-0000-000000000003"
ISSUER = f"https://login.microsoftonline.com/{TENANT}/v2.0"


class PerRequestSQLite:
    def __init__(self, path: Path) -> None:
        self.path = path

    def submit(self, request: InvestigationRequest, *, at: datetime) -> Investigation:
        with SQLiteInvestigationStore(self.path) as store:
            return store.submit(request, at=at)

    def get_investigation(
        self, investigation_id: str, *, access_scope: str
    ) -> Investigation:
        with SQLiteInvestigationStore(self.path) as store:
            return store.get_investigation(investigation_id, access_scope=access_scope)

    def cancel(
        self, investigation_id: str, *, access_scope: str, at: datetime
    ) -> Investigation:
        with SQLiteInvestigationStore(self.path) as store:
            return store.cancel(investigation_id, access_scope=access_scope, at=at)


class Grants:
    grant = InvestigationGrant(
        "scope:a",
        "test",
        frozenset({"orders"}),
        frozenset({"submit", "read", "cancel"}),
    )

    def grant_for(self, tenant_id: str, object_id: str) -> InvestigationGrant:
        return self.grant


class HTTPAPITests(unittest.TestCase):
    def test_authentication_authorization_and_lifecycle(self) -> None:
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        key: dict[str, Any] = json.loads(
            jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key())
        )
        key.update(kid="key-1", use="sig", issuer=ISSUER)
        auth = EntraAuthenticator(
            TENANT, AUDIENCE, "investigate", fetch_keys=lambda _: {"keys": [key]}
        )
        now = int(time.time())
        claims = {
            "iss": ISSUER,
            "aud": AUDIENCE,
            "tid": TENANT,
            "oid": OBJECT,
            "ver": "2.0",
            "scp": "investigate",
            "iat": now,
            "nbf": now - 1,
            "exp": now + 60,
        }
        token = jwt.encode(
            claims, private_key, algorithm="RS256", headers={"kid": "key-1"}
        )
        headers = {"Authorization": f"Bearer {token}"}
        request = {
            "submission_key": "key",
            "service": "orders",
            "environment": "test",
            "window_start": "2026-01-01T00:00:00Z",
            "window_end": "2026-01-01T00:01:00Z",
        }
        with tempfile.TemporaryDirectory() as directory:
            grants = Grants()
            app = create_app(
                InvestigationSubmission(
                    PerRequestSQLite(Path(directory) / "jobs.sqlite")
                ),
                auth,
                grants,
            )
            with TestClient(app) as client:
                self.assertEqual(
                    client.post("/investigations", json=request).status_code, 401
                )
                self.assertEqual(
                    client.post(
                        "/investigations",
                        json=request,
                        headers={"Authorization": "Bearer invalid"},
                    ).status_code,
                    401,
                )
                submitted = client.post(
                    "/investigations", json=request, headers=headers
                )
                self.assertEqual(submitted.status_code, 202)
                job_id = submitted.json()["investigation_id"]
                self.assertEqual(
                    client.post(
                        "/investigations", json=request, headers=headers
                    ).json()["investigation_id"],
                    job_id,
                )
                self.assertEqual(
                    client.get(
                        f"/investigations/{job_id}", headers=headers
                    ).status_code,
                    200,
                )
                grants.grant = InvestigationGrant(
                    "scope:a", "test", frozenset({"orders"}), frozenset({"read"})
                )
                self.assertEqual(
                    client.post(
                        f"/investigations/{job_id}/cancel", headers=headers
                    ).status_code,
                    404,
                )
                grants.grant = InvestigationGrant(
                    "scope:a",
                    "test",
                    frozenset({"orders"}),
                    frozenset({"read", "cancel"}),
                )
                self.assertEqual(
                    client.post(
                        f"/investigations/{job_id}/cancel", headers=headers
                    ).json()["status"],
                    "cancelled",
                )
                grants.grant = InvestigationGrant(
                    "scope:other", "test", frozenset({"orders"}), frozenset({"read"})
                )
                self.assertEqual(
                    client.get(
                        f"/investigations/{job_id}", headers=headers
                    ).status_code,
                    404,
                )
