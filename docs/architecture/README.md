# TRACE architecture view

Status: Sprint 3 SQLite persistence proposal, 2026-10-05. This view describes implemented code and approved direction; it does not claim an incident investigation is implemented.

```mermaid
flowchart LR
    User[Engineer] --> CLI[trace-app CLI]
    CLI --> Config[Configuration loader]
    CLI --> Log[JSON logging and redaction]
    CLI --> Demo[OrderWorkflow demo]
    CLI --> Replay[Seeded dependency replay]
    Replay --> Demo
    Replay --> Evidence[Synthetic evidence bundle]
    Evidence --> Store[SQLite snapshot and job state]
    Demo --> Customer[Customer fixture]
    Demo --> Payment[Payment fixture]
    Demo --> Notification[Notification fixture]
    Log -. planned EC2 collection .-> CW[CloudWatch Logs]
    CLI -. later S3-S6 .-> Investigation[Read-only investigation]
    Investigation -. later source adapters .-> Sources[Authorized evidence sources]
    Investigation -. later report .-> User
    Approved[Exact action approval] -. final capstone only .-> Executor[Separate deterministic remediation executor]
```

Solid arrows are implemented local behavior. Dotted arrows are planned boundaries or deployment work. [ADR 0001](../adr/0001-repository-runtime-and-local-tooling.md) selects one modular Python application; the current `src/trace_app` package contains CLI, configuration, structured logging and the synthetic Order workflow, dependency replay and SQLite snapshot/job-state adapter with in-process fixtures. [ADR 0002](../adr/0002-terraform-and-ec2-cloud-deployment.md) selects Terraform/EC2 for the Cloud MVP, and [ADR 0003](../adr/0003-cloudwatch-hosted-logging.md) selects hosted logging, but no EC2 runtime or hosted delivery is verified. No investigator, real source adapter, model, HTTP API or remediation executor exists yet. The SQLite adapter persists local synthetic snapshots and execution state; it is not a real-source integration. [ADR 0004](../adr/0004-synchronous-synthetic-order-workflow.md) records the synchronous demo boundary.

The Local/Cloud MVP investigation remains read-only. The final capstone's [approved production remediation scope](../planning/production-remediation-scope.md) requires a separate deterministic executor with proposal-bound approval, state revalidation, bounded execution and outcome verification. A source filter or investigation access cannot grant mutation authority.

- [Order–Payment workflow](order-payment-workflow.md) shows the implemented request path and fixture limits.
- [Evidence and data contracts](data-contracts.md) distinguish settings, logs, workflow records and incident evidence.
- [Dependency replay contract](dependency-replay-evidence.md) defines the version 1 envelope, replay rules and evaluator separation.
- [SQLite investigation store](sqlite-investigation-store.md) defines persistence, retry/recovery, access and deletion rules.
- [Interfaces and API contracts](interfaces.md) describe the current CLI and the deferred application/source APIs.
- [Development guide](../development.md) gives runnable local commands and the current quality gate.
- [Reuse review](../planning/production-usefulness-review.md) and [approved amendment](../planning/production-roadmap-amendment.md) explain why educational components must enter through TRACE-owned contracts.
