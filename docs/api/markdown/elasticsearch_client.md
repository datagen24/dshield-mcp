# elasticsearch_client

Elasticsearch client for querying DShield SIEM events and logs.

Optimized for DShield SIEM integration patterns.

## ElasticsearchClient

Client for interacting with DShield SIEM Elasticsearch.

#### __init__

```python
def __init__(self, error_handler)
```

Initialize the Elasticsearch client.

        Sets up the client connection, field mappings, and configuration
        for DShield SIEM integration.

        Args:
            error_handler: Optional MCPErrorHandler instance for proper error handling

        New config option:
            - 'compatibility_mode' (bool, default: false):
                If true, sets compatibility_mode=True on the Elasticsearch Python client (for ES 8.x servers).

#### _check_circuit_breaker

```python
def _check_circuit_breaker(self, operation)
```

Check if circuit breaker allows the operation.

        Args:
            operation: Name of the operation being performed

        Returns:
            True if operation is allowed, False if circuit breaker is open

        Raises:
            Exception: If circuit breaker is open with detailed error message

#### _record_circuit_breaker_success

```python
def _record_circuit_breaker_success(self)
```

Record successful operation with circuit breaker.

#### _record_circuit_breaker_failure

```python
def _record_circuit_breaker_failure(self, exception)
```

Record failed operation with circuit breaker.

#### get_circuit_breaker_status

```python
def get_circuit_breaker_status(self)
```

Get the current status of the Elasticsearch circuit breaker.

        Returns:
            Circuit breaker status dictionary or None if not enabled

#### _optimize_fields

```python
def _optimize_fields(self, fields)
```

Optimize field selection for better performance.

        Analyzes the requested fields and optimizes the selection
        to improve query performance while maintaining data quality.
        This includes removing redundant fields and adding essential
        fields that are needed for proper event parsing.

        Args:
            fields: List of requested fields

        Returns:
            Optimized list of fields for the query

#### _build_dshield_query

```python
def _build_dshield_query(self, start_time, end_time, filters)
```

Build Elasticsearch query for DShield events.

        Constructs a standardized Elasticsearch query for DShield
        security events with proper time range filtering and
        additional filter criteria.

        Args:
            start_time: Start time for the query range
            end_time: End time for the query range
            filters: Additional filter criteria to apply

        Returns:
            Dictionary containing the complete Elasticsearch query

        Raises:
            ValueError: If time range is invalid

#### _build_ip_query

```python
def _build_ip_query(self, ip_addresses, start_time, end_time)
```

Build Elasticsearch query for IP-specific events.

        Constructs a query that matches events where the specified
        IP addresses appear as either source or destination IPs.

        Args:
            ip_addresses: List of IP addresses to search for
            start_time: Start time for the query range
            end_time: End time for the query range

        Returns:
            Dictionary containing the complete Elasticsearch query

        Raises:
            ValueError: If time range is invalid or IP list is empty

#### _parse_dshield_event

```python
def _parse_dshield_event(self, hit, indices)
```

Parse Elasticsearch hit into standardized DShield event.

        Converts raw Elasticsearch document into a standardized
        DShield event format with proper field mapping and
        data normalization.

        Args:
            hit: Raw Elasticsearch hit document
            indices: List of indices the hit came from (for context)

        Returns:
            Standardized DShield event dictionary or None if parsing fails

        Raises:
            KeyError: If required fields are missing
            ValueError: If timestamp parsing fails

#### _extract_field_mapped

```python
def _extract_field_mapped(self, source, field_type, default)
```

Extract field value using DShield field mappings.

        Supports dot notation for both top-level and nested fields. Attempts to map the requested field type
        to the correct field in the source document using the DShield field mapping configuration.

        Args:
            source: Source dictionary from Elasticsearch document
            field_type: Logical DShield field type to extract (e.g., 'source_ip', 'event_type')
            default: Default value to return if field is not found

        Returns:
            The extracted value if found, otherwise the default value

#### log_unmapped_fields

```python
def log_unmapped_fields(self, source)
```

Log any fields in the source document that are not mapped to any known field type.

        Args:
            source: Source dictionary from Elasticsearch document

        Returns:
            None

#### _compile_geo_stats

```python
def _compile_geo_stats(self, geo_data)
```

Compile geographic statistics from geo data.

        Aggregates event counts by country from a list of geo-tagged events.

        Args:
            geo_data: List of event dictionaries containing 'country' keys

        Returns:
            Dictionary mapping country names to event counts

#### _generate_pagination_info

```python
def _generate_pagination_info(self, page, page_size, total_count)
```

Generate pagination information for response.

        Args:
            page: Current page number
            page_size: Number of results per page
            total_count: Total number of results available

        Returns:
            Dictionary containing pagination metadata, including current page, total pages, and navigation info

#### _generate_enhanced_pagination_info

```python
def _generate_enhanced_pagination_info(self, page, page_size, total_count, cursor, next_cursor, sort_by, sort_order)
```

Generate enhanced pagination information for response.

        Provides comprehensive pagination details including cursor tokens,
        total available count, and sorting information for massive datasets.
        Supports both traditional page-based and cursor-based pagination.

        Args:
            page: Current page number
            page_size: Number of results per page
            total_count: Total number of results available
            cursor: Current cursor token for cursor-based pagination
            next_cursor: Next cursor token for continuing pagination
            sort_by: Field used for sorting
            sort_order: Sort order ('asc' or 'desc')

        Returns:
            Dictionary containing comprehensive pagination metadata

#### _map_query_fields

```python
def _map_query_fields(self, filters)
```

Map user-friendly field names to ECS dot notation for querying.

        This handles the mismatch between display fields (source_ip) and
        query fields (source.ip) as described in GitHub issue #17.
        Converts user-friendly field names to the proper Elasticsearch
        Common Schema (ECS) field names for querying.

        Args:
            filters: Dictionary containing user-friendly field names and values

        Returns:
            Dictionary with field names mapped to ECS notation

        Raises:
            ValueError: If field mapping is invalid

#### _get_field_suggestions

```python
def _get_field_suggestions(self, field_name)
```

Get suggestions for field name alternatives.

        Provides alternative field names when a user-friendly field name
        is not found in the mapping. This helps users understand the
        correct ECS field names to use.

        Args:
            field_name: The field name that needs alternatives

        Returns:
            List of suggested field name alternatives

#### _generate_session_key

```python
def _generate_session_key(self, event, session_fields)
```

Generate a session key from event data using specified session fields.

        Creates a unique session identifier by combining values from
        specified session fields. This is used for grouping related
        events together in session-based streaming.

        Args:
            event: The event data dictionary
            session_fields: List of fields to use for session grouping

        Returns:
            Session key string or None if no session fields are available

#### _calculate_session_duration

```python
def _calculate_session_duration(self, first_timestamp, last_timestamp)
```

Calculate session duration in minutes.

        Computes the duration between the first and last events in a session.
        This is used for session analysis and reporting.

        Args:
            first_timestamp: First event timestamp in ISO format
            last_timestamp: Last event timestamp in ISO format

        Returns:
            Duration in minutes or None if timestamps are invalid

        Raises:
            ValueError: If timestamp format is invalid

#### _get_current_time

```python
def _get_current_time(self)
```

Get current UTC time.

        Returns:
            Current UTC datetime

#### _get_timestamp_for_query

```python
def _get_timestamp_for_query(self)
```

Get current timestamp in ISO format for queries.

        Returns:
            Current timestamp in ISO format

#### _get_timestamp_for_logging

```python
def _get_timestamp_for_logging(self)
```

Get current timestamp in ISO format for logging.

        Returns:
            Current timestamp in ISO format

#### _get_timestamp_for_metrics

```python
def _get_timestamp_for_metrics(self)
```

Get current timestamp in ISO format for metrics.

        Returns:
            Current timestamp in ISO format

#### _get_timestamp_for_cache

```python
def _get_timestamp_for_cache(self)
```

Get current UTC time for cache operations.

        Returns:
            Current UTC datetime

#### _get_timestamp_for_session

```python
def _get_timestamp_for_session(self)
```

Get current UTC time for session operations.

        Returns:
            Current UTC datetime
