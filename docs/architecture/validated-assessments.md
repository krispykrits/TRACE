# Validated assessments and cited support

Scoped story [#35](https://github.com/krispykrits/TRACE/issues/35), following accepted #34 / merged PR #51. [ADR 0013](../adr/0013-assessment-validation-and-support-review.md) records the proposed acceptance policy. This implements a validation/use-case boundary for hand-authored or generated reports; the investigator loop and inspection UI remain #37/#38.

## Versioned schema

`investigation.assessment_schema.AssessmentReport` parses `assessment.v2`. The existing `CandidateReport` version `1` remains unchanged for #14 and historical scoring. All fields are required; unknown fields, excessive bytes/text/counts, duplicate claim/reference IDs and inconsistent supported/abstained states are rejected before acceptance.

| Field | Contract |
| --- | --- |
| `schema_version` | Exactly `assessment.v2`; the provider response must declare this response-schema ID |
| `assessment_status` | `supported` or `abstained`; execution failures have a separate validation outcome |
| `observations` | Claims with unique `claim_id`, nonempty statement and bounded cited IDs |
| `primary_hypothesis` | Claim/service/cause plus `contradicting_citations` and `causal_basis`; required for supported candidates, null for abstention |
| `alternative_hypotheses` | At most 20 competing hypotheses with the same closed fields |
| `uncertainty` | Required qualitative text; no confidence/causal-probability field |
| `missing_evidence` | Bounded explanations, required when the supplied source inventory has gaps |
| `source_gaps` | Exact disclosed inventory/knowledge/omission IDs from the supplied context |
| `abstention_reason` | Required for abstention, null for supported candidates; independent outcome review checks its justification |
| `next_check` | Fixed read-only tool, validated arguments and nonempty rationale; evidence windows cannot exceed the supplied window |
| `timeline_evidence_ids` | The supplied deterministic ordering of admitted evidence IDs; models cannot reorder or omit them |

The report is bounded to 65,536 serialized bytes, 100 claims, 2,000 characters per text field and 32 references per claim/contradiction list. These are implementation ceilings, not owner-defined quality targets. Supporting and contradicting references must be separate. Primary causal basis requires `mechanism`; `temporal_only`, `score_only` and `context_only` cannot become a supported primary diagnosis. Declaring a mechanism does not prove it: independent support review still applies. Alternatives can retain weaker bases as possibilities to check.

`candidate.to_dict()` is the explicit version-1 projection. It keeps #14's observations/hypotheses/uncertainty/abstention shape and represents the check through its rationale; contradictions, causal bases, typed arguments and gap IDs remain in the full v2 report. Do not use that projection as a replacement for protected inspection or rewrite frozen evaluator artifacts/hashes.

## Composition and current references

`bootstrap.create_assessment_validator(package, scope=..., tools=..., reviews=...)` requires the supplied scoped evidence package, the independently composed fixed tool session and a trusted review reader. Package, provider and tool-session investigation identities must match. There is no default review authority, credential or live call.

The context freezes a canonical snapshot privately and rejects failed timeline/retrieval components. Missing source inventory, absent knowledge and truncation/omissions are disclosed as gaps; storage or tool failure stays an execution failure. Evidence references re-resolve through `evidence.get`; knowledge references use `knowledge.resolve` with their original corpus generation/chunk. Current access, source time validity/revocation and exact source/revision/content comparisons come from those existing source contracts. A past successful read is not standing authorization.

Only provider-admitted citation IDs can support the report. The provider response retains each exact sanitized field projection and local redaction provenance, including history-derived views. Citation-view reads revalidate its original source dependencies. Review output contains those admitted projections, approved source/revision IDs, evidence timestamps or knowledge generation/chunk/offset mappings. Raw source payloads and free-text knowledge section titles do not enter the artifact through the resolver. Redaction provenance contains locations/reasons, never removed values.

## Validation outcomes and support review

`AssessmentValidator.validate(response, scope)` returns content-free metadata plus an optional protected handle:

| Outcome | Meaning |
| --- | --- |
| `accepted` | Schema/current citations/gaps/bounds pass; every claim and outcome has agreed trusted supported review |
| `review_required` | IDs are valid, but at least one support decision is unreviewed, indeterminate or disputed |
| `rejected` | Malformed report, invalid/denied/mismatched reference, policy violation or an unsupported claim |
| `execution_failed` | Tool/storage/review dependency failure; this is never completed abstention |

`citation_validity` is `unchecked`, `valid` or `invalid`; `claim_support` is reported separately. A reviewer/dependency failure cannot retroactively imply that a previously checked ID was invented. Valid IDs alone do not establish passage/claim support. Unsupported claims are withheld from accepted assessments by rejecting the candidate; pending proposals remain explicitly untrusted review material. No automatic retry/correction call is issued.

`handle.review_packet(scope, claim_ids=...)` prepares a bounded sample with exact statements, supporting/contradicting refs, admitted citation views and per-task bindings. It also provides an `assessment-outcome` task for the reported conclusion/abstention and next-check rationale. The packet carries `artifact_role=untrusted_support_review`, original sensitivity and `mutation_authority=false`.

The independent `SupportReviewReader` supplies current decisions with claim/binding IDs, reviewer identity, rationale, kind `human_review` and rubric `trace-claim-support.v1`. Use [#14's rubric](development-evaluation.md#citation-support-review-rubric): supported at the stated strength, unsupported/unrelated/overstated, or indeterminate. Preserve contrary evidence and missing captures. Model fields, evaluator answers and `fixture_expectation` judgments cannot create approval. Changed report/view/provenance/gaps/scope invalidates a prior binding; withdrawal of support makes future accepted reads fail. Sampling leaves unsampled claims unreviewed.

`handle.read(scope)` exposes accepted content only after fresh provider/source/review checks. It preserves source identity/revision and observed/collected timestamps in the observed timeline. `handle.export(scope)` also requires current original transmission permission. The most sensitive original input classification survives redaction and summarization; changing the viewer/scope or forging a different backing response does not grant access. Source permission is checked again after review reads to prevent a review-time revocation from releasing content.

No read/check/review executes a recommended tool or production mutation. `next_check` is a bounded proposal, not an execution authorization. Tool/model budgets, correction accounting and durable workflow state remain #36/#37. Operator authentication, review persistence, retention/deletion and UI/export enforcement remain #38/production gates. Plain dictionaries already read by an authorized caller cannot be retroactively erased; application composition/filesystem are trusted, not an arbitrary-Python sandbox.

## Reproduction and evidence

Run the hand-authored answerable, competing/unrelated-deployment and insufficient-evidence examples and negative cases:

```sh
uv run --locked python -m unittest tests.unit.test_assessment_schema tests.contracts.test_assessment_validation tests.integration.test_assessments -v
make check lint format-check type-check architecture-check test integration package-check
```

[Fixture reports](../../tests/fixtures/assessments.py) are hand-authored; reviewer decisions are explicitly synthetic test records, not actual human endorsement or diagnosis-quality evidence. The actual SQLite/corpus/process tests resolve evidence and knowledge together, revoke knowledge after review, exercise denied/expired scope and separate database failure from abstention. Contract cases cover malformed/oversized output, invented references, contradictions, missing gaps, score/temporal-only causal claims, blocked mutation tools, sample review artifacts, input sensitivity/redaction provenance and denied wider response access. Provider field names containing known credentials are blocked before provenance writes.

No new paid model call is required or performed for this provider-independent story. #34's prior native Azure check remains separate evidence; it does not measure v2 assessment quality. Future live generated assessments must use the same admission/validation interfaces and explicit budget/access authorization. No Operational Pilot, full investigation, Cloud MVP or remediation acceptance is inferred.
