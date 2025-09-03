# tcp_server

TCP server implementation for DShield MCP Server.

This module provides the core TCP server implementation with full MCP protocol
support, authentication, security, and integration with the existing MCP server.

## MCPServerAdapter

Adapter to integrate TCP transport with MCP server.

    This class bridges the gap between the TCP transport layer and the
    existing MCP server, handling protocol translation and message routing.

#### __init__

```python
def __init__(self, mcp_server, config)
```

Initialize the MCP server adapter.

        Args:
            mcp_server: The MCP server instance
            config: Adapter configuration

#### _create_error_response

```python
def _create_error_response(self, message_id, error_code, error_message, error_data)
```

Create a JSON-RPC error response.

        Args:
            message_id: Message ID
            error_code: Error code
            error_message: Error message
            error_data: Additional error data

        Returns:
            Error response dictionary

## EnhancedTCPServer

Enhanced TCP server with full MCP protocol support.

    This class provides a complete TCP server implementation that integrates
    with the existing MCP server, providing authentication, security, and
    full protocol compliance.

#### __init__

```python
def __init__(self, mcp_server, config)
```

Initialize the enhanced TCP server.

        Args:
            mcp_server: The MCP server instance
            config: Server configuration

#### get_server_statistics

```python
def get_server_statistics(self)
```

Get server statistics.

        Returns:
            Dictionary of server statistics
