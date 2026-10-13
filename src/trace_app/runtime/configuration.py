"""Validated runtime configuration for the TRACE CLI."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

_ENVIRONMENT_NAMES = frozenset({"development", "test", "production"})
_LOG_LEVELS = frozenset({"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"})
_SUPPORTED_KEYS = frozenset({"TRACE_ENVIRONMENT", "TRACE_LOG_LEVEL", "TRACE_ENV_FILE"})
_DOTENV_KEY = re.compile(r"^[A-Z_][A-Z0-9_]*$")


class ConfigurationError(ValueError):
    """Raised when configuration cannot be read or validated safely."""


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated settings used by the current CLI foundation."""

    environment: str
    log_level: str


def _parse_env_file(contents: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(contents.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, raw_value = line.partition("=")
        key = key.strip()
        if not separator or not _DOTENV_KEY.fullmatch(key):
            raise ConfigurationError(
                f"Invalid .env entry on line {line_number}; expected KEY=VALUE."
            )
        if key in values:
            raise ConfigurationError(
                f"Duplicate configuration variable {key} on line {line_number}."
            )
        value = raw_value.strip()
        if value.startswith(("'", '"')):
            quote = value[0]
            if len(value) < 2 or value[-1] != quote:
                raise ConfigurationError(
                    f"Invalid quoted value for {key} on line {line_number}."
                )
            value = value[1:-1]
        values[key] = value
    return values


def _read_env_file(path: Path, *, required: bool) -> dict[str, str]:
    try:
        contents = path.read_text(encoding="utf-8")
    except FileNotFoundError as error:
        if required:
            raise ConfigurationError(
                "The selected configuration file cannot be found."
            ) from error
        return {}
    except (OSError, UnicodeError) as error:
        raise ConfigurationError(
            "The selected configuration file cannot be read as UTF-8."
        ) from error
    return _parse_env_file(contents)


def load_settings(
    *,
    environ: Mapping[str, str] | None = None,
    dotenv_path: Path | str | None = None,
    overrides: Mapping[str, str] | None = None,
) -> Settings:
    """Load settings with CLI overrides, process environment, .env, then defaults.

    A missing default .env is allowed. A path selected explicitly with
    dotenv_path or TRACE_ENV_FILE must exist and be readable.
    """
    process_environment = dict(os.environ if environ is None else environ)
    explicit_path = dotenv_path is not None or bool(
        process_environment.get("TRACE_ENV_FILE")
    )
    selected_path = (
        Path(dotenv_path)
        if dotenv_path is not None
        else Path(process_environment.get("TRACE_ENV_FILE") or ".env")
    )
    file_values = _read_env_file(selected_path, required=explicit_path)
    command_overrides = dict(overrides or {})

    for source in (file_values, process_environment, command_overrides):
        for key in source:
            if key.startswith("TRACE_") and key not in _SUPPORTED_KEYS:
                raise ConfigurationError(
                    f"Unsupported configuration variable {key}; remove it or use a documented setting."
                )
    if "TRACE_ENV_FILE" in file_values:
        raise ConfigurationError(
            "TRACE_ENV_FILE must be selected in the process environment or with --env-file."
        )
    for key in command_overrides:
        if key not in {"TRACE_ENVIRONMENT", "TRACE_LOG_LEVEL"}:
            raise ConfigurationError(
                f"Unsupported command-line configuration key {key}."
            )

    merged = {"TRACE_LOG_LEVEL": "INFO"}
    merged.update(
        {
            key: value
            for key, value in file_values.items()
            if key in {"TRACE_ENVIRONMENT", "TRACE_LOG_LEVEL"}
        }
    )
    merged.update(
        {
            key: value
            for key, value in process_environment.items()
            if key in {"TRACE_ENVIRONMENT", "TRACE_LOG_LEVEL"}
        }
    )
    merged.update(command_overrides)

    environment = merged.get("TRACE_ENVIRONMENT", "").strip().lower()
    if not environment:
        raise ConfigurationError(
            "Missing required TRACE_ENVIRONMENT. Set it in .env, the process environment, or pass --environment."
        )
    if environment not in _ENVIRONMENT_NAMES:
        raise ConfigurationError(
            "Invalid TRACE_ENVIRONMENT; expected development, test, or production."
        )

    log_level = merged.get("TRACE_LOG_LEVEL", "").strip().upper()
    if log_level not in _LOG_LEVELS:
        raise ConfigurationError(
            "Invalid TRACE_LOG_LEVEL; expected DEBUG, INFO, WARNING, ERROR, or CRITICAL."
        )

    return Settings(environment=environment, log_level=log_level)
