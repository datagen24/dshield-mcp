# stdio_transport

STDIO transport implementation for DShield MCP Server.

This module provides the STDIO-based transport implementation, which is the
default transport mechanism for MCP servers using stdin/stdout for communication.

## STDIOTransport

STDIO-based transport implementation.

    This transport uses stdin/stdout for MCP protocol communication,
    which is the standard transport mechanism for MCP servers.

    Attributes:
        server: The MCP server instance
        config: STDIO-specific configuration
        read_stream: Input stream for reading messages
        write_stream: Output stream for writing messages

#### __init__

```python
def __init__(self, server, config)
```

Initialize the STDIO transport.

        Args:
            server: The MCP server instance
            config: STDIO-specific configuration

#### transport_type

```python
def transport_type(self)
```

Get the transport type identifier.

        Returns:
            'stdio' for STDIO transport

#### get_streams

```python
def get_streams(self)
```

Get the read and write streams.

        Returns:
            Tuple of (read_stream, write_stream)

#### is_available

```python
def is_available(self)
```

Check if STDIO transport is available.

        STDIO transport is always available if stdin/stdout are available.

        Returns:
            True if STDIO is available, False otherwise
