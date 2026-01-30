"""
Cosmos DB Data Migration Tool
Migrate data between containers, databases, or accounts
"""

import os
import json
import time
from typing import Dict, Any, List, Optional
from azure.cosmos import CosmosClient, PartitionKey
import concurrent.futures
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CosmosDBMigrationTool:
    """Tool for migrating data in Cosmos DB"""

    def __init__(self):
        self.stats = {
            'total_documents': 0,
            'migrated': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': None,
            'end_time': None
        }

    def migrate_container(
        self,
        source_endpoint: str,
        source_key: str,
        source_database: str,
        source_container: str,
        target_endpoint: str,
        target_key: str,
        target_database: str,
        target_container: str,
        batch_size: int = 100,
        max_workers: int = 5,
        transform_func: Optional[callable] = None
    ):
        """
        Migrate all documents from source container to target container

        Args:
            source_endpoint: Source Cosmos DB endpoint
            source_key: Source Cosmos DB key
            source_database: Source database name
            source_container: Source container name
            target_endpoint: Target Cosmos DB endpoint
            target_key: Target Cosmos DB key
            target_database: Target database name
            target_container: Target container name
            batch_size: Number of documents per batch
            max_workers: Number of parallel workers
            transform_func: Optional function to transform documents during migration
        """
        self.stats['start_time'] = datetime.now()
        logger.info(f"Starting migration from {source_container} to {target_container}")

        # Initialize clients
        source_client = CosmosClient(source_endpoint, source_key)
        target_client = CosmosClient(target_endpoint, target_key)

        source_db = source_client.get_database_client(source_database)
        target_db = target_client.get_database_client(target_database)

        source_cont = source_db.get_container_client(source_container)
        target_cont = target_db.get_container_client(target_container)

        # Query all documents from source
        query = "SELECT * FROM c"
        items = list(source_cont.query_items(
            query=query,
            enable_cross_partition_query=True
        ))

        self.stats['total_documents'] = len(items)
        logger.info(f"Found {self.stats['total_documents']} documents to migrate")

        # Migrate in batches
        batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []

            for batch in batches:
                future = executor.submit(
                    self._migrate_batch,
                    target_cont,
                    batch,
                    transform_func
                )
                futures.append(future)

            # Wait for all batches to complete
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Batch migration failed: {e}")

        self.stats['end_time'] = datetime.now()
        self._print_stats()

    def _migrate_batch(
        self,
        target_container,
        documents: List[Dict[str, Any]],
        transform_func: Optional[callable]
    ):
        """Migrate a batch of documents"""
        for doc in documents:
            try:
                # Transform document if function provided
                if transform_func:
                    doc = transform_func(doc)

                # Upsert to target
                target_container.upsert_item(doc)
                self.stats['migrated'] += 1

                if self.stats['migrated'] % 100 == 0:
                    logger.info(f"Migrated {self.stats['migrated']}/{self.stats['total_documents']} documents")

            except Exception as e:
                logger.error(f"Failed to migrate document {doc.get('id')}: {e}")
                self.stats['failed'] += 1

    def migrate_with_change_feed(
        self,
        source_endpoint: str,
        source_key: str,
        source_database: str,
        source_container: str,
        target_endpoint: str,
        target_key: str,
        target_database: str,
        target_container: str,
        transform_func: Optional[callable] = None
    ):
        """
        Continuous migration using change feed
        Monitors source container and replicates changes to target
        """
        logger.info("Starting continuous migration with change feed")

        # Initialize clients
        source_client = CosmosClient(source_endpoint, source_key)
        target_client = CosmosClient(target_endpoint, target_key)

        source_db = source_client.get_database_client(source_database)
        target_db = target_client.get_database_client(target_database)

        source_cont = source_db.get_container_client(source_container)
        target_cont = target_db.get_container_client(target_container)

        # Read change feed
        change_feed_iterator = source_cont.query_items_change_feed(
            start_time='Beginning'
        )

        for changes in change_feed_iterator:
            if not changes:
                logger.info("No more changes, waiting...")
                time.sleep(5)
                continue

            logger.info(f"Processing {len(changes)} changes")

            for change in changes:
                try:
                    # Transform if needed
                    if transform_func:
                        change = transform_func(change)

                    # Replicate to target
                    target_cont.upsert_item(change)
                    self.stats['migrated'] += 1

                except Exception as e:
                    logger.error(f"Failed to replicate change: {e}")
                    self.stats['failed'] += 1

    def export_to_json(
        self,
        endpoint: str,
        key: str,
        database: str,
        container: str,
        output_file: str,
        query: Optional[str] = None
    ):
        """
        Export container data to JSON file

        Args:
            endpoint: Cosmos DB endpoint
            key: Cosmos DB key
            database: Database name
            container: Container name
            output_file: Output JSON file path
            query: Optional SQL query to filter documents
        """
        logger.info(f"Exporting {container} to {output_file}")

        client = CosmosClient(endpoint, key)
        db = client.get_database_client(database)
        cont = db.get_container_client(container)

        # Query documents
        query = query or "SELECT * FROM c"
        items = list(cont.query_items(
            query=query,
            enable_cross_partition_query=True
        ))

        # Write to file
        with open(output_file, 'w') as f:
            json.dump(items, f, indent=2, default=str)

        logger.info(f"Exported {len(items)} documents to {output_file}")

    def import_from_json(
        self,
        endpoint: str,
        key: str,
        database: str,
        container: str,
        input_file: str,
        batch_size: int = 100
    ):
        """
        Import data from JSON file to container

        Args:
            endpoint: Cosmos DB endpoint
            key: Cosmos DB key
            database: Database name
            container: Container name
            input_file: Input JSON file path
            batch_size: Batch size for import
        """
        logger.info(f"Importing from {input_file} to {container}")

        client = CosmosClient(endpoint, key)
        db = client.get_database_client(database)
        cont = db.get_container_client(container)

        # Read from file
        with open(input_file, 'r') as f:
            items = json.load(f)

        self.stats['total_documents'] = len(items)
        logger.info(f"Found {self.stats['total_documents']} documents to import")

        # Import in batches
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]

            for item in batch:
                try:
                    cont.upsert_item(item)
                    self.stats['migrated'] += 1
                except Exception as e:
                    logger.error(f"Failed to import document: {e}")
                    self.stats['failed'] += 1

            logger.info(f"Imported {self.stats['migrated']}/{self.stats['total_documents']} documents")

        logger.info("Import complete")

    def _print_stats(self):
        """Print migration statistics"""
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()

        logger.info("\n" + "="*60)
        logger.info("MIGRATION STATISTICS")
        logger.info("="*60)
        logger.info(f"Total documents: {self.stats['total_documents']}")
        logger.info(f"Migrated: {self.stats['migrated']}")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Skipped: {self.stats['skipped']}")
        logger.info(f"Duration: {duration:.2f} seconds")
        logger.info(f"Throughput: {self.stats['migrated']/duration:.2f} docs/sec")
        logger.info("="*60)


# Example transformation functions

def transform_rename_field(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Example: Rename a field"""
    if 'oldFieldName' in doc:
        doc['newFieldName'] = doc.pop('oldFieldName')
    return doc


def transform_add_field(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Example: Add a new field"""
    doc['migrationDate'] = datetime.now().isoformat()
    doc['version'] = 2
    return doc


def transform_partition_key(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Example: Change partition key structure"""
    if 'customerId' in doc and 'year' in doc:
        doc['partitionKey'] = f"{doc['customerId']}-{doc['year']}"
    return doc


def transform_denormalize(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Example: Denormalize related data"""
    # Add embedded customer info
    doc['customerInfo'] = {
        'name': doc.get('customerName'),
        'email': doc.get('customerEmail')
    }
    return doc


# CLI interface
def main():
    """Main function for CLI usage"""
    import argparse

    parser = argparse.ArgumentParser(description='Cosmos DB Migration Tool')
    parser.add_argument('command', choices=['migrate', 'export', 'import', 'sync'])
    parser.add_argument('--source-endpoint', help='Source Cosmos DB endpoint')
    parser.add_argument('--source-key', help='Source Cosmos DB key')
    parser.add_argument('--source-database', help='Source database name')
    parser.add_argument('--source-container', help='Source container name')
    parser.add_argument('--target-endpoint', help='Target Cosmos DB endpoint')
    parser.add_argument('--target-key', help='Target Cosmos DB key')
    parser.add_argument('--target-database', help='Target database name')
    parser.add_argument('--target-container', help='Target container name')
    parser.add_argument('--file', help='JSON file for import/export')
    parser.add_argument('--batch-size', type=int, default=100, help='Batch size')
    parser.add_argument('--workers', type=int, default=5, help='Number of parallel workers')

    args = parser.parse_args()

    tool = CosmosDBMigrationTool()

    if args.command == 'migrate':
        tool.migrate_container(
            args.source_endpoint,
            args.source_key,
            args.source_database,
            args.source_container,
            args.target_endpoint,
            args.target_key,
            args.target_database,
            args.target_container,
            batch_size=args.batch_size,
            max_workers=args.workers
        )

    elif args.command == 'export':
        tool.export_to_json(
            args.source_endpoint,
            args.source_key,
            args.source_database,
            args.source_container,
            args.file
        )

    elif args.command == 'import':
        tool.import_from_json(
            args.target_endpoint,
            args.target_key,
            args.target_database,
            args.target_container,
            args.file,
            batch_size=args.batch_size
        )

    elif args.command == 'sync':
        tool.migrate_with_change_feed(
            args.source_endpoint,
            args.source_key,
            args.source_database,
            args.source_container,
            args.target_endpoint,
            args.target_key,
            args.target_database,
            args.target_container
        )


if __name__ == '__main__':
    main()
