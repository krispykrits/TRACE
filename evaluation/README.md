# Evaluation material

## Package refactor and archived source identity

The #46 package refactor preserves frozen suites, reviews and reports. V4 passage reports were produced with the pre-refactor scorer and require commit `43582e3f084ff645b1227bc139d4d441b99fd220` for exact rescoring. Do not modify their source hashes or interpret a current-source mismatch as changed historical metrics. For those reports:

```sh
git worktree add --detach /tmp/trace-retrieval-v4 43582e3f084ff645b1227bc139d4d441b99fd220
cd /tmp/trace-retrieval-v4
uv run --locked python -m evaluation.retrieval_quality --rescore evaluation/reports/retrieval_passage_acceptance_v4.json
```

From the current checkout, use a fresh exploration output path and rescore that new artifact:

```sh
uv run --locked python -m evaluation.retrieval_quality --modes lexical --output /tmp/trace-retrieval-current.json
uv run --locked python -m evaluation.retrieval_quality --rescore /tmp/trace-retrieval-current.json
```

Fresh source manifests include nested application modules. The remaining historical evidence descriptions below refer to their recorded implementation; they do not instruct current code to accept an incompatible scorer snapshot.

`ground_truth/` contains evaluator-only manifests. It is outside the installable runtime package. Never mount, index, retrieve, prompt with or export this directory through investigator interfaces. See the [development catalog and isolation boundary](../docs/architecture/development-scenarios.md).

The `mvp-suite.v1` manifest records four development cases at seed 17. Related seed, capture-gap, distractor and original `payment-dependency.v1` variants form one `order-payment-timeout-v1` group. Keep the entire group in development. Validation and final-test allocations/answers remain reserved and ungenerated; independent grouping and cohort allocation must precede later acceptance/final study. Opaque case/evidence IDs are bookkeeping, not legitimate diagnostic features.

A future authorized historical-replay cohort requires a named data-access owner, independent permission, sanitization/versioning and separate operational-pilot reporting. Access is currently blocked. Never mix that cohort into held-out capstone data or claim synthetic replay establishes operational usefulness.

The [development evaluation contract](../docs/architecture/development-evaluation.md) defines the candidate schema, deterministic scoring, citation-support rubric, saved run format and baseline comparison protocol. `fixtures/` contains hand-authored candidate outputs and fixture expectations, also evaluator-only. Run `uv run --locked python -m evaluation.runner run --output /tmp/trace-s3-evaluation` from the repository root with a fresh output path, then `rescore --run-dir /tmp/trace-s3-evaluation` to verify saved inputs and reproduce scores. These scores demonstrate plumbing, not model quality; model usage and actual human/operator review remain unavailable.

`retrieval/queries_v1.json` and `reports/retrieval_development_v1.json` are evaluator-only development ranking material, also excluded from ingestion/runtime interfaces. `uv run --locked --extra semantic python -m evaluation.retrieval_baseline --output /tmp/trace-retrieval-review.json` compares the three adapted modes using the real cached CPU model. `--rescore evaluation/reports/retrieval_development_v1.json` recomputes hash-verified saved metrics without loading a model. Document judgments, absent-knowledge results, failure denominators and limits are described in the [search contract](../docs/architecture/knowledge-retrieval.md). The [passage/context contract](../docs/architecture/retrieval-evaluation-context.md) extends evaluation in #17.

`retrieval/queries_v4.json`, `acceptance_v3.json`, `reviews_v4.json`, `review_bundle_v4.md` and passage reports are evaluator-only. The 100 requests span 15 related development families; 211 human relevance/claim decisions record the owner’s blanket endorsement, with shared provenance and no fabricated per-target notes. Owner thresholds are frozen before measurements. `python -m evaluation.retrieval_quality` compares exact passage ranks independently of model answers; `--modes lexical` needs no encoder, and `--rescore PATH` verifies saved inputs without a model. `--acceptance --output NEW_PATH` blocks before execution until actual human review is complete. The two passage reports compare a per-document cap of 1 and 20 with the same candidate pool; neither is an acceptance run. The separate [lexical acceptance report](reports/retrieval_passage_acceptance_v4.json) snapshots the later human endorsement and passes the frozen thresholds with all 100 queries and six freshness exclusions. Never ingest these artifacts or treat their probe claims as operational evidence.

The [AI findings and revision record](retrieval/judgment-revisions.md) corrects review provenance and preserves the earlier proposals with their exact scorer checkouts. Default commands now use v4 eligible-passage gold and question-specific probes, with separate observed freshness-policy exclusion checks. Protocol v3 changes only the suite binding; owner thresholds remain unchanged. AI findings are separate from the later actual human blanket endorsement, which is recorded in `reviews_v4.json`; v2/v3 review files remain empty.

`fixtures/tool_choices_v1.json` contains evaluator-only agent-authored development expectations for independent tool choice/arguments: 18 cases and 21 examples. `uv run --locked python -m evaluation.tool_evaluation --output NEW_PATH` executes the declared API examples with scoped local fixtures; `--rescore reports/tool_choices_development_v1.json` verifies saved input hashes/schedule/results without a model. Choice correctness against exact declared alternatives is separate from legal API execution; model-selected choice evaluation is **not run**. The [S4 runtime package](reports/sprint_04_evidence_package_v1.json) contains source observations/context without these labels; [integration contract](../docs/architecture/scripted-evidence-package.md) documents its deterministic source hash, actual variable audit, limitations and reproduction. Keep cases in development, preserve historical report checkouts and refine/version semantic alternatives before later model evaluation.
