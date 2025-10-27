"""Resource manager for DShield MCP server."""

import asyncio
from collections.abc import Callable
from typing import Any


class ResourceManager:
    """Manages resource cleanup during shutdown."""

    def __init__(self) -> None:
        """Initialize the resource manager."""
        self.resources: list[Any] = []
        self.cleanup_handlers: list[Callable[[], Any]] = []

    def register_resource(self, resource: Any, cleanup_func: Callable[[], Any]) -> None:
        """Register a resource with its cleanup function.

        Args:
            resource: The resource to track.
            cleanup_func: Function to call for cleanup.
        """
        self.resources.append(resource)
        self.cleanup_handlers.append(cleanup_func)

    def register_cleanup_handler(self, handler_func: Callable[[], Any]) -> None:
        """Register a cleanup handler function.

        Args:
            handler_func: Function to call during cleanup.
        """
        self.cleanup_handlers.append(handler_func)

    async def cleanup_all(self) -> None:
        """Execute all registered cleanup handlers."""
        for handler in self.cleanup_handlers:
            try:
                result = handler()
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                print(f"[MCP SERVER] Resource cleanup error: {e}")

    async def force_cleanup(self) -> None:
        """Force cleanup of all resources."""
        await self.cleanup_all()
