# Development judgment revisions

## Review provenance correction — 2026-10-12

The findings below were **AI review findings relayed by the project owner**, who requested implementation corrections. The earlier record incorrectly called them an actual project-owner review. That attribution is withdrawn. AI findings, an instruction to revise, or a request to review a bundle do not establish human review or endorsement of passage/claim judgments.

The owner supplied the acceptance configuration before measurement and initially named themselves as the intended human reviewer. Those planning inputs are separate from judgment review. All v2/v3/v4 review files remain empty; no actual human verdicts or acceptance result are recorded.

The original v2 proposal suite/bundle/protocol and exploratory reports remain available. Their scorer is at commit `f7635cef120944cefe010a17a4fa260d8db94e14`. The v3 scorer and exact bundle before the second correction are at commit `0c38dfb9c06386bf2e407bae8dfd20a0b98268c8`. Use the corresponding checkout to rescore archived reports. Current commands use scorer v3 and suite v4. Historical report snapshots/hashes do not change.

## First AI findings and applied v3 corrections

| AI finding relayed by owner | Revision in v3 |
| --- | --- |
| `exact-code-2` omits the timeout runbook's Scope, which answers whether a symptom identifies the failing configuration | Add Scope to the related causal-code questions (`exact-code`, `-2`, `-3`, `-6`). Add Missing evidence's direct warning against causal guesses from symptoms. Remove Evidence checks from `-2`/`-3`, where preserving codes does not directly answer the causal-label question. |
| `production-approval` omits the eligible certificate archive's Investigation lesson | Add this passage across the seven production-approval variants; retain the runbook's explicit authorization warning. Payment eligibility includes both documents. |
| `service-identity-5` asks about accepted receipts versus failed requests, but reviews a service-identity claim | Replace its probe with “Failed requests and accepted receipts are distinct observations.” |
| `service-boundary-4` asks about real charges, but reviews a deadline claim | Replace its probe with “The Payment development fixture makes no real charge.” |
| Other variants reuse claims that fail to address their questions | Audit the families; align Payment input, Order argument/dispatch, delayed source identity, queue health/deployment, missing-evidence, historical recovery and production-approval probes with their specific questions. Unsupported probes remain explicitly unsupported; they are not silently turned into evidence. |
| `stale-certificate-3` is answerable from policy metadata even though no expired passage is eligible | Declare relevance scope `eligible_passage_content`. Reword metadata-only stale requests (`-2`, `-3`, `-5`) to request eligible passage content. Separately check each stale case's actual eligibility at 12:04, freshness deadline 12:05, exclusion at 12:10 and saved-citation denial. An empty passage-gold set does not claim that freshness metadata is unanswerable. |

## Further AI findings and applied v4 corrections

| AI finding relayed by owner | Revision |
| --- | --- |
| `exact-code-4` asks how to compare errors with duration, but probes discuss code preservation/symptom labels | Use passage-specific claims about same-window caller failures, Payment durations/dependency spans, separately observed effective timeout settings, and source-linked duration/budget/configuration evidence. |
| `exact-code-5` asks for evidence vocabulary, but repeats the same probes | Use each passage's actual vocabulary: failures, work durations, dependency spans, effective budgets/settings and configuration revisions/history. |
| `saved-permission-5/-6` ask what to disclose and when to revalidate | Probe the disclosed withdrawal/freshness limitation and the explicit condition for requesting authorized revalidation. Related saved-permission variants now address standing access, stale-source handling and withdrawal. |
| Other reused claims can miss parts of their questions | Align the certificate observations, correlation/service fields, historical-transfer and production-approval variants. Deliberately unsupported probes remain labeled; literal support is not a substitute for query alignment. |
| The v3 bundle tells reviewers to use `reviews_v2.json` while the evaluator reads v3 | The generator and CLI share one current review-file default; explicit `--reviews` is passed through to the generator. V4 instructions identify `reviews_v4.json`. Unit and process checks cover custom review-file selection. The archived v3 bundle carries an obsolete-instruction notice. |
| The record labels AI findings as actual project-owner review | Correct attribution explicitly in this record, status and PR/issue evidence. No human review records are created from AI findings. |

The [v4 suite](queries_v4.json) retains 100 questions/15 development families, 84 proposed passage-answerable cases, 16 without relevant eligible passages and 211 review targets (100 relevance sets plus 111 passage/claim pairs). Gold passage sets and query text are unchanged from v3; corrected probe claims and verdicts produce a new suite hash. These remain AI-authored proposals until actual human review of [the current bundle](review_bundle_v4.md).

[Protocol v3](acceptance_v3.json) rebinds the suite hash and preserves all owner threshold/configuration fields and their original approval timestamp. That timestamp records threshold approval, not endorsement of labels. No acceptance run has happened. AI corrections cannot lower a threshold or satisfy the human gate. Source-policy exclusion remains a separately verified correctness requirement. No family enters validation/final-test data.
