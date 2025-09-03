"""Operation tracker for DShield MCP server."""

import asyncio
from typing import Any


class OperationTracker:
    """Tracks active operations for graceful shutdown."""

    def __init__(self) -> None:
        """Initialize the operation tracker."""
        self.active_operations: dict[str, asyncio.Task[Any]] = {}
        self.operation_timeouts: dict[str, int] = {}

    def register_operation(self, operation_id: str, task: asyncio.Task[Any], timeout: int = 30) -> None:
        """Register an active operation for tracking.

        Args:
            operation_id: Unique identifier for the operation.
            task: The asyncio task to track.
            timeout: Timeout in seconds for the operation.
        """
        self.active_operations[operation_id] = task
        self.operation_timeouts[operation_id] = timeout

    def complete_operation(self, operation_id: str) -> None:
        """Mark an operation as completed and remove it from tracking.

        Args:
            operation_id: Unique identifier for the operation to complete.
        """
        if operation_id in self.active_operations:
            del self.active_operations[operation_id]
            del self.operation_timeouts[operation_id]

    async def wait_for_operations(self, timeout: int = 30) -> None:
        """Wait for all active operations to complete.

        Args:
            timeout: Maximum time to wait in seconds.
        """
        if not self.active_operations:
            return
        await asyncio.wait([task for task in self.active_operations.values()], timeout=timeout)

    def get_active_operations(self) -> list[str]:
        """Get list of active operation IDs.

        Returns:
            List of active operation identifiers.
        """
        return list(self.active_operations.keys())
