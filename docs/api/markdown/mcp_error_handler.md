# mcp_error_handler

MCP Error Handler for DShield MCP Server.

This module provides centralized error handling for all MCP operations,
ensuring proper JSON-RPC error responses with correct error codes,
timeout handling, retry logic, and comprehensive error context capture.

The error handler follows the JSON-RPC 2.0 specification and provides
user-friendly error messages while maintaining detailed logging for
debugging and troubleshooting.

Example:
    >>> error_handler = MCPErrorHandler(config)
    >>> error_response = error_handler.create_validation_error("tool_name", validation_error)
    >>> timeout_response = error_handler.create_timeout_error("tool_name", 30)

## CircuitBreakerState

Circuit breaker states.

## CircuitBreakerConfig

Configuration for circuit breaker behavior.

    Attributes:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Time to wait before attempting recovery
        expected_exception: Exception types that count as failures
        success_threshold: Number of successes needed to close circuit

## ErrorHandlingConfig

Configuration for error handling behavior.

    Attributes:
        timeouts: Timeout settings for different operations
        retry_settings: Retry configuration for transient failures
        logging: Logging configuration for error handling
        circuit_breaker: Circuit breaker configuration
        error_aggregation: Error aggregation settings

## MCPErrorHandler

Handles JSON-RPC error responses for MCP server.

    This class provides comprehensive error handling for all MCP operations,
    including proper error code generation, timeout handling, retry logic,
    and detailed error logging for debugging and troubleshooting.

    The error handler follows the JSON-RPC 2.0 specification and ensures
    that all error responses are properly formatted and contain actionable
    information for users while maintaining detailed logging for developers.

    Attributes:
        config: Error handling configuration
        logger: Structured logger instance

#### __init__

```python
def __init__(self, config)
```

Initialize the MCP error handler.

        Args:
            config: Error handling configuration. If None, uses default values.

#### _validate_config

```python
def _validate_config(self)
```

Validate the error handling configuration.

        Raises:
            ValueError: If configuration values are invalid.

#### create_error

```python
def create_error(self, code, message, data, request_id)
```

Create a properly formatted JSON-RPC error response.

        Args:
            code: JSON-RPC error code
            message: Human-readable error message
            data: Additional error data (optional)
            request_id: Request ID for correlation (optional)

        Returns:
            Dictionary containing the JSON-RPC error response.

        Example:
            >>> error = error_handler.create_error(
            ...     MCPErrorHandler.INVALID_PARAMS,
            ...     "Invalid parameters provided",
            ...     {"field": "time_range", "issue": "must be positive"}
            ... )

#### _get_error_type

```python
def _get_error_type(self, code)
```

Get a human-readable error type from error code.

        Args:
            code: JSON-RPC error code

        Returns:
            String representation of error type.

#### create_parse_error

```python
def create_parse_error(self, message, data)
```

Create a parse error response.

        Args:
            message: Error message
            data: Additional error data

        Returns:
            Parse error response.

#### create_invalid_request_error

```python
def create_invalid_request_error(self, message, data)
```

Create an invalid request error response.

        Args:
            message: Error message
            data: Additional error data

        Returns:
            Invalid request error response.

#### create_method_not_found_error

```python
def create_method_not_found_error(self, method, data)
```

Create a method not found error response.

        Args:
            method: Method name that was not found
            data: Additional error data

        Returns:
            Method not found error response.

#### create_invalid_params_error

```python
def create_invalid_params_error(self, message, data)
```

Create an invalid parameters error response.

        Args:
            message: Error message
            data: Additional error data

        Returns:
            Invalid parameters error response.

#### create_internal_error

```python
def create_internal_error(self, message, data)
```

Create an internal error response.

        Args:
            message: Error message
            data: Additional error data

        Returns:
            Internal error response.

#### create_validation_error

```python
def create_validation_error(self, tool_name, validation_error, data)
```

Create a validation error response.

        Args:
            tool_name: Name of the tool that failed validation
            validation_error: Pydantic validation error
            data: Additional error data

        Returns:
            Validation error response.

#### create_timeout_error

```python
def create_timeout_error(self, tool_name, timeout_seconds, data)
```

Create a timeout error response.

        Args:
            tool_name: Name of the tool that timed out
            timeout_seconds: Timeout value in seconds
            data: Additional error data

        Returns:
            Timeout error response.

#### create_resource_error

```python
def create_resource_error(self, resource_uri, error_type, message, data)
```

Create a resource-related error response.

        Args:
            resource_uri: URI of the resource that caused the error
            error_type: Type of resource error
            message: Error message
            data: Additional error data

        Returns:
            Resource error response.

#### create_external_service_error

```python
def create_external_service_error(self, service_name, error_message, data)
```

Create an external service error response.

        Args:
            service_name: Name of the external service
            error_message: Error message from the service
            data: Additional error data

        Returns:
            External service error response.

#### create_rate_limit_error

```python
def create_rate_limit_error(self, service_name, retry_after, data)
```

Create a rate limit error response.

        Args:
            service_name: Name of the service that rate limited the request
            retry_after: Suggested retry delay in seconds
            data: Additional error data

        Returns:
            Rate limit error response.

#### create_security_error

```python
def create_security_error(self, message, data)
```

Create a security error response.

        Args:
            message: Security error message
            data: Additional error data

        Returns:
            Security error response.

#### create_schema_validation_error

```python
def create_schema_validation_error(self, message, data)
```

Create a schema validation error response.

        Args:
            message: Schema validation error message
            data: Additional error data

        Returns:
            Schema validation error response.

#### validate_tool_exists

```python
def validate_tool_exists(self, tool_name, available_tools)
```

Validate that a tool exists before execution.

        Args:
            tool_name: Name of the tool to validate
            available_tools: List of available tool names

        Raises:
            ValueError: If the tool does not exist.

#### validate_arguments

```python
def validate_arguments(self, tool_name, arguments, schema)
```

Validate arguments against a tool schema.

        Args:
            tool_name: Name of the tool
            arguments: Arguments to validate
            schema: Tool schema for validation

        Raises:
            ValidationError: If arguments are invalid.

#### _log_error

```python
def _log_error(self, code, message, data, request_id)
```

Log error information to stderr for debugging.

        Args:
            code: Error code
            message: Error message
            data: Additional error data
            request_id: Request ID for correlation

#### get_error_summary

```python
def get_error_summary(self)
```

Get a summary of error handling configuration.

        Returns:
            Dictionary containing error handling configuration summary.

#### create_resource_not_found_error

```python
def create_resource_not_found_error(self, resource_uri, data)
```

Create a resource not found error response.

        Args:
            resource_uri: URI of the resource that was not found
            data: Additional error data

        Returns:
            Resource not found error response.

#### create_resource_access_denied_error

```python
def create_resource_access_denied_error(self, resource_uri, reason, data)
```

Create a resource access denied error response.

        Args:
            resource_uri: URI of the resource that access was denied to
            reason: Reason for access denial
            data: Additional error data

        Returns:
            Resource access denied error response.

#### create_resource_unavailable_error

```python
def create_resource_unavailable_error(self, resource_uri, reason, data)
```

Create a resource unavailable error response.

        Args:
            resource_uri: URI of the resource that is unavailable
            reason: Reason for unavailability
            data: Additional error data

        Returns:
            Resource unavailable error response.

#### create_circuit_breaker_open_error

```python
def create_circuit_breaker_open_error(self, service_name, data)
```

Create a circuit breaker open error response.

        Args:
            service_name: Name of the service with open circuit breaker
            data: Additional error data

        Returns:
            Circuit breaker open error response.

#### create_validation_error_with_context

```python
def create_validation_error_with_context(self, tool_name, validation_error, context, data)
```

Create a validation error response with additional context.

        Args:
            tool_name: Name of the tool that failed validation
            validation_error: Pydantic validation error
            context: Additional context about the validation failure
            data: Additional error data

        Returns:
            Enhanced validation error response.

#### create_timeout_error_with_context

```python
def create_timeout_error_with_context(self, tool_name, timeout_seconds, operation_context, data)
```

Create a timeout error response with operation context.

        Args:
            tool_name: Name of the tool that timed out
            timeout_seconds: Timeout value that was exceeded
            operation_context: Context about the operation that timed out
            data: Additional error data

        Returns:
            Enhanced timeout error response.

#### get_enhanced_error_summary

```python
def get_enhanced_error_summary(self)
```

Get an enhanced summary including Phase 3 features.

        Returns:
            Dictionary containing comprehensive error handling configuration and capabilities.

#### get_error_analytics

```python
def get_error_analytics(self, window_seconds)
```

Get error analytics and patterns from the aggregator.

        Args:
            window_seconds: Time window in seconds (uses config default if None)

        Returns:
            Dictionary containing error analytics and patterns.

#### get_circuit_breaker_status

```python
def get_circuit_breaker_status(self, service_name)
```

Get circuit breaker status for a specific service.

        Args:
            service_name: Name of the service to check

        Returns:
            Circuit breaker status or None if not found.

## CircuitBreaker

Circuit breaker implementation for external service calls.

    This class implements the circuit breaker pattern to prevent cascading failures
    when external services are experiencing issues. It tracks failures and
    automatically opens the circuit when the failure threshold is reached.

    Attributes:
        config: Circuit breaker configuration
        state: Current circuit breaker state
        failure_count: Number of consecutive failures
        success_count: Number of consecutive successes
        last_failure_time: Timestamp of last failure
        logger: Structured logger instance

#### __init__

```python
def __init__(self, service_name, config)
```

Initialize the circuit breaker.

        Args:
            service_name: Name of the service being protected
            config: Circuit breaker configuration

#### can_execute

```python
def can_execute(self)
```

Check if the circuit breaker allows execution.

        Returns:
            True if execution is allowed, False otherwise.

#### on_success

```python
def on_success(self)
```

Record a successful operation.

#### on_failure

```python
def on_failure(self, exception)
```

Record a failed operation.

        Args:
            exception: The exception that occurred

#### _should_attempt_reset

```python
def _should_attempt_reset(self)
```

Check if enough time has passed to attempt reset.

        Returns:
            True if reset should be attempted.

#### _set_half_open

```python
def _set_half_open(self)
```

Set circuit breaker to half-open state.

#### _set_open

```python
def _set_open(self)
```

Set circuit breaker to open state.

#### _set_closed

```python
def _set_closed(self)
```

Set circuit breaker to closed state.

#### get_status

```python
def get_status(self)
```

Get the current status of the circuit breaker.

        Returns:
            Dictionary containing circuit breaker status.

## ErrorAggregator

Error aggregation and analytics for monitoring and debugging.

    This class tracks error patterns, frequencies, and trends to help
    identify systemic issues and provide insights for debugging.

    Attributes:
        config: Error aggregation configuration
        error_counts: Count of errors by type and time window
        error_history: Recent error history for analysis
        logger: Structured logger instance

#### __init__

```python
def __init__(self, config)
```

Initialize the error aggregator.

        Args:
            config: Error aggregation configuration

#### record_error

```python
def record_error(self, error_code, error_type, context)
```

Record an error occurrence.

        Args:
            error_code: JSON-RPC error code
            error_type: Type of error (e.g., 'timeout', 'validation', 'external_service')
            context: Additional context about the error

#### _check_error_thresholds

```python
def _check_error_thresholds(self, error_type)
```

Check if error thresholds are exceeded and log warnings.

        Args:
            error_type: Type of error to check

#### _get_recent_errors

```python
def _get_recent_errors(self, window_seconds)
```

Get errors from the recent time window.

        Args:
            window_seconds: Time window in seconds

        Returns:
            List of recent errors

#### get_error_summary

```python
def get_error_summary(self, window_seconds)
```

Get a summary of error patterns.

        Args:
            window_seconds: Time window in seconds (uses config default if None)

        Returns:
            Dictionary containing error summary and patterns.

#### get_error_trends

```python
def get_error_trends(self, hours)
```

Get error trends over a longer time period.

        Args:
            hours: Number of hours to analyze

        Returns:
            Dictionary containing error trends and patterns.

#### _describe_trend

```python
def _describe_trend(self, trend_percentage)
```

Describe the error trend in human-readable terms.

        Args:
            trend_percentage: Percentage change in error rate

        Returns:
            Human-readable trend description.

#### reset

```python
def reset(self)
```

Reset all error tracking data.
