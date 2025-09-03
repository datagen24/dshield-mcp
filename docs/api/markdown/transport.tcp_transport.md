# tcp_transport

TCP transport implementation for DShield MCP Server.

This module provides the TCP socket-based transport implementation, enabling
network-based MCP protocol communication with authentication and rate limiting.

## TCPConnection

Represents a TCP connection to the MCP server.

    Attributes:
        reader: StreamReader for reading from the connection
        writer: StreamWriter for writing to the connection
        client_address: Client IP address and port
        api_key: API key for this connection
        connected_at: Timestamp when connection was established
        last_activity: Timestamp of last activity
        rate_limiter: Rate limiter for this connection

#### __init__

```python
def __init__(self, reader, writer, client_address, api_key)
```

Initialize a TCP connection.

        Args:
            reader: StreamReader for reading from the connection
            writer: StreamWriter for writing to the connection
            client_address: Client IP address and port
            api_key: API key for this connection

#### update_activity

```python
def update_activity(self)
```

Update the last activity timestamp.

#### is_expired

```python
def is_expired(self, timeout_seconds)
```

Check if the connection has expired.

        Args:
            timeout_seconds: Connection timeout in seconds

        Returns:
            True if connection has expired, False otherwise

## RateLimiter

Rate limiter for TCP connections.

    Implements token bucket rate limiting for individual connections.

#### __init__

```python
def __init__(self, requests_per_minute, burst_limit)
```

Initialize the rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute
            burst_limit: Maximum burst requests

#### is_allowed

```python
def is_allowed(self)
```

Check if a request is allowed.

        Returns:
            True if request is allowed, False if rate limited

## TCPTransport

TCP socket-based transport implementation.

    This transport uses TCP sockets for MCP protocol communication,
    supporting multiple concurrent connections with authentication and rate limiting.

    Attributes:
        server: The MCP server instance
        config: TCP-specific configuration
        server_socket: TCP server socket
        connections: Set of active connections
        is_running: Whether the transport is currently running

#### __init__

```python
def __init__(self, server, config)
```

Initialize the TCP transport.

        Args:
            server: The MCP server instance
            config: TCP-specific configuration

#### transport_type

```python
def transport_type(self)
```

Get the transport type identifier.

        Returns:
            'tcp' for TCP transport

#### get_connection_count

```python
def get_connection_count(self)
```

Get the number of active connections.

        Returns:
            Number of active connections

#### get_connections_info

```python
def get_connections_info(self)
```

Get information about active connections.

        Returns:
            List of connection information dictionaries
