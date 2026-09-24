"""Deterministic tests for runtime configuration loading."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from trace_app.configuration import ConfigurationError, load_settings


class ConfigurationTests(unittest.TestCase):
    def _empty_env_file(self, directory: str) -> Path:
        env_file = Path(directory) / ".env"
        env_file.write_text("", encoding="utf-8")
        return env_file

    def test_precedence_is_cli_then_process_then_file_then_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                "TRACE_ENVIRONMENT=production\nTRACE_LOG_LEVEL=WARNING\n",
                encoding="utf-8",
            )
            settings = load_settings(
                environ={
                    "TRACE_ENVIRONMENT": "test",
                    "TRACE_LOG_LEVEL": "DEBUG",
                },
                dotenv_path=env_file,
                overrides={
                    "TRACE_ENVIRONMENT": "development",
                    "TRACE_LOG_LEVEL": "ERROR",
                },
            )

        self.assertEqual(settings.environment, "development")
        self.assertEqual(settings.log_level, "ERROR")

    def test_process_environment_overrides_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_file = Path(directory) / ".env"
            env_file.write_text(
                "TRACE_ENVIRONMENT=production\nTRACE_LOG_LEVEL=WARNING\n",
                encoding="utf-8",
            )
            settings = load_settings(
                environ={"TRACE_ENVIRONMENT": "test", "TRACE_LOG_LEVEL": "DEBUG"},
                dotenv_path=env_file,
            )

        self.assertEqual(settings.environment, "test")
        self.assertEqual(settings.log_level, "DEBUG")

    def test_log_level_defaults_to_info(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_file = self._empty_env_file(directory)
            env_file.write_text("TRACE_ENVIRONMENT=development\n", encoding="utf-8")
            settings = load_settings(environ={}, dotenv_path=env_file)

        self.assertEqual(settings.log_level, "INFO")

    def test_missing_required_environment_is_actionable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_file = self._empty_env_file(directory)
            with self.assertRaisesRegex(
                ConfigurationError, "Missing required TRACE_ENVIRONMENT"
            ):
                load_settings(environ={}, dotenv_path=env_file)

    def test_invalid_environment_does_not_echo_supplied_value(self) -> None:
        secret_fixture = "do-not-print-this-value"
        with tempfile.TemporaryDirectory() as directory:
            env_file = self._empty_env_file(directory)
            with self.assertRaises(ConfigurationError) as raised:
                load_settings(
                    environ={"TRACE_ENVIRONMENT": secret_fixture},
                    dotenv_path=env_file,
                )

        self.assertIn("Invalid TRACE_ENVIRONMENT", str(raised.exception))
        self.assertNotIn(secret_fixture, str(raised.exception))

    def test_invalid_log_level_fails_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            env_file = self._empty_env_file(directory)
            with self.assertRaisesRegex(
                ConfigurationError, "Invalid TRACE_LOG_LEVEL"
            ):
                load_settings(
                    environ={
                        "TRACE_ENVIRONMENT": "development",
                        "TRACE_LOG_LEVEL": "VERBOSE",
                    },
                    dotenv_path=env_file,
                )

    def test_selected_missing_file_fails_without_disclosing_path(self) -> None:
        with self.assertRaisesRegex(
            ConfigurationError, "selected configuration file cannot be found"
        ) as raised:
            load_settings(environ={}, dotenv_path="/private/dir/settings.env")

        self.assertNotIn("/private/dir", str(raised.exception))

    def test_unsupported_secret_setting_names_key_but_never_value(self) -> None:
        secret_fixture = "fixture-api-secret-value"
        with tempfile.TemporaryDirectory() as directory:
            env_file = self._empty_env_file(directory)
            with self.assertRaises(ConfigurationError) as raised:
                load_settings(
                    environ={
                        "TRACE_ENVIRONMENT": "development",
                        "TRACE_PROVIDER_API_KEY": secret_fixture,
                    },
                    dotenv_path=env_file,
                )

        self.assertIn("TRACE_PROVIDER_API_KEY", str(raised.exception))
        self.assertNotIn(secret_fixture, str(raised.exception))


if __name__ == "__main__":
    unittest.main()
