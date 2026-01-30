// Cosmos DB Multi-Region Account with SQL API
@description('Name of the Cosmos DB account')
param cosmosDbAccountName string = 'cosmos-${uniqueString(resourceGroup().id)}'

@description('Primary location for Cosmos DB account')
param primaryLocation string = resourceGroup().location

@description('Secondary location for multi-region replication')
param secondaryLocation string = 'westus2'

@description('Consistency level for the Cosmos DB account')
@allowed([
  'Eventual'
  'ConsistentPrefix'
  'Session'
  'BoundedStaleness'
  'Strong'
])
param consistencyLevel string = 'Session'

@description('Max staleness prefix for Bounded Staleness')
param maxStalenessPrefix int = 100000

@description('Max interval in seconds for Bounded Staleness')
param maxIntervalInSeconds int = 300

@description('Enable automatic failover')
param enableAutomaticFailover bool = true

@description('Enable multi-region writes')
param enableMultipleWriteLocations bool = false

@description('Database name')
param databaseName string = 'ProductCatalog'

@description('Throughput for database (RU/s)')
param databaseThroughput int = 400

// Cosmos DB Account
resource cosmosDbAccount 'Microsoft.DocumentDB/databaseAccounts@2023-04-15' = {
  name: cosmosDbAccountName
  location: primaryLocation
  kind: 'GlobalDocumentDB'
  properties: {
    consistencyPolicy: {
      defaultConsistencyLevel: consistencyLevel
      maxStalenessPrefix: consistencyLevel == 'BoundedStaleness' ? maxStalenessPrefix : null
      maxIntervalInSeconds: consistencyLevel == 'BoundedStaleness' ? maxIntervalInSeconds : null
    }
    locations: [
      {
        locationName: primaryLocation
        failoverPriority: 0
        isZoneRedundant: false
      }
      {
        locationName: secondaryLocation
        failoverPriority: 1
        isZoneRedundant: false
      }
    ]
    databaseAccountOfferType: 'Standard'
    enableAutomaticFailover: enableAutomaticFailover
    enableMultipleWriteLocations: enableMultipleWriteLocations
    capabilities: [
      {
        name: 'EnableServerless'
      }
    ]
    publicNetworkAccess: 'Enabled'
    enableFreeTier: false
    backupPolicy: {
      type: 'Periodic'
      periodicModeProperties: {
        backupIntervalInMinutes: 240
        backupRetentionIntervalInHours: 8
        backupStorageRedundancy: 'Geo'
      }
    }
  }
}

// Database
resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2023-04-15' = {
  parent: cosmosDbAccount
  name: databaseName
  properties: {
    resource: {
      id: databaseName
    }
    options: {
      throughput: databaseThroughput
    }
  }
}

// Products Container with partition key /categoryId
resource productsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: database
  name: 'Products'
  properties: {
    resource: {
      id: 'Products'
      partitionKey: {
        paths: [
          '/categoryId'
        ]
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: [
          {
            path: '/"_etag"/?'
          }
        ]
        compositeIndexes: [
          [
            {
              path: '/categoryId'
              order: 'ascending'
            }
            {
              path: '/price'
              order: 'descending'
            }
          ]
        ]
      }
      uniqueKeyPolicy: {
        uniqueKeys: [
          {
            paths: [
              '/sku'
            ]
          }
        ]
      }
      defaultTtl: -1
    }
  }
}

// Orders Container with partition key /customerId
resource ordersContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: database
  name: 'Orders'
  properties: {
    resource: {
      id: 'Orders'
      partitionKey: {
        paths: [
          '/customerId'
        ]
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: [
          {
            path: '/"_etag"/?'
          }
        ]
      }
      defaultTtl: -1
    }
  }
}

// Customers Container with partition key /userId
resource customersContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: database
  name: 'Customers'
  properties: {
    resource: {
      id: 'Customers'
      partitionKey: {
        paths: [
          '/userId'
        ]
        kind: 'Hash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          {
            path: '/*'
          }
        ]
        excludedPaths: [
          {
            path: '/"_etag"/?'
          }
        ]
      }
    }
  }
}

// Analytics Container with hierarchical partition key
resource analyticsContainer 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2023-04-15' = {
  parent: database
  name: 'Analytics'
  properties: {
    resource: {
      id: 'Analytics'
      partitionKey: {
        paths: [
          '/tenantId'
          '/year'
          '/month'
        ]
        kind: 'MultiHash'
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
      }
      analyticalStorageTtl: 2592000 // 30 days
    }
  }
}

// Outputs
output cosmosDbAccountName string = cosmosDbAccount.name
output cosmosDbEndpoint string = cosmosDbAccount.properties.documentEndpoint
output databaseName string = database.name
output primaryKey string = cosmosDbAccount.listKeys().primaryMasterKey
output connectionString string = cosmosDbAccount.listConnectionStrings().connectionStrings[0].connectionString
