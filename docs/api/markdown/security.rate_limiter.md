# rate_limiter

Rate limiting system for API keys and connections.

This module provides comprehensive rate limiting functionality to prevent
abuse and ensure fair resource usage across all API keys and connections.

## RateLimiter

Token bucket rate limiter for API keys and connections.

#### __init__

```python
def __init__(self, requests_per_minute, burst_size)
```

Initialize the rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute
            burst_size: Maximum burst size (defaults to requests_per_minute)

## SlidingWindowRateLimiter

Sliding window rate limiter for more precise rate limiting.

#### __init__

```python
def __init__(self, requests_per_minute, window_size)
```

Initialize the sliding window rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute
            window_size: Window size in seconds

## APIKeyRateLimiter

Rate limiter for individual API keys.

#### __init__

```python
def __init__(self)
```

Initialize the API key rate limiter.

## ConnectionRateLimiter

Rate limiter for individual connections.

#### __init__

```python
def __init__(self)
```

Initialize the connection rate limiter.

## GlobalRateLimiter

Global rate limiter for the entire server.

#### __init__

```python
def __init__(self, max_requests_per_minute)
```

Initialize the global rate limiter.

        Args:
            max_requests_per_minute: Maximum total requests per minute
