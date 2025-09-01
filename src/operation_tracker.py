"""Operation tracker for DShield MCP server."""
import asyncio
from typing import Dict, List


class OperationTracker:
    """Tracks active operations for graceful shutdown."""

    def __init__(self) -> None:
        self.active_operations: Dict[str, asyncio.Task] = {}
        self.operation_timeouts: Dict[str, int] = {}

    def register_operation(self, operation_id: str, task: asyncio.Task, timeout: int = 30) -> None:
        self.active_operations[operation_id] = task
        self.operation_timeouts[operation_id] = timeout

    def complete_operation(self, operation_id: str) -> None:
        if operation_id in self.active_operations:
            del self.active_operations[operation_id]
            del self.operation_timeouts[operation_id]

    async def wait_for_operations(self, timeout: int = 30) -> None:
        if not self.active_operations:
            return
        await asyncio.wait([task for task in self.active_operations.values()], timeout=timeout)

    def get_active_operations(self) -> List[str]:
        return list(self.active_operations.keys())
