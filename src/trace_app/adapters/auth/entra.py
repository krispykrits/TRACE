"""Validate single-tenant Microsoft Entra delegated access tokens."""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Callable
from urllib.request import urlopen

import jwt


class AuthenticationError(PermissionError):
    """A bearer token could not be authenticated."""


@dataclass(frozen=True, slots=True)
class Principal:
    tenant_id: str
    object_id: str


class EntraAuthenticator:
    """Accept v2 delegated tokens for one configured tenant and API audience."""

    def __init__(
        self,
        tenant_id: str,
        audience: str,
        required_scope: str,
        *,
        fetch_keys: Callable[[str], Any] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.tenant_id = str(uuid.UUID(tenant_id))
        self.audience = str(uuid.UUID(audience))
        if not required_scope or len(required_scope.split()) != 1:
            raise ValueError("One delegated API scope is required.")
        self.required_scope = required_scope
        self.issuer = f"https://login.microsoftonline.com/{self.tenant_id}/v2.0"
        self._keys_url = (
            f"https://login.microsoftonline.com/{self.tenant_id}/discovery/v2.0/keys"
        )
        self._fetch_keys = fetch_keys or self._download_keys
        self._clock = clock
        self._expires = 0.0
        self._keys: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    @staticmethod
    def _download_keys(url: str) -> Any:
        with urlopen(url, timeout=5) as response:
            payload = response.read(1_000_001)
        if len(payload) > 1_000_000:
            raise ValueError("Key set is too large.")
        return json.loads(payload)

    def _signing_key(self, kid: str) -> jwt.PyJWK:
        with self._lock:
            if not self._keys or self._clock() >= self._expires:
                payload = self._fetch_keys(self._keys_url)
                keys = payload.get("keys") if isinstance(payload, dict) else None
                if not isinstance(keys, list) or not all(
                    isinstance(k, dict) for k in keys
                ):
                    raise AuthenticationError("Invalid signing keys.")
                self._keys = keys
                self._expires = self._clock() + 300
            matches = [k for k in self._keys if k.get("kid") == kid]
            if len(matches) != 1:
                # Do not perform an attacker-controlled fetch for every unknown key.
                raise AuthenticationError("Signing key is unavailable.")
            key = matches[0]
            key_issuer = key.get("issuer")
            if (
                not isinstance(key_issuer, str)
                or key_issuer.replace("{tenantid}", self.tenant_id) != self.issuer
            ):
                raise AuthenticationError("Signing key issuer is invalid.")
            if key.get("kty") != "RSA" or key.get("use") != "sig":
                raise AuthenticationError("Signing key type is invalid.")
            return jwt.PyJWK.from_dict(key, algorithm="RS256")

    def authenticate(self, token: str) -> Principal:
        try:
            if not isinstance(token, str) or not 0 < len(token) <= 16_384:
                raise AuthenticationError("Invalid access token.")
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")
            if header.get("alg") != "RS256" or not isinstance(kid, str) or not kid:
                raise AuthenticationError("Invalid access token.")
            key = self._signing_key(kid)
            claims = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={
                    "require": [
                        "exp",
                        "iat",
                        "nbf",
                        "iss",
                        "aud",
                        "tid",
                        "oid",
                        "scp",
                        "ver",
                    ]
                },
            )
            if claims["tid"] != self.tenant_id or claims["ver"] != "2.0":
                raise AuthenticationError("Invalid access token.")
            scopes = claims["scp"]
            if not isinstance(scopes, str) or self.required_scope not in scopes.split():
                raise AuthenticationError("Invalid access token.")
            return Principal(self.tenant_id, str(uuid.UUID(claims["oid"])))
        except Exception as error:
            raise AuthenticationError("Authentication failed.") from error
