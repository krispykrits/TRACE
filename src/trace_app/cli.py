"""Minimal CLI entry point for the TRACE scaffold."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from trace_app import __version__
from trace_app.configuration import ConfigurationError, load_settings
from trace_app.structured_logging import collect_secret_values, configure_logging


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trace-app",
        description="TRACE incident investigation scaffold.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    commands = parser.add_subparsers(dest="command")
    config_parser = commands.add_parser(
        "check-config",
        help="validate configuration and emit a structured startup record",
    )
    config_parser.add_argument(
        "--env-file",
        type=Path,
        help="read settings from this .env-style file instead of .env",
    )
    config_parser.add_argument(
        "--environment",
        choices=("development", "test", "production"),
        help="override TRACE_ENVIRONMENT for this invocation",
    )
    config_parser.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        help="override TRACE_LOG_LEVEL for this invocation",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Validate configuration for the selected CLI command."""
    parser = _parser()
    arguments = list(argv) if argv is not None else sys.argv[1:]
    if not arguments:
        parser.print_help()
        return 0
    parsed = parser.parse_args(arguments)
    if parsed.command != "check-config":
        return 0

    process_environment = dict(os.environ)
    secrets = collect_secret_values(process_environment)
    overrides: dict[str, str] = {}
    if parsed.environment is not None:
        overrides["TRACE_ENVIRONMENT"] = parsed.environment
    if parsed.log_level is not None:
        overrides["TRACE_LOG_LEVEL"] = parsed.log_level
    try:
        settings = load_settings(
            environ=process_environment,
            dotenv_path=parsed.env_file,
            overrides=overrides,
        )
    except ConfigurationError as error:
        configure_logging(level="ERROR", secret_values=secrets)
        logging.getLogger("trace_app.configuration").error(
            str(error),
            extra={
                "event": "configuration.invalid",
                "error": str(error),
                "application_version": __version__,
            },
        )
        return 2

    configure_logging(level=settings.log_level, secret_values=secrets)
    logging.getLogger("trace_app.configuration").info(
        "Configuration validated.",
        extra={
            "event": "configuration.validated",
            "environment": settings.environment,
            "application_version": __version__,
        },
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
