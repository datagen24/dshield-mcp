# security_validator

Security validation module for DShield MCP server.

This module provides security validation for MCP tools, including:
- Tool description validation
- Parameter schema validation
- Input sanitization checks
- Security monitoring and logging

## SecurityRiskLevel

Security risk levels.

## SecurityIssue

Represents a security issue found during validation.

#### __post_init__

```python
def __post_init__(self)
```

Initialize timestamp if not provided.

#### to_dict

```python
def to_dict(self)
```

Convert to dictionary for serialization.

## SecurityValidator

Security validation for MCP tools and parameters.

#### __init__

```python
def __init__(self, enable_logging)
```

Initialize security validator.

        Args:
            enable_logging: Whether to enable security logging

#### validate_tool_description

```python
def validate_tool_description(self, tool_name, description)
```

Validate tool description for security issues.

        Args:
            tool_name: Name of the tool being validated
            description: Tool description to validate

        Returns:
            List of security issues found

#### validate_tool_schema

```python
def validate_tool_schema(self, tool_name, schema)
```

Validate tool schema for security issues.

        Args:
            tool_name: Name of the tool being validated
            schema: Tool parameter schema to validate

        Returns:
            List of security issues found

#### validate_tool_arguments

```python
def validate_tool_arguments(self, tool_name, arguments)
```

Validate tool arguments for security issues.

        Args:
            tool_name: Name of the tool being validated
            arguments: Tool arguments to validate

        Returns:
            List of security issues found

#### validate_server_configuration

```python
def validate_server_configuration(self, config)
```

Validate MCP server configuration for security issues.

        Args:
            config: Server configuration to validate

        Returns:
            List of security issues found

#### get_security_summary

```python
def get_security_summary(self)
```

Get a summary of all security issues found.

#### clear_issues

```python
def clear_issues(self)
```

Clear all recorded security issues.

#### _log_issues

```python
def _log_issues(self, issues)
```

Log security issues and add to tracking list.

## SecurityMonitor

Real-time security monitoring for MCP server.

#### __init__

```python
def __init__(self, validator)
```

Initialize security monitor.

        Args:
            validator: Security validator instance

#### monitor_tool_registration

```python
def monitor_tool_registration(self, tool_name, description, schema)
```

Monitor tool registration for security issues.

#### monitor_tool_execution

```python
def monitor_tool_execution(self, tool_name, arguments)
```

Monitor tool execution for security issues.

#### get_security_metrics

```python
def get_security_metrics(self)
```

Get security monitoring metrics.

#### set_alert_threshold

```python
def set_alert_threshold(self, threshold)
```

Set the alert threshold for security monitoring.

#### enable_monitoring

```python
def enable_monitoring(self)
```

Enable security monitoring.

#### disable_monitoring

```python
def disable_monitoring(self)
```

Disable security monitoring.
