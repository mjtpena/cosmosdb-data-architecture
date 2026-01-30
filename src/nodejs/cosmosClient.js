/**
 * Cosmos DB Node.js SDK Examples
 * Demonstrates CRUD operations, queries, and best practices
 */

const { CosmosClient } = require('@azure/cosmos');

class CosmosDBManager {
  /**
   * Initialize Cosmos DB client
   * @param {string} endpoint - Cosmos DB endpoint URL
   * @param {string} key - Cosmos DB primary or secondary key
   * @param {string} databaseName - Name of the database
   */
  constructor(endpoint, key, databaseName) {
    this.client = new CosmosClient({
      endpoint,
      key,
      connectionPolicy: {
        requestTimeout: 30000,
        enableEndpointDiscovery: true
      }
    });
    this.database = this.client.database(databaseName);
    console.log(`Connected to database: ${databaseName}`);
  }

  /**
   * Get container client
   * @param {string} containerName - Name of the container
   * @returns {Container} Container client
   */
  getContainer(containerName) {
    return this.database.container(containerName);
  }

  // CREATE Operations

  /**
   * Create a new item in the container
   * @param {string} containerName - Name of the container
   * @param {object} item - Item to create (must include 'id' and partition key)
   * @returns {Promise<object>} Created item
   */
  async createItem(containerName, item) {
    const container = this.getContainer(containerName);
    try {
      const { resource: createdItem, requestCharge } = await container.items.create(item);
      console.log(`Created item with id: ${createdItem.id}, RU: ${requestCharge}`);
      return createdItem;
    } catch (error) {
      if (error.code === 409) {
        console.error(`Item with id ${item.id} already exists`);
      }
      throw error;
    }
  }

  /**
   * Create multiple items using bulk operations
   * @param {string} containerName - Name of the container
   * @param {Array<object>} items - Array of items to create
   * @returns {Promise<Array<object>>} Array of created items
   */
  async createItemsBulk(containerName, items) {
    const container = this.getContainer(containerName);
    const results = [];

    const operations = items.map(item => ({
      operationType: 'Create',
      resourceBody: item
    }));

    try {
      const { resources, requestCharge } = await container.items.bulk(operations);
      console.log(`Bulk created ${resources.length} items, RU: ${requestCharge}`);
      return resources;
    } catch (error) {
      console.error('Bulk create failed:', error.message);
      throw error;
    }
  }

  // READ Operations

  /**
   * Read a single item by ID and partition key (point read - most efficient)
   * @param {string} containerName - Name of the container
   * @param {string} itemId - ID of the item
   * @param {string} partitionKey - Partition key value
   * @returns {Promise<object|null>} Item if found, null otherwise
   */
  async readItem(containerName, itemId, partitionKey) {
    const container = this.getContainer(containerName);
    try {
      const { resource: item, requestCharge } = await container.item(itemId, partitionKey).read();
      console.log(`Read item with id: ${itemId}, RU: ${requestCharge}`);
      return item;
    } catch (error) {
      if (error.code === 404) {
        console.warn(`Item with id ${itemId} not found`);
        return null;
      }
      throw error;
    }
  }

  /**
   * Query items using SQL query
   * @param {string} containerName - Name of the container
   * @param {string} query - SQL query string
   * @param {Array<object>} parameters - Query parameters
   * @param {string} partitionKey - Optional partition key for single-partition query
   * @param {number} maxItemCount - Maximum items per page
   * @returns {Promise<Array<object>>} Array of items matching the query
   */
  async queryItems(containerName, query, parameters = [], partitionKey = null, maxItemCount = 100) {
    const container = this.getContainer(containerName);

    const querySpec = {
      query,
      parameters
    };

    const options = {
      maxItemCount
    };

    if (partitionKey) {
      options.partitionKey = partitionKey;
    }

    try {
      const { resources: items, requestCharge } = await container.items
        .query(querySpec, options)
        .fetchAll();

      console.log(`Query returned ${items.length} items, RU: ${requestCharge}`);
      return items;
    } catch (error) {
      console.error('Query failed:', error.message);
      throw error;
    }
  }

  /**
   * Query items with pagination
   * @param {string} containerName - Name of the container
   * @param {string} query - SQL query string
   * @param {Array<object>} parameters - Query parameters
   * @param {string} partitionKey - Optional partition key
   * @param {number} pageSize - Items per page
   * @returns {AsyncGenerator<Array<object>>} Async generator yielding pages of items
   */
  async *queryItemsPaginated(containerName, query, parameters = [], partitionKey = null, pageSize = 100) {
    const container = this.getContainer(containerName);

    const querySpec = {
      query,
      parameters
    };

    const options = {
      maxItemCount: pageSize
    };

    if (partitionKey) {
      options.partitionKey = partitionKey;
    }

    const iterator = container.items.query(querySpec, options);

    while (iterator.hasMoreResults()) {
      const { resources: items } = await iterator.fetchNext();
      if (items.length > 0) {
        yield items;
      }
    }
  }

  // UPDATE Operations

  /**
   * Update an item (read-replace pattern)
   * @param {string} containerName - Name of the container
   * @param {string} itemId - ID of the item
   * @param {string} partitionKey - Partition key value
   * @param {object} updates - Object with fields to update
   * @returns {Promise<object>} Updated item
   */
  async updateItem(containerName, itemId, partitionKey, updates) {
    const container = this.getContainer(containerName);

    try {
      // Read current item
      const { resource: item } = await container.item(itemId, partitionKey).read();

      // Apply updates
      const updatedItem = { ...item, ...updates };

      // Replace item
      const { resource: result, requestCharge } = await container
        .item(itemId, partitionKey)
        .replace(updatedItem);

      console.log(`Updated item with id: ${itemId}, RU: ${requestCharge}`);
      return result;
    } catch (error) {
      console.error('Update failed:', error.message);
      throw error;
    }
  }

  /**
   * Upsert an item (create or replace if exists)
   * @param {string} containerName - Name of the container
   * @param {object} item - Item to upsert
   * @returns {Promise<object>} Upserted item
   */
  async upsertItem(containerName, item) {
    const container = this.getContainer(containerName);
    try {
      const { resource: upsertedItem, requestCharge } = await container.items.upsert(item);
      console.log(`Upserted item with id: ${upsertedItem.id}, RU: ${requestCharge}`);
      return upsertedItem;
    } catch (error) {
      console.error('Upsert failed:', error.message);
      throw error;
    }
  }

  /**
   * Patch an item using partial document update
   * @param {string} containerName - Name of the container
   * @param {string} itemId - ID of the item
   * @param {string} partitionKey - Partition key value
   * @param {Array<object>} operations - Array of patch operations
   * @returns {Promise<object>} Patched item
   */
  async patchItem(containerName, itemId, partitionKey, operations) {
    const container = this.getContainer(containerName);
    try {
      const { resource: patchedItem, requestCharge } = await container
        .item(itemId, partitionKey)
        .patch(operations);

      console.log(`Patched item with id: ${itemId}, RU: ${requestCharge}`);
      return patchedItem;
    } catch (error) {
      console.error('Patch failed:', error.message);
      throw error;
    }
  }

  // DELETE Operations

  /**
   * Delete an item
   * @param {string} containerName - Name of the container
   * @param {string} itemId - ID of the item
   * @param {string} partitionKey - Partition key value
   */
  async deleteItem(containerName, itemId, partitionKey) {
    const container = this.getContainer(containerName);
    try {
      const { requestCharge } = await container.item(itemId, partitionKey).delete();
      console.log(`Deleted item with id: ${itemId}, RU: ${requestCharge}`);
    } catch (error) {
      if (error.code === 404) {
        console.warn(`Item with id ${itemId} not found`);
      } else {
        throw error;
      }
    }
  }

  // Advanced Operations

  /**
   * Execute a stored procedure
   * @param {string} containerName - Name of the container
   * @param {string} sprocName - Name of the stored procedure
   * @param {string} partitionKey - Partition key value
   * @param {Array} params - Parameters to pass to the stored procedure
   * @returns {Promise<any>} Result from stored procedure
   */
  async executeStoredProcedure(containerName, sprocName, partitionKey, params = []) {
    const container = this.getContainer(containerName);
    try {
      const { resource: result, requestCharge } = await container
        .scripts
        .storedProcedure(sprocName)
        .execute(partitionKey, params);

      console.log(`Executed stored procedure: ${sprocName}, RU: ${requestCharge}`);
      return result;
    } catch (error) {
      console.error('Stored procedure execution failed:', error.message);
      throw error;
    }
  }

  /**
   * Read change feed
   * @param {string} containerName - Name of the container
   * @param {string} partitionKey - Optional partition key
   * @returns {AsyncGenerator<Array<object>>} Async generator yielding change batches
   */
  async *readChangeFeed(containerName, partitionKey = null) {
    const container = this.getContainer(containerName);

    const options = {
      startFromBeginning: true
    };

    if (partitionKey) {
      options.partitionKey = partitionKey;
    }

    const iterator = container.items.getChangeFeedIterator(options);

    while (iterator.hasMoreResults) {
      const response = await iterator.readNext();

      if (response.result && response.result.length > 0) {
        yield response.result;
      } else {
        break; // No more changes
      }
    }
  }

  /**
   * Get container throughput
   * @param {string} containerName - Name of the container
   * @returns {Promise<number|null>} Throughput in RU/s or null if not found
   */
  async getThroughput(containerName) {
    const container = this.getContainer(containerName);
    try {
      const { resource: offer } = await container.readOffer();
      const throughput = offer?.content?.offerThroughput;
      console.log(`Container throughput: ${throughput} RU/s`);
      return throughput;
    } catch (error) {
      console.error('Failed to get throughput:', error.message);
      return null;
    }
  }

  /**
   * Execute transactional batch
   * @param {string} containerName - Name of the container
   * @param {string} partitionKey - Partition key value
   * @param {Array<object>} operations - Array of batch operations
   * @returns {Promise<object>} Batch response
   */
  async executeBatch(containerName, partitionKey, operations) {
    const container = this.getContainer(containerName);
    try {
      const response = await container.items.batch(operations, partitionKey);
      console.log(`Executed batch, RU: ${response.requestCharge}`);
      return response;
    } catch (error) {
      console.error('Batch execution failed:', error.message);
      throw error;
    }
  }
}

// Example usage
async function exampleUsage() {
  // Initialize (use environment variables in production)
  const endpoint = process.env.COSMOS_ENDPOINT || 'https://your-account.documents.azure.com:443/';
  const key = process.env.COSMOS_KEY || 'your-key';
  const databaseName = 'ProductCatalog';

  const manager = new CosmosDBManager(endpoint, key, databaseName);

  try {
    // Create a product
    const product = {
      id: 'prod-001',
      categoryId: 'electronics',
      name: 'Laptop',
      sku: 'LAP-001',
      price: 999.99,
      inventory: 50
    };

    const createdProduct = await manager.createItem('Products', product);
    console.log('Created:', createdProduct);

    // Read the product (point read)
    const readProduct = await manager.readItem('Products', 'prod-001', 'electronics');
    console.log('Read:', readProduct);

    // Query products by category
    const query = 'SELECT * FROM c WHERE c.categoryId = @categoryId AND c.price < @maxPrice';
    const parameters = [
      { name: '@categoryId', value: 'electronics' },
      { name: '@maxPrice', value: 1500 }
    ];
    const products = await manager.queryItems('Products', query, parameters, 'electronics');
    console.log(`Query results: ${products.length} products`);

    // Update product using patch
    const patchOps = [
      { op: 'add', path: '/onSale', value: true },
      { op: 'replace', path: '/price', value: 899.99 },
      { op: 'incr', path: '/inventory', value: -1 }
    ];
    const updated = await manager.patchItem('Products', 'prod-001', 'electronics', patchOps);
    console.log('Updated:', updated);

    // Delete product
    await manager.deleteItem('Products', 'prod-001', 'electronics');
    console.log('Product deleted');

  } catch (error) {
    console.error('Error:', error);
  }
}

// Export for use in other modules
module.exports = { CosmosDBManager, exampleUsage };

// Run example if executed directly
if (require.main === module) {
  exampleUsage().catch(console.error);
}
