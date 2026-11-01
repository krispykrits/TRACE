"""Verify real signatures, claims and signing-key scope without network access."""

from __future__ import annotations

import json
import time
import unittest
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa

from trace_app.adapters.auth.entra import AuthenticationError, EntraAuthenticator

TENANT = "00000000-0000-0000-0000-000000000001"
AUDIENCE = "00000000-0000-0000-0000-000000000002"
OBJECT = "00000000-0000-0000-0000-000000000003"
ISSUER = f"https://login.microsoftonline.com/{TENANT}/v2.0"


class EntraAuthTests(unittest.TestCase):
    private_key: rsa.RSAPrivateKey
    key: dict[str, Any]

    @classmethod
    def setUpClass(cls) -> None:
        cls.private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.key = json.loads(
            jwt.algorithms.RSAAlgorithm.to_jwk(cls.private_key.public_key())
        )
        cls.key.update(kid="key-1", use="sig", issuer=ISSUER)

    def test_delegated_token_and_invalid_claims(self) -> None:
        auth = EntraAuthenticator(
            TENANT, AUDIENCE, "investigate", fetch_keys=lambda _: {"keys": [self.key]}
        )
        now = int(time.time())
        claims: dict[str, Any] = {
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

        def token(values: dict[str, Any], key: Any = None) -> str:
            return jwt.encode(
                values,
                key or self.private_key,
                algorithm="RS256",
                headers={"kid": "key-1"},
            )

        self.assertEqual(auth.authenticate(token(claims)).object_id, OBJECT)
        for changed in (
            {"aud": "00000000-0000-0000-0000-000000000004"},
            {"tid": "00000000-0000-0000-0000-000000000004"},
            {"scp": "other"},
            {"oid": "not-a-uuid"},
            {"exp": now - 1},
        ):
            with self.subTest(changed=changed), self.assertRaises(AuthenticationError):
                auth.authenticate(token(claims | changed))
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        with self.assertRaises(AuthenticationError):
            auth.authenticate(token(claims, other_key))
        wrong_issuer = self.key | {"issuer": "https://wrong.example/v2.0"}
        wrong_auth = EntraAuthenticator(
            TENANT,
            AUDIENCE,
            "investigate",
            fetch_keys=lambda _: {"keys": [wrong_issuer]},
        )
        with self.assertRaises(AuthenticationError):
            wrong_auth.authenticate(token(claims))
