# ADR 0012: Provider-neutral model contract and bounded call boundary

- **Status:** Process boundary proposed for owner review in [PR #51](https://github.com/krispykrits/TRACE/pull/51); owner-selected Azure AI Foundry and $20/month model cap; exact model/deployment and live acceptance pending
- **Date:** 2026-10-13 (America/New_York)
- **Owner:** Project owner
- **Scope:** Offline model contracts and one-call execution; recorded provider/spending direction, with hosted adapter implementation pending

## Owner decision — 2026-10-13

The owner stated: “Will use Azure AI foundry; will limit to $20 a month.” Record Azure AI Foundry as the selected provider platform and $20/month as TRACE's model spending cap. This resolves provider-platform selection and the numeric model budget; it does not accept the proposed process boundary or complete #34.

Exact model/deployment/version, subscription/account restrictions, region/endpoint, authentication and permitted prompt transmission/retention remain open. Model selection and adapter design must fit this cap and the required structured-response/output-bound contract. Monthly accounting and enforcement are not implemented by this offline work; #36 owns usage/cost controls. The model cap includes TRACE live checks/evaluation and does not settle the independent AWS budget. No resource provisioning, prompt transmission or live acceptance is evidenced by this decision.

## Context

The owner accepted Sprint 4 through merged #19 / PR #49. #34 is the next Ready roadmap story and explicitly allows contract/offline tests while provider spending/account/data-handling decisions are pending. Core investigation code needs reproducible identities, structured responses, explicit usage absence and safe failures without binding to a vendor or gaining source/tool authority. A timeout hint alone cannot stop a stalled synchronous call.

## Proposed decision

Put `model-provider.v1` and `ModelProvider`/`ModelTransport` ports in `investigation.provider`. Keep configuration, prompt/source text, output bounds, result metadata and error categories explicit. Permit no automatic SDK retry or alternate-provider/model fallback. Local readiness is preflight, not live acceptance. Treat JSON as an untrusted intermediate response; #35 separately owns assessment/citation validation.

Implement `adapters/models/process.py` as a spawned, killable one-call boundary selected through bootstrap. Validate JSON and bounds on both sides; discard worker output/logs and publish only fixed failures plus correlated metadata. Actual remote cancellation/cost is not inferred from local timeout. Model transports receive request text, not source or tool handles; update ADR 0010, the package guide, import checker/negative cases and installed-wheel requirements together.

Keep the explicitly selected deterministic transport under tests only. Do not choose a hosted provider, add a vendor SDK, define credential/environment setup or claim live readiness without the owner inputs. Track this reviewable work as #50 so merging it cannot complete parent #34 prematurely. No dependency/lock change is required for this standard-library implementation.

## Alternatives and tradeoffs

At initial contract implementation, a concrete vendor SDK would have prematurely selected an owner-gated provider and added unapproved dependencies. Azure AI Foundry is now selected; its exact model/API/SDK choice remains a subsequent design step. A port without any execution boundary would leave deadline enforcement unproven. Running synchronous calls in threads would permit stalled calls to continue after timeout. Spawned processes add startup/serialization overhead and require a serializable transport; they permit local termination and keep raw third-party failures out of parent logs. This is not a general process/network sandbox, streaming reader or complete investigation budget policy.

## Verification and revisit conditions

Credential-free tests cover strict readiness/configuration, explicit offline selection, structured/usage contracts, raw-content isolation, fixed error propagation, single attempts, actual timeout termination and output rejection. Architecture negatives reject source/tool/storage/evaluator access; installed-wheel checks include nested model modules and exclude test fixtures. Run all required repository quality gates before PR handoff.

Extend this ADR for the Azure AI Foundry model/deployment/API choice within the $20/month cap after remaining account/access/transmission/retention inputs: compare concrete models, justify and lock any SDK, prove native token bounds and disabled SDK retries, document credential/configuration precedence, and record a real opted-in contract check. Revisit the provider direction if a demonstrated access, cost or capability constraint requires an owner decision. Revisit process selection if measured startup overhead or a selected SDK's initialization/serialization requirements make it unsuitable. Revisit bounded streaming for a demonstrated workload gap. #36 owns total execution/usage/cost policy; #37 owns durable attempts and uncertain-call recovery. No model/Operational Pilot/Cloud MVP or remediation acceptance follows from these offline checks.
