terraform {
  required_version = ">= 1.17.0, < 2.0.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 5.12.0"
    }
  }
  backend "azurerm" {
    use_azuread_auth = true
    use_cli          = true
  }
}

provider "azurerm" {
  features {}
  resource_provider_registrations = "none"
}

variable "registry_resource_id" {
  type = string
}

variable "registry_name" {
  type = string
}

variable "resource_group_name" {
  type = string
}

variable "location" {
  type = string
}

import {
  to = azurerm_container_registry.trace
  id = var.registry_resource_id
}

resource "azurerm_container_registry" "trace" {
  admin_enabled                                = false
  anonymous_pull_enabled                       = false
  azuread_authentication_as_arm_policy_enabled = true
  data_endpoint_enabled                        = false
  encryption                                   = []
  export_policy_enabled                        = true
  location                                     = var.location
  name                                         = var.registry_name
  network_rule_bypass_for_tasks_enabled        = false
  network_rule_bypass_option                   = "AzureServices"
  network_rule_set                             = []
  public_network_access_enabled                = true
  quarantine_policy_enabled                    = false
  resource_group_name                          = var.resource_group_name
  retention_policy_in_days                     = 0
  role_assignment_mode                         = "LegacyRegistryPermissions"
  sku                                          = "Basic"
  tags                                         = {}
  zone_redundancy_enabled                      = false
}
