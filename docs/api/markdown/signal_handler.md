# signal_handler

Signal handler for graceful shutdown of DShield MCP server.

## SignalHandler

Manages signal handling for graceful shutdown.

#### __init__

```python
def __init__(self, server)
```

Initialize the signal handler.

        Args:
            server: The MCP server instance to manage.

#### setup_handlers

```python
def setup_handlers(self)
```

Set up signal handlers for SIGINT and SIGTERM.

#### signal_handler

```python
def signal_handler(self, signum, frame)
```

Handle system signals for graceful shutdown.

        Args:
            signum: Signal number.
            frame: Current stack frame.
