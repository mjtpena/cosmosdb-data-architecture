# Quick Start Guide

Get started with Cosmos DB Data Architecture in 5 minutes.

## Prerequisites

- Azure subscription
- Azure CLI installed
- Git installed
- Python 3.9+ OR .NET 8 OR Node.js 18+

## Step 1: Clone the Repository

```bash
git clone https://github.com/mjtpena/cosmosdb-data-architecture.git
cd cosmosdb-data-architecture
```

## Step 2: Deploy Infrastructure

### Option A: Using Bicep (Recommended)

```bash
cd infrastructure/bicep

# Login to Azure
az login

# Create resource group
az group create --name rg-cosmosdb-demo --location eastus

# Deploy
az deployment group create \
  --resource-group rg-cosmosdb-demo \
  --template-file main.bicep \
  --parameters parameters.json

# Get connection details
az deployment group show \
  --resource-group rg-cosmosdb-demo \
  --name <deployment-name> \
  --query properties.outputs
```

### Option B: Using Terraform

```bash
cd infrastructure/terraform

# Initialize
terraform init

# Plan
terraform plan

# Apply
terraform apply

# Get outputs
terraform output
```

## Step 3: Configure Environment

Create `.env` file in the root directory:

```bash
cp .env.example .env
```

Edit `.env` with your Cosmos DB credentials:

```
COSMOS_ENDPOINT=https://your-account.documents.azure.com:443/
COSMOS_KEY=your-primary-key
COSMOS_ACCOUNT_NAME=your-account-name
COSMOS_DATABASE=ProductCatalog
```

## Step 4: Run SDK Examples

### Python

```bash
cd src/python
pip install -r requirements.txt
python cosmos_client.py
```

### C#

```bash
cd src/csharp
dotnet restore
dotnet run
```

### Node.js

```bash
cd src/nodejs
npm install
npm start
```

## Step 5: Run Tests (Optional)

```bash
# Set environment variables
source .env

# Run consistency level tests
cd tests
python test_consistency_levels.py

# Run API tests
python test_cosmos_api.py

# Run performance benchmarks
cd ../benchmarks
python performance_benchmark.py
```

## What's Next?

1. **Learn Data Modeling**: Read [Partition Key Patterns](models/partition-key-patterns.md)
2. **Explore Denormalization**: Read [Denormalization Patterns](models/denormalization-patterns.md)
3. **Optimize Performance**: Run benchmarks and analyze results
4. **Try Migration**: Use migration tools to move data
5. **Read Full Documentation**: Check [README.md](README.md) for comprehensive guide

## Common Operations

### Point Read (Most Efficient)
```python
item = container.read_item(item_id, partition_key)
```

### Query with Partition Key
```python
query = "SELECT * FROM c WHERE c.categoryId = @category"
items = container.query_items(query, partition_key=category_id)
```

### Bulk Insert
```python
for item in items:
    container.create_item(item)
```

### Patch Update
```python
operations = [
    {'op': 'replace', 'path': '/price', 'value': 99.99}
]
container.patch_item(item_id, partition_key, operations)
```

## Troubleshooting

### Issue: 429 Too Many Requests
**Solution**: Increase RU/s in portal or implement retry logic

### Issue: Connection Timeout
**Solution**: Check firewall rules, ensure public access enabled

### Issue: Document Not Found
**Solution**: Verify partition key value is correct

### Issue: Import Module Errors
**Solution**: Install dependencies: `pip install -r requirements.txt`

## Resources

- [Full README](README.md)
- [GitHub Repository](https://github.com/mjtpena/cosmosdb-data-architecture)
- [Azure Cosmos DB Docs](https://docs.microsoft.com/azure/cosmos-db/)

## Support

For issues and questions, please [open an issue](https://github.com/mjtpena/cosmosdb-data-architecture/issues) on GitHub.
