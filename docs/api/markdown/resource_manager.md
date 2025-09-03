# resource_manager

Resource manager for DShield MCP server.

## ResourceManager

Manages resource cleanup during shutdown.

#### __init__

```python
def __init__(self)
```

Initialize the resource manager.

#### register_resource

```python
def register_resource(self, resource, cleanup_func)
```

Register a resource with its cleanup function.

        Args:
            resource: The resource to track.
            cleanup_func: Function to call for cleanup.

#### register_cleanup_handler

```python
def register_cleanup_handler(self, handler_func)
```

Register a cleanup handler function.

        Args:
            handler_func: Function to call during cleanup.
