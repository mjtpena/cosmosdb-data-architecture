# Cosmos DB Partition Key Design Patterns

## Overview
Choosing the right partition key is critical for optimal performance and scalability in Cosmos DB. This document outlines best practices and common patterns.

## Key Principles

### 1. High Cardinality
- Choose a property with many unique values
- Distributes data evenly across partitions
- Avoids hot partitions

### 2. Even Distribution
- Data should be spread uniformly
- Request load should be balanced
- Avoid logical partitions > 20GB

### 3. Query Efficiency
- Most queries should include the partition key
- Cross-partition queries are expensive
- Design for your most common access patterns

## Common Partition Key Patterns

### Pattern 1: Entity ID (e.g., userId, customerId)
```json
{
  "id": "user123",
  "userId": "user123",
  "name": "John Doe",
  "email": "john@example.com"
}
```
**Partition Key**: `/userId`

**Pros**:
- High cardinality
- Point reads are efficient
- Natural grouping of user data

**Cons**:
- Single-tenant queries only
- May create hot partitions for popular users

**Use Cases**: User profiles, customer data, account information

### Pattern 2: Category/Type
```json
{
  "id": "product456",
  "categoryId": "electronics",
  "name": "Laptop",
  "price": 999.99
}
```
**Partition Key**: `/categoryId`

**Pros**:
- Logical grouping
- Efficient category queries
- Good for hierarchical data

**Cons**:
- May have uneven distribution
- Popular categories become hot partitions

**Use Cases**: Product catalogs, content management, taxonomy-based data

### Pattern 3: Composite Key (Synthetic)
```json
{
  "id": "order789",
  "customerId": "cust123",
  "orderDate": "2026-01-15",
  "partitionKey": "cust123-2026-01"
}
```
**Partition Key**: `/partitionKey` (composed of customerId + year-month)

**Pros**:
- Balances distribution and query efficiency
- Time-based queries are efficient
- Prevents single partition growth

**Cons**:
- Additional property to maintain
- Requires application logic to construct

**Use Cases**: Orders, transactions, time-series data

### Pattern 4: Hierarchical Partition Keys (Sub-partitioning)
```json
{
  "id": "analytics001",
  "tenantId": "tenant1",
  "year": "2026",
  "month": "01",
  "metrics": {...}
}
```
**Partition Key**: `/tenantId`, `/year`, `/month`

**Pros**:
- Multi-level distribution
- Efficient range queries
- Better data locality

**Cons**:
- Requires careful planning
- More complex query patterns

**Use Cases**: Multi-tenant applications, analytics, time-series with multiple dimensions

### Pattern 5: Hash-Based Distribution
```json
{
  "id": "event123",
  "eventId": "event123",
  "hash": 42,
  "data": {...}
}
```
**Partition Key**: `/hash` (computed hash value, e.g., hash(eventId) % 100)

**Pros**:
- Guaranteed even distribution
- Prevents hot partitions
- Scales predictably

**Cons**:
- Requires cross-partition queries for single item lookup
- Less intuitive data organization

**Use Cases**: Event sourcing, high-throughput ingestion, queue systems

## Anti-Patterns to Avoid

### 1. Low Cardinality Keys
```json
// BAD: Only a few unique values
{
  "id": "item123",
  "status": "active" // Only 2-3 values possible
}
```
**Problem**: Creates few, large partitions and potential hot spots

### 2. Sequential IDs
```json
// BAD: Sequential values concentrate writes
{
  "id": "order00001",
  "orderId": "order00001", // Sequential
  "timestamp": "2026-01-30T10:00:00Z"
}
```
**Problem**: All writes go to same partition, creating hot partition

### 3. Unbounded Growth
```json
// BAD: Partition can grow indefinitely
{
  "id": "log123",
  "tenantId": "tenant1", // Same tenant forever
  "logEntry": "..."
}
```
**Problem**: Exceeds 20GB logical partition limit

### 4. Using /id as Partition Key
```json
// BAD: Every document in its own partition
{
  "id": "doc123", // Unique per document
  "data": {...}
}
```
**Problem**: Cannot query related documents efficiently, excessive cross-partition queries

## Partition Key Decision Tree

```
Start
  |
  ├─ Multi-tenant application?
  |    YES → Use tenantId (possibly hierarchical)
  |    NO → Continue
  |
  ├─ High write throughput?
  |    YES → Consider hash-based distribution
  |    NO → Continue
  |
  ├─ Time-series data?
  |    YES → Use composite key (entity + time period)
  |    NO → Continue
  |
  ├─ Natural grouping exists?
  |    YES → Use entity ID (userId, customerId)
  |    NO → Consider synthetic key
```

## Performance Considerations

### Request Unit (RU) Impact
- Point reads (with partition key): ~1 RU for 1KB document
- Cross-partition query: 2.5+ RUs per 1KB document
- Single partition query: ~2 RUs per 1KB document

### Throughput Distribution
- Throughput is distributed evenly across physical partitions
- A single partition can use maximum of ~10,000 RU/s
- Design for parallel operations across partitions

### Storage Limits
- Logical partition: 20GB maximum
- Physical partition: 50GB
- Plan for data growth and archival strategy

## Best Practices Checklist

- [ ] Partition key has high cardinality (thousands+ unique values)
- [ ] Data is distributed evenly across partitions
- [ ] Most common queries include the partition key
- [ ] No single partition exceeds 20GB
- [ ] Write operations are distributed across partitions
- [ ] Partition key is immutable (cannot be changed after creation)
- [ ] Time-series data includes time period in partition key
- [ ] Multi-tenant applications use tenantId in partition key
- [ ] Consider future data growth and scaling needs

## Example Scenarios

### E-Commerce Platform
```json
// Orders Container
{
  "id": "order123",
  "customerId": "cust456",
  "orderDate": "2026-01-30",
  "items": [...],
  "total": 299.99
}
```
**Partition Key**: `/customerId`
**Rationale**: Queries typically fetch orders for a specific customer

### IoT Telemetry
```json
// Telemetry Container
{
  "id": "reading001",
  "deviceId": "device789",
  "date": "2026-01-30",
  "partitionKey": "device789-2026-01-30",
  "temperature": 72.5
}
```
**Partition Key**: `/partitionKey` (deviceId + date)
**Rationale**: Distributes data by device and time, prevents unbounded growth

### Social Media Posts
```json
// Posts Container
{
  "id": "post001",
  "userId": "user123",
  "timestamp": "2026-01-30T10:00:00Z",
  "content": "Hello world",
  "likes": 42
}
```
**Partition Key**: `/userId`
**Rationale**: Users typically query their own posts, enables efficient timeline queries

## Additional Resources

- [Azure Cosmos DB Partitioning Documentation](https://docs.microsoft.com/azure/cosmos-db/partitioning-overview)
- [Partition Key Selection Guide](https://docs.microsoft.com/azure/cosmos-db/partition-data)
- [Performance Tips](https://docs.microsoft.com/azure/cosmos-db/performance-tips)
