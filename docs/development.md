# Local development

Use CPython 3.12 on Linux, uv 0.12.17 and GNU make. Run commands from the repository root. `pyproject.toml`/`uv.lock` own dependency versions; [package layout](architecture/package-layout.md) owns import boundaries.

The public CLI handles configuration, synthetic Order/replay commands and local captured-window investigation, protected saved inspection/export and cancellation. See the [investigator CLI contract](architecture/investigator-cli.md) for trusted profile setup and one-command offline reproduction.

## Setup and first run

~~~sh
make sync
uv run --locked trace-app --help
uv run --locked trace-app --version
uv run --locked trace-app check-config --env-file .env.example
~~~

The example contains no credentials. Default CLI help/version needs no configuration. Keep local environment/provider files private and Git-ignored; setup does not require an Azure account or a cluster.

## Quality checks

~~~sh
make check lint format-check type-check architecture-check test integration package-check
~~~

| Command | Purpose |
| --- | --- |
| `make sync` | Recreate the locked environment |
| `make run` | Show CLI help |
| `make check` | Compile source, tests, scripts and evaluation |
| `make lint` / `make format-check` | Ruff lint/format verification |
| `make type-check` | Static typing |
| `make architecture-check` | Dependency direction and evaluator isolation |
| `make test` | Unit and contract suites |
| `make integration` | SQLite, evaluator, process/CLI and workflow integration |
| `make package-check` | Build/install/smoke-test the runtime wheel outside the checkout |
| `make integration-s4` | Scripted evidence-package and tool-evaluation checks |
| `make integration-semantic` / `make retrieval-evaluate` | Separately opted-in cached-model retrieval comparisons |
| `make integration-live` | Explicitly authorized paid provider gate |
| `make clean` | Remove `.venv`, `build` and `dist`; optional cleanup |

The credential-free GitHub Actions job runs the same quality checks on Ubuntu 24.04. It installs public locked dependencies; it performs no paid model request. Model benchmarks and live checks are separate from deterministic CI. Passing tests does not establish operational/release acceptance.

## Configuration and logs

| Setting | Contract |
| --- | --- |
| `TRACE_ENVIRONMENT` | Required: `development`, `test` or `production` |
| `TRACE_LOG_LEVEL` | Optional, default `INFO`; standard DEBUG through CRITICAL levels |
| `--env-file` / `TRACE_ENV_FILE` | Explicit settings file; the CLI option takes precedence |
| `TRACE_INVESTIGATOR_PROFILE` / `TRACE_ALLOW_PAID_LIVE` | Process-only investigator/provider settings; foundation/demo commands ignore them without reading profile/provider files |

Value precedence is built-in defaults → selected dotenv file → process environment → CLI overrides. With no selected file, a missing working-directory `.env` is allowed. An explicitly selected file must be readable.

Investigator commands instead use the owner-managed `TRACE_INVESTIGATOR_PROFILE` and explicit `--environment`/`--provider`; they do not read dotenv settings. [Their profile and exit contract](architecture/investigator-cli.md) is separate.

Dotenv parsing accepts blank/comment lines and `KEY=VALUE`, removes matching surrounding quotes and performs no shell evaluation, variable expansion or inline-comment interpretation. Unknown `TRACE_` settings and invalid values fail without echoing their contents.

~~~sh
uv run --locked trace-app check-config --environment test --log-level DEBUG
~~~

Application JSON goes to stderr; command result JSON goes to stdout. Logs carry UTC time, component/event, correlation and relevant execution/version metadata. Secret fields and registered secret values are redacted; numeric token usage is retained only as nonnegative integers/null. Never log raw prompts, responses, credentials, removed redaction values or unsafe provider errors.

Environment/log validation is separate from model readiness. The [provider guide](architecture/model-provider.md) owns explicit private provider files, trusted authority/prompt composition, admission and spending. There is no silent fake/provider/source-permission fallback.

## Public CLI

| Command | Behavior |
| --- | --- |
| `trace-app` / `--help` / `--version` | Help or package version |
| `trace-app check-config` | Configuration validation and correlated JSON startup log |
| `trace-app demo-order` | Validated synthetic Order → Payment request |
| `trace-app replay-dependency` | Seeded dependency evidence export |
| `trace-app replay-scenario` | Explicit development case export, with optional distractor omission |
| `trace-app investigate` | Explicit Azure/evidence-only investigation over a configured development/test capture |
| `trace-app report` | Current-authority saved display, citation resolution or private JSON export |
| `trace-app cancel-investigation` | Durable cancellation of a queued/running job |

~~~sh
uv run --locked trace-app demo-order --environment test --order-id order-001 --customer-id customer-001 --amount-cents 1250
uv run --locked trace-app replay-dependency --environment test --seed 17 --mode failure
uv run --locked trace-app replay-scenario --environment test --case c01 --seed 17
~~~

The fixtures accept `customer-001` and run only in development/test. Replay exports observed evidence, not evaluator labels. Configuration/invalid input exits 2; the Order demo reports adapter dependency failure with exit 3. A valid replay can return observed failure data with exit 0. See [Order workflow](architecture/order-payment-workflow.md), [replay envelope](architecture/dependency-replay-evidence.md) and [scenario catalog](architecture/development-scenarios.md).

## Developer demonstrations

These commands use synthetic fixtures and temporary/private state. They are not the operator CLI. Choose fresh output paths; scripts refuse overwrite where documented.

| Demonstration | Command | Contract |
| --- | --- | --- |
| Corpus ingestion/restart | `uv run --locked python scripts/demo_corpus.py` | [Corpus](architecture/knowledge-corpus.md) |
| Lexical search | `uv run --locked python scripts/demo_search.py --query "TLS certificate expiry" --top-k 3` | [Retrieval](architecture/knowledge-retrieval.md) |
| Bounded quoted context | `uv run --locked python scripts/demo_context.py --query "PAYMENT_TIMEOUT evidence" --max-passages 1` | [Context](architecture/retrieval-evaluation-context.md) |
| Timeline and citations | `uv run --locked python scripts/demo_timeline.py --case c01 --seed 17` | [Timeline](architecture/incident-timelines.md) |
| Six read-only tools and rejected requests | `uv run --locked python scripts/demo_tools.py` | [Tool catalog](architecture/investigation-tools.md) |
| Scripted cited package | `uv run --locked python scripts/demo_integration.py --output /tmp/trace-s4-package.json` | [Integration](architecture/scripted-evidence-package.md) |
| Bounded investigator | `uv run --locked python -m scripts.demo_investigator --output /tmp/trace-investigator-demo.json` | [Investigator](architecture/bounded-investigator.md) |

The investigator demonstration runs answerable, insufficient-evidence and timeout paths through real application/SQLite/tool boundaries with hand-authored model/review records. It makes zero actual provider calls and performs no actual human review.

Persist evidence and read it in a later process:

~~~sh
uv run --locked python scripts/demo_persistence.py ingest --db /tmp/trace-store-demo.sqlite3 --seed 17 --mode failure --submission-key case-17
~~~

Copy the printed investigation ID into the next command:

~~~sh
uv run --locked python scripts/demo_persistence.py show --db /tmp/trace-store-demo.sqlite3 --investigation-id <id-from-ingest>
~~~

Repeated ingestion of the same submission is idempotent. The file uses a fixed synthetic scope and private permissions. Writable startup migrates earlier job schemas to schema 3 before read-only workers start. [SQLite storage](architecture/sqlite-investigation-store.md) and [bounded queries](architecture/bounded-evidence-queries.md) define query filters, duplicate/recovery and deletion behavior.

## Evaluation and optional embeddings

~~~sh
uv run --locked python -m evaluation.runner run --output /tmp/trace-s3-evaluation
uv run --locked python -m evaluation.runner rescore --run-dir /tmp/trace-s3-evaluation
~~~

Use a new run directory. These candidate fixtures test scoring plumbing. Saved scores include failed/malformed/absent outcomes; success of the scorer is separate from quality of a candidate. See [the evaluation guide](../evaluation/README.md) for protected inputs, actual versus fixture review and exact historical checkouts.

Lexical search needs no embedding weights. Semantic/hybrid comparison requires the locked `semantic` extra and an explicitly prepared pinned local cache. Follow the [retrieval setup](architecture/knowledge-retrieval.md); missing cache/dependencies fail explicitly, without automatic download or lexical fallback.

The v4 retrieval judgments were owner-endorsed and their frozen lexical acceptance passed. Historical reports require their recorded scorer checkout; current-source exploration must use new output paths. [The passage protocol](architecture/retrieval-evaluation-context.md) owns those thresholds and review provenance.

## Live provider and hosted work

The actual synthetic Azure connector check is recorded as historical evidence in [the provider guide](architecture/model-provider.md#reproduction-and-live-evidence). New paid checks require explicit authorization, `TRACE_ALLOW_PAID_LIVE=1` and all private setup/secret/journal/report and known-spending inputs. Missing/empty/skipped live suites fail closed. The manual hosted live job has no private configuration by default.

Azure/AKS deployment, shared PostgreSQL admission, pod identity and Azure telemetry remain [cloud work](../deploy/README.md). TRACE's own application logs are distinct from incident-source telemetry; collection does not supply source/transmission rights.

## Contributing

Follow [package boundaries](architecture/package-layout.md), [security](security/README.md), [documentation maintenance](README.md#keep-documentation-current) and [repository workflow](../AGENTS.md#git-and-pull-requests). Update behavior and its canonical guide together. Preserve frozen evaluator/corpus artifacts and use their recorded checkouts for historical rescoring.
