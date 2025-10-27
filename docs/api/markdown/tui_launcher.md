# tui_launcher

TUI launcher for DShield MCP Server.

This module provides the main entry point for the terminal user interface,
handling server process management and TUI integration.

## TUIProcessManager

Manages the MCP server process for the TUI.

    This class handles starting, stopping, and monitoring the MCP server
    process when running in TUI mode.

#### __init__

```python
def __init__(self, config_path)
```

Initialize the TUI process manager.

        Args:
            config_path: Optional path to configuration file

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

Get server process status.

        Returns:
            Dictionary of server status information

## DShieldTUILauncher

Main launcher for the DShield MCP TUI.

    This class coordinates the TUI application and server process management.

#### __init__

```python
def __init__(self, config_path)
```

Initialize the TUI launcher.

        Args:
            config_path: Optional path to configuration file

#### run

```python
def run(self)
```

Run the TUI application with server management.

        This method starts the TUI application and manages the server process.

#### _start_server_sync

```python
def _start_server_sync(self)
```

Start the server (called by TUI app).

#### _stop_server_sync

```python
def _stop_server_sync(self)
```

Stop the server (called by TUI app).

#### _restart_server_sync

```python
def _restart_server_sync(self)
```

Restart the server (called by TUI app).

#### cleanup_sync

```python
def cleanup_sync(self)
```

Clean up resources in sync context.

### run_tui

```python
def run_tui(config_path)
```

Run the TUI application.

    Args:
        config_path: Optional path to configuration file
