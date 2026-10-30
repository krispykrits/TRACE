# Azure model connector and provider policy

Roadmap story [#34](https://github.com/krispykrits/TRACE/issues/34), implementation subtask [#50](https://github.com/krispykrits/TRACE/issues/50), merged in [PR #51](https://github.com/krispykrits/TRACE/pull/51). [ADR 0012](../adr/0012-model-provider-contract-and-bounded-call.md) records the boundary and tradeoffs. The owner selected Azure AI Foundry / GPT-6 Luna, deployment `gpt-6-luna`, a $20/month model cap and resource API-key authentication after Entra sign-in returned 53003. Resource-specific configuration and credentials remain private. The implemented connector, deterministic policy checks and opted-in synthetic live result are described below; owner closure of #34 accepts the Local MVP synthetic provider scope; operational-use gates remain separate.

## Owner-approved transmission policy — 2026-10-13

The owner supplied this policy. It grants no access or transmission permission for a named operational source.

| Data type | Approved TRACE policy |
| --- | --- |
| Synthetic incident evidence | Allow fixture logs, metrics, traces, deployments and runbooks. Exclude evaluation answer keys. |
| Operational metadata | Allow scoped timestamps, error codes, latency, deployment versions and necessary correlation identifiers. Review identifiers for sensitivity. |
| Logs, traces and stack traces | Allow selected excerpts after removing secrets, personal information and unnecessary request/response bodies. |
| Internal runbooks, configuration and source code | Allow relevant excerpts when the source owner authorizes sending them to Azure. Repository access alone does not establish transmission permission. |
| Customer or employee data | Block by default: names, emails, customer records and identifying payloads. Any exception needs an approved purpose and handling policy. |
| Secrets and credentials | Never put passwords, API keys, tokens, cookies, private keys or credential-bearing URLs into model context. Provider credentials belong in transport authentication. |
| Evaluation ground truth | Never include expected root causes, hidden labels or reference answers in investigation prompts—even for synthetic cases. |

## Required production enforcement — 2026-10-13

The owner requires these controls before every provider request, including later tool results, under `trace-provider-data-policy.v1`:

1. Check source access **and** permission to transmit the content.
2. Select bounded evidence, redact sensitive fields and reject unresolved policy violations.
3. Preserve citation IDs and record redaction provenance locally.
4. Log content-free metadata—policy version, evidence IDs, model/deployment, usage and outcome—without raw prompts or responses.
5. Treat retrieved text as untrusted evidence and protect generated responses according to the sensitivity of their inputs.

`investigation.provider_policy.PolicyModelProvider` is the application entry point. A `ProviderCall` contains registered prompt IDs, evidence ID/revision/field selections, explicit bounds and optional previously protected responses. It accepts no caller-provided evidence text or permission flags. A separately composed `EvidenceAuthority` resolves current content, reviewed field classifications, source access and Azure transmission grants for a trusted `ProviderScope`. Missing, denied, expired or unreviewed grants fail closed. Internal runbooks/configuration/code additionally require source-owner permission. Customer/employee/evaluator sources are blocked; no exception or declassification path is implemented.

Selected scalar fields are bounded before dispatch. Secret/restricted fields are withheld; known credentials, emails, credential URLs, bearer credentials and complete private keys are redacted. Credential assignments cause the whole selected excerpt to be withheld, including quoted values and multi-value cookies. Unknown/unreviewed classifications, evaluator labels, incomplete private-key material, missing fields and unresolved violations are rejected. Pattern matching cannot establish that arbitrary prose is free of all personal data or secrets: source-side field review/classification is mandatory. Citation IDs and source revisions stay intact. The private ledger records policy/source/revision/evidence/field identifiers and transformation reasons, never removed values.

After writing provenance and reserving spending, the application resolves the dependencies again, rejecting changed content/classification or revoked access/transmission grants before dispatch. A short-lived HMAC receipt binds the full prepared request, scope, policy, evidence IDs, sensitivity and bounds. Both the process provider and Azure transport require it; the transport checks it again after TLS connection setup. Unsigned, changed and expired requests produce zero HTTP requests. Expiry and dispatch-time checks do not provide instantaneous distributed revocation during an in-flight remote call.

Every later selection or prior response passes admission again. Protected responses inherit the most sensitive contributing input **before redaction**. Content reads require the issuing scope and current source access; exports and later provider reuse also recheck transmission permission and content revisions. Forged/cloned response handles, changed content/classification and revoked grants are rejected. Returned JSON is scanned for unsafe credential/evaluator fields and known sensitive text before release; it is an intermediate response, not an accepted assessment. #35 validates claim support and citations; #37 routes each workflow call through this interface; the [#38 local CLI](investigator-cli.md) preserves these checks across saved display/export.

These boundaries assume trusted application composition and a controlled filesystem. They do not authenticate an operator, derive real-source permissions, or sandbox arbitrary Python. No production authority is inferred from repository access. Operational source adapters must supply independently derived grants rather than forwarding caller claims. No operational source is currently authorized by this implementation.

## Private provider configuration

The owner has supplied the project/inference endpoints, deployment name, model version, region and deployment type. Actual addresses are in Git-ignored `.env.provider-setup.local`; the API key is separately in `.env.provider-secrets.local`. Both must be private (mode 0600). Project URLs ending in `/api/projects/<project>` are not model API bases. Accepted inference bases are HTTPS Azure resource hosts ending in `/openai/v1/`, with no embedded credentials, query, fragment or alternate port. [Microsoft v1 endpoint and authentication documentation](https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle).

`bootstrap.create_azure_model_provider_from_files` reads explicitly supplied setup/secret files without shell evaluation, process-environment fallback or implicit sign-in. The setup record uses:

```dotenv
AZURE_OPENAI_BASE_URL=https://<resource>.services.ai.azure.com/openai/v1/
AZURE_OPENAI_DEPLOYMENT=gpt-6-luna
AZURE_OPENAI_MODEL_ID=gpt-6-luna
AZURE_OPENAI_MODEL_VERSION=<deployed-version>
AZURE_OPENAI_CONFIGURATION_ID=azure-luna-config.v1
AZURE_OPENAI_DEPLOYMENT_TYPE=GlobalStandard
AZURE_OPENAI_AUTH_METHOD=api_key
```

`MODEL_ID` and `CONFIGURATION_ID` have the displayed defaults; other fields are required. The secret file contains `AZURE_OPENAI_API_KEY=<private value>`. Never share the value in chat, GitHub, source or diagnostics. This adapter supports the selected Luna/Global Standard pricing contract only; incompatible settings fail explicitly. `trace-app check-config` still covers environment/log configuration, not provider readiness. The composition function additionally requires a trusted scope, independent evidence authority, registered prompt catalog, shared private journal path, approved monthly allowance and initial known spending estimate. There is no implicit fake/source authority or automatic Entra fallback.

The recorded October 13 local sign-in attempt returned 53003, and the owner authorized the API-key path used for that check. This is historical check evidence, not a current account-health diagnosis. TRACE has not verified the future AKS pod token path; #58 owns that acceptance under the account's authorized identity/flow restrictions. No Conditional Access or Azure authentication setting was modified. [Microsoft Conditional Access troubleshooting](https://learn.microsoft.com/en-us/entra/identity/conditional-access/troubleshoot-conditional-access).

Applicable operational credential ownership/rotation, network/quota/account restrictions, source rights, provider processing/retention, authenticated grant derivation and audit retention/deletion remain owner-dependent production/pilot gates. `store=false` does not establish zero provider retention or resource-local processing. Review [Foundry data privacy](https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/openai/data-privacy) before real-data use.

## Contract, transport and bounds

`investigation.provider` owns `model-provider.v1`, strict configuration, requests/results, nullable usage and content-free error categories. Selected deployment/version and provider-reported model are separate metadata. Local readiness is `offline_test_only` or `live_check_required`; credential presence is not valid authentication. Offline fakes and source authorities exist only in tests and are excluded from the wheel.

`adapters.models.azure.AzureResponsesTransport` uses the standard-library HTTPS client and verified TLS, with one stateless `POST /responses`. The API key appears only in authentication headers. The payload selects the deployment, separate trusted instructions, the admitted text input, JSON-object format, native `max_output_tokens`, `store=false` and disabled truncation. JSON mode requires the JSON format marker in context; TRACE's admitted envelope includes it. There are no uploads, remote history, tools, streaming, redirects or automatic retries. [Azure Responses API](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/responses), [OpenAI JSON-mode requirements](https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses).

Each call requires `timeout_ms`, `max_response_bytes` and `max_output_tokens`. Core safety ceilings are 600,000 ms, 1,000,000 response bytes and 100,000 output tokens; Azure's native minimum is 16 output tokens. Default policy ceilings are 32 source dependencies and 65,536 context bytes; overflow is rejected. These are implementation limits, not approved diagnostic/performance targets.

`adapters.models.process` enforces a monotonic deadline across startup, transport, IPC and validation; a stalled partial IPC response is terminated and the worker reaped. The Azure reader bounds the full native response envelope. Both process sides validate complete UTF-8 JSON objects, duplicate keys, nonfinite numbers, depth/node limits, output bounds and completion. Unsupported native tool outputs/refusals/incomplete responses fail explicitly. Known usage survives output rejection. Missing usage stays null. Raw errors, worker stdout/stderr and worker logs are suppressed. HTTP failures retain only allowlisted status/code/parameter metadata; never Azure's raw error message/body.

Stopping the local worker cannot prove remote cancellation or absence of charges. No fallback provider, fake or fabricated assessment replaces failure. The implementation is not an OS/memory sandbox or a streaming reader. Import checks keep network execution in adapters and model adapters away from source/storage/tool handles; only model/policy contracts and runtime utilities are available to them within TRACE.

## Audit and the $20 monthly allowance

`adapters.models.journal.SqliteProviderJournal` uses a shared private mode-0600 SQLite file. An immediate transaction reserves a conservative allowance and persists redaction provenance **before** dispatch. Every attempt, including policy/budget/dependency failure, records approved identifiers, policy/configuration/deployment/version, evidence IDs, input sensitivity, elapsed time, numeric usage availability and outcome. Successful native model/operation metadata is recorded when available. No raw prompt, source text, response or removed sensitive value is stored. `models.policy.completed` emits content-free correlated JSON; exact numeric token metrics survive logging redaction while credential tokens remain masked. Local audit failure blocks dispatch or withholds the response. Azure Monitor hosted delivery remains a separate #59 acceptance gate; #3's historical CloudWatch requirement is superseded.

For a future explicitly composed comparison, the journal also accepts a SHA-256 run identifier and a run allowance together. All calls composed with the same run identifier share the allowance, using the same SQLite transaction as the monthly reservation. A retained reservation or uncertain dispatched outcome blocks further calls in that run, including calls for other investigations. The run identifier is fixed to one allowance and UTC month; changing either is rejected. A denied call before dispatch releases its scoped reservation. This is an accounting primitive: the caller must bind the identifier to the approved run and ensure **every** model arm uses it. It does not authenticate approvals, account for spending outside this journal or implement the #87 live comparison runner.

The versioned `azure-luna-global-ceiling-2026-09-22.v1` snapshot reserves 250 nanodollars/input token and 750/output token ($0.25/$0.75 per million), using the published long-context cached-write input/output ceiling and no cache discount. Input allowance is admitted UTF-8 byte length plus a conservative 1,024-token framing allowance; output uses the native cap. Known complete usage reconciles an **estimate**; partial/missing usage retains the whole reservation. Pricing changes require explicit journal configuration review. [Microsoft's published Luna pricing](https://azure.microsoft.com/en-us/blog/gpt-6-astra-sol-and-luna-for-production-agents-in-microsoft-foundry/).

The caller supplies an allowance no greater than $20 and the initial known spending estimate; no default zero-spend assumption is made. All TRACE processes must share one journal. Pending/crashed, timed-out and uncertain dependency attempts block same-scope replay; there is no automatic reconciliation/retry. A failure before dispatch refunds the reservation. Estimates, reservations and provider billing are distinct. Deleting/switching journals, external calls, taxes or other account spending are not an Azure account-wide hard cap. The [#36 shared execution policy](investigation-budgets.md) adds investigation-wide model/tool/retry/correction/token bounds and current durable job checks; #37 composes the bounded workflow and prevents implicit paid replay. Standalone explicitly authorized connector diagnostics retain their per-call and monthly bounds without creating an investigator run.

## Reproduction and live evidence

Fast checks use no credentials or paid calls:

```sh
make check lint format-check type-check architecture-check test integration package-check
```

The real check is `tests/live/test_azure_provider.py`, with an explicit test-only authority for one owner-authorized synthetic observation. Missing opt-in, missing/empty suites or skipped tests cannot pass the gate. Before a deliberately authorized invocation, provide these nonsecret path/accounting inputs:

```sh
TRACE_ALLOW_PAID_LIVE=1 \
TRACE_AZURE_SETUP_PATH=.env.provider-setup.local \
TRACE_AZURE_SECRETS_PATH=.env.provider-secrets.local \
TRACE_PROVIDER_JOURNAL_PATH=.env.provider-journal.local \
TRACE_PROVIDER_REPORT_PATH=.env.provider-live-result.local \
TRACE_INITIAL_SPEND_NUSD=<known-current-month-estimate> \
make integration-live
```

The key is never sourced into the shell. Keep the journal and metadata report private/Git-ignored. Supply the real known initial estimate when creating a journal; repeated construction never reseeds/reset its balance. Do not copy a historical report or fixture result as live verification. The manual GitHub workflow remains unconfigured for private source files/budget ownership and cannot substitute for a local live result.

On **2026-10-13**, the actual TRACE connector/policy/process/journal live check passed with a preserved synthetic citation, complete valid JSON, **143 input / 90 output tokens**, and **2,400 ms** elapsed. It used a 30-second deadline, 256-output-token cap, 65,536-byte response bound, `store=false` and one attempt with zero automatic retries. The response named `gpt-6-luna` without a dated version; that version remains owner-reported. Metadata is in private `.env.provider-live-result.local` and the audit journal, never raw content.

Three preceding configuration-rejected connector checks were preserved; the last identified the JSON-mode input requirement. Their usage was unavailable and their reservations remain charged conservatively. Including the prior direct 23-input/24-output smoke estimate, the private ledger reserves/estimates **$0.00190975** for known TRACE checks; this is not an Azure invoice. No further paid check runs automatically. The synthetic result verifies this connector's native contract; deterministic negative/bypass tests verify the policy behavior. Neither proves operational-source permissions, diagnostic quality, Operational Pilot usefulness, Cloud MVP or production remediation acceptance.

## Assessment and workflow consumers

[Story #35](validated-assessments.md) adds strict v2 assessment validation and scoped support-review packets. Protected responses now retain their exact admitted citation projections and value-free redaction provenance, including later history, accessible only after fresh source checks. Assessment acceptance/read/export preserves those dependencies and original sensitivity; model text or a valid citation ID cannot supply human support or declassification. Runtime review/inspection/persistence remains scoped as documented in ADR 0013 and #38.

The budget session records configured model/version/deployment separately from nullable `reported_model` and provider operation ID. A bare reported model name cannot independently confirm the owner-reported dated version. Sensitive provider metadata is withheld while retaining numeric usage. Both private ledgers share the call ID and versioned pricing snapshot; a late cancellation/expiry updates the spending outcome as well as the execution record.

The [#37 investigator](bounded-investigator.md) repeats admission on refinement/correction with complete protected history and independently current new-source grants. A closed `InvestigationFrame` supplies deterministic metadata only; source/model text cannot select a provider, grant or budget. Explicit `offline_test` composition uses the same policy for simulations; Azure remains live with no fallback. This mode permits no operational readiness or actual-provider claims. Stored structured outcomes preserve input-derived sensitivity and local provenance; content-free metadata and #38 restoration rights remain separate.

## Azure AKS cloud follow-up — 2026-10-14

[ADR 0015](../adr/0015-azure-aks-cloud-deployment.md) replaces the cloud hosting target. #58 must implement/verify pod Entra Workload Identity and the native token credential path under account restrictions; local API-key fallback remains the currently accepted connector behavior, not cloud keyless acceptance. #57 must migrate the provider journal/spending and execution state into shared transactional storage so concurrent pods/restarts cannot each admit another $20 allowance. Keep policy/current grants, protected outputs/review/citations, conservative unknown-usage reservations and content-free audit throughout that migration. No model/source permission or paid request is expanded by the architecture update.
