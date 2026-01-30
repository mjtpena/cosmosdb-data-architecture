# Cosmos DB Denormalization Patterns

## Overview
Unlike relational databases, Cosmos DB benefits from denormalization to optimize for read performance and reduce cross-partition queries. This document covers common denormalization patterns and when to use them.

## Why Denormalize?

### Benefits
1. **Reduced Query Complexity**: Single document contains all needed data
2. **Lower Latency**: No joins or multiple queries required
3. **Better Performance**: Point reads instead of cross-partition queries
4. **Lower Cost**: Fewer RUs consumed per operation

### Trade-offs
1. **Data Duplication**: Same data stored in multiple places
2. **Update Complexity**: Must update multiple documents for consistency
3. **Increased Storage**: Duplicated data consumes more space
4. **Consistency Challenges**: Risk of stale or inconsistent data

## Pattern 1: Embedding Related Data

### One-to-Few Relationships
Embed related entities directly in the parent document.

#### Example: Order with Line Items
```json
{
  "id": "order-123",
  "customerId": "cust-456",
  "orderDate": "2026-01-30T10:00:00Z",
  "status": "shipped",
  "customer": {
    "name": "John Doe",
    "email": "john@example.com",
    "shippingAddress": {
      "street": "123 Main St",
      "city": "Seattle",
      "state": "WA",
      "zip": "98101"
    }
  },
  "items": [
    {
      "productId": "prod-789",
      "productName": "Laptop",
      "sku": "LAP-001",
      "quantity": 1,
      "price": 999.99
    },
    {
      "productId": "prod-790",
      "productName": "Mouse",
      "sku": "MOU-002",
      "quantity": 2,
      "price": 19.99
    }
  ],
  "total": 1039.97
}
```

**When to Use**:
- Child items always queried with parent
- Limited number of child items (< 100)
- Child items rarely updated independently
- Parent and children form a transaction boundary

**Benefits**:
- Single query retrieves entire order
- Atomic operations on order and items
- No cross-partition queries

**Considerations**:
- Document size limit: 2MB
- Update customer info requires updating all orders
- Cannot query items independently

## Pattern 2: Reference Pattern

### One-to-Many with References
Store references (IDs) instead of full objects for large or frequently changing data.

#### Example: Product Reviews
```json
// Product Document
{
  "id": "prod-123",
  "categoryId": "electronics",
  "name": "Laptop",
  "price": 999.99,
  "reviewCount": 42,
  "averageRating": 4.5,
  "recentReviewIds": ["rev-001", "rev-002", "rev-003"]
}

// Review Document (separate container)
{
  "id": "rev-001",
  "productId": "prod-123",
  "userId": "user-456",
  "rating": 5,
  "comment": "Great laptop!",
  "date": "2026-01-30"
}
```

**When to Use**:
- One-to-many relationships with many children
- Child items updated frequently
- Need to query children independently
- Children shared across multiple parents

**Benefits**:
- Smaller parent documents
- Independent updates to reviews
- Can paginate through reviews
- Flexible querying of reviews

**Considerations**:
- Requires multiple queries
- Higher RU consumption
- Need to maintain counts/aggregates manually

## Pattern 3: Hybrid Pattern (Snapshot + Reference)

Combine embedding and referencing for frequently accessed data.

#### Example: Blog Post with Comments
```json
// Post Document
{
  "id": "post-123",
  "userId": "user-456",
  "title": "Introduction to Cosmos DB",
  "content": "...",
  "publishDate": "2026-01-30",
  "stats": {
    "views": 1250,
    "likes": 42,
    "commentCount": 15
  },
  "author": {
    "id": "user-456",
    "name": "Jane Smith",
    "avatar": "https://..."
  },
  "topComments": [
    {
      "id": "comment-001",
      "userId": "user-789",
      "userName": "Bob Johnson",
      "text": "Great article!",
      "likes": 10,
      "date": "2026-01-30T11:00:00Z"
    }
  ],
  "commentIds": ["comment-001", "comment-002", "..."]
}

// Comment Document (separate container for full list)
{
  "id": "comment-001",
  "postId": "post-123",
  "userId": "user-789",
  "text": "Great article!",
  "likes": 10,
  "date": "2026-01-30T11:00:00Z"
}
```

**When to Use**:
- Need quick access to summary data
- Full dataset too large to embed
- Common queries need subset of data
- Want to avoid always loading all data

**Benefits**:
- Fast initial page load (top comments embedded)
- Full data available via additional query
- Flexible querying of all comments
- Optimized for common access patterns

## Pattern 4: Bucketing Pattern

Group related items into buckets to manage document size.

#### Example: User Activity Log
```json
// Activity Bucket Document
{
  "id": "activity-user456-2026-01",
  "userId": "user-456",
  "year": 2026,
  "month": 1,
  "partitionKey": "user-456",
  "activities": [
    {
      "timestamp": "2026-01-30T10:00:00Z",
      "action": "login",
      "ipAddress": "192.168.1.1"
    },
    {
      "timestamp": "2026-01-30T10:05:00Z",
      "action": "view_product",
      "productId": "prod-123"
    }
    // ... more activities for January 2026
  ],
  "count": 150
}
```

**When to Use**:
- Time-series data
- Append-only scenarios
- Many small related items
- Predictable growth patterns

**Benefits**:
- Prevents unbounded document growth
- Efficient time-range queries
- Better partition distribution
- Manageable document sizes

**Considerations**:
- Need strategy for bucket boundaries
- May require multiple document reads for ranges
- Must handle bucket rollovers

## Pattern 5: Aggregation Pattern

Pre-calculate and store aggregates to avoid expensive queries.

#### Example: Product Analytics
```json
{
  "id": "analytics-prod123-2026-01-30",
  "productId": "prod-123",
  "date": "2026-01-30",
  "partitionKey": "prod-123-2026-01",
  "dailyStats": {
    "views": 1500,
    "purchases": 45,
    "conversionRate": 0.03,
    "revenue": 44999.55,
    "averagePrice": 999.99
  },
  "hourlyStats": [
    {
      "hour": 0,
      "views": 50,
      "purchases": 2,
      "revenue": 1999.98
    },
    // ... 24 hours
  ],
  "topReferrers": [
    {"source": "google", "count": 800},
    {"source": "facebook", "count": 400}
  ]
}
```

**When to Use**:
- Complex aggregations on large datasets
- Dashboard and reporting scenarios
- Real-time analytics requirements
- Data updated periodically

**Benefits**:
- Instant query results
- Predictable performance
- Lower RU consumption
- Better user experience

**Considerations**:
- Requires background processing (Change Feed)
- Data may be slightly stale
- Storage overhead for aggregates
- Complexity in maintaining accuracy

## Pattern 6: Materialized Views

Create specialized documents optimized for specific query patterns.

#### Example: Customer 360 View
```json
// Operational Customer Document
{
  "id": "cust-456",
  "userId": "cust-456",
  "name": "John Doe",
  "email": "john@example.com",
  "registrationDate": "2025-01-15"
}

// Materialized View: Customer Summary
{
  "id": "summary-cust-456",
  "customerId": "cust-456",
  "viewType": "customer-summary",
  "partitionKey": "cust-456",
  "profile": {
    "name": "John Doe",
    "email": "john@example.com",
    "tier": "Gold"
  },
  "orderSummary": {
    "totalOrders": 42,
    "totalSpent": 12450.00,
    "averageOrderValue": 296.43,
    "lastOrderDate": "2026-01-28"
  },
  "recentOrders": [
    {
      "orderId": "order-789",
      "date": "2026-01-28",
      "total": 299.99
    }
  ],
  "preferences": {
    "favoriteCategories": ["electronics", "books"],
    "newsletter": true
  },
  "lastUpdated": "2026-01-30T10:00:00Z"
}
```

**When to Use**:
- Complex queries across multiple containers
- Frequently accessed summary data
- Performance-critical read paths
- Dashboard and reporting needs

**Benefits**:
- Optimized for specific queries
- Single query for complex data
- Consistent performance
- Reduced complexity in application

**Considerations**:
- Data duplication
- Must keep views synchronized
- Use Change Feed for updates
- Storage overhead

## Pattern 7: Event Sourcing with Snapshots

Store events with periodic snapshots for efficient state reconstruction.

#### Example: Shopping Cart
```json
// Cart Snapshot (current state)
{
  "id": "cart-user456",
  "userId": "user-456",
  "partitionKey": "user-456",
  "type": "snapshot",
  "items": [
    {
      "productId": "prod-123",
      "quantity": 2,
      "price": 999.99
    }
  ],
  "total": 1999.98,
  "snapshotVersion": 10,
  "lastModified": "2026-01-30T10:00:00Z"
}

// Cart Events
{
  "id": "cart-event-001",
  "cartId": "cart-user456",
  "userId": "user-456",
  "partitionKey": "user-456",
  "type": "event",
  "eventType": "item-added",
  "version": 11,
  "data": {
    "productId": "prod-124",
    "quantity": 1,
    "price": 49.99
  },
  "timestamp": "2026-01-30T10:05:00Z"
}
```

**When to Use**:
- Need complete audit trail
- Temporal queries (state at specific time)
- Complex business logic
- Debugging and analytics

**Benefits**:
- Complete history preserved
- Can replay events
- Snapshots improve read performance
- Flexible querying

## Decision Matrix

| Scenario | Pattern | Reason |
|----------|---------|--------|
| Order with 5-10 line items | Embedding | Small, related data |
| Product with 10,000 reviews | Reference | Too many to embed |
| Blog post with comments | Hybrid | Show top 3, load rest on demand |
| User activity logs | Bucketing | Time-series, manage size |
| Dashboard metrics | Aggregation | Pre-calculate for speed |
| Customer 360 view | Materialized View | Complex cross-container query |
| Audit requirements | Event Sourcing | Need complete history |

## Best Practices

### 1. Start with Query Patterns
- Identify most common queries
- Optimize for read performance
- Consider query frequency vs. update frequency

### 2. Monitor Document Size
- Keep documents under 100KB when possible
- Max size is 2MB
- Use bucketing for large collections

### 3. Use Change Feed for Consistency
```javascript
// Example: Update materialized view on change
changeFeed.on('change', async (changes) => {
  for (const change of changes) {
    await updateMaterializedView(change);
  }
});
```

### 4. Consider Update Patterns
- High read, low write → Embed
- High write → Reference
- Mixed → Hybrid

### 5. Implement Versioning
```json
{
  "id": "doc-123",
  "version": 5,
  "data": {...},
  "_etag": "..."
}
```

### 6. Use TTL for Temporary Data
```json
{
  "id": "session-123",
  "ttl": 3600, // Expire in 1 hour
  "data": {...}
}
```

## Anti-Patterns

### 1. Over-Normalization
```json
// BAD: Too many references
{
  "id": "order-123",
  "customerId": "cust-456",
  "addressId": "addr-789",
  "paymentId": "pay-012"
}
```
**Problem**: Multiple queries for simple operation

### 2. Unbounded Arrays
```json
// BAD: Array grows without limit
{
  "id": "product-123",
  "allReviews": [/* thousands of reviews */]
}
```
**Problem**: Exceeds document size limit, slow queries

### 3. Redundant Denormalization
```json
// BAD: Denormalizing data that never changes together
{
  "id": "order-123",
  "productCatalog": [/* entire product catalog */]
}
```
**Problem**: Unnecessary duplication, difficult to maintain

## Monitoring and Optimization

### Metrics to Track
- Document size distribution
- Query patterns and costs
- Update frequency
- Cross-partition query ratio
- Change feed lag

### Optimization Tools
- Query metrics in portal
- Application Insights
- Cosmos DB diagnostics
- Load testing results

## Resources

- [Azure Cosmos DB Data Modeling](https://docs.microsoft.com/azure/cosmos-db/modeling-data)
- [Partitioning and Horizontal Scaling](https://docs.microsoft.com/azure/cosmos-db/partitioning-overview)
- [Change Feed Documentation](https://docs.microsoft.com/azure/cosmos-db/change-feed)
