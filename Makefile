.PHONY: sync run test check clean

sync:
	uv sync --locked

run:
	uv run --locked trace-app

test:
	uv run --locked python -m unittest discover -s tests -v

check:
	uv run --locked python -m compileall -q src tests

clean:
	rm -rf .venv build dist
