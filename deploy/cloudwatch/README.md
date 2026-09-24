# TRACE hosted application logs

CloudWatch Logs is the owner-selected hosted platform; see [ADR 0003](../../docs/adr/0003-cloudwatch-hosted-logging.md). This directory supplies a collection example, not deployed infrastructure. Do not apply the example unchanged.

## Before activation

Owner-selected settings: AWS account 267653922622, region us-east-2, seven-day retention and a $5/month CloudWatch spending alert. The alert email and target EC2 host/environment are pending. Choose a bounded local rotation policy and provision reader/collector identities. The current aws-app-local identity resolves to the selected account but lacks logs:DescribeLogGroups. Use an authorized deployment profile/role before planning or applying. No AWS resources have been created by this PR.

Use Terraform to create the approved log group with explicit retention and tags. Replace REPLACE_ENVIRONMENT in agent.example.json with the chosen environment and validate the rendered configuration using the installed CloudWatch agent schema. Region follows the EC2 host unless deployment explicitly configures otherwise. Retention is intentionally absent from the agent example because Terraform owns it; the collector should not modify retention or create arbitrary groups.

The service launcher must capture the application's JSON stderr in /var/log/trace/application.jsonl with restricted file access. The CloudWatch agent tails that file using the instance identity; it does not capture arbitrary application stderr by itself. Do not mix non-JSON launcher output into the application file. Configure bounded disk retention/rotation and verify collection across rotation and agent restart; do not assume exactly-once delivery. If deployment uses containers instead, record and test the chosen native collector integration before replacing this file-based example.

Keep redaction in TRACE before records reach disk or AWS. Do not enable verbose collector request-body logging. Define handling for collector outage and disk exhaustion; application progress must not wait for a synchronous AWS log API call, and log loss must be observable.

## Hosted acceptance for issue #3

1. Apply reviewed Terraform and collector configuration only after account, region, retention and spending inputs are settled.
2. Run a valid and invalid check-config invocation on the target host; record the generated correlation IDs and UTC window.
3. Search the selected log group in Logs Insights using the query below, replacing the placeholder with the observed ID. Verify timestamp, level, component, event and application_version in the actual JSON event.
4. Exercise a synthetic redaction fixture containing no real credentials. Check both local output and hosted records; sensitive fields must not expose the fixture value.
5. Verify the configured retention, write/read access boundaries, rotation behavior and collector interruption/recovery. Record observable delivery lag and any duplicate/loss behavior; choose acceptance thresholds before the run.
6. Link account/region (without credentials), group, query window, sanitized result evidence and relevant infrastructure revision in the issue. Keep the issue open until hosted acceptance and code review pass.

```text
fields @timestamp, level, component, event, correlation_id, application_version, @message
| filter correlation_id = "REPLACE_WITH_OBSERVED_ID"
| sort @timestamp asc
| limit 100
```

Select a narrow time range and the intended group before running queries. Retention does not cap ingestion costs, and budget alerts do not stop spending. Review current regional ingestion, storage and query costs against expected volume before deployment.

This integration stores TRACE's own application logs. It does not implement the later read-only evidence adapters for Order/Payment or other monitored services.
## Terraform handoff

main.tf prepares the log group, seven-day retention and $5 monthly budget notification. The provider refuses other accounts. The budget covers all Amazon CloudWatch service costs in this account, across regions, including other workloads and non-log CloudWatch charges; it is intentionally broader than TRACE-only log costs. Cost-allocation tag filtering can be adopted later if accurately activated and verified. The budget is account-wide: manage this root once, not separately per environment with the same budget name.

Supply environment and alert_email through private TF_VAR values or an ignored tfvars file. Use the authorized AWS_PROFILE; never put credentials in Terraform source. Terraform state contains the notification recipient despite its sensitive designation; protect the state. Before shared/cloud operation choose an access-controlled encrypted remote state backend and locking; do not lose or share local state casually.

After the PR and deployment inputs are reviewed:

```sh
cd deploy/cloudwatch
terraform init
terraform fmt -check
terraform validate
terraform plan -out=cloudwatch.tfplan
```

Commit the generated provider lockfile after initialization/review. Terraform is not installed in the current environment, so format/schema/provider validation and a live plan have not been run. Do not treat the checked-in HCL as a verified deployment. Review the saved plan before apply. No EC2 instance or role attachment is created here; the collector policy output must be integrated with the approved host's role separately. Existing resources must be discovered/imported before apply, not blindly recreated. Teardown must explicitly decide whether to preserve logs; destroying a log group deletes its retained events.