"""Signal handler for graceful shutdown of DShield MCP server."""
import asyncio
import signal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp_server import DShieldMCPServer

class SignalHandler:
    """Manages signal handling for graceful shutdown."""
    def __init__(self, server: 'DShieldMCPServer') -> None:
        self.server = server
        self._shutdown_event = asyncio.Event()
        self._shutdown_timeout = 30  # seconds

    def setup_handlers(self) -> None:
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        print(f"[MCP SERVER] Received signal {signum}, initiating graceful shutdown...", flush=True)
        asyncio.get_event_loop().create_task(self.graceful_shutdown())

    async def wait_for_shutdown(self):
        await self._shutdown_event.wait()

    async def graceful_shutdown(self):
        print("[MCP SERVER] Running graceful shutdown procedures...", flush=True)
        await self.server.cleanup()
        self._shutdown_event.set() 