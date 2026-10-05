"""CLI entry point for TRACE's foundation and synthetic Order demo."""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

from trace_app import __version__
from trace_app.configuration import ConfigurationError, load_settings
from trace_app.demo_fixtures import CustomerFixture, NotificationFixture, PaymentFixture
from trace_app.order_workflow import (
    ORDER_SERVICE,
    BoundaryContext,
    DependencyUnavailable,
    OrderInputError,
    OrderRequest,
    OrderWorkflow,
)
from trace_app.replay import ReplayConfig, ReplaySession
from trace_app.structured_logging import collect_secret_values, configure_logging


def _settings_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument(
        "--env-file",
        type=Path,
        help="read settings from this .env-style file instead of .env",
    )
    command.add_argument(
        "--environment",
        choices=("development", "test", "production"),
        help="override TRACE_ENVIRONMENT for this invocation",
    )
    command.add_argument(
        "--log-level",
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        help="override TRACE_LOG_LEVEL for this invocation",
    )


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
    _settings_arguments(config_parser)

    demo_parser = commands.add_parser(
        "demo-order",
        help="run a synthetic Order → Payment request without external services",
    )
    _settings_arguments(demo_parser)
    demo_parser.add_argument("--order-id", required=True, help="synthetic order ID")
    demo_parser.add_argument(
        "--customer-id", required=True, help="synthetic customer ID"
    )
    demo_parser.add_argument(
        "--amount-cents", required=True, type=int, help="positive integer amount"
    )
    replay_parser = commands.add_parser(
        "replay-dependency",
        help="export synthetic Order → Payment evidence for one seeded replay",
    )
    _settings_arguments(replay_parser)
    replay_parser.add_argument("--seed", required=True, type=int)
    replay_parser.add_argument("--mode", required=True, choices=("normal", "failure"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the selected CLI command with validated configuration."""
    parser = _parser()
    arguments = list(argv) if argv is not None else sys.argv[1:]
    if not arguments:
        parser.print_help()
        return 0
    parsed = parser.parse_args(arguments)
    if parsed.command not in {"check-config", "demo-order", "replay-dependency"}:
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

    correlation_id = configure_logging(level=settings.log_level, secret_values=secrets)
    if parsed.command == "check-config":
        logging.getLogger("trace_app.configuration").info(
            "Configuration validated.",
            extra={
                "event": "configuration.validated",
                "environment": settings.environment,
                "application_version": __version__,
            },
        )
        return 0

    if parsed.command == "replay-dependency":
        replay_environment: Literal["development", "test"]
        if settings.environment == "development":
            replay_environment = "development"
        elif settings.environment == "test":
            replay_environment = "test"
        else:
            logging.getLogger("trace_app.replay").error(
                "Synthetic replay is restricted to development and test.",
                extra={
                    "event": "replay.invalid",
                    "environment": settings.environment,
                },
            )
            return 2
        try:
            config = ReplayConfig(
                seed=parsed.seed,
                mode=parsed.mode,
                environment=replay_environment,
            )
        except ValueError as error:
            logging.getLogger("trace_app.replay").error(
                str(error),
                extra={"event": "replay.invalid", "environment": settings.environment},
            )
            return 2
        result = ReplaySession(config).replay()
        logging.getLogger("trace_app.replay").info(
            "Synthetic dependency replay completed.",
            extra={
                "event": "replay.completed",
                "environment": replay_environment,
                "correlation_id": result.evidence.records[0].correlation_id,
                "status": result.status,
                "evidence_count": len(result.evidence.records),
            },
        )
        print(
            json.dumps(
                {"status": result.status, "evidence": result.evidence.to_dict()},
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        return 0

    logger = logging.getLogger("trace_app.order")
    if settings.environment == "production":
        logger.error(
            "The synthetic Order demo is restricted to development and test.",
            extra={
                "event": "order.demo_environment_rejected",
                "service": ORDER_SERVICE,
                "environment": settings.environment,
            },
        )
        return 2
    try:
        request = OrderRequest(
            order_id=parsed.order_id,
            customer_id=parsed.customer_id,
            amount_cents=parsed.amount_cents,
        )
    except OrderInputError as error:
        logger.error(
            str(error),
            extra={
                "event": "order.invalid",
                "service": ORDER_SERVICE,
                "environment": settings.environment,
            },
        )
        return 2

    context = BoundaryContext(
        service=ORDER_SERVICE,
        environment=settings.environment,
        correlation_id=correlation_id,
    )
    workflow = OrderWorkflow(
        customers=CustomerFixture(),
        payments=PaymentFixture(),
        notifications=NotificationFixture(),
    )
    try:
        outcome = workflow.place(request, context=context)
    except DependencyUnavailable as error:
        logger.error(
            "Synthetic Order dependency failed.",
            extra={
                "event": "order.dependency_failed",
                "service": ORDER_SERVICE,
                "environment": settings.environment,
                "dependency": error.dependency,
            },
        )
        return 3

    print(
        json.dumps(
            {
                "status": outcome.status,
                "reason": outcome.reason,
                "order_id": outcome.order_id,
                "service": outcome.context.service,
                "environment": outcome.context.environment,
                "correlation_id": outcome.context.correlation_id,
                "payment_authorization_id": outcome.payment_authorization_id,
                "notification_recorded": outcome.notification_recorded,
            },
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
