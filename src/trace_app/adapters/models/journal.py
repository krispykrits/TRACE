"""Private SQLite provenance/audit and conservative local monthly reservations."""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from trace_app.investigation.provider import (
    ModelErrorCode,
    ModelProviderError,
    ModelUsage,
)
from trace_app.investigation.provider_policy import Redaction


@dataclass(frozen=True, slots=True)
class ModelPricing:
    """Versioned USD nanodollar estimates; cached input receives no discount."""

    version: str
    input_nusd_per_token: int
    output_nusd_per_token: int

    def __post_init__(self) -> None:
        if (
            not self.version
            or len(self.version) > 128
            or any(
                type(value) is not int or value <= 0
                for value in (self.input_nusd_per_token, self.output_nusd_per_token)
            )
        ):
            raise ModelProviderError(ModelErrorCode.CONFIGURATION)

    def estimate(self, input_tokens: int, output_tokens: int) -> int:
        return (
            input_tokens * self.input_nusd_per_token
            + output_tokens * self.output_nusd_per_token
        )


def _month(now: float) -> str:
    return datetime.fromtimestamp(now, timezone.utc).strftime("%Y-%m")


class SqliteProviderJournal:
    """All instances sharing this file reserve atomically; external spend is separate."""

    def __init__(
        self,
        path: Path,
        pricing: ModelPricing,
        *,
        monthly_limit_nusd: int,
        initial_spend_nusd: int,
        now: float,
    ) -> None:
        if (
            type(monthly_limit_nusd) is not int
            or not 0 < monthly_limit_nusd <= 20_000_000_000
            or type(initial_spend_nusd) is not int
            or not 0 <= initial_spend_nusd <= monthly_limit_nusd
        ):
            raise ModelProviderError(ModelErrorCode.CONFIGURATION)
        self._path = path
        self._pricing = pricing
        self._limit = monthly_limit_nusd
        try:
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
            try:
                if os.fstat(descriptor).st_mode & 0o077:
                    raise ValueError("Private journal required.")
            finally:
                os.close(descriptor)
            with self._connect() as connection:
                connection.executescript("""
                    CREATE TABLE IF NOT EXISTS configuration (
                        id INTEGER PRIMARY KEY CHECK (id=1),
                        limit_nusd INTEGER NOT NULL, pricing TEXT NOT NULL,
                        input_rate INTEGER NOT NULL, output_rate INTEGER NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS months (
                        month TEXT PRIMARY KEY, initial_nusd INTEGER NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS attempts (
                        request_id TEXT PRIMARY KEY, scope_id TEXT NOT NULL,
                        month TEXT NOT NULL, allowance_nusd INTEGER NOT NULL,
                        charged_nusd INTEGER NOT NULL, outcome TEXT NOT NULL,
                        metadata TEXT NOT NULL, dispatched INTEGER NOT NULL
                    );
                    CREATE TABLE IF NOT EXISTS redactions (
                        request_id TEXT NOT NULL REFERENCES attempts(request_id),
                        provenance TEXT NOT NULL
                    );
                """)
                connection.execute("BEGIN IMMEDIATE")
                expected = (
                    monthly_limit_nusd,
                    pricing.version,
                    pricing.input_nusd_per_token,
                    pricing.output_nusd_per_token,
                )
                connection.execute(
                    "INSERT OR IGNORE INTO configuration VALUES (1,?,?,?,?)", expected
                )
                actual = connection.execute(
                    "SELECT limit_nusd,pricing,input_rate,output_rate FROM configuration WHERE id=1"
                ).fetchone()
                if actual != expected:
                    raise ValueError("Journal configuration differs.")
                connection.execute(
                    "INSERT OR IGNORE INTO months VALUES (?,?)",
                    (_month(now), initial_spend_nusd),
                )
        except (OSError, sqlite3.Error, ValueError):
            raise ModelProviderError(ModelErrorCode.AUDIT) from None

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        if self._path.is_symlink() or self._path.stat().st_mode & 0o077:
            raise ModelProviderError(ModelErrorCode.AUDIT)
        connection = sqlite3.connect(self._path, timeout=5)
        try:
            connection.execute("PRAGMA foreign_keys=ON")
            with connection:
                yield connection
        finally:
            connection.close()

    def begin(
        self,
        metadata: dict[str, object],
        redactions: tuple[Redaction, ...],
        input_allowance: int,
        output_allowance: int,
        now: float,
    ) -> None:
        reservation = self._pricing.estimate(input_allowance, output_allowance)
        month = _month(now)
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                connection.execute(
                    "INSERT OR IGNORE INTO months VALUES (?,0)", (month,)
                )
                used = connection.execute(
                    "SELECT COALESCE(SUM(charged_nusd),0) FROM attempts WHERE month=?",
                    (month,),
                ).fetchone()[0]
                initial = connection.execute(
                    "SELECT initial_nusd FROM months WHERE month=?", (month,)
                ).fetchone()[0]
                uncertain = connection.execute(
                    "SELECT 1 FROM attempts WHERE scope_id=? AND (outcome='reserved' OR (dispatched=1 AND outcome IN (?, ?, ?))) LIMIT 1",
                    (
                        metadata["scope_id"],
                        ModelErrorCode.TIMEOUT.value,
                        ModelErrorCode.AUDIT.value,
                        ModelErrorCode.DEPENDENCY.value,
                    ),
                ).fetchone()
                if uncertain or used + initial + reservation > self._limit:
                    raise ModelProviderError(ModelErrorCode.BUDGET)
                connection.execute(
                    "INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)",
                    (
                        metadata["request_id"],
                        metadata["scope_id"],
                        month,
                        reservation,
                        reservation,
                        "reserved",
                        json.dumps(metadata, allow_nan=False),
                        0,
                    ),
                )
                connection.executemany(
                    "INSERT INTO redactions VALUES (?,?)",
                    [
                        (metadata["request_id"], json.dumps(row.to_dict()))
                        for row in redactions
                    ],
                )
        except ModelProviderError:
            raise
        except (OSError, sqlite3.Error, ValueError):
            raise ModelProviderError(ModelErrorCode.AUDIT) from None

    def finish(
        self,
        metadata: dict[str, object],
        usage: ModelUsage,
        dispatched: bool,
        now: float,
    ) -> None:
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                previous = connection.execute(
                    "SELECT allowance_nusd FROM attempts WHERE request_id=?",
                    (metadata["request_id"],),
                ).fetchone()
                estimate = None
                if (
                    dispatched
                    and usage.input_tokens is not None
                    and usage.output_tokens is not None
                ):
                    estimate = self._pricing.estimate(
                        usage.input_tokens, usage.output_tokens
                    )
                charge = (
                    (estimate if estimate is not None else previous[0])
                    if dispatched and previous
                    else 0
                )
                enriched = {
                    **metadata,
                    "pricing_version": self._pricing.version,
                    "currency": "USD",
                    "estimated_cost_nusd": estimate,
                    "reserved_or_estimated_charge_nusd": charge,
                }
                connection.execute(
                    """INSERT INTO attempts VALUES (?,?,?,?,?,?,?,?)
                       ON CONFLICT(request_id) DO UPDATE SET
                       charged_nusd=excluded.charged_nusd,outcome=excluded.outcome,
                       metadata=excluded.metadata,dispatched=excluded.dispatched""",
                    (
                        metadata["request_id"],
                        metadata["scope_id"],
                        _month(now),
                        previous[0] if previous else 0,
                        charge,
                        metadata["outcome"],
                        json.dumps(enriched, allow_nan=False),
                        int(dispatched),
                    ),
                )
        except (OSError, sqlite3.Error, ValueError):
            raise ModelProviderError(ModelErrorCode.AUDIT) from None
