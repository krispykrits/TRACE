# Local MVP owner-settings dry run v2

The [manifest](manifest.json) records the [owner decision](../../../docs/planning/local-mvp-owner-decisions-2026-10-16.md) at implementation commit `cd3f9b00de479f324e2d9be7f4affe46ef312d1b`. Adjacent [protocol](protocol.json) and [decisions](decisions.json) preserve exact v2 input bytes; the manifest binds 101 source hashes.

The plan declares 36 attempts, 24 model investigations and a $0.405504 reservation ceiling under the frozen rates. All 12 integrated reports and every emitted claim are assigned to `krispykrits` as sole reviewer. Actual review decisions and provider calls are both zero; no second reviewer or inter-rater agreement is claimed. The final-study independence requirement remains separate.

Exit 1 is expected: 19 factual/authority/freeze fields remain missing, including current provider/spending/source/live-run details, cleanup owner and final approval bindings. The owner's accepted $1 planning allowance does not supply those facts. No measurement, verdict or release acceptance is inferred. The [original v1 draft](../local_mvp_preparation_v1/README.md) remains unchanged at its own recorded checkout.

For exact reproduction, use unused paths:

~~~sh
git worktree add --detach /tmp/trace-local-mvp-owner-plan cd3f9b00de479f324e2d9be7f4affe46ef312d1b
cd /tmp/trace-local-mvp-owner-plan
uv run --locked python -m evaluation.local_mvp --output /tmp/trace-local-mvp-owner-plan-reproduced
~~~

The saved `manifest.json` regenerates byte for byte with the recorded source bytes. Current-source exploration uses a fresh output directory and retains its own hashes. This is offline planning evidence, not an acceptance run or human-review result.
