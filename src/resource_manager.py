"""Resource manager for DShield MCP server."""
import asyncio
from typing import Any, Callable, List


class ResourceManager:
    """Manages resource cleanup during shutdown."""

    def __init__(self) -> None:
        self.resources: List[Any] = []
        self.cleanup_handlers: List[Callable[[], Any]] = []

    def register_resource(self, resource: Any, cleanup_func: Callable[[], Any]) -> None:
        self.resources.append(resource)
        self.cleanup_handlers.append(cleanup_func)

    def register_cleanup_handler(self, handler_func: Callable[[], Any]) -> None:
        self.cleanup_handlers.append(handler_func)

    async def cleanup_all(self) -> None:
        for handler in self.cleanup_handlers:
            try:
                result = handler()
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                print(f"[MCP SERVER] Resource cleanup error: {e}")

    async def force_cleanup(self) -> None:
        await self.cleanup_all()
