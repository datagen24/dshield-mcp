# Query Performance Metrics Implementation

## Overview
This document describes the implementation of query performance metrics in the DShield MCP backend. These metrics provide essential visibility into query execution, backend optimizations, and data access patterns.

## Metrics Tracked
- **query_time_ms**: Total time spent executing the query (milliseconds)
- **optimization_applied**: List of optimizations used (e.g., pagination, field_selection, cursor_pagination, aggregation)
- **indices_scanned**: Number of indices included in the query
- **total_documents_examined**: Number of documents scanned by Elasticsearch
- **query_complexity**: Heuristic label (simple, moderate, complex, aggregation)
- **cache_hit**: Whether the query was served from cache (future use)
- **shards_scanned**: Number of shards involved in the query
- **aggregations_used**: Whether aggregations were used

## Where Metrics Appear
- **pagination_metadata**: Included in all paginated query responses
- **aggregation responses**: Included in aggregation result objects

## Example (Paginated Query)
```json
{
  "pagination_metadata": {
    "page_size": 100,
    "page_number": 1,
    "total_available": 10000,
    "has_more": true,
    "sort_by": "@timestamp",
    "sort_order": "desc",
    "query_time_ms": 42,
    "indices_scanned": 17,
    "total_documents_examined": 10000,
    "query_complexity": "simple",
    "optimization_applied": ["page_pagination"]
  },
  "events": [ ... ]
}
```

## Example (Aggregation Query)
```json
{
  "aggregations": { ... },
  "performance_metrics": {
    "query_time_ms": 15,
    "indices_scanned": 17,
    "total_documents_examined": 10000,
    "query_complexity": "aggregation",
    "optimization_applied": ["aggregation"],
    "aggregations_used": true
  }
}
```

## Usage
- Metrics are automatically included in all relevant API responses.
- No client changes are required to receive metrics.
- Use these metrics to monitor backend performance, debug slow queries, and validate optimization effectiveness.

## Implementation Notes
- Metrics are tracked in `src/elasticsearch_client.py` and attached to the response in `_generate_enhanced_pagination_info` and `execute_aggregation_query`.
- The structure is extensible for future metrics (e.g., cache hits, network time). 