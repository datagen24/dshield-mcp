# operation_tracker

Operation tracker for DShield MCP server.

## OperationTracker

Tracks active operations for graceful shutdown.

#### __init__

```python
def __init__(self)
```

Initialize the operation tracker.

#### register_operation

```python
def register_operation(self, operation_id, task, timeout)
```

Register an active operation for tracking.

        Args:
            operation_id: Unique identifier for the operation.
            task: The asyncio task to track.
            timeout: Timeout in seconds for the operation.

#### complete_operation

```python
def complete_operation(self, operation_id)
```

Mark an operation as completed and remove it from tracking.

        Args:
            operation_id: Unique identifier for the operation to complete.

#### get_active_operations

```python
def get_active_operations(self)
```

Get list of active operation IDs.

        Returns:
            List of active operation identifiers.
