# Local readiness and handoff

This guide supports [#68](https://github.com/krispykrits/TRACE/issues/68). It describes the local synthetic demonstration and the information needed for the owner's Sprint 6 handoff. The [Sprint 6 review](../sprints/sprint-06-review.md) records the actual run and outstanding evidence. Local readiness does not establish real-model quality or authorize Azure calls.

## Setup and offline comparison

Use Linux, Python 3.12 and the exact `uv` version specified in `pyproject.toml`. From a clean checkout, follow [development setup](../development.md#setup-and-first-run). Record the checkout, platform, Python and `uv` versions, lock hash, commands and outcomes in the review. Use new private paths for each run; the comparison refuses an existing output directory.

```sh
uv sync --locked
uv run --locked python -m evaluation.local_mvp_comparison run --output /tmp/trace-local-readiness-comparison
uv run --locked python -m evaluation.local_mvp_comparison rescore --run-dir /tmp/trace-local-readiness-comparison > /tmp/trace-local-readiness-rescore.json
cmp /tmp/trace-local-readiness-comparison/scores.json /tmp/trace-local-readiness-rescore.json
make check lint format-check type-check architecture-check test integration package-check
```

Rescore from the same implementation and bound inputs; later code changes require the recorded checkout. The comparison uses a hand-authored model and synthetic capture. The complete manifest is written last; preserve incomplete, failed, cancelled, missing and review-required outcomes rather than counting them as successful runs. Actual provider use and human judgments are not produced by this command. The report includes evaluator-only ground truth: keep the run directory private and outside the runtime or retrieval inputs. `package-check` installs the wheel in a separate temporary environment and exercises its entry points, synthetic workflow and evaluator exclusion; it does not by itself demonstrate an installed-wheel investigation and protected review workflow.

## Inspect a synthetic investigation

The fixture below creates a private local profile, evidence store and index with a fixed clock and a scripted provider. It uses no credentials. It exits 7 when its candidate is awaiting support review. Its profile and grants are fictional, and the script is outside the installed wheel.

```sh
uv run --locked python -m scripts.investigator_fixture --directory /tmp/trace-local-readiness-pending --unreviewed
```

Copy the investigation ID and an admitted citation ID from the output. Then inspect the saved result and a citation using the same fixture directory:

```sh
uv run --locked python -m scripts.investigator_fixture --directory /tmp/trace-local-readiness-pending -- report --investigation-id <investigation-id>
uv run --locked python -m scripts.investigator_fixture --directory /tmp/trace-local-readiness-pending -- report --investigation-id <investigation-id> --citation-id <citation-id> --format json
uv run --locked python -m scripts.investigator_fixture --directory /tmp/trace-local-readiness-pending -- report --investigation-id <investigation-id> --format json --output /tmp/trace-local-readiness-report.json
```

Saved inspection applies current source and support checks. JSON output is an export and requires the separate transmission and source-owner checks. A denied source or withdrawn support blocks disclosure; a citation ID grants no access. The pending result is not a supported assessment. See the [CLI contract](../architecture/investigator-cli.md#output-and-disclosure) for status, exit codes, sensitivity, cancellation and no-overwrite behavior.

## Owner walkthrough and handoff

The owner must actually walk through the protected review packet, its bound claim and citation, a decision and a revision, with the identity and any assistance recorded. Do not create verdicts on the owner's behalf. The [review rubric and bound review file](../architecture/investigator-evaluation.md#support-sample-and-independent-review) explain the separate evaluation workflow; pending runtime reports are not automatically promoted by evaluator decisions. Use synthetic material for this readiness walkthrough, and keep original decisions and any revisions distinct. The walkthrough is a usability and mechanics check, not acceptance of actual Azure diagnostic quality.

The owner reviews the [Sprint 6 evidence and outstanding gates](../sprints/sprint-06-review.md), then records an explicit local-readiness/handoff decision. A missing walkthrough, incomplete installed-wheel demonstration, failed critical check or unreviewed decision remains open; green tests alone do not close #68.

## Recovery and S7 handoff

Follow [local recovery](local-recovery.md) for stop, quiescent backup/restore, duplicate or uncertain attempts, journal freshness and retention. An unknown remote outcome must be reconciled before a separately approved retry. Cancellation does not prove a provider stopped or incurred no charge. A 30-day expectation applies to new private working copies; cleanup ownership and deletion of all copies need explicit assignment. Do not delete frozen evidence or assume a backup was erased.

Before any S7 actual-provider dispatch, record and verify the actual provider/deployment/model/API and arm configuration; source and transmission rights and retention; current spending and unresolved reservations in the shared journal; cleanup owner, stop contact, scope and final owner approval bound to the applicable protocol and source bytes. Unknown facts block dispatch. The planning allowance is not approval to spend. #87 produces actual comparison evidence and #65 owns the subsequent owner quality review and diagnostic decision. Azure/AKS hosting, operational source access and remediation remain separate gates.
