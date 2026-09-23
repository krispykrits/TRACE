# TRACE production-usefulness review

Date: 2026-09-23. Scope: source review of the local educational implementations, supplied Volume 5/6 architectures, and TRACE GitHub planning at commit e8f08e8c62f68e7da682356cb171087d7417ca0c. This is a planning assessment, not production certification. No application implementation or cloud resources were changed.

## Recommendation

Keep TRACE's approved MVP-first delivery order. Reuse selected components through TRACE-owned contracts; do not assemble the educational applications unchanged. Add a separate operational pilot gate: synthetic evaluation and cloud deployment do not demonstrate usefulness to an on-call engineer.

Start with a read-only investigator that accepts a service and incident window, assembles an auditable evidence timeline, identifies supported hypotheses and missing information, and suggests the next useful check. Its first value should be faster evidence collection and less manual navigation. Reliable abstention is useful even when a root cause cannot be established.

The project owner approved this review and all recommendations on 2026-09-23. The companion [roadmap amendment](production-roadmap-amendment.md) records the adopted changes. Findings and test results below are the review snapshot; approval does not mark implementation work complete.

## Inventory and reuse decision

The requested ai-incident-triage directory identifies itself as Volume 1 in README and package metadata. A separate ml-incident-anomaly-detector exists and was included as the likely Volume 2 implementation.

| Asset | Reuse | Replace or defer |
| --- | --- | --- |
| ai-incident-triage | Incident/service vocabulary, small deterministic algorithm fixtures, separation of transport and orchestration concepts | In-memory lifecycle, text-overlap diagnosis, simulated action execution and generic search/planning as the runtime investigator |
| ml-incident-anomaly-detector | Offline training, artifact metadata/checksum patterns, temporal features, classical detector as a later benchmark candidate | Development fallback in production, illustrative Bayesian weights, hard-coded dependencies/threshold diagnoses, generic confidence and label-bearing runtime inputs |
| dl-telemetry-incident-detector | Predictor boundary, feature/class compatibility checks, training-only preprocessing fit, chronological LSTM evaluation, model comparison/reporting | Default production deployment; require evidence of benefit over statistical/classical baselines first |
| incident-search | Strongest direct reuse candidate: provenance, original offsets, stable chunk IDs, pinned encoder, atomic generations, hybrid/semantic adapters, evaluation harness | Synthetic-only source contract, unauthenticated API, whole-corpus in-process deployment assumptions, lack of freshness/revocation and answerability policy |
| Volume 5 | Design input: evidence-first workflow, typed tools, context limits, structured assessments, abstention, deterministic authorization | No implementation exists to import; implement these capabilities within TRACE |
| Volume 6 | Design input: evaluation, durable jobs, operational telemetry, release controls, cost/reliability testing | No implementation exists to import; integrate incrementally rather than building a prerequisite standalone platform |

## Findings that affect production reuse

Source paths below are relative to /home/christian/projects/applied-ai. Findings distinguish observed code behavior from proposed integration controls.

### 1. Triage returns simulated investigation progress rather than gathered evidence

ai-incident-triage/src/incident_triage/domain.py: InvestigationAction.execute returns an instruction string. integration.py:123 builds investigated:<action> facts and searches until actions have been visited. This does not query an operational source. The repository is a process-local dictionary (repository.py:10), so restarts lose state and workers do not share it.

TRACE should retain the vocabulary but build typed, bounded source adapters and persistent investigation/evidence records. A tool attempt, a successful observation and an inferred conclusion must be different records.

### 2. Triage confidence is heuristic and can ignore evidence because of casing

integration.py:77-106 constructs 0.75/0.25 likelihoods from word overlap. Likelihood keys are lowercased, while default evidence retains symptom casing. probabilistic.py looks up exact strings and applies the same fallback likelihood to every cause when a key is absent; an uppercase symptom can therefore leave relative priors unchanged. CSP candidate filtering also does not filter the ranked_causes call.

These are static findings, not newly added failing tests. Do not promote these scores as calibrated root-cause probabilities. Reuse deterministic rules only when their evidentiary semantics and provenance are explicit.

### 3. ML readiness can mask missing or incompatible artifacts

ml-incident-anomaly-detector/src/application/detector_service.py:28-40 selects development_fallback whenever no artifact loaded. interfaces/http/api.py:63-70 still reports ready. That fallback reaches reasoning/learning_system.py and training/anomaly_detection.py, where an IsolationForest is fitted on request records selected using incident_label. The runtime HTTP schema accepts this evaluator-style label. Thus the fallback can train during a request and use supplied labels, despite the normal persisted-artifact path correctly separating training from inference.

Production mode should fail readiness when its required model is absent/incompatible; a deliberately selected statistical baseline must be a separately named and versioned capability. Remove labels from operational input contracts. Report the loaded artifact's actual version/threshold, not only settings.model_version/settings.decision_threshold as the current HTTP metadata does. Bound input size and validate source/service/time semantics.

### 4. DL classification has no operational stream identity

The DL telemetry schema contains timestamp and 14 features but no service/environment identity. StreamingPredictor (inference/predictor.py:98-121) holds one arrival-order list; it does not partition by source or enforce event ordering/cadence. Frame validation rejects duplicate timestamps, but not out-of-order or stale samples. IncidentPrediction.timestamp is prediction time (line 92), not the evidence window.

Before live reuse, isolate streams by service/environment, define late-data and missing-data policies, record window start/end and generated_at separately, enforce training/inference window compatibility, and provide unknown/out-of-distribution handling. This is a known-class classifier, not a general root-cause detector.

### 5. The DL dataset does not establish temporal benefit

data/generator.py:40 uses an 80% anomaly default and line 58 samples independent class labels per timestamp with clear synthetic signatures. Contiguous chronological splitting is implemented for LSTM evaluation; the concern is realism, not an assertion that the current LSTM evaluation uses random splits. Independent snapshots do not establish useful incident progression, rare-event alert quality or cross-service generalization.

Evaluate by held-out service/time/incident episode, include realistic base rates and missing telemetry, and measure false alerts per service-day, detection delay and downstream investigator benefit. Keep neural inference optional until it wins on these measures.

### 6. Retrieval is reusable, but its production boundary is new work

incident-search/src/incident_search/domain.py:30 requires synthetic:// sources; Filters at line 80 contains only caller-controlled service/type filters. api/__init__.py has no authentication/authorization dependency. A service filter is not an access-control decision.

TRACE needs source-owned stable identities and revisions, access scope derived from the authenticated principal, filtering before candidate retrieval and authorization checks when resolving citations. Add document updates/deletions, freshness, tombstones and revocation behavior across generations. Preserve immutable evidence snapshots subject to retention/access policy. A first pilot can be single-organization; this does not require building a multitenant SaaS platform.

The current search scans eligible chunks and exact dense vectors in process. Keep that as the small-corpus correctness baseline. Move storage behind an adapter when concurrency, freshness or measured scale requires it; PostgreSQL/pgvector can fit the supplied design but is not a reason to discard the existing retrieval contract. Do not add a reranker solely because the target diagram includes one.

### 7. Retrieval scores do not establish claim support or answerability

The recorded frozen synthetic test report has semantic Recall@5 0.629 / MRR 0.858 and hybrid Recall@5 0.613 / MRR 0.875. Semantic leads recall; hybrid leads first-relevant rank. These are previous experiment results, not a rerun in this review. The report explicitly documents cross-service ambiguity, negation confusion and absent-knowledge matches.

The corpus has 300 synthetic documents and only 20 frozen test queries with agent-authored judgments. Production validation needs human-reviewed passage/claim support, time-valid relevance, access filtering and unknown-answer cases. Citation ID existence is necessary but does not prove that the cited passage supports a claim. No universal cosine/RRF threshold should be presented as confidence.

## Reconcile the Volume 5 and 6 designs

1. Preserve Volume 5's observed/inferred/uncertain/abstained assessment semantics. Volume 6's root_cause/confidence example must not force one answer; use hypotheses, supporting/contradicting evidence and explicit insufficiency.
2. Keep execution status separate from assessment and review status. A completed job can contain an abstention; a failed job is not an abstention. Add cancellation, expiry, partial source failure and retry-attempt records.
3. Move provenance, scoped authorization, redaction, model/tool budgets, tracing and evaluation into the first vertical slice. Volume 5's later evaluation/observability steps and Volume 6's post-deployment observability phase are unsuitable as the first appearance of those controls.
4. Implement durable dispatch before hosting long-running investigations. Persisting a job and publishing a queue message as two independent writes leaves a loss window. Use transactional job polling or an outbox with idempotent consumers; test crashes and duplicate delivery. External model retries can still incur duplicate charges, so record attempts and bound spend rather than claim exactly-once provider execution. See [AWS transactional outbox guidance](https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/transactional-outbox.html).
5. Expand Evidence beyond content plus an optional timestamp: source record/revision, observed_at, collected_at, service/environment, query window, retrieval/tool version, access classification, integrity hash and redaction status. Represent missing and truncated source results explicitly.
6. Keep authorization outside prompts and apply it to tools, evidence reads, exports and citations. If PostgreSQL row security is selected as defense in depth, test the actual runtime role: owners and privileged roles may bypass normal policies. See [PostgreSQL row security documentation](https://www.postgresql.org/docs/18/ddl-rowsecurity.html).
7. Start with one implementation repository and a modular application, separating worker/API deployment only where needed. Pin imported code/artifact versions; do not depend on editable sibling directories. The generic ML package name src needs repackaging or a narrow adapter before integration.
8. Keep investigation read-only. Review approval of an assessment is distinct from authorizing a future action. Simulated consequential actions can satisfy the capstone experiment; real remediation is a separate product scope.

The documents are reference architectures, not instructions to execute their implementation steps now. In particular, Volume 6's statement that its gates precede Volume 7 does not override the user's decision to implement those capabilities inside TRACE.

## Evidence of usefulness

Use two tracks: synthetic scenarios for controlled regression and an authorized operational cohort for usefulness. Choose one team/service and one telemetry/deployment/knowledge source first. Sanitized historical replay can precede live read-only shadow operation. If access is unavailable, report the pilot gate as blocked; synthetic success does not substitute for it.

Compare TRACE with the engineer's current dashboard/search workflow and a deterministic evidence bundle, in addition to the capstone's LLM ablations. Measure time to first useful evidence, time to a defensible next action, manual investigation effort, unsupported-claim rate, justified abstention, citation support, missing-data disclosure, reliability and cost. Use paired cases, record reviewer disagreement and avoid claiming causal MTTR reduction from a small offline study.

Set numeric thresholds with the pilot owner before acceptance; no workload, budget or operator baseline was provided. Security boundary regressions, cross-scope evidence disclosure and acceptance of invalid evidence IDs should be release blockers in the tested suite. Passing that suite is not proof that such failures are impossible.

## Validation performed

| Project | Current result | Qualification |
| --- | --- | --- |
| ai-incident-triage | 37 passed | Native .venv failed collection because FastAPI is missing. Passed using ml-incident-anomaly-detector/.venv with PYTHONPATH=src; not a clean-install reproducibility pass. |
| ml-incident-anomaly-detector | 111 passed | Existing project .venv; one dependency deprecation warning. |
| incident-search | 56 passed | Existing .venv, HF_HUB_OFFLINE=1; includes integration tests with local cached model; one dependency deprecation warning. |
| dl-telemetry-incident-detector | Not validated dynamically | No project .venv. Available search environment lacks pandas; available ML environment lacks torch. Collection failed; no dependencies installed. Static review only. |

Commands: python -m pytest -q in the respective project; triage used the ML interpreter and PYTHONPATH=src. DL attempts used -o addopts=, so even a successful attempt would not have certified its configured coverage gate. No model training, load test, fresh dependency install, cloud test or real operational-data evaluation was performed.

## Sprint readiness

Complete the charter/reuse decisions before skeleton work, as current issues #1 and #2 already require. Record the first operator workflow, data-access owner, packaging/runtime details for the approved TRACE repository, dependency budget and production-pilot gate. Credentials are not needed to define schemas, build replay/adapter tests or implement persistence and evaluation contracts. Live integration and operational usefulness acceptance do require actual authorized sources.

The current roadmap remains a useful backbone. The change is stronger evidence of utility and earlier operational contracts, not a larger collection of AI techniques.