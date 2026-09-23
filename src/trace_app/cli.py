"""Minimal CLI entry point for the TRACE scaffold."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from trace_app import __version__


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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Print help by default; reserve application behavior for later increments."""
    parser = _parser()
    arguments = list(argv) if argv is not None else sys.argv[1:]
    if arguments:
        parser.parse_args(arguments)
    else:
        parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
