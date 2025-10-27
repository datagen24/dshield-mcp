# connection_manager

Connection manager for DShield MCP Server.

This module provides connection management functionality for TCP transport,
handling connection lifecycle, authentication, and monitoring.

## ConnectionManager

Manages TCP connections and API keys for the MCP server.

    This class handles the lifecycle of TCP connections, API key management,
    authentication, and connection monitoring.

    Attributes:
        op_secrets: OnePassword secrets manager
        api_keys: Dictionary of API keys by key value
        connections: Set of active connections
        config: Connection management configuration

#### __init__

```python
def __init__(self, config)
```

Initialize the connection manager.

        Args:
            config: Connection management configuration

#### revoke_api_key

```python
def revoke_api_key(self, key_value)
```

Revoke an API key.

        Args:
            key_value: The API key value to revoke

        Returns:
            True if key was revoked, False if not found

#### add_connection

```python
def add_connection(self, connection)
```

Add a connection to the manager.

        Args:
            connection: The connection to add

#### remove_connection

```python
def remove_connection(self, connection)
```

Remove a connection from the manager.

        Args:
            connection: The connection to remove

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

#### get_api_keys_info

```python
def get_api_keys_info(self)
```

Get information about all API keys.

        Returns:
            List of API key information dictionaries

#### get_active_api_keys_count

```python
def get_active_api_keys_count(self)
```

Get the number of active API keys.

        Returns:
            Number of active API keys

#### cleanup_expired_keys

```python
def cleanup_expired_keys(self)
```

Clean up expired API keys.

        Returns:
            Number of keys cleaned up

#### get_statistics

```python
def get_statistics(self)
```

Get connection manager statistics.

        Returns:
            Dictionary of statistics
