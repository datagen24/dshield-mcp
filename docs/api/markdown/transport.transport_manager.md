# transport_manager

Transport manager for DShield MCP Server.

This module provides the transport manager that handles transport selection,
lifecycle management, and coordination between different transport types.

## TransportManager

Manages transport selection and lifecycle for the MCP server.

    This class handles the selection of appropriate transport mechanisms
    based on configuration and execution context, managing the lifecycle
    of transport instances.

    Attributes:
        server: The MCP server instance
        config: Transport configuration
        current_transport: Currently active transport
        transport_registry: Registry of available transport types

#### __init__

```python
def __init__(self, server, config)
```

Initialize the transport manager.

        Args:
            server: The MCP server instance
            config: Transport configuration

#### detect_transport_mode

```python
def detect_transport_mode(self)
```

Detect the appropriate transport mode based on execution context.

        This method implements the transport detection logic:
        1. Check if TUI is the parent process (process parent detection)
        2. Fall back to command-line flag detection
        3. Default to STDIO mode for safety

        Returns:
            Transport mode identifier ('stdio' or 'tcp')

#### _is_tui_parent

```python
def _is_tui_parent(self)
```

Check if TUI is the parent process using multiple detection strategies.

        Detection order:
        1. Check environment variable DSHIELD_TUI_MODE
        2. Check parent process name/cmdline for TUI indicators
        3. Check for TUI-specific markers in command line
        4. Default to STDIO if uncertain

        Returns:
            True if TUI appears to be the parent process

#### _has_tcp_flag

```python
def _has_tcp_flag(self)
```

Check for TCP-related command-line flags.

        Returns:
            True if TCP flags are present

#### create_transport

```python
def create_transport(self, transport_type)
```

Create a transport instance.

        Args:
            transport_type: Type of transport to create (auto-detected if None)

        Returns:
            Transport instance

        Raises:
            TransportError: If transport type is not supported

#### _get_transport_config

```python
def _get_transport_config(self, transport_type)
```

Get configuration for a specific transport type.

        Args:
            transport_type: Type of transport

        Returns:
            Transport-specific configuration

#### get_current_transport

```python
def get_current_transport(self)
```

Get the currently active transport.

        Returns:
            Current transport instance or None

#### get_transport_info

```python
def get_transport_info(self)
```

Get information about the current transport.

        Returns:
            Transport information dictionary
