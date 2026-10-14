# ADR 0013: Assessment validation and independent support review

- **Status:** Accepted for scoped Local MVP assessment validation after owner merge of [PR #52](https://github.com/krispykrits/TRACE/pull/52) / closure of #35; operational review and pilot gates remain separate
- **Date:** 2026-10-14 (America/New_York)
- **Scope:** Local MVP assessment acceptance; read-only, without an investigation loop or production authority

## Context

The owner closed #34 after merging PR #51. The provider gate protects each call, its admitted citation views and generated response access. A syntactically valid response can still invent references, conceal missing sources or overstate causal support. #14's frozen candidate/scoring contract already separates ID validity from human support; changing its serialized version would undermine historical rescoring. #35 requires contradictions, gaps, current scope/revision checks, justified abstention and a bounded next read-only check.

## Decision

Keep `investigation.assessment.CandidateReport` version 1 unchanged. Add `assessment_schema.AssessmentReport` (`assessment.v2`) with strict closed fields, supporting/contradicting references, explicit causal basis, source-gap IDs and a typed fixed-catalog next check. Preserve an explicit v1 projection for the existing evaluator; it omits v2-only detail and never replaces the full protected report.

`assessment_context` freezes the supplied evidence package and rejects execution-failed components. Its citation resolver uses the existing read-only tool port for current evidence and generation-bound knowledge reads, comparing full source snapshots privately. Output mappings contain only approved identifiers, offsets and timestamps; free-text knowledge section titles are withheld. Models cannot select a reader, grant scope or invent event order. The retained timeline comes from #13's observed ordering, with source identity/revision and observed/collected times preserved.

`assessment_validation` consumes only an issued protected provider response under its original scope and expected schema. It requires citations to be both in the supplied context and in the actual admitted projection, revalidates every contributing input and preserves its redacted view/provenance. Generated/derived responses retain the original most-sensitive classification. Reads revalidate current source and support decisions; exports also retain the provider transmission check. No declassification or mutation approval results from validation.

Separate `citation_validity` from `claim_support`. Unreviewed, indeterminate or disputed proposals remain `review_required`; agreed unsupported claims reject the report. Before marking an assessment accepted, an independently composed trusted review reader must supply current `human_review` decisions for every claim and the overall outcome/abstention/next-check rationale. Bind decisions to exact report content, scoped identity, sanitized cited views/provenance and disclosed gaps, never removed values or a public hash of raw sensitive context. Model-declared reviews and evaluator fixture expectations cannot satisfy this port. Human judgments support the stated strength; they do not prove causation or supply calibrated probabilities.

Review packets can sample claim IDs for #14's rubric. Partial sampling does not implicitly endorse unsampled claims. The outcome task protects justification of abstention and the recommended check, including reports without hypotheses. Recheck source permission after review reads before accepting/releasing content. Invalid/malformed reports are rejected; tool/storage failures remain `execution_failed`, not abstaining success. No automatic correction/model call is made; later corrections belong to #36/#37 accounting.

## Alternatives and tradeoffs

Accepting a cited ID as semantic support would label unrelated deployment evidence as proof. A model's confidence or its own review is not independent evidence. Text-overlap heuristics would introduce an unsupported root-cause scorer. The conservative local policy withholds acceptance pending trusted review while allowing scoped inspection of the untrusted proposal. This adds reviewer work; reconsider publication of explicitly unreviewed hypotheses only through a reviewed change preserving their status and source controls. An accepted read-only report is not an approved remediation.

Requiring a measured two-reviewer study for every local assessment would conflate #14's study protocol with this runtime safety gate. One trusted decision can satisfy local review; disagreements remain pending. Test reviewer records are explicitly synthetic and are not actual human review or utility measurements. Operational reviewer authentication/storage, inspection UI and persistent export remain #38/production gates.

## Verification and revisit conditions

Use deterministic schema/port checks and actual SQLite/process citation workflows. Include fabricated/denied/stale/revoked references, contradictory and unrelated-deployment fixtures, missing/truncated captures, insufficient-evidence abstention, storage failure, bound violations, denied wider access/declassification, changing review bindings and review-time source revocation. Keep fakes/fixtures/evaluators outside the wheel and model transports away from assessment acceptance/readers. No dependency change is needed.

Revisit when #37 integrates the investigator and #38 adds operator inspection/review storage, when actual reviewer work/utility warrants changing the conservative acceptance policy, or for operational identity/retention requirements. Preserve frozen reports and their recorded checkout for historical rescoring. No synthetic test proves diagnostic quality, Operational Pilot readiness, cloud acceptance or production remediation.
