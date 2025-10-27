# server_panel

Server management panel for DShield MCP TUI.

This module provides a terminal UI panel for managing the MCP server,
including starting/stopping the server, viewing server status, and configuration.

## ServerStart

Message sent when server should be started.

## ServerStop

Message sent when server should be stopped.

## ServerRestart

Message sent when server should be restarted.

## ServerConfigUpdate

Message sent when server configuration should be updated.

#### __init__

```python
def __init__(self, config)
```

Initialize server config update message.

        Args:
            config: New server configuration

## ServerPanel

Panel for managing the MCP server.

    This panel provides controls for starting/stopping the server,
    viewing server status, and managing server configuration.

#### __init__

```python
def __init__(self, id, config_path)
```

Initialize the server panel.

        Args:
            id: Panel ID
            config_path: Optional path to configuration file

#### compose

```python
def compose(self)
```

Compose the server panel layout.

        Returns:
            ComposeResult: The composed UI elements

#### on_mount

```python
def on_mount(self)
```

Handle panel mount event.

#### _initialize_config_display

```python
def _initialize_config_display(self)
```

Initialize configuration display with effective configuration.

#### _update_server_status

```python
def _update_server_status(self)
```

Update server status from process manager.

#### _on_server_status_update

```python
def _on_server_status_update(self, message)
```

Handle server status update from process manager.

        Args:
            message: Server status update message

#### update_server_statistics

```python
def update_server_statistics(self, stats)
```

Update server statistics display.

        Args:
            stats: Server statistics dictionary

#### on_button_pressed

```python
def on_button_pressed(self, event)
```

Handle button press events.

        Args:
            event: Button press event

#### _start_server

```python
def _start_server(self)
```

Start the server.

#### _stop_server

```python
def _stop_server(self)
```

Stop the server.

#### _restart_server

```python
def _restart_server(self)
```

Restart the server.

#### get_server_health

```python
def get_server_health(self)
```

Get server health information.

        Returns:
            Dictionary of server health information
