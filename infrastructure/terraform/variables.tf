variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
  default     = "rg-cosmosdb-data-arch"
}

variable "primary_location" {
  description = "Primary Azure region for deployment"
  type        = string
  default     = "eastus"
}

variable "secondary_location" {
  description = "Secondary Azure region for multi-region replication"
  type        = string
  default     = "westus2"
}

variable "cosmosdb_account_name" {
  description = "Name of the Cosmos DB account"
  type        = string
  default     = "cosmos-data-arch"
}

variable "database_name" {
  description = "Name of the Cosmos DB database"
  type        = string
  default     = "ProductCatalog"
}

variable "database_throughput" {
  description = "Throughput for the database in RU/s"
  type        = number
  default     = 400
}

variable "consistency_level" {
  description = "Consistency level for the Cosmos DB account"
  type        = string
  default     = "Session"

  validation {
    condition     = contains(["Eventual", "ConsistentPrefix", "Session", "BoundedStaleness", "Strong"], var.consistency_level)
    error_message = "Consistency level must be one of: Eventual, ConsistentPrefix, Session, BoundedStaleness, Strong."
  }
}

variable "max_staleness_prefix" {
  description = "Max staleness prefix for Bounded Staleness consistency"
  type        = number
  default     = 100000
}

variable "max_interval_in_seconds" {
  description = "Max interval in seconds for Bounded Staleness consistency"
  type        = number
  default     = 300
}

variable "enable_automatic_failover" {
  description = "Enable automatic failover for Cosmos DB account"
  type        = bool
  default     = true
}

variable "enable_multiple_write_locations" {
  description = "Enable multi-region writes for Cosmos DB account"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default = {
    Environment = "Development"
    Project     = "CosmosDB-Data-Architecture"
    ManagedBy   = "Terraform"
  }
}
