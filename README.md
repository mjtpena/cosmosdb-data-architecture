# Cosmos DB Data Architecture

A comprehensive reference implementation demonstrating Azure Cosmos DB best practices, data modeling patterns, SDK usage, and infrastructure as code.

## Overview

This repository provides production-ready examples and patterns for building scalable, high-performance applications with Azure Cosmos DB. It covers everything from infrastructure deployment to application development, testing, and migration.

## Repository Structure

```
cosmosdb-data-architecture/
├── infrastructure/          # Infrastructure as Code
│   ├── bicep/              # Azure Bicep templates
│   └── terraform/          # Terraform configurations
├── models/                 # Data modeling patterns and documentation
├── src/                    # SDK examples in multiple languages
│   ├── python/            # Python SDK examples
│   ├── csharp/            # C# SDK examples
│   └── nodejs/            # Node.js SDK examples
├── tests/                  # Testing suites
├── benchmarks/             # Performance benchmarking tools
└── migration/              # Data migration utilities
```

## Features

### Infrastructure as Code
- **Bicep**: Complete Azure Cosmos DB deployment with multi-region replication
- **Terraform**: Infrastructure provisioning with variables and outputs
- Multi-region configuration with automatic failover
- Multiple consistency levels
- Hierarchical partition keys
- Analytical storage integration

### Data Modeling Patterns
- **Partition Key Design**: Best practices and anti-patterns
- **Denormalization Patterns**: Embedding, referencing, hybrid approaches
- **Bucketing**: Managing time-series and growing data
- **Materialized Views**: Query optimization strategies
- **Event Sourcing**: Audit trails and temporal queries

### SDK Examples
Complete CRUD operations in multiple languages:
- **Python**: Full-featured client with async support
- **C#**: .NET 8 implementation with best practices
- **Node.js**: Modern JavaScript/TypeScript examples

Features demonstrated:
- Point reads (most efficient)
- Complex queries with parameters
- Bulk operations
- Patch operations (partial updates)
- Stored procedures
- Change feed processing
- Transactional batches

### Testing & Benchmarking
- **Consistency Level Testing**: Compare behavior across all consistency levels
- **REST API Testing**: Direct API interaction examples
- **Performance Benchmarking**: Comprehensive throughput and latency tests
- **Multi-region Testing**: Geo-distribution validation

### Migration Tools
- Container-to-container migration
- Cross-account migration
- Change feed-based continuous sync
- JSON export/import
- Data transformation during migration

## Quick Start

### Prerequisites
- Azure subscription
- Azure CLI or Azure PowerShell
- Python 3.9+, .NET 8, or Node.js 18+ (depending on SDK choice)

### 1. Deploy Infrastructure

#### Using Bicep
```bash
cd infrastructure/bicep

# Create resource group
az group create --name rg-cosmosdb-demo --location eastus

# Deploy Cosmos DB
az deployment group create \
  --resource-group rg-cosmosdb-demo \
  --template-file main.bicep \
  --parameters parameters.json
```

#### Using Terraform
```bash
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Review plan
terraform plan

# Deploy
terraform apply

# Get connection details
terraform output cosmosdb_endpoint
terraform output -raw cosmosdb_primary_key
```

### 2. Configure Environment Variables

```bash
export COSMOS_ENDPOINT="https://your-account.documents.azure.com:443/"
export COSMOS_KEY="your-primary-key"
export COSMOS_DATABASE="ProductCatalog"
```

### 3. Run SDK Examples

#### Python
```bash
cd src/python
pip install -r requirements.txt
python cosmos_client.py
```

#### C#
```bash
cd src/csharp
dotnet restore
dotnet run
```

#### Node.js
```bash
cd src/nodejs
npm install
npm start
```

## Architecture Patterns

### 1. E-Commerce Platform
**Use Case**: Product catalog with orders and customers

**Containers**:
- **Products**: Partition key `/categoryId`
- **Orders**: Partition key `/customerId`
- **Customers**: Partition key `/userId`

**Why**: Natural grouping enables efficient queries while distributing load

### 2. IoT Telemetry
**Use Case**: High-throughput sensor data ingestion

**Container**: Telemetry
**Partition Key**: `/deviceId-date` (composite)

**Why**: Prevents single partition growth, enables time-based queries

### 3. Multi-Tenant SaaS
**Use Case**: Isolated tenant data with shared infrastructure

**Container**: Universal
**Partition Key**: `/tenantId` (hierarchical with subkeys)

**Why**: Logical isolation, compliance, efficient tenant queries

### 4. Social Media
**Use Case**: User posts, feeds, and interactions

**Containers**:
- **Posts**: Partition key `/userId`
- **Feeds**: Materialized view with denormalized data

**Why**: Fast user-specific queries, optimized for common access patterns

## Data Modeling Best Practices

### Partition Key Selection

✅ **DO**:
- Choose high-cardinality keys (thousands+ unique values)
- Include partition key in most queries
- Consider future data growth
- Use composite keys for time-series data
- Implement hierarchical keys for multi-level distribution

❌ **DON'T**:
- Use low-cardinality keys (status, type, category alone)
- Create unbounded partitions (single tenant forever)
- Use sequential IDs as partition keys
- Use `/id` as partition key (one document per partition)

### Denormalization Strategy

**Embed** when:
- Related data always queried together
- Child items are few (< 100)
- Data rarely updated independently
- Need atomic operations

**Reference** when:
- One-to-many with many children
- Children updated frequently
- Need independent queries
- Data shared across parents

**Hybrid** when:
- Need summary data immediately
- Full dataset too large
- Common queries need subset only

## Consistency Levels

| Level | Latency | Availability | Staleness | Use Case |
|-------|---------|--------------|-----------|----------|
| **Strong** | Highest | Lowest | None | Financial transactions, inventory |
| **Bounded Staleness** | High | Medium | K versions/T time | Consistent views, scoreboard |
| **Session** | Medium | High | Within session | User experiences, shopping carts |
| **Consistent Prefix** | Low | High | In-order | Social media feeds, comments |
| **Eventual** | Lowest | Highest | Unpredictable | Analytics, telemetry, logs |

### Choosing Consistency Level

1. **Strong**: When you need linearizability (read reflects latest write)
2. **Bounded Staleness**: When you need consistency with defined lag
3. **Session**: When user should see their own writes (default, recommended)
4. **Consistent Prefix**: When order matters but staleness acceptable
5. **Eventual**: When lowest latency and highest availability critical

## Performance Optimization

### Request Units (RU) Optimization

**Point Reads** (most efficient):
```python
# 1 RU for 1KB document
item = container.read_item(item_id, partition_key)
```

**Single-Partition Query**:
```python
# ~2 RUs per 1KB document
query = "SELECT * FROM c WHERE c.categoryId = @category"
items = container.query_items(query, partition_key=category_id)
```

**Cross-Partition Query** (expensive):
```python
# 2.5+ RUs per 1KB document
query = "SELECT * FROM c WHERE c.price > 100"
items = container.query_items(query, enable_cross_partition_query=True)
```

### Indexing Best Practices

```json
{
  "indexingPolicy": {
    "automatic": true,
    "indexingMode": "consistent",
    "includedPaths": [
      {"path": "/*"}
    ],
    "excludedPaths": [
      {"path": "/largeText/?"},
      {"path": "/\"_etag\"/?"}
    ],
    "compositeIndexes": [
      [
        {"path": "/categoryId", "order": "ascending"},
        {"path": "/price", "order": "descending"}
      ]
    ]
  }
}
```

**Tips**:
- Exclude large text fields from indexing
- Use composite indexes for ORDER BY on multiple fields
- Exclude `/_etag` to save RUs on writes
- Use spatial indexes only when needed

## Testing

### Run Consistency Tests
```bash
cd tests
python test_consistency_levels.py
```

Output compares latency across all consistency levels.

### Run API Tests
```bash
python test_cosmos_api.py
```

Tests REST API endpoints directly.

### Run Performance Benchmarks
```bash
cd benchmarks
python performance_benchmark.py
```

Generates detailed performance report:
- Point read/write latency
- Query performance
- Bulk operation throughput
- Concurrent operation handling
- Document size impact

## Migration

### Container-to-Container Migration
```bash
cd migration

python data_migration_tool.py migrate \
  --source-endpoint $SOURCE_ENDPOINT \
  --source-key $SOURCE_KEY \
  --source-database ProductCatalog \
  --source-container OldProducts \
  --target-endpoint $TARGET_ENDPOINT \
  --target-key $TARGET_KEY \
  --target-database ProductCatalog \
  --target-container NewProducts \
  --workers 10
```

### Export to JSON
```bash
python data_migration_tool.py export \
  --source-endpoint $COSMOS_ENDPOINT \
  --source-key $COSMOS_KEY \
  --source-database ProductCatalog \
  --source-container Products \
  --file products_backup.json
```

### Import from JSON
```bash
python data_migration_tool.py import \
  --target-endpoint $COSMOS_ENDPOINT \
  --target-key $COSMOS_KEY \
  --target-database ProductCatalog \
  --target-container Products \
  --file products_backup.json
```

### Continuous Sync (Change Feed)
```bash
python data_migration_tool.py sync \
  --source-endpoint $SOURCE_ENDPOINT \
  --source-key $SOURCE_KEY \
  --source-database ProductCatalog \
  --source-container Products \
  --target-endpoint $TARGET_ENDPOINT \
  --target-key $TARGET_KEY \
  --target-database ProductCatalog \
  --target-container ProductsReplica
```

## Cost Optimization

### Strategies

1. **Use Autoscale**: Scale RU/s based on demand
2. **Optimize Queries**: Always include partition key
3. **Right-size Documents**: Keep under 100KB when possible
4. **Use TTL**: Automatically expire old data
5. **Leverage Serverless**: For unpredictable workloads
6. **Batch Operations**: Reduce per-operation overhead
7. **Use Patch**: Update specific fields instead of replace
8. **Archive Old Data**: Move to cheaper storage tiers

### Monitoring

Key metrics to track:
- Request Units consumed
- Throttling rate (429 errors)
- Query patterns and costs
- Document size distribution
- Partition hot spots

## Multi-Region Deployment

### Benefits
- **Low Latency**: Read from nearest region
- **High Availability**: Automatic failover
- **Disaster Recovery**: Data replicated globally
- **Compliance**: Data residency requirements

### Configuration

```typescript
// Preferred read regions
const client = new CosmosClient({
  endpoint,
  key,
  connectionPolicy: {
    preferredLocations: ['West US', 'East US', 'UK South']
  }
});
```

### Consistency Across Regions

| Consistency Level | Cross-Region Behavior |
|------------------|----------------------|
| Strong | Synchronous replication, highest latency |
| Bounded Staleness | Guaranteed lag bounds |
| Session | Consistent within session, any region |
| Consistent Prefix | In-order updates |
| Eventual | Asynchronous, lowest latency |

## Security Best Practices

1. **Use Azure AD Authentication**: Avoid master keys in production
2. **Enable Private Endpoints**: Restrict network access
3. **Implement RBAC**: Fine-grained access control
4. **Rotate Keys**: Regular key rotation policy
5. **Audit Logging**: Enable diagnostic logs
6. **Encryption**: TLS in transit, encryption at rest
7. **Firewall Rules**: Limit IP access
8. **Resource Tokens**: Scoped access for client apps

## Troubleshooting

### Common Issues

**429 (Too Many Requests)**
- Solution: Increase RU/s or implement retry logic
- Check for hot partitions

**High Query RUs**
- Solution: Add partition key to query
- Create composite indexes
- Optimize query predicate

**Large Document Size**
- Solution: Split into multiple documents
- Use bucketing pattern
- Store large content in Blob Storage

**Slow Queries**
- Solution: Add appropriate indexes
- Use partition key in WHERE clause
- Avoid SELECT * in production

## Additional Resources

### Documentation
- [Azure Cosmos DB Documentation](https://docs.microsoft.com/azure/cosmos-db/)
- [Partitioning Guide](https://docs.microsoft.com/azure/cosmos-db/partitioning-overview)
- [Data Modeling Guide](https://docs.microsoft.com/azure/cosmos-db/modeling-data)
- [Performance Tips](https://docs.microsoft.com/azure/cosmos-db/performance-tips)

### Tools
- [Azure Cosmos DB Explorer](https://cosmos.azure.com/)
- [Cosmos DB Emulator](https://docs.microsoft.com/azure/cosmos-db/local-emulator)
- [Data Migration Tool](https://docs.microsoft.com/azure/cosmos-db/import-data)

### SDKs
- [Python SDK](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/cosmos)
- [.NET SDK](https://github.com/Azure/azure-cosmos-dotnet-v3)
- [Node.js SDK](https://github.com/Azure/azure-sdk-for-js/tree/main/sdk/cosmosdb)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Contact

For questions and support, please open an issue in this repository.

---

**Built with ❤️ for Azure Cosmos DB developers**
