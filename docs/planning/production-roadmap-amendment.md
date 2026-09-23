# Approved TRACE roadmap amendment: production usefulness

Status: approved by the project owner on 2026-09-23, including all recommendations in the implementation review. This amendment supplements the MVP-first plan and governs production-usefulness acceptance; it does not commit calendar dates or capacity. See [implementation review](production-usefulness-review.md) for source findings and validation limits.

## Change the release claims

Keep Local MVP (S1-S6), Cloud MVP (S7-S9) and Full Capstone (S10-S18). Add an independent **Operational Pilot** gate. Local MVP proves an evaluated vertical slice; Cloud MVP proves repeatable hosted operation; Full Capstone proves academic capabilities and the controlled study. None alone establishes production usefulness.

Operational Pilot acceptance requires authorized real or sanitized historical incident evidence, then read-only shadow operation with a named user/team; comparison with their current workflow; documented scope, cost and quality thresholds; recoverability/access controls; support ownership and operator feedback. Its timing depends on access and capacity. It may overlap existing releases, but cannot be declared passed solely from synthetic data or a demo.

Do not present existing 18 provisional increments as unchanged capacity estimates. Refine and resize affected increments; defer optional expansion before weakening pilot or safety gates.

## Targeted changes by sprint

| Existing increment | Approved addition/change | Acceptance evidence |
| --- | --- | --- |
| S1 Foundation | Adopt the reuse inventory. Mark V5/V6 as design-only. Choose one pilot user/workflow and data-access owner. Record source adapters, packaging, supported environment and budget decisions. | Charter distinguishes capstone completion from operational pilot. Existing test/environment gaps are recorded. Chosen code is versioned and reproducibly packaged; no sibling editable imports. |
| S2 Minimal workflow | Preserve Order/Payment synthetic replay. Define a source-neutral evidence envelope and adapter contract; add one sanitized export fixture when authorized. | service/environment, event/collection time, source revision, access classification and correlation survive normalization. Ground truth is absent from operational inputs. |
| S3 Evidence and scoring | Add durable investigation state and evidence snapshots; specify idempotency, cancellation, retries, partial failure and dispatch recovery. Define operator-task metrics now. | Restart preserves evidence/status. Duplicate submissions have documented behavior. Missing telemetry cannot become an observation. Scorers distinguish job failure from abstention. |
| S4 Retrieval and tools | Adapt Volume 4 rather than reimplement it. Keep semantic/lexical/hybrid baselines available. Introduce real source identity, time validity and authorization scope independent of caller filters. | Access tests cover search, tools, direct evidence reads and citations. Updates/revocations are enforced. Exact-code, stale-source, absent-knowledge and injection fixtures pass appropriate assertions. |
| S5 Investigator | Implement Volume 5 capabilities within TRACE: deterministic baseline gathering, bounded context, structured observations/hypotheses, claim support and abstention. Add execution/cost telemetry from first invocation. | Real provider contract test when credentials exist; offline stub tests remain explicitly distinct. Tool/model deadlines and budgets are enforced; malformed/unsupported output is rejected or safely degraded. |
| S6 Local gate | Retain LLM-only reference, add deterministic evidence-bundle baseline and human-reviewed support cases. Exercise failure/restart/duplicate handling relevant to the local runtime. | Reproduce quality/latency/cost/failure results and disclose synthetic limitations. Local gate does not claim operational pilot success. |
| S7-S9 Cloud gate | Apply V6 async and operational controls: durable workers, safe dispatch, access/identity, bounded retries, audit/redaction, backup/restore, retention/deletion and rollout rollback. | Worker crash and duplicate delivery tests; restore demonstration; access isolation; quota/provider failure handling; end-to-end latency including queue wait; teardown/recreation. |
| S10-S11 Detection | Reuse V2 classical pipeline as a candidate after hardening. Evaluate by service/time/episode with realistic base rates. Keep V3 DL optional. | False positives per service-day, detection delay and downstream time/tool/cost benefit versus statistical baseline; model failure never forces failure of evidence-only investigation. |
| S12 Retrieval refinement | Prioritize context/service disambiguation, passage support, freshness and absent knowledge before adding reranking or new stores. | Human-reviewed development results justify each retrieval change; source/access/citation behavior remains correct. |
| S13-S18 Evaluation/defense | Preserve five-arm capstone study and frozen held-out protocol. Report pilot results separately from synthetic study; include operator-workflow and deterministic-bundle comparisons. | Operational claims match cohort evidence. Negative ML/DL findings remain valid; any unavailable pilot data is disclosed as a blocked production claim, not hidden by capstone scores. |

## Architecture decisions to make before their implementation

- Use the TRACE repository for a modular Python application; separate API and worker entry points when durable execution needs them. Preserve educational repositories as reference implementations.
- Define Evidence, Investigation, Assessment, ToolResult, RetrievalResult and ModelSignal contracts. Scores have explicit semantics: ranking score, class probability, anomaly score and root-cause support are different quantities.
- Use persistent storage for job/evidence/audit state. If an external queue is selected, use an outbox or another recoverable dispatch design; otherwise a transactional database job runner is a reasonable initial option. Do not introduce a broker merely to match a diagram.
- Scope initial access to one organization/team, with least-privilege source credentials and server-derived access decisions. A caller-selected service filter is not authorization.
- Decide source retention, redaction, deletion, evidence snapshot access and prompt/log data handling before accepting real operational data.
- Choose one model-provider adapter and one operational source integration first. Implement deterministic fixtures and recorded replay while waiting for credentials. Fake-provider success never satisfies live-provider or operational-pilot acceptance.
- Defer autonomous investigation loops, real remediation, deep learning, a broad connector catalog and large UI work until measured need. The existing capstone's simulated approval boundary remains in scope.

## Backlog changes

| Existing item | Amendment |
| --- | --- |
| #1 Charter | Add named pilot workflow/user and access owner, independent pilot gate, source inventory, V5/V6 design-only status, reuse decisions and success metrics. Resolve owner decisions before #2 as already required. |
| #2 Repository/environment | Make selected dependency versions reproducible, package reuse without local path coupling, and separate runtime inputs from evaluation labels. Keep implementation limited to the agreed skeleton. |
| #9 Roadmap | Link this review and record the operational pilot gate; incorporate the approved S2-S6 and cloud acceptance criteria. Preserve Project Status, existing milestone assignments and undated future work. |

The existing S1-S4 issues (#1-#8 and #10-#19) were reviewed during adoption. Their relevant acceptance criteria are extended in place; no duplicate stories are required. Project Status, milestone assignments and implementation completion remain unchanged.

## First sprint focus

Deliver an accepted charter/reuse record, a supported and locked environment, a runnable/testable skeleton, configuration/redaction/logging foundation, and CI. Include concrete schemas/adapter examples in design artifacts where they resolve contract decisions; implement domain behavior in its planned increments. Reuse inspection reduces uncertainty but does not mean the educational components are production-approved.

Open decisions: pilot operator/team, accessible operational sources and permissions, workload/latency budget, cloud/model budget, package/runtime details, weekly capacity and university constraints. Assign an owner and deadline/gate for each. Credentials can remain pending for later integration while foundation work proceeds.