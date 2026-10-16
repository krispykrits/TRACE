# Local investigator CLI and saved reports

Issue [#38](https://github.com/krispykrits/TRACE/issues/38) exposes the [bounded investigator](bounded-investigator.md). [ADR 0019](../adr/0019-local-cli-and-saved-report-access.md) records local trust and restoration. This is read-only development/test investigation over an already ingested capture. JSON ingestion for the independent .NET testbed, authenticated operational identities and real-source acceptance remain their separate stories.

## Offline reproduction

After [local setup](../development.md#setup-and-first-run), use a new private directory:

~~~sh
uv run --locked python -m scripts.investigator_fixture --directory /tmp/trace-cli-answer
uv run --locked python -m scripts.investigator_fixture --directory /tmp/trace-cli-insufficient --case c04
uv run --locked python -m scripts.investigator_fixture --directory /tmp/trace-cli-pending --unreviewed
uv run --locked python -m scripts.investigator_fixture --directory /tmp/trace-cli-timeout --failure timeout
~~~

The script prepares real SQLite/corpus/index state and calls the public CLI with an explicitly injected hand-authored provider. It uses a fixed simulation clock (2026-10-12 12:00 UTC). Results declare `offline_test`, `offline_hand_authored_simulation` and `actual_human_review=false`. Fictional support decisions exercise accepted supported/abstained paths; these are not human endorsement or diagnosis-quality evidence. No evaluator labels or credentials are loaded and no paid requests occur. Scripts/tests are excluded from the runtime wheel. The normal executable rejects `--provider offline-fixture`; it cannot import a provider selected by a path or module flag.

Copy the printed investigation ID into subsequent invocations. The script retains its private state for restart/inspection; each invocation uses the same explicit fixture composition:

~~~sh
uv run --locked python -m scripts.investigator_fixture --directory /tmp/trace-cli-answer -- report --investigation-id <id>
uv run --locked python -m scripts.investigator_fixture --directory /tmp/trace-cli-answer -- report --investigation-id <id> --format json --output /tmp/trace-private-report.json
uv run --locked python -m scripts.investigator_fixture --directory /tmp/trace-cli-answer -- report --investigation-id <id> --citation-id <citation-id> --format json
uv run --locked python -m scripts.investigator_fixture --directory /tmp/trace-cli-answer -- investigate --service order --environment test --window-start invalid --window-end invalid --provider offline-fixture
~~~

An insufficient capture is a successful abstention (exit 0). The unreviewed candidate remains pending (exit 7), even when its generated assessment proposes `supported`. Timeout exits 5 with labeled retained evidence and no assessment. Invalid input exits 2 before source/provider access.

## Trusted local configuration

The application reads the absolute `TRACE_INVESTIGATOR_PROFILE` environment path. There is no CLI grant/scope/profile/module-path flag. The profile must be a regular file owned by the current Unix user, mode 0600, at most 1 MB and not a symlink. Place it and its source databases/index/private journals in an owner-controlled directory; keep it outside Git. Query service/environment/window filters narrow access and never become grants. A local user able to rewrite trusted files or application composition is trusted; this is not operational authentication or protection from that OS user.

Profile schema `local-investigator.v1` has these required fields:

| Field | Meaning |
| --- | --- |
| `principal_id`, `clearance`, `expires_at` | Trusted actor, maximum original input sensitivity (`public`, `internal`, `restricted`) and UTC grant/retention deadline |
| `evidence_db`, `corpus_db`, `index_root` | Absolute configured local source/state paths |
| `source_investigation_id` | Existing ingested capture; its access scope, environment, service and expiry are checked independently |
| `evidence_scope` | `access_scope`, `environment`, `allowed_services` for dependency evidence, independently of the requested subject |
| `knowledge_scope` | `access_scope`, `environment`, `allowed_services`, `evaluation_role`, `valid_at`, under the existing corpus policy |
| `execution_policy` | Explicit fields from `ExecutionPolicy`, with finite validated defaults for omitted fields; see [budgets](investigation-budgets.md) |
| `grants` | Per-citation exact-content approvals described below; no default grants |
| `reviews` | Independent current, scoped support decisions described below; an empty list means unreviewed |
| `azure` | Required only for a new Azure run: absolute `setup_path`, `secrets_path`, `journal_path`, explicit `monthly_limit_nusd` and `initial_spend_nusd` |

Each `grants[citation_id]` records `source_id`, `revision`, `kind`, `content_sha256`, `sensitivity`, boolean `access_allowed`, `transmission_allowed`, `source_owner_allowed`, `identifiers_reviewed`, `fields_reviewed`, and `expires_at`. Hash the canonical UTF-8 `source_content` projection defined in the [workflow contract](bounded-investigator.md#application-contract-and-composition); a hash is a content binding, never permission by itself. The local adapter resolves originals from the configured capture and current corpus/index, then compares the separately approved hash/revision/classification. Current storage uses synthetic operational evidence (`kind=synthetic`); corpus references use `internal_runbook`. Do not use this adapter to relabel real telemetry as synthetic. Source/field grants for real .NET JSON exports remain #73.

The generated fixture profile is an executable example of this structure with **fictional** grants; it is not a template authorizing real sources or Azure transmission. Do not change its simulation flags to claim actual support. For each real local capture the owner must independently prepare reviewed fields, classification, expiry, exact content approvals and source-owner transmission permission. Missing policy fails closed.

A `reviews` row contains `principal_id`, `investigation_id` and `decision`. The decision uses the existing `SupportDecision` fields: `binding_id`, `claim_id`, `verdict`, `reviewer_id`, `rationale`, `kind=human_review`, `rubric_version=trace-claim-support.v1`. Trusted review infrastructure supplies these, not model text. Accepted saved results recheck all persisted claim/outcome bindings against current records after restart. Removing, disputing or withdrawing support blocks accepted content. Pending packets remain pending; adding decisions does not silently promote an immutable saved outcome or execute any action. A reviewer workflow/promotion interface is not included.

Profile identity, paths, scope or clearance changes during one operation deny it. Every source/review read reloads current grant records. Source revisions/content, field review/classification, withdrawals, corpus freshness/retention, profile/source expiry, grants and original actor bindings remain current checks. Source objects and exact projections must still be available; a stored report does not replace its dependencies.

## Normal invocation and live opt-in

With an independently prepared private profile and already ingested development/test capture:

~~~sh
export TRACE_INVESTIGATOR_PROFILE=/absolute/private/investigator.json
uv run --locked trace-app investigate --service order --environment test --window-start <utc-start> --window-end <utc-end> --provider evidence-only
uv run --locked trace-app report --investigation-id <id>
~~~

Only separately authorized live work should select Azure:

~~~sh
TRACE_ALLOW_PAID_LIVE=1 uv run --locked trace-app investigate --service order --environment test --window-start <utc-start> --window-end <utc-end> --provider azure
~~~

This command is documented, not executed as part of #38. The task does not authorize a paid investigation. Before invoking it, supply [provider setup/credentials](model-provider.md), known existing spending, the explicit monthly cap (at most $20), finite execution limits, reviewed source/transmission/retention permissions and the exact authorized run scope. No missing provider, dependency or permission falls back to a fixture. Azure assessments without independent support decisions are pending. Cloud deployment and hosted identity remain separate gates.

The incident window must be UTC, ordered, at most 24 hours and inside the configured capture. Production is rejected before provider calls because the existing local job/provider contracts support development/test. New jobs receive a scoped deterministic submission key from normalized service/environment/window and permit one attempt. Provider selection does not change that key. Repeating a request returns its stored state and original configuration, including failed, cancelled, running or pending state, without another dispatch. A different capture/job key or manual database edit is not a reconciliation workflow and must not be used to retry an uncertain paid call.

`trace-app cancel-investigation --investigation-id <id>` durably cancels a queued/running job. SIGINT/SIGTERM follow cancellation handling; the workflow retains already gathered evidence and labels its attempt cancelled. Hard termination leaves a durable running/possibly dispatched attempt; repeat invocation only inspects it. An expired lease/unknown remote outcome is not retried by this command. Cancellation cannot prove that a remote provider stopped or avoided charges; outstanding spending/admission records remain conservative until reconciliation.

## Output and disclosure

`investigation-cli.v2` includes investigation ID, execution/assessment/validation states, failure code, provider/configuration and configuration/workflow versions, sensitivity, deterministic observed timeline, assessment observations/hypotheses/alternatives/gaps/uncertainty/abstention/next check, authorized citation mappings, labeled artifact/attempt records and usage availability. `usage` describes the final response only; aggregate and unknown-call records remain in the private execution journal. Missing usage is unknown, not zero. Text JSON-quotes untrusted prose to avoid terminal escape execution.

`report --artifact-id <id>` inspects a retained evidence artifact through the same current access checks. It returns timeline/provenance descriptors rather than raw payloads or arbitrary files. Version 2 delivers every captured authorized event independently of the admitted model subset, with its original evidence record and noncausal status. `timeline_capture` carries query, source availability, matching count and truncation; completeness refers to the captured window and does not imply unavailable sources were observed. `model_context_omissions` preserves model exclusions. The assessment’s `timeline_evidence_ids` and `citations` remain restricted to admitted references; timeline membership does not grant model citation or transmission permission. New private publications use `investigation-result.v2`; older publications without a captured timeline explicitly report capture status `unavailable` rather than reconstructing completeness from citations. Report sensitivity is the maximum of all contributing evidence and model-response bindings. `--citation-id <id>` resolves a report's authorized admitted/redacted citation mapping. A report/artifact/citation ID and a file path never supply grants. Ground truth, credentials, raw prompts, unredacted gathered payloads, private dependency fingerprints and support decision rationale are excluded from delivery.

Text display checks local read rights. **All `--format json` output, including stdout and citation resolution, is an export** and additionally checks current transmission/source-owner permission. A summary retains original input sensitivity. Every contributing package input and every original model dependency is revalidated, including admitted inputs omitted from prose/history. Accepted results also require current support. After review reads, sources are checked again. A narrower clearance, different actor, revoked input or missing dependency denies content with a fixed content-free error and no body.

`--output` requires JSON and exclusively creates a new mode-0600 file, refusing overwrite and symlinks. Existing bytes remain intact on failure. Destinations and already exported dictionaries/files are under the authorized local user's control; exports are not retroactively erased by later revocation. Copying beyond the permitted audience/retention is not granted. This implementation does not authenticate a remote audience, declassify content or implement backup deletion.

Older artifacts without durable dependency bindings remain metadata-only through the old internal API and cannot be restored through the CLI. Do not regenerate bindings from their current scope or silently rerun a historical paid investigation. No database schema migration is required for the new private metadata.

| Exit | Outcome |
| --- | --- |
| 0 | Completed accepted assessment (including abstention), deliberate evidence-only result or authorized citation resolution |
| 2 | Invalid request/configuration, unavailable explicitly selected fixture, missing paid opt-in |
| 3 | Dependency/audit/model failure or export file creation failure |
| 4 | Denied disclosure, source/transmission/classification/retention/citation/support failure; no content |
| 5 | Model timeout or execution expiry/deadline |
| 6 | Running/queued/stopped or conflicting current execution; no paid replay |
| 7 | Completed execution with candidate awaiting independent support |
| 130 | Interrupted/durably cancelled investigation |

If content is denied, exit 4 takes precedence over the investigation's execution outcome. Correlated logs retain identifiers/fixed outcomes and no report or exception text. Inspection/export does not invoke tools or models after terminal state. Tests exercise real child processes with deterministic adapters, not paid/live verification. #39 owns actual-output scoring; S6, operational usefulness, cloud and production-remediation acceptance remain separate.
