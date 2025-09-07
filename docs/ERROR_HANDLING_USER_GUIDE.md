# DShield MCP Server Error Handling User Guide

## Overview

This guide provides comprehensive information about the error handling system implemented in the DShield MCP Server. The system provides robust, production-ready error handling with full JSON-RPC 2.0 compliance and advanced features like circuit breakers and error analytics.

## Table of Contents

1. [Error Handling Overview](#error-handling-overview)
2. [JSON-RPC 2.0 Error Codes](#json-rpc-20-error-codes)
3. [Error Response Structure](#error-response-structure)
4. [Circuit Breaker Pattern](#circuit-breaker-pattern)
5. [Error Analytics and Monitoring](#error-analytics-and-monitoring)
6. [Configuration Options](#configuration-options)
7. [Common Error Scenarios](#common-error-scenarios)
8. [Troubleshooting Guide](#troubleshooting-guide)
9. [Best Practices](#best-practices)

## Error Handling Overview

The DShield MCP Server implements a comprehensive error handling system that ensures:

- **Reliability**: Graceful handling of all error conditions
- **Compliance**: Full JSON-RPC 2.0 protocol compliance
- **Observability**: Detailed error tracking and analytics
- **Resilience**: Circuit breaker pattern for external service protection
- **User Experience**: Clear, actionable error messages

### Key Components

- **MCPErrorHandler**: Central error handling class
- **CircuitBreaker**: Automatic failure detection and service isolation
- **ErrorAggregator**: Error pattern analysis and monitoring
- **Configuration Management**: Flexible error handling settings

## JSON-RPC 2.0 Error Codes

The server implements both standard JSON-RPC 2.0 error codes and custom server-defined codes:

### Standard JSON-RPC 2.0 Error Codes

| Code | Name | Description |
|------|------|-------------|
| -32700 | PARSE_ERROR | Invalid JSON received by the server |
| -32600 | INVALID_REQUEST | The JSON sent is not a valid Request object |
| -32601 | METHOD_NOT_FOUND | The method does not exist / is not available |
| -32602 | INVALID_PARAMS | Invalid method parameter(s) |
| -32603 | INTERNAL_ERROR | Internal JSON-RPC error |

### Server-Defined Error Codes

| Code | Name | Description |
|------|------|-------------|
| -32000 | EXTERNAL_SERVICE_ERROR | Error from external service (Elasticsearch, DShield API) |
| -32001 | RESOURCE_NOT_FOUND | Requested resource not found |
| -32002 | RESOURCE_ACCESS_DENIED | Access denied to requested resource |
| -32003 | RESOURCE_UNAVAILABLE | Resource temporarily unavailable |
| -32004 | VALIDATION_ERROR | Input validation failed |
| -32005 | TIMEOUT_ERROR | Operation timed out |
| -32006 | RATE_LIMIT_ERROR | Rate limit exceeded |
| -32007 | CIRCUIT_BREAKER_OPEN | Circuit breaker is open (service protection) |

## Error Response Structure

All error responses follow the JSON-RPC 2.0 specification:

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32000,
    "message": "External service error: Elasticsearch connection failed",
    "data": {
      "service": "elasticsearch",
      "suggestion": "Check Elasticsearch cluster status and network connectivity",
      "timestamp": "2025-08-29T18:30:00Z"
    }
  }
}
```

### Error Response Fields

- **jsonrpc**: Always "2.0" for JSON-RPC 2.0 compliance
- **error.code**: Numeric error code (negative values)
- **error.message**: Human-readable error description
- **error.data**: Additional error context (optional)

## Circuit Breaker Pattern

The server implements circuit breakers to protect against external service failures:

### Circuit Breaker States

1. **CLOSED**: Normal operation, requests pass through
2. **OPEN**: Service is failing, requests are blocked
3. **HALF_OPEN**: Testing if service has recovered

### Circuit Breaker Configuration

```yaml
circuit_breaker:
  failure_threshold: 5        # Number of failures before opening
  recovery_timeout: 60        # Seconds to wait before testing recovery
  expected_exception: "ConnectionError"  # Exception type to monitor
  success_threshold: 2        # Successful calls needed to close
```

### Circuit Breaker Status Tools

The server provides tools to monitor circuit breaker status:

- `get_elasticsearch_circuit_breaker_status`: Monitor Elasticsearch circuit breaker
- `get_dshield_circuit_breaker_status`: Monitor DShield API circuit breaker
- `get_latex_circuit_breaker_status`: Monitor LaTeX compilation circuit breaker

## Error Analytics and Monitoring

The error handling system provides comprehensive analytics and monitoring:

### Error Analytics Tool

```json
{
  "name": "get_error_analytics",
  "description": "Get error analytics and patterns from the error handler",
  "inputSchema": {
    "type": "object",
    "properties": {
      "window_seconds": {
        "type": "integer",
        "description": "Time window for analysis in seconds",
        "default": 300
      }
    }
  }
}
```

### Error Handling Status Tool

```json
{
  "name": "get_error_handling_status",
  "description": "Get comprehensive error handling status and configuration",
  "inputSchema": {
    "type": "object",
    "properties": {
      "include_analytics": {
        "type": "boolean",
        "description": "Include error analytics in response",
        "default": true
      }
    }
  }
}
```

## Configuration Options

Error handling can be configured through `user_config.yaml`:

```yaml
error_handling:
  timeouts:
    tool_execution: 120.0      # Tool execution timeout in seconds
    external_service: 30.0     # External service timeout in seconds
    resource_access: 15.0      # Resource access timeout in seconds

  retry:
    max_attempts: 3            # Maximum retry attempts
    backoff_factor: 2.0        # Exponential backoff factor
    max_delay: 60.0            # Maximum delay between retries

  circuit_breaker:
    failure_threshold: 5       # Failures before opening circuit breaker
    recovery_timeout: 60       # Seconds to wait before testing recovery
    expected_exception: "ConnectionError"
    success_threshold: 2       # Successful calls needed to close

  error_aggregation:
    enabled: true              # Enable error aggregation
    history_size: 1000        # Number of errors to track
    threshold_warnings: 10     # Warning threshold for error frequency
    threshold_critical: 50     # Critical threshold for error frequency
    window_seconds: 300        # Time window for threshold analysis
```

## Common Error Scenarios

### 1. External Service Failures

**Scenario**: Elasticsearch cluster is down
**Error Code**: -32000 (EXTERNAL_SERVICE_ERROR)
**Response**: Clear message with service name and suggestion
**Circuit Breaker**: Opens after configured failure threshold

**Example Response**:
```json
{
  "error": {
    "code": -32000,
    "message": "External service 'elasticsearch' error: Connection refused",
    "data": {
      "service": "elasticsearch",
      "suggestion": "The service may be temporarily unavailable. Please try again later."
    }
  }
}
```

### 2. Input Validation Failures

**Scenario**: Invalid parameters provided to tool
**Error Code**: -32004 (VALIDATION_ERROR)
**Response**: Detailed validation errors with suggestions

**Example Response**:
```json
{
  "error": {
    "code": -32004,
    "message": "Invalid parameters for tool 'query_dshield_events'",
    "data": {
      "tool": "query_dshield_events",
      "validation_errors": [
        {
          "loc": ["time_range"],
          "msg": "field required"
        }
      ],
      "suggestion": "Please check the tool schema and provide valid parameters"
    }
  }
}
```

### 3. Timeout Errors

**Scenario**: Tool execution exceeds timeout
**Error Code**: -32005 (TIMEOUT_ERROR)
**Response**: Timeout information with suggestions

**Example Response**:
```json
{
  "error": {
    "code": -32005,
    "message": "Tool 'analyze_campaign' execution timed out after 120.0 seconds",
    "data": {
      "tool": "analyze_campaign",
      "timeout_seconds": 120.0,
      "suggestion": "Try reducing the scope of your request or contact support if the issue persists"
    }
  }
}
```

### 4. Circuit Breaker Open

**Scenario**: Service is failing and circuit breaker is open
**Error Code**: -32007 (CIRCUIT_BREAKER_OPEN)
**Response**: Circuit breaker status with recovery information

**Example Response**:
```json
{
  "error": {
    "code": -32007,
    "message": "Circuit breaker for 'elasticsearch' is open",
    "data": {
      "service": "elasticsearch",
      "state": "OPEN",
      "failure_count": 15,
      "last_failure": "2025-08-29T18:25:00Z",
      "recovery_timeout": 60,
      "suggestion": "Service is temporarily unavailable. Please try again later."
    }
  }
}
```

## Troubleshooting Guide

### Common Issues and Solutions

#### 1. High Error Rates

**Symptoms**: Frequent error responses, circuit breakers opening
**Diagnosis**: Check error analytics using `get_error_analytics` tool
**Solutions**:
- Review external service health
- Check network connectivity
- Verify configuration settings
- Monitor resource usage

#### 2. Circuit Breaker Stuck Open

**Symptoms**: Service unavailable even after external service recovery
**Diagnosis**: Check circuit breaker status using status tools
**Solutions**:
- Wait for recovery timeout to complete
- Check circuit breaker configuration
- Verify external service is truly healthy
- Consider manual circuit breaker reset

#### 3. Timeout Issues

**Symptoms**: Frequent timeout errors
**Diagnosis**: Review timeout configuration and external service performance
**Solutions**:
- Increase timeout values if appropriate
- Optimize external service queries
- Check network latency
- Review resource allocation

#### 4. Validation Errors

**Symptoms**: Frequent validation error responses
**Diagnosis**: Check tool input schemas and provided parameters
**Solutions**:
- Review tool documentation
- Verify parameter types and formats
- Check required vs. optional parameters
- Use `get_tool_schema` to understand requirements

### Debugging Commands

Use these tools to diagnose error handling issues:

```bash
# Get error analytics for the last 5 minutes
curl -X POST "http://localhost:8000/tools/call" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "get_error_analytics",
    "arguments": {"window_seconds": 300}
  }'

# Get comprehensive error handling status
curl -X POST "http://localhost:8000/tools/call" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "get_error_handling_status",
    "arguments": {"include_analytics": true}
  }'

# Check circuit breaker status for specific service
curl -X POST "http://localhost:8000/tools/call" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "get_elasticsearch_circuit_breaker_status",
    "arguments": {}
  }'
```

## Best Practices

### 1. Error Handling Configuration

- **Set Appropriate Timeouts**: Balance between user experience and system stability
- **Configure Circuit Breakers**: Use failure thresholds that reflect your tolerance for errors
- **Enable Error Aggregation**: Monitor error patterns for proactive issue detection
- **Regular Review**: Periodically review error analytics and adjust configuration

### 2. User Experience

- **Clear Messages**: Provide actionable error messages
- **Helpful Suggestions**: Include specific steps to resolve issues
- **Consistent Format**: Use consistent error response structure
- **Graceful Degradation**: Provide fallback options when possible

### 3. Monitoring and Alerting

- **Error Rate Monitoring**: Set up alerts for high error rates
- **Circuit Breaker Alerts**: Monitor circuit breaker state changes
- **Performance Metrics**: Track error handling overhead
- **Trend Analysis**: Monitor error patterns over time

### 4. Development and Testing

- **Test Error Scenarios**: Include error handling in test suites
- **Mock External Services**: Test circuit breaker behavior
- **Validate Error Responses**: Ensure JSON-RPC 2.0 compliance
- **Performance Testing**: Measure error handling overhead

## API Reference

For detailed API documentation, see:
- **HTML Documentation**: `docs/api/` directory
- **Source Code**: `src/mcp_error_handler.py`
- **Implementation Details**: `docs/Implementation_Docs/ISSUE_58_JSON_RPC_ERROR_HANDLING_IMPLEMENTATION.md`

## Support and Feedback

If you encounter issues with the error handling system:

1. **Check the logs**: Review server logs for detailed error information
2. **Use diagnostic tools**: Use the provided error analytics and status tools
3. **Review configuration**: Verify error handling configuration settings
4. **Check external services**: Ensure dependent services are healthy
5. **Contact support**: Provide error details and context for assistance

---

**Version**: 1.0
**Last Updated**: 2025-08-29
**Related Issue**: #58 - JSON-RPC Error Handling Implementation
