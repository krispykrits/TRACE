# Local development

TRACE currently provides an importable CLI, configuration check and synthetic Order–Payment demo. It has no incident investigator, real provider integration, retrieval, model call or deployed cloud runtime.

## Supported setup

The supported development and CI runtime is CPython 3.12 on Linux. Install Python 3.12, uv 0.12.17 and GNU make, then run these commands from the repository root. The project rejects other Python minor versions and other uv versions so local setup and CI use the same toolchain:

| Goal | Command |
| --- | --- |
| Create or update the locked environment | `make sync` |
| Run the CLI scaffold | `make run` |
| Run the syntax check | `make check` |
| Run lint checks | `make lint` |
| Check formatting | `make format-check` |
| Run static type checks | `make type-check` |
| Run the deterministic test suite | `make test` |
| Run the process-boundary integration test | `make integration` |
| Run the opt-in provider gate | `make integration-live` |
| Remove generated local build state | `make clean` |

The equivalent setup and first validation sequence is:

```sh
make clean
make sync
make check
make lint
make format-check
make type-check
make test
make integration
```

Run that sequence twice from the repository root to check a fresh setup and repeatability. The integration fixture uses temporary directories, passes a deliberately minimal environment to a real Python CLI subprocess, and removes its files on both success and failure. It makes no provider calls and needs no production credentials or AWS resources. The tests are offline fixtures; they do not count as live-provider or Operational Pilot evidence. Use `make clean` to remove the local virtual environment and build outputs.

The checked-in example contains no credentials. The .env file is ignored by Git. The default trace-app invocation still prints help, and --version does not require configuration.

## Synthetic Order demo

Run one Order → Payment request with the in-process Customer, Payment and Notification fixtures:

```sh
uv run --locked trace-app demo-order --environment test --order-id order-001 --customer-id customer-001 --amount-cents 1250
```

The command prints one JSON business outcome to stdout and correlated JSON operational logs to stderr. It needs no credentials, network service or AWS resource. The fixture recognizes only `customer-001`; an unknown customer yields a rejected outcome without Payment or Notification calls. Invalid input/configuration exits 2; an adapter dependency error exits 3 without an accepted receipt. The demo refuses the `production` environment. See the [workflow contract and fixture limits](architecture/order-payment-workflow.md) and [ADR 0004](adr/0004-synchronous-synthetic-order-workflow.md). These logs are not incident evidence or Operational Pilot data.

## GitHub Actions quality gate

Pull requests and pushes to `main` run the `Quality checks` workflow on `ubuntu-24.04`. It uses CPython 3.12, uv 0.12.17 and the committed `uv.lock`; `uv sync --locked` fails if dependency metadata and the lock disagree. The job records the Python and uv versions and the resolved dependency tree in its log. It runs the same syntax, lint, format, type, unit and process-integration commands listed above. Any failed command fails the job. These checks are deterministic and require no credentials, network-backed application service, AWS access or paid model call; model benchmarks are not part of this workflow.

The manual workflow has a separate **Run live provider integration checks** input, off by default. Enabling it runs a distinct job and cannot change or skip the fast quality job. That job fails with an explicit message until real checks are added under `tests/live_provider`; a missing or empty suite cannot pass as verified. No provider checks currently exist and no credentials are configured for the job, so it is not live-provider acceptance evidence. Record an enabled, passing run before describing such checks as verified.

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
