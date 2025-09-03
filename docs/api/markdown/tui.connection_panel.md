# connection_panel

Connection management panel for DShield MCP TUI.

This module provides a terminal UI panel for managing TCP connections,
including viewing active connections, disconnecting clients, and managing API keys.

## ConnectionDisconnect

Message sent when a connection should be disconnected.

#### __init__

```python
def __init__(self, client_address)
```

Initialize connection disconnect message.

        Args:
            client_address: Address of the client to disconnect

## APIKeyGenerate

Message sent when a new API key should be generated.

#### __init__

```python
def __init__(self, permissions)
```

Initialize API key generation message.

        Args:
            permissions: Optional permissions for the new API key

## APIKeyRevoke

Message sent when an API key should be revoked.

#### __init__

```python
def __init__(self, api_key_id)
```

Initialize API key revocation message.

        Args:
            api_key_id: ID of the API key to revoke

## ConnectionPanel

Panel for managing TCP connections and API keys.

    This panel displays active connections, allows disconnecting clients,
    and provides API key management functionality.

#### __init__

```python
def __init__(self, id)
```

Initialize the connection panel.

        Args:
            id: Panel ID

#### compose

```python
def compose(self)
```

Compose the connection panel layout.

        Returns:
            ComposeResult: The composed UI elements

#### on_mount

```python
def on_mount(self)
```

Handle panel mount event.

#### update_connections

```python
def update_connections(self, connections)
```

Update the connections display.

        Args:
            connections: List of connection information

#### update_api_keys

```python
def update_api_keys(self, api_keys)
```

Update the API keys display.

        Args:
            api_keys: List of API key information

#### on_button_pressed

```python
def on_button_pressed(self, event)
```

Handle button press events.

        Args:
            event: Button press event

#### on_data_table_row_selected

```python
def on_data_table_row_selected(self, event)
```

Handle data table row selection.

        Args:
            event: Row selection event

#### _disconnect_selected_connection

```python
def _disconnect_selected_connection(self)
```

Disconnect the selected connection.

#### _disconnect_all_connections

```python
def _disconnect_all_connections(self)
```

Disconnect all active connections.

#### _refresh_connections

```python
def _refresh_connections(self)
```

Refresh the connections display.

#### _generate_api_key

```python
def _generate_api_key(self)
```

Generate a new API key.

#### _revoke_selected_api_key

```python
def _revoke_selected_api_key(self)
```

Revoke the selected API key.

#### _refresh_api_keys

```python
def _refresh_api_keys(self)
```

Refresh the API keys display.

#### _select_connection

```python
def _select_connection(self, row_key)
```

Select a connection.

        Args:
            row_key: Row key of the selected connection

#### _select_api_key

```python
def _select_api_key(self, row_key)
```

Select an API key.

        Args:
            row_key: Row key of the selected API key

#### get_connection_statistics

```python
def get_connection_statistics(self)
```

Get connection statistics.

        Returns:
            Dictionary of connection statistics

#### get_api_key_statistics

```python
def get_api_key_statistics(self)
```

Get API key statistics.

        Returns:
            Dictionary of API key statistics
