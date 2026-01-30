"""
Cosmos DB REST API Testing
Tests Cosmos DB using REST APIs directly
"""

import os
import hashlib
import hmac
import base64
from datetime import datetime
from urllib.parse import quote
import requests
import json


class CosmosDBRestClient:
    """Direct REST API client for Cosmos DB"""

    def __init__(self, account_name: str, master_key: str):
        self.account_name = account_name
        self.master_key = master_key
        self.base_url = f"https://{account_name}.documents.azure.com"

    def _generate_auth_token(self, verb: str, resource_type: str, resource_link: str, date: str) -> str:
        """Generate authorization token for Cosmos DB REST API"""
        key = base64.b64decode(self.master_key)
        text = f"{verb.lower()}\n{resource_type.lower()}\n{resource_link}\n{date.lower()}\n\n"
        body = text.encode('utf-8')
        digest = hmac.new(key, body, hashlib.sha256).digest()
        signature = base64.b64encode(digest).decode()
        master_token = f"type=master&ver=1.0&sig={signature}"
        return quote(master_token)

    def _get_headers(self, verb: str, resource_type: str, resource_link: str) -> dict:
        """Get HTTP headers for Cosmos DB REST API request"""
        utc_date = datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')
        auth_token = self._generate_auth_token(verb, resource_type, resource_link, utc_date)

        return {
            'Authorization': auth_token,
            'x-ms-date': utc_date,
            'x-ms-version': '2018-12-31',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

    def list_databases(self) -> dict:
        """List all databases"""
        url = f"{self.base_url}/dbs"
        headers = self._get_headers('GET', 'dbs', '')

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def get_database(self, database_id: str) -> dict:
        """Get database information"""
        url = f"{self.base_url}/dbs/{database_id}"
        resource_link = f"dbs/{database_id}"
        headers = self._get_headers('GET', 'dbs', resource_link)

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def list_containers(self, database_id: str) -> dict:
        """List all containers in a database"""
        url = f"{self.base_url}/dbs/{database_id}/colls"
        resource_link = f"dbs/{database_id}"
        headers = self._get_headers('GET', 'colls', resource_link)

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def create_document(self, database_id: str, container_id: str, document: dict, partition_key: str) -> dict:
        """Create a document"""
        url = f"{self.base_url}/dbs/{database_id}/colls/{container_id}/docs"
        resource_link = f"dbs/{database_id}/colls/{container_id}"
        headers = self._get_headers('POST', 'docs', resource_link)
        headers['x-ms-documentdb-partitionkey'] = json.dumps([partition_key])

        response = requests.post(url, headers=headers, json=document)
        response.raise_for_status()
        return response.json()

    def read_document(self, database_id: str, container_id: str, document_id: str, partition_key: str) -> dict:
        """Read a document"""
        url = f"{self.base_url}/dbs/{database_id}/colls/{container_id}/docs/{document_id}"
        resource_link = f"dbs/{database_id}/colls/{container_id}/docs/{document_id}"
        headers = self._get_headers('GET', 'docs', resource_link)
        headers['x-ms-documentdb-partitionkey'] = json.dumps([partition_key])

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def query_documents(self, database_id: str, container_id: str, query: str, partition_key: str = None) -> dict:
        """Query documents"""
        url = f"{self.base_url}/dbs/{database_id}/colls/{container_id}/docs"
        resource_link = f"dbs/{database_id}/colls/{container_id}"
        headers = self._get_headers('POST', 'docs', resource_link)
        headers['x-ms-documentdb-isquery'] = 'True'
        headers['x-ms-documentdb-query-enablecrosspartition'] = 'True' if not partition_key else 'False'

        if partition_key:
            headers['x-ms-documentdb-partitionkey'] = json.dumps([partition_key])

        query_body = {
            "query": query,
            "parameters": []
        }

        response = requests.post(url, headers=headers, json=query_body)
        response.raise_for_status()
        return response.json()

    def delete_document(self, database_id: str, container_id: str, document_id: str, partition_key: str) -> None:
        """Delete a document"""
        url = f"{self.base_url}/dbs/{database_id}/colls/{container_id}/docs/{document_id}"
        resource_link = f"dbs/{database_id}/colls/{container_id}/docs/{document_id}"
        headers = self._get_headers('DELETE', 'docs', resource_link)
        headers['x-ms-documentdb-partitionkey'] = json.dumps([partition_key])

        response = requests.delete(url, headers=headers)
        response.raise_for_status()

    def get_request_charge(self, response: requests.Response) -> float:
        """Extract request charge from response headers"""
        return float(response.headers.get('x-ms-request-charge', 0))


def test_database_operations():
    """Test database-level operations"""
    account_name = os.getenv('COSMOS_ACCOUNT_NAME', 'your-account')
    master_key = os.getenv('COSMOS_KEY', 'your-key')

    client = CosmosDBRestClient(account_name, master_key)

    print("\n=== Testing Database Operations ===")

    # List databases
    try:
        databases = client.list_databases()
        print(f"✓ List databases: Found {len(databases.get('Databases', []))} databases")

        if databases.get('Databases'):
            db_id = databases['Databases'][0]['id']
            print(f"  First database: {db_id}")

            # Get database details
            db_info = client.get_database(db_id)
            print(f"✓ Get database: {db_info['id']}")

            # List containers
            containers = client.list_containers(db_id)
            print(f"✓ List containers: Found {len(containers.get('DocumentCollections', []))} containers")

    except requests.exceptions.HTTPError as e:
        print(f"✗ Database operation failed: {e}")


def test_document_operations():
    """Test document-level CRUD operations"""
    account_name = os.getenv('COSMOS_ACCOUNT_NAME', 'your-account')
    master_key = os.getenv('COSMOS_KEY', 'your-key')
    database_id = os.getenv('COSMOS_DATABASE', 'ProductCatalog')
    container_id = 'Products'

    client = CosmosDBRestClient(account_name, master_key)

    print("\n=== Testing Document Operations ===")

    # Create document
    document = {
        'id': 'rest-api-test-001',
        'categoryId': 'test',
        'name': 'REST API Test Product',
        'price': 99.99,
        'inventory': 10
    }

    try:
        created = client.create_document(database_id, container_id, document, 'test')
        print(f"✓ Create document: {created['id']}")

        # Read document
        read_doc = client.read_document(database_id, container_id, document['id'], 'test')
        print(f"✓ Read document: {read_doc['id']} - {read_doc['name']}")

        # Query documents
        query = "SELECT * FROM c WHERE c.categoryId = 'test'"
        results = client.query_documents(database_id, container_id, query, 'test')
        print(f"✓ Query documents: Found {len(results.get('Documents', []))} documents")

        # Delete document
        client.delete_document(database_id, container_id, document['id'], 'test')
        print(f"✓ Delete document: {document['id']}")

    except requests.exceptions.HTTPError as e:
        print(f"✗ Document operation failed: {e}")
        print(f"  Response: {e.response.text if hasattr(e, 'response') else 'N/A'}")


def test_query_performance():
    """Test query performance with different patterns"""
    account_name = os.getenv('COSMOS_ACCOUNT_NAME', 'your-account')
    master_key = os.getenv('COSMOS_KEY', 'your-key')
    database_id = os.getenv('COSMOS_DATABASE', 'ProductCatalog')
    container_id = 'Products'

    client = CosmosDBRestClient(account_name, master_key)

    print("\n=== Testing Query Performance ===")

    queries = [
        ("Point query (with partition key)", "SELECT * FROM c WHERE c.id = 'test-001'", 'test'),
        ("Range query (single partition)", "SELECT * FROM c WHERE c.price > 50 AND c.price < 100", 'test'),
        ("Cross-partition query", "SELECT * FROM c WHERE c.price > 50", None),
    ]

    for name, query, partition_key in queries:
        try:
            import time
            start = time.time()
            result = client.query_documents(database_id, container_id, query, partition_key)
            elapsed = (time.time() - start) * 1000

            print(f"\n{name}:")
            print(f"  Query: {query}")
            print(f"  Latency: {elapsed:.2f}ms")
            print(f"  Results: {len(result.get('Documents', []))} documents")

        except Exception as e:
            print(f"✗ Query failed: {e}")


def test_api_endpoints():
    """Test various Cosmos DB REST API endpoints"""
    print("\n" + "="*60)
    print("COSMOS DB REST API TESTS")
    print("="*60)

    # Check environment variables
    required_vars = ['COSMOS_ACCOUNT_NAME', 'COSMOS_KEY']
    missing_vars = [var for var in required_vars if not os.getenv(var)]

    if missing_vars:
        print(f"\n⚠ Missing environment variables: {', '.join(missing_vars)}")
        print("  Set these variables to run the tests")
        return

    # Run tests
    test_database_operations()
    test_document_operations()
    test_query_performance()

    print("\n" + "="*60)
    print("API Tests Complete")
    print("="*60)


if __name__ == '__main__':
    test_api_endpoints()
