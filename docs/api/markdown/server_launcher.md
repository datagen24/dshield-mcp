# server_launcher

Server launcher for DShield MCP Server.

This module provides the main entry point for the DShield MCP server,
supporting both STDIO and TCP transport modes with automatic detection.

## DShieldServerLauncher

Launcher for the DShield MCP server with transport selection.

    This class handles the initialization and startup of the MCP server
    with automatic transport mode detection and configuration.

#### __init__

```python
def __init__(self, config_path)
```

Initialize the server launcher.

        Args:
            config_path: Optional path to configuration file
