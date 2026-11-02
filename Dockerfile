FROM ghcr.io/astral-sh/uv:0.12.17 AS uv
FROM python:3.12-slim
COPY --from=uv /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --locked --no-dev && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin trace
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "trace_app.adapters.http.api:app_factory", "--factory", "--host", "0.0.0.0", "--port", "8000"]
