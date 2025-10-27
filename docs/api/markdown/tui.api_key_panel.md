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

#### app

```python
def app(self)
```

Return the active Textual app or a test override.

        - When `_app_override` is set (tests), return it.
        - Otherwise, defer to Textual's base implementation.
        - If there is no active app, return None.

#### app

```python
def app(self, value)
```

#### app

```python
def app(self)
```

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

#### set_api_key

```python
def set_api_key(self, key)
```

Set the current API key and refresh display.

        Args:
            key: API key value

        Returns:
            True when set.

#### _update_display

```python
def _update_display(self)
```

#### get_api_key

```python
def get_api_key(self)
```

Get the current API key if set.

#### validate_api_key

```python
def validate_api_key(self, key)
```

Validate API key format (alnum, underscore, dash).

#### clear_api_key

```python
def clear_api_key(self)
```

Clear stored API key.

#### is_key_visible

```python
def is_key_visible(self)
```

Return whether the key is visible (test helper).

#### toggle_key_visibility

```python
def toggle_key_visibility(self)
```

Toggle key visibility flag (test helper).

#### generate_new_key

```python
def generate_new_key(self)
```

Generate a new key and return it via helper.

#### _generate_key

```python
def _generate_key(self)
```

#### save_api_key

```python
def save_api_key(self, key)
```

Persist provided API key via helper.

#### _save_to_storage

```python
def _save_to_storage(self, key)
```

#### load_api_key

```python
def load_api_key(self)
```

Load API key via helper.

#### _load_from_storage

```python
def _load_from_storage(self)
```

#### rotate_api_key

```python
def rotate_api_key(self)
```

Rotate (generate and set) a new API key.
