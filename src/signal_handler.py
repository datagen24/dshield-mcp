"""Signal handler for graceful shutdown of DShield MCP server."""

import asyncio
import signal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp_server import DShieldMCPServer


class SignalHandler:
    """Manages signal handling for graceful shutdown."""

    def __init__(self, server: "DShieldMCPServer") -> None:
        """Initialize the signal handler.

        Args:
            server: The MCP server instance to manage.
        """
        self.server = server
        self._shutdown_event = asyncio.Event()
        self._shutdown_timeout = 30  # seconds

    def setup_handlers(self) -> None:
        """Set up signal handlers for SIGINT and SIGTERM."""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum: int, frame: Any) -> None:
        """Handle system signals for graceful shutdown.

        Args:
            signum: Signal number.
            frame: Current stack frame.
        """
        print(f"[MCP SERVER] Received signal {signum}, initiating graceful shutdown...", flush=True)
        asyncio.get_event_loop().create_task(self.graceful_shutdown())

    async def wait_for_shutdown(self) -> None:
        """Wait for shutdown event to be set."""
        await self._shutdown_event.wait()

    async def graceful_shutdown(self) -> None:
        """Perform graceful shutdown of the server."""
        print("[MCP SERVER] Running graceful shutdown procedures...", flush=True)
        await self.server.cleanup()
        self._shutdown_event.set()
