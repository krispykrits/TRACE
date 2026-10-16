# Local MVP owner decisions — 2026-10-16

This record captures owner decisions for [#63](https://github.com/krispykrits/TRACE/issues/63) before acceptance measurement. [Version 2 decisions](../../evaluation/local_mvp_decisions_v2.json) own the numeric settings; [protocol v2](../../evaluation/local_mvp_protocol_v2.json) owns coverage and review semantics. The original v1 inputs and [draft evidence](../../evaluation/reports/local_mvp_preparation_v1/README.md) remain unchanged.

## Approval provenance

In the TRACE owner conversation on 2026-10-16, following the concrete recommendation and explanation of its $0.405504 reservation estimate, the owner said:

> got it. I like the recommendation and I will be doing the human review

When asked whether a second independent engineer would review or the owner would be the sole reviewer, the owner explicitly answered:

> I’ll be the sole reviewer

Codex transcribed these statements. They establish accepted planning settings and the owner's intended review role. They do not contain actual claim judgments, implementation/PR approval, current spending facts, final hash-bound run approval or permission to merge. No approval timestamp is invented for the messages; the record identifies their client-local date and conversation context.

## Accepted planning settings

The canonical JSON records: schema/completion/citation/timeline validity 100%; cause/service accuracy at least 80%; assessment accuracy at least 90%; abstention accuracy 100%; zero unsupported reviewed integrated claims; elapsed p95 at most 60 seconds; maximum estimated per-investigation model cost $0.02. These are Local MVP engineering targets on the existing four-case development cohort, not general reliability claims or transferred retrieval thresholds.

The accepted plan uses three repeats and three arms: 36 attempts, 24 model investigations, at most 72 model calls. Per investigation: three model calls, 16,384 input-token allowance and 2,048 output tokens per call, 20 integrated tool calls, a 120-second hard deadline, zero automatic paid retries and serial execution. LLM-only has no tool channel. The $1 run allowance remains subject to verified monthly headroom within the separate $20 application model cap. Under the frozen repository rates the maximum reservation estimate is $0.405504; this is not measured spend or verified current billing.

## Human review

`krispykrits` is the sole planned Local MVP reviewer. Review all 12 integrated reports and every emitted claim, with explicit abstention-adequacy and next-check-usefulness judgments for every report. There is no fixed claim quota: concise reports must not be padded to satisfy sampling requirements. Missing output/review coverage remains a failure or blocker, never a smaller successful denominator.

Retain exact statement/citation/report/input/rubric bindings, reviewer identity, original verdicts/rationales and any assistance or prior scenario familiarity. The owner's review is independent of the model's own assertions but is not a second-person, blinded or independently replicated review. Do not report inter-rater agreement from one reviewer or count Codex explanations/transcription as another human judgment. No actual review has occurred for the new run.

All primary causal assertions need determinate supported judgments. Any unsupported claim fails the zero-unsupported threshold. Indeterminate or vague claims provide no positive support; zero determinate support cannot pass. An explicit justified abstention remains valid when evidence is insufficient. Unassessable consequential claims, inadequate abstention, unsupported next checks and unresolved consequential objections block release. LLM-only review coverage is descriptive and does not impose an integrated-arm release gate. Evidence bundles emit no generated diagnosis to support-review.

This owner-selected single-reviewer policy applies only to Local MVP. The [final-study independent-review policy](../architecture/development-evaluation.md#citation-support-review-rubric), Operational Pilot, runtime source/support authorization and production-remediation approval remain distinct. A later second review is a new bound artifact; preserve the original owner decisions and any disagreement.

## Retention and resources

The planning budgets are 4 GiB memory and 2 GiB artifact storage. The actual host's capacity and controller enforcement still need verification; no resources were provisioned and no OS sandbox is claimed. New private working copies have a 30-day retention expectation. Selected sanitized evidence remains subject to repository evidence-preservation rules; this does not authorize deleting frozen reports or rewriting hashes. Cleanup responsibility remains unassigned pending an explicit operational record.

## Remaining run gates

Actual provider/model/API/configuration and arm prompt/tool/policy revisions, current spend/outstanding reservations and shared journal, applicable source/transmission permissions, a concrete live-run scope/stop contact and final protocol/decision/source approval bindings remain to be recorded and checked. The $1 planning allowance does not start the run or supply those facts. Keep missing facts null and preserve partial/unknown usage; do not substitute zero spend or old connector results.

The current v2 planner validates settings and prepares a cost/schedule/review manifest. #64 must implement actual comparison execution and #65 must collect/reconcile real owner judgments before release assessment. No paid call or acceptance run was made while recording these decisions.
