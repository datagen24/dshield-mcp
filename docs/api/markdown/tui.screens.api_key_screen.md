# api_key_screen

API key generation screen for DShield MCP TUI.

This module provides a modal screen for generating and configuring API keys
with permissions, expiration, and rate limiting options.

## APIKeyGenerated

Message sent when an API key has been generated.

#### __init__

```python
def __init__(self, key_config)
```

Initialize API key generated message.

        Args:
            key_config: Configuration for the generated API key

## APIKeyGenerationScreen

Modal screen for API key configuration and generation.

#### __init__

```python
def __init__(self)
```

Initialize the API key generation screen.

#### compose

```python
def compose(self)
```

Compose the screen layout.

#### on_button_pressed

```python
def on_button_pressed(self, event)
```

Handle button press events.

#### _generate_api_key

```python
def _generate_api_key(self)
```

Generate API key with the configured settings.

#### _confirm_key_generation

```python
def _confirm_key_generation(self)
```

Confirm key generation and send the message.

#### _clear_plaintext_key

```python
def _clear_plaintext_key(self)
```

Clear the plaintext key from memory for security.

#### on_dismiss

```python
def on_dismiss(self)
```

Handle screen dismissal - clear plaintext key.

#### on_mount

```python
def on_mount(self)
```

Handle screen mount event.

#### show_api_key_form

```python
def show_api_key_form(self)
```

Show the API key configuration form.

        Returns:
            True when the form is rendered.

#### _render_form

```python
def _render_form(self)
```

Render the configuration form (no-op for tests).

#### validate_api_key_input

```python
def validate_api_key_input(self, value)
```

Validate the API key input string.

        Args:
            value: The input string to validate

        Returns:
            True if the value matches allowed characters.

#### save_api_key

```python
def save_api_key(self, key)
```

Save the API key via helper.

        Args:
            key: The API key to save

        Returns:
            True on success.

#### _save_key

```python
def _save_key(self, key)
```

#### load_existing_api_key

```python
def load_existing_api_key(self)
```

Load an existing API key if present.

#### _load_key

```python
def _load_key(self)
```

#### generate_new_api_key

```python
def generate_new_api_key(self)
```

Generate a new API key via helper.

#### _generate_key

```python
def _generate_key(self)
```

#### show_api_key_status

```python
def show_api_key_status(self, key)
```

Show API key status using helper renderer.

#### _render_status

```python
def _render_status(self)
```

#### handle_key_validation

```python
def handle_key_validation(self, key)
```

Handle validation for the provided key via helper.

        Args:
            key: The API key to validate

        Returns:
            Validation result mapping

#### _validate_key

```python
def _validate_key(self, key)
```

#### show_help_text

```python
def show_help_text(self)
```

Show help text via helper renderer.

#### _render_help

```python
def _render_help(self)
```

#### navigate_back

```python
def navigate_back(self)
```

Navigate back from the screen via helper.

#### _navigate_back

```python
def _navigate_back(self)
```
