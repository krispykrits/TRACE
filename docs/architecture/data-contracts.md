# Data contracts

Current implementation includes evidence/corpus/retrieval, provider/assessment/execution and bounded workflow contracts. Schema names have independent meanings; SQLite schema 3 is not evidence-envelope or report version 3.

| Record | Current contract | Authoritative guide/source |
| --- | --- | --- |
| Settings | Required environment, optional log level, explicit precedence and value-safe errors | [Development](../development.md#configuration-and-logs), [configuration](../../src/trace_app/runtime/configuration.py) |
| Application log | Correlated UTC JSON to stderr; reviewed metadata/numeric usage and secret redaction | [Logging](../../src/trace_app/runtime/logging.py), [security](../security/README.md) |
| Synthetic Order and boundary context | Validated IDs/cents, typed outcome, propagated environment/correlation and receiving logical service identity | [Order workflow](order-payment-workflow.md) |
| Incident evidence | Version 1 envelope with stable source/evidence IDs, revision, event/collection time, window, classification, provenance and source availability | [Replay envelope](dependency-replay-evidence.md) |
| SQLite investigation state | Schema 3 stores snapshots/jobs/attempts, execution admission and private workflow records; older job schemas migrate transactionally | [SQLite state](sqlite-investigation-store.md), [store source](../../src/trace_app/adapters/storage/sqlite/investigations.py) |
| Evidence query | Trusted grants narrowable by filters; bounded inclusive UTC reads, stable IDs and distinct empty/incomplete/failure results | [Bounded queries](bounded-evidence-queries.md) |
| Timeline | Deterministic observed UTC/evidence-ID ordering with provenance, scoped citations and explicit omissions | [Timelines](incident-timelines.md) |
| Corpus document/chunk/generation | Source-owned identity/revision, original offsets, content/policy generations and current freshness/revocation checks | [Corpus](knowledge-corpus.md) |
| Knowledge result/context | Bounded authorized ranking, whole quoted passages, current full-provenance citations and omission ledger | [Retrieval](knowledge-retrieval.md), [context](retrieval-evaluation-context.md) |
| Tool request/result | Closed typed catalog arguments, independent trusted scope, external execution limits and metadata-only audit | [Tools](investigation-tools.md) |
| Model call/protected response | `model-provider.v1` and `trace-provider-data-policy.v1`; reference-based independent source/transmission admission, inherited sensitivity and nullable usage | [Provider](model-provider.md) |
| Assessment | `assessment.v2` with strict claims/references/contradictions, causal basis, missing evidence, abstention and typed next check; v1 projection retained for historical scoring | [Validated assessments](validated-assessments.md) |
| Execution session | Durable attempt/deadline/model/tool/retry/correction/token bounds, reservation/usage and conservative unknown-outcome handling | [Budgets](investigation-budgets.md) |
| Workflow publication | Protected observed package, accepted assessment or untrusted review packet, atomically bound to current job/attempt; terminal execution is separate from support acceptance | [Investigator](bounded-investigator.md) |
| Evaluator run | Repository-only labels, judgments, failure denominators and hash-verified saved artifacts; excluded from runtime inputs | [Evaluation](development-evaluation.md), [artifact guide](../../evaluation/README.md) |

## Source and authority rules

Preserve event versus collection time, source identity/revision, service/environment, access/transmission classification and completeness through every adapter. Missing or truncated telemetry cannot be converted into an observation.

Current local fixtures test these contracts. Operational JSON/Azure adapters must provide independently derived grants and preserve current citation/review/output protection. The owner is the planned .NET service owner/initial investigator; exact permitted fields, transmission, retention and live access remain [charter gates](../charter.md#open-inputs-and-decision-gates).

The final ranked-response schema is planned under [ADR 0018](../adr/0018-flexible-ml-and-ranked-response-options.md). It must be versioned separately; this cleanup adds no fields to accepted report or evidence contracts.
