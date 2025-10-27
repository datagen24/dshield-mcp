# threat_intelligence_manager

Threat Intelligence Manager for DShield MCP.

This module provides a centralized manager for coordinating multiple threat intelligence
sources including DShield, VirusTotal, Shodan, and other security APIs. It handles
source coordination, rate limiting, caching, and result correlation.

Features:
- Multi-source threat intelligence aggregation
- Intelligent correlation and scoring
- Advanced caching with configurable TTL
- Rate limiting and error handling
- Extensible architecture for new sources

Example:
    >>> from src.threat_intelligence_manager import ThreatIntelligenceManager
    >>> async with ThreatIntelligenceManager() as manager:
    ...     result = await manager.enrich_ip_comprehensive("8.8.8.8")
    ...     print(result.overall_threat_score)

## ThreatIntelligenceManager

Manages multiple threat intelligence sources and correlation.

    This class provides a unified interface for querying multiple threat intelligence
    sources, aggregating results, and providing comprehensive threat assessments.
    It handles rate limiting, caching, error handling, and result correlation.

    Attributes:
        config: Application configuration
        user_config: User-specific configuration
        clients: Dictionary of source clients
        correlation_config: Correlation settings
        confidence_threshold: Minimum confidence threshold
        max_sources: Maximum sources per query
        cache: In-memory cache for results
        cache_ttl: Cache time-to-live
        rate_limit_trackers: Rate limiting trackers per source

    Example:
        >>> async with ThreatIntelligenceManager() as manager:
        ...     result = await manager.enrich_ip_comprehensive("8.8.8.8")
        ...     print(f"Threat score: {result.overall_threat_score}")

#### __init__

```python
def __init__(self)
```

Initialize the threat intelligence manager.

        Loads configuration, initializes source clients, and sets up
        correlation and caching parameters.

        Raises:
            RuntimeError: If configuration loading fails

#### _initialize_clients

```python
def _initialize_clients(self)
```

Initialize threat intelligence source clients.

#### _initialize_sqlite_cache

```python
def _initialize_sqlite_cache(self)
```

Initialize SQLite cache database.

        Creates the database file and tables if they don't exist.
        Sets up proper indexes for efficient querying.

#### _initialize_rate_limit_trackers

```python
def _initialize_rate_limit_trackers(self)
```

Initialize rate limiting trackers and concurrency controls for each source.

#### _deduplicate_indicators

```python
def _deduplicate_indicators(self, indicators)
```

Remove duplicate indicators and merge metadata.

        Args:
            indicators: List of raw indicators

        Returns:
            List of deduplicated indicators with metadata

#### _classify_indicator

```python
def _classify_indicator(self, indicator)
```

Classify the type of indicator.

        Args:
            indicator: The indicator string

        Returns:
            The indicator type classification

#### _aggregate_geographic_data

```python
def _aggregate_geographic_data(self, result)
```

Aggregate geographic data from multiple sources.

        Args:
            result: The threat intelligence result to update

#### _aggregate_network_data

```python
def _aggregate_network_data(self, result)
```

Aggregate network data from multiple sources.

        Args:
            result: The threat intelligence result to update

#### _determine_timestamps

```python
def _determine_timestamps(self, result)
```

Determine first and last seen timestamps across sources.

        Args:
            result: The threat intelligence result to update

#### _get_cached_result

```python
def _get_cached_result(self, cache_key)
```

Get cached result if available and not expired.

        Args:
            cache_key: The cache key to look up

        Returns:
            Cached result if available and valid, None otherwise

#### _cache_result

```python
def _cache_result(self, cache_key, result)
```

Cache a result.

        Args:
            cache_key: The cache key
            result: The result to cache

#### _get_cached_domain_result

```python
def _get_cached_domain_result(self, cache_key)
```

Get cached domain result if available and not expired.

        Args:
            cache_key: The cache key to look up

        Returns:
            Cached domain result if available and valid, None otherwise

#### _cache_domain_result

```python
def _cache_domain_result(self, cache_key, result)
```

Cache a domain result.

        Args:
            cache_key: The cache key
            result: The domain result to cache

#### _cache_result_to_sqlite

```python
def _cache_result_to_sqlite(self, cache_key, result)
```

Cache a result to SQLite.

        Args:
            cache_key: The cache key
            result: The result to cache

#### _cleanup_sqlite_cache

```python
def _cleanup_sqlite_cache(self)
```

Clean up expired entries from SQLite cache.

#### get_available_sources

```python
def get_available_sources(self)
```

Get list of available threat intelligence sources.

        Returns:
            List of available sources

#### get_source_status

```python
def get_source_status(self)
```

Get status of all threat intelligence sources.

        Returns:
            Dictionary containing source status information

#### get_cache_statistics

```python
def get_cache_statistics(self)
```

Get cache statistics for both memory and SQLite caches.

        Returns:
            Dictionary containing cache statistics

#### _initialize_elasticsearch

```python
def _initialize_elasticsearch(self)
```

Initialize Elasticsearch client for enrichment writeback if enabled in config.

#### _aggregate_geographic_data_advanced

```python
def _aggregate_geographic_data_advanced(self, result)
```

Aggregate geographic data with confidence weighting and conflict resolution.

        Args:
            result: The threat intelligence result to update

#### _aggregate_network_data_advanced

```python
def _aggregate_network_data_advanced(self, result)
```

Aggregate network data with confidence weighting and conflict resolution.

        Args:
            result: The threat intelligence result to update

#### _determine_timestamps_advanced

```python
def _determine_timestamps_advanced(self, result)
```

Determine timestamps with temporal correlation and source weighting.

        Args:
            result: The threat intelligence result to update

#### _calculate_correlation_metrics

```python
def _calculate_correlation_metrics(self, result)
```

Calculate correlation metrics and quality indicators.

        Args:
            result: The threat intelligence result to update
