"""Exercise token acquisition without connecting to an external database."""

import unittest
from unittest.mock import Mock, patch

from trace_app.adapters.storage.postgres import connection


class PostgresEntraTest(unittest.TestCase):
    dsn = "host=db.example user=trace dbname=trace sslmode=verify-full"

    def test_gets_a_token_for_each_connection(self):
        credential = Mock()
        credential.get_token.side_effect = [Mock(token="one"), Mock(token="two")]
        with (
            patch.dict("os.environ", {"TRACE_POSTGRES_AUTH": "entra"}),
            patch.object(connection, "_credential", return_value=credential),
            patch.object(connection.psycopg, "connect") as connect,
        ):
            connection.connect(self.dsn)
            connection.connect(self.dsn)
        self.assertEqual(
            [call.kwargs["password"] for call in connect.call_args_list], ["one", "two"]
        )
        credential.get_token.assert_called_with(connection.POSTGRES_SCOPE)

    def test_rejects_password_or_unverified_tls(self):
        with patch.dict("os.environ", {"TRACE_POSTGRES_AUTH": "entra"}):
            for dsn in (
                self.dsn + " password=unsafe",
                "host=db.example sslmode=require",
            ):
                with self.subTest(dsn=dsn), self.assertRaises(ValueError):
                    connection.connect(dsn)


if __name__ == "__main__":
    unittest.main()
