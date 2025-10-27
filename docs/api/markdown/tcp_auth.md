# tcp_auth

TCP authentication system for DShield MCP Server.

This module provides authentication functionality for TCP connections,
including API key validation, permission checking, and session management.

## AuthenticationError

Exception raised for authentication-related errors.

    Attributes:
        error_code: JSON-RPC error code
        message: Error message
        details: Additional error details

#### __init__

```python
def __init__(self, error_code, message, details)
```

Initialize authentication error.

        Args:
            error_code: JSON-RPC error code
            message: Error message
            details: Additional error details

## TCPAuthenticator

Handles authentication for TCP connections.

    This class manages API key validation, permission checking, and
    session management for TCP-based MCP connections.

    Attributes:
        connection_manager: Connection manager instance
        error_handler: MCP error handler instance
        sessions: Active authentication sessions
        config: Authentication configuration

#### __init__

```python
def __init__(self, connection_manager, error_handler, config)
```

Initialize the TCP authenticator.

        Args:
            connection_manager: Connection manager instance
            error_handler: MCP error handler instance
            config: Authentication configuration

#### _check_session_limits

```python
def _check_session_limits(self, api_key)
```

Check if session limits are exceeded for an API key.

        Args:
            api_key: The API key to check

        Returns:
            True if session limits are not exceeded, False otherwise

#### _create_session

```python
def _create_session(self, connection, api_key_obj)
```

Create a new authentication session.

        Args:
            connection: The TCP connection
            api_key_obj: The validated API key object

        Returns:
            Session ID for the new session

#### _is_session_expired

```python
def _is_session_expired(self, session)
```

Check if a session has expired.

        Args:
            session: Session dictionary

        Returns:
            True if session has expired, False otherwise

#### validate_session

```python
def validate_session(self, session_id)
```

Validate an authentication session.

        Args:
            session_id: Session ID to validate

        Returns:
            Session information if valid, None if invalid

#### revoke_session

```python
def revoke_session(self, session_id)
```

Revoke an authentication session.

        Args:
            session_id: Session ID to revoke

        Returns:
            True if session was revoked, False if not found

#### revoke_all_sessions_for_key

```python
def revoke_all_sessions_for_key(self, api_key)
```

Revoke all sessions for a specific API key.

        Args:
            api_key: API key to revoke sessions for

        Returns:
            Number of sessions revoked

#### check_permission

```python
def check_permission(self, session_id, permission)
```

Check if a session has a specific permission.

        Args:
            session_id: Session ID to check
            permission: Permission to check

        Returns:
            True if permission is granted, False otherwise

#### check_tool_permission

```python
def check_tool_permission(self, session_id, tool_name)
```

Check if a session has permission to use a specific tool.

        Args:
            session_id: Session ID to check
            tool_name: Tool name to check

        Returns:
            True if tool permission is granted, False otherwise

#### get_session_info

```python
def get_session_info(self, session_id)
```

Get information about a session.

        Args:
            session_id: Session ID

        Returns:
            Session information if valid, None if invalid

#### get_all_sessions_info

```python
def get_all_sessions_info(self)
```

Get information about all active sessions.

        Returns:
            List of session information dictionaries

#### cleanup_expired_sessions

```python
def cleanup_expired_sessions(self)
```

Clean up expired sessions.

        Returns:
            Number of sessions cleaned up

#### get_statistics

```python
def get_statistics(self)
```

Get authentication statistics.

        Returns:
            Dictionary of authentication statistics
