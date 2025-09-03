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
def __init__(self, id)
```

Initialize the server panel.

        Args:
            id: Panel ID

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

#### _initialize_config_inputs

```python
def _initialize_config_inputs(self)
```

Initialize configuration input fields.

#### update_server_status

```python
def update_server_status(self, running)
```

Update server running status.

        Args:
            running: Whether the server is running

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

#### on_input_changed

```python
def on_input_changed(self, event)
```

Handle input field changes.

        Args:
            event: Input change event

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

#### _apply_config

```python
def _apply_config(self)
```

Apply configuration changes.

#### _reset_config

```python
def _reset_config(self)
```

Reset configuration to defaults.

#### get_server_configuration

```python
def get_server_configuration(self)
```

Get current server configuration from inputs.

        Returns:
            Dictionary of server configuration

#### set_server_configuration

```python
def set_server_configuration(self, config)
```

Set server configuration in inputs.

        Args:
            config: Server configuration dictionary

#### get_server_health

```python
def get_server_health(self)
```

Get server health information.

        Returns:
            Dictionary of server health information
