using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using Microsoft.Azure.Cosmos;
using Microsoft.Extensions.Logging;
using Newtonsoft.Json;

namespace CosmosDB.DataArchitecture
{
    /// <summary>
    /// Cosmos DB C# SDK Examples
    /// Demonstrates CRUD operations, queries, and best practices
    /// </summary>
    public class CosmosDBManager
    {
        private readonly CosmosClient _client;
        private readonly Database _database;
        private readonly ILogger<CosmosDBManager> _logger;

        public CosmosDBManager(string endpoint, string key, string databaseName, ILogger<CosmosDBManager> logger)
        {
            var clientOptions = new CosmosClientOptions
            {
                ApplicationName = "CosmosDB-Data-Architecture",
                ConnectionMode = ConnectionMode.Direct,
                MaxRetryAttemptsOnRateLimitedRequests = 9,
                MaxRetryWaitTimeOnRateLimitedRequests = TimeSpan.FromSeconds(30),
                ConsistencyLevel = ConsistencyLevel.Session
            };

            _client = new CosmosClient(endpoint, key, clientOptions);
            _database = _client.GetDatabase(databaseName);
            _logger = logger;

            _logger.LogInformation($"Connected to database: {databaseName}");
        }

        private Container GetContainer(string containerName)
        {
            return _database.GetContainer(containerName);
        }

        #region CREATE Operations

        /// <summary>
        /// Create a new item in the container
        /// </summary>
        public async Task<T> CreateItemAsync<T>(string containerName, T item, string partitionKey)
        {
            var container = GetContainer(containerName);
            try
            {
                var response = await container.CreateItemAsync(
                    item,
                    new PartitionKey(partitionKey)
                );

                _logger.LogInformation($"Created item. RU: {response.RequestCharge}");
                return response.Resource;
            }
            catch (CosmosException ex) when (ex.StatusCode == System.Net.HttpStatusCode.Conflict)
            {
                _logger.LogError($"Item already exists: {ex.Message}");
                throw;
            }
        }

        /// <summary>
        /// Create multiple items using bulk operations
        /// </summary>
        public async Task<List<T>> CreateItemsBulkAsync<T>(string containerName, List<(T item, string partitionKey)> items)
        {
            var container = GetContainer(containerName);
            var tasks = new List<Task<ItemResponse<T>>>();

            foreach (var (item, partitionKey) in items)
            {
                tasks.Add(container.CreateItemAsync(
                    item,
                    new PartitionKey(partitionKey)
                ));
            }

            var responses = await Task.WhenAll(tasks);
            var results = responses.Select(r => r.Resource).ToList();

            _logger.LogInformation($"Bulk created {results.Count} items");
            return results;
        }

        #endregion

        #region READ Operations

        /// <summary>
        /// Read a single item by ID and partition key (point read - most efficient)
        /// </summary>
        public async Task<T> ReadItemAsync<T>(string containerName, string itemId, string partitionKey)
        {
            var container = GetContainer(containerName);
            try
            {
                var response = await container.ReadItemAsync<T>(
                    itemId,
                    new PartitionKey(partitionKey)
                );

                _logger.LogInformation($"Read item. RU: {response.RequestCharge}");
                return response.Resource;
            }
            catch (CosmosException ex) when (ex.StatusCode == System.Net.HttpStatusCode.NotFound)
            {
                _logger.LogWarning($"Item not found: {itemId}");
                return default;
            }
        }

        /// <summary>
        /// Query items using SQL query
        /// </summary>
        public async Task<List<T>> QueryItemsAsync<T>(
            string containerName,
            string query,
            Dictionary<string, object> parameters = null,
            string partitionKey = null,
            int maxItemCount = 100)
        {
            var container = GetContainer(containerName);
            var queryDefinition = new QueryDefinition(query);

            if (parameters != null)
            {
                foreach (var param in parameters)
                {
                    queryDefinition.WithParameter(param.Key, param.Value);
                }
            }

            var queryRequestOptions = new QueryRequestOptions
            {
                MaxItemCount = maxItemCount
            };

            if (!string.IsNullOrEmpty(partitionKey))
            {
                queryRequestOptions.PartitionKey = new PartitionKey(partitionKey);
            }

            var results = new List<T>();
            double totalRU = 0;

            using var iterator = container.GetItemQueryIterator<T>(queryDefinition, requestOptions: queryRequestOptions);

            while (iterator.HasMoreResults)
            {
                var response = await iterator.ReadNextAsync();
                results.AddRange(response);
                totalRU += response.RequestCharge;
            }

            _logger.LogInformation($"Query returned {results.Count} items. Total RU: {totalRU}");
            return results;
        }

        /// <summary>
        /// Query items with pagination
        /// </summary>
        public async IAsyncEnumerable<List<T>> QueryItemsPaginatedAsync<T>(
            string containerName,
            string query,
            Dictionary<string, object> parameters = null,
            string partitionKey = null,
            int pageSize = 100)
        {
            var container = GetContainer(containerName);
            var queryDefinition = new QueryDefinition(query);

            if (parameters != null)
            {
                foreach (var param in parameters)
                {
                    queryDefinition.WithParameter(param.Key, param.Value);
                }
            }

            var queryRequestOptions = new QueryRequestOptions
            {
                MaxItemCount = pageSize
            };

            if (!string.IsNullOrEmpty(partitionKey))
            {
                queryRequestOptions.PartitionKey = new PartitionKey(partitionKey);
            }

            using var iterator = container.GetItemQueryIterator<T>(queryDefinition, requestOptions: queryRequestOptions);

            while (iterator.HasMoreResults)
            {
                var response = await iterator.ReadNextAsync();
                yield return response.ToList();
            }
        }

        #endregion

        #region UPDATE Operations

        /// <summary>
        /// Update an item (read-replace pattern)
        /// </summary>
        public async Task<T> UpdateItemAsync<T>(
            string containerName,
            string itemId,
            string partitionKey,
            Action<T> updateAction)
        {
            var container = GetContainer(containerName);

            // Read current item
            var response = await container.ReadItemAsync<T>(
                itemId,
                new PartitionKey(partitionKey)
            );

            var item = response.Resource;

            // Apply updates
            updateAction(item);

            // Replace item
            var updateResponse = await container.ReplaceItemAsync(
                item,
                itemId,
                new PartitionKey(partitionKey)
            );

            _logger.LogInformation($"Updated item. RU: {updateResponse.RequestCharge}");
            return updateResponse.Resource;
        }

        /// <summary>
        /// Upsert an item (create or replace if exists)
        /// </summary>
        public async Task<T> UpsertItemAsync<T>(string containerName, T item, string partitionKey)
        {
            var container = GetContainer(containerName);

            var response = await container.UpsertItemAsync(
                item,
                new PartitionKey(partitionKey)
            );

            _logger.LogInformation($"Upserted item. RU: {response.RequestCharge}");
            return response.Resource;
        }

        /// <summary>
        /// Patch an item using partial document update
        /// </summary>
        public async Task<T> PatchItemAsync<T>(
            string containerName,
            string itemId,
            string partitionKey,
            List<PatchOperation> patchOperations)
        {
            var container = GetContainer(containerName);

            var response = await container.PatchItemAsync<T>(
                itemId,
                new PartitionKey(partitionKey),
                patchOperations
            );

            _logger.LogInformation($"Patched item. RU: {response.RequestCharge}");
            return response.Resource;
        }

        #endregion

        #region DELETE Operations

        /// <summary>
        /// Delete an item
        /// </summary>
        public async Task DeleteItemAsync(string containerName, string itemId, string partitionKey)
        {
            var container = GetContainer(containerName);

            try
            {
                var response = await container.DeleteItemAsync<object>(
                    itemId,
                    new PartitionKey(partitionKey)
                );

                _logger.LogInformation($"Deleted item. RU: {response.RequestCharge}");
            }
            catch (CosmosException ex) when (ex.StatusCode == System.Net.HttpStatusCode.NotFound)
            {
                _logger.LogWarning($"Item not found: {itemId}");
            }
        }

        #endregion

        #region Advanced Operations

        /// <summary>
        /// Execute a stored procedure
        /// </summary>
        public async Task<T> ExecuteStoredProcedureAsync<T>(
            string containerName,
            string sprocName,
            string partitionKey,
            dynamic[] parameters = null)
        {
            var container = GetContainer(containerName);

            var response = await container.Scripts.ExecuteStoredProcedureAsync<T>(
                sprocName,
                new PartitionKey(partitionKey),
                parameters
            );

            _logger.LogInformation($"Executed stored procedure. RU: {response.RequestCharge}");
            return response.Resource;
        }

        /// <summary>
        /// Read change feed
        /// </summary>
        public async IAsyncEnumerable<List<T>> ReadChangeFeedAsync<T>(
            string containerName,
            string partitionKey = null)
        {
            var container = GetContainer(containerName);

            var changeFeedIterator = container.GetChangeFeedIterator<T>(
                ChangeFeedStartFrom.Beginning(),
                ChangeFeedMode.Incremental
            );

            while (changeFeedIterator.HasMoreResults)
            {
                var response = await changeFeedIterator.ReadNextAsync();

                if (response.StatusCode == System.Net.HttpStatusCode.NotModified)
                {
                    break;
                }

                yield return response.ToList();
            }
        }

        /// <summary>
        /// Get container throughput
        /// </summary>
        public async Task<int?> GetThroughputAsync(string containerName)
        {
            var container = GetContainer(containerName);

            try
            {
                var throughput = await container.ReadThroughputAsync();
                _logger.LogInformation($"Container throughput: {throughput} RU/s");
                return throughput;
            }
            catch (CosmosException ex)
            {
                _logger.LogError($"Failed to get throughput: {ex.Message}");
                return null;
            }
        }

        /// <summary>
        /// Execute transactional batch
        /// </summary>
        public async Task<TransactionalBatchResponse> ExecuteBatchAsync(
            string containerName,
            string partitionKey,
            List<TransactionalBatchItemRequestOptions> operations)
        {
            var container = GetContainer(containerName);

            var batch = container.CreateTransactionalBatch(new PartitionKey(partitionKey));

            // Operations must be added to batch before execution
            var response = await batch.ExecuteAsync();

            _logger.LogInformation($"Executed batch. RU: {response.RequestCharge}");
            return response;
        }

        #endregion
    }

    #region Model Classes

    public class Product
    {
        [JsonProperty("id")]
        public string Id { get; set; }

        [JsonProperty("categoryId")]
        public string CategoryId { get; set; }

        [JsonProperty("name")]
        public string Name { get; set; }

        [JsonProperty("sku")]
        public string Sku { get; set; }

        [JsonProperty("price")]
        public decimal Price { get; set; }

        [JsonProperty("inventory")]
        public int Inventory { get; set; }
    }

    public class Order
    {
        [JsonProperty("id")]
        public string Id { get; set; }

        [JsonProperty("customerId")]
        public string CustomerId { get; set; }

        [JsonProperty("orderDate")]
        public DateTime OrderDate { get; set; }

        [JsonProperty("items")]
        public List<OrderItem> Items { get; set; }

        [JsonProperty("total")]
        public decimal Total { get; set; }
    }

    public class OrderItem
    {
        [JsonProperty("productId")]
        public string ProductId { get; set; }

        [JsonProperty("quantity")]
        public int Quantity { get; set; }

        [JsonProperty("price")]
        public decimal Price { get; set; }
    }

    #endregion
}
