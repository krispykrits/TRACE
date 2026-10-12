# Evaluation material

`ground_truth/` contains evaluator-only manifests. It is outside the installable runtime package. Never mount, index, retrieve, prompt with or export this directory through investigator interfaces. See the [development catalog and isolation boundary](../docs/architecture/development-scenarios.md).

The `mvp-suite.v1` manifest records four development cases at seed 17. Related seed, capture-gap, distractor and original `payment-dependency.v1` variants form one `order-payment-timeout-v1` group. Keep the entire group in development. Validation and final-test allocations/answers remain reserved and ungenerated; independent grouping and cohort allocation must precede later acceptance/final study. Opaque case/evidence IDs are bookkeeping, not legitimate diagnostic features.

A future authorized historical-replay cohort requires a named data-access owner, independent permission, sanitization/versioning and separate operational-pilot reporting. Access is currently blocked. Never mix that cohort into held-out capstone data or claim synthetic replay establishes operational usefulness.

The [development evaluation contract](../docs/architecture/development-evaluation.md) defines the candidate schema, deterministic scoring, citation-support rubric, saved run format and baseline comparison protocol. `fixtures/` contains hand-authored candidate outputs and fixture expectations, also evaluator-only. Run `uv run --locked python -m evaluation.runner run --output /tmp/trace-s3-evaluation` from the repository root with a fresh output path, then `rescore --run-dir /tmp/trace-s3-evaluation` to verify saved inputs and reproduce scores. These scores demonstrate plumbing, not model quality; model usage and actual human/operator review remain unavailable.
