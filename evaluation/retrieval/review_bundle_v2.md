# Passage relevance and claim-support review

This is evaluator-only development material. All judgments below are agent-authored proposals, with no human sign-off yet.

Suite SHA-256: `dfa9b0d7ebd9d65f55d92f300d28d372ef5455175fce83d83086fb82d0aa75db`.

Review every query's proposed relevant set, including empty sets, and each passage/claim verdict against the original quote and metadata. Record supported/unsupported/indeterminate decisions and rationales in reviews_v2.json using the target IDs below. A relevance verdict of supported endorses the complete proposed relevant set; another verdict records a rejection/uncertainty. Claim verdicts concern the stated probe claim, not a generated answer.

The 100 requests are variants across 15 related development families over six fictional/curated references. They are not 100 independent incidents. Stale-source cases give the certificate reference a fixture freshness deadline of 12:05 UTC, index it at 12:00 and query at 12:10 on 2026-10-12. No held-out material is supplied.

## Original passages

### chunk-39f82b466c7b49c1584c35b5961d24f7cea04107777130365d16655aa212fb65

Document: `trace-dev-history-certificate`; section: Investigation lesson

```json
{
  "document_id": "trace-dev-history-certificate",
  "document_type": "incident",
  "title": "Fictional archive: certificate expiry investigation",
  "service": "payment",
  "environment": "test",
  "source_uri": "synthetic://trace-knowledge/history-certificate",
  "source_record_id": "reference/history-certificate",
  "source_revision": "2026-10-12.v1",
  "version": "1.0.0",
  "provenance": "TRACE-authored development reference; fictional history where explicitly stated",
  "access_scope": "local:knowledge-development",
  "access_classification": "synthetic_public",
  "evaluation_role": "development_reference",
  "answer_bearing": true,
  "valid_from": "2026-01-01T00:00:00Z",
  "valid_until": null,
  "verified_at": "2026-10-12T12:00:00Z",
  "fresh_until": "2026-11-12T12:00:00Z"
}
```

Original offsets: 513–827.

> # Investigation lesson
> The archived explanation depended on certificate and trace evidence, not timing alone. A current investigation would need its own authorized observations. Reusing the historical explanation without the distinguishing evidence is unsupported. No production action is authorized by this note.

### chunk-3bcd76338ebe1579510d564f6f648afd1ceb859dc121564efbb701307fa81538

Document: `trace-dev-order-interface`; section: Limits

```json
{
  "document_id": "trace-dev-order-interface",
  "document_type": "service",
  "title": "Order service interface and dependencies",
  "service": "order",
  "environment": "test",
  "source_uri": "synthetic://trace-knowledge/order-interface",
  "source_record_id": "reference/order-interface",
  "source_revision": "2026-10-12.v1",
  "version": "1.0.0",
  "provenance": "TRACE-authored development reference; fictional history where explicitly stated",
  "access_scope": "local:knowledge-development",
  "access_classification": "synthetic_public",
  "evaluation_role": "development_reference",
  "answer_bearing": false,
  "valid_from": "2026-01-01T00:00:00Z",
  "valid_until": null,
  "verified_at": "2026-10-12T12:00:00Z",
  "fresh_until": "2026-11-12T12:00:00Z"
}
```

Original offsets: 519–790.

> # Limits
> The current fixtures have no operational telemetry adapter. Notification activity or a deployment near an Order error is not sufficient evidence that Notification caused it. This reference describes the development interface, not a deployed production topology.

### chunk-4e0343369dacbfad9affc8fbb8011cbc9bd296d5702cbe8fe5297ab6b2ddeeb0

Document: `trace-dev-history-queue`; section: Development history

```json
{
  "document_id": "trace-dev-history-queue",
  "document_type": "postmortem",
  "title": "Fictional archive: queue backlog investigation",
  "service": "order",
  "environment": "test",
  "source_uri": "synthetic://trace-knowledge/history-queue",
  "source_record_id": "reference/history-queue",
  "source_revision": "2026-10-12.v1",
  "version": "1.0.0",
  "provenance": "TRACE-authored development reference; fictional history where explicitly stated",
  "access_scope": "local:knowledge-development",
  "access_classification": "synthetic_public",
  "evaluation_role": "development_reference",
  "answer_bearing": true,
  "valid_from": "2026-01-01T00:00:00Z",
  "valid_until": null,
  "verified_at": "2026-10-12T12:00:00Z",
  "fresh_until": "2026-11-12T12:00:00Z"
}
```

Original offsets: 0–229.

> # Development history
> This fictional historical note illustrates an investigation unrelated to the seeded timeout mechanisms. It provides development context only, without held-out case identifiers, labels or benchmark answers.
> 

### chunk-7952c735c44e632f1f4314d0aa0bffcaf390c3006a23af2a007c0d09a4b7aed9

Document: `trace-dev-history-queue`; section: Investigation lesson

```json
{
  "document_id": "trace-dev-history-queue",
  "document_type": "postmortem",
  "title": "Fictional archive: queue backlog investigation",
  "service": "order",
  "environment": "test",
  "source_uri": "synthetic://trace-knowledge/history-queue",
  "source_record_id": "reference/history-queue",
  "source_revision": "2026-10-12.v1",
  "version": "1.0.0",
  "provenance": "TRACE-authored development reference; fictional history where explicitly stated",
  "access_scope": "local:knowledge-development",
  "access_classification": "synthetic_public",
  "evaluation_role": "development_reference",
  "answer_bearing": true,
  "valid_from": "2026-01-01T00:00:00Z",
  "valid_until": null,
  "verified_at": "2026-10-12T12:00:00Z",
  "fresh_until": "2026-11-12T12:00:00Z"
}
```

Original offsets: 570–894.

> # Investigation lesson
> Historical cause statements are not facts about a new incident. Check live worker state, source coverage and the relevant window before transferring an explanation. If those observations are absent, preserve uncertainty and ask for the missing evidence. Recovery requires a separate approval process.

### chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3

Document: `trace-dev-timeout-evidence`; section: Missing evidence

```json
{
  "document_id": "trace-dev-timeout-evidence",
  "document_type": "runbook",
  "title": "Timeout evidence collection",
  "service": "payment",
  "environment": "test",
  "source_uri": "synthetic://trace-knowledge/timeout-evidence",
  "source_record_id": "reference/timeout-evidence",
  "source_revision": "2026-10-12.v1",
  "version": "1.0.0",
  "provenance": "TRACE-authored development reference; fictional history where explicitly stated",
  "access_scope": "local:knowledge-development",
  "access_classification": "synthetic_public",
  "evaluation_role": "development_reference",
  "answer_bearing": false,
  "valid_from": "2026-01-01T00:00:00Z",
  "valid_until": null,
  "verified_at": "2026-10-12T12:00:00Z",
  "fresh_until": "2026-11-12T12:00:00Z"
}
```

Original offsets: 601–912.

> # Missing evidence
> Report capture gaps and collection delay. If configuration or downstream duration cannot be observed, retain competing explanations and propose a specific source check. Do not guess a cause from a symptom or from the absence of logs. Suggested checks do not authorize a configuration change.

### chunk-7ffb5ee9fd1c54938d530e73a30dfd387264efe8e39c2760cc6827a88ae68553

Document: `trace-dev-source-freshness`; section: Scope

```json
{
  "document_id": "trace-dev-source-freshness",
  "document_type": "runbook",
  "title": "Checking source freshness and gaps",
  "service": "order",
  "environment": "test",
  "source_uri": "synthetic://trace-knowledge/source-freshness",
  "source_record_id": "reference/source-freshness",
  "source_revision": "2026-10-12.v1",
  "version": "1.0.0",
  "provenance": "TRACE-authored development reference; fictional history where explicitly stated",
  "access_scope": "local:knowledge-development",
  "access_classification": "synthetic_public",
  "evaluation_role": "development_reference",
  "answer_bearing": false,
  "valid_from": "2026-01-01T00:00:00Z",
  "valid_until": null,
  "verified_at": "2026-10-12T12:00:00Z",
  "fresh_until": "2026-11-12T12:00:00Z"
}
```

Original offsets: 0–214.

> # Scope
> Establish which log, metric and deployment sources are permitted for the service and window. A successful empty result, a failed query, a truncated result and an unavailable source are different outcomes.
> 

### chunk-87083ef5e8c7c9f7934ab9eee09f30243eceac1a2bb398166182b0f18efb39e8

Document: `trace-dev-payment-interface`; section: Boundary

```json
{
  "document_id": "trace-dev-payment-interface",
  "document_type": "service",
  "title": "Payment service evidence vocabulary",
  "service": "payment",
  "environment": "test",
  "source_uri": "synthetic://trace-knowledge/payment-interface",
  "source_record_id": "reference/payment-interface",
  "source_revision": "2026-10-12.v1",
  "version": "1.0.0",
  "provenance": "TRACE-authored development reference; fictional history where explicitly stated",
  "access_scope": "local:knowledge-development",
  "access_classification": "synthetic_public",
  "evaluation_role": "development_reference",
  "answer_bearing": false,
  "valid_from": "2026-01-01T00:00:00Z",
  "valid_until": null,
  "verified_at": "2026-10-12T12:00:00Z",
  "fresh_until": "2026-11-12T12:00:00Z"
}
```

Original offsets: 0–200.

> # Boundary
> The Payment development fixture receives an order ID and positive amount. The work result and the caller's configured deadline are separate observations. The fixture makes no real charge.
> 

### chunk-97ea9848b883f7631587f97016ac45d37821152f9a2fd4bb97524625eec712fa

Document: `trace-dev-payment-interface`; section: Evidence vocabulary

```json
{
  "document_id": "trace-dev-payment-interface",
  "document_type": "service",
  "title": "Payment service evidence vocabulary",
  "service": "payment",
  "environment": "test",
  "source_uri": "synthetic://trace-knowledge/payment-interface",
  "source_record_id": "reference/payment-interface",
  "source_revision": "2026-10-12.v1",
  "version": "1.0.0",
  "provenance": "TRACE-authored development reference; fictional history where explicitly stated",
  "access_scope": "local:knowledge-development",
  "access_classification": "synthetic_public",
  "evaluation_role": "development_reference",
  "answer_bearing": false,
  "valid_from": "2026-01-01T00:00:00Z",
  "valid_until": null,
  "verified_at": "2026-10-12T12:00:00Z",
  "fresh_until": "2026-11-12T12:00:00Z"
}
```

Original offsets: 200–515.

> # Evidence vocabulary
> Useful evidence can include request failures, measured work duration, effective caller budget and configuration revisions. Keep each source's record identity, version, service, environment and observed time when joining a request timeline. HTTP 504 is a symptom code, not a root-cause label.
> 

### chunk-9bb28e983e90fa34b2f00798cf4c3b8a1b27d03181b24dc3c0fbab6bf7350abe

Document: `trace-dev-timeout-evidence`; section: Evidence checks

```json
{
  "document_id": "trace-dev-timeout-evidence",
  "document_type": "runbook",
  "title": "Timeout evidence collection",
  "service": "payment",
  "environment": "test",
  "source_uri": "synthetic://trace-knowledge/timeout-evidence",
  "source_record_id": "reference/timeout-evidence",
  "source_revision": "2026-10-12.v1",
  "version": "1.0.0",
  "provenance": "TRACE-authored development reference; fictional history where explicitly stated",
  "access_scope": "local:knowledge-development",
  "access_classification": "synthetic_public",
  "evaluation_role": "development_reference",
  "answer_bearing": false,
  "valid_from": "2026-01-01T00:00:00Z",
  "valid_until": null,
  "verified_at": "2026-10-12T12:00:00Z",
  "fresh_until": "2026-11-12T12:00:00Z"
}
```

Original offsets: 238–601.

> # Evidence checks
> Compare caller failures with Payment request durations and dependency spans from the same authorized window. Check deployment/configuration history, timestamps, effective timeout configuration and work duration separately. Preserve exact error codes such as HTTP 504 and /v1/orders without rewriting them. A nearby deployment can be unrelated.
> 

### chunk-a38ad3f58e817f8c656d0c027be95c8a4d56665062d074ae6c065355716c7574

Document: `trace-dev-order-interface`; section: Request boundary

```json
{
  "document_id": "trace-dev-order-interface",
  "document_type": "service",
  "title": "Order service interface and dependencies",
  "service": "order",
  "environment": "test",
  "source_uri": "synthetic://trace-knowledge/order-interface",
  "source_record_id": "reference/order-interface",
  "source_revision": "2026-10-12.v1",
  "version": "1.0.0",
  "provenance": "TRACE-authored development reference; fictional history where explicitly stated",
  "access_scope": "local:knowledge-development",
  "access_classification": "synthetic_public",
  "evaluation_role": "development_reference",
  "answer_bearing": false,
  "valid_from": "2026-01-01T00:00:00Z",
  "valid_until": null,
  "verified_at": "2026-10-12T12:00:00Z",
  "fresh_until": "2026-11-12T12:00:00Z"
}
```

Original offsets: 0–236.

> # Request boundary
> The development Order interface accepts an order ID, customer ID and amount in cents. It asks Customer for eligibility, invokes Payment, and dispatches the in-process Notification fixture after a successful payment.
> 

### chunk-ab1aed6f89a2841d256dc1b1329689c8db0663363d23115949db1ab7a44698cd

Document: `trace-dev-order-interface`; section: Observability

```json
{
  "document_id": "trace-dev-order-interface",
  "document_type": "service",
  "title": "Order service interface and dependencies",
  "service": "order",
  "environment": "test",
  "source_uri": "synthetic://trace-knowledge/order-interface",
  "source_record_id": "reference/order-interface",
  "source_revision": "2026-10-12.v1",
  "version": "1.0.0",
  "provenance": "TRACE-authored development reference; fictional history where explicitly stated",
  "access_scope": "local:knowledge-development",
  "access_classification": "synthetic_public",
  "evaluation_role": "development_reference",
  "answer_bearing": false,
  "valid_from": "2026-01-01T00:00:00Z",
  "valid_until": null,
  "verified_at": "2026-10-12T12:00:00Z",
  "fresh_until": "2026-11-12T12:00:00Z"
}
```

Original offsets: 236–519.

> # Observability
> A correlation ID follows one request across the logical boundaries. Service identity changes at the receiving boundary. Preserve both fields rather than treating all correlated records as one service. Failed requests and accepted receipts are distinct observations.
> 

### chunk-afc1fc54e71e5da0bc5007b338b1e1ad1282f5fa8e0317222f9b646a021f8821

Document: `trace-dev-history-certificate`; section: Development history

```json
{
  "document_id": "trace-dev-history-certificate",
  "document_type": "incident",
  "title": "Fictional archive: certificate expiry investigation",
  "service": "payment",
  "environment": "test",
  "source_uri": "synthetic://trace-knowledge/history-certificate",
  "source_record_id": "reference/history-certificate",
  "source_revision": "2026-10-12.v1",
  "version": "1.0.0",
  "provenance": "TRACE-authored development reference; fictional history where explicitly stated",
  "access_scope": "local:knowledge-development",
  "access_classification": "synthetic_public",
  "evaluation_role": "development_reference",
  "answer_bearing": true,
  "valid_from": "2026-01-01T00:00:00Z",
  "valid_until": null,
  "verified_at": "2026-10-12T12:00:00Z",
  "fresh_until": "2026-11-12T12:00:00Z"
}
```

Original offsets: 0–205.

> # Development history
> This independent fictional incident is an educational archive example. It is not a replay of the seed-17 development cases and is not an operational postmortem or final-test answer.
> 

### chunk-b80174ddde722d6ccd694bccf44b7a681036d7410d340c8ff7e9c304204a638c

Document: `trace-dev-history-certificate`; section: Observations

```json
{
  "document_id": "trace-dev-history-certificate",
  "document_type": "incident",
  "title": "Fictional archive: certificate expiry investigation",
  "service": "payment",
  "environment": "test",
  "source_uri": "synthetic://trace-knowledge/history-certificate",
  "source_record_id": "reference/history-certificate",
  "source_revision": "2026-10-12.v1",
  "version": "1.0.0",
  "provenance": "TRACE-authored development reference; fictional history where explicitly stated",
  "access_scope": "local:knowledge-development",
  "access_classification": "synthetic_public",
  "evaluation_role": "development_reference",
  "answer_bearing": true,
  "valid_from": "2026-01-01T00:00:00Z",
  "valid_until": null,
  "verified_at": "2026-10-12T12:00:00Z",
  "fresh_until": "2026-11-12T12:00:00Z"
}
```

Original offsets: 205–513.

> # Observations
> In this example, Payment requests failed during a certificate rollover. The archive retained a TLS certificate expiry error, the certificate validity interval and a dependency trace. A nearby Notification rollout was initially considered, but its records did not support a causal connection.
> 

### chunk-c8ccd466e62a6a323e6b9b89dde5065525370ff1fcca7a4999f51d243098a96b

Document: `trace-dev-payment-interface`; section: Interpretation

```json
{
  "document_id": "trace-dev-payment-interface",
  "document_type": "service",
  "title": "Payment service evidence vocabulary",
  "service": "payment",
  "environment": "test",
  "source_uri": "synthetic://trace-knowledge/payment-interface",
  "source_record_id": "reference/payment-interface",
  "source_revision": "2026-10-12.v1",
  "version": "1.0.0",
  "provenance": "TRACE-authored development reference; fictional history where explicitly stated",
  "access_scope": "local:knowledge-development",
  "access_classification": "synthetic_public",
  "evaluation_role": "development_reference",
  "answer_bearing": false,
  "valid_from": "2026-01-01T00:00:00Z",
  "valid_until": null,
  "verified_at": "2026-10-12T12:00:00Z",
  "fresh_until": "2026-11-12T12:00:00Z"
}
```

Original offsets: 515–836.

> # Interpretation
> A hypothesis must account for supporting evidence and alternatives. An unchanged budget with slower observed work calls for different checks than a changed budget with stable work. Missing evidence can make these hypotheses indistinguishable; disclose the gap rather than assigning a causal probability.

### chunk-d2228cb1127d51fbf4d5d21c99c8a31d14411ebe37907a9fd0057dc6605bd8af

Document: `trace-dev-source-freshness`; section: Time and provenance

```json
{
  "document_id": "trace-dev-source-freshness",
  "document_type": "runbook",
  "title": "Checking source freshness and gaps",
  "service": "order",
  "environment": "test",
  "source_uri": "synthetic://trace-knowledge/source-freshness",
  "source_record_id": "reference/source-freshness",
  "source_revision": "2026-10-12.v1",
  "version": "1.0.0",
  "provenance": "TRACE-authored development reference; fictional history where explicitly stated",
  "access_scope": "local:knowledge-development",
  "access_classification": "synthetic_public",
  "evaluation_role": "development_reference",
  "answer_bearing": false,
  "valid_from": "2026-01-01T00:00:00Z",
  "valid_until": null,
  "verified_at": "2026-10-12T12:00:00Z",
  "fresh_until": "2026-11-12T12:00:00Z"
}
```

Original offsets: 214–493.

> # Time and provenance
> Use observed event time for the incident timeline and retain collection time as provenance. Record source identity and revision. Delayed collection must not imply a later operational event. Query only within granted services, environment and access scope.
> 

### chunk-d75f8b3a2d09e63d77a1bde080640c97f3ece21ef5985b441b26ba86ea071b1a

Document: `trace-dev-timeout-evidence`; section: Scope

```json
{
  "document_id": "trace-dev-timeout-evidence",
  "document_type": "runbook",
  "title": "Timeout evidence collection",
  "service": "payment",
  "environment": "test",
  "source_uri": "synthetic://trace-knowledge/timeout-evidence",
  "source_record_id": "reference/timeout-evidence",
  "source_revision": "2026-10-12.v1",
  "version": "1.0.0",
  "provenance": "TRACE-authored development reference; fictional history where explicitly stated",
  "access_scope": "local:knowledge-development",
  "access_classification": "synthetic_public",
  "evaluation_role": "development_reference",
  "answer_bearing": false,
  "valid_from": "2026-01-01T00:00:00Z",
  "valid_until": null,
  "verified_at": "2026-10-12T12:00:00Z",
  "fresh_until": "2026-11-12T12:00:00Z"
}
```

Original offsets: 0–238.

> # Scope
> A timeout reports a caller-visible deadline failure. It does not identify which dependency or configuration caused the delay. Record service, environment, incident window and the authorized evidence sources before investigating.
> 

### chunk-e2debbd2df4c20f2624bb63dcb8bc6b97e9e9e8fbfdabddaaf1607323574a748

Document: `trace-dev-history-queue`; section: Observations

```json
{
  "document_id": "trace-dev-history-queue",
  "document_type": "postmortem",
  "title": "Fictional archive: queue backlog investigation",
  "service": "order",
  "environment": "test",
  "source_uri": "synthetic://trace-knowledge/history-queue",
  "source_record_id": "reference/history-queue",
  "source_revision": "2026-10-12.v1",
  "version": "1.0.0",
  "provenance": "TRACE-authored development reference; fictional history where explicitly stated",
  "access_scope": "local:knowledge-development",
  "access_classification": "synthetic_public",
  "evaluation_role": "development_reference",
  "answer_bearing": true,
  "valid_from": "2026-01-01T00:00:00Z",
  "valid_until": null,
  "verified_at": "2026-10-12T12:00:00Z",
  "fresh_until": "2026-11-12T12:00:00Z"
}
```

Original offsets: 229–570.

> # Observations
> The example retained a growing Order work queue, worker completion metrics and a dependency health check. The dependency check was healthy while the queue kept growing. The archive attributed the backlog to a paused worker based on retained worker state; a recent Payment deployment alone did not establish that explanation.
> 

### chunk-f3dded5575d6ece71420e0371428faaf0dcfeb0fb2efb0e4db97782c18aee6ce

Document: `trace-dev-source-freshness`; section: Recheck

```json
{
  "document_id": "trace-dev-source-freshness",
  "document_type": "runbook",
  "title": "Checking source freshness and gaps",
  "service": "order",
  "environment": "test",
  "source_uri": "synthetic://trace-knowledge/source-freshness",
  "source_record_id": "reference/source-freshness",
  "source_revision": "2026-10-12.v1",
  "version": "1.0.0",
  "provenance": "TRACE-authored development reference; fictional history where explicitly stated",
  "access_scope": "local:knowledge-development",
  "access_classification": "synthetic_public",
  "evaluation_role": "development_reference",
  "answer_bearing": false,
  "valid_from": "2026-01-01T00:00:00Z",
  "valid_until": null,
  "verified_at": "2026-10-12T12:00:00Z",
  "fresh_until": "2026-11-12T12:00:00Z"
}
```

Original offsets: 493–746.

> # Recheck
> A saved citation must still resolve under current permissions and source freshness. If a source is withdrawn or no longer fresh, report that limitation and request an authorized revalidation. An old snapshot is not standing access permission.

## Review targets

### exact-code

Query: HTTP 504 /v1/orders: what do the exact code and path establish?

Family/category: exact-code / exact_code; service filter: None.

Relevance target: `relevance:exact-code`.

Proposed relevant passages: `chunk-9bb28e983e90fa34b2f00798cf4c3b8a1b27d03181b24dc3c0fbab6bf7350abe`, `chunk-97ea9848b883f7631587f97016ac45d37821152f9a2fd4bb97524625eec712fa`.

Claim target: `support:exact-code:chunk-9bb28e983e90fa34b2f00798cf4c3b8a1b27d03181b24dc3c0fbab6bf7350abe`.

Claim: Exact HTTP 504 codes and /v1/orders paths should be preserved.

Proposed verdict: **supported**.

Claim target: `support:exact-code:chunk-97ea9848b883f7631587f97016ac45d37821152f9a2fd4bb97524625eec712fa`.

Claim: HTTP 504 is a symptom code, not a root-cause label.

Proposed verdict: **supported**.

### negation-order

Query: Does a Notification deployment near an Order error prove Notification caused it?

Family/category: negation-order / negation; service filter: order.

Relevance target: `relevance:negation-order`.

Proposed relevant passages: `chunk-3bcd76338ebe1579510d564f6f648afd1ceb859dc121564efbb701307fa81538`.

Claim target: `support:negation-order:chunk-3bcd76338ebe1579510d564f6f648afd1ceb859dc121564efbb701307fa81538`.

Claim: Notification caused the Order error because its deployment was nearby.

Proposed verdict: **unsupported**.

### negation-certificate

Query: Did the nearby Notification rollout cause Payment failures in the fictional certificate archive?

Family/category: negation-certificate / misleading; service filter: payment.

Relevance target: `relevance:negation-certificate`.

Proposed relevant passages: `chunk-b80174ddde722d6ccd694bccf44b7a681036d7410d340c8ff7e9c304204a638c`.

Claim target: `support:negation-certificate:chunk-b80174ddde722d6ccd694bccf44b7a681036d7410d340c8ff7e9c304204a638c`.

Claim: The archived records did not support a causal connection to Notification.

Proposed verdict: **supported**.

### service-boundary

Query: Which service receives a positive amount, and how do work results differ from caller deadlines?

Family/category: service-boundary / service_ambiguity; service filter: payment.

Relevance target: `relevance:service-boundary`.

Proposed relevant passages: `chunk-87083ef5e8c7c9f7934ab9eee09f30243eceac1a2bb398166182b0f18efb39e8`.

Claim target: `support:service-boundary:chunk-87083ef5e8c7c9f7934ab9eee09f30243eceac1a2bb398166182b0f18efb39e8`.

Claim: Payment work results and caller deadlines are separate observations.

Proposed verdict: **supported**.

### request-path

Query: Which services handle an accepted order before the notification is dispatched?

Family/category: request-path / answerable; service filter: order.

Relevance target: `relevance:request-path`.

Proposed relevant passages: `chunk-a38ad3f58e817f8c656d0c027be95c8a4d56665062d074ae6c065355716c7574`.

Claim target: `support:request-path:chunk-a38ad3f58e817f8c656d0c027be95c8a4d56665062d074ae6c065355716c7574`.

Claim: Order asks Customer, invokes Payment, then dispatches Notification after success.

Proposed verdict: **supported**.

### collection-delay

Query: Which timestamp belongs on a timeline when source collection arrives late?

Family/category: collection-delay / answerable; service filter: order.

Relevance target: `relevance:collection-delay`.

Proposed relevant passages: `chunk-d2228cb1127d51fbf4d5d21c99c8a31d14411ebe37907a9fd0057dc6605bd8af`.

Claim target: `support:collection-delay:chunk-d2228cb1127d51fbf4d5d21c99c8a31d14411ebe37907a9fd0057dc6605bd8af`.

Claim: Observed event time determines the timeline; collection time remains provenance.

Proposed verdict: **supported**.

### saved-permission

Query: Can a saved citation bypass withdrawn permissions or source freshness?

Family/category: saved-permission / answerable; service filter: order.

Relevance target: `relevance:saved-permission`.

Proposed relevant passages: `chunk-f3dded5575d6ece71420e0371428faaf0dcfeb0fb2efb0e4db97782c18aee6ce`.

Claim target: `support:saved-permission:chunk-f3dded5575d6ece71420e0371428faaf0dcfeb0fb2efb0e4db97782c18aee6ce`.

Claim: A saved citation must still pass current permission and freshness checks.

Proposed verdict: **supported**.

### queue-health

Query: What did the fictional queue archive retain when dependencies were healthy but the worker was paused?

Family/category: queue-health / answerable; service filter: order.

Relevance target: `relevance:queue-health`.

Proposed relevant passages: `chunk-e2debbd2df4c20f2624bb63dcb8bc6b97e9e9e8fbfdabddaaf1607323574a748`.

Claim target: `support:queue-health:chunk-e2debbd2df4c20f2624bb63dcb8bc6b97e9e9e8fbfdabddaaf1607323574a748`.

Claim: The archive attributed backlog to a paused worker using retained worker state.

Proposed verdict: **supported**.

### missing-evidence

Query: What should be reported when neither configuration nor downstream duration is observable?

Family/category: missing-evidence / answerable; service filter: payment.

Relevance target: `relevance:missing-evidence`.

Proposed relevant passages: `chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`, `chunk-c8ccd466e62a6a323e6b9b89dde5065525370ff1fcca7a4999f51d243098a96b`.

Claim target: `support:missing-evidence:chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`.

Claim: Missing configuration or duration observations can leave competing explanations indistinguishable.

Proposed verdict: **supported**.

Claim target: `support:missing-evidence:chunk-c8ccd466e62a6a323e6b9b89dde5065525370ff1fcca7a4999f51d243098a96b`.

Claim: Missing configuration or duration observations can leave competing explanations indistinguishable.

Proposed verdict: **supported**.

### historical-transfer

Query: Does the fictional archive establish that the current live worker is paused?

Family/category: historical-transfer / misleading; service filter: order.

Relevance target: `relevance:historical-transfer`.

Proposed relevant passages: `chunk-7952c735c44e632f1f4314d0aa0bffcaf390c3006a23af2a007c0d09a4b7aed9`.

Claim target: `support:historical-transfer:chunk-7952c735c44e632f1f4314d0aa0bffcaf390c3006a23af2a007c0d09a4b7aed9`.

Claim: The archived paused worker is a fact about the current live incident.

Proposed verdict: **unsupported**.

### production-approval

Query: Does a timeout symptom authorize changing production configuration?

Family/category: production-approval / misleading; service filter: payment.

Relevance target: `relevance:production-approval`.

Proposed relevant passages: `chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`.

Claim target: `support:production-approval:chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`.

Claim: Suggested evidence checks authorize a production configuration change.

Proposed verdict: **unsupported**.

### service-identity

Query: Does a correlation ID make all receiving boundaries the same service?

Family/category: service-identity / service_ambiguity; service filter: order.

Relevance target: `relevance:service-identity`.

Proposed relevant passages: `chunk-ab1aed6f89a2841d256dc1b1329689c8db0663363d23115949db1ab7a44698cd`.

Claim target: `support:service-identity:chunk-ab1aed6f89a2841d256dc1b1329689c8db0663363d23115949db1ab7a44698cd`.

Claim: Service identity changes at the receiving boundary while correlation is preserved.

Proposed verdict: **supported**.

### absent-database

Query: PostgreSQL WAL archive recovery commands and replication slots

Family/category: absent-database / absent_knowledge; service filter: None.

Relevance target: `relevance:absent-database`.

Proposed relevant passages: none.

### absent-notification

Query: Notification webhook signature algorithm and rate-limit retry configuration

Family/category: absent-notification / absent_knowledge; service filter: None.

Relevance target: `relevance:absent-notification`.

Proposed relevant passages: none.

### stale-certificate

Query: What currently permitted evidence describes TLS certificate expiry during rollover?

Family/category: stale-certificate / stale_source; service filter: payment.

Relevance target: `relevance:stale-certificate`.

Proposed relevant passages: none.

### exact-code-1

Query: Why should HTTP 504 and /v1/orders be retained verbatim in timeout evidence?

Family/category: exact-code / exact_code; service filter: None.

Relevance target: `relevance:exact-code-1`.

Proposed relevant passages: `chunk-9bb28e983e90fa34b2f00798cf4c3b8a1b27d03181b24dc3c0fbab6bf7350abe`, `chunk-97ea9848b883f7631587f97016ac45d37821152f9a2fd4bb97524625eec712fa`.

Claim target: `support:exact-code-1:chunk-9bb28e983e90fa34b2f00798cf4c3b8a1b27d03181b24dc3c0fbab6bf7350abe`.

Claim: Exact HTTP 504 codes and /v1/orders paths should be preserved.

Proposed verdict: **supported**.

Claim target: `support:exact-code-1:chunk-97ea9848b883f7631587f97016ac45d37821152f9a2fd4bb97524625eec712fa`.

Claim: HTTP 504 is a symptom code, not a root-cause label.

Proposed verdict: **supported**.

### exact-code-2

Query: Does an HTTP 504 response identify the failing configuration or only a symptom?

Family/category: exact-code / exact_code; service filter: None.

Relevance target: `relevance:exact-code-2`.

Proposed relevant passages: `chunk-9bb28e983e90fa34b2f00798cf4c3b8a1b27d03181b24dc3c0fbab6bf7350abe`, `chunk-97ea9848b883f7631587f97016ac45d37821152f9a2fd4bb97524625eec712fa`.

Claim target: `support:exact-code-2:chunk-9bb28e983e90fa34b2f00798cf4c3b8a1b27d03181b24dc3c0fbab6bf7350abe`.

Claim: Exact HTTP 504 codes and /v1/orders paths should be preserved.

Proposed verdict: **supported**.

Claim target: `support:exact-code-2:chunk-97ea9848b883f7631587f97016ac45d37821152f9a2fd4bb97524625eec712fa`.

Claim: HTTP 504 is a symptom code, not a root-cause label.

Proposed verdict: **supported**.

### exact-code-3

Query: Which reference distinguishes HTTP 504 symptoms from causal labels?

Family/category: exact-code / exact_code; service filter: None.

Relevance target: `relevance:exact-code-3`.

Proposed relevant passages: `chunk-9bb28e983e90fa34b2f00798cf4c3b8a1b27d03181b24dc3c0fbab6bf7350abe`, `chunk-97ea9848b883f7631587f97016ac45d37821152f9a2fd4bb97524625eec712fa`.

Claim target: `support:exact-code-3:chunk-9bb28e983e90fa34b2f00798cf4c3b8a1b27d03181b24dc3c0fbab6bf7350abe`.

Claim: Exact HTTP 504 codes and /v1/orders paths should be preserved.

Proposed verdict: **supported**.

Claim target: `support:exact-code-3:chunk-97ea9848b883f7631587f97016ac45d37821152f9a2fd4bb97524625eec712fa`.

Claim: HTTP 504 is a symptom code, not a root-cause label.

Proposed verdict: **supported**.

### exact-code-4

Query: How should /v1/orders errors be compared with request work duration?

Family/category: exact-code / exact_code; service filter: None.

Relevance target: `relevance:exact-code-4`.

Proposed relevant passages: `chunk-9bb28e983e90fa34b2f00798cf4c3b8a1b27d03181b24dc3c0fbab6bf7350abe`, `chunk-97ea9848b883f7631587f97016ac45d37821152f9a2fd4bb97524625eec712fa`.

Claim target: `support:exact-code-4:chunk-9bb28e983e90fa34b2f00798cf4c3b8a1b27d03181b24dc3c0fbab6bf7350abe`.

Claim: Exact HTTP 504 codes and /v1/orders paths should be preserved.

Proposed verdict: **supported**.

Claim target: `support:exact-code-4:chunk-97ea9848b883f7631587f97016ac45d37821152f9a2fd4bb97524625eec712fa`.

Claim: HTTP 504 is a symptom code, not a root-cause label.

Proposed verdict: **supported**.

### exact-code-5

Query: What evidence vocabulary accompanies an exact HTTP 504 failure code?

Family/category: exact-code / exact_code; service filter: None.

Relevance target: `relevance:exact-code-5`.

Proposed relevant passages: `chunk-9bb28e983e90fa34b2f00798cf4c3b8a1b27d03181b24dc3c0fbab6bf7350abe`, `chunk-97ea9848b883f7631587f97016ac45d37821152f9a2fd4bb97524625eec712fa`.

Claim target: `support:exact-code-5:chunk-9bb28e983e90fa34b2f00798cf4c3b8a1b27d03181b24dc3c0fbab6bf7350abe`.

Claim: Exact HTTP 504 codes and /v1/orders paths should be preserved.

Proposed verdict: **supported**.

Claim target: `support:exact-code-5:chunk-97ea9848b883f7631587f97016ac45d37821152f9a2fd4bb97524625eec712fa`.

Claim: HTTP 504 is a symptom code, not a root-cause label.

Proposed verdict: **supported**.

### exact-code-6

Query: Can rewriting HTTP 504 into a causal label lose incident evidence?

Family/category: exact-code / exact_code; service filter: None.

Relevance target: `relevance:exact-code-6`.

Proposed relevant passages: `chunk-9bb28e983e90fa34b2f00798cf4c3b8a1b27d03181b24dc3c0fbab6bf7350abe`, `chunk-97ea9848b883f7631587f97016ac45d37821152f9a2fd4bb97524625eec712fa`.

Claim target: `support:exact-code-6:chunk-9bb28e983e90fa34b2f00798cf4c3b8a1b27d03181b24dc3c0fbab6bf7350abe`.

Claim: Exact HTTP 504 codes and /v1/orders paths should be preserved.

Proposed verdict: **supported**.

Claim target: `support:exact-code-6:chunk-97ea9848b883f7631587f97016ac45d37821152f9a2fd4bb97524625eec712fa`.

Claim: HTTP 504 is a symptom code, not a root-cause label.

Proposed verdict: **supported**.

### negation-order-1

Query: Is nearby Notification activity sufficient evidence of an Order root cause?

Family/category: negation-order / negation; service filter: order.

Relevance target: `relevance:negation-order-1`.

Proposed relevant passages: `chunk-3bcd76338ebe1579510d564f6f648afd1ceb859dc121564efbb701307fa81538`.

Claim target: `support:negation-order-1:chunk-3bcd76338ebe1579510d564f6f648afd1ceb859dc121564efbb701307fa81538`.

Claim: Notification caused the Order error because its deployment was nearby.

Proposed verdict: **unsupported**.

### negation-order-2

Query: What does Order documentation say about blaming a nearby Notification rollout?

Family/category: negation-order / negation; service filter: order.

Relevance target: `relevance:negation-order-2`.

Proposed relevant passages: `chunk-3bcd76338ebe1579510d564f6f648afd1ceb859dc121564efbb701307fa81538`.

Claim target: `support:negation-order-2:chunk-3bcd76338ebe1579510d564f6f648afd1ceb859dc121564efbb701307fa81538`.

Claim: Notification caused the Order error because its deployment was nearby.

Proposed verdict: **unsupported**.

### negation-order-3

Query: Does timing alone connect a Notification deployment to an Order error?

Family/category: negation-order / negation; service filter: order.

Relevance target: `relevance:negation-order-3`.

Proposed relevant passages: `chunk-3bcd76338ebe1579510d564f6f648afd1ceb859dc121564efbb701307fa81538`.

Claim target: `support:negation-order-3:chunk-3bcd76338ebe1579510d564f6f648afd1ceb859dc121564efbb701307fa81538`.

Claim: Notification caused the Order error because its deployment was nearby.

Proposed verdict: **unsupported**.

### negation-order-4

Query: Can I conclude Notification caused Order failures from a recent deployment?

Family/category: negation-order / negation; service filter: order.

Relevance target: `relevance:negation-order-4`.

Proposed relevant passages: `chunk-3bcd76338ebe1579510d564f6f648afd1ceb859dc121564efbb701307fa81538`.

Claim target: `support:negation-order-4:chunk-3bcd76338ebe1579510d564f6f648afd1ceb859dc121564efbb701307fa81538`.

Claim: Notification caused the Order error because its deployment was nearby.

Proposed verdict: **unsupported**.

### negation-order-5

Query: Is Notification causal merely because it appeared close to the error?

Family/category: negation-order / negation; service filter: order.

Relevance target: `relevance:negation-order-5`.

Proposed relevant passages: `chunk-3bcd76338ebe1579510d564f6f648afd1ceb859dc121564efbb701307fa81538`.

Claim target: `support:negation-order-5:chunk-3bcd76338ebe1579510d564f6f648afd1ceb859dc121564efbb701307fa81538`.

Claim: Notification caused the Order error because its deployment was nearby.

Proposed verdict: **unsupported**.

### negation-order-6

Query: Which Order reference warns against inferring cause from Notification timing?

Family/category: negation-order / negation; service filter: order.

Relevance target: `relevance:negation-order-6`.

Proposed relevant passages: `chunk-3bcd76338ebe1579510d564f6f648afd1ceb859dc121564efbb701307fa81538`.

Claim target: `support:negation-order-6:chunk-3bcd76338ebe1579510d564f6f648afd1ceb859dc121564efbb701307fa81538`.

Claim: Notification caused the Order error because its deployment was nearby.

Proposed verdict: **unsupported**.

### negation-certificate-1

Query: Was Notification implicated by records in the fictional certificate investigation?

Family/category: negation-certificate / misleading; service filter: payment.

Relevance target: `relevance:negation-certificate-1`.

Proposed relevant passages: `chunk-b80174ddde722d6ccd694bccf44b7a681036d7410d340c8ff7e9c304204a638c`.

Claim target: `support:negation-certificate-1:chunk-b80174ddde722d6ccd694bccf44b7a681036d7410d340c8ff7e9c304204a638c`.

Claim: The archived records did not support a causal connection to Notification.

Proposed verdict: **supported**.

### negation-certificate-2

Query: What explanation did the certificate archive reject despite a nearby rollout?

Family/category: negation-certificate / misleading; service filter: payment.

Relevance target: `relevance:negation-certificate-2`.

Proposed relevant passages: `chunk-b80174ddde722d6ccd694bccf44b7a681036d7410d340c8ff7e9c304204a638c`.

Claim target: `support:negation-certificate-2:chunk-b80174ddde722d6ccd694bccf44b7a681036d7410d340c8ff7e9c304204a638c`.

Claim: The archived records did not support a causal connection to Notification.

Proposed verdict: **supported**.

### negation-certificate-3

Query: Did the archived Payment TLS failures have a supported Notification connection?

Family/category: negation-certificate / misleading; service filter: payment.

Relevance target: `relevance:negation-certificate-3`.

Proposed relevant passages: `chunk-b80174ddde722d6ccd694bccf44b7a681036d7410d340c8ff7e9c304204a638c`.

Claim target: `support:negation-certificate-3:chunk-b80174ddde722d6ccd694bccf44b7a681036d7410d340c8ff7e9c304204a638c`.

Claim: The archived records did not support a causal connection to Notification.

Proposed verdict: **supported**.

### negation-certificate-4

Query: How did the fictional certificate archive treat the Notification rollout?

Family/category: negation-certificate / misleading; service filter: payment.

Relevance target: `relevance:negation-certificate-4`.

Proposed relevant passages: `chunk-b80174ddde722d6ccd694bccf44b7a681036d7410d340c8ff7e9c304204a638c`.

Claim target: `support:negation-certificate-4:chunk-b80174ddde722d6ccd694bccf44b7a681036d7410d340c8ff7e9c304204a638c`.

Claim: The archived records did not support a causal connection to Notification.

Proposed verdict: **supported**.

### negation-certificate-5

Query: What did the archive retain about TLS validity and the nearby Notification change?

Family/category: negation-certificate / misleading; service filter: payment.

Relevance target: `relevance:negation-certificate-5`.

Proposed relevant passages: `chunk-b80174ddde722d6ccd694bccf44b7a681036d7410d340c8ff7e9c304204a638c`.

Claim target: `support:negation-certificate-5:chunk-b80174ddde722d6ccd694bccf44b7a681036d7410d340c8ff7e9c304204a638c`.

Claim: The archived records did not support a causal connection to Notification.

Proposed verdict: **supported**.

### negation-certificate-6

Query: Can the Payment certificate example substantiate Notification as the cause?

Family/category: negation-certificate / misleading; service filter: payment.

Relevance target: `relevance:negation-certificate-6`.

Proposed relevant passages: `chunk-b80174ddde722d6ccd694bccf44b7a681036d7410d340c8ff7e9c304204a638c`.

Claim target: `support:negation-certificate-6:chunk-b80174ddde722d6ccd694bccf44b7a681036d7410d340c8ff7e9c304204a638c`.

Claim: The archived records did not support a causal connection to Notification.

Proposed verdict: **supported**.

### service-boundary-1

Query: What does the Payment fixture receive at its request boundary?

Family/category: service-boundary / service_ambiguity; service filter: payment.

Relevance target: `relevance:service-boundary-1`.

Proposed relevant passages: `chunk-87083ef5e8c7c9f7934ab9eee09f30243eceac1a2bb398166182b0f18efb39e8`.

Claim target: `support:service-boundary-1:chunk-87083ef5e8c7c9f7934ab9eee09f30243eceac1a2bb398166182b0f18efb39e8`.

Claim: Payment work results and caller deadlines are separate observations.

Proposed verdict: **supported**.

### service-boundary-2

Query: Are the Payment work result and caller deadline the same observation?

Family/category: service-boundary / service_ambiguity; service filter: payment.

Relevance target: `relevance:service-boundary-2`.

Proposed relevant passages: `chunk-87083ef5e8c7c9f7934ab9eee09f30243eceac1a2bb398166182b0f18efb39e8`.

Claim target: `support:service-boundary-2:chunk-87083ef5e8c7c9f7934ab9eee09f30243eceac1a2bb398166182b0f18efb39e8`.

Claim: Payment work results and caller deadlines are separate observations.

Proposed verdict: **supported**.

### service-boundary-3

Query: How does Payment separate positive amount input from the caller time limit?

Family/category: service-boundary / service_ambiguity; service filter: payment.

Relevance target: `relevance:service-boundary-3`.

Proposed relevant passages: `chunk-87083ef5e8c7c9f7934ab9eee09f30243eceac1a2bb398166182b0f18efb39e8`.

Claim target: `support:service-boundary-3:chunk-87083ef5e8c7c9f7934ab9eee09f30243eceac1a2bb398166182b0f18efb39e8`.

Claim: Payment work results and caller deadlines are separate observations.

Proposed verdict: **supported**.

### service-boundary-4

Query: Does Payment charge real money in the development request fixture?

Family/category: service-boundary / service_ambiguity; service filter: payment.

Relevance target: `relevance:service-boundary-4`.

Proposed relevant passages: `chunk-87083ef5e8c7c9f7934ab9eee09f30243eceac1a2bb398166182b0f18efb39e8`.

Claim target: `support:service-boundary-4:chunk-87083ef5e8c7c9f7934ab9eee09f30243eceac1a2bb398166182b0f18efb39e8`.

Claim: Payment work results and caller deadlines are separate observations.

Proposed verdict: **supported**.

### service-boundary-5

Query: Which Payment boundary documents positive amounts and separate deadline results?

Family/category: service-boundary / service_ambiguity; service filter: payment.

Relevance target: `relevance:service-boundary-5`.

Proposed relevant passages: `chunk-87083ef5e8c7c9f7934ab9eee09f30243eceac1a2bb398166182b0f18efb39e8`.

Claim target: `support:service-boundary-5:chunk-87083ef5e8c7c9f7934ab9eee09f30243eceac1a2bb398166182b0f18efb39e8`.

Claim: Payment work results and caller deadlines are separate observations.

Proposed verdict: **supported**.

### service-boundary-6

Query: Where are order ID, positive amount and caller deadline distinguished?

Family/category: service-boundary / service_ambiguity; service filter: payment.

Relevance target: `relevance:service-boundary-6`.

Proposed relevant passages: `chunk-87083ef5e8c7c9f7934ab9eee09f30243eceac1a2bb398166182b0f18efb39e8`.

Claim target: `support:service-boundary-6:chunk-87083ef5e8c7c9f7934ab9eee09f30243eceac1a2bb398166182b0f18efb39e8`.

Claim: Payment work results and caller deadlines are separate observations.

Proposed verdict: **supported**.

### request-path-1

Query: When does Order send the in-process Notification after Payment?

Family/category: request-path / answerable; service filter: order.

Relevance target: `relevance:request-path-1`.

Proposed relevant passages: `chunk-a38ad3f58e817f8c656d0c027be95c8a4d56665062d074ae6c065355716c7574`.

Claim target: `support:request-path-1:chunk-a38ad3f58e817f8c656d0c027be95c8a4d56665062d074ae6c065355716c7574`.

Claim: Order asks Customer, invokes Payment, then dispatches Notification after success.

Proposed verdict: **supported**.

### request-path-2

Query: Which request arguments does Order accept before asking Customer?

Family/category: request-path / answerable; service filter: order.

Relevance target: `relevance:request-path-2`.

Proposed relevant passages: `chunk-a38ad3f58e817f8c656d0c027be95c8a4d56665062d074ae6c065355716c7574`.

Claim target: `support:request-path-2:chunk-a38ad3f58e817f8c656d0c027be95c8a4d56665062d074ae6c065355716c7574`.

Claim: Order asks Customer, invokes Payment, then dispatches Notification after success.

Proposed verdict: **supported**.

### request-path-3

Query: How are Customer eligibility and Payment invoked on the Order path?

Family/category: request-path / answerable; service filter: order.

Relevance target: `relevance:request-path-3`.

Proposed relevant passages: `chunk-a38ad3f58e817f8c656d0c027be95c8a4d56665062d074ae6c065355716c7574`.

Claim target: `support:request-path-3:chunk-a38ad3f58e817f8c656d0c027be95c8a4d56665062d074ae6c065355716c7574`.

Claim: Order asks Customer, invokes Payment, then dispatches Notification after success.

Proposed verdict: **supported**.

### request-path-4

Query: What happens after an Order payment succeeds?

Family/category: request-path / answerable; service filter: order.

Relevance target: `relevance:request-path-4`.

Proposed relevant passages: `chunk-a38ad3f58e817f8c656d0c027be95c8a4d56665062d074ae6c065355716c7574`.

Claim target: `support:request-path-4:chunk-a38ad3f58e817f8c656d0c027be95c8a4d56665062d074ae6c065355716c7574`.

Claim: Order asks Customer, invokes Payment, then dispatches Notification after success.

Proposed verdict: **supported**.

### request-path-5

Query: What is the Customer to Payment to Notification sequence for Order?

Family/category: request-path / answerable; service filter: order.

Relevance target: `relevance:request-path-5`.

Proposed relevant passages: `chunk-a38ad3f58e817f8c656d0c027be95c8a4d56665062d074ae6c065355716c7574`.

Claim target: `support:request-path-5:chunk-a38ad3f58e817f8c656d0c027be95c8a4d56665062d074ae6c065355716c7574`.

Claim: Order asks Customer, invokes Payment, then dispatches Notification after success.

Proposed verdict: **supported**.

### request-path-6

Query: Does the development Order request dispatch Notification before payment succeeds?

Family/category: request-path / answerable; service filter: order.

Relevance target: `relevance:request-path-6`.

Proposed relevant passages: `chunk-a38ad3f58e817f8c656d0c027be95c8a4d56665062d074ae6c065355716c7574`.

Claim target: `support:request-path-6:chunk-a38ad3f58e817f8c656d0c027be95c8a4d56665062d074ae6c065355716c7574`.

Claim: Order asks Customer, invokes Payment, then dispatches Notification after success.

Proposed verdict: **supported**.

### collection-delay-1

Query: Does delayed collection move the operational event later on the timeline?

Family/category: collection-delay / answerable; service filter: order.

Relevance target: `relevance:collection-delay-1`.

Proposed relevant passages: `chunk-d2228cb1127d51fbf4d5d21c99c8a31d14411ebe37907a9fd0057dc6605bd8af`.

Claim target: `support:collection-delay-1:chunk-d2228cb1127d51fbf4d5d21c99c8a31d14411ebe37907a9fd0057dc6605bd8af`.

Claim: Observed event time determines the timeline; collection time remains provenance.

Proposed verdict: **supported**.

### collection-delay-2

Query: Which clock is used for events and which clock preserves source collection?

Family/category: collection-delay / answerable; service filter: order.

Relevance target: `relevance:collection-delay-2`.

Proposed relevant passages: `chunk-d2228cb1127d51fbf4d5d21c99c8a31d14411ebe37907a9fd0057dc6605bd8af`.

Claim target: `support:collection-delay-2:chunk-d2228cb1127d51fbf4d5d21c99c8a31d14411ebe37907a9fd0057dc6605bd8af`.

Claim: Observed event time determines the timeline; collection time remains provenance.

Proposed verdict: **supported**.

### collection-delay-3

Query: How should observed event time and collection time be distinguished?

Family/category: collection-delay / answerable; service filter: order.

Relevance target: `relevance:collection-delay-3`.

Proposed relevant passages: `chunk-d2228cb1127d51fbf4d5d21c99c8a31d14411ebe37907a9fd0057dc6605bd8af`.

Claim target: `support:collection-delay-3:chunk-d2228cb1127d51fbf4d5d21c99c8a31d14411ebe37907a9fd0057dc6605bd8af`.

Claim: Observed event time determines the timeline; collection time remains provenance.

Proposed verdict: **supported**.

### collection-delay-4

Query: What source identity and revision should accompany a delayed record?

Family/category: collection-delay / answerable; service filter: order.

Relevance target: `relevance:collection-delay-4`.

Proposed relevant passages: `chunk-d2228cb1127d51fbf4d5d21c99c8a31d14411ebe37907a9fd0057dc6605bd8af`.

Claim target: `support:collection-delay-4:chunk-d2228cb1127d51fbf4d5d21c99c8a31d14411ebe37907a9fd0057dc6605bd8af`.

Claim: Observed event time determines the timeline; collection time remains provenance.

Proposed verdict: **supported**.

### collection-delay-5

Query: Should late-arriving logs be ordered by observed or collection time?

Family/category: collection-delay / answerable; service filter: order.

Relevance target: `relevance:collection-delay-5`.

Proposed relevant passages: `chunk-d2228cb1127d51fbf4d5d21c99c8a31d14411ebe37907a9fd0057dc6605bd8af`.

Claim target: `support:collection-delay-5:chunk-d2228cb1127d51fbf4d5d21c99c8a31d14411ebe37907a9fd0057dc6605bd8af`.

Claim: Observed event time determines the timeline; collection time remains provenance.

Proposed verdict: **supported**.

### collection-delay-6

Query: Can a delayed collection timestamp imply a later incident event?

Family/category: collection-delay / answerable; service filter: order.

Relevance target: `relevance:collection-delay-6`.

Proposed relevant passages: `chunk-d2228cb1127d51fbf4d5d21c99c8a31d14411ebe37907a9fd0057dc6605bd8af`.

Claim target: `support:collection-delay-6:chunk-d2228cb1127d51fbf4d5d21c99c8a31d14411ebe37907a9fd0057dc6605bd8af`.

Claim: Observed event time determines the timeline; collection time remains provenance.

Proposed verdict: **supported**.

### saved-permission-1

Query: Does a previously saved snapshot provide standing access permission?

Family/category: saved-permission / answerable; service filter: order.

Relevance target: `relevance:saved-permission-1`.

Proposed relevant passages: `chunk-f3dded5575d6ece71420e0371428faaf0dcfeb0fb2efb0e4db97782c18aee6ce`.

Claim target: `support:saved-permission-1:chunk-f3dded5575d6ece71420e0371428faaf0dcfeb0fb2efb0e4db97782c18aee6ce`.

Claim: A saved citation must still pass current permission and freshness checks.

Proposed verdict: **supported**.

### saved-permission-2

Query: What should happen when an old citation source is no longer fresh?

Family/category: saved-permission / answerable; service filter: order.

Relevance target: `relevance:saved-permission-2`.

Proposed relevant passages: `chunk-f3dded5575d6ece71420e0371428faaf0dcfeb0fb2efb0e4db97782c18aee6ce`.

Claim target: `support:saved-permission-2:chunk-f3dded5575d6ece71420e0371428faaf0dcfeb0fb2efb0e4db97782c18aee6ce`.

Claim: A saved citation must still pass current permission and freshness checks.

Proposed verdict: **supported**.

### saved-permission-3

Query: How are saved references rechecked after source withdrawal?

Family/category: saved-permission / answerable; service filter: order.

Relevance target: `relevance:saved-permission-3`.

Proposed relevant passages: `chunk-f3dded5575d6ece71420e0371428faaf0dcfeb0fb2efb0e4db97782c18aee6ce`.

Claim target: `support:saved-permission-3:chunk-f3dded5575d6ece71420e0371428faaf0dcfeb0fb2efb0e4db97782c18aee6ce`.

Claim: A saved citation must still pass current permission and freshness checks.

Proposed verdict: **supported**.

### saved-permission-4

Query: Can I bypass current scope checks by reading a historical citation?

Family/category: saved-permission / answerable; service filter: order.

Relevance target: `relevance:saved-permission-4`.

Proposed relevant passages: `chunk-f3dded5575d6ece71420e0371428faaf0dcfeb0fb2efb0e4db97782c18aee6ce`.

Claim target: `support:saved-permission-4:chunk-f3dded5575d6ece71420e0371428faaf0dcfeb0fb2efb0e4db97782c18aee6ce`.

Claim: A saved citation must still pass current permission and freshness checks.

Proposed verdict: **supported**.

### saved-permission-5

Query: What limitation should be disclosed for a withdrawn source reference?

Family/category: saved-permission / answerable; service filter: order.

Relevance target: `relevance:saved-permission-5`.

Proposed relevant passages: `chunk-f3dded5575d6ece71420e0371428faaf0dcfeb0fb2efb0e4db97782c18aee6ce`.

Claim target: `support:saved-permission-5:chunk-f3dded5575d6ece71420e0371428faaf0dcfeb0fb2efb0e4db97782c18aee6ce`.

Claim: A saved citation must still pass current permission and freshness checks.

Proposed verdict: **supported**.

### saved-permission-6

Query: When should a source citation request authorized revalidation?

Family/category: saved-permission / answerable; service filter: order.

Relevance target: `relevance:saved-permission-6`.

Proposed relevant passages: `chunk-f3dded5575d6ece71420e0371428faaf0dcfeb0fb2efb0e4db97782c18aee6ce`.

Claim target: `support:saved-permission-6:chunk-f3dded5575d6ece71420e0371428faaf0dcfeb0fb2efb0e4db97782c18aee6ce`.

Claim: A saved citation must still pass current permission and freshness checks.

Proposed verdict: **supported**.

### queue-health-1

Query: What distinguished the paused-worker explanation in the fictional queue note?

Family/category: queue-health / answerable; service filter: order.

Relevance target: `relevance:queue-health-1`.

Proposed relevant passages: `chunk-e2debbd2df4c20f2624bb63dcb8bc6b97e9e9e8fbfdabddaaf1607323574a748`.

Claim target: `support:queue-health-1:chunk-e2debbd2df4c20f2624bb63dcb8bc6b97e9e9e8fbfdabddaaf1607323574a748`.

Claim: The archive attributed backlog to a paused worker using retained worker state.

Proposed verdict: **supported**.

### queue-health-2

Query: Was the downstream dependency healthy while the archived Order queue grew?

Family/category: queue-health / answerable; service filter: order.

Relevance target: `relevance:queue-health-2`.

Proposed relevant passages: `chunk-e2debbd2df4c20f2624bb63dcb8bc6b97e9e9e8fbfdabddaaf1607323574a748`.

Claim target: `support:queue-health-2:chunk-e2debbd2df4c20f2624bb63dcb8bc6b97e9e9e8fbfdabddaaf1607323574a748`.

Claim: The archive attributed backlog to a paused worker using retained worker state.

Proposed verdict: **supported**.

### queue-health-3

Query: Which retained worker state explained the fictional backlog?

Family/category: queue-health / answerable; service filter: order.

Relevance target: `relevance:queue-health-3`.

Proposed relevant passages: `chunk-e2debbd2df4c20f2624bb63dcb8bc6b97e9e9e8fbfdabddaaf1607323574a748`.

Claim target: `support:queue-health-3:chunk-e2debbd2df4c20f2624bb63dcb8bc6b97e9e9e8fbfdabddaaf1607323574a748`.

Claim: The archive attributed backlog to a paused worker using retained worker state.

Proposed verdict: **supported**.

### queue-health-4

Query: Did a Payment deployment alone establish the archived queue explanation?

Family/category: queue-health / answerable; service filter: order.

Relevance target: `relevance:queue-health-4`.

Proposed relevant passages: `chunk-e2debbd2df4c20f2624bb63dcb8bc6b97e9e9e8fbfdabddaaf1607323574a748`.

Claim target: `support:queue-health-4:chunk-e2debbd2df4c20f2624bb63dcb8bc6b97e9e9e8fbfdabddaaf1607323574a748`.

Claim: The archive attributed backlog to a paused worker using retained worker state.

Proposed verdict: **supported**.

### queue-health-5

Query: How did queue growth, completions and dependency health differ in the archive?

Family/category: queue-health / answerable; service filter: order.

Relevance target: `relevance:queue-health-5`.

Proposed relevant passages: `chunk-e2debbd2df4c20f2624bb63dcb8bc6b97e9e9e8fbfdabddaaf1607323574a748`.

Claim target: `support:queue-health-5:chunk-e2debbd2df4c20f2624bb63dcb8bc6b97e9e9e8fbfdabddaaf1607323574a748`.

Claim: The archive attributed backlog to a paused worker using retained worker state.

Proposed verdict: **supported**.

### queue-health-6

Query: What supported the historical paused-worker attribution?

Family/category: queue-health / answerable; service filter: order.

Relevance target: `relevance:queue-health-6`.

Proposed relevant passages: `chunk-e2debbd2df4c20f2624bb63dcb8bc6b97e9e9e8fbfdabddaaf1607323574a748`.

Claim target: `support:queue-health-6:chunk-e2debbd2df4c20f2624bb63dcb8bc6b97e9e9e8fbfdabddaaf1607323574a748`.

Claim: The archive attributed backlog to a paused worker using retained worker state.

Proposed verdict: **supported**.

### missing-evidence-1

Query: Can absent budget and duration evidence distinguish timeout mechanisms?

Family/category: missing-evidence / answerable; service filter: payment.

Relevance target: `relevance:missing-evidence-1`.

Proposed relevant passages: `chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`, `chunk-c8ccd466e62a6a323e6b9b89dde5065525370ff1fcca7a4999f51d243098a96b`.

Claim target: `support:missing-evidence-1:chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`.

Claim: Missing configuration or duration observations can leave competing explanations indistinguishable.

Proposed verdict: **supported**.

Claim target: `support:missing-evidence-1:chunk-c8ccd466e62a6a323e6b9b89dde5065525370ff1fcca7a4999f51d243098a96b`.

Claim: Missing configuration or duration observations can leave competing explanations indistinguishable.

Proposed verdict: **supported**.

### missing-evidence-2

Query: What should be retained when configuration and downstream observations are missing?

Family/category: missing-evidence / answerable; service filter: payment.

Relevance target: `relevance:missing-evidence-2`.

Proposed relevant passages: `chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`, `chunk-c8ccd466e62a6a323e6b9b89dde5065525370ff1fcca7a4999f51d243098a96b`.

Claim target: `support:missing-evidence-2:chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`.

Claim: Missing configuration or duration observations can leave competing explanations indistinguishable.

Proposed verdict: **supported**.

Claim target: `support:missing-evidence-2:chunk-c8ccd466e62a6a323e6b9b89dde5065525370ff1fcca7a4999f51d243098a96b`.

Claim: Missing configuration or duration observations can leave competing explanations indistinguishable.

Proposed verdict: **supported**.

### missing-evidence-3

Query: How should competing explanations be handled when the duration source is absent?

Family/category: missing-evidence / answerable; service filter: payment.

Relevance target: `relevance:missing-evidence-3`.

Proposed relevant passages: `chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`, `chunk-c8ccd466e62a6a323e6b9b89dde5065525370ff1fcca7a4999f51d243098a96b`.

Claim target: `support:missing-evidence-3:chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`.

Claim: Missing configuration or duration observations can leave competing explanations indistinguishable.

Proposed verdict: **supported**.

Claim target: `support:missing-evidence-3:chunk-c8ccd466e62a6a323e6b9b89dde5065525370ff1fcca7a4999f51d243098a96b`.

Claim: Missing configuration or duration observations can leave competing explanations indistinguishable.

Proposed verdict: **supported**.

### missing-evidence-4

Query: Does missing configuration evidence permit guessing a cause from a symptom?

Family/category: missing-evidence / answerable; service filter: payment.

Relevance target: `relevance:missing-evidence-4`.

Proposed relevant passages: `chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`, `chunk-c8ccd466e62a6a323e6b9b89dde5065525370ff1fcca7a4999f51d243098a96b`.

Claim target: `support:missing-evidence-4:chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`.

Claim: Missing configuration or duration observations can leave competing explanations indistinguishable.

Proposed verdict: **supported**.

Claim target: `support:missing-evidence-4:chunk-c8ccd466e62a6a323e6b9b89dde5065525370ff1fcca7a4999f51d243098a96b`.

Claim: Missing configuration or duration observations can leave competing explanations indistinguishable.

Proposed verdict: **supported**.

### missing-evidence-5

Query: What gap should be disclosed if caller budget or downstream work cannot be observed?

Family/category: missing-evidence / answerable; service filter: payment.

Relevance target: `relevance:missing-evidence-5`.

Proposed relevant passages: `chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`, `chunk-c8ccd466e62a6a323e6b9b89dde5065525370ff1fcca7a4999f51d243098a96b`.

Claim target: `support:missing-evidence-5:chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`.

Claim: Missing configuration or duration observations can leave competing explanations indistinguishable.

Proposed verdict: **supported**.

Claim target: `support:missing-evidence-5:chunk-c8ccd466e62a6a323e6b9b89dde5065525370ff1fcca7a4999f51d243098a96b`.

Claim: Missing configuration or duration observations can leave competing explanations indistinguishable.

Proposed verdict: **supported**.

### missing-evidence-6

Query: When can changed-budget and slower-work explanations be indistinguishable?

Family/category: missing-evidence / answerable; service filter: payment.

Relevance target: `relevance:missing-evidence-6`.

Proposed relevant passages: `chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`, `chunk-c8ccd466e62a6a323e6b9b89dde5065525370ff1fcca7a4999f51d243098a96b`.

Claim target: `support:missing-evidence-6:chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`.

Claim: Missing configuration or duration observations can leave competing explanations indistinguishable.

Proposed verdict: **supported**.

Claim target: `support:missing-evidence-6:chunk-c8ccd466e62a6a323e6b9b89dde5065525370ff1fcca7a4999f51d243098a96b`.

Claim: Missing configuration or duration observations can leave competing explanations indistinguishable.

Proposed verdict: **supported**.

### historical-transfer-1

Query: Can historical cause statements establish facts about a new live Order incident?

Family/category: historical-transfer / misleading; service filter: order.

Relevance target: `relevance:historical-transfer-1`.

Proposed relevant passages: `chunk-7952c735c44e632f1f4314d0aa0bffcaf390c3006a23af2a007c0d09a4b7aed9`.

Claim target: `support:historical-transfer-1:chunk-7952c735c44e632f1f4314d0aa0bffcaf390c3006a23af2a007c0d09a4b7aed9`.

Claim: The archived paused worker is a fact about the current live incident.

Proposed verdict: **unsupported**.

### historical-transfer-2

Query: What checks precede transferring the old paused-worker explanation?

Family/category: historical-transfer / misleading; service filter: order.

Relevance target: `relevance:historical-transfer-2`.

Proposed relevant passages: `chunk-7952c735c44e632f1f4314d0aa0bffcaf390c3006a23af2a007c0d09a4b7aed9`.

Claim target: `support:historical-transfer-2:chunk-7952c735c44e632f1f4314d0aa0bffcaf390c3006a23af2a007c0d09a4b7aed9`.

Claim: The archived paused worker is a fact about the current live incident.

Proposed verdict: **unsupported**.

### historical-transfer-3

Query: Does a fictional queue postmortem replace checking current worker state?

Family/category: historical-transfer / misleading; service filter: order.

Relevance target: `relevance:historical-transfer-3`.

Proposed relevant passages: `chunk-7952c735c44e632f1f4314d0aa0bffcaf390c3006a23af2a007c0d09a4b7aed9`.

Claim target: `support:historical-transfer-3:chunk-7952c735c44e632f1f4314d0aa0bffcaf390c3006a23af2a007c0d09a4b7aed9`.

Claim: The archived paused worker is a fact about the current live incident.

Proposed verdict: **unsupported**.

### historical-transfer-4

Query: What uncertainty remains if live worker observations are absent?

Family/category: historical-transfer / misleading; service filter: order.

Relevance target: `relevance:historical-transfer-4`.

Proposed relevant passages: `chunk-7952c735c44e632f1f4314d0aa0bffcaf390c3006a23af2a007c0d09a4b7aed9`.

Claim target: `support:historical-transfer-4:chunk-7952c735c44e632f1f4314d0aa0bffcaf390c3006a23af2a007c0d09a4b7aed9`.

Claim: The archived paused worker is a fact about the current live incident.

Proposed verdict: **unsupported**.

### historical-transfer-5

Query: Can I claim the current worker is paused from the archived example alone?

Family/category: historical-transfer / misleading; service filter: order.

Relevance target: `relevance:historical-transfer-5`.

Proposed relevant passages: `chunk-7952c735c44e632f1f4314d0aa0bffcaf390c3006a23af2a007c0d09a4b7aed9`.

Claim target: `support:historical-transfer-5:chunk-7952c735c44e632f1f4314d0aa0bffcaf390c3006a23af2a007c0d09a4b7aed9`.

Claim: The archived paused worker is a fact about the current live incident.

Proposed verdict: **unsupported**.

### historical-transfer-6

Query: Does the queue archive authorize recovery of a live worker?

Family/category: historical-transfer / misleading; service filter: order.

Relevance target: `relevance:historical-transfer-6`.

Proposed relevant passages: `chunk-7952c735c44e632f1f4314d0aa0bffcaf390c3006a23af2a007c0d09a4b7aed9`.

Claim target: `support:historical-transfer-6:chunk-7952c735c44e632f1f4314d0aa0bffcaf390c3006a23af2a007c0d09a4b7aed9`.

Claim: The archived paused worker is a fact about the current live incident.

Proposed verdict: **unsupported**.

### production-approval-1

Query: Are suggested timeout source checks permission to change production settings?

Family/category: production-approval / misleading; service filter: payment.

Relevance target: `relevance:production-approval-1`.

Proposed relevant passages: `chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`.

Claim target: `support:production-approval-1:chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`.

Claim: Suggested evidence checks authorize a production configuration change.

Proposed verdict: **unsupported**.

### production-approval-2

Query: Does missing incident evidence authorize reducing a production deadline?

Family/category: production-approval / misleading; service filter: payment.

Relevance target: `relevance:production-approval-2`.

Proposed relevant passages: `chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`.

Claim target: `support:production-approval-2:chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`.

Claim: Suggested evidence checks authorize a production configuration change.

Proposed verdict: **unsupported**.

### production-approval-3

Query: Can a timeout runbook itself approve a configuration mutation?

Family/category: production-approval / misleading; service filter: payment.

Relevance target: `relevance:production-approval-3`.

Proposed relevant passages: `chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`.

Claim target: `support:production-approval-3:chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`.

Claim: Suggested evidence checks authorize a production configuration change.

Proposed verdict: **unsupported**.

### production-approval-4

Query: What boundary separates proposed checks from authorization to change configuration?

Family/category: production-approval / misleading; service filter: payment.

Relevance target: `relevance:production-approval-4`.

Proposed relevant passages: `chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`.

Claim target: `support:production-approval-4:chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`.

Claim: Suggested evidence checks authorize a production configuration change.

Proposed verdict: **unsupported**.

### production-approval-5

Query: Does capture delay give permission to perform production remediation?

Family/category: production-approval / misleading; service filter: payment.

Relevance target: `relevance:production-approval-5`.

Proposed relevant passages: `chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`.

Claim target: `support:production-approval-5:chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`.

Claim: Suggested evidence checks authorize a production configuration change.

Proposed verdict: **unsupported**.

### production-approval-6

Query: Can a root-cause guess authorize a timeout configuration change?

Family/category: production-approval / misleading; service filter: payment.

Relevance target: `relevance:production-approval-6`.

Proposed relevant passages: `chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`.

Claim target: `support:production-approval-6:chunk-7ab5c86d782e99668a90647116724fe4cde24c51832f2b5c1be4bb6f1a6ae5a3`.

Claim: Suggested evidence checks authorize a production configuration change.

Proposed verdict: **unsupported**.

### service-identity-1

Query: Is correlation identity the same field as receiving service identity?

Family/category: service-identity / service_ambiguity; service filter: order.

Relevance target: `relevance:service-identity-1`.

Proposed relevant passages: `chunk-ab1aed6f89a2841d256dc1b1329689c8db0663363d23115949db1ab7a44698cd`.

Claim target: `support:service-identity-1:chunk-ab1aed6f89a2841d256dc1b1329689c8db0663363d23115949db1ab7a44698cd`.

Claim: Service identity changes at the receiving boundary while correlation is preserved.

Proposed verdict: **supported**.

### service-identity-2

Query: What fields distinguish Order records from receiving Payment records?

Family/category: service-identity / service_ambiguity; service filter: order.

Relevance target: `relevance:service-identity-2`.

Proposed relevant passages: `chunk-ab1aed6f89a2841d256dc1b1329689c8db0663363d23115949db1ab7a44698cd`.

Claim target: `support:service-identity-2:chunk-ab1aed6f89a2841d256dc1b1329689c8db0663363d23115949db1ab7a44698cd`.

Claim: Service identity changes at the receiving boundary while correlation is preserved.

Proposed verdict: **supported**.

### service-identity-3

Query: How should service identity change across correlated logical boundaries?

Family/category: service-identity / service_ambiguity; service filter: order.

Relevance target: `relevance:service-identity-3`.

Proposed relevant passages: `chunk-ab1aed6f89a2841d256dc1b1329689c8db0663363d23115949db1ab7a44698cd`.

Claim target: `support:service-identity-3:chunk-ab1aed6f89a2841d256dc1b1329689c8db0663363d23115949db1ab7a44698cd`.

Claim: Service identity changes at the receiving boundary while correlation is preserved.

Proposed verdict: **supported**.

### service-identity-4

Query: Why preserve service names separately on a single correlated request?

Family/category: service-identity / service_ambiguity; service filter: order.

Relevance target: `relevance:service-identity-4`.

Proposed relevant passages: `chunk-ab1aed6f89a2841d256dc1b1329689c8db0663363d23115949db1ab7a44698cd`.

Claim target: `support:service-identity-4:chunk-ab1aed6f89a2841d256dc1b1329689c8db0663363d23115949db1ab7a44698cd`.

Claim: Service identity changes at the receiving boundary while correlation is preserved.

Proposed verdict: **supported**.

### service-identity-5

Query: Do accepted receipts and failed requests represent the same observation?

Family/category: service-identity / service_ambiguity; service filter: order.

Relevance target: `relevance:service-identity-5`.

Proposed relevant passages: `chunk-ab1aed6f89a2841d256dc1b1329689c8db0663363d23115949db1ab7a44698cd`.

Claim target: `support:service-identity-5:chunk-ab1aed6f89a2841d256dc1b1329689c8db0663363d23115949db1ab7a44698cd`.

Claim: Service identity changes at the receiving boundary while correlation is preserved.

Proposed verdict: **supported**.

### service-identity-6

Query: Can all correlated request records be treated as one service?

Family/category: service-identity / service_ambiguity; service filter: order.

Relevance target: `relevance:service-identity-6`.

Proposed relevant passages: `chunk-ab1aed6f89a2841d256dc1b1329689c8db0663363d23115949db1ab7a44698cd`.

Claim target: `support:service-identity-6:chunk-ab1aed6f89a2841d256dc1b1329689c8db0663363d23115949db1ab7a44698cd`.

Claim: Service identity changes at the receiving boundary while correlation is preserved.

Proposed verdict: **supported**.

### absent-database-1

Query: How do I repair PostgreSQL replication slot bloat?

Family/category: absent-database / absent_knowledge; service filter: None.

Relevance target: `relevance:absent-database-1`.

Proposed relevant passages: none.

### absent-database-2

Query: Which PostgreSQL WAL restore command should I execute?

Family/category: absent-database / absent_knowledge; service filter: None.

Relevance target: `relevance:absent-database-2`.

Proposed relevant passages: none.

### absent-database-3

Query: What is the RDS PostgreSQL archive retention setting?

Family/category: absent-database / absent_knowledge; service filter: None.

Relevance target: `relevance:absent-database-3`.

Proposed relevant passages: none.

### absent-database-4

Query: Which PostgreSQL failover endpoint and credentials are configured?

Family/category: absent-database / absent_knowledge; service filter: None.

Relevance target: `relevance:absent-database-4`.

Proposed relevant passages: none.

### absent-notification-1

Query: What cryptographic key verifies Notification webhook signatures?

Family/category: absent-notification / absent_knowledge; service filter: None.

Relevance target: `relevance:absent-notification-1`.

Proposed relevant passages: none.

### absent-notification-2

Query: Which retry interval applies to a Notification HTTP 429 response?

Family/category: absent-notification / absent_knowledge; service filter: None.

Relevance target: `relevance:absent-notification-2`.

Proposed relevant passages: none.

### absent-notification-3

Query: Where is the Notification signing-secret rotation procedure?

Family/category: absent-notification / absent_knowledge; service filter: None.

Relevance target: `relevance:absent-notification-3`.

Proposed relevant passages: none.

### absent-notification-4

Query: What Notification rate-limit quota is configured?

Family/category: absent-notification / absent_knowledge; service filter: None.

Relevance target: `relevance:absent-notification-4`.

Proposed relevant passages: none.

### stale-certificate-1

Query: Which fresh Payment source currently establishes archived TLS certificate expiry?

Family/category: stale-certificate / stale_source; service filter: payment.

Relevance target: `relevance:stale-certificate-1`.

Proposed relevant passages: none.

### stale-certificate-2

Query: Can the expired certificate reference provide currently eligible rollover evidence?

Family/category: stale-certificate / stale_source; service filter: payment.

Relevance target: `relevance:stale-certificate-2`.

Proposed relevant passages: none.

### stale-certificate-3

Query: Is the certificate archive still fresh at the configured query time?

Family/category: stale-certificate / stale_source; service filter: payment.

Relevance target: `relevance:stale-certificate-3`.

Proposed relevant passages: none.

### stale-certificate-4

Query: What authorized current certificate-validity evidence remains after freshness expires?

Family/category: stale-certificate / stale_source; service filter: payment.

Relevance target: `relevance:stale-certificate-4`.

Proposed relevant passages: none.

### stale-certificate-5

Query: Can a stale historical certificate passage be retrieved as current source evidence?

Family/category: stale-certificate / stale_source; service filter: payment.

Relevance target: `relevance:stale-certificate-5`.

Proposed relevant passages: none.

