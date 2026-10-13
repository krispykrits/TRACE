# Local development

TRACE currently provides an importable CLI, configuration check, synthetic Order–Payment demo and a local SQLite evidence-store demo. It also provides authorized local knowledge search with optional cached CPU embeddings. It has no incident investigator, hosted model API, operational source integration or deployed cloud runtime.

The [model-provider contract](architecture/model-provider.md) adds provider-neutral interfaces and bounded single-call execution for #34's offline subtask #50. Its fake is explicitly selected in tests only. The owner selected Azure AI Foundry / GPT-6 Luna and a $20/month model spending cap on 2026-10-13 and reports an existing deployment. The guide records the approved category-based transmission policy, proposed stateless request/retention defaults and a nonsecret deployment checklist. Apply source access and transmission permissions separately; implement negative cases for secrets/PII, internal-source permission and evaluator-answer exclusion before hosted acceptance. The owner-selected resource API-key fallback passed one direct synthetic Azure JSON smoke check; the guide records its limits, usage and private metadata artifact. TRACE adapter/live-suite acceptance, provider processing/retention and policy/spend enforcement remain open. A passed offline check does not establish model readiness or enforce monthly spending.

For production, [the per-request gate](architecture/model-provider.md#required-production-enforcement--2026-10-13) must cover every model call and later tool result/history/retry: current source/transmission authorization, bounded redaction with unresolved violations blocking dispatch, unchanged citation IDs with local redaction provenance, content-free versioned audit and input-derived response protection. #34–#38 acceptance includes corresponding negative/bypass/output-disclosure cases. Do not report the existing raw-string `ModelRequest`/process wrapper as this gate; it is not implemented there. No new runtime boundary or SDK is introduced by recording these requirements.

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
| Run unit and contract tests | `make test` |
| Run storage, evaluator and process integration tests | `make integration` |
| Enforce dependency direction and evaluator isolation | `make architecture-check` |
| Build/install and smoke-test the runtime wheel | `make package-check` |
| Compare real cached lexical/semantic/hybrid baselines | `make integration-semantic` |
| Compare #17 passage rankings and context | `make retrieval-evaluate` |
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
make architecture-check
make test
make integration
make package-check
```

The integration fixtures use temporary state, including a deliberately minimal environment for actual CLI subprocesses, and clean up on success/failure. Unit/contract and integration suites have separate discovery and do not duplicate process tests. The package check installs a built wheel and locked runtime dependencies into a clean environment outside the checkout; package downloads are public dependencies, not live provider calls. These checks need no production credentials or AWS resources and do not count as Operational Pilot evidence. See [package placement and contribution rules](architecture/package-layout.md). Use `make clean` to remove the local virtual environment and build outputs.

The checked-in example contains no credentials. The .env file is ignored by Git. The default trace-app invocation still prints help, and --version does not require configuration.

## Synthetic Order demo

Run one Order → Payment request with the in-process Customer, Payment and Notification fixtures:

```sh
uv run --locked trace-app demo-order --environment test --order-id order-001 --customer-id customer-001 --amount-cents 1250
```

The command prints one JSON business outcome to stdout and correlated JSON operational logs to stderr. It needs no credentials, network service or AWS resource. The fixture recognizes only `customer-001`; an unknown customer yields a rejected outcome without Payment or Notification calls. Invalid input/configuration exits 2; an adapter dependency error exits 3 without an accepted receipt. The demo refuses the `production` environment. See the [workflow contract and fixture limits](architecture/order-payment-workflow.md) and [ADR 0004](adr/0004-synchronous-synthetic-order-workflow.md). These logs are not incident evidence or Operational Pilot data.

## Local SQLite evidence demo

The developer-only store demo persists seeded synthetic evidence and reads it after a process restart. Use a path outside the repository and copy the ID printed by the first command:

```sh
uv run --locked python scripts/demo_persistence.py ingest --db /tmp/trace-story-10.sqlite3 --seed 17 --mode failure --submission-key case-17
uv run --locked python scripts/demo_persistence.py show --db /tmp/trace-story-10.sqlite3 --investigation-id <id-from-ingest>
```

Re-running `ingest` with the same submission key and scenario returns zero new records; malformed input exits without creating the database. The file is mode 0600 and accepts only synthetic development/test evidence through a fixed demo scope. The [store contract](architecture/sqlite-investigation-store.md) defines schema setup, duplicate handling, attempt recovery and deletion. After copying the printed investigation_id, use scripts/demo_persistence.py query with the same database path, investigation ID and an optional service/time filter; the [query contract](architecture/bounded-evidence-queries.md) shows exact commands and empty/limit cases. The demo does not ingest authorized operational data or satisfy the Operational Pilot gate.

## GitHub Actions quality gate

Pull requests and pushes to `main` run the `Quality checks` workflow on `ubuntu-24.04`. It uses CPython 3.12, uv 0.12.17 and the committed `uv.lock`; `uv sync --locked` fails if dependency metadata and the lock disagree. The job records the Python and uv versions and the resolved dependency tree in its log. It runs the same syntax, lint, format, type, unit and process-integration commands listed above. Any failed command fails the job. These checks are deterministic and require no credentials, network-backed application service, AWS access or paid model call; model benchmarks are not part of this workflow.

The manual workflow has a separate **Run live provider integration checks** input, off by default. Enabling it runs a distinct job and cannot change or skip the fast quality job. That job fails with an explicit message until real checks are added under `tests/live`; a missing or empty suite cannot pass as verified. No provider checks currently exist and no credentials are configured for the job, so it is not live-provider acceptance evidence. Record an enabled, passing run before describing such checks as verified.

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

`trace-app check-config` has no model provider or model artifact configuration; the separate developer knowledge-search command validates its pinned optional cached embedding model when that mode is requested. A successful configuration check does not claim provider or artifact readiness. When a future command requires a provider or artifact, production startup must fail if that required capability is missing or incompatible; it must not silently select a development fallback.

## Structured logs

check-config emits one JSON record on stderr. Records include an RFC 3339 UTC timestamp, level, component, correlation_id, event, message, and application_version. The correlation ID is generated once per CLI invocation and can be propagated through a future investigation. Add investigation_id, tool_attempt_id, model_attempt_id, and source/model/prompt/configuration version fields when those operations exist. Only record usage or cost after measuring a real invocation; this scaffold emits no fabricated metrics.

The formatter redacts values under fields named for passwords, secrets, tokens, API keys, authorization, credentials, or private keys. Callers can also register known secret values for removal from messages and exception text. Do not place secrets in application errors, and do not log unredacted provider payloads.

## Repository map

- src/trace_app/ — TRACE-owned application package and CLI entry point
- corpus/ — curated development knowledge sources and versioned manifests
- evaluation/ — evaluator-only manifests, candidate fixtures and offline scorer tooling
- tests/ — deterministic, credential-free unit and process-boundary tests
- docs/ — project decisions, plans, and development notes
- pyproject.toml — package metadata, script entry point, and dependency groups
- uv.lock — locked project dependency resolution

The package uses the specific trace_app module name to avoid colliding with Python's standard-library trace module. Educational projects remain references; no sibling-directory dependency is installed. The approved [reuse review](planning/production-usefulness-review.md) records these environment gaps: ai-incident-triage's native environment lacked FastAPI and its 37 tests passed only with the ML project's existing environment and PYTHONPATH; ml-incident-anomaly-detector's 111 tests used its existing virtual environment; incident-search's 56 tests used its existing virtual environment and cached model with offline mode; and the DL project could not be dynamically validated because its environment lacked the needed pandas/PyTorch combination. These results are not clean-install evidence and must not be inherited as TRACE runtime requirements. TRACE uses its own locked Python 3.12 environment and must pass from a clean checkout without educational-project environments.

## Log output and incident evidence

The TRACE logging module uses Python's standard logging framework to emit structured JSON to stderr. It provides correlation fields and redaction for the application's own operational records. It does not store, index, or query telemetry. The local SQLite adapter stores bounded synthetic evidence snapshots and job state; it is separate from CloudWatch application logging.

Amazon CloudWatch Logs is the selected hosted platform (owner decision, 2026-09-24). See [ADR 0003](adr/0003-cloudwatch-hosted-logging.md) and the [collection example and hosted acceptance procedure](../deploy/cloudwatch/README.md). The existing JSON stderr output remains the application boundary; deployment captures it to a file collected by the EC2 CloudWatch agent. CloudWatch delivery is not yet deployed or verified. Although issue #3 is closed on GitHub, its hosted acceptance evidence remains unverified and is not implied by local tests.

TRACE's incident investigation still needs read-only adapters to query the operator's actual log and metric sources. The roadmap places bounded evidence queries in S3 and real-source contracts and controlled tools in S4. Sending TRACE's own runtime logs to CloudWatch does not satisfy those incident evidence integrations. If the authorized pilot source already uses Elastic, TRACE should query that source through an adapter rather than creating a second log store.

References: [CloudWatch agent collection](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html), [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/), [Elastic pricing](https://www.elastic.co/pricing), [Elastic licensing](https://www.elastic.co/pricing/faq/licensing).

## MVP development fixtures

Replay the four small synthetic cases with `trace-app replay-scenario --environment test --case c01 --seed 17` (also `c02`, `c03`, `c04`). Add `--without-distractor` to remove the unrelated Notification deployment. The [scenario catalog](architecture/development-scenarios.md) defines configuration, typed output, capture gaps/delays, reset and evaluator isolation. Its manifest is developer/evaluator material, outside investigator inputs. No held-out answers, real-source access or operational acceptance is claimed.

## Deterministic timeline demo

`uv run --locked python scripts/demo_timeline.py --case c01 --seed 17` shuffles a development fixture, persists/reopens its temporary SQLite state, constructs the bounded timeline and resolves its citations. Try `--case c03` for source gaps or `--limit 1` for explicit result truncation. The [timeline contract](architecture/incident-timelines.md) defines offset-window input, ordering, duplicate identity and access/error behavior. No causal relationship is inferred from this sequence.

## Early development scoring

From the repository root, run the offline hand-authored candidates against the four development cases using a new directory:

```sh
uv run --locked python -m evaluation.runner run --output /tmp/trace-s3-evaluation
uv run --locked python -m evaluation.runner rescore --run-dir /tmp/trace-s3-evaluation
```

The [evaluation contract](architecture/development-evaluation.md) defines metrics, expected scores, schemas, artifact isolation and support-review/baseline protocols. Saved runs are exclusive and version/hash checked; input errors exit 2. Successful scoring exits 0 even when candidate fixtures fail checks. Application and evaluator code are included in the documented quality commands. No model usage, actual human review, operator timing or operational acceptance is claimed. Only the operational files under a saved run's `inputs/` may be supplied to an investigator; keep evaluator manifests, candidate fixtures and labels out of its context.

## Curated knowledge ingestion

`uv run --locked python scripts/demo_corpus.py` ingests six development references twice across a SQLite restart and resolves all 18 stable chunks. It runs offline with a fixed synthetic clock and temporary state. The [corpus contract](architecture/knowledge-corpus.md) defines adapters, metadata, chunking, atomic generations, revision/policy updates, revocation and retention, plus the contamination checklist. The historical notes are explicitly fictional development material. Real source permission, freshness and retention remain owner-dependent inputs; the [retrieval contract](architecture/knowledge-retrieval.md) records #16 search and measured development evidence.

## Knowledge search and cached embedding comparison

`uv run --locked python scripts/demo_search.py --query "TLS certificate expiry" --top-k 3` runs the measured lexical default without model packages or weights. Semantic/hybrid modes are explicit and require `--extra semantic` plus the pinned cached model. Follow the [search setup, rebuild and comparison instructions](architecture/knowledge-retrieval.md); missing dependencies/cache fail without fallback. `make integration-semantic` runs a real local model comparison separately from fast CI and the live-provider gate. Model preparation is an explicit public download; search itself reads cached files only. The checked-in development report does not establish held-out quality or pilot usefulness.

## Passage evaluation and context demonstration

`uv run --locked python scripts/demo_context.py --query "PAYMENT_TIMEOUT evidence" --max-passages 1` demonstrates whole-passage omissions and resolvable source mappings. `uv run --locked python -m evaluation.retrieval_quality --modes lexical --output /tmp/trace-passage-review.json` scores 100 evaluator-only development requests without an encoder. Follow the [protocol, review bundle and reproduction instructions](architecture/retrieval-evaluation-context.md) for real-model comparison, model-free rescoring and the owner's pending human review. Acceptance cannot run until those decisions are recorded; the saved thresholds precede measurement.
