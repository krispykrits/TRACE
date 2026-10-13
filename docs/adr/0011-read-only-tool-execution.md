# ADR 0011: Read-only tools with bounded local worker execution

- **Status:** Proposed implementation for #18; awaiting owner PR review/merge
- **Date:** 2026-10-12
- **Owner:** Project owner
- **Scope:** Local MVP investigation tool authority, execution and audit boundary

## Context

Issue #18 requires validated log/metric/deployment/knowledge tools, authorization independent of model-selected arguments, externally enforced attempts/time/result bounds, direct evidence/citation protection and redacted correlated audit. Existing evidence and corpus stores combine trusted administration with reader ports; merely hiding write methods in a prompt would not establish least privilege. A thread timeout could leave a blocked reader running and repeated attempts could accumulate workers.

## Decision

Keep the fixed catalog, typed arguments, trusted scope, quota/result contracts and session orchestration in `investigation.tools`. Implement local execution/audit in `adapters.tools`, selected by bootstrap under ADR 0010. Each attempt starts the same isolated Python worker with configured approved source paths and fixed trusted contexts. It opens existing SQLite databases in read-only URI/query-only mode and reads immutable index artifacts. It cannot create/migrate sources or dispatch administrative operations. Model arguments can only narrow filters and result limits.

Enforce one active worker per session, a bounded attempt count and monotonic total/call deadlines outside prompts. Count malformed and concurrent denied calls. Kill/reap an overdue worker and discard late output; no retries or fallback. Keep original source records/quotes, current authorized citation revalidation and whole-item loss diagnostics within bounded JSON payloads. Emit metadata-only audit through the existing logger; fail closed when the audit sink raises. Use no new dependencies, provider calls, semantic default or cloud resource.

The worker is not an OS privilege/filesystem sandbox and the timing bounds are not a hard real-time SLA. Deployment must protect configured source files, supply current authenticated grants, retain the real clock, configure logging and use least-privilege operational adapters when introduced. Real-source redaction and hosted CloudWatch delivery remain separate gates. Investigation assessment review never authorizes production mutation; the deterministic remediation executor remains separate.

## Alternatives and consequences

Direct synchronous reads would be smaller, but a stuck dependency could hold the investigator indefinitely. Cooperative deadlines alone require every future adapter to honor cancellation. Thread timeouts cannot stop late readers. A fixed subprocess worker gives a concrete local termination boundary with no inherited publisher handles; startup overhead and JSON transport cost are acceptable for this small local baseline, remain measured in audit and may need revisiting for a hosted source/workload.

Reusing store reader logic with explicit read-only construction avoids duplicate SQL/schema/source-policy implementations. Publisher defaults stay intact; readonly construction is covered by write-denial/no-create/no-migrate tests. The worker and core dependency direction, evaluator exclusion and installed-wheel invocation are verified separately. Historical retrieval reports remain frozen at their recorded checkout; this story does not rewrite hashes or reaccept held-out quality.

## Revisit conditions

Revisit process reuse or asynchronous execution only with measured overhead/concurrency requirements and an equivalent bounded termination, least-privilege and provenance contract. Add real source/credential adapters through their scoped issue and current policy tests. Do not expand this catalog to mutations; use the approved separate executor and action-bound approvals. See the [tool catalog](../architecture/investigation-tools.md) for schemas, bounds, error/audit conventions and reproduction.
