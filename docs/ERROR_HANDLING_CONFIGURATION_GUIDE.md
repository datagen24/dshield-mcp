# DShield MCP Server Error Handling Configuration Guide

## Overview

This guide provides detailed configuration information for the error handling system implemented in the DShield MCP Server. It covers all configuration options, environment variables, and best practices for production deployment.

## Table of Contents

1. [Configuration Overview](#configuration-overview)
2. [Configuration File Structure](#configuration-file-structure)
3. [Environment Variables](#environment-variables)
4. [Error Handling Settings](#error-handling-settings)
5. [Circuit Breaker Configuration](#circuit-breaker-configuration)
6. [Timeout Configuration](#timeout-configuration)
7. [Retry Configuration](#retry-configuration)
8. [Error Aggregation Configuration](#error-aggregation-configuration)
9. [Production Configuration Examples](#production-configuration-examples)
10. [Configuration Validation](#configuration-validation)
11. [Troubleshooting Configuration Issues](#troubleshooting-configuration-issues)

## Configuration Overview

The error handling system can be configured through multiple methods:

1. **Configuration File**: `user_config.yaml` (recommended for production)
2. **Environment Variables**: Override specific settings
3. **Default Values**: Built-in sensible defaults
4. **Runtime Configuration**: Dynamic configuration changes

### Configuration Priority (Highest to Lowest)

1. Environment Variables
2. Configuration File (`user_config.yaml`)
3. Default Values (built into code)

## Configuration File Structure

The main configuration file is `user_config.yaml` in the project root:

```yaml
# DShield MCP Server Configuration
server:
  name: "dshield-elastic-mcp"
  version: "1.0.0"
  debug: false

# Error Handling Configuration
error_handling:
  # Timeout settings for different operations
  timeouts:
    tool_execution: 120.0      # Tool execution timeout in seconds
    external_service: 30.0     # External service timeout in seconds
    resource_access: 15.0      # Resource access timeout in seconds
    validation: 5.0            # Input validation timeout in seconds
  
  # Retry configuration for failed operations
  retry:
    max_attempts: 3            # Maximum retry attempts
    backoff_factor: 2.0        # Exponential backoff factor
    max_delay: 60.0            # Maximum delay between retries
    jitter: 0.1                # Random jitter factor (0.0 to 1.0)
  
  # Circuit breaker configuration
  circuit_breaker:
    failure_threshold: 5       # Failures before opening circuit breaker
    recovery_timeout: 60       # Seconds to wait before testing recovery
    expected_exception: "ConnectionError"  # Exception type to monitor
    success_threshold: 2       # Successful calls needed to close
    half_open_max_calls: 3     # Max calls in half-open state
  
  # Error aggregation and monitoring
  error_aggregation:
    enabled: true              # Enable error aggregation
    history_size: 1000        # Number of errors to track
    threshold_warnings: 10     # Warning threshold for error frequency
    threshold_critical: 50     # Critical threshold for error frequency
    window_seconds: 300        # Time window for threshold analysis
    cleanup_interval: 3600     # Cleanup interval in seconds
  
  # Logging configuration
  logging:
    level: "INFO"              # Log level (DEBUG, INFO, WARNING, ERROR)
    include_context: true      # Include error context in logs
    include_stack_trace: false # Include stack traces in logs
    format: "json"             # Log format (json, text)
  
  # Performance monitoring
  performance:
    track_error_overhead: true # Track error handling performance impact
    sample_rate: 0.1           # Sampling rate for performance metrics (0.0 to 1.0)
    metrics_retention: 86400   # Metrics retention time in seconds
```

## Environment Variables

Environment variables can override configuration file settings:

### Timeout Configuration

```bash
# Tool execution timeout
export ERROR_HANDLING_TIMEOUTS_TOOL_EXECUTION=180.0

# External service timeout
export ERROR_HANDLING_TIMEOUTS_EXTERNAL_SERVICE=45.0

# Resource access timeout
export ERROR_HANDLING_TIMEOUTS_RESOURCE_ACCESS=20.0
```

### Circuit Breaker Configuration

```bash
# Circuit breaker failure threshold
export ERROR_HANDLING_CIRCUIT_BREAKER_FAILURE_THRESHOLD=10

# Circuit breaker recovery timeout
export ERROR_HANDLING_CIRCUIT_BREAKER_RECOVERY_TIMEOUT=120

# Circuit breaker success threshold
export ERROR_HANDLING_CIRCUIT_BREAKER_SUCCESS_THRESHOLD=3
```

### Error Aggregation Configuration

```bash
# Enable/disable error aggregation
export ERROR_HANDLING_ERROR_AGGREGATION_ENABLED=true

# Error history size
export ERROR_HANDLING_ERROR_AGGREGATION_HISTORY_SIZE=2000

# Warning threshold
export ERROR_HANDLING_ERROR_AGGREGATION_THRESHOLD_WARNINGS=20
```

### Logging Configuration

```bash
# Log level
export ERROR_HANDLING_LOGGING_LEVEL=DEBUG

# Include error context
export ERROR_HANDLING_LOGGING_INCLUDE_CONTEXT=true

# Include stack traces
export ERROR_HANDLING_LOGGING_INCLUDE_STACK_TRACE=false
```

## Error Handling Settings

### Timeout Configuration

Timeouts control how long the system waits for operations to complete:

```yaml
timeouts:
  tool_execution: 120.0      # Maximum time for tool execution
  external_service: 30.0     # Maximum time for external service calls
  resource_access: 15.0      # Maximum time for resource access
  validation: 5.0            # Maximum time for input validation
```

**Recommendations**:
- **tool_execution**: 60-300 seconds (depends on tool complexity)
- **external_service**: 15-60 seconds (depends on service reliability)
- **resource_access**: 5-30 seconds (depends on resource size)
- **validation**: 1-10 seconds (should be very fast)

### Retry Configuration

Retry settings control automatic retry behavior for failed operations:

```yaml
retry:
  max_attempts: 3            # Total attempts (initial + retries)
  backoff_factor: 2.0        # Exponential backoff multiplier
  max_delay: 60.0            # Maximum delay between retries
  jitter: 0.1                # Random jitter to prevent thundering herd
```

**Recommendations**:
- **max_attempts**: 2-5 (balance between reliability and user experience)
- **backoff_factor**: 1.5-3.0 (exponential backoff)
- **max_delay**: 30-120 seconds (prevent excessive delays)
- **jitter**: 0.1-0.3 (randomize retry timing)

## Circuit Breaker Configuration

Circuit breakers protect the system from external service failures:

```yaml
circuit_breaker:
  failure_threshold: 5       # Failures before opening
  recovery_timeout: 60       # Seconds to wait before testing recovery
  expected_exception: "ConnectionError"  # Exception type to monitor
  success_threshold: 2       # Successful calls needed to close
  half_open_max_calls: 3     # Max calls in half-open state
```

### Circuit Breaker States

1. **CLOSED**: Normal operation, requests pass through
2. **OPEN**: Service is failing, requests are blocked
3. **HALF_OPEN**: Testing if service has recovered

### Configuration Guidelines

- **failure_threshold**: 3-10 (depends on tolerance for errors)
- **recovery_timeout**: 30-300 seconds (depends on service recovery time)
- **success_threshold**: 1-5 (depends on confidence requirements)
- **half_open_max_calls**: 1-5 (prevent overwhelming recovering service)

### Exception Types

Common exception types to monitor:

```python
# Network and connection errors
"ConnectionError"
"TimeoutError"
"ConnectionRefusedError"

# HTTP and API errors
"HTTPError"
"ClientError"
"ServerError"

# Custom exception classes
"ElasticsearchError"
"DShieldAPIError"
"LaTeXCompilationError"
```

## Error Aggregation Configuration

Error aggregation provides monitoring and alerting capabilities:

```yaml
error_aggregation:
  enabled: true              # Enable error aggregation
  history_size: 1000        # Number of errors to track
  threshold_warnings: 10     # Warning threshold for error frequency
  threshold_critical: 50     # Critical threshold for error frequency
  window_seconds: 300        # Time window for threshold analysis
  cleanup_interval: 3600     # Cleanup interval in seconds
```

### Threshold Configuration

- **threshold_warnings**: Alert when errors exceed this rate
- **threshold_critical**: Critical alert when errors exceed this rate
- **window_seconds**: Time window for rate calculation
- **cleanup_interval**: How often to clean up old error data

### Monitoring Integration

Error aggregation can integrate with monitoring systems:

```yaml
error_aggregation:
  # ... other settings ...
  monitoring:
    prometheus_enabled: true
    statsd_enabled: false
    custom_metrics: true
    alerting:
      webhook_url: "https://alerts.example.com/webhook"
      slack_webhook: "https://hooks.slack.com/services/..."
```

## Production Configuration Examples

### High-Availability Configuration

```yaml
error_handling:
  timeouts:
    tool_execution: 300.0     # Longer timeouts for complex operations
    external_service: 60.0    # Generous timeouts for external services
    resource_access: 30.0     # Adequate time for large resources
  
  retry:
    max_attempts: 5           # More retry attempts
    backoff_factor: 2.5       # Aggressive backoff
    max_delay: 120.0          # Longer maximum delay
  
  circuit_breaker:
    failure_threshold: 3      # Quick failure detection
    recovery_timeout: 120     # Longer recovery time
    success_threshold: 3      # Higher confidence for recovery
  
  error_aggregation:
    enabled: true
    history_size: 5000        # Larger history for analysis
    threshold_warnings: 5     # Lower warning threshold
    threshold_critical: 20    # Lower critical threshold
    window_seconds: 600       # Longer analysis window
```

### Development/Testing Configuration

```yaml
error_handling:
  timeouts:
    tool_execution: 60.0      # Shorter timeouts for quick feedback
    external_service: 15.0    # Fast failure for development
    resource_access: 10.0     # Quick resource access
  
  retry:
    max_attempts: 2           # Fewer retries for development
    backoff_factor: 1.5       # Gentle backoff
    max_delay: 30.0           # Shorter delays
  
  circuit_breaker:
    failure_threshold: 2      # Quick circuit breaker activation
    recovery_timeout: 30      # Fast recovery testing
    success_threshold: 1      # Quick recovery confirmation
  
  error_aggregation:
    enabled: true
    history_size: 1000        # Smaller history for development
    threshold_warnings: 20    # Higher thresholds for development
    threshold_critical: 100   # Higher critical threshold
    window_seconds: 300       # Standard analysis window
  
  logging:
    level: "DEBUG"            # Detailed logging for development
    include_context: true     # Include error context
    include_stack_trace: true # Include stack traces
```

### Minimal Configuration

```yaml
error_handling:
  # Use all default values
  # Only override essential settings
  
  timeouts:
    tool_execution: 120.0     # Standard tool timeout
  
  circuit_breaker:
    failure_threshold: 5      # Standard failure threshold
    recovery_timeout: 60      # Standard recovery timeout
```

## Configuration Validation

The system validates configuration at startup:

### Validation Rules

1. **Timeout Values**: Must be positive numbers
2. **Retry Settings**: Must be valid retry configuration
3. **Circuit Breaker**: Must have valid thresholds and timeouts
4. **Error Aggregation**: Must have valid thresholds and windows

### Validation Errors

Common validation errors and solutions:

```yaml
# ERROR: Timeout value must be positive
timeouts:
  tool_execution: -10.0  # ❌ Invalid: negative value

# SOLUTION: Use positive value
timeouts:
  tool_execution: 10.0   # ✅ Valid: positive value
```

```yaml
# ERROR: Circuit breaker failure threshold must be >= 1
circuit_breaker:
  failure_threshold: 0   # ❌ Invalid: must be at least 1

# SOLUTION: Use valid threshold
circuit_breaker:
  failure_threshold: 1   # ✅ Valid: minimum threshold
```

```yaml
# ERROR: Recovery timeout must be positive
circuit_breaker:
  recovery_timeout: -30  # ❌ Invalid: negative value

# SOLUTION: Use positive value
circuit_breaker:
  recovery_timeout: 30   # ✅ Valid: positive value
```

## Troubleshooting Configuration Issues

### Common Issues

#### 1. Configuration File Not Loaded

**Symptoms**: Default values being used, configuration changes not taking effect
**Diagnosis**: Check file path and permissions
**Solutions**:
- Verify `user_config.yaml` exists in project root
- Check file permissions (should be readable)
- Verify YAML syntax is correct
- Check server logs for configuration errors

#### 2. Environment Variables Not Recognized

**Symptoms**: Environment variable changes not affecting behavior
**Diagnosis**: Check variable naming and server restart
**Solutions**:
- Verify environment variable names (use exact format)
- Restart server after environment variable changes
- Check variable naming convention
- Verify variable values are correct

#### 3. Invalid Configuration Values

**Symptoms**: Server startup failures, validation errors
**Diagnosis**: Check configuration validation logs
**Solutions**:
- Review configuration validation rules
- Fix invalid values (negative timeouts, etc.)
- Check YAML syntax
- Validate configuration manually

#### 4. Configuration Conflicts

**Symptoms**: Unexpected behavior, settings not working as expected
**Diagnosis**: Check configuration priority and conflicts
**Solutions**:
- Understand configuration priority (env vars > file > defaults)
- Check for conflicting settings
- Verify configuration inheritance
- Review server logs for configuration warnings

### Debugging Configuration

Enable debug logging to troubleshoot configuration issues:

```yaml
error_handling:
  logging:
    level: "DEBUG"
    include_context: true
    include_stack_trace: true
```

### Configuration Testing

Test configuration changes in a safe environment:

1. **Development Environment**: Test changes in development first
2. **Configuration Validation**: Use built-in validation
3. **Gradual Rollout**: Apply changes incrementally
4. **Monitoring**: Monitor system behavior after changes
5. **Rollback Plan**: Have rollback strategy ready

## Best Practices

### 1. Configuration Management

- **Version Control**: Keep configuration in version control
- **Environment Separation**: Use different configs for different environments
- **Documentation**: Document all configuration changes
- **Testing**: Test configuration changes before production

### 2. Production Configuration

- **Conservative Timeouts**: Use generous timeouts for production
- **Robust Circuit Breakers**: Configure for high availability
- **Comprehensive Monitoring**: Enable all monitoring features
- **Regular Review**: Periodically review and adjust configuration

### 3. Security Considerations

- **Sensitive Data**: Never include secrets in configuration files
- **Access Control**: Restrict access to configuration files
- **Audit Logging**: Log configuration changes
- **Validation**: Validate all configuration inputs

### 4. Performance Optimization

- **Timeout Tuning**: Balance between reliability and performance
- **Retry Optimization**: Optimize retry strategies for your use case
- **Circuit Breaker Tuning**: Adjust thresholds based on service characteristics
- **Monitoring Overhead**: Balance monitoring detail with performance impact

## Configuration Reference

### Complete Configuration Schema

```yaml
error_handling:
  timeouts:
    tool_execution: float      # Required: Tool execution timeout
    external_service: float    # Required: External service timeout
    resource_access: float     # Required: Resource access timeout
    validation: float          # Optional: Validation timeout (default: 5.0)
  
  retry:
    max_attempts: int          # Required: Maximum retry attempts
    backoff_factor: float      # Required: Exponential backoff factor
    max_delay: float           # Required: Maximum delay between retries
    jitter: float              # Optional: Random jitter (default: 0.1)
  
  circuit_breaker:
    failure_threshold: int     # Required: Failures before opening
    recovery_timeout: float    # Required: Recovery timeout in seconds
    expected_exception: str    # Required: Exception type to monitor
    success_threshold: int     # Required: Successful calls to close
    half_open_max_calls: int  # Optional: Max calls in half-open (default: 3)
  
  error_aggregation:
    enabled: bool              # Required: Enable error aggregation
    history_size: int          # Required: Number of errors to track
    threshold_warnings: int    # Required: Warning threshold
    threshold_critical: int    # Required: Critical threshold
    window_seconds: int        # Required: Analysis window in seconds
    cleanup_interval: int      # Optional: Cleanup interval (default: 3600)
  
  logging:
    level: str                 # Required: Log level
    include_context: bool      # Required: Include error context
    include_stack_trace: bool  # Required: Include stack traces
    format: str                # Optional: Log format (default: "json")
  
  performance:
    track_error_overhead: bool # Optional: Track performance impact (default: true)
    sample_rate: float         # Optional: Sampling rate (default: 0.1)
    metrics_retention: int     # Optional: Metrics retention (default: 86400)
```

### Default Values

```yaml
error_handling:
  timeouts:
    tool_execution: 120.0
    external_service: 30.0
    resource_access: 15.0
    validation: 5.0
  
  retry:
    max_attempts: 3
    backoff_factor: 2.0
    max_delay: 60.0
    jitter: 0.1
  
  circuit_breaker:
    failure_threshold: 5
    recovery_timeout: 60
    expected_exception: "ConnectionError"
    success_threshold: 2
    half_open_max_calls: 3
  
  error_aggregation:
    enabled: true
    history_size: 1000
    threshold_warnings: 10
    threshold_critical: 50
    window_seconds: 300
    cleanup_interval: 3600
  
  logging:
    level: "INFO"
    include_context: true
    include_stack_trace: false
    format: "json"
  
  performance:
    track_error_overhead: true
    sample_rate: 0.1
    metrics_retention: 86400
```

---

**Version**: 1.0  
**Last Updated**: 2025-08-29  
**Related Issue**: #58 - JSON-RPC Error Handling Implementation
