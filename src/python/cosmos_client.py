"""
Cosmos DB Python SDK Examples
Demonstrates CRUD operations, queries, and best practices
"""

import os
import json
from typing import List, Dict, Any, Optional
from azure.cosmos import CosmosClient, PartitionKey, exceptions
from azure.cosmos.container import ContainerProxy
from azure.cosmos.database import DatabaseProxy
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CosmosDBManager:
    """Manager class for Cosmos DB operations"""

    def __init__(self, endpoint: str, key: str, database_name: str):
        """
        Initialize Cosmos DB client

        Args:
            endpoint: Cosmos DB endpoint URL
            key: Cosmos DB primary or secondary key
            database_name: Name of the database
        """
        self.client = CosmosClient(endpoint, key)
        self.database: DatabaseProxy = self.client.get_database_client(database_name)
        logger.info(f"Connected to database: {database_name}")

    def get_container(self, container_name: str) -> ContainerProxy:
        """Get container client"""
        return self.database.get_container_client(container_name)

    # CREATE Operations

    def create_item(self, container_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new item in the container

        Args:
            container_name: Name of the container
            item: Item to create (must include 'id' and partition key)

        Returns:
            Created item with system properties
        """
        container = self.get_container(container_name)
        try:
            created_item = container.create_item(body=item)
            logger.info(f"Created item with id: {created_item['id']}")
            return created_item
        except exceptions.CosmosResourceExistsError:
            logger.error(f"Item with id {item['id']} already exists")
            raise
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Failed to create item: {e.message}")
            raise

    def create_items_bulk(self, container_name: str, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create multiple items using bulk operations

        Args:
            container_name: Name of the container
            items: List of items to create

        Returns:
            List of created items
        """
        container = self.get_container(container_name)
        results = []

        for item in items:
            try:
                result = container.create_item(body=item)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to create item {item.get('id')}: {str(e)}")

        logger.info(f"Bulk created {len(results)} items")
        return results

    # READ Operations

    def read_item(self, container_name: str, item_id: str, partition_key: str) -> Optional[Dict[str, Any]]:
        """
        Read a single item by ID and partition key (point read - most efficient)

        Args:
            container_name: Name of the container
            item_id: ID of the item
            partition_key: Partition key value

        Returns:
            Item if found, None otherwise
        """
        container = self.get_container(container_name)
        try:
            item = container.read_item(item=item_id, partition_key=partition_key)
            logger.info(f"Read item with id: {item_id}")
            return item
        except exceptions.CosmosResourceNotFoundError:
            logger.warning(f"Item with id {item_id} not found")
            return None
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Failed to read item: {e.message}")
            raise

    def query_items(
        self,
        container_name: str,
        query: str,
        parameters: Optional[List[Dict[str, Any]]] = None,
        partition_key: Optional[str] = None,
        max_item_count: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Query items using SQL query

        Args:
            container_name: Name of the container
            query: SQL query string
            parameters: Query parameters
            partition_key: Optional partition key for single-partition query
            max_item_count: Maximum items per page

        Returns:
            List of items matching the query
        """
        container = self.get_container(container_name)

        query_options = {
            'max_item_count': max_item_count
        }

        if partition_key:
            query_options['partition_key'] = partition_key

        try:
            items = list(container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=(partition_key is None),
                **query_options
            ))
            logger.info(f"Query returned {len(items)} items")
            return items
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Query failed: {e.message}")
            raise

    def query_items_paginated(
        self,
        container_name: str,
        query: str,
        parameters: Optional[List[Dict[str, Any]]] = None,
        partition_key: Optional[str] = None,
        page_size: int = 100
    ):
        """
        Query items with pagination support

        Yields:
            Pages of items
        """
        container = self.get_container(container_name)

        query_iterable = container.query_items(
            query=query,
            parameters=parameters,
            enable_cross_partition_query=(partition_key is None),
            partition_key=partition_key,
            max_item_count=page_size
        )

        for page in query_iterable.by_page():
            yield list(page)

    # UPDATE Operations

    def update_item(
        self,
        container_name: str,
        item_id: str,
        partition_key: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update an item (read-replace pattern)

        Args:
            container_name: Name of the container
            item_id: ID of the item
            partition_key: Partition key value
            updates: Dictionary of fields to update

        Returns:
            Updated item
        """
        container = self.get_container(container_name)

        try:
            # Read current item
            item = container.read_item(item=item_id, partition_key=partition_key)

            # Apply updates
            item.update(updates)

            # Replace item
            updated_item = container.replace_item(item=item_id, body=item)
            logger.info(f"Updated item with id: {item_id}")
            return updated_item
        except exceptions.CosmosResourceNotFoundError:
            logger.error(f"Item with id {item_id} not found")
            raise
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Failed to update item: {e.message}")
            raise

    def upsert_item(self, container_name: str, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upsert an item (create or replace if exists)

        Args:
            container_name: Name of the container
            item: Item to upsert

        Returns:
            Upserted item
        """
        container = self.get_container(container_name)
        try:
            upserted_item = container.upsert_item(body=item)
            logger.info(f"Upserted item with id: {upserted_item['id']}")
            return upserted_item
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Failed to upsert item: {e.message}")
            raise

    def patch_item(
        self,
        container_name: str,
        item_id: str,
        partition_key: str,
        operations: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Patch an item using partial document update

        Args:
            container_name: Name of the container
            item_id: ID of the item
            partition_key: Partition key value
            operations: List of patch operations

        Returns:
            Patched item
        """
        container = self.get_container(container_name)
        try:
            patched_item = container.patch_item(
                item=item_id,
                partition_key=partition_key,
                patch_operations=operations
            )
            logger.info(f"Patched item with id: {item_id}")
            return patched_item
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Failed to patch item: {e.message}")
            raise

    # DELETE Operations

    def delete_item(self, container_name: str, item_id: str, partition_key: str) -> None:
        """
        Delete an item

        Args:
            container_name: Name of the container
            item_id: ID of the item
            partition_key: Partition key value
        """
        container = self.get_container(container_name)
        try:
            container.delete_item(item=item_id, partition_key=partition_key)
            logger.info(f"Deleted item with id: {item_id}")
        except exceptions.CosmosResourceNotFoundError:
            logger.warning(f"Item with id {item_id} not found")
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Failed to delete item: {e.message}")
            raise

    # Advanced Operations

    def execute_stored_procedure(
        self,
        container_name: str,
        sproc_name: str,
        partition_key: str,
        params: Optional[List[Any]] = None
    ) -> Any:
        """
        Execute a stored procedure

        Args:
            container_name: Name of the container
            sproc_name: Name of the stored procedure
            partition_key: Partition key value
            params: Parameters to pass to the stored procedure

        Returns:
            Result from stored procedure
        """
        container = self.get_container(container_name)
        try:
            result = container.scripts.execute_stored_procedure(
                sproc=sproc_name,
                partition_key=partition_key,
                params=params
            )
            logger.info(f"Executed stored procedure: {sproc_name}")
            return result
        except exceptions.CosmosHttpResponseError as e:
            logger.error(f"Failed to execute stored procedure: {e.message}")
            raise

    def get_throughput(self, container_name: str) -> Optional[int]:
        """Get current throughput (RU/s) for a container"""
        container = self.get_container(container_name)
        try:
            offer = container.read_offer()
            throughput = offer.properties.get('content', {}).get('offerThroughput')
            logger.info(f"Container throughput: {throughput} RU/s")
            return throughput
        except Exception as e:
            logger.error(f"Failed to get throughput: {str(e)}")
            return None

    def get_request_charge(self, response_headers: Dict[str, str]) -> float:
        """Extract request charge from response headers"""
        return float(response_headers.get('x-ms-request-charge', 0))


def example_usage():
    """Example usage of CosmosDBManager"""

    # Initialize (use environment variables in production)
    endpoint = os.getenv('COSMOS_ENDPOINT', 'https://your-account.documents.azure.com:443/')
    key = os.getenv('COSMOS_KEY', 'your-key')
    database_name = 'ProductCatalog'

    manager = CosmosDBManager(endpoint, key, database_name)

    # Create a product
    product = {
        'id': 'prod-001',
        'categoryId': 'electronics',
        'name': 'Laptop',
        'sku': 'LAP-001',
        'price': 999.99,
        'inventory': 50
    }

    created_product = manager.create_item('Products', product)
    print(f"Created: {created_product}")

    # Read the product (point read)
    read_product = manager.read_item('Products', 'prod-001', 'electronics')
    print(f"Read: {read_product}")

    # Query products by category
    query = "SELECT * FROM c WHERE c.categoryId = @categoryId AND c.price < @maxPrice"
    parameters = [
        {'name': '@categoryId', 'value': 'electronics'},
        {'name': '@maxPrice', 'value': 1500}
    ]
    products = manager.query_items('Products', query, parameters, partition_key='electronics')
    print(f"Query results: {len(products)} products")

    # Update product using patch
    patch_ops = [
        {'op': 'add', 'path': '/onSale', 'value': True},
        {'op': 'replace', 'path': '/price', 'value': 899.99},
        {'op': 'incr', 'path': '/inventory', 'value': -1}
    ]
    updated = manager.patch_item('Products', 'prod-001', 'electronics', patch_ops)
    print(f"Updated: {updated}")

    # Delete product
    manager.delete_item('Products', 'prod-001', 'electronics')
    print("Product deleted")


if __name__ == '__main__':
    example_usage()
