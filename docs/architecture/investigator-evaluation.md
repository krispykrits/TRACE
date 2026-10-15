# First investigator evaluation and Sprint 5 gate

Issue [#39](https://github.com/krispykrits/TRACE/issues/39) connects actual [bounded investigator](bounded-investigator.md) / [CLI](investigator-cli.md) outputs to the [#14 scorer](development-evaluation.md). [ADR 0020](../adr/0020-investigator-evaluation-and-artifact-isolation.md) records the process/artifact boundary. This is an offline assembled-path contract run, not a real-provider diagnostic benchmark or Local MVP release.

## Execute and rescore

Use a fresh output directory from the repository root after [setup](../development.md#setup-and-first-run):

~~~sh
uv run --locked python -m evaluation.investigator run --output /tmp/trace-sprint-05
uv run --locked python -m evaluation.investigator rescore --run-dir /tmp/trace-sprint-05
~~~

The first command runs every case in the versioned [protocol](../../evaluation/investigator_protocol_v1.json) through the public CLI in fresh child processes with real SQLite, local corpus/index and read-only workers. The provider and runtime support decisions are explicitly hand-authored fixtures. The fake uses observed source gaps for abstention, and a constant placeholder cause; it never reads expected cause labels. Negative label results are retained. `actual_provider_calls=0` and `offline_fixture` are explicit. No credentials or paid opt-in are forwarded to the child.

The second command verifies bounded artifact bytes, exact protocol, implementation/lock hashes and source revisions, then regenerates identical canonical scores without subprocesses, provider requests, tools or a source database. It requires the recorded source checkout. Different fresh executions have normal differing job/call IDs and measured wall times; deterministic rescoring means identical scores from the same saved artifacts.

The first retained run is [investigator_offline_v1](../../evaluation/reports/investigator_offline_v1/manifest.json); its [Sprint 5 review](../sprints/sprint-05-review.md#demonstration-and-reproducibility) records measured results and open gates. Rescore it with `uv run --locked python -m evaluation.investigator rescore --run-dir evaluation/reports/investigator_offline_v1` at the manifest's implementation checkout.

Exit 0 means the offline mechanical contract passed. Exit 1 means scoring finished but a planned outcome or critical boundary check failed; the complete report still includes every attempt. Exit 2 means invalid configuration/artifact/version/hash or execution/storage failure prevented a valid score bundle. `run --mode live` fails explicitly without a fixture fallback. No new live permission is inferred from this task.

## Predeclared cohort and gate

Protocol `sprint-05-investigator-protocol.v1` is recorded before measurement and includes all ten planned attempts:

| Cohort | Cases |
| --- | --- |
| Four development incidents | Seed-17 `c01` regression, `c02` dependency degradation with noncausal Payment/Notification deployments, `c03`/`c04` insufficient Payment capture |
| Six mechanical boundary checks | Malformed generated assessment, model timeout, cross-scope/nonadmitted citation, hostile observed instructions, evaluator-marker rejection and source dependency failure |

Related scenarios stay in `order-payment-timeout-v1`. Existing validation/final-test groups remain reserved, ungenerated and untouched. There is no new family allocation or tuning on hidden answers. Hostile input uses fixed nonanswer sentinels; actual evaluator labels never enter a child, prompt, tool or corpus.

The offline gate requires all planned attempts accounted for, their expected mechanical outcomes, and no unresolved access, citation or label-isolation failure. Failed jobs remain in denominators. A fake continuing to emit a scripted answer is not proof of real-model prompt-injection resistance. The hostile-instruction case checks instruction/data roles, unchanged grants and current saved disclosure; actual model robustness remains unmeasured.

Sprint 5 numeric diagnostic criteria, paid run scope/known spending, source/transmission approval and actual support-review coverage are not supplied. They remain owner gates before the relevant real measurement. This protocol selects no quality/performance threshold, does not consume a model allowance and does not replace S6's [#63–#68 acceptance track](../planning/capstone-project-plan.md#backlogs-and-dependencies).

## Scores and denominators

`investigator-output-scorer.v1` validates `assessment.v2` and projects its candidate into #14's unchanged v1 label/claim-support rubric. The old runner and historical fixtures remain available. An optional authorized-reference set lets the rubric count independently checked knowledge citations as well as operational evidence; the default v1 behavior stays unchanged.

Every rate records numerator, denominator and value (null for an empty denominator). Reports include all ten attempts, plus separate development-incident and boundary-check summaries, so safety fault cases cannot disappear from the totals or masquerade as a diagnostic cohort.

| Measure | Definition |
| --- | --- |
| Schema validity | Valid v2 candidate / all attempted cases; rejected malformed responses and missing outputs are distinct |
| Cause/service accuracy | Exact candidate primary label/service matches / all answerable attempts, including failures; never interpret a fixture rate as model quality |
| Assessment accuracy | Candidate supported/abstained status matches the evaluator-only expected status / all attempts |
| Structural abstention accuracy | Abstention with a reason, missing-evidence explanation and every actual unavailable-source gap recorded / insufficient-evidence attempts; semantic justification still needs review |
| Citation validity | Claim references with authorized saved mappings / all claim references in valid reports; source revisions/times, knowledge generation/chunk identity and unredacted projection hashes are checked |
| Timeline order/completeness | #14's ordered known sequence and exact full supplied snapshot sequence / all attempts; model-context omissions remain visible |
| Delivered timeline validity | Authorized observed-time/ID ordering, source revisions, event/collection timestamps and agreement with candidate timeline / all attempts |
| Human unsupported-claim rate | Agreed unsupported claims / agreed determinate human-reviewed claims; disputes/indeterminate judgments are excluded and reported separately |
| Offline contract | Expected mechanical outcomes / all planned attempts; any critical boundary failure denies the gate |

Runtime execution status, publication/support status, candidate status and evaluation correctness remain separate. Fictional runtime support ports exercise accepted publication but never count as evaluation human judgments. Valid citation IDs do not establish claim support. Pending/unreviewed candidate content does not become an accepted operational assessment through scoring.

## Support sample and independent review

`support_sample.json` samples every claim emitted by the four base incidents, as declared before measurement. It includes claim text, exact admitted/redacted citation projections, contradictions and a binding to attempt/case/seed, report, observed input, citation mapping and rubric hashes. It contains no fabricated verdict. `human_reviews.json` initially has an empty review list and the exact sample hash.

An actual reviewer can create a separate private review file using that envelope. Each supplied row has `binding_id`, `reviewer_id`, `kind=human_review`, `verdict` (`supported`, `unsupported`, `indeterminate`) and a concrete `rationale`. The binding must be in this exact sample. Duplicate reviewer/binding decisions, cross-report bindings and sample-hash mismatches fail. Multiple reviewers may disagree; no majority or automatic endorsement is invented. Use #14's [support rubric](development-evaluation.md#citation-support-review-rubric), including whether observations, causal claims and alternatives are actually supported rather than merely cited.

~~~sh
uv run --locked python -m evaluation.investigator review --run-dir /tmp/trace-sprint-05 --reviews /absolute/private/actual-human-reviews.json --output /tmp/trace-sprint-05-human-scores.json
~~~

The command creates a new private score artifact with review/run hashes and leaves frozen inputs/scores unchanged. Review files are trusted supplied records, not authenticated reviewer infrastructure. AI fixture judgments, runtime `ScriptedReviews`, retrieval's earlier blanket endorsement and PR merge do not become per-claim human evidence. Actual review coverage is reported, including zero, and remains a named blocker until judgments arrive. This does not modify runtime support grants or promote stored outcomes.

## Artifacts, provenance and isolation

Output is an exclusive mode-0700 directory with mode-0600 files. A final `manifest.json` is written last; an incomplete run cannot count as accepted. It binds protocol, all planned per-case inputs/results/execution/source manifests, support sample, actual review file and canonical scores, plus recursive runtime/evaluator/script implementation hashes, pyproject/lock hashes and checkout/dirty state. Original code/source manifests and frozen component reports are never rewritten to make a new scorer match them.

Per-case artifacts preserve only synthetic observed input, authorized CLI export, exact source-revision/projection hashes and content-free execution metadata. Metadata includes selected model/configuration, prompt/tool/policy/pricing versions, attempts/job outcomes, elapsed wall time, model/tool counts, native usage and estimated cost availability. Unknown usage/cost remains null; a reservation is not actual usage or an invoice. Simulated token counts/costs are labeled synthetic port measurements, and measured CLI wall latency is distinguished from the fixed simulation clock. Raw prompts, raw rejected responses, credentials, private grant/profile files, SQLite state and review-port rationale are excluded from saved scoring bundles.

The evaluator loads development truth in its parent process. The separate `scripts.investigator_suite` child receives only a development generator selector and mechanical fault choice; its fake receives admitted operational context. It records any loaded `evaluation` module as a gate failure. Current source/corpus grants come from explicit trusted fixture composition, not from expected labels. This separation plus import/behavioral tests is a local architectural guardrail, not an OS sandbox against trusted code/filesystem access.

Saved bundles are authorized evaluation exports in the controlled local filesystem. Rescoring renders metric/provenance results, not an operational report read or new transmission grant. Copies and historical scores cannot be erased retroactively; real-source evaluation/export rights and retention must be separately approved. Report IDs still confer no current source access.

Independent retrieval/context/tool contracts and frozen reports are reused by identity/hash. No retrieval threshold is retuned or historical report rescored with incompatible code. The [Sprint 5 review](../sprints/sprint-05-review.md) records actual results, historical live connector evidence, blocked live diagnosis/human review and S6 handoff. Fast CI runs the assembled deterministic path; paid checks remain separately opted in under the [provider guide](model-provider.md#reproduction-and-live-evidence).
