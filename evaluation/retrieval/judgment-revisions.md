# Development judgment revisions

2026-10-12: the project owner reviewed the original bundle and recommended corrections before acceptance. This is actual review feedback, not approval of the revised suite. Human sign-off remains pending; no complete human decisions have been manufactured.

The original [v2 suite](queries_v2.json), [bundle](review_bundle_v2.md), [protocol](acceptance_v1.json), empty review snapshot and exploratory reports are retained. They describe the original proposals, not accepted gold. Their scorer is available at commit `f7635cef120944cefe010a17a4fa260d8db94e14`; use that checkout for original v2 report rescoring. Current commands use scorer v2 and suite v3. Historical report hashes do not change.

| Owner finding | Revision in v3 |
| --- | --- |
| `exact-code-2` omits the timeout runbook's Scope, which answers whether a symptom identifies the failing configuration | Add Scope to the related causal-code questions (`exact-code`, `-2`, `-3`, `-6`). Add Missing evidence's direct warning against causal guesses from symptoms. Remove Evidence checks from `-2`/`-3`, where preserving codes does not directly answer the causal-label question. |
| `production-approval` omits the eligible certificate archive's Investigation lesson | Add this passage across the seven production-approval variants; retain the runbook's explicit authorization warning. Payment eligibility includes both documents. |
| `service-identity-5` asks about accepted receipts versus failed requests, but reviews a service-identity claim | Replace its probe with “Failed requests and accepted receipts are distinct observations.” |
| `service-boundary-4` asks about real charges, but reviews a deadline claim | Replace its probe with “The Payment development fixture makes no real charge.” |
| Other variants reuse claims that fail to address their questions | Audit the families; align Payment input, Order argument/dispatch, delayed source identity, queue health/deployment, missing-evidence, historical recovery and production-approval probes with their specific questions. Unsupported probes remain explicitly unsupported; they are not silently turned into evidence. |
| `stale-certificate-3` is answerable from policy metadata even though no expired passage is eligible | Declare relevance scope `eligible_passage_content`. Reword metadata-only stale requests (`-2`, `-3`, `-5`) to request eligible passage content. Separately check each stale case's actual eligibility at 12:04, freshness deadline 12:05, exclusion at 12:10 and saved-citation denial. An empty passage-gold set does not claim that freshness metadata is unanswerable. |

The [v3 suite](queries_v3.json) still has 100 questions in 15 development families: 84 with proposed relevant eligible passages and 16 with none. It now has 211 review targets (100 relevance sets plus 111 passage/claim pairs). No family enters validation/final-test data. These are revised proposals until the owner endorses the actual sets/verdicts in [the new bundle](review_bundle_v3.md).

[Protocol v2](acceptance_v2.json) rebinds the revised suite hash while preserving every owner threshold/configuration field and the original threshold approval timestamp. That timestamp records approval of thresholds, not approval of the revised labels. No acceptance run has happened. Label corrections must not become a reason to lower a threshold. Current-policy exclusion is a correctness requirement, separately verified from rank metrics; its failure also prevents acceptance.
