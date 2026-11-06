"""Shared, conservative PostgreSQL model-spending reservations."""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any

import psycopg
from psycopg.rows import dict_row

from trace_app.adapters.storage.postgres.connection import connect
from trace_app.investigation.provider import (
    ModelErrorCode,
    ModelPricing,
    ModelProviderError,
    ModelUsage,
)
from trace_app.investigation.provider_policy import Redaction


class PostgresModelJournal:
    """Require pre-provisioned budget/month records; never assume prior spend is zero."""

    def __init__(
        self, dsn: str, pricing: ModelPricing, *, monthly_limit_nusd: int
    ) -> None:
        if (
            not dsn
            or type(monthly_limit_nusd) is not int
            or not 0 < monthly_limit_nusd <= 20_000_000_000
        ):
            raise ModelProviderError(ModelErrorCode.CONFIGURATION)
        self._dsn, self._pricing, self._limit = dsn, pricing, monthly_limit_nusd

    @property
    def pricing(self) -> ModelPricing:
        return self._pricing

    @staticmethod
    def _budget_column(connection: Any) -> str:
        # Accept the old name during rollout; the migration renames it without
        # changing the values used for spending admission.
        rows = connection.execute(
            """SELECT attname FROM pg_attribute
                WHERE attrelid='trace_model_attempts'::regclass AND NOT attisdropped
                  AND attname IN ('budgeted_usd','budgeted_nusd','charged_nusd')"""
        ).fetchall()
        columns = {row["attname"] for row in rows}
        if "budgeted_usd" in columns:
            return "budgeted_usd"
        return "budgeted_nusd" if "budgeted_nusd" in columns else "charged_nusd"

    @staticmethod
    def _amount(value: int, column: str) -> int | Decimal:
        return (
            Decimal(value) / Decimal(1_000_000_000)
            if column.endswith("_usd")
            else value
        )

    @staticmethod
    def _nano(value: int | Decimal, column: str) -> int:
        return int(value * 1_000_000_000) if column.endswith("_usd") else int(value)

    def _budget(self, connection: Any) -> str:
        config = connection.execute(
            "SELECT * FROM trace_model_budget WHERE id=1 FOR UPDATE"
        ).fetchone()
        expected = (
            self._limit,
            self._pricing.version,
            self._pricing.input_nusd_per_token,
            self._pricing.output_nusd_per_token,
        )
        if (
            config is None
            or tuple(
                config[k]
                for k in ("limit_nusd", "pricing", "input_rate", "output_rate")
            )
            != expected
        ):
            raise ModelProviderError(ModelErrorCode.AUDIT)
        month = connection.execute(
            "SELECT to_char(clock_timestamp() AT TIME ZONE 'UTC', 'YYYY-MM') AS month"
        ).fetchone()["month"]
        if (
            connection.execute(
                "SELECT 1 FROM trace_model_months WHERE month=%s", (month,)
            ).fetchone()
            is None
        ):
            raise ModelProviderError(ModelErrorCode.AUDIT)
        return str(month)

    def begin(
        self,
        metadata: dict[str, object],
        redactions: tuple[Redaction, ...],
        input_allowance: int,
        output_allowance: int,
        now: float,
    ) -> None:
        try:
            reservation = self._pricing.estimate(input_allowance, output_allowance)
            with connect(
                self._dsn, row_factory=dict_row, connect_timeout=5
            ) as connection:
                month = self._budget(connection)
                budget_column = self._budget_column(connection)
                job = connection.execute(
                    """SELECT j.*, clock_timestamp() AS database_now FROM trace_jobs j
                    WHERE investigation_id=%s FOR UPDATE""",
                    (metadata["scope_id"],),
                ).fetchone()
                if (
                    job is None
                    or job["status"] != "running"
                    or job["active_attempt_id"] != metadata.get("attempt_id")
                    or job["lease_until"] is None
                    or job["lease_until"] <= job["database_now"]
                ):
                    raise ModelProviderError(ModelErrorCode.POLICY)
                grant = connection.execute(
                    """SELECT * FROM trace_principal_grants WHERE tenant_id=%s AND object_id=%s FOR SHARE""",
                    (job["submitted_tenant"], job["submitted_object"]),
                ).fetchone()
                if (
                    grant is None
                    or grant["access_scope"] != job["access_scope"]
                    or grant["environment"] != job["environment"]
                    or job["service"] not in grant["services"]
                    or "submit" not in grant["actions"]
                ):
                    raise ModelProviderError(ModelErrorCode.POLICY)
                initial_row = connection.execute(
                    "SELECT initial_nusd FROM trace_model_months WHERE month=%s",
                    (month,),
                ).fetchone()
                used_row = connection.execute(
                    f"SELECT COALESCE(SUM({budget_column}),0) AS used FROM trace_model_attempts WHERE month=%s",
                    (month,),
                ).fetchone()
                if initial_row is None or used_row is None:
                    raise ModelProviderError(ModelErrorCode.AUDIT)
                initial = initial_row["initial_nusd"]
                used = self._nano(used_row["used"], budget_column)
                uncertain = connection.execute(
                    """SELECT 1 FROM trace_model_attempts WHERE scope_id=%s AND
                    (outcome='reserved' OR (dispatched AND outcome IN (%s,%s,%s,%s,%s))) LIMIT 1""",
                    (
                        metadata["scope_id"],
                        ModelErrorCode.TIMEOUT.value,
                        ModelErrorCode.AUDIT.value,
                        ModelErrorCode.DEPENDENCY.value,
                        ModelErrorCode.CANCELLED.value,
                        ModelErrorCode.EXPIRED.value,
                    ),
                ).fetchone()
                if uncertain or used + initial + reservation > self._limit:
                    raise ModelProviderError(ModelErrorCode.BUDGET)
                connection.execute(
                    "INSERT INTO trace_model_attempts VALUES (%s,%s,%s,%s,%s,'reserved',%s,false)",
                    (
                        metadata["request_id"],
                        metadata["scope_id"],
                        month,
                        self._amount(reservation, budget_column),
                        self._amount(reservation, budget_column),
                        json.dumps(
                            {
                                **metadata,
                                "input_allowance": input_allowance,
                                "output_allowance": output_allowance,
                            },
                            allow_nan=False,
                        ),
                    ),
                )
                for redaction in redactions:
                    connection.execute(
                        "INSERT INTO trace_model_redactions VALUES (%s,%s)",
                        (
                            metadata["request_id"],
                            json.dumps(redaction.to_dict(), allow_nan=False),
                        ),
                    )
        except ModelProviderError:
            raise
        except (psycopg.Error, ValueError, KeyError, TypeError):
            raise ModelProviderError(ModelErrorCode.AUDIT) from None

    def finish(
        self,
        metadata: dict[str, object],
        usage: ModelUsage,
        dispatched: bool,
        now: float,
    ) -> None:
        try:
            with connect(
                self._dsn, row_factory=dict_row, connect_timeout=5
            ) as connection:
                month = self._budget(connection)
                budget_column = self._budget_column(connection)
                previous = connection.execute(
                    "SELECT * FROM trace_model_attempts WHERE request_id=%s FOR UPDATE",
                    (metadata["request_id"],),
                ).fetchone()
                if previous is None:
                    if dispatched:
                        raise ModelProviderError(ModelErrorCode.AUDIT)
                    connection.execute(
                        "INSERT INTO trace_model_attempts VALUES (%s,%s,%s,0,0,%s,%s,false)",
                        (
                            metadata["request_id"],
                            metadata["scope_id"],
                            month,
                            metadata["outcome"],
                            json.dumps(metadata, allow_nan=False),
                        ),
                    )
                    return
                if previous["scope_id"] != metadata["scope_id"]:
                    raise ModelProviderError(ModelErrorCode.AUDIT)
                previous_metadata = json.loads(previous["metadata"])
                was_dispatched = dispatched or previous["dispatched"]
                estimate = None
                if was_dispatched:
                    if (
                        usage.input_tokens is not None
                        and usage.output_tokens is not None
                    ):
                        estimate = self._pricing.estimate(
                            usage.input_tokens, usage.output_tokens
                        )
                        charge = estimate
                    else:
                        partial = self._pricing.estimate(
                            usage.input_tokens
                            if usage.input_tokens is not None
                            else previous_metadata["input_allowance"],
                            usage.output_tokens
                            if usage.output_tokens is not None
                            else previous_metadata["output_allowance"],
                        )
                        charge = max(
                            self._nano(previous[budget_column], budget_column),
                            self._nano(
                                previous[
                                    "allowance_usd"
                                    if budget_column.endswith("_usd")
                                    else "allowance_nusd"
                                ],
                                budget_column,
                            ),
                            partial,
                        )
                else:
                    charge = 0
                if previous["outcome"] != "reserved" and previous["dispatched"]:
                    charge = max(
                        charge, self._nano(previous[budget_column], budget_column)
                    )
                enriched = {
                    **previous_metadata,
                    **metadata,
                    "cost_kind": "estimate",
                    "pricing_version": self._pricing.version,
                    "currency": "USD",
                    "actual_billed_usd": None,
                    "estimated_cost_usd": None
                    if estimate is None
                    else f"{Decimal(estimate) / Decimal(1_000_000_000):.9f}",
                    "budgeted_usd": f"{Decimal(charge) / Decimal(1_000_000_000):.9f}",
                }
                for old_key in (
                    "estimated_cost_nusd",
                    "actual_billed_nusd",
                    "budgeted_nusd",
                ):
                    enriched.pop(old_key, None)
                if not budget_column.endswith("_usd"):
                    enriched["estimated_cost_nusd"] = estimate
                enriched.pop("reserved_or_estimated_charge_nusd", None)
                connection.execute(
                    f"""UPDATE trace_model_attempts SET {budget_column}=%s, outcome=%s, metadata=%s, dispatched=%s
                    WHERE request_id=%s""",
                    (
                        self._amount(charge, budget_column),
                        metadata["outcome"],
                        json.dumps(enriched, allow_nan=False),
                        was_dispatched,
                        metadata["request_id"],
                    ),
                )
        except ModelProviderError:
            raise
        except (psycopg.Error, ValueError, KeyError, TypeError):
            raise ModelProviderError(ModelErrorCode.AUDIT) from None
