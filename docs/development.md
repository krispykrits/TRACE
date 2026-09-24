# Local development

TRACE currently provides an importable CLI scaffold and configuration check. It has no incident workflow, provider integration, retrieval, model call, or cloud code.

## Supported setup

The initial development target is CPython 3.12 on Linux. Install uv and Python 3.12, then from the repository root:

```sh
uv sync --locked
cp .env.example .env
uv run --locked trace-app check-config
uv run --locked python -m unittest discover -s tests -v
```

The checked-in example contains no credentials. The .env file is ignored by Git. The default trace-app invocation still prints help, and --version does not require configuration.

## Configuration

The configuration check currently accepts:

| Name | Requirement | Values |
| --- | --- | --- |
| TRACE_ENVIRONMENT | Required | development, test, production |
| TRACE_LOG_LEVEL | Optional; defaults to INFO | DEBUG, INFO, WARNING, ERROR, CRITICAL |

Configuration values follow this precedence, from lowest to highest: built-in defaults, the selected .env file, process environment variables, then command-line options. Use --env-file to select a file for one invocation. Otherwise TRACE_ENV_FILE selects a file; if neither is supplied, TRACE loads .env from the working directory when present. A missing default .env is allowed, while a selected file must exist and be readable.

The .env parser accepts blank lines, full-line comments, and KEY=VALUE entries. Matching single or double quotes around a value are removed. It does not execute shell syntax, expand variables, or interpret inline comments. Unsupported TRACE_ settings and invalid values fail with an error that names the setting without echoing its value.

Example:

```sh
uv run --locked trace-app check-config --environment test --log-level DEBUG
uv run --locked trace-app check-config --env-file .env.example
```

The current CLI has no model provider or model artifact configuration. A successful configuration check does not claim provider or artifact readiness. When a future command requires a provider or artifact, production startup must fail if that required capability is missing or incompatible; it must not silently select a development fallback.

## Structured logs

check-config emits one JSON record on stderr. Records include an RFC 3339 UTC timestamp, level, component, correlation_id, event, message, and application_version. The correlation ID is generated once per CLI invocation and can be propagated through a future investigation. Add investigation_id, tool_attempt_id, model_attempt_id, and source/model/prompt/configuration version fields when those operations exist. Only record usage or cost after measuring a real invocation; this scaffold emits no fabricated metrics.

The formatter redacts values under fields named for passwords, secrets, tokens, API keys, authorization, credentials, or private keys. Callers can also register known secret values for removal from messages and exception text. Do not place secrets in application errors, and do not log unredacted provider payloads.

## Repository map

- src/trace_app/ — TRACE-owned application package and CLI entry point
- tests/ — deterministic, credential-free tests
- docs/ — project decisions, plans, and development notes
- pyproject.toml — package metadata, script entry point, and dependency groups
- uv.lock — locked project dependency resolution

The package uses the specific trace_app module name to avoid colliding with Python's standard-library trace module. Educational projects remain references; no sibling-directory dependency is installed.
