# Security and trust boundaries

The local application assumes trusted composition, an authorized caller and a controlled filesystem. These contracts protect scoped data paths; they do not supply operational authentication, a multitenant network service or a complete Python/OS sandbox.

## Implemented controls

| Boundary | Control and source of truth |
| --- | --- |
| Evidence/knowledge reads | Trusted grants are separate from filters; service/environment, freshness, withdrawal/revision and saved citations are checked by [queries](../architecture/bounded-evidence-queries.md), [corpus](../architecture/knowledge-corpus.md) and [retrieval](../architecture/knowledge-retrieval.md) |
| Evaluator isolation | Labels/answers/tests are outside the runtime wheel; import checks and behavioral tests protect source/input paths; [package rules](../architecture/package-layout.md) |
| Provider transmission | Independent current source access and Azure transmission grants, reviewed fields, bounded redaction and fail-closed admission before dispatch/history/reuse; [provider policy](../architecture/model-provider.md#owner-approved-transmission-policy--2026-10-13) |
| Transport | Short-lived signed preparation is checked by process and Azure adapters; verified TLS, bounded call/result and content-free errors; no unsigned direct request |
| Protected responses | Original input sensitivity survives redaction; current source/revision/transmission rights apply to content reads, exports and later context reuse |
| Assessment/support review | Strict report/reference validation and independent current support bindings; sanitized private review packets, not model-supplied reviewer approval; [assessment guide](../architecture/validated-assessments.md) |
| Execution/publication | Current job/attempt/lease, finite shared budgets and atomic private outcomes; unknown dispatch blocks replay; [budgets](../architecture/investigation-budgets.md), [workflow](../architecture/bounded-investigator.md) |
| Credentials/audit | Explicit private setup/key/journal files, mode 0600, authentication-only credential use and content-free usage/outcome/provenance metadata |

The current provider implementation blocks customer/employee/evaluator sources and has no exception/declassification path. Unknown/unreviewed classifications fail closed. The source owner must independently authorize Azure transmission for relevant internal code/runbooks/configuration.

## Limits that remain explicit

- Pattern scanners cannot establish that arbitrary prose is free of secrets or personal data; source-side field classification/review is mandatory.
- Local scope and file permissions do not authenticate an operator or derive real-source grants. Direct filesystem/application-composition access remains trusted.
- Dispatch-time checks cannot instantly revoke a request already executing remotely, and stopping a local worker cannot prove remote cancellation or absence of charges.
- Authorized dictionaries already read cannot be erased retroactively. Hosted identity, audit access/retention, distributed revocation and backup deletion require their own implementation/evidence.
- `store=false` is a request setting, not proof of zero provider retention or resource-local processing.
- Provider tests do not certify unrelated corpus-integrity/database-error findings or operational source integrations. Independent source, grant and storage failure cases retain their own scope.
- Synthetic support records and AI findings never constitute actual human endorsement or mutation approval.

## Logs, review and disclosure

Never record raw prompts/responses/provider errors, removed sensitive values, evaluator answers or credentials. Audit/logs retain permitted identifiers, nonnegative integer/null usage and explicit outcomes. Known credentials in field names are rejected before provenance writes.

Accepted assessments and pending review packets inherit source sensitivity and admitted redacted citation/provenance views. Reads/exports revalidate original provider dependencies plus current evidence/knowledge policy and support bindings. The bounded workflow preserves these rules; #38 must implement authenticated restoration/inspection/review persistence/export without a scope-only stored-body bypass.

## Hosted and real-data acceptance

Before real data or hosted use, record authenticated identity/grant derivation, least-privilege source/database/provider roles, field/transmission policy, processing/retention, deletion including vectors/backups and audit/support ownership. Require adversarial and failure evidence rather than inferring readiness from local tests.

[ADR 0015](../adr/0015-azure-aks-cloud-deployment.md) and #55–#60 separate CI/Terraform, node/image-pull, pod Workload Identity, database/admin and telemetry grants. Verify wrong/revoked pod identity and account restrictions before cloud inference. Shared PostgreSQL admission must preserve budgets, source/transmission and protected report/review rules across concurrent/replaced pods.

## Response authority

Initial investigation remains read-only. Recommendations, assessment support, engineer selection and execution approval are separate. Code/configuration changes follow reviewed delivery. Supported operational actions require the separate deterministic catalog/executor with exact-action approval, state revalidation, limits, reconciliation, verification and recovery. See [response/remediation scope](../planning/production-remediation-scope.md).
