# tcp_security

TCP security module for DShield MCP Server.

This module provides security measures for TCP transport, including
rate limiting, input validation, and abuse detection.

## SecurityViolation

Exception raised for security violations.

    Attributes:
        violation_type: Type of security violation
        message: Violation message
        details: Additional violation details

#### __init__

```python
def __init__(self, violation_type, message, details)
```

Initialize security violation.

        Args:
            violation_type: Type of security violation
            message: Violation message
            details: Additional violation details

## RateLimiter

Advanced rate limiter with multiple strategies.

    Implements token bucket, sliding window, and adaptive rate limiting
    for different types of operations and clients.

#### __init__

```python
def __init__(self, requests_per_minute, burst_limit, window_size, adaptive)
```

Initialize the rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute
            burst_limit: Maximum burst requests
            window_size: Time window size in seconds
            adaptive: Whether to use adaptive rate limiting

#### is_allowed

```python
def is_allowed(self, client_id)
```

Check if a request is allowed.

        Args:
            client_id: Client identifier for tracking

        Returns:
            True if request is allowed, False if rate limited

#### _check_token_bucket

```python
def _check_token_bucket(self, now)
```

Check token bucket rate limiting.

        Args:
            now: Current timestamp

        Returns:
            True if tokens available, False otherwise

#### _check_sliding_window

```python
def _check_sliding_window(self, now)
```

Check sliding window rate limiting.

        Args:
            now: Current timestamp

        Returns:
            True if within window limits, False otherwise

#### _update_adaptive_limits

```python
def _update_adaptive_limits(self, now)
```

Update adaptive rate limits based on recent violations.

        Args:
            now: Current timestamp

#### record_violation

```python
def record_violation(self)
```

Record a rate limit violation.

## InputValidator

Validates and sanitizes input for TCP connections.

    Provides comprehensive input validation for MCP messages,
    preventing injection attacks and malformed requests.

#### __init__

```python
def __init__(self, config)
```

Initialize the input validator.

        Args:
            config: Validation configuration

#### validate_message

```python
def validate_message(self, message)
```

Validate an MCP message.

        Args:
            message: Message to validate

        Returns:
            Validated and sanitized message

        Raises:
            SecurityViolation: If message validation fails

#### _validate_json_rpc_structure

```python
def _validate_json_rpc_structure(self, message)
```

Validate JSON-RPC 2.0 structure.

        Args:
            message: Message to validate

        Raises:
            SecurityViolation: If structure is invalid

#### _validate_method

```python
def _validate_method(self, method)
```

Validate method name.

        Args:
            method: Method name to validate

        Raises:
            SecurityViolation: If method is invalid

#### _validate_params

```python
def _validate_params(self, params)
```

Validate parameters.

        Args:
            params: Parameters to validate

        Raises:
            SecurityViolation: If parameters are invalid

#### _validate_object_params

```python
def _validate_object_params(self, params)
```

Validate object parameters.

        Args:
            params: Object parameters to validate

        Raises:
            SecurityViolation: If parameters are invalid

#### _validate_array_params

```python
def _validate_array_params(self, params)
```

Validate array parameters.

        Args:
            params: Array parameters to validate

        Raises:
            SecurityViolation: If parameters are invalid

#### _validate_param_value

```python
def _validate_param_value(self, value, path)
```

Validate a parameter value.

        Args:
            value: Value to validate
            path: Path to the value for error reporting

        Raises:
            SecurityViolation: If value is invalid

#### _validate_id

```python
def _validate_id(self, id_value)
```

Validate JSON-RPC ID.

        Args:
            id_value: ID value to validate

        Raises:
            SecurityViolation: If ID is invalid

## TCPSecurityManager

Manages security for TCP connections.

    Provides comprehensive security measures including rate limiting,
    input validation, abuse detection, and connection monitoring.

#### __init__

```python
def __init__(self, config)
```

Initialize the TCP security manager.

        Args:
            config: Security configuration

#### validate_message

```python
def validate_message(self, message, client_id)
```

Validate a message from a client.

        Args:
            message: Message to validate
            client_id: Client identifier

        Returns:
            Validated message

        Raises:
            SecurityViolation: If validation fails

#### _is_client_blocked

```python
def _is_client_blocked(self, client_id)
```

Check if a client is currently blocked.

        Args:
            client_id: Client identifier

        Returns:
            True if client is blocked, False otherwise

#### _check_rate_limits

```python
def _check_rate_limits(self, client_id)
```

Check rate limits for a client.

        Args:
            client_id: Client identifier

        Returns:
            True if within rate limits, False otherwise

#### _record_violation

```python
def _record_violation(self, client_id, violation_type)
```

Record a security violation for a client.

        Args:
            client_id: Client identifier
            violation_type: Type of violation

#### _block_client

```python
def _block_client(self, client_id, violation_type)
```

Block a client due to security violations.

        Args:
            client_id: Client identifier
            violation_type: Type of violation that triggered the block

#### _unblock_client

```python
def _unblock_client(self, client_id)
```

Unblock a client after block period expires.

        Args:
            client_id: Client identifier

#### record_connection_attempt

```python
def record_connection_attempt(self, client_id)
```

Record a connection attempt and check if it should be allowed.

        Args:
            client_id: Client identifier

        Returns:
            True if connection should be allowed, False otherwise

#### get_security_statistics

```python
def get_security_statistics(self)
```

Get security statistics.

        Returns:
            Dictionary of security statistics

#### cleanup_expired_data

```python
def cleanup_expired_data(self)
```

Clean up expired security data.

        Returns:
            Number of items cleaned up
