# Deterministic incident timelines

Sprint 3 [story #13](https://github.com/krispykrits/TRACE/issues/13), proposed for review. Timelines contain authorized observations from the existing bounded evidence query service. No model, causal inference, real-source integration or operational write capability is added.

## Reproduce

```sh
uv run --locked python scripts/demo_timeline.py --case c01 --seed 17
uv run --locked python scripts/demo_timeline.py --case c03 --seed 17
uv run --locked python scripts/demo_timeline.py --case c02 --seed 17 --limit 1
uv run --locked python scripts/demo_timeline.py --case c01 --seed 17 --window-start 2026-01-01T05:30:17+05:30 --window-end 2026-01-01T05:30:24+05:30
```

The developer demo shuffles the selected synthetic fixture with a seeded RNG, stores it in a private temporary SQLite database, closes/reopens storage, constructs the timeline, and resolves every included evidence ID. Stdout is the versioned timeline plus `resolved_evidence_ids`; correlated logs go to stderr. The temporary state is removed on success or failure. Capture time is fixed at October 12, 2026, 12:00 UTC for reproducibility; it is simulated metadata, not an actual collection measurement. Each run creates a new investigation ID, while logical records and their ordering are stable. Valid empty/incomplete timelines return exit 0; invalid requests or read/citation errors return 2. The demo uses a fixed local synthetic trusted context, with no user-selectable authority. Fixture selection and local state writes are developer setup, not operational investigation mutations.

For seed 17, complete c01/c02 evidence sorts by source ordinals `000, 001, 002, d01, 003, 004, 005, 006, 007`. The Notification deployment `d01` and Order request `002` share an observed timestamp and are ordered by evidence ID. The incomplete c03/c04 cases contain only `002, d01, 003, 007`; the missing Payment events never appear. All default fixtures report the unsupplied sanitized export as unavailable, so their timeline status is `incomplete`, including the cases with all synthetic records present.

## Time boundary

`normalize_timestamp(str)` accepts RFC 3339 with uppercase `T` and `Z`, or a numeric `±HH:MM` offset. Fractional seconds may contain one through six digits. It returns UTC with `Z`, preserving microsecond precision. Offset minutes must be 00–59 and hours 00–23. Calendar-invalid dates/times, leap seconds, more than six fractional digits, UTC conversion overflow, date-only/naive timestamps, named zones and RFC 3339's unknown-offset `-00:00` fail with an actionable error. Local daylight-saving ambiguity is never guessed; the source must supply an explicit offset.

Source adapters may use `EvidenceRecord.from_source_dict(mapping)` to normalize `observed_at` and `collected_at` before validating the complete version 1 envelope. Both fields retain distinct meanings. Missing/extra fields, unsupported versions and evaluator labels still fail validation. Source IDs/revision, access/redaction status, correlation and supplied integrity digest are preserved. The adapter remains responsible for verifying source integrity before normalization; the digest is not recalculated or treated as proof of authenticity. Existing records, stored-envelope `from_dict`, query windows and SQLite schema remain UTC-only, with no storage migration. The demo explicitly normalizes its input window before constructing an `EvidenceQuery`.

## Ordering and identity

`order_evidence(tuple[EvidenceEntry, ...])` sorts by `(parsed observed_at UTC instant, evidence_id)`. It uses neither collection time nor lexicographic timestamp comparison; fractions and different textual representations of an equal instant sort correctly. `EvidenceBundle.timeline()` uses the same instant/ID order for its older record-only helper. Collection time, service/environment, source record ID/revision, correlation, access/redaction status and typed payload remain attached to each original observation.

Duplicate evidence IDs or duplicate `(source_record_id, source_revision)` pairs within a timeline input are rejected, including identical repeats. This matches the existing snapshot batch policy. Separate idempotent snapshot re-ingestion preserves the first stored collection time; changed logical content conflicts. Equal-time events with distinct identities remain distinct. Events are never collapsed by message or timestamp. The pure ordering and serialization helpers are internal data functions and do not authorize reads.

## Scoped application contract and output

```python
service = TimelineService(EvidenceQueryService(store))
timeline = service.build(investigation_id, query, context=trusted_context)
entry = service.resolve(timeline, timeline.events[0].record.evidence_id,
                        context=trusted_context)
```

The trusted application supplies the context independently of requested filters and saved timeline metadata. Build inherits [#11's query scope and limits](bounded-evidence-queries.md): investigation/access scope, environment, service grants, inclusive observed-time window, maximum duration and result/read bounds. Caller filters can only narrow those grants. No unrestricted file/SQL/shell query or new source adapter is exposed.

| Timeline field | Meaning |
| --- | --- |
| `schema_version` | `1`, independent of the unchanged version 1 evidence envelope |
| `investigation_id`, `query` | Source investigation and narrowing window/service/kind/limit; no authority is serialized |
| `status`, `failure_code` | Query outcome: `complete`, `empty`, `incomplete`, `snapshot_missing` or `storage_failure`; failures retain their code |
| `matching_count`, `truncated` | Authorized matches before result limiting, and whether that limit omitted matches |
| `sources` | Preserved availability/reasons, including source truncation/unavailability or absent source manifest |
| `events` | Ordered typed entries, each with an `evidence_id` citation, `record`, `kind`, `payload` and `causal_status: observed` |

Source truncation is reported through `sources`/`incomplete`; the top-level `truncated` flag specifically denotes the query result limit. Empty complete coverage differs from an incomplete result with zero records. Missing snapshots and storage failures return no invented events and remain distinct from empty evidence. A missing source manifest cannot establish complete coverage.

Every event's citation resolves only if it belongs to that timeline and still passes the query service's current trusted scope, environment, filter and window checks. Deleted evidence, withdrawn service grants and another scope/environment fail with `StoreAccessError`; read failures propagate as `StoreDependencyError`. Content that no longer matches the saved event fails with `StoreConflictError`. Resolving an omitted/truncated ID is rejected rather than silently expanding the timeline. Saving a timeline or knowing an ID does not grant a new read; previously disclosed data cannot be retroactively hidden. Protected persistence/export and full operational-source freshness/revocation remain S4/S5 work.

## Observations and causality

`causal_status: observed` identifies each entry as a recorded observation, not a causal relationship. The output contains no inferred edges, hypothesis, cause label or confidence score. Nearby deployments, shared correlation IDs and sequence alone do not establish root cause. Later assessment contracts must represent supported and competing hypotheses separately from this sequence. Missing events remain source gaps even if a developer knows the fixture mechanism.

The correlated `timeline.constructed` log records investigation ID, status, returned count and result truncation, without evidence payloads or evaluator answers. No evaluator manifest is loaded by timeline construction, resolution or the demo.

## Verification and next work

`make check lint format-check type-check test integration` covers source offset normalization/rejection, equal/fractional timestamps, duplicate identity rejection, shuffled development fixture inclusion, delayed collection, authorized citation resolution, denied scope/window/service reads, deleted/altered citations, explicit empty/partial/missing/storage-failure outcomes and a real-process restart/shuffle demo. No network, credentials, model calls or final-test answers are needed. Issue #14 owns report/evaluator schemas and scoring; these timelines do not complete Local MVP or Operational Pilot acceptance.
