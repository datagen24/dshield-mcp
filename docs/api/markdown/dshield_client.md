# dshield_client

DShield client for threat intelligence and IP reputation lookup.

This module provides a client for interacting with the DShield threat intelligence API.
It supports IP reputation lookups, attack summaries, batch enrichment, and detailed
IP information retrieval. The client handles authentication, rate limiting, caching,
and error handling for robust integration with DShield services.

Features:
- IP reputation and details lookup
- Attack summary retrieval
- Batch enrichment of IPs
- Caching and rate limiting
- Async context management

Example:
    >>> from src.dshield_client import DShieldClient
    >>> async with DShieldClient() as client:
    ...     rep = await client.get_ip_reputation("8.8.8.8")
    ...     print(rep)

## DShieldClient

Client for interacting with DShield threat intelligence API.

    This class provides methods to query DShield for IP reputation, details,
    attack summaries, and batch enrichment. It manages authentication, rate
    limiting, caching, and session lifecycle for efficient API usage.

    Attributes:
        api_key: API key for DShield authentication
        base_url: Base URL for DShield API
        session: aiohttp.ClientSession for HTTP requests
        rate_limit_requests: Max requests per minute
        rate_limit_window: Time window for rate limiting (seconds)
        request_times: List of request timestamps for rate limiting
        cache: In-memory cache for API responses
        cache_ttl: Time-to-live for cache entries (seconds)
        enable_caching: Whether caching is enabled
        max_cache_size: Maximum cache size
        request_timeout: Timeout for API requests (seconds)
        enable_performance_logging: Whether to log performance metrics
        headers: HTTP headers for API requests
        batch_size: Maximum batch size for IP enrichment

    Example:
        >>> async with DShieldClient() as client:
        ...     rep = await client.get_ip_reputation("8.8.8.8")
        ...     print(rep)

#### __init__

```python
def __init__(self, error_handler)
```

Initialize the DShield client.

        Loads configuration, resolves secrets, sets up rate limiting,
        caching, and prepares HTTP headers for API requests.

        Args:
            error_handler: Optional MCPErrorHandler for structured error responses

        Raises:
            RuntimeError: If configuration or secret resolution fails

#### _check_circuit_breaker

```python
def _check_circuit_breaker(self, operation)
```

Check if circuit breaker allows execution.

        Args:
            operation: Name of the operation being performed

        Returns:
            True if execution is allowed, False if circuit breaker is open

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

        Args:
            exception: The exception that occurred

#### get_circuit_breaker_status

```python
def get_circuit_breaker_status(self)
```

Get the current status of the DShield API circuit breaker.

        Returns:
            Circuit breaker status dictionary or None if not enabled

#### _parse_ip_reputation

```python
def _parse_ip_reputation(self, data, ip_address)
```

Parse DShield IP reputation response.

#### _parse_ip_details

```python
def _parse_ip_details(self, data, ip_address)
```

Parse DShield IP details response.

#### _parse_top_attackers

```python
def _parse_top_attackers(self, data)
```

Parse DShield top attackers response.

#### _parse_attack_summary

```python
def _parse_attack_summary(self, data)
```

Parse DShield attack summary response.

#### _create_default_reputation

```python
def _create_default_reputation(self, ip_address)
```

Create default reputation data for IP.

#### _create_default_details

```python
def _create_default_details(self, ip_address)
```

Create default details data for IP.

#### _create_default_summary

```python
def _create_default_summary(self)
```

Create default attack summary.

#### _get_cached_data

```python
def _get_cached_data(self, cache_key)
```

Get data from cache if not expired.

#### _cache_data

```python
def _cache_data(self, cache_key, data)
```

Cache data with timestamp.
