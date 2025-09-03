# connection_manager

Connection manager for DShield MCP Server.

This module provides connection management functionality for TCP transport,
handling connection lifecycle, authentication, and monitoring.

## APIKey

Represents an API key with associated permissions and metadata.

    Attributes:
        key_id: Unique identifier for the API key
        key_value: The actual API key value
        permissions: Dictionary of permissions for this key
        created_at: Timestamp when the key was created
        expires_at: Timestamp when the key expires
        last_used: Timestamp of last usage
        usage_count: Number of times the key has been used
        is_active: Whether the key is currently active

#### __init__

```python
def __init__(self, key_id, key_value, permissions, expires_days)
```

Initialize an API key.

        Args:
            key_id: Unique identifier for the API key
            key_value: The actual API key value
            permissions: Dictionary of permissions for this key
            expires_days: Number of days until the key expires

#### is_expired

```python
def is_expired(self)
```

Check if the API key has expired.

        Returns:
            True if the key has expired, False otherwise

#### is_valid

```python
def is_valid(self)
```

Check if the API key is valid (active and not expired).

        Returns:
            True if the key is valid, False otherwise

#### update_usage

```python
def update_usage(self)
```

Update the usage statistics for this key.

#### to_dict

```python
def to_dict(self)
```

Convert the API key to a dictionary.

        Returns:
            Dictionary representation of the API key

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
