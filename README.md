# TRACE

Telemetry & Root-Cause Analysis Copilot for Engineers — an Applied AI Engineering capstone focused on evidence-supported incident diagnosis.

## Project organization

- [TRACE Project](https://github.com/users/krispykrits/projects/2) — status and release grouping
- [Sprint milestones](https://github.com/krispykrits/TRACE/milestones) — all 18 planned increments

Individual issues are stories/tasks; milestones are sprints. Project Status is the authoritative work status. Future milestones remain undated pending capacity planning.

## Delivery roadmap

| Release | Provisional sprints | Outcome |
| --- | --- | --- |
| Local MVP | 1–6 | Order → Payment incidents, small retrieval corpus, bounded read-only tools, cited diagnosis, abstention, timeline and automated scoring |
| Cloud MVP | 7–9 | The same workflow on AWS with repeatable deployment, access controls, observability, cost limits and teardown |
| Full capstone | 10–18 | Broader scenarios, evaluated ML, five-arm study, production hardening and final defense |

- [Complete project plan and release gates](docs/planning/capstone-project-plan.md)
- [Approved production-usefulness amendment](docs/planning/production-roadmap-amendment.md)
- [Implementation reuse review](docs/planning/production-usefulness-review.md)
- [MVP-first delivery tracker](https://github.com/krispykrits/TRACE/issues/9)
- [Charter and minimum decisions](https://github.com/krispykrits/TRACE/issues/1)
- [Backlog](https://github.com/krispykrits/TRACE/issues)

Customer and Notification begin as lightweight fixtures. The first investigator is evaluated before expanding ML or infrastructure. ML and the full five-configuration comparison remain final capstone requirements.

Sprint numbers are provisional scope increments, not calendar commitments. Dates, capacity, budget and technology decisions remain explicit charter/ADR work. This repository contains project planning artifacts, a Python CLI and a synthetic Order–Payment workflow.

## Local development

See [the development guide](docs/development.md) for the Python 3.12/uv setup, safe local environment example, configuration precedence and structured logging conventions. The [synthetic Order–Payment workflow](docs/architecture/order-payment-workflow.md) has a runnable CLI request and explicit fixture limits. The [architecture view](docs/architecture/README.md), [ADR index](docs/adr/README.md), [infrastructure responsibilities](deploy/README.md) and [Sprint 1 evidence review](docs/sprints/sprint-01-review.md) describe current boundaries and open gates.

## Production usefulness

The September 23 amendment is owner-approved. An independent Operational Pilot gate requires authorized historical replay and read-only shadow use, measured against an engineer's current workflow and a deterministic evidence bundle. Synthetic evaluations, cloud deployment and capstone completion alone do not satisfy this gate.

TRACE will use this repository for a modular Python application. Volume 5/6 capabilities will be implemented within TRACE; they are currently designs. Selected educational components are reused through versioned contracts, with reliability, authorization, provenance and evaluation introduced in the first useful workflow.

## Controlled production response

TRACE is an incident intelligence and controlled-response platform. The first investigation releases are read-only; the final capstone includes at least one real, explicitly approved production remediation. See the [approved remediation scope](docs/planning/production-remediation-scope.md) for staging-to-production promotion, approval binding, execution limits and outcome verification. Production access and an appropriate target are required; a simulated or staging-only action does not satisfy the final production gate.
