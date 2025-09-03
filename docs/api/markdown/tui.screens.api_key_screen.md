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

#### on_mount

```python
def on_mount(self)
```

Handle screen mount event.
