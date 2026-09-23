# Approved scope: real production remediation

Owner-requested on 2026-09-23. This supersedes the simulated-only final action scope in earlier planning. TRACE is an incident intelligence and controlled-response platform. The first Local/Cloud MVP investigation releases remain read-only; the final capstone must implement real remediation, not merely simulate approval.

## Completion requirement

Implement at least one narrowly scoped, approval-gated remediation against an explicitly authorized production workload. Select the workload, action, service owner and approval authority during charter/ADR refinement. A deployment rollback is a candidate, not a decision: compatibility, migration safety, health criteria and a known-good target revision must make it appropriate for the selected workload.

Production means a workload serving a real operational purpose for its owner. A demo deployment, staging execution or an environment named production does not alone satisfy this gate. A team-owned production service can qualify; an external enterprise customer is not required. If no authorized production workload is available, report production acceptance as blocked rather than silently substituting simulation. Do not manufacture a production outage to complete the capstone; use a legitimate, owner-approved remediation opportunity and change window.

This scope approval authorizes planning and development. It is not standing authorization to mutate an unspecified production resource. Each eventual execution requires the concrete target/action approval below.

## Execution boundary

Investigation remains read-only. A separate deterministic remediation executor has a narrow, versioned action catalog and least-privilege workload identity. The model may propose an action; it cannot create executable code, grant permission or bypass approval. Prefer an existing deployment/runbook API over a general command runner. AWS Systems Manager is one possible adapter, not a selected dependency; its [manual approval action](https://docs.aws.amazon.com/systems-manager/latest/userguide/automation-action-approve.html) illustrates a native approval primitive that would still need TRACE's target, policy and outcome checks.

Flow: evidence-backed proposal → deterministic eligibility/preflight → concrete human approval → revalidation → bounded execution → outcome verification → recorded result or escalation.

Approval binds an immutable proposal hash to the exact account/environment/resource, action and runbook version, parameters, expected current state, target revision, blast-radius limits, execution window/expiry, approver identity and recovery plan. Reject expired/revoked approval, changed parameters or changed deployment state; require a new proposal/approval when material facts change. Enforce these controls in software and identity policy, independently of prompts. Reviewing a diagnosis never implicitly approves an action.

Persist proposal, approval, execution attempts, external operation IDs and verification evidence separately. Use target-level concurrency control and idempotency keys. After a timeout or worker crash, reconcile provider state before retrying; do not repeat an uncertain mutation blindly. Mark unknown outcomes explicitly. Cancellation/kill switch stops pending or further steps but must not claim to undo an already issued external action.

Limit the first action's resources, concurrency, duration and permitted revisions. Immediately before mutation, check authorization, approval validity, current resource state, ongoing changes and the runbook's specific prerequisites. Use an available conditional-write/version primitive; otherwise serialize changes through the authorized deployment control and document residual race conditions.

Define measurable pre/post health checks and a verification window. Provider acceptance is not proof of recovery. Record applied-and-verified, applied-but-unhealthy, rejected, failed and unknown outcomes. Stop/escalate on degraded or inconclusive results. Compensating actions must be explicitly included within the original approval or receive separate approval; do not assume every rollback is reversible. Preserve an access-controlled, tamper-evident audit history and on-call ownership.

## Delivery and promotion gates

| Increment | Required work |
| --- | --- |
| S1 | Record production target/action candidates, accountable owner, approver, access prerequisites and change policy; unresolved access is a tracked production gate. Keep skeleton scope small. |
| S7-S9 | Define separate investigation/execution identities, audit and change-control integration; MVP remains read-only and execution credentials are disabled until promotion. |
| S14 | Implement the real adapter and deterministic approval/execution state machine; prove in staging that the action changes actual workload state. Include denied, expired, altered and stale approvals, duplicate delivery, concurrent change, crash/timeout reconciliation, kill switch, failed verification and recovery/escalation tests. |
| S15 | Operational remediation readiness review and owner-supervised production rollout after staging and policy gates. Keep this separate from the validation-only AI study pilot. |
| S16 | Require production remediation evidence or record a blocking remediation item before claiming revised capstone completion. Freeze the AI study separately; remediation does not alter held-out diagnosis data. |
| S17-S18 | Report action outcomes, verification, failures, recovery and audit evidence separately from the five-arm diagnosis study. Demonstrate the capability using saved evidence or a separately approved execution, not a forced live incident. |

These increments remain provisional and must be resized for capacity. The added production requirement may extend delivery. Preserve the existing academic capabilities and operational-investigation pilot; neither substitutes for production remediation acceptance.

## Acceptance evidence

- Named authorized production workload, action/runbook version, service owner and approver, with action-specific limits and prerequisites.
- Successful staging execution and critical negative/failure tests, followed by an explicitly approved production execution.
- Provider operation record and before/after resource-state evidence proving the requested mutation actually occurred.
- Health verification demonstrating the intended operational result, with latency, failures, operator effort and costs recorded where measurable.
- Bound proposal/approval/attempt/verification audit trail, concurrency and retry reconciliation evidence, tested stop/recovery procedures and support ownership.
- Honest disclosure of partial, failed or unknown outcomes; no completion credit for a simulated action, approval UI alone or successful API submission without verified outcome.