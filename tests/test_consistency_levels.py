"""
Cosmos DB Consistency Level Testing
Demonstrates different consistency levels and their behavior
"""

import os
import time
import asyncio
from typing import Dict, Any
from azure.cosmos import CosmosClient, PartitionKey, exceptions
import pytest


class ConsistencyTester:
    """Test different consistency levels and their effects"""

    def __init__(self, endpoint: str, key: str):
        self.endpoint = endpoint
        self.key = key
        self.clients = {}

    def create_client(self, consistency_level: str) -> CosmosClient:
        """Create client with specific consistency level"""
        if consistency_level not in self.clients:
            self.clients[consistency_level] = CosmosClient(
                self.endpoint,
                self.key,
                consistency_level=consistency_level
            )
        return self.clients[consistency_level]

    def test_strong_consistency(self):
        """
        Strong Consistency Test
        - Guarantees linearizability
        - Reads always return most recent write
        - Highest consistency, highest latency
        """
        print("\n=== Testing Strong Consistency ===")

        client = self.create_client('Strong')
        database = client.get_database_client('ProductCatalog')
        container = database.get_container_client('Products')

        # Write item
        item = {
            'id': 'test-strong-001',
            'categoryId': 'test',
            'name': 'Strong Consistency Test',
            'value': 1,
            'timestamp': time.time()
        }

        start = time.time()
        container.upsert_item(item)
        write_time = time.time() - start

        # Immediate read should return latest value
        start = time.time()
        read_item = container.read_item('test-strong-001', 'test')
        read_time = time.time() - start

        print(f"Write latency: {write_time*1000:.2f}ms")
        print(f"Read latency: {read_time*1000:.2f}ms")
        print(f"Value matches: {read_item['value'] == item['value']}")

        assert read_item['value'] == item['value'], "Strong consistency guarantees latest value"

        return {
            'consistency_level': 'Strong',
            'write_latency_ms': write_time * 1000,
            'read_latency_ms': read_time * 1000,
            'data_consistent': True
        }

    def test_bounded_staleness(self, max_lag_operations: int = 100):
        """
        Bounded Staleness Test
        - Reads lag behind writes by at most K versions or T time
        - Guarantees consistent prefix
        - Good for scenarios needing consistency with lower latency
        """
        print("\n=== Testing Bounded Staleness ===")

        client = self.create_client('BoundedStaleness')
        database = client.get_database_client('ProductCatalog')
        container = database.get_container_client('Products')

        # Write multiple versions
        item_id = 'test-bounded-001'
        latencies = []

        for i in range(5):
            item = {
                'id': item_id,
                'categoryId': 'test',
                'name': 'Bounded Staleness Test',
                'value': i,
                'timestamp': time.time()
            }

            start = time.time()
            container.upsert_item(item)
            latencies.append((time.time() - start) * 1000)

            # Read immediately
            read_item = container.read_item(item_id, 'test')
            print(f"Write {i}: value={read_item['value']}, latency={latencies[-1]:.2f}ms")

        avg_latency = sum(latencies) / len(latencies)
        print(f"Average latency: {avg_latency:.2f}ms")

        return {
            'consistency_level': 'BoundedStaleness',
            'average_latency_ms': avg_latency,
            'max_lag_operations': max_lag_operations
        }

    def test_session_consistency(self):
        """
        Session Consistency Test
        - Guarantees consistency within a session
        - Different sessions may see different values
        - Default consistency level, good balance
        """
        print("\n=== Testing Session Consistency ===")

        client1 = self.create_client('Session')
        client2 = CosmosClient(self.endpoint, self.key, consistency_level='Session')

        database1 = client1.get_database_client('ProductCatalog')
        database2 = client2.get_database_client('ProductCatalog')

        container1 = database1.get_container_client('Products')
        container2 = database2.get_container_client('Products')

        item_id = 'test-session-001'

        # Client 1 writes
        item = {
            'id': item_id,
            'categoryId': 'test',
            'name': 'Session Consistency Test',
            'value': 100,
            'timestamp': time.time()
        }

        start = time.time()
        container1.upsert_item(item)
        write_latency = (time.time() - start) * 1000

        # Client 1 reads (same session) - should see latest
        read1 = container1.read_item(item_id, 'test')
        print(f"Client 1 (same session) reads: {read1['value']}")

        # Small delay
        time.sleep(0.1)

        # Client 2 reads (different session) - may see stale
        read2 = container2.read_item(item_id, 'test')
        print(f"Client 2 (different session) reads: {read2['value']}")

        print(f"Write latency: {write_latency:.2f}ms")

        return {
            'consistency_level': 'Session',
            'write_latency_ms': write_latency,
            'session_consistent': read1['value'] == item['value']
        }

    def test_consistent_prefix(self):
        """
        Consistent Prefix Test
        - Guarantees reads never see out-of-order writes
        - May see stale data but always in correct order
        - Lower latency than bounded staleness
        """
        print("\n=== Testing Consistent Prefix ===")

        client = self.create_client('ConsistentPrefix')
        database = client.get_database_client('ProductCatalog')
        container = database.get_container_client('Products')

        item_id = 'test-prefix-001'
        latencies = []

        # Write sequence
        for i in range(3):
            item = {
                'id': item_id,
                'categoryId': 'test',
                'name': 'Consistent Prefix Test',
                'value': i,
                'sequence': i,
                'timestamp': time.time()
            }

            start = time.time()
            container.upsert_item(item)
            latency = (time.time() - start) * 1000
            latencies.append(latency)

            print(f"Wrote sequence {i}, latency: {latency:.2f}ms")

        avg_latency = sum(latencies) / len(latencies)
        print(f"Average write latency: {avg_latency:.2f}ms")

        return {
            'consistency_level': 'ConsistentPrefix',
            'average_latency_ms': avg_latency
        }

    def test_eventual_consistency(self):
        """
        Eventual Consistency Test
        - Lowest latency, highest availability
        - No ordering guarantees
        - Reads may return stale data
        - Best for scenarios where consistency can be relaxed
        """
        print("\n=== Testing Eventual Consistency ===")

        client = self.create_client('Eventual')
        database = client.get_database_client('ProductCatalog')
        container = database.get_container_client('Products')

        item_id = 'test-eventual-001'
        latencies = []

        # Rapid writes
        for i in range(10):
            item = {
                'id': item_id,
                'categoryId': 'test',
                'name': 'Eventual Consistency Test',
                'value': i,
                'timestamp': time.time()
            }

            start = time.time()
            container.upsert_item(item)
            latency = (time.time() - start) * 1000
            latencies.append(latency)

        avg_latency = sum(latencies) / len(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)

        print(f"Average latency: {avg_latency:.2f}ms")
        print(f"Min latency: {min_latency:.2f}ms")
        print(f"Max latency: {max_latency:.2f}ms")

        return {
            'consistency_level': 'Eventual',
            'average_latency_ms': avg_latency,
            'min_latency_ms': min_latency,
            'max_latency_ms': max_latency
        }

    def compare_all_levels(self):
        """Run all consistency tests and compare results"""
        print("\n" + "="*60)
        print("COSMOS DB CONSISTENCY LEVEL COMPARISON")
        print("="*60)

        results = []

        try:
            results.append(self.test_strong_consistency())
        except Exception as e:
            print(f"Strong consistency test failed: {e}")

        try:
            results.append(self.test_bounded_staleness())
        except Exception as e:
            print(f"Bounded staleness test failed: {e}")

        try:
            results.append(self.test_session_consistency())
        except Exception as e:
            print(f"Session consistency test failed: {e}")

        try:
            results.append(self.test_consistent_prefix())
        except Exception as e:
            print(f"Consistent prefix test failed: {e}")

        try:
            results.append(self.test_eventual_consistency())
        except Exception as e:
            print(f"Eventual consistency test failed: {e}")

        # Summary
        print("\n" + "="*60)
        print("SUMMARY")
        print("="*60)
        print(f"{'Consistency Level':<20} {'Avg Latency (ms)':<20}")
        print("-"*60)

        for result in results:
            level = result['consistency_level']
            latency = result.get('write_latency_ms') or result.get('average_latency_ms', 0)
            print(f"{level:<20} {latency:<20.2f}")

        return results


def test_multi_region_read_preference():
    """
    Test reading from preferred regions
    Demonstrates geo-distribution benefits
    """
    endpoint = os.getenv('COSMOS_ENDPOINT')
    key = os.getenv('COSMOS_KEY')

    if not endpoint or not key:
        print("Skipping multi-region test - credentials not configured")
        return

    # Client with preferred locations
    client = CosmosClient(
        endpoint,
        key,
        preferred_locations=['East US', 'West US 2']
    )

    database = client.get_database_client('ProductCatalog')
    container = database.get_container_client('Products')

    # Test read latency
    item_id = 'test-region-001'
    start = time.time()
    try:
        container.read_item(item_id, 'test')
    except:
        pass
    latency = (time.time() - start) * 1000

    print(f"\nMulti-region read latency: {latency:.2f}ms")


if __name__ == '__main__':
    endpoint = os.getenv('COSMOS_ENDPOINT', 'https://your-account.documents.azure.com:443/')
    key = os.getenv('COSMOS_KEY', 'your-key')

    tester = ConsistencyTester(endpoint, key)
    results = tester.compare_all_levels()

    # Save results
    import json
    with open('consistency_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("\nResults saved to consistency_test_results.json")
