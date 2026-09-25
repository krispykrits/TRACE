# Infrastructure and environment responsibilities

Status: Sprint 1 foundation, 2026-09-25. [ADR 0002](../docs/adr/0002-terraform-and-ec2-cloud-deployment.md) selects Terraform and EC2 for the Cloud MVP. [ADR 0003](../docs/adr/0003-cloudwatch-hosted-logging.md) selects CloudWatch Logs for application logging. [ADR 0005](../docs/adr/0005-sqlite-local-postgresql-rds-cloud.md) selects PostgreSQL on RDS for Cloud MVP state after SQLite Local MVP. [ADR 0006](../docs/adr/0006-pgvector-cloud-retrieval-storage.md) selects pgvector on that RDS database for cloud vector retrieval; embedding/index configuration and retrieval acceptance remain gated. Selection does not authorize an AWS apply. The existing [CloudWatch example](cloudwatch/README.md) is deployment preparation, not a deployed environment.

| Environment | Purpose and owner | Current infrastructure boundary |
| --- | --- | --- |
| Local development | Contributor runs CLI and offline checks with Python 3.12, pinned uv and Makefile | No AWS account, credentials or cloud resources required; use disposable local `.venv` |
| Development cloud | Future S7/S8 integration target, designed by project team with account owner | Define EC2/RDS identity, network, state, cost, retention, migration, recovery and teardown before Terraform apply; no target exists yet |
| Demo / Cloud MVP | Future reviewed release of the accepted local workflow on EC2 | Provision measured EC2/RDS resources, migrate SQLite state, promote an immutable app version, smoke test, record costs and prove backup/restore and teardown/recreation; exact design remains open |
| Operational Pilot | Separately authorized real-source replay and read-only shadow use | Requires named operator/source owner, data permissions, retention/deletion, recovery and support ownership; a demo deployment cannot substitute |

## Apply gates for later cloud work

1. Record measured workload and owner-approved spending constraints. ADR 0003's $5 monthly CloudWatch alert is a notification, not a hard cap or an overall AWS budget. Estimate EC2, RDS, storage, data transfer, logs and state costs for the selected design; set limits/alerts before apply.
2. Confirm account, region, deployment role and scoped workload identity. Do not commit credentials or Terraform state. Separate Terraform deployment permissions, EC2 collector write permissions, RDS database roles, log-reader access and application/source access. The current `aws-app-local` identity lacks `logs:DescribeLogGroups`; the [CloudWatch activation guide](cloudwatch/README.md) records its pending inputs.
3. Review Terraform plan, resource names, network exposure, retention, backup/restore and state storage/locking. Record who owns promotion, rollback, incident response and cost monitoring. Do not use Terraform remote provisioners as routine app deployment; see ADR 0002.
4. Document and rehearse teardown/recreation, including state handling, retained data/logs and deletion policy. Verify no orphaned billable resources remain after a demo. S7/S9 own this acceptance; this issue creates no resources.

S7 chooses exact EC2/RDS topology, database access/backup, pgvector extension compatibility and Terraform state; S8 migrates SQLite state to RDS, enables pgvector after its workload, budget, access and compatibility gates are met, chooses application artifact release/rollback and configures CloudWatch Logs collection on EC2; S9 verifies migration, restore, hosted delivery, retention, rotation and collector recovery as part of Cloud MVP acceptance. Until then, use the [local development workflow](../docs/development.md). Neither a plan file nor these documents prove hosted logging delivery or Cloud MVP acceptance.
