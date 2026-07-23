data "azurerm_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 6
  lower   = true
  numeric = true
  special = false
  upper   = false
}

locals {
  suffix                   = random_string.suffix.result
  base_name                = "${var.name_prefix}-${local.suffix}"
  storage_name             = "${replace(var.name_prefix, "-", "")}${local.suffix}"
  function_name            = "${local.base_name}-api"
  foundry_account_name     = "${local.base_name}-foundry"
  foundry_project_name     = "dream-palace"
  foundry_project_endpoint = "https://${local.foundry_account_name}.services.ai.azure.com/api/projects/${local.foundry_project_name}"
  function_base_url        = "https://${local.function_name}.azurewebsites.net"

  runtime_storage_roles = toset([
    "Storage Blob Data Owner",
    "Storage Queue Data Contributor",
    "Storage Table Data Contributor",
  ])
}

resource "azurerm_resource_group" "main" {
  name     = "${local.base_name}-rg"
  location = var.location
  tags     = var.tags
}

resource "azurerm_user_assigned_identity" "runtime" {
  name                = "${local.base_name}-runtime"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags
}

resource "azurerm_user_assigned_identity" "github" {
  name                = "${local.base_name}-github"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tags                = var.tags
}

resource "azurerm_federated_identity_credential" "github" {
  name                = "github-production"
  resource_group_name = azurerm_resource_group.main.name
  parent_id           = azurerm_user_assigned_identity.github.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = "https://token.actions.githubusercontent.com"
  subject             = "repo:${var.github_repository}:environment:production"
}

resource "azurerm_storage_account" "main" {
  name                            = local.storage_name
  resource_group_name             = azurerm_resource_group.main.name
  location                        = azurerm_resource_group.main.location
  account_tier                    = "Standard"
  account_replication_type        = "ZRS"
  min_tls_version                 = "TLS1_2"
  allow_nested_items_to_be_public = false
  shared_access_key_enabled       = false
  tags                            = var.tags
}

resource "azurerm_storage_container" "function_releases" {
  name                  = "function-releases"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

resource "azurerm_storage_container" "dream_media" {
  name                  = "dream-media"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

resource "azurerm_role_assignment" "runtime_storage" {
  for_each = local.runtime_storage_roles

  scope                            = azurerm_storage_account.main.id
  role_definition_name             = each.value
  principal_id                     = azurerm_user_assigned_identity.runtime.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "migration_storage" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Owner"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_cosmosdb_account" "main" {
  name                          = "${local.base_name}-cosmos"
  location                      = azurerm_resource_group.main.location
  resource_group_name           = azurerm_resource_group.main.name
  offer_type                    = "Standard"
  kind                          = "GlobalDocumentDB"
  local_authentication_enabled  = false
  public_network_access_enabled = true

  capabilities {
    name = "EnableServerless"
  }

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = azurerm_resource_group.main.location
    failover_priority = 0
  }

  tags = var.tags
}

resource "azurerm_cosmosdb_sql_database" "main" {
  name                = "dream-palace"
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
}

resource "azurerm_cosmosdb_sql_container" "users" {
  name                  = "users"
  resource_group_name   = azurerm_resource_group.main.name
  account_name          = azurerm_cosmosdb_account.main.name
  database_name         = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths   = ["/telegram_id"]
  partition_key_version = 2
}

resource "azurerm_cosmosdb_sql_container" "dreams" {
  name                  = "dreams"
  resource_group_name   = azurerm_resource_group.main.name
  account_name          = azurerm_cosmosdb_account.main.name
  database_name         = azurerm_cosmosdb_sql_database.main.name
  partition_key_paths   = ["/user_id"]
  partition_key_version = 2
}

resource "azurerm_cosmosdb_sql_role_assignment" "runtime" {
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  role_definition_id  = "${azurerm_cosmosdb_account.main.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = azurerm_user_assigned_identity.runtime.principal_id
  scope               = azurerm_cosmosdb_account.main.id
}

resource "azurerm_cosmosdb_sql_role_assignment" "migration" {
  resource_group_name = azurerm_resource_group.main.name
  account_name        = azurerm_cosmosdb_account.main.name
  role_definition_id  = "${azurerm_cosmosdb_account.main.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = data.azurerm_client_config.current.object_id
  scope               = azurerm_cosmosdb_account.main.id
}

resource "azurerm_key_vault" "main" {
  name                       = "${local.base_name}-kv"
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  enable_rbac_authorization  = true
  purge_protection_enabled   = true
  soft_delete_retention_days = 7
  tags                       = var.tags
}

resource "azurerm_role_assignment" "runtime_key_vault" {
  scope                            = azurerm_key_vault.main.id
  role_definition_name             = "Key Vault Secrets User"
  principal_id                     = azurerm_user_assigned_identity.runtime.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "deployer_key_vault" {
  scope                = azurerm_key_vault.main.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

resource "azurerm_log_analytics_workspace" "main" {
  name                = "${local.base_name}-logs"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = var.tags
}

resource "azurerm_application_insights" "main" {
  name                = "${local.base_name}-insights"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
  tags                = var.tags
}

resource "azurerm_cognitive_account" "foundry" {
  name                       = local.foundry_account_name
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  kind                       = "AIServices"
  sku_name                   = "S0"
  custom_subdomain_name      = local.foundry_account_name
  project_management_enabled = true
  local_auth_enabled         = false

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

resource "azurerm_cognitive_account_project" "foundry" {
  name                 = local.foundry_project_name
  cognitive_account_id = azurerm_cognitive_account.foundry.id
  location             = azurerm_resource_group.main.location
  display_name         = "Dream Palace"
  description          = "Microsoft Foundry project for the hosted dream analyst."

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

resource "azurerm_cognitive_deployment" "model" {
  name                 = var.foundry_model_deployment_name
  cognitive_account_id = azurerm_cognitive_account.foundry.id

  model {
    format  = "OpenAI"
    name    = var.foundry_model_name
    version = var.foundry_model_version
  }

  scale {
    type     = "GlobalStandard"
    capacity = var.foundry_model_capacity
  }
}

resource "azurerm_role_assignment" "runtime_foundry" {
  scope                            = azurerm_cognitive_account_project.foundry.id
  role_definition_name             = "Foundry Agent Consumer"
  principal_id                     = azurerm_user_assigned_identity.runtime.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

resource "azurerm_service_plan" "functions" {
  name                = "${local.base_name}-flex"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = "FC1"
  tags                = var.tags
}

resource "azurerm_function_app_flex_consumption" "api" {
  name                = local.function_name
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  service_plan_id     = azurerm_service_plan.functions.id

  storage_container_type            = "blobContainer"
  storage_container_endpoint        = "${azurerm_storage_account.main.primary_blob_endpoint}${azurerm_storage_container.function_releases.name}"
  storage_authentication_type       = "UserAssignedIdentity"
  storage_user_assigned_identity_id = azurerm_user_assigned_identity.runtime.id

  runtime_name           = "python"
  runtime_version        = "3.12"
  maximum_instance_count = var.function_maximum_instance_count
  instance_memory_in_mb  = 2048
  http_concurrency       = 20

  https_only                      = true
  public_network_access_enabled   = true
  key_vault_reference_identity_id = azurerm_user_assigned_identity.runtime.id

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.runtime.id]
  }

  app_settings = {
    FUNCTIONS_EXTENSION_VERSION          = "~4"
    FUNCTIONS_WORKER_RUNTIME             = "python"
    AzureWebJobsStorage__accountName     = azurerm_storage_account.main.name
    AzureWebJobsStorage__credential      = "managedidentity"
    AzureWebJobsStorage__clientId        = azurerm_user_assigned_identity.runtime.client_id
    BOT_TOKEN                            = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault.main.vault_uri}secrets/bot-token)"
    WEBHOOK_SECRET                       = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault.main.vault_uri}secrets/telegram-webhook-secret)"
    ADMIN_TELEGRAM_IDS                   = var.admin_telegram_ids
    WEBAPP_URL                           = "${local.function_base_url}/app"
    AZURE_CLIENT_ID                      = azurerm_user_assigned_identity.runtime.client_id
    AZURE_STORAGE_ACCOUNT_URL            = azurerm_storage_account.main.primary_blob_endpoint
    AZURE_STORAGE_CONTAINER              = azurerm_storage_container.dream_media.name
    COSMOS_ENDPOINT                      = azurerm_cosmosdb_account.main.endpoint
    COSMOS_DATABASE_NAME                 = azurerm_cosmosdb_sql_database.main.name
    COSMOS_USERS_CONTAINER               = azurerm_cosmosdb_sql_container.users.name
    COSMOS_DREAMS_CONTAINER              = azurerm_cosmosdb_sql_container.dreams.name
    FOUNDRY_PROJECT_ENDPOINT             = local.foundry_project_endpoint
    FOUNDRY_AGENT_NAME                   = "dream-analyst"
  }

  site_config {
    application_insights_connection_string = azurerm_application_insights.main.connection_string
    health_check_path                      = "/health"
  }

  depends_on = [
    azurerm_role_assignment.runtime_storage,
    azurerm_role_assignment.runtime_key_vault,
    azurerm_role_assignment.runtime_foundry,
    azurerm_cosmosdb_sql_role_assignment.runtime,
  ]

  tags = var.tags
}

resource "azurerm_role_assignment" "github_contributor" {
  scope                            = azurerm_resource_group.main.id
  role_definition_name             = "Contributor"
  principal_id                     = azurerm_user_assigned_identity.github.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "github_storage" {
  scope                            = azurerm_storage_account.main.id
  role_definition_name             = "Storage Blob Data Owner"
  principal_id                     = azurerm_user_assigned_identity.github.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}

resource "azurerm_role_assignment" "github_foundry" {
  scope                            = azurerm_cognitive_account_project.foundry.id
  role_definition_name             = "Foundry Project Manager"
  principal_id                     = azurerm_user_assigned_identity.github.principal_id
  principal_type                   = "ServicePrincipal"
  skip_service_principal_aad_check = true
}
