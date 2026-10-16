# Proposed Local MVP tool-budget adjustment — 2026-10-16

Status: **proposal pending owner decision**, for [#64 / PR #86](https://github.com/krispykrits/TRACE/pull/86). The active [v2 decisions](../../evaluation/local_mvp_decisions_v2.json) still specify 20 calls. This record does not approve a new limit, relax a quality threshold, authorize paid calls or revise original failed evidence.

The 20-call recommendation was below the measured mandatory workflow cost. [Four offline capacity probes](../../evaluation/reports/local_mvp_tool_capacity_probe_v1/summary.json) used an explicit diagnostic ceiling of 100 solely to count completion reads with no manufactured runtime support decisions. All four completed as `review_required`: c01/c02 each used 30 tool calls; c03/c04 each used 23. Each used one scripted model call. Actual provider calls and human judgments were zero. Exact observed/result/execution/source bytes, diagnostic policy, source inventory and hashes are retained in the adjacent manifest at checkout `e0698ef97aee8019969243c4abe4271e65da807b`. These one-off probes are not the declared repeated comparison or acceptance evidence.

For c01/c02, 18 calls gather and resolve evidence, and 12 fresh citation-resolution reads check validation and publication. Checks around review/publication protect against changed sources, stale citations and revoked access. They must not be cached across those boundaries or removed merely to make the 20-call setting pass. Reducing retrieved evidence/context just to fit that setting would also change the declared comparison.

## Recommended revision

Raise the per-attempt tool ceiling from **20 to 40** for the currently declared Local MVP comparison. Forty allows the observed maximum of 30 plus 10 calls of headroom. This is scoped to this workflow/cohort/options, not a claim that every future refinement/correction or previously endorsed runtime publication fits 40.

Keep the 120-second deadline, serial schedule, three model-call ceiling, token bounds, zero automatic paid retries, $1 scope allowance, $20 monthly application cap, quality thresholds and sole-owner review unchanged. Raising this read-only tool ceiling does not raise the model reservation estimate of $0.405504; actual latency/source access and monthly spending still require verification. The independent live-executor, provider/source/transmission/spending/approval gates remain unresolved.

If the owner adopts this proposal, publish a new decision revision with explicit provenance, bind it and the implementation/source snapshot into a fresh plan, and rerun all 36 scheduled offline attempts with saved rescoring. Preserve the original 0/12 integrated-completion report unchanged and report any subsequent quality/support failures. Completing a scripted proposal only removes the tool-budget blocker; it cannot accept diagnostic quality, human support or the release.
