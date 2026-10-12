.PHONY: sync run check lint format-check type-check architecture-check package-check test integration integration-live integration-semantic retrieval-evaluate clean

sync:
	uv sync --locked

run:
	uv run --locked trace-app

check:
	uv run --locked python -m compileall -q src tests scripts evaluation

lint:
	uv run --locked ruff check src tests scripts evaluation

format-check:
	uv run --locked ruff format --check src tests scripts evaluation

type-check:
	uv run --locked mypy src tests evaluation

test:
	uv run --locked python -m unittest discover -s tests/unit -t . -v
	uv run --locked python -m unittest discover -s tests/contracts -t . -v

integration:
	uv run --locked python -m unittest discover -s tests/integration -t . -v

architecture-check:
	uv run --locked python scripts/check_architecture.py

package-check:
	uv run --locked python scripts/check_package.py

integration-live:
	uv run --locked python scripts/run_live_provider_checks.py

integration-semantic:
	uv run --locked --extra semantic python -m evaluation.retrieval_baseline

retrieval-evaluate:
	uv run --locked --extra semantic python -m evaluation.retrieval_quality

clean:
	rm -rf .venv build dist
