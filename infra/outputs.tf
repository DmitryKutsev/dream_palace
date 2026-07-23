output "resource_group_name" {
  value = azurerm_resource_group.main.name
}

output "function_app_name" {
  value = azurerm_function_app_flex_consumption.api.name
}

output "function_base_url" {
  value = local.function_base_url
}

output "storage_account_url" {
  value = azurerm_storage_account.main.primary_blob_endpoint
}

output "cosmos_endpoint" {
  value = azurerm_cosmosdb_account.main.endpoint
}

output "key_vault_name" {
  value = azurerm_key_vault.main.name
}

output "foundry_project_endpoint" {
  value = local.foundry_project_endpoint
}

output "foundry_model_deployment_name" {
  value = azurerm_cognitive_deployment.model.name
}

output "github_actions_client_id" {
  value = azurerm_user_assigned_identity.github.client_id
}

output "azure_tenant_id" {
  value = data.azurerm_client_config.current.tenant_id
}

output "azure_subscription_id" {
  value = data.azurerm_client_config.current.subscription_id
}
