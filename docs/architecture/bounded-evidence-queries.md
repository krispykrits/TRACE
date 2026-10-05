# Bounded local evidence queries

Status: Sprint 3 [story #11](https://github.com/krispykrits/TRACE/issues/11), proposed for review. This is an internal Python read boundary over SQLite synthetic snapshots. It does not connect to real operational sources or expose an HTTP/investigator tool API.

## Reproduce the query

Run from the repository root after setup. The first command prints the investigation ID; the second command saves that same JSON field for subsequent commands:

~~~sh
uv run --locked python scripts/demo_persistence.py ingest --db /tmp/trace-story-11.sqlite3 --seed 17 --mode failure --submission-key case-17
TRACE_INVESTIGATION_ID="$(uv run --locked python scripts/demo_persistence.py ingest --db /tmp/trace-story-11.sqlite3 --seed 17 --mode failure --submission-key case-17 | python3 -c 'import json,sys; print(json.load(sys.stdin)["investigation_id"])')"
uv run --locked python scripts/demo_persistence.py query --db /tmp/trace-story-11.sqlite3 --investigation-id "$TRACE_INVESTIGATION_ID" --service payment --window-start 2026-01-01T00:00:19Z --window-end 2026-01-01T00:00:19Z
uv run --locked python scripts/demo_persistence.py query --db /tmp/trace-story-11.sqlite3 --investigation-id "$TRACE_INVESTIGATION_ID" --limit 1
uv run --locked python scripts/demo_persistence.py query --db /tmp/trace-story-11.sqlite3 --investigation-id "$TRACE_INVESTIGATION_ID" --service notification
~~~

The seeded failure has a Payment timeout at 00:00:19Z. The first query returns that record. The second returns one record with truncated=true and matching_count=4. Notification has no record and returns zero matches. The replay snapshot also reports the unsupplied sanitized export as unavailable, so these result statuses are incomplete, including the zero-match case; they are never presented as complete operational coverage. The CLI uses a fixed synthetic trusted context and exposes no scope or environment argument.

## Python contract

EvidenceQueryService.query(investigation_id, EvidenceQuery, context=TrustedQueryContext) returns a typed EvidenceQueryResult. get_by_id resolves a record under the same scope, environment, service and time rules. The trusted application boundary supplies TrustedQueryContext(access_scope, environment, allowed_services) from authenticated or otherwise trusted execution context. Client-selected service and kind only narrow those grants. The local demo constructs a fixed test context; it is not an authentication mechanism. Direct filesystem access to SQLite bypasses application authorization and must remain restricted.

EvidenceQuery contains only UTC window_start/window_end, optional service and kind (log, metric, deployment), and a positive result limit. Identifiers allow bounded safe ASCII; arbitrary SQL and shell syntax are not accepted. The query window must fit inside the stored investigation window and within the configured maximum duration. The default maximum is 24 hours and the default maximum result count is 100; callers may lower these limits. The SQLite snapshot read guard defaults to 1,000 records per investigation. These are local safety bounds, not performance or production service targets.

Both window endpoints are **inclusive**. Filtering and ordering use the source event's observed_at UTC instant, not collected_at; fractional seconds are compared as instants, avoiding text-format ordering errors. Equal timestamps sort by evidence ID. Results contain the original typed payload and complete version 1 record envelope: stable evidence ID, source ID/revision, event and collection times, service/environment, correlation, access/redaction status and integrity digest. This story returns raw metrics only; it computes no summary that could lose contributing evidence IDs. The API reads one persisted snapshot at a time and never scans unrelated investigations.

| Result or error | Meaning |
| --- | --- |
| complete | Matches returned, source manifest present and every source available; no result truncation |
| empty | No matches within the filters, source manifest present and every source available |
| incomplete | Source availability is absent, at least one source is unavailable/truncated, or the result limit cut matches; inspect sources, truncated and matching_count |
| snapshot_missing | Authorized investigation exists but no snapshot has been ingested; failure_code names this case |
| storage_failure | SQLite read failed, stored data is invalid, the schema is incompatible, or the configured read bound was exceeded; failure_code is storage_failure or schema_incompatible and no empty result is fabricated |
| StoreInputError | Invalid field, window, limit or configured bound |
| StoreAccessError | Investigation/ID absent or outside trusted scope, environment, authorized services or selected window |

A direct ID read raises StoreDependencyError on storage failure. It raises the same access error for absent and inaccessible IDs. query includes source availability from the snapshot even for zero matches, plus an exact count of authorized matches before result truncation. There is no cursor or implicit second page; narrow the window or filters when truncated. Storage and access failures do not fall back to synthetic data.

Tests cover inclusive/fractional boundaries, service and kind filters, deterministic order, provenance and ID resolution, empty and incomplete source states, result/read bounds, bad requests, wrong scope/environment/service, stale event-time exclusion, no snapshot, closed-database failure, corrupted stored data and incompatible snapshot schema. Authorized real-source adapters, source-specific freshness/revocation, distributed authorization, and S4 investigator tools remain separate acceptance gates.
