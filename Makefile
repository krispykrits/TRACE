.PHONY: sync run check lint format-check type-check test integration integration-live clean

sync:
	uv sync --locked

run:
	uv run --locked trace-app

check:
	uv run --locked python -m compileall -q src tests scripts

lint:
	uv run --locked ruff check src tests scripts

format-check:
	uv run --locked ruff format --check src tests scripts

type-check:
	uv run --locked mypy src tests

test:
	uv run --locked python -m unittest discover -s tests -v

integration:
	uv run --locked python -m unittest discover -s tests -p 'test_cli_process.py' -v

integration-live:
	uv run --locked python scripts/run_live_provider_checks.py

clean:
	rm -rf .venv build dist
