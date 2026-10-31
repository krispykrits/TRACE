# TRACE document and evaluation migration inventory

Status: **working inventory**, baseline tracked files at `7568d22ef2c0825c78967585e59aa26c2af608cb` plus proposed handoff documents in PR #99. Coordinates [#55](https://github.com/krispykrits/TRACE/issues/55) and [#89](https://github.com/krispykrits/TRACE/issues/89); no file has been copied or moved. This is a conservative proposed placement, not a classification or deletion authorization. Confirm actual sensitivity, owner, permitted use, individual retention, adviser access, and external destination before any move; approximate 14-day owner preference is not an approved universal deletion period.

This lists tracked documents and non-report corpus/evaluation files individually. Each report directory is listed as a bundle; its manifest, where present, enumerates individual artifact names and hashes. Standalone report files are listed individually. The owning source repository retains documents needed to build, run, test and maintain that component. OneDrive is a proposed destination for detailed working or academic content, not a replacement for recorded decisions or evaluation manifests until links, bytes and reproduction are verified. Private Blob is planned under [#98](https://github.com/krispykrits/TRACE/issues/98); it is not yet a verified destination. All rows retain their existing bytes and retention pending review.

| Tracked path or report bundle | Purpose / reader | Candidate canonical home | Migration condition |
| --- | --- | --- | --- |
| `corpus/README.md` | Retrieval input / developer | TRACE development corpus | Preserve exact input bytes and hashes |
| `corpus/development/documents/history-certificate.md` | Retrieval input / developer | TRACE development corpus | Preserve exact input bytes and hashes |
| `corpus/development/documents/history-queue.md` | Retrieval input / developer | TRACE development corpus | Preserve exact input bytes and hashes |
| `corpus/development/documents/order-interface.md` | Retrieval input / developer | TRACE development corpus | Preserve exact input bytes and hashes |
| `corpus/development/documents/payment-interface.md` | Retrieval input / developer | TRACE development corpus | Preserve exact input bytes and hashes |
| `corpus/development/documents/source-freshness.md` | Retrieval input / developer | TRACE development corpus | Preserve exact input bytes and hashes |
| `corpus/development/documents/timeout-evidence.md` | Retrieval input / developer | TRACE development corpus | Preserve exact input bytes and hashes |
| `corpus/development/manifest.json` | Retrieval input / developer | TRACE development corpus | Preserve exact input bytes and hashes |
| `docs/README.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/adr/0001-repository-runtime-and-local-tooling.md` | Decision / engineer | TRACE | Retain decision history |
| `docs/adr/0002-terraform-and-ec2-cloud-deployment.md` | Decision / engineer | TRACE | Retain decision history |
| `docs/adr/0003-cloudwatch-hosted-logging.md` | Decision / engineer | TRACE | Retain decision history |
| `docs/adr/0004-synchronous-synthetic-order-workflow.md` | Decision / engineer | TRACE | Retain decision history |
| `docs/adr/0005-sqlite-local-postgresql-rds-cloud.md` | Decision / engineer | TRACE | Retain decision history |
| `docs/adr/0006-pgvector-cloud-retrieval-storage.md` | Decision / engineer | TRACE | Retain decision history |
| `docs/adr/0007-synthetic-evidence-identity-and-isolation.md` | Decision / engineer | TRACE | Retain decision history |
| `docs/adr/0008-local-corpus-generations-and-source-policy.md` | Decision / engineer | TRACE | Retain decision history |
| `docs/adr/0009-local-exact-knowledge-retrieval.md` | Decision / engineer | TRACE | Retain decision history |
| `docs/adr/0010-capability-packages-and-adapter-boundaries.md` | Decision / engineer | TRACE | Retain decision history |
| `docs/adr/0011-read-only-tool-execution.md` | Decision / engineer | TRACE | Retain decision history |
| `docs/adr/0012-model-provider-contract-and-bounded-call.md` | Decision / engineer | TRACE | Retain decision history |
| `docs/adr/0013-assessment-validation-and-support-review.md` | Decision / engineer | TRACE | Retain decision history |
| `docs/adr/0014-durable-investigation-budgets.md` | Decision / engineer | TRACE | Retain decision history |
| `docs/adr/0015-azure-aks-cloud-deployment.md` | Decision / engineer | TRACE | Retain decision history |
| `docs/adr/0016-bounded-investigation-and-private-publication.md` | Decision / engineer | TRACE | Retain decision history |
| `docs/adr/0017-dotnet-testbed-and-json-first-evidence.md` | Decision / engineer | TRACE | Retain decision history |
| `docs/adr/0018-flexible-ml-and-ranked-response-options.md` | Decision / engineer | TRACE | Retain decision history |
| `docs/adr/0019-local-cli-and-saved-report-access.md` | Decision / engineer | TRACE | Retain decision history |
| `docs/adr/0020-investigator-evaluation-and-artifact-isolation.md` | Decision / engineer | TRACE | Retain decision history |
| `docs/adr/0021-interactive-platform-and-repository-boundaries.md` | Decision / engineer | TRACE | Retain decision history |
| `docs/adr/0022-sprint-06-readiness-and-sprint-07-diagnostics.md` | Decision / engineer | TRACE | Retain decision history |
| `docs/adr/README.md` | Decision / engineer | TRACE | Retain decision history |
| `docs/adr/template.md` | Decision / engineer | TRACE | Retain decision history |
| `docs/architecture/README.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/architecture/azure-cloud.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/architecture/bounded-evidence-queries.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/architecture/bounded-investigator.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/architecture/data-contracts.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/architecture/dependency-replay-evidence.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/architecture/development-evaluation.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/architecture/development-scenarios.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/architecture/incident-timelines.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/architecture/investigation-budgets.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/architecture/investigation-tools.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/architecture/investigator-cli.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/architecture/investigator-evaluation.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/architecture/knowledge-corpus.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/architecture/knowledge-retrieval.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/architecture/model-provider.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/architecture/order-payment-workflow.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/architecture/package-layout.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/architecture/retrieval-evaluation-context.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/architecture/s7-implementation-contract.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/architecture/s7-platform-design.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/architecture/scripted-evidence-package.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/architecture/sqlite-investigation-store.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/architecture/validated-assessments.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/archive/2026-09-23-reuse-review.md` | Historical context / maintainer | TRACE archive | Retain until links and history verified |
| `docs/archive/README.md` | Historical context / maintainer | TRACE archive | Retain until links and history verified |
| `docs/archive/cloudwatch-preparation.md` | Historical context / maintainer | TRACE archive | Retain until links and history verified |
| `docs/charter.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/current-status.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/development.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/operations/README.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/operations/local-readiness.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/operations/local-recovery.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/planning/azure-cloud-backlog.md` | Plan and gates / owner | TRACE + OneDrive candidate | Preserve decisions and issue links; review individually |
| `docs/planning/azure-cost-scenario-s7.md` | Plan and gates / owner | TRACE + OneDrive candidate | Preserve decisions and issue links; review individually |
| `docs/planning/capstone-project-plan.md` | Plan and gates / owner | TRACE + OneDrive candidate | Preserve decisions and issue links; review individually |
| `docs/planning/dotnet-testbed-backlog.md` | Plan and gates / owner | TRACE + OneDrive candidate | Preserve decisions and issue links; review individually |
| `docs/planning/local-mvp-acceptance.md` | Plan and gates / owner | TRACE + OneDrive candidate | Preserve decisions and issue links; review individually |
| `docs/planning/local-mvp-owner-decisions-2026-10-16.md` | Plan and gates / owner | TRACE + OneDrive candidate | Preserve decisions and issue links; review individually |
| `docs/planning/local-mvp-tool-budget-adjustment-2026-10-16.md` | Plan and gates / owner | TRACE + OneDrive candidate | Preserve decisions and issue links; review individually |
| `docs/planning/production-remediation-scope.md` | Plan and gates / owner | TRACE + OneDrive candidate | Preserve decisions and issue links; review individually |
| `docs/planning/s7-azure-deployment-candidate.md` | Plan and gates / owner | TRACE + OneDrive candidate | Preserve decisions and issue links; review individually |
| `docs/planning/s7-implementation-handoff.md` | Plan and gates / owner | TRACE + OneDrive candidate | Preserve decisions and issue links; review individually |
| `docs/planning/s7-repository-and-evidence-inventory.md` | Plan and gates / owner | TRACE + OneDrive candidate | Preserve decisions and issue links; review individually |
| `docs/security/README.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/security/local-mvp-matrix.md` | Product or operations / contributor | TRACE | Keep with owning component; review links before extraction |
| `docs/sprints/sprint-01-review.md` | Sprint evidence / reviewer | TRACE + OneDrive candidate | Preserve history; verify copy before any move |
| `docs/sprints/sprint-04-review.md` | Sprint evidence / reviewer | TRACE + OneDrive candidate | Preserve history; verify copy before any move |
| `docs/sprints/sprint-05-review.md` | Sprint evidence / reviewer | TRACE + OneDrive candidate | Preserve history; verify copy before any move |
| `docs/sprints/sprint-06-review.md` | Sprint evidence / reviewer | TRACE + OneDrive candidate | Preserve history; verify copy before any move |
| `docs/sprints/sprint-review-template.md` | Sprint evidence / reviewer | TRACE + OneDrive candidate | Preserve history; verify copy before any move |
| `evaluation/README.md` | Evaluation tools / evaluator | TRACE evaluator area | Preserve frozen versions and no-call reproduction |
| `evaluation/__init__.py` | Evaluation tools / evaluator | TRACE evaluator area | Preserve frozen versions and no-call reproduction |
| `evaluation/fixtures/candidates_v1.json` | Scoring input / evaluator | TRACE evaluator area or restricted store | Keep outside runtime; verify split and access before migration |
| `evaluation/fixtures/tool_choices_v1.json` | Scoring input / evaluator | TRACE evaluator area or restricted store | Keep outside runtime; verify split and access before migration |
| `evaluation/ground_truth/mvp_suite_v1.json` | Scoring input / evaluator | TRACE evaluator area or restricted store | Keep outside runtime; verify split and access before migration |
| `evaluation/ground_truth/payment_dependency_v1.json` | Scoring input / evaluator | TRACE evaluator area or restricted store | Keep outside runtime; verify split and access before migration |
| `evaluation/investigator.py` | Evaluation tools / evaluator | TRACE evaluator area | Preserve frozen versions and no-call reproduction |
| `evaluation/investigator_protocol_v1.json` | Evaluation tools / evaluator | TRACE evaluator area | Preserve frozen versions and no-call reproduction |
| `evaluation/investigator_scoring.py` | Evaluation tools / evaluator | TRACE evaluator area | Preserve frozen versions and no-call reproduction |
| `evaluation/local_mvp.py` | Evaluation tools / evaluator | TRACE evaluator area | Preserve frozen versions and no-call reproduction |
| `evaluation/local_mvp_comparison.py` | Evaluation tools / evaluator | TRACE evaluator area | Preserve frozen versions and no-call reproduction |
| `evaluation/local_mvp_decisions_v1.json` | Evaluation tools / evaluator | TRACE evaluator area | Preserve frozen versions and no-call reproduction |
| `evaluation/local_mvp_decisions_v2.json` | Evaluation tools / evaluator | TRACE evaluator area | Preserve frozen versions and no-call reproduction |
| `evaluation/local_mvp_decisions_v3.json` | Evaluation tools / evaluator | TRACE evaluator area | Preserve frozen versions and no-call reproduction |
| `evaluation/local_mvp_protocol_v1.json` | Evaluation tools / evaluator | TRACE evaluator area | Preserve frozen versions and no-call reproduction |
| `evaluation/local_mvp_protocol_v2.json` | Evaluation tools / evaluator | TRACE evaluator area | Preserve frozen versions and no-call reproduction |
| `evaluation/retrieval/acceptance_v1.json` | Scoring input / evaluator | TRACE evaluator area or restricted store | Keep outside runtime; verify split and access before migration |
| `evaluation/retrieval/acceptance_v2.json` | Scoring input / evaluator | TRACE evaluator area or restricted store | Keep outside runtime; verify split and access before migration |
| `evaluation/retrieval/acceptance_v3.json` | Scoring input / evaluator | TRACE evaluator area or restricted store | Keep outside runtime; verify split and access before migration |
| `evaluation/retrieval/judgment-revisions.md` | Scoring input / evaluator | TRACE evaluator area or restricted store | Keep outside runtime; verify split and access before migration |
| `evaluation/retrieval/queries_v1.json` | Scoring input / evaluator | TRACE evaluator area or restricted store | Keep outside runtime; verify split and access before migration |
| `evaluation/retrieval/queries_v2.json` | Scoring input / evaluator | TRACE evaluator area or restricted store | Keep outside runtime; verify split and access before migration |
| `evaluation/retrieval/queries_v3.json` | Scoring input / evaluator | TRACE evaluator area or restricted store | Keep outside runtime; verify split and access before migration |
| `evaluation/retrieval/queries_v4.json` | Scoring input / evaluator | TRACE evaluator area or restricted store | Keep outside runtime; verify split and access before migration |
| `evaluation/retrieval/review_bundle_v2.md` | Scoring input / evaluator | TRACE evaluator area or restricted store | Keep outside runtime; verify split and access before migration |
| `evaluation/retrieval/review_bundle_v3.md` | Scoring input / evaluator | TRACE evaluator area or restricted store | Keep outside runtime; verify split and access before migration |
| `evaluation/retrieval/review_bundle_v4.md` | Scoring input / evaluator | TRACE evaluator area or restricted store | Keep outside runtime; verify split and access before migration |
| `evaluation/retrieval/reviews_v2.json` | Scoring input / evaluator | TRACE evaluator area or restricted store | Keep outside runtime; verify split and access before migration |
| `evaluation/retrieval/reviews_v3.json` | Scoring input / evaluator | TRACE evaluator area or restricted store | Keep outside runtime; verify split and access before migration |
| `evaluation/retrieval/reviews_v4.json` | Scoring input / evaluator | TRACE evaluator area or restricted store | Keep outside runtime; verify split and access before migration |
| `evaluation/retrieval_baseline.py` | Evaluation tools / evaluator | TRACE evaluator area | Preserve frozen versions and no-call reproduction |
| `evaluation/retrieval_quality.py` | Evaluation tools / evaluator | TRACE evaluator area | Preserve frozen versions and no-call reproduction |
| `evaluation/runner.py` | Evaluation tools / evaluator | TRACE evaluator area | Preserve frozen versions and no-call reproduction |
| `evaluation/scoring.py` | Evaluation tools / evaluator | TRACE evaluator area | Preserve frozen versions and no-call reproduction |
| `evaluation/tool_evaluation.py` | Evaluation tools / evaluator | TRACE evaluator area | Preserve frozen versions and no-call reproduction |
| `evaluation/reports/investigation_tools_demo_v1.json` | Recorded evidence / evaluator | TRACE until verified private artifact storage | Retain exact bytes, manifest and source checkout; no deletion |
| `evaluation/reports/investigator_offline_v1` | Recorded evidence / evaluator | TRACE until verified private artifact storage | Retain exact bytes, manifest and source checkout; no deletion |
| `evaluation/reports/investigator_offline_v1_human_review_v1` | Recorded evidence / evaluator | TRACE until verified private artifact storage | Retain exact bytes, manifest and source checkout; no deletion |
| `evaluation/reports/local_mvp_comparison_offline_v3` | Recorded evidence / evaluator | TRACE until verified private artifact storage | Retain exact bytes, manifest and source checkout; no deletion |
| `evaluation/reports/local_mvp_owner_plan_v2` | Recorded evidence / evaluator | TRACE until verified private artifact storage | Retain exact bytes, manifest and source checkout; no deletion |
| `evaluation/reports/local_mvp_preparation_v1` | Recorded evidence / evaluator | TRACE until verified private artifact storage | Retain exact bytes, manifest and source checkout; no deletion |
| `evaluation/reports/local_mvp_tool_capacity_probe_v1` | Recorded evidence / evaluator | TRACE until verified private artifact storage | Retain exact bytes, manifest and source checkout; no deletion |
| `evaluation/reports/local_recovery_v1` | Recorded evidence / evaluator | TRACE until verified private artifact storage | Retain exact bytes, manifest and source checkout; no deletion |
| `evaluation/reports/local_security_v1` | Recorded evidence / evaluator | TRACE until verified private artifact storage | Retain exact bytes, manifest and source checkout; no deletion |
| `evaluation/reports/retrieval_development_v1.json` | Recorded evidence / evaluator | TRACE until verified private artifact storage | Retain exact bytes, manifest and source checkout; no deletion |
| `evaluation/reports/retrieval_passage_acceptance_v4.json` | Recorded evidence / evaluator | TRACE until verified private artifact storage | Retain exact bytes, manifest and source checkout; no deletion |
| `evaluation/reports/retrieval_passage_baseline_v2.json` | Recorded evidence / evaluator | TRACE until verified private artifact storage | Retain exact bytes, manifest and source checkout; no deletion |
| `evaluation/reports/retrieval_passage_baseline_v3.json` | Recorded evidence / evaluator | TRACE until verified private artifact storage | Retain exact bytes, manifest and source checkout; no deletion |
| `evaluation/reports/retrieval_passage_baseline_v4.json` | Recorded evidence / evaluator | TRACE until verified private artifact storage | Retain exact bytes, manifest and source checkout; no deletion |
| `evaluation/reports/retrieval_passage_candidates_v2.json` | Recorded evidence / evaluator | TRACE until verified private artifact storage | Retain exact bytes, manifest and source checkout; no deletion |
| `evaluation/reports/retrieval_passage_candidates_v3.json` | Recorded evidence / evaluator | TRACE until verified private artifact storage | Retain exact bytes, manifest and source checkout; no deletion |
| `evaluation/reports/retrieval_passage_candidates_v4.json` | Recorded evidence / evaluator | TRACE until verified private artifact storage | Retain exact bytes, manifest and source checkout; no deletion |
| `evaluation/reports/sprint_04_evidence_package_v1.json` | Recorded evidence / evaluator | TRACE until verified private artifact storage | Retain exact bytes, manifest and source checkout; no deletion |
| `evaluation/reports/tool_choices_development_v1.json` | Recorded evidence / evaluator | TRACE until verified private artifact storage | Retain exact bytes, manifest and source checkout; no deletion |
