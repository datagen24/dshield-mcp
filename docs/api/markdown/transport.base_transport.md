# base_transport

Base transport class for DShield MCP Server.

This module provides the abstract base class for all transport implementations,
defining the interface that must be implemented by STDIO and TCP transports.

## BaseTransport

Abstract base class for MCP transport implementations.

    This class defines the interface that all transport implementations must
    follow to ensure consistent behavior and MCP protocol compliance.

    Attributes:
        server: The MCP server instance
        config: Transport-specific configuration
        is_running: Whether the transport is currently running

#### __init__

```python
def __init__(self, server, config)
```

Initialize the base transport.

        Args:
            server: The MCP server instance
            config: Transport-specific configuration

#### transport_type

```python
def transport_type(self)
```

Get the transport type identifier.

        Returns:
            String identifier for the transport type (e.g., 'stdio', 'tcp')

#### get_config

```python
def get_config(self, key, default)
```

Get a configuration value.

        Args:
            key: Configuration key
            default: Default value if key not found

        Returns:
            Configuration value or default

#### set_config

```python
def set_config(self, key, value)
```

Set a configuration value.

        Args:
            key: Configuration key
            value: Configuration value

## TransportError

Exception raised for transport-related errors.

    This exception is raised when transport operations fail, such as
    connection failures, protocol errors, or resource issues.

#### __init__

```python
def __init__(self, message, transport_type, error_code)
```

Initialize the transport error.

        Args:
            message: Error message
            transport_type: Type of transport that failed
            error_code: Optional error code for programmatic handling

#### __str__

```python
def __str__(self)
```

Get string representation of the error.

        Returns:
            Formatted error string
