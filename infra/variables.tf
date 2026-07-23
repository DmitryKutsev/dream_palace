variable "name_prefix" {
  description = "Short lowercase prefix used for globally unique Azure resource names."
  type        = string
  default     = "dreampalace"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,11}$", var.name_prefix))
    error_message = "name_prefix must be 3-12 lowercase letters, numbers, or hyphens."
  }
}

variable "location" {
  description = "Azure region. Sweden Central supports both Flex Consumption and hosted agents."
  type        = string
  default     = "swedencentral"
}

variable "github_repository" {
  description = "GitHub repository allowed to exchange an OIDC token in the production environment."
  type        = string
  default     = "DmitryKutsev/dream_palace"
}

variable "admin_telegram_ids" {
  description = "Comma-separated Telegram IDs allowed to approve users."
  type        = string
}

variable "foundry_model_name" {
  description = "Foundry model catalog name."
  type        = string
  default     = "gpt-5.4-mini"
}

variable "foundry_model_version" {
  description = "Foundry model version available in the selected region."
  type        = string
  default     = "2026-03-17"
}

variable "foundry_model_deployment_name" {
  description = "Deployment name injected into the hosted agent."
  type        = string
  default     = "gpt-5.4-mini"
}

variable "foundry_model_capacity" {
  description = "Global Standard deployment capacity in thousands of tokens per minute."
  type        = number
  default     = 10
}

variable "function_maximum_instance_count" {
  description = "Maximum Flex Consumption scale-out."
  type        = number
  default     = 20
}

variable "tags" {
  description = "Tags applied to Azure resources."
  type        = map(string)
  default = {
    application = "dream-palace"
    managed-by  = "terraform"
  }
}
