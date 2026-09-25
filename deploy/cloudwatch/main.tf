terraform {
  required_version = ">= 1.6, < 2.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region              = "us-east-2"
  allowed_account_ids = ["267653922622"]
}

variable "environment" {
  description = "Approved deployment environment; keep development and production logs separate."
  type        = string
  validation {
    condition     = contains(["development", "test", "production"], var.environment)
    error_message = "Choose development, test, or production."
  }
}

variable "alert_email" {
  description = "Owner-approved budget notification recipient; supply privately, not in committed tfvars."
  type        = string
  sensitive   = true
  validation {
    condition     = can(regex("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", var.alert_email))
    error_message = "Provide a valid notification email address."
  }
}

resource "aws_cloudwatch_log_group" "application" {
  name              = "/trace/${var.environment}/application"
  retention_in_days = 7
  tags = {
    Application = "TRACE"
    Environment = var.environment
  }
}

# Account-wide CloudWatch service cost, not just TRACE or log ingestion.
# Deliberately broad: avoids gaps from unactivated cost-allocation tags.
resource "aws_budgets_budget" "cloudwatch" {
  account_id   = "267653922622"
  name         = "trace-cloudwatch-monthly"
  budget_type  = "COST"
  limit_amount = "5"
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  cost_filter {
    name   = "Service"
    values = ["AmazonCloudWatch"]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }
}

output "log_group_name" {
  value = aws_cloudwatch_log_group.application.name
}

# Attach through the separately reviewed EC2 role configuration. This does not
# create an instance, grant access to this caller, or attach a policy by itself.
output "collector_policy_json" {
  value = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "${aws_cloudwatch_log_group.application.arn}:*"
    }]
  })
}