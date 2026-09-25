.PHONY: sync run check test integration clean

sync:
	uv sync --locked

run:
	uv run --locked trace-app

check:
	uv run --locked python -m compileall -q src tests

test:
	uv run --locked python -m unittest discover -s tests -v

integration:
	uv run --locked python -m unittest discover -s tests -p 'test_cli_process.py' -v

clean:
	rm -rf .venv build dist
