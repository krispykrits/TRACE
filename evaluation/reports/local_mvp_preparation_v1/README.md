# Local MVP protocol preparation evidence

The [manifest](manifest.json) is a dry run of the [#63 planner](../../../docs/planning/local-mvp-acceptance.md) at implementation commit `073b89a7104bf661e9e3739d3ba7b6e0486c36b3`. It binds the adjacent exact [protocol](protocol.json) and [pending decisions](decisions.json), plus 100 implementation/development-source hashes.

The command exited 1 as specified: 45 owner inputs remain unresolved, projected cost and measured usage are null, actual provider calls are zero, and Local MVP release is not assessed. The twelve case/arm combinations are a schedule template; repeats and an executable acceptance schedule are not selected. No review, source permission, spending approval or provider configuration is inferred. No final-test data was generated or accessed.

For exact reproduction, choose unused paths and the recorded checkout:

~~~sh
git worktree add --detach /tmp/trace-local-mvp-preparation 073b89a7104bf661e9e3739d3ba7b6e0486c36b3
cd /tmp/trace-local-mvp-preparation
uv run --locked python -m evaluation.local_mvp --output /tmp/trace-local-mvp-plan-reproduced
~~~

Exit 1 is the expected blocked-preflight outcome. Its `manifest.json` regenerates byte for byte with the listed source bytes. A current-source plan uses a new directory and retains its own hashes. This record supplies no acceptance result; owner decisions and #64–#68 evidence remain pending.
