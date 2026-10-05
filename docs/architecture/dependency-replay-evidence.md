# Dependency replay and evidence contract

Status: Sprint 2 issue [#8](https://github.com/krispykrits/TRACE/issues/8), implementation merged 2026-10-05. [ADR 0007](../adr/0007-synthetic-evidence-identity-and-isolation.md) records the identity and isolation decision.

## Run and reset

```sh
uv run --locked trace-app replay-dependency --environment test --seed 17 --mode normal
uv run --locked trace-app replay-dependency --environment test --seed 17 --mode failure
```

Both commands print one JSON result with `status` and `evidence` on stdout. Valid seeds are integers from 0 through 1,000,000,000. The scenario version is `payment-dependency.v1`; unsupported versions fail. Replay is restricted to development and test and calls only in-process fixtures. A Python `ReplaySession` permits one play, then requires `reset()` to clear its events and notification count before replay. Each CLI invocation starts a new session. The same version, seed, mode and environment yield the same logical event sequence, correlation ID, evidence IDs, source IDs, integrity digests and observed times. A different collection run can have a different `collected_at` and runtime log timestamps; those values do not enter stable identity.

The Payment timeout fixture raises `DependencyUnavailable("payment")` before returning an authorization. Order therefore cannot accept the request and Notification is not called. Operational evidence records the observed `payment.timeout` and `order.dependency_failed` events. The evaluator-only [manifest](../../evaluation/ground_truth/payment_dependency_v1.json) records the induced cause, mechanism, symptoms, expected evidence and causal chain. The manifest is outside the installable `trace_app` package and is never loaded by the replay or CLI. Do not mount, index, retrieve, export or prompt with evaluator material through investigator paths.

## Operational envelope, version 1

`EvidenceBundle` has `schema_version`, an inclusive UTC `query_window`, `sources` and `records`. Every `EvidenceRecord` contains the fields below. The JSON export uses an explicit field list, so adding evaluator metadata to another object cannot silently add it to the public record.

| Field | Contract |
| --- | --- |
| `schema_version` | `1`; consumers reject unsupported versions |
| `evidence_id` | Stable for scenario version, seed, mode, environment and event index; independent of collection time |
| `service`, `environment` | Logical boundary that produced the event and the replay environment |
| `observed_at` | Synthetic logical event time in RFC 3339 UTC, one second per ordered event from the versioned base time plus seed offset |
| `collected_at` | UTC time at this replay/export attempt; can vary between identical replays |
| `source_record_id`, `source_revision` | Stable source record identity and scenario version; future exports retain their own source IDs and revisions |
| `access_classification`, `redaction_status` | `synthetic_public` and `not_required` for this fixture; future real sources must supply actual authorization and redaction status |
| `correlation_id` | Shared across Order, Customer, Payment and Notification events for a replay |
| `event` | Observed event name, without a diagnosis or evaluator label |
| `integrity_sha256` | SHA-256 of canonical source record ID, service, event, observed time and correlation ID; this detects accidental fixture record changes, not cryptographic source authenticity |

The versioned generator creates timestamps in event order. `EvidenceBundle.timeline()` sorts by `(observed_at, evidence_id)` without an LLM. This ordering shows sequence, not proof of root cause. The separately recorded fixture mechanism establishes the controlled causal chain for evaluator use. No runtime latency, timeout duration, or production source timestamp is inferred from the one-second spacing.

## Source adapter contract and access gate

The synthetic replay adapter accepts validated `ReplayConfig` and emits an `EvidenceBundle` with source availability. A future authorized sanitized-export adapter must emit the same envelope while preserving source-owned record ID/revision, observed and collected UTC times, service/environment, correlation, access classification, redaction state, query window and any applicable integrity metadata. It must authorize access before reading or exporting, sanitize before normalization, record the source identity and revision, and expose no evaluator labels. It must return an explicit `unavailable` or `truncated` source status with a reason when access is absent or a query is incomplete; it must never invent evidence to fill gaps. Investigator reads and citation resolution will need the same access check in S3/S4.

No sanitized operational export or source owner permission has been supplied. Every current replay bundle therefore reports `sanitized_export: unavailable` with reason `no_authorized_export_supplied`. This is a recorded access gap, not an attempted real-source read. Retention, source authorization, revocation and durable snapshots remain later gates. Synthetic replay cannot satisfy the independent Operational Pilot gate.

## Demonstration and verification

Run both commands above and compare `records[*].event`, `evidence_id`, `observed_at`, `collected_at`, and `sources`. Inspect evaluator ground truth separately with `cat evaluation/ground_truth/payment_dependency_v1.json`. `make test` covers reset/replay, normal/failure distinction, evidence fields, UTC identity, deterministic ordering, negative ground-truth export checks and invalid input. `make integration` exercises the timeout path through the real CLI process and verifies no accepted result or Notification evidence.
