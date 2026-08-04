variable "resource_group_name" {
  description = "Azure resource group name"
  type        = string
  default     = "ai-mep-rg"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "admin_username" {
  description = "VM admin username"
  type        = string
  default     = "azureuser"
}

variable "admin_password" {
  description = "VM admin password"
  type        = string
  default     = "ChangeMe123!"
  sensitive   = true
}

variable "db_admin_username" {
  description = "PostgreSQL admin username"
  type        = string
  default     = "postgresadmin"
}

variable "db_admin_password" {
  description = "PostgreSQL admin password"
  type        = string
  default     = "ChangeMe123!"
  sensitive   = true
}
