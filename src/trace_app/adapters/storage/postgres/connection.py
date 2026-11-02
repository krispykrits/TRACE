"""Open PostgreSQL connections with a fresh Entra access token when configured."""

import os
from functools import lru_cache
from typing import Any

import psycopg
from psycopg.conninfo import conninfo_to_dict

POSTGRES_SCOPE = "https://ossrdbms-aad.database.windows.net/.default"


@lru_cache(maxsize=1)
def _credential() -> Any:
    from azure.identity import DefaultAzureCredential

    return DefaultAzureCredential()


def connect(dsn: str, **kwargs: Any) -> Any:
    mode = os.environ.get("TRACE_POSTGRES_AUTH", "password")
    if mode == "entra":
        settings = conninfo_to_dict(dsn)
        if settings.get("sslmode") != "verify-full" or not settings.get("host"):
            raise ValueError(
                "Entra PostgreSQL requires a hostname and sslmode=verify-full."
            )
        if "password" in settings:
            raise ValueError(
                "A password must not be included with Entra PostgreSQL authentication."
            )
        try:
            token = _credential().get_token(POSTGRES_SCOPE).token
        except Exception as error:
            raise psycopg.OperationalError(
                "PostgreSQL authentication is unavailable."
            ) from error
        return psycopg.connect(dsn, password=token, **kwargs)
    if mode != "password":
        raise ValueError("Unsupported PostgreSQL authentication mode.")
    return psycopg.connect(dsn, **kwargs)
