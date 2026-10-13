# ADR 0012: Provider-neutral model contract and bounded call boundary

- **Status:** Proposed for owner review; offline subtask #50 of #34; provider/model choice and live acceptance pending
- **Date:** 2026-10-13 (America/New_York)
- **Owner:** Project owner
- **Scope:** Offline model contracts and one-call execution; no hosted provider selection

## Context

The owner accepted Sprint 4 through merged #19 / PR #49. #34 is the next Ready roadmap story and explicitly allows contract/offline tests while provider spending/account/data-handling decisions are pending. Core investigation code needs reproducible identities, structured responses, explicit usage absence and safe failures without binding to a vendor or gaining source/tool authority. A timeout hint alone cannot stop a stalled synchronous call.

## Proposed decision

Put `model-provider.v1` and `ModelProvider`/`ModelTransport` ports in `investigation.provider`. Keep configuration, prompt/source text, output bounds, result metadata and error categories explicit. Permit no automatic SDK retry or alternate-provider/model fallback. Local readiness is preflight, not live acceptance. Treat JSON as an untrusted intermediate response; #35 separately owns assessment/citation validation.

Implement `adapters/models/process.py` as a spawned, killable one-call boundary selected through bootstrap. Validate JSON and bounds on both sides; discard worker output/logs and publish only fixed failures plus correlated metadata. Actual remote cancellation/cost is not inferred from local timeout. Model transports receive request text, not source or tool handles; update ADR 0010, the package guide, import checker/negative cases and installed-wheel requirements together.

Keep the explicitly selected deterministic transport under tests only. Do not choose a hosted provider, add a vendor SDK, define credential/environment setup or claim live readiness without the owner inputs. Track this reviewable work as #50 so merging it cannot complete parent #34 prematurely. No dependency/lock change is required for this standard-library implementation.

## Alternatives and tradeoffs

A concrete vendor SDK now would prematurely select an owner-gated provider and add unapproved dependencies. A port without any execution boundary would leave deadline enforcement unproven. Running synchronous calls in threads would permit stalled calls to continue after timeout. Spawned processes add startup/serialization overhead and require a serializable transport; they permit local termination and keep raw third-party failures out of parent logs. This is not a general process/network sandbox, streaming reader or complete investigation budget policy.

## Verification and revisit conditions

Credential-free tests cover strict readiness/configuration, explicit offline selection, structured/usage contracts, raw-content isolation, fixed error propagation, single attempts, actual timeout termination and output rejection. Architecture negatives reject source/tool/storage/evaluator access; installed-wheel checks include nested model modules and exclude test fixtures. Run all required repository quality gates before PR handoff.

Extend this ADR after owner provider/model/spending/account/transmission/retention decisions: compare concrete candidates, justify and lock any SDK, prove native token bounds and disabled SDK retries, document credential/configuration precedence, and record a real opted-in contract check. Revisit process selection if measured startup overhead or a selected SDK's initialization/serialization requirements make it unsuitable. Revisit bounded streaming for a demonstrated workload gap. #36 owns total execution/usage/cost policy; #37 owns durable attempts and uncertain-call recovery. No model/Operational Pilot/Cloud MVP or remediation acceptance follows from these offline checks.
