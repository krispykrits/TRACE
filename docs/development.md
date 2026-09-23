# Local development

TRACE currently provides only an importable CLI scaffold. It has no runtime
dependencies, service behavior, provider integrations, retrieval, model calls,
or cloud code.

## Supported setup

The initial development target is CPython 3.12 on Linux. Install
[uv](https://docs.astral.sh/uv/) and Python 3.12, then from the repository root:

```sh
uv sync --locked
uv run --locked trace-app --help
uv run --locked python -m unittest discover -s tests -v
```

Equivalent Make targets are `make sync`, `make run`, `make test`,
`make check`, and `make clean`. The check target compiles the Python source
and tests; CI quality gates are tracked separately.

## Repository map

- `src/trace_app/` — TRACE-owned application package and CLI entry point
- `tests/` — deterministic, credential-free smoke tests
- `docs/` — project decisions, plans, and development notes
- `pyproject.toml` — package metadata, script entry point, and dependency groups
- `uv.lock` — locked project dependency resolution

The package uses the specific `trace_app` module name to avoid colliding with
Python's standard-library `trace` module. Educational projects remain
references; no sibling-directory dependency is installed.

The CLI currently reports help and version only. Order/Payment behavior,
evidence contracts, integrations, and AWS deployment belong to later scoped
increments and their accepted decisions.
