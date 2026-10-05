# ADR 0007: Stable synthetic evidence identity and evaluator isolation

Status: Accepted with merged issue #8 PR #31, 2026-10-05. Revisit when S3 persistence or an authorized real source tests the contract.

## Context

The first Payment dependency incident must replay reproducibly while retaining source provenance and keeping benchmark answers out of investigator inputs. Application logs use wall-clock timestamps and request-specific correlation IDs, so they cannot by themselves supply stable incident evidence identity.

## Decision

Use a TRACE-owned version 1 evidence envelope. Derive synthetic correlation, source record and evidence IDs from version, seed, mode, environment and event index. Assign observed times from a fixed UTC base plus a seed offset and event ordinal. Record collection time separately. Keep the evaluator cause/symptom manifest under `evaluation/ground_truth`, outside the installable package and outside all operational exports. Serialize operational fields through an explicit allowlist. Report unavailable sanitized export access in the source status rather than treating synthetic replay as operational evidence.

The replay adapter observes actual Customer, Payment and Notification fixture calls and propagates the Payment failure through `OrderWorkflow`. It does not infer causality from timestamps. See the [contract](../architecture/dependency-replay-evidence.md).

## Alternatives and tradeoffs

- Wall-clock event times and random UUIDs would be simple, but would change identities on every run and weaken replay comparison.
- Converting application stderr logs into evidence would reuse existing output, but runtime timestamps and handler behavior are not a stable incident-source contract.
- Placing manifest labels in the same public fixture object would ease scoring, but risks exposing answers through exports, tools or retrieval.

The deterministic clock is synthetic and does not measure latency. Hash-based IDs are fixture identities, not proof of source authenticity. A repository checkout can still read the evaluator file; the boundary is the installable runtime and investigator interface. Stronger filesystem access separation is required before held-out evaluation is deployed.

## Revisit conditions

Revisit ID collision policy, canonicalization, authorization and source integrity when #10 adds SQLite snapshots, when an authorized sanitized export is supplied, or when S4 citation/revocation checks require stronger source identity. Do not change existing evidence identities silently during migration.
