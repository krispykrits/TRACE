# Development evaluation contracts

Status: issue [#14](https://github.com/krispykrits/TRACE/issues/14) merged via [PR #42](https://github.com/krispykrits/TRACE/pull/42), 2026-10-12. This offline runner checks hand-authored candidate fixtures against the four seed-17 development cases. It provides scoring plumbing before investigator/model integration. Its deliberately mixed correct, incorrect, abstaining, missing, malformed and failed outputs are a scorer demonstration; their rates do not measure a model or establish Local MVP, Cloud MVP, Full Capstone or Operational Pilot acceptance.

## Run and reproduce

From the repository root, use a new output path:

```sh
uv run --locked python -m evaluation.runner run --output /tmp/trace-s3-evaluation
uv run --locked python -m evaluation.runner rescore --run-dir /tmp/trace-s3-evaluation
```

Both commands print the same canonical score JSON to stdout. Structured logs go to stderr with a command correlation ID; the success event includes the manifest hash. A completed scorer exits 0 even when candidate fixtures fail checks. Invalid input, incompatible versions, changed hashes, score disagreement or filesystem failure exits 2. Existing output directories are refused. A partially written directory without its final manifest is incomplete; use a fresh directory rather than overwriting it.

The runner lives in repository-only `evaluation/`, outside the installable application package. It uses the standard library and TRACE contracts, without a provider, network call, investigator, LLM judge or new dependency. `make check lint format-check type-check test integration` includes evaluator code and deterministic tests. The real-process test runs, rescores and rejects altered artifacts.

## Candidate and evaluator schemas

[CandidateReport](../../src/trace_app/investigation/assessment.py) is a runtime-owned contract with no evaluator dependency. Its `from_dict` boundary rejects unknown/missing keys, unsupported schema versions and inconsistent status fields. Direct dataclass construction is for trusted application values; untrusted dictionaries must use the parser. Schema version `1` requires these fields:

| Field | Meaning |
| --- | --- |
| `assessment_status` | `supported` or `abstained`, separate from execution status |
| `observations` | Claims about observed evidence, each with unique `claim_id`, `statement` and `citations` |
| `primary_hypothesis` | Nullable object with `claim`, `service` and `cause`; required for supported reports and forbidden for abstention |
| `alternative_hypotheses` | Competing hypotheses with the same structure, preserved even when diagnosis abstains |
| `uncertainty` | Nonempty explanation of limitations; no fabricated numeric confidence |
| `missing_evidence` | Source names required to resolve uncertainty |
| `abstention_reason` | Required nonempty text for abstention; null for supported reports |
| `next_check` | Nonempty suggested evidence check; grants no execution authority |
| `timeline_evidence_ids` | Ordered references to the supplied operational snapshot |

Every claim ID is unique across observations and hypotheses. Text is nonempty and bounded to 2,000 characters; observation, alternative and string lists are bounded to 100 elements. Citation and timeline lists reject duplicate IDs. Empty citations remain parseable so the scorer can report an uncited claim explicitly. Ground-truth labels, arbitrary extra fields and probability/score fields are rejected.

[EvaluationAttempt](../../evaluation/scoring.py) belongs only to the evaluator. It requires `attempt_id`, `case_id`, `seed`, `execution_status`, `failure_code`, `report`, `usage` and `support_reviews`. Execution is `completed`, `failed`, `cancelled` or `expired`; every noncompleted outcome requires a failure code, while completion forbids one. Completed attempts can contain a missing or malformed report, which remains in scoring. Usage fields are `latency_ms`, `tokens`, `estimated_cost_usd` and `tool_calls`; unavailable values are null, numbers must be finite and nonnegative, and token/tool counts must be integers. All built-in usage values are null because no integrated investigator/model operation is measured.

Each support review requires `claim_id`, `verdict` (`supported`, `unsupported`, `indeterminate`), `reviewer_id`, `rationale` and `kind` (`fixture_expectation`, `human_review`). Lists are bounded to 1,000 reviews and duplicate reviewer/claim/kind decisions are rejected. Reviews of a valid report must reference an existing claim. The two built-in unsupported decisions are hand-authored fixture expectations, not human-review evidence. No actual operator/reviewer result is supplied by this increment.

The runner accepts only the versioned four-case development manifest and seed 17, with 1–100 unique attempts. Artifact reads are bounded to 2 MB per file, reject duplicate JSON keys/nonfinite constants and refuse symbolic-link files. Operational inputs use the strict version 1 synthetic evidence envelope and cannot add evaluator labels.

## Metrics and denominators

Each rate has explicit `numerator`, `denominator` and `value`; an empty denominator gives null. Every attempted case remains visible, including job failures and missing/malformed reports. Per-attempt scores retain failure codes, schema errors, invalid references, claim review states and source gaps.

| Metric | Numerator / denominator |
| --- | --- |
| Schema validity | Completed, valid reports / all attempts |
| Cause accuracy | Exact primary cause-label matches / all attempts on answerable cases |
| Service accuracy | Exact primary service matches / all attempts on answerable cases |
| Assessment accuracy | Valid report status matches expected supported/abstained / all attempts |
| Abstention contract accuracy | Valid abstentions with a reason and nonempty missing-source names drawn from actual unavailable/truncated sources / all insufficient-evidence attempts |
| Citation validity | Claim references present in that attempt's supplied evidence snapshot / all claim references in valid reports |
| Timeline order accuracy | Valid, known references in parsed UTC observed-time/evidence-ID order / all attempts; empty sequences fail when evidence exists |
| Timeline complete accuracy | Exact full supplied snapshot sequence / all attempts |
| Human unsupported-claim rate | Agreed unsupported claims / claims with agreed determinate human reviews |

Failed, missing and malformed answerable attempts score false for cause/service and remain in their denominators. Insufficient-evidence cases have null cause/service scores: a lucky match to a hidden cause earns no diagnosis credit. Abstention contract scoring checks structure and real source gaps; reviewers must separately assess the reason's adequacy and the proposed next check. Cause/service matching alone does not prove causal support. Observation/hypothesis prose is not automatically semantically graded.

Citation validity checks existence within the supplied authorized snapshot, not whether an ID's contents justify a statement. Repeated references across claims count as separate references. Timeline references have separate invalid-ID output and ordering/completeness checks. Uncited claims and claims containing invalid citations are explicitly structurally unsupported. Fixture-expected unsupported claims, human unsupported claims, indeterminate claims, disagreements and unreviewed claims are separate outputs. Citation support is never inferred from IDs, temporal proximity or a correct hidden label.

Execution counts distinguish completed/failed/cancelled/expired. `source_incomplete_attempts` counts snapshots with absent or unavailable/truncated sources, independently of execution and assessment; `capture_gap_attempts` identifies the missing-telemetry cases separately. Every built-in snapshot lacks the unsupplied sanitized export, so all seven attempts are source-incomplete even when synthetic sources suffice for a diagnosis. That absence is not a runner/job failure. The fixture's failed job is a declared simulated outcome, not a measured provider timeout.

The known-score demonstration expects:

| Outcome | Expected result |
| --- | --- |
| Attempts and execution | 7 attempted; 6 completed, 1 failed, 0 cancelled/expired |
| Missing / invalid reports | 1 / 1 |
| Incomplete-source / capture-gap attempts | 7 / 2 |
| Schema / cause / service / assessment | 4/7, 1/5, 1/5, 3/7 |
| Abstention contract / citation validity | 1/2, 13/14 |
| Timeline order / completeness | 3/7, 3/7 |
| Structurally / fixture-expected unsupported claims | 1 / 2 |
| Human unsupported rate / disagreements / unreviewed claims | 0/0 (null), 0, 10 |

These values test the scorer, including failure accounting. They are not quality thresholds.

## Citation-support review rubric

Review each observation and hypothesis against its cited operational content, source availability, provenance and stated uncertainty. Record the reviewer identity, claim ID and rationale with a verdict:

- **Supported:** the cited content establishes the observation, or supports the hypothesis at the strength stated while preserving plausible alternatives and missing evidence.
- **Unsupported:** evidence contradicts the statement, is unrelated, or the claim overstates what it shows; an unrelated deployment and temporal correlation alone cannot establish cause.
- **Indeterminate:** authorized evidence is insufficient to decide support, including unresolved provenance or capture gaps. Preserve uncertainty rather than forcing a binary verdict.

For a later measured study, collect two independent human reviews using this rubric, preserving both records. Disagreement is explicit and excluded from the agreed unsupported-rate denominator; agreed indeterminate claims are also excluded. Adjudication must record a separate rationale and original decisions rather than silently rewriting them. The early scorer can represent one reviewer, but that does not satisfy a two-reviewer study protocol. Without human reviews, the human rate is unavailable and claims remain unreviewed. Tests with synthetic reviewer decisions verify aggregation only.

Class probability means a classifier's probability over defined labels, requiring measured calibration for the relevant cohort. Anomaly score expresses deviation under its own detector; retrieval rank score measures ordering/relevance under a retrieval configuration. Neither is a causal probability. Causal support is an evidence judgment under the rubric. This report schema provides qualitative uncertainty and review decisions only; introducing any numeric score later requires its own named semantics, versioned method and evaluation evidence.

## Saved run and investigator isolation

```text
run/
  manifest.json
  ground_truth.json        evaluator only
  attempts.json            candidates and evaluator review expectations
  scores.json              evaluator only
  inputs/c01.json          operational evidence only
  inputs/c02.json
  inputs/c03.json
  inputs/c04.json
```

The manifest records schema/scorer/suite/fixture/configuration versions, seed 17, the fixed capture timestamp, report/evidence/timeline schema versions, hashes of all application/evaluator Python sources and hashes of the saved files. Model/prompt versions are null. Ground-truth and input hashes identify exact dataset content. Reproduction requires the matching implementation, not merely a matching version string; rescoring reads saved snapshots rather than regenerating them and rejects score disagreement. Two fresh runs under the same code produce identical artifacts. Hashes detect changes relative to a manifest; they do not authenticate a source or authorize access.

Directories are created mode 0700 and files mode 0600. The manifest is written last. Keep generated runs outside source control and delete temporary copies when no longer needed; operational retention/deletion rules require owner decisions before real-source ingestion. Share only `inputs/*.json` with a future investigator. Never mount, index, retrieve or prompt with the run's evaluator files, fixture reports, manifests or labels. The runtime never imports `evaluation`; scenario replay uses case configuration, not ground truth. The related fixture group remains entirely development; no validation/final-test answers are generated or exercised.

## Baseline and operator comparison protocol

The approved amendment requires comparisons against a deterministic evidence bundle and the current operator workflow. Define these before collecting measured investigator results:

| Arm | Inputs and behavior |
| --- | --- |
| Deterministic evidence bundle | Same authorized service/window and data version; bounded observed timeline, source status, provenance and resolvable citations; no predicted cause or model-generated next action |
| Current operator workflow | Named operator/team's documented tools, runbooks and usual evidence checks, with matched authorized source access and task scope |
| TRACE investigator | Same task/evidence scope plus the eventual versioned investigator, retrieval and model configuration; preserve uncertainty and abstention |

Keep synthetic development results and an independently authorized historical/live pilot in separate cohorts and reports. Group related incidents/variants to prevent leakage. Use matched tasks, comparable access, and a recorded/counterbalanced arm order to limit familiarity effects; do not expose evaluator labels to operators or investigators. Record unavailable sources and access differences instead of attributing their effects to the investigator.

Start elapsed time when the participant receives the incident brief and authorized task. Record the first useful evidence timestamp and first useful next-action/check timestamp, with reviewers' rubric decisions explaining usefulness. Use a monotonic clock for elapsed durations when measuring live work and retained UTC timestamps for audit. Useful evidence narrows plausible explanations or exposes a consequential gap with provenance; a useful next step is a concrete, justified check within the task's authority. A proposed remediation grants no production execution permission.

Report time to useful evidence and next action, total active manual effort in minutes, tool/manual interaction counts, completion/failure/cancellation, source gaps, abstention adequacy, unsupported claims and reviewer disagreement. Include queue/dependency delay in elapsed time and identify it separately when measurable. Predeclare treatment of stopped/expired tasks and report their counts and observation bounds; do not drop them or fabricate a useful-evidence time. Preserve per-arm attempted denominators and missing measurements. Collect independent support/usefulness reviews and disagreements using the rubric above.

Operational comparison remains blocked on a named operator/team and source owner, permitted/versioned sanitized access, cohort selection, retention/access rules and owner-approved success thresholds. No actual current-operator baseline, measured human time, calibration result or pilot evidence is available here. Thresholds must be settled before the applicable acceptance study; tiny synthetic fixture scores cannot substitute for those inputs or any production remediation acceptance.
