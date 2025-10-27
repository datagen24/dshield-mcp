# server_process_manager

Server Process Manager for DShield MCP TUI.

This module provides a process manager wrapper that handles TCP server lifecycle
management with proper timeout handling and event emission for the TUI.

## ServerStatusUpdate

Message sent when server status is updated.

#### __init__

```python
def __init__(self, status)
```

Initialize server status update message.

        Args:
            status: Server status information

## ServerProcessManager

Manages the MCP server process with timeout handling and event emission.

    This class provides a wrapper around the TUIProcessManager that adds:
    - Proper timeout handling for graceful shutdown
    - Event emission for status updates
    - Configuration display
    - Status monitoring

    Attributes:
        config_path: Path to configuration file
        user_config: User configuration manager
        process_manager: Underlying TUI process manager
        server_running: Whether the server is currently running
        server_start_time: When the server was started
        graceful_shutdown_timeout: Timeout for graceful shutdown in seconds

#### __init__

```python
def __init__(self, config_path)
```

Initialize the server process manager.

        Args:
            config_path: Optional path to configuration file

#### add_status_handler

```python
def add_status_handler(self, handler)
```

Add a status update handler.

        Args:
            handler: Function to call when status updates

#### remove_status_handler

```python
def remove_status_handler(self, handler)
```

Remove a status update handler.

        Args:
            handler: Handler to remove

#### _emit_status_update

```python
def _emit_status_update(self, status)
```

Emit a status update to all handlers.

        Args:
            status: Status information to emit

#### is_server_running

```python
def is_server_running(self)
```

Check if the server process is running.

        Returns:
            True if server is running, False otherwise

#### get_server_status

```python
def get_server_status(self)
```

Get comprehensive server status information.

        Returns:
            Dictionary of server status information

#### get_effective_configuration

```python
def get_effective_configuration(self)
```

Get the effective server configuration.

        Returns:
            Dictionary of effective server configuration

#### _get_server_status

```python
def _get_server_status(self)
```

Get internal server status.

        Returns:
            Dictionary of server status information
