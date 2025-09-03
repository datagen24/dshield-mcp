# tui_app

Main TUI application for DShield MCP Server.

This module provides the main terminal user interface application using textual,
including layout management, event handling, and integration with the TCP server.

### _get_dshield_mcp_server

```python
def _get_dshield_mcp_server()
```

Get DShieldMCPServer class with late import to avoid circular dependencies.

## ServerStatusUpdate

Message sent when server status is updated.

#### __init__

```python
def __init__(self, status)
```

Initialize server status update message.

        Args:
            status: Server status information

## ConnectionUpdate

Message sent when connection information is updated.

#### __init__

```python
def __init__(self, connections)
```

Initialize connection update message.

        Args:
            connections: List of connection information

## LogUpdate

Message sent when new log entries are available.

#### __init__

```python
def __init__(self, log_entries)
```

Initialize log update message.

        Args:
            log_entries: List of log entries

## DShieldTUIApp

Main TUI application for DShield MCP Server.

    This class provides the main terminal user interface with panels for
    connection management, server control, and log monitoring.

#### __init__

```python
def __init__(self, config_path)
```

Initialize the TUI application.

        Args:
            config_path: Optional path to configuration file

#### compose

```python
def compose(self)
```

Compose the TUI layout.

        Returns:
            ComposeResult: The composed UI elements

#### on_mount

```python
def on_mount(self)
```

Handle application mount event.

#### on_unmount

```python
def on_unmount(self)
```

Handle application unmount event.

#### _periodic_update

```python
def _periodic_update(self)
```

Periodic update task for refreshing UI data.

#### _update_ui_data

```python
def _update_ui_data(self)
```

Update UI data from server components.

#### _update_server_panel_status

```python
def _update_server_panel_status(self)
```

Update the server panel status display.

#### _update_connection_panel

```python
def _update_connection_panel(self)
```

Update the connection panel with API keys and connections.

#### _add_log_entry

```python
def _add_log_entry(self, level, message)
```

Add a log entry to the log panel.

#### action_quit

```python
def action_quit(self)
```

Quit the application.

#### action_restart_server

```python
def action_restart_server(self)
```

Restart the TCP server.

#### action_stop_server

```python
def action_stop_server(self)
```

Stop the TCP server.

#### action_test_log

```python
def action_test_log(self)
```

Test log entry creation.

#### action_clear_logs

```python
def action_clear_logs(self)
```

Clear the log display.

#### action_show_help

```python
def action_show_help(self)
```

Show help information.

#### action_switch_panel

```python
def action_switch_panel(self)
```

Switch between panels.

#### on_server_start

```python
def on_server_start(self, event)
```

Handle server start message from server panel.

#### on_server_stop

```python
def on_server_stop(self, event)
```

Handle server stop message from server panel.

#### on_server_restart

```python
def on_server_restart(self, event)
```

Handle server restart message from server panel.

#### _start_server

```python
def _start_server(self)
```

Start the TCP server.

#### _stop_server

```python
def _stop_server(self)
```

Stop the TCP server.

#### _create_mcp_server

```python
def _create_mcp_server(self)
```

Create and initialize DShieldMCPServer instance.

        Returns:
            Initialized DShieldMCPServer instance

#### on_server_status_update

```python
def on_server_status_update(self, message)
```

Handle server status update message.

#### on_connection_update

```python
def on_connection_update(self, message)
```

Handle connection update message.

#### on_log_update

```python
def on_log_update(self, message)
```

Handle log update message.

#### watch_server_running

```python
def watch_server_running(self, running)
```

Watch for server running state changes.

#### watch_server_port

```python
def watch_server_port(self, port)
```

Watch for server port changes.

#### watch_server_address

```python
def watch_server_address(self, address)
```

Watch for server address changes.

### run_tui

```python
def run_tui(config_path)
```

Run the TUI application.

    Args:
        config_path: Optional path to configuration file
