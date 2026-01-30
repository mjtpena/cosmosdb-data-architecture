terraform {
  required_version = ">= 1.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# Resource Group
resource "azurerm_resource_group" "cosmos" {
  name     = var.resource_group_name
  location = var.primary_location

  tags = var.tags
}

# Random suffix for unique naming
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

# Cosmos DB Account
resource "azurerm_cosmosdb_account" "main" {
  name                = "${var.cosmosdb_account_name}-${random_string.suffix.result}"
  location            = azurerm_resource_group.cosmos.location
  resource_group_name = azurerm_resource_group.cosmos.name
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"

  enable_automatic_failover       = var.enable_automatic_failover
  enable_multiple_write_locations = var.enable_multiple_write_locations
  public_network_access_enabled   = true
  enable_free_tier                = false

  consistency_policy {
    consistency_level       = var.consistency_level
    max_interval_in_seconds = var.consistency_level == "BoundedStaleness" ? var.max_interval_in_seconds : null
    max_staleness_prefix    = var.consistency_level == "BoundedStaleness" ? var.max_staleness_prefix : null
  }

  geo_location {
    location          = var.primary_location
    failover_priority = 0
    zone_redundant    = false
  }

  geo_location {
    location          = var.secondary_location
    failover_priority = 1
    zone_redundant    = false
  }

  backup {
    type                = "Periodic"
    interval_in_minutes = 240
    retention_in_hours  = 8
    storage_redundancy  = "Geo"
  }

  capabilities {
    name = "EnableServerless"
  }

  tags = var.tags
}

# SQL Database
resource "azurerm_cosmosdb_sql_database" "main" {
  name                = var.database_name
  resource_group_name = azurerm_resource_group.cosmos.name
  account_name        = azurerm_cosmosdb_account.main.name
  throughput          = var.database_throughput
}

# Products Container
resource "azurerm_cosmosdb_sql_container" "products" {
  name                = "Products"
  resource_group_name = azurerm_resource_group.cosmos.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/categoryId"
  default_ttl         = -1

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }

    excluded_path {
      path = "/\"_etag\"/?"
    }

    composite_index {
      index {
        path  = "/categoryId"
        order = "ascending"
      }

      index {
        path  = "/price"
        order = "descending"
      }
    }
  }

  unique_key {
    paths = ["/sku"]
  }
}

# Orders Container
resource "azurerm_cosmosdb_sql_container" "orders" {
  name                = "Orders"
  resource_group_name = azurerm_resource_group.cosmos.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/customerId"
  default_ttl         = -1

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }

    excluded_path {
      path = "/\"_etag\"/?"
    }
  }
}

# Customers Container
resource "azurerm_cosmosdb_sql_container" "customers" {
  name                = "Customers"
  resource_group_name = azurerm_resource_group.cosmos.name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_sql_database.main.name
  partition_key_path  = "/userId"

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }

    excluded_path {
      path = "/\"_etag\"/?"
    }
  }
}

# Analytics Container with hierarchical partition key
resource "azurerm_cosmosdb_sql_container" "analytics" {
  name                  = "Analytics"
  resource_group_name   = azurerm_resource_group.cosmos.name
  account_name          = azurerm_cosmosdb_account.main.name
  database_name         = azurerm_cosmosdb_sql_database.main.name
  partition_key_path    = "/tenantId"
  partition_key_version = 2
  analytical_storage_ttl = 2592000 # 30 days

  indexing_policy {
    indexing_mode = "consistent"

    included_path {
      path = "/*"
    }
  }
}
