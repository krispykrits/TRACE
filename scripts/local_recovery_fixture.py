"""Explicit synthetic CLI crash seams; never selected by application bootstrap."""

from __future__ import annotations

import argparse
import os
import signal
from pathlib import Path
from unittest.mock import patch

from scripts.investigator_fixture import main as fixture_main
from trace_app.adapters.storage.sqlite.workflow import SQLiteWorkflowStore
from trace_app.investigation.execution import ExecutionSession

POINTS = (
    "before_retention",
    "after_retention",
    "before_dispatch",
    "after_dispatch",
    "before_publication",
    "during_publication",
    "after_publication",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--point", choices=POINTS, required=True)
    parser.add_argument("--marker", type=Path, required=True)
    args, remaining = parser.parse_known_args()

    def crash() -> None:
        # The parent observes this marker only after reaching the exact boundary.
        args.marker.write_text(args.point)
        os.kill(os.getpid(), signal.SIGKILL)

    retain = SQLiteWorkflowStore.retain
    publish = SQLiteWorkflowStore.publish
    complete = SQLiteWorkflowStore._complete
    dispatch = ExecutionSession.dispatch

    def retention(self, *values, **keywords):
        if args.point == "before_retention":
            crash()
        result = retain(self, *values, **keywords)
        if args.point == "after_retention":
            crash()
        return result

    def publication(self, *values, **keywords):
        if args.point == "before_publication":
            crash()
        result = publish(self, *values, **keywords)
        if args.point == "after_publication":
            crash()
        return result

    def completion(self, *values, **keywords):
        if args.point == "during_publication":
            crash()
        return complete(self, *values, **keywords)

    def model_dispatch(self, ticket):
        if ticket.kind == "model" and args.point == "before_dispatch":
            crash()
        result = dispatch(self, ticket)
        if ticket.kind == "model" and args.point == "after_dispatch":
            crash()
        return result

    import sys

    with (
        patch.object(SQLiteWorkflowStore, "retain", retention),
        patch.object(SQLiteWorkflowStore, "publish", publication),
        patch.object(SQLiteWorkflowStore, "_complete", completion),
        patch.object(ExecutionSession, "dispatch", model_dispatch),
        patch.object(sys, "argv", ["local-recovery-fixture", *remaining]),
    ):
        return fixture_main()


if __name__ == "__main__":
    raise SystemExit(main())
