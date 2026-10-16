"""Argument validation, protected rendering and fixed investigator exit outcomes."""

from __future__ import annotations

import argparse
import json
import logging
import os
import signal
from pathlib import Path
from typing import Any

from trace_app.bootstrap import create_local_investigator
from trace_app.investigation.assessment_context import AssessmentBoundaryError
from trace_app.investigation.execution import ExecutionRejected
from trace_app.investigation.models import (
    StoreAccessError,
    StoreConflictError,
    StoreInputError,
    StoreStateError,
)
from trace_app.investigation.provider import ModelErrorCode, ModelProviderError
from trace_app.runtime.logging import configure_logging

COMMANDS = ("investigate", "report", "cancel-investigation")


def add_commands(commands: Any) -> None:
    start = commands.add_parser(
        "investigate",
        help="investigate a captured service/window using trusted local grants",
    )
    start.add_argument("--service", required=True)
    start.add_argument(
        "--environment", required=True, choices=("development", "test", "production")
    )
    start.add_argument("--window-start", required=True)
    start.add_argument("--window-end", required=True)
    start.add_argument(
        "--provider",
        required=True,
        choices=("azure", "evidence-only", "offline-fixture"),
    )
    show = commands.add_parser(
        "report",
        help="inspect or export a saved investigation with current permissions",
    )
    show.add_argument("--investigation-id", required=True)
    show.add_argument("--artifact-id")
    show.add_argument("--citation-id")
    cancel = commands.add_parser(
        "cancel-investigation", help="cancel a queued/running local investigation"
    )
    cancel.add_argument("--investigation-id", required=True)
    for command in (start, show, cancel):
        command.add_argument("--format", choices=("text", "json"), default="text")
        command.add_argument(
            "--output",
            type=Path,
            help="create a new private JSON export; requires --format json",
        )


def exit_code(data: dict[str, Any]) -> int:
    failure = data.get("failure_code")
    if data.get("execution_status") == "cancelled" or failure == "cancelled":
        return 130
    if data.get("execution_status") == "expired" or failure in ("timeout", "expired"):
        return 5
    if failure in (
        "access_denied",
        "scope_mismatch",
        "policy_rejected",
        "citation_denied",
    ):
        return 4
    if data.get("execution_status") == "failed":
        return 3
    if data.get("execution_status") in ("running", "queued"):
        return 6
    if data.get("assessment_status") == "pending" and data.get("report"):
        return 7
    return 0


def render(data: dict[str, Any]) -> str:
    # JSON quoting prevents source/model terminal control sequences from executing.
    if "citation" in data:
        return json.dumps(data, indent=2, ensure_ascii=True)
    lines = [
        f"Investigation: {data['investigation_id']}",
        f"Execution: {data['execution_status']} | Assessment: {data['assessment_status']}",
        "Provider/configuration: "
        + json.dumps(data.get("configuration"), sort_keys=True),
        f"Validation: {data['validation_outcome']} | Sensitivity: {data['sensitivity']}",
        "Usage: " + json.dumps(data["usage"])
        if data["usage_available"]
        else "Usage: unknown / unavailable",
        "Timeline capture: " + json.dumps(data.get("timeline_capture"), sort_keys=True),
        "Model context omissions: "
        + json.dumps(data.get("model_context_omissions"), sort_keys=True),
        "Timeline (observed; time correlation does not prove cause):",
    ]
    lines.extend("  " + json.dumps(event, sort_keys=True) for event in data["timeline"])
    if data.get("report"):
        for name, value in data["report"].items():
            lines.append(
                name.replace("_", " ").capitalize()
                + ": "
                + json.dumps(value, ensure_ascii=True, sort_keys=True)
            )
    if data["failure_code"]:
        lines.append("Failure: " + data["failure_code"])
    return "\n".join(lines)


def run(parsed: argparse.Namespace) -> int:
    configure_logging()
    app = None
    previous = signal.getsignal(signal.SIGTERM)

    def interrupt(signum: int, frame: Any) -> None:
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, interrupt)
    try:
        if parsed.output and parsed.format != "json":
            raise ValueError("Export requires JSON.")
        if parsed.command == "investigate":
            # Validate caller filters before opening sources, budget journals or credentials.
            from datetime import timedelta

            from trace_app.evidence.models import _parse_utc
            from trace_app.investigation.models import _identifier

            _identifier("service", parsed.service)
            start, end = _parse_utc(parsed.window_start), _parse_utc(parsed.window_end)
            if (
                start > end
                or end - start > timedelta(hours=24)
                or parsed.environment == "production"
            ):
                raise ValueError("Invalid local request.")
        path = Path(os.environ["TRACE_INVESTIGATOR_PROFILE"])
        if not path.is_absolute():
            raise ValueError("Profile must be absolute.")
        app = create_local_investigator(path)
        if parsed.command == "investigate":
            data = app.investigate(
                service=parsed.service,
                environment=parsed.environment,
                window_start=parsed.window_start,
                window_end=parsed.window_end,
                provider=parsed.provider,
            )
            if parsed.format == "json":
                data = app.read(data["investigation_id"], export=True)
        elif parsed.command == "cancel-investigation":
            data = app.cancel(parsed.investigation_id)
            if parsed.format == "json":
                data = app.read(parsed.investigation_id, export=True)
        else:
            data = app.read(
                parsed.investigation_id,
                export=parsed.format == "json",
                artifact_id=parsed.artifact_id,
                citation_id=parsed.citation_id,
            )
        output = (
            json.dumps(data, sort_keys=True, ensure_ascii=True, allow_nan=False)
            if parsed.format == "json"
            else render(data)
        )
        if parsed.output:
            descriptor = os.open(
                parsed.output,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                0o600,
            )
            with os.fdopen(descriptor, "w") as stream:
                stream.write(output + "\n")
            print(
                json.dumps(
                    {
                        "schema_version": "investigation-export.v1",
                        "investigation_id": data["investigation_id"],
                        "outcome": "exported",
                    }
                )
            )
        else:
            print(output)
        return exit_code(data) if "execution_status" in data else 0
    except ModelProviderError as error:
        if error.code in (
            ModelErrorCode.CONFIGURATION,
            ModelErrorCode.CREDENTIALS_MISSING,
            ModelErrorCode.CAPABILITY_UNSUPPORTED,
        ):
            code, outcome = 2, "invalid_request_or_configuration"
        elif error.code in (ModelErrorCode.POLICY, ModelErrorCode.AUTHENTICATION):
            code, outcome = 4, "access_denied"
        elif error.code in (ModelErrorCode.TIMEOUT, ModelErrorCode.EXPIRED):
            code, outcome = 5, "timeout_or_expired"
        elif error.code == ModelErrorCode.CANCELLED:
            code, outcome = 130, "cancelled"
        else:
            code, outcome = 3, "dependency_failure"
    except (AssessmentBoundaryError, StoreAccessError) as error:
        dependency = isinstance(error, AssessmentBoundaryError) and error.code in (
            "execution_failure",
            "dependency_failure",
        )
        code, outcome = (
            (3, "dependency_failure") if dependency else (4, "access_denied")
        )
    except (ValueError, KeyError, TypeError, StoreInputError, StoreConflictError):
        code, outcome = 2, "invalid_request_or_configuration"
    except (StoreStateError, ExecutionRejected):
        code, outcome = 6, "execution_stopped"
    except KeyboardInterrupt:
        code, outcome = 130, "cancelled"
    except Exception:
        code, outcome = 3, "dependency_failure"
    finally:
        signal.signal(signal.SIGTERM, previous)
        if app:
            app.close()
    logging.getLogger("trace_app.cli").error(
        "Investigator command did not disclose content.",
        extra={"event": "investigator.denied", "outcome": outcome},
    )
    return code
