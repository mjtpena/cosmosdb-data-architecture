#!/bin/bash
# Deploy Cosmos DB infrastructure using Bicep

set -e

# Configuration
RESOURCE_GROUP="rg-cosmosdb-data-arch"
LOCATION="eastus"
DEPLOYMENT_NAME="cosmosdb-deployment-$(date +%Y%m%d-%H%M%S)"

# Check if Azure CLI is installed
if ! command -v az &> /dev/null; then
    echo "Error: Azure CLI is not installed"
    exit 1
fi

# Check if logged in
if ! az account show &> /dev/null; then
    echo "Error: Not logged into Azure. Run 'az login' first"
    exit 1
fi

echo "=== Deploying Cosmos DB Infrastructure ==="
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "Deployment Name: $DEPLOYMENT_NAME"
echo ""

# Create resource group if it doesn't exist
echo "Creating resource group..."
az group create \
    --name "$RESOURCE_GROUP" \
    --location "$LOCATION" \
    --output table

# Deploy Bicep template
echo ""
echo "Deploying Cosmos DB account..."
az deployment group create \
    --resource-group "$RESOURCE_GROUP" \
    --name "$DEPLOYMENT_NAME" \
    --template-file main.bicep \
    --parameters parameters.json \
    --output table

# Get deployment outputs
echo ""
echo "=== Deployment Outputs ==="
az deployment group show \
    --resource-group "$RESOURCE_GROUP" \
    --name "$DEPLOYMENT_NAME" \
    --query properties.outputs \
    --output table

# Save connection details to .env file
echo ""
echo "Saving connection details to .env..."
ENDPOINT=$(az deployment group show --resource-group "$RESOURCE_GROUP" --name "$DEPLOYMENT_NAME" --query properties.outputs.cosmosDbEndpoint.value -o tsv)
KEY=$(az deployment group show --resource-group "$RESOURCE_GROUP" --name "$DEPLOYMENT_NAME" --query properties.outputs.primaryKey.value -o tsv)
ACCOUNT_NAME=$(az deployment group show --resource-group "$RESOURCE_GROUP" --name "$DEPLOYMENT_NAME" --query properties.outputs.cosmosDbAccountName.value -o tsv)
DATABASE=$(az deployment group show --resource-group "$RESOURCE_GROUP" --name "$DEPLOYMENT_NAME" --query properties.outputs.databaseName.value -o tsv)

cat > ../../.env << EOF
COSMOS_ENDPOINT=$ENDPOINT
COSMOS_KEY=$KEY
COSMOS_ACCOUNT_NAME=$ACCOUNT_NAME
COSMOS_DATABASE=$DATABASE
EOF

echo ""
echo "=== Deployment Complete ==="
echo "Connection details saved to .env file"
echo ""
echo "Next steps:"
echo "1. Source the .env file: source .env"
echo "2. Run SDK examples in src/"
echo "3. Run tests in tests/"
