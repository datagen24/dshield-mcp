#!/usr/bin/env python3
"""STDIO transport implementation for DShield MCP Server.

This module provides the STDIO-based transport implementation, which is the
default transport mechanism for MCP servers using stdin/stdout for communication.
"""

import sys
from typing import Any, Dict, Optional, Tuple

import structlog
from mcp.server.stdio import stdio_server  # type: ignore

from .base_transport import BaseTransport, TransportError

logger = structlog.get_logger(__name__)


class STDIOTransport(BaseTransport):
    """STDIO-based transport implementation.
    
    This transport uses stdin/stdout for MCP protocol communication,
    which is the standard transport mechanism for MCP servers.
    
    Attributes:
        server: The MCP server instance
        config: STDIO-specific configuration
        read_stream: Input stream for reading messages
        write_stream: Output stream for writing messages

    """

    def __init__(self, server: Any, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the STDIO transport.
        
        Args:
            server: The MCP server instance
            config: STDIO-specific configuration

        """
        super().__init__(server, config)
        self.read_stream = None
        self.write_stream = None

    @property
    def transport_type(self) -> str:
        """Get the transport type identifier.
        
        Returns:
            'stdio' for STDIO transport

        """
        return "stdio"

    async def start(self) -> None:
        """Start the STDIO transport.
        
        Initializes the STDIO server and sets up the read/write streams.
        
        Raises:
            TransportError: If the STDIO transport fails to start

        """
        try:
            self.logger.info("Starting STDIO transport")

            # Create STDIO server context
            self.stdio_context = stdio_server()
            self.read_stream, self.write_stream = await self.stdio_context.__aenter__()

            self.is_running = True
            self.logger.info("STDIO transport started successfully")

        except Exception as e:
            self.logger.error("Failed to start STDIO transport", error=str(e))
            raise TransportError(f"Failed to start STDIO transport: {e}", "stdio")

    async def stop(self) -> None:
        """Stop the STDIO transport.
        
        Closes the STDIO streams and cleans up resources.
        """
        try:
            self.logger.info("Stopping STDIO transport")

            if hasattr(self, "stdio_context") and self.stdio_context:
                await self.stdio_context.__aexit__(None, None, None)

            self.read_stream = None
            self.write_stream = None
            self.is_running = False

            self.logger.info("STDIO transport stopped successfully")

        except Exception as e:
            self.logger.error("Error stopping STDIO transport", error=str(e))

    async def run(self) -> None:
        """Run the STDIO transport main loop.
        
        Executes the MCP server with STDIO streams, handling the complete
        MCP protocol lifecycle including initialization and message processing.
        
        Raises:
            TransportError: If the transport fails during execution

        """
        if not self.is_running:
            raise TransportError("STDIO transport is not running", "stdio")

        try:
            self.logger.info("Running STDIO transport main loop")

            # Run the MCP server with STDIO streams
            await self.server.run(
                self.read_stream,
                self.write_stream,
                self.server.get_initialization_options(),
            )

        except Exception as e:
            self.logger.error("STDIO transport main loop failed", error=str(e))
            raise TransportError(f"STDIO transport main loop failed: {e}", "stdio")

    def get_streams(self) -> Tuple[Any, Any]:
        """Get the read and write streams.
        
        Returns:
            Tuple of (read_stream, write_stream)

        """
        return self.read_stream, self.write_stream

    def is_available(self) -> bool:
        """Check if STDIO transport is available.
        
        STDIO transport is always available if stdin/stdout are available.
        
        Returns:
            True if STDIO is available, False otherwise

        """
        try:
            # Check if stdin/stdout are available and not redirected to a file
            return (sys.stdin.isatty() or not sys.stdin.closed) and \
                   (sys.stdout.isatty() or not sys.stdout.closed)
        except Exception:
            return False
