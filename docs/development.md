# Local development

TRACE currently provides an importable CLI scaffold and configuration check. It has no incident workflow, provider integration, retrieval, model call, or cloud code.

## Supported setup

The declared development target is CPython 3.12 on Linux. Install Python 3.12, uv and GNU make, then run these commands from the repository root:

| Goal | Command |
| --- | --- |
| Create or update the locked environment | `make sync` |
| Run the CLI scaffold | `make run` |
| Run the syntax check | `make check` |
| Run the deterministic test suite | `make test` |
| Run the process-boundary integration test | `make integration` |
| Remove generated local build state | `make clean` |

The equivalent setup and first validation sequence is:

```sh
make clean
make sync
make check
make test
make integration
```

Run that sequence twice from the repository root to check a fresh setup and repeatability. The integration fixture uses temporary directories, passes a deliberately minimal environment to a real Python CLI subprocess, and removes its files on both success and failure. It makes no provider calls and needs no production credentials or AWS resources. The tests are offline fixtures; they do not count as live-provider or Operational Pilot evidence. Use `make clean` to remove the local virtual environment and build outputs.

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
- tests/ — deterministic, credential-free unit and process-boundary tests
- docs/ — project decisions, plans, and development notes
- pyproject.toml — package metadata, script entry point, and dependency groups
- uv.lock — locked project dependency resolution

The package uses the specific trace_app module name to avoid colliding with Python's standard-library trace module. Educational projects remain references; no sibling-directory dependency is installed. The approved [reuse review](planning/production-usefulness-review.md) records these environment gaps: ai-incident-triage's native environment lacked FastAPI and its 37 tests passed only with the ML project's existing environment and PYTHONPATH; ml-incident-anomaly-detector's 111 tests used its existing virtual environment; incident-search's 56 tests used its existing virtual environment and cached model with offline mode; and the DL project could not be dynamically validated because its environment lacked the needed pandas/PyTorch combination. These results are not clean-install evidence and must not be inherited as TRACE runtime requirements. TRACE uses its own locked Python 3.12 environment and must pass from a clean checkout without educational-project environments.

## Log output and incident evidence

The TRACE logging module uses Python's standard logging framework to emit structured JSON to stderr. It provides correlation fields and redaction for the application's own operational records. It does not store, index, or query telemetry.

Amazon CloudWatch Logs is the selected hosted platform (owner decision, 2026-09-24). See [ADR 0003](adr/0003-cloudwatch-hosted-logging.md) and the [collection example and hosted acceptance procedure](../deploy/cloudwatch/README.md). The existing JSON stderr output remains the application boundary; deployment captures it to a file collected by the EC2 CloudWatch agent. CloudWatch delivery is not yet deployed or verified. Although issue #3 is closed on GitHub, its hosted acceptance evidence remains unverified and is not implied by local tests.

TRACE's incident investigation still needs read-only adapters to query the operator's actual log and metric sources. The roadmap places bounded evidence queries in S3 and real-source contracts and controlled tools in S4. Sending TRACE's own runtime logs to CloudWatch does not satisfy those incident evidence integrations. If the authorized pilot source already uses Elastic, TRACE should query that source through an adapter rather than creating a second log store.

References: [CloudWatch agent collection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html), [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/), [Elastic pricing](https://www.elastic.co/pricing), [Elastic licensing](https://www.elastic.co/pricing/faq/licensing).
