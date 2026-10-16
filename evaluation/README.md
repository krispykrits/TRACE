# Evaluation artifacts and reproduction

`evaluation/` is repository-only and excluded from the runtime wheel. Expected labels, fault schedules, candidate fixtures, reviewer judgments and reference answers must never enter investigator tools, corpus ingestion, prompts or exported operational inputs.

## What the existing artifacts establish

| Material | Evidence and limits |
| --- | --- |
| `ground_truth/` and `fixtures/candidates_v1.json` | Four seed-17 development cases and hand-authored candidates; scorer plumbing, not model quality |
| `reports/retrieval_development_v1.json` | Recorded lexical/semantic/hybrid document-ranking comparison with its source/model identity |
| `retrieval/review_bundle_v2.md` / `v3.md` / `v4.md` | Immutable proposal/revision snapshots; v2/v3 review files remain empty |
| `retrieval/queries_v4.json`, `acceptance_v3.json` and `reviews_v4.json` | 100 requests in 15 related development families; predeclared thresholds and the owner's later blanket endorsement of 211 relevance/support decisions |
| Frozen v4 passage reports | Exploratory baseline/candidate reports are not acceptance; the separate lexical acceptance report passed its recorded protocol |
| `fixtures/tool_choices_v1.json` | Agent-authored tool-choice/argument expectations: 18 cases/21 examples; legal API execution is separate from model-selected choice quality |
| `reports/sprint_04_evidence_package_v1.json` | Observed cited package without evaluator labels; scripted integration evidence |
| Actual-output Sprint 5 runner | [Protocol](investigator_protocol_v1.json), actual CLI/private artifacts, deterministic v2-to-v1 scoring, explicit failures and an unreviewed support sample; offline mechanical evidence only |
| [Sprint 5 human review addendum](reports/investigator_offline_v1_human_review_v1/README.md) | One guided owner review: 10/10 sampled claims indeterminate because the wording was too vague; zero determinate support evidence; original run unchanged |
| Offline investigator demo | Actual local application/storage/tool boundaries with hand-authored model/review records; zero actual provider calls or human review |

The v4 owner endorsement is shared blanket provenance, not fabricated per-target notes or independent end-to-end reviewer evidence. [Judgment revisions](retrieval/judgment-revisions.md) and [the passage contract](../docs/architecture/retrieval-evaluation-context.md) preserve the chronology and exact metrics. All 16 no-relevant v4 queries returning candidates remains a documented limitation.

## First investigator and Sprint 5

~~~sh
uv run --locked python -m evaluation.investigator run --output /tmp/trace-sprint-05
uv run --locked python -m evaluation.investigator rescore --run-dir /tmp/trace-sprint-05
~~~

Use a fresh directory. Ten planned development/boundary attempts run through the public CLI with an explicit hand-authored provider and fictional runtime review ports. All attempted cases and unknown usage remain visible. Actual human judgments initially number zero; sampled claim/citation bindings are ready for independent review. Live diagnosis is explicitly not run and blocked on owner run/budget/data/criteria/review inputs. This does not reaccept Local MVP, actual model quality or operational usefulness. See the [actual-output contract](../docs/architecture/investigator-evaluation.md) and [Sprint 5 review](../docs/sprints/sprint-05-review.md).

The later [human review addendum](reports/investigator_offline_v1_human_review_v1/README.md) preserves the owner's ten guided indeterminate decisions, completed packet and regenerated scores separately from the frozen run. All sampled claims were judged too vague to assess; the support rate remains unavailable with a zero determinate denominator. Its reproduction command makes no provider call and does not alter original artifacts.

The old `evaluation.runner` below remains the frozen v1 candidate-fixture path. Existing historical bytes/schemas are preserved.

## Current-source exploration

Use fresh output paths:

~~~sh
uv run --locked python -m evaluation.runner run --output /tmp/trace-s3-evaluation
uv run --locked python -m evaluation.runner rescore --run-dir /tmp/trace-s3-evaluation
uv run --locked python -m evaluation.retrieval_quality --modes lexical --output /tmp/trace-retrieval-current.json
uv run --locked python -m evaluation.retrieval_quality --rescore /tmp/trace-retrieval-current.json
~~~

A successful scorer process can contain failed candidates. Invalid input, changed hashes or incompatible source/scorer snapshots fail explicitly. [Development evaluation](../docs/architecture/development-evaluation.md) owns schemas, failure denominators and support-review/baseline protocols.

Semantic/hybrid comparisons require the locked optional extra and pinned cached model; follow [retrieval setup](../docs/architecture/knowledge-retrieval.md). Model preparation is explicit; model-free rescoring makes no new model call.

## Exact historical rescoring

Frozen reports identify the source/scorer/lock and input hashes used to produce them. Use that recorded checkout; do not edit frozen hashes or interpret a current-source mismatch as changed historical metrics.

V4 passage reports require the pre-refactor scorer at `43582e3f084ff645b1227bc139d4d441b99fd220`:

~~~sh
git worktree add --detach /tmp/trace-retrieval-v4 43582e3f084ff645b1227bc139d4d441b99fd220
cd /tmp/trace-retrieval-v4
uv run --locked python -m evaluation.retrieval_quality --rescore evaluation/reports/retrieval_passage_acceptance_v4.json
~~~

Choose an unused worktree path. Current code manifests include nested application modules; older reports keep their original module paths/identities. Preserve suite, review, protocol and report bytes. Create a new versioned artifact for revised cohorts/judgments or behavior.

## Cohorts and acceptance

Sprint 6 [Local MVP protocol preparation](../docs/planning/local-mvp-acceptance.md) uses protocol/decisions v2 with [owner-approved numeric planning settings and sole owner review](../docs/planning/local-mvp-owner-decisions-2026-10-16.md), plus a dry-run planner:

~~~sh
uv run --locked python -m evaluation.local_mvp --output /tmp/trace-local-mvp-plan-v2
~~~

Use a new directory. Exit 1 saves a valid blocked plan when required owner inputs are missing; it makes no provider call and measures no acceptance result. The current settings declare 36 attempts and a $0.405504 model reservation ceiling under frozen rates; actual usage, current spending and applicable live authority remain unverified. Review covers all integrated reports/claims and explicitly has one owner reviewer, with no new judgments. The original v1 draft/input/report bytes remain unchanged at their recorded checkout. Approval must bind exact protocol, decision and source hashes; the planner supplies no live authority or release endorsement. #64–#68 retain comparison, review, boundary and release implementation/evidence.

Related seeds, capture gaps, distractors and `payment-dependency.v1` variants form the `order-payment-timeout-v1` development group. Keep related variants together; opaque IDs are not diagnostic features. Existing four-case development data does not establish an independent final-test cohort.

Predeclare group allocations, allowed evidence/arms, thresholds, actual review coverage, budget/run scope and failure/unknown denominators before acceptance measurement. Validation/final-test data and held-out answers remain isolated; freeze the study before final-test access.

Representative operational replay requires named source/field/transmission/retention authority and actual recordings. The owner is the planned .NET service owner/initial investigator; generated .NET incidents remain a separate controlled-testbed cohort. [The Operational Pilot](../docs/planning/capstone-project-plan.md#independent-operational-pilot) has its own utility/access/support gates.

## Planned ML and ranked-response evaluation

[ADR 0018](../docs/adr/0018-flexible-ml-and-ranked-response-options.md) requires a justified evaluated ML contribution with a suitable method and baselines. S10–S11 select/evaluate it; S13–S17 retain the five-arm ablation and frozen held-out protocol. Classical ML, deep learning, pretrained and other suitable ML methods are candidates.

S14 versions the ranked-response contract and review rubric, including applicable alternatives, recommended-action rationale, uncertainty, benefit/risk, prerequisites and verification/recovery. [The future evaluation requirements](../docs/architecture/development-evaluation.md#planned-final-ml-and-response-evaluation--2026-10-15) are separate from existing v1/v2 fixture scores. Recommendations do not supply execution approval; actual remediation verification has its own evidence.
