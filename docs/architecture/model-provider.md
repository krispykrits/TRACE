# Model-provider contract and offline execution

Scoped offline subtask [#50](https://github.com/krispykrits/TRACE/issues/50) of roadmap story [#34](https://github.com/krispykrits/TRACE/issues/34). [ADR 0012](../adr/0012-model-provider-contract-and-bounded-call.md) proposes this boundary for owner review. The owner selected **Azure AI Foundry, GPT-6 Luna and a $20/month model spending cap** on 2026-10-13 and reports an existing model deployment. Actual deployment configuration/access and hosted adapter/live acceptance remain open; #34 is not complete. The accepted Sprint 4 gate is #19 / merged PR #49 at `a9db329`.

The cap applies to TRACE model usage, including live contract checks and model-backed evaluation. The current offline boundary does not enforce a monthly monetary cap. #36 owns execution/usage/cost controls; actual deployment pricing, account restrictions, monthly accounting and spend enforcement must be settled before paid runs. The selected model is `gpt-6-luna`; its deployed version and deployment name must be confirmed from the owner's resource. Model selection does not establish permitted prompt transmission/retention.

## Recommended initial prompt policy — pending owner confirmation

Use **synthetic TRACE development data only** for initial live checks and the Local MVP. Send one bounded incident packet containing service/environment/window, selected synthetic log/metric/deployment observations, event and collection timestamps, evidence IDs/provenance, explicit source gaps, and a small set of relevant development-runbook excerpts with citation/revision metadata. Supply TRACE-owned workflow instructions and the output schema separately from untrusted evidence text.

Exclude secrets/credentials, personal/customer/payment data, real operational telemetry, unrelated source content, full repository/database exports, evaluator labels/ground truth/expected reports and held-out answer-bearing material. For later operational replay, obtain the source owner's permission and approve sanitization/data-handling separately under the Operational Pilot gates. The current recommendation is not a grant to transmit either synthetic or operational prompts.

Prefer synchronous, stateless Responses calls with `store=false`, no provider file/vector-store uploads and no raw prompt/response content in TRACE logs/default evaluation metadata. Persist only deliberately validated/redacted assessments and authorized citation mappings under TRACE's scope. These are proposed adapter requirements; they are not implemented by the offline process contract.

Microsoft documents stateless Responses mode with `store=false`; it does not establish absence of all service-side processing/storage. The standard abuse-monitoring process can store flagged prompts/completions for human review. Global deployments can process prompts outside the resource's geography; Data Zone deployments constrain processing to the selected zone. Confirm the deployment type and applicable monitoring settings before the live check. Sources: [Responses API](https://learn.microsoft.com/en-us/azure/foundry/openai/how-to/responses), [Foundry data privacy](https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/openai/data-privacy).

## Deployment details needed from the owner

| Detail | Purpose |
| --- | --- |
| Exact deployment name and deployed model version | Azure's API uses the deployment name for `model`; separately record GPT-6 Luna's actual version for reproducibility |
| Resource inference endpoint from the deployment's consume/code view | Identify the Azure OpenAI/Foundry resource API endpoint, distinct from a portal/project URL |
| Resource region and deployment type (Global Standard, Data Zone Standard or other) | Determine processing-location and pricing constraints |
| Authentication method: Microsoft Entra ID or API key | Prefer Entra ID for local development; confirm the invoking identity has `Cognitive Services OpenAI User` or an appropriate equivalent role |
| Network access: public endpoint, selected networks or private endpoint | Establish whether this WSL environment can reach the deployment; no network relaxation is implied |
| Available token/request quota and additional account restrictions, if known | Configure bounded calls against the actual deployment |
| Confirmation of the initial synthetic-only prompt/retention policy above | Resolve #34's transmission/retention gate without granting operational-source access |

Share nonsecret configuration only. Keep API keys/access tokens/passwords/client secrets in a local secret source; no secret value is needed in chat, GitHub or repository documents. Subscription/resource-group identifiers are only needed later if an authorized resource-management or role diagnostic requires them. For Azure OpenAI v1, common resource endpoints end in `/openai/v1/` and the API supports Entra ID or keys; see [Microsoft's v1 setup](https://learn.microsoft.com/en-us/azure/foundry/openai/api-version-lifecycle).

## Contract and placement

`investigation.provider` owns `model-provider.v1`, configuration, requests, structured results, usage and error categories. It imports only the standard library. `adapters.models.process` runs one explicitly supplied `ModelTransport` in a spawned worker. `bootstrap.create_model_provider` composes it without a default transport. Only `tests/fixtures/model_provider.py` contains the deterministic fake; it requires explicit `offline_test` selection and is excluded from the runtime wheel.

| Contract | Fields and behavior |
| --- | --- |
| Configuration | Provider, model, configuration and adapter identifiers; explicit live/offline mode; JSON-object response format; automatic retries fixed at zero |
| Request | Contract/request/prompt/response-schema identifiers, separate instructions and untrusted source context, and explicit per-call bounds |
| Reply/result | Validated JSON object, optional provider operation ID, usage availability; model JSON is not yet an accepted assessment |
| Usage | Input/output token counts may independently be null; availability is available, partial or unavailable; missing measurements never become zero |
| Error | Configuration, missing credentials, unavailable model, unsupported capability, authentication, rate limit, deadline, dependency, malformed output or output limit; public messages are fixed and content-free |

`ModelConfiguration.from_dict` rejects missing/unknown fields, invalid identifiers, unsupported format/mode and automatic retries. Configuration and source text are separate; source text cannot select a provider, supply credentials or change execution bounds. `validate_model_readiness` compares the selected configuration with an adapter's declared model/capability/version support and credential presence. It returns **offline_test_only** or **live_check_required**. Local compatibility and credential presence do not establish valid credentials, current remote model access or live readiness; a real adapter and opted-in invocation must prove those separately.

There is no provider environment-variable/CLI loader yet. Callers supply validated configuration through trusted composition. Existing `trace-app check-config` precedence (defaults, .env, process environment, CLI) remains limited to environment/log settings and cannot report model readiness. #34's provider decision will define vendor credentials, configuration precedence and permitted handling; no generic credential value is serialized into configuration or metadata.

## Bounds and outcomes

Every request supplies `timeout_ms`, `max_response_bytes` and `max_output_tokens`; there are no default model budgets. Supported hard implementation ceilings are 600,000 ms, 1,000,000 response bytes and 100,000 output tokens. Instructions and source context each have a 131,072-byte UTF-8 ceiling. These are safety ceilings, not approved spending, quality or operational performance thresholds.

The worker receives the configured output-token limit through the request; a concrete transport must also enforce the selected provider's native limit and disable all SDK retries. The parent invokes it once and never retries or substitutes another provider/model. Startup, response receipt and validation count toward the monotonic deadline; a watchdog also terminates a stalled partial IPC response, and timeout stops and joins the local worker. Output byte/token excess and provider-reported truncation fail explicitly. Missing usage stays unknown, so a concrete adapter's native token cap is still required. Stopping a local worker does not prove that a remote paid request was cancelled; #36/#37 must preserve uncertain outcomes and prevent implicit paid-call replay.

Only complete UTF-8 JSON objects are accepted. Unknown finish reasons, malformed JSON, duplicate keys, nonfinite/overflowing numbers, invalid Unicode, nesting deeper than 32 and more than 10,000 JSON nodes are rejected. The worker validates before transmitting; the parent bounds the IPC envelope and validates again. An oversized response is rejected after transport return; this implementation does not provide a streaming response reader or a general memory/OS sandbox. Concrete transports remain trusted code and must be spawn-serializable and comply with their bounded network-read contract.

Receiving structured JSON does not validate the assessment schema, citation permissions or claim support. Those remain #35. Investigation-wide call/retry/token/spending policy, persistent attempt ownership and usage/cost accounting remain #36/#37. No tool loop, investigation runner or remediation authority is added here.

## Content handling and logging

Prompts/responses are retained only in application memory for the call/result; request/reply/result representations omit raw content. Their default `metadata()` exports contain identifiers, configuration, outcome and explicit usage/operation availability, with no prompt, source context or structured response. The application must deliberately extract `structured_response()` and apply #35 validation before report retention. Model JSON can still contain sensitive source content; it is not automatically an approved artifact.

The process adapter emits one correlated `models.call.completed` record with public request/configuration identifiers, outcome and measured elapsed time. Worker stdout/stderr are discarded and worker logging is disabled before transport execution. SDK exception text never travels to the parent. Errors use fixed categories/messages; credentials belong only in the selected trusted transport, not public configuration. The boundary does not grant transmission or retention permission and does not establish hosted CloudWatch delivery.

Import checks prohibit model adapters from source/storage/tool adapters, evidence/knowledge packages, investigation tools/state/bundle modules, demos and evaluators. They can use only the model contract and runtime utilities within TRACE. These checks guide dependency direction; they do not remove the process's OS credentials or network authority.

## Reproduction and acceptance limits

From the locked Linux/Python 3.12 environment, run:

```sh
uv run --locked python -m unittest tests.contracts.test_model_provider tests.integration.test_model_provider -v
make check lint format-check type-check architecture-check test integration package-check
```

The test-only adapter demonstrates structured output and content-free metadata, missing-credential/model/capability failures, explicit unavailable/partial usage, one attempt on authentication/rate-limit/dependency failure, killed-worker timeout, malformed/oversized/truncated response rejection and source-text/configuration separation. Negative architecture cases and the installed-wheel gate protect evaluator/fake exclusion. These are contract and actual local-process checks, not diagnostic-quality or live-model evidence.

`make integration-live` remains fail-closed because no real provider test is configured. It must not pass on these fixtures. Azure AI Foundry, GPT-6 Luna and the $20/month model cap are recorded; to complete #34, obtain deployment name/version, account/region/endpoint and restrictions, authorized authentication, confirmed prompt transmission/retention policy and spend controls for the live check. Implement the selected adapter with its documented credential/configuration setup and any justified locked dependency; then add a separate explicitly opted-in live check that records actual model/configuration, operation and usage availability, bounded response and outcome. No paid call or live acceptance is authorized by the offline tests. Operational Pilot and real production remediation retain their independent gates.
