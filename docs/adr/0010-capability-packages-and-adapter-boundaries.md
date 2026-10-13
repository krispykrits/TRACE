# ADR 0010: Capability packages and explicit adapter composition

- **Status:** Accepted and merged for #46 in PR #47; owner merge verified 2026-10-12 (America/New_York)
- **Date:** 2026-10-12
- **Owner:** Project owner
- **Scope:** Structural refactor of the modular Python application; no new product capability

## Context

The flat scaffold now includes evidence, durable state, corpus ingestion, retrieval and bounded context. Sprint 5 introduces provider execution and investigation orchestration. Core search currently imports numerical implementations and storage-defined index records, making future adapters harder to substitute safely. Test discovery also repeats process integration checks and root-only source hashing would miss nested modules.

## Decision

Adopt the [capability layout](../architecture/package-layout.md): evidence, knowledge and investigation contracts/use cases remain independent of frameworks; concrete storage/scoring/embedding/source implementations live in adapters; bootstrap selects implementations; CLI presents application outcomes; runtime utilities and explicit synthetic demos have separate homes. Inject the existing exact scorer through a small port and move corpus/index records into knowledge contracts. Preserve trace_app, public CLI behavior, serialized identifiers/schemas, dependency lock and retrieval semantics.

Organize unit, contract, integration and opt-in live tests. Enforce import direction and evaluator isolation with a standard-library AST check and negative fixtures. Verify a built wheel from outside the checkout in CI. Make nested source hashing explicit, preserve archived evaluation snapshots and document the exact pre-refactor checkout for historic rescoring. AGENTS.md governs placement and required checks for subsequent work.

## Alternatives

Keep a flat package: smallest immediate edit, but increasing adapter/core coupling and unclear test discovery. Universal domain/application/infrastructure layers: valid dependency direction, but more navigation and empty layers for the current capability sizes. Multiple services: adds deployment and network boundaries without workload evidence. Capability packages with separated adapters fit the existing application and approved incremental design.

## Consequences and verification

Imports and source links change; old internal module paths are removed rather than maintained as duplicate implementations. Public console/module CLI entry points stay supported. The import checker cannot establish security against arbitrary reflection or file/network access; review and boundary tests remain necessary. Historical scorer hashes intentionally differ from current code and require their recorded checkout. Relevant tests, typing, lint/format, architecture and installed-wheel checks must pass before owner merge.

No provider/RDS/remediation implementation, AWS resource, benchmark threshold change or production-readiness claim follows from this decision. Add new capabilities or adjust dependency policy only through a reviewed scoped change and update the checker/documentation together.

## Proposed extension — #34 offline subtask #50, 2026-10-13

[ADR 0012](0012-model-provider-contract-and-bounded-call.md) proposes `investigation.provider` and `investigation.provider_policy` for model/admission contracts and rules, and `adapters/models` for bounded Azure transport/process execution and private SQLite audit/provenance/spending. Model adapters can import only these model/policy contracts and runtime within TRACE; source/storage/tool handles stay outside. Network execution belongs to adapters; core URL parsing remains allowed. The checker, negative cases and package guide change together. Test-only transports/authorities are excluded from the wheel. Azure/owner policy is selected; actual synthetic live evidence and operational acceptance limits are recorded in the provider guide. No SDK dependency is added.
