"""
Cosmos DB Performance Benchmarking Suite
Measures throughput, latency, and RU consumption for various operations
"""

import os
import time
import statistics
import concurrent.futures
from typing import List, Dict, Any
from azure.cosmos import CosmosClient, PartitionKey
import random
import string
import json


class PerformanceBenchmark:
    """Benchmark Cosmos DB performance"""

    def __init__(self, endpoint: str, key: str, database_name: str, container_name: str):
        self.client = CosmosClient(endpoint, key)
        self.database = self.client.get_database_client(database_name)
        self.container = self.database.get_container_client(container_name)
        self.results = []

    def generate_test_document(self, doc_id: str, partition_key: str, size_kb: int = 1) -> dict:
        """Generate a test document of specified size"""
        # Calculate padding to reach desired size
        base_doc = {
            'id': doc_id,
            'categoryId': partition_key,
            'name': f'Test Product {doc_id}',
            'price': random.uniform(10, 1000),
            'inventory': random.randint(0, 1000)
        }

        current_size = len(json.dumps(base_doc))
        target_size = size_kb * 1024
        padding_size = max(0, target_size - current_size)

        if padding_size > 0:
            base_doc['padding'] = ''.join(random.choices(string.ascii_letters, k=padding_size))

        return base_doc

    def benchmark_point_reads(self, num_operations: int = 100) -> Dict[str, Any]:
        """Benchmark point read operations"""
        print(f"\n=== Benchmarking Point Reads ({num_operations} operations) ===")

        # Create test documents
        partition_key = 'benchmark-reads'
        doc_ids = []

        for i in range(num_operations):
            doc_id = f'read-test-{i}'
            doc = self.generate_test_document(doc_id, partition_key)
            self.container.upsert_item(doc)
            doc_ids.append(doc_id)

        # Benchmark reads
        latencies = []
        ru_charges = []

        for doc_id in doc_ids:
            start = time.time()
            response = self.container.read_item(doc_id, partition_key)
            elapsed = (time.time() - start) * 1000
            latencies.append(elapsed)
            ru_charges.append(float(self.container.client_connection.last_response_headers.get('x-ms-request-charge', 0)))

        results = {
            'operation': 'Point Read',
            'num_operations': num_operations,
            'avg_latency_ms': statistics.mean(latencies),
            'p50_latency_ms': statistics.median(latencies),
            'p95_latency_ms': self._percentile(latencies, 95),
            'p99_latency_ms': self._percentile(latencies, 99),
            'min_latency_ms': min(latencies),
            'max_latency_ms': max(latencies),
            'avg_ru': statistics.mean(ru_charges),
            'total_ru': sum(ru_charges)
        }

        self._print_results(results)
        self.results.append(results)
        return results

    def benchmark_writes(self, num_operations: int = 100, doc_size_kb: int = 1) -> Dict[str, Any]:
        """Benchmark write operations"""
        print(f"\n=== Benchmarking Writes ({num_operations} operations, {doc_size_kb}KB docs) ===")

        partition_key = 'benchmark-writes'
        latencies = []
        ru_charges = []

        for i in range(num_operations):
            doc_id = f'write-test-{i}-{int(time.time())}'
            doc = self.generate_test_document(doc_id, partition_key, doc_size_kb)

            start = time.time()
            response = self.container.create_item(doc)
            elapsed = (time.time() - start) * 1000
            latencies.append(elapsed)
            ru_charges.append(float(self.container.client_connection.last_response_headers.get('x-ms-request-charge', 0)))

        results = {
            'operation': 'Write',
            'num_operations': num_operations,
            'doc_size_kb': doc_size_kb,
            'avg_latency_ms': statistics.mean(latencies),
            'p50_latency_ms': statistics.median(latencies),
            'p95_latency_ms': self._percentile(latencies, 95),
            'p99_latency_ms': self._percentile(latencies, 99),
            'min_latency_ms': min(latencies),
            'max_latency_ms': max(latencies),
            'avg_ru': statistics.mean(ru_charges),
            'total_ru': sum(ru_charges),
            'throughput_ops_sec': num_operations / (sum(latencies) / 1000)
        }

        self._print_results(results)
        self.results.append(results)
        return results

    def benchmark_queries(self, num_operations: int = 50) -> Dict[str, Any]:
        """Benchmark query operations"""
        print(f"\n=== Benchmarking Queries ({num_operations} operations) ===")

        partition_key = 'benchmark-query'

        # Create test data
        for i in range(100):
            doc = self.generate_test_document(f'query-test-{i}', partition_key)
            self.container.upsert_item(doc)

        # Benchmark queries
        latencies = []
        ru_charges = []
        result_counts = []

        query = "SELECT * FROM c WHERE c.categoryId = @pk AND c.price > @minPrice"

        for i in range(num_operations):
            min_price = random.uniform(100, 500)
            parameters = [
                {'name': '@pk', 'value': partition_key},
                {'name': '@minPrice', 'value': min_price}
            ]

            start = time.time()
            items = list(self.container.query_items(
                query=query,
                parameters=parameters,
                partition_key=partition_key
            ))
            elapsed = (time.time() - start) * 1000
            latencies.append(elapsed)
            result_counts.append(len(items))
            ru_charges.append(float(self.container.client_connection.last_response_headers.get('x-ms-request-charge', 0)))

        results = {
            'operation': 'Query (single partition)',
            'num_operations': num_operations,
            'avg_results': statistics.mean(result_counts),
            'avg_latency_ms': statistics.mean(latencies),
            'p50_latency_ms': statistics.median(latencies),
            'p95_latency_ms': self._percentile(latencies, 95),
            'p99_latency_ms': self._percentile(latencies, 99),
            'avg_ru': statistics.mean(ru_charges),
            'total_ru': sum(ru_charges)
        }

        self._print_results(results)
        self.results.append(results)
        return results

    def benchmark_cross_partition_queries(self, num_operations: int = 20) -> Dict[str, Any]:
        """Benchmark cross-partition query operations"""
        print(f"\n=== Benchmarking Cross-Partition Queries ({num_operations} operations) ===")

        latencies = []
        ru_charges = []
        result_counts = []

        query = "SELECT * FROM c WHERE c.price > @minPrice"

        for i in range(num_operations):
            min_price = random.uniform(100, 500)
            parameters = [{'name': '@minPrice', 'value': min_price}]

            start = time.time()
            items = list(self.container.query_items(
                query=query,
                parameters=parameters,
                enable_cross_partition_query=True
            ))
            elapsed = (time.time() - start) * 1000
            latencies.append(elapsed)
            result_counts.append(len(items))
            ru_charges.append(float(self.container.client_connection.last_response_headers.get('x-ms-request-charge', 0)))

        results = {
            'operation': 'Query (cross-partition)',
            'num_operations': num_operations,
            'avg_results': statistics.mean(result_counts),
            'avg_latency_ms': statistics.mean(latencies),
            'p50_latency_ms': statistics.median(latencies),
            'p95_latency_ms': self._percentile(latencies, 95),
            'p99_latency_ms': self._percentile(latencies, 99),
            'avg_ru': statistics.mean(ru_charges),
            'total_ru': sum(ru_charges)
        }

        self._print_results(results)
        self.results.append(results)
        return results

    def benchmark_bulk_operations(self, num_operations: int = 1000) -> Dict[str, Any]:
        """Benchmark bulk write operations"""
        print(f"\n=== Benchmarking Bulk Operations ({num_operations} operations) ===")

        partition_key = 'benchmark-bulk'
        documents = [
            self.generate_test_document(f'bulk-test-{i}', partition_key)
            for i in range(num_operations)
        ]

        start = time.time()
        created_count = 0
        total_ru = 0

        for doc in documents:
            try:
                self.container.create_item(doc)
                created_count += 1
                total_ru += float(self.container.client_connection.last_response_headers.get('x-ms-request-charge', 0))
            except Exception as e:
                print(f"Failed to create document: {e}")

        elapsed = time.time() - start

        results = {
            'operation': 'Bulk Write',
            'num_operations': num_operations,
            'successful': created_count,
            'total_time_sec': elapsed,
            'throughput_ops_sec': created_count / elapsed,
            'total_ru': total_ru,
            'avg_ru_per_op': total_ru / created_count if created_count > 0 else 0
        }

        self._print_results(results)
        self.results.append(results)
        return results

    def benchmark_concurrent_operations(self, num_threads: int = 10, ops_per_thread: int = 100) -> Dict[str, Any]:
        """Benchmark concurrent operations"""
        print(f"\n=== Benchmarking Concurrent Operations ({num_threads} threads, {ops_per_thread} ops/thread) ===")

        def write_batch(thread_id: int):
            partition_key = f'benchmark-concurrent-{thread_id}'
            latencies = []

            for i in range(ops_per_thread):
                doc = self.generate_test_document(f'concurrent-{thread_id}-{i}', partition_key)
                start = time.time()
                self.container.create_item(doc)
                latencies.append((time.time() - start) * 1000)

            return latencies

        start = time.time()
        all_latencies = []

        with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(write_batch, i) for i in range(num_threads)]
            for future in concurrent.futures.as_completed(futures):
                all_latencies.extend(future.result())

        elapsed = time.time() - start

        results = {
            'operation': 'Concurrent Write',
            'num_threads': num_threads,
            'ops_per_thread': ops_per_thread,
            'total_operations': num_threads * ops_per_thread,
            'total_time_sec': elapsed,
            'throughput_ops_sec': (num_threads * ops_per_thread) / elapsed,
            'avg_latency_ms': statistics.mean(all_latencies),
            'p95_latency_ms': self._percentile(all_latencies, 95),
            'p99_latency_ms': self._percentile(all_latencies, 99)
        }

        self._print_results(results)
        self.results.append(results)
        return results

    def benchmark_document_sizes(self, sizes_kb: List[int] = [1, 5, 10, 50, 100]) -> Dict[str, Any]:
        """Benchmark operations with different document sizes"""
        print(f"\n=== Benchmarking Document Sizes ===")

        size_results = []

        for size_kb in sizes_kb:
            print(f"\nTesting {size_kb}KB documents...")
            partition_key = f'benchmark-size-{size_kb}'

            # Write test
            write_latencies = []
            write_ru = []

            for i in range(10):
                doc = self.generate_test_document(f'size-test-{size_kb}-{i}', partition_key, size_kb)
                start = time.time()
                self.container.create_item(doc)
                write_latencies.append((time.time() - start) * 1000)
                write_ru.append(float(self.container.client_connection.last_response_headers.get('x-ms-request-charge', 0)))

            # Read test
            read_latencies = []
            read_ru = []

            for i in range(10):
                doc_id = f'size-test-{size_kb}-{i}'
                start = time.time()
                self.container.read_item(doc_id, partition_key)
                read_latencies.append((time.time() - start) * 1000)
                read_ru.append(float(self.container.client_connection.last_response_headers.get('x-ms-request-charge', 0)))

            size_results.append({
                'size_kb': size_kb,
                'write_latency_ms': statistics.mean(write_latencies),
                'write_ru': statistics.mean(write_ru),
                'read_latency_ms': statistics.mean(read_latencies),
                'read_ru': statistics.mean(read_ru)
            })

        # Print comparison
        print(f"\n{'Size (KB)':<12} {'Write Lat (ms)':<18} {'Write RU':<12} {'Read Lat (ms)':<18} {'Read RU':<12}")
        print("-" * 80)
        for result in size_results:
            print(f"{result['size_kb']:<12} {result['write_latency_ms']:<18.2f} "
                  f"{result['write_ru']:<12.2f} {result['read_latency_ms']:<18.2f} {result['read_ru']:<12.2f}")

        return {'operation': 'Document Size Comparison', 'results': size_results}

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile"""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * (percentile / 100))
        return sorted_data[min(index, len(sorted_data) - 1)]

    def _print_results(self, results: Dict[str, Any]):
        """Print benchmark results"""
        print(f"\nResults for {results['operation']}:")
        for key, value in results.items():
            if key != 'operation' and isinstance(value, (int, float)):
                print(f"  {key}: {value:.2f}")

    def run_all_benchmarks(self):
        """Run all benchmarks"""
        print("\n" + "="*80)
        print("COSMOS DB PERFORMANCE BENCHMARKS")
        print("="*80)

        # Run benchmarks
        self.benchmark_point_reads(100)
        self.benchmark_writes(100, doc_size_kb=1)
        self.benchmark_writes(50, doc_size_kb=10)
        self.benchmark_queries(50)
        self.benchmark_cross_partition_queries(20)
        self.benchmark_bulk_operations(1000)
        self.benchmark_concurrent_operations(10, 100)
        self.benchmark_document_sizes([1, 5, 10, 50])

        # Save results
        with open('benchmark_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)

        print("\n" + "="*80)
        print("Benchmarks Complete - Results saved to benchmark_results.json")
        print("="*80)


if __name__ == '__main__':
    endpoint = os.getenv('COSMOS_ENDPOINT', 'https://your-account.documents.azure.com:443/')
    key = os.getenv('COSMOS_KEY', 'your-key')
    database_name = 'ProductCatalog'
    container_name = 'Products'

    benchmark = PerformanceBenchmark(endpoint, key, database_name, container_name)
    benchmark.run_all_benchmarks()
