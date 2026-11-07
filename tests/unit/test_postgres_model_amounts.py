"""Exact conversion for PostgreSQL model budget amounts."""

import unittest
from decimal import Decimal
from unittest.mock import MagicMock

from trace_app.adapters.storage.postgres.model_journal import PostgresModelJournal


class ModelAmountTests(unittest.TestCase):
    def test_usd_round_trip_preserves_nine_decimal_places(self):
        self.assertEqual(
            PostgresModelJournal._amount(3_798_000, "budgeted_usd"),
            Decimal("0.003798000"),
        )
        self.assertEqual(
            PostgresModelJournal._nano(Decimal("0.003798000"), "budgeted_usd"),
            3_798_000,
        )
        self.assertEqual(
            PostgresModelJournal._amount(3_798_000, "budgeted_nusd"), 3_798_000
        )

    def test_column_selection_supports_both_migrations(self):
        connection = MagicMock()
        for column in ("budgeted_usd", "budgeted_nusd", "charged_nusd"):
            connection.execute.return_value.fetchall.return_value = [
                {"attname": column}
            ]
            self.assertEqual(PostgresModelJournal._budget_column(connection), column)


if __name__ == "__main__":
    unittest.main()
