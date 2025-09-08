# api_key_panel

API key management panel for DShield MCP TUI.

This module provides a panel for managing API keys, including viewing,
generating, and deleting API keys stored in 1Password.

## APIKeyDelete

Message sent when an API key should be deleted.

#### __init__

```python
def __init__(self, key_id)
```

Initialize API key delete message.

        Args:
            key_id: The unique identifier of the API key to delete

## APIKeyRotate

Message sent when an API key should be rotated.

#### __init__

```python
def __init__(self, key_id)
```

Initialize API key rotate message.

        Args:
            key_id: The unique identifier of the API key to rotate

## APIKeyPanel

Panel for managing API keys.

#### __init__

```python
def __init__(self)
```

Initialize the API key panel.

#### compose

```python
def compose(self)
```

Compose the panel layout.

#### on_mount

```python
def on_mount(self)
```

Handle panel mount event.

#### on_button_pressed

```python
def on_button_pressed(self, event)
```

Handle button press events.

#### on_data_table_row_selected

```python
def on_data_table_row_selected(self, event)
```

Handle row selection in the data table.

#### _generate_new_key

```python
def _generate_new_key(self)
```

Open the API key generation screen.

#### _rotate_selected_key

```python
def _rotate_selected_key(self)
```

Rotate the selected API key.

#### _delete_selected_key

```python
def _delete_selected_key(self)
```

Delete the selected API key.

#### _view_key_details

```python
def _view_key_details(self)
```

View details of the selected API key.

#### refresh_api_keys

```python
def refresh_api_keys(self)
```

Refresh the API keys list.

#### _update_table

```python
def _update_table(self)
```

Update the data table with current API keys.

#### on_api_key_rotate

```python
def on_api_key_rotate(self, event)
```

Handle API key rotation.

#### on_api_key_delete

```python
def on_api_key_delete(self, event)
```

Handle API key deletion.
