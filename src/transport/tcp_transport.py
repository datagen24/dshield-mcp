#!/usr/bin/env python3
"""TCP transport implementation for DShield MCP Server.

This module provides the TCP socket-based transport implementation, enabling
network-based MCP protocol communication with authentication and rate limiting.
"""

import asyncio
import json
from datetime import datetime
from typing import Any

import structlog

from .base_transport import BaseTransport, TransportError

logger = structlog.get_logger(__name__)


class TCPConnection:
    """Represents a TCP connection to the MCP server.

    Attributes:
        reader: StreamReader for reading from the connection
        writer: StreamWriter for writing to the connection
        client_address: Client IP address and port
        api_key: API key for this connection
        connected_at: Timestamp when connection was established
        last_activity: Timestamp of last activity
        rate_limiter: Rate limiter for this connection

    """

    def __init__(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
        client_address: tuple[str, int],
        api_key: str | None = None,
    ) -> None:
        """Initialize a TCP connection.

        Args:
            reader: StreamReader for reading from the connection
            writer: StreamWriter for writing to the connection
            client_address: Client IP address and port
            api_key: API key for this connection

        """
        self.reader = reader
        self.writer = writer
        self.client_address = client_address
        self.api_key = api_key
        self.connected_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
        self.rate_limiter = RateLimiter()
        self.is_authenticated = api_key is not None
        self.is_initialized = False

    async def close(self) -> None:
        """Close the connection.

        Closes the writer and reader streams.
        """
        try:
            if self.writer:
                self.writer.close()
                await self.writer.wait_closed()
        except Exception as e:
            logger.warning(
                "Error closing TCP connection", client_address=self.client_address, error=str(e)
            )

    def update_activity(self) -> None:
        """Update the last activity timestamp."""
        self.last_activity = datetime.utcnow()

    def is_expired(self, timeout_seconds: int) -> bool:
        """Check if the connection has expired.

        Args:
            timeout_seconds: Connection timeout in seconds

        Returns:
            True if connection has expired, False otherwise

        """
        return (datetime.utcnow() - self.last_activity).total_seconds() > timeout_seconds


class RateLimiter:
    """Rate limiter for TCP connections.

    Implements token bucket rate limiting for individual connections.
    """

    def __init__(self, requests_per_minute: int = 60, burst_limit: int = 10) -> None:
        """Initialize the rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute
            burst_limit: Maximum burst requests

        """
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.tokens: float = float(burst_limit)
        self.last_refill = datetime.utcnow()

    def is_allowed(self) -> bool:
        """Check if a request is allowed.

        Returns:
            True if request is allowed, False if rate limited

        """
        now = datetime.utcnow()
        time_passed = (now - self.last_refill).total_seconds()

        # Refill tokens based on time passed
        tokens_to_add = (time_passed / 60.0) * self.requests_per_minute
        self.tokens = min(self.burst_limit, self.tokens + tokens_to_add)
        self.last_refill = now

        # Check if we have tokens available
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False


class TCPTransport(BaseTransport):
    """TCP socket-based transport implementation.

    This transport uses TCP sockets for MCP protocol communication,
    supporting multiple concurrent connections with authentication and rate limiting.

    Attributes:
        server: The MCP server instance
        config: TCP-specific configuration
        server_socket: TCP server socket
        connections: Set of active connections
        is_running: Whether the transport is currently running

    """

    def __init__(self, server: Any, config: dict[str, Any] | None = None) -> None:
        """Initialize the TCP transport.

        Args:
            server: The MCP server instance
            config: TCP-specific configuration

        """
        super().__init__(server, config)
        self.server_socket: asyncio.Server | None = None
        self.connections: set[TCPConnection] = set()
        self._cleanup_task: asyncio.Task[None] | None = None

    @property
    def transport_type(self) -> str:
        """Get the transport type identifier.

        Returns:
            'tcp' for TCP transport

        """
        return "tcp"

    async def start(self) -> None:
        """Start the TCP transport.

        Creates and binds the TCP server socket, then begins accepting connections.

        Raises:
            TransportError: If the TCP transport fails to start

        """
        try:
            port = self.get_config("port", 3000)
            bind_address = self.get_config("bind_address", "127.0.0.1")
            max_connections = self.get_config("max_connections", 10)

            self.logger.info(
                "Starting TCP transport",
                port=port,
                bind_address=bind_address,
                max_connections=max_connections,
            )

            # Create TCP server
            self.server_socket = await asyncio.start_server(
                self._handle_connection,
                bind_address,
                port,
                limit=max_connections,
            )

            # Start cleanup task for expired connections
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_connections())

            self.is_running = True
            self.logger.info(
                "TCP transport started successfully", port=port, bind_address=bind_address
            )

        except Exception as e:
            self.logger.error("Failed to start TCP transport", error=str(e))
            raise TransportError(f"Failed to start TCP transport: {e}", "tcp") from e

    async def stop(self) -> None:
        """Stop the TCP transport.

        Closes all connections, stops the server socket, and cleans up resources.
        """
        try:
            self.logger.info("Stopping TCP transport")

            # Cancel cleanup task
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass

            # Close all connections
            for connection in list(self.connections):
                await connection.close()
            self.connections.clear()

            # Close server socket
            if self.server_socket:
                self.server_socket.close()
                await self.server_socket.wait_closed()

            self.is_running = False
            self.logger.info("TCP transport stopped successfully")

        except Exception as e:
            self.logger.error("Error stopping TCP transport", error=str(e))

    async def run(self) -> None:
        """Run the TCP transport main loop.

        Starts the server and waits for it to complete.

        Raises:
            TransportError: If the transport fails during execution

        """
        if not self.is_running:
            raise TransportError("TCP transport is not running", "tcp")

        try:
            self.logger.info("Running TCP transport main loop")

            # Start serving
            if self.server_socket is not None:
                async with self.server_socket:
                    await self.server_socket.serve_forever()
            else:
                raise TransportError("Server socket is not initialized", "tcp")

        except Exception as e:
            self.logger.error("TCP transport main loop failed", error=str(e))
            raise TransportError(f"TCP transport main loop failed: {e}", "tcp") from e

    async def _handle_connection(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ) -> None:
        """Handle a new TCP connection.

        Args:
            reader: StreamReader for reading from the connection
            writer: StreamWriter for writing to the connection

        """
        client_address = writer.get_extra_info("peername")
        connection = None

        try:
            self.logger.info("New TCP connection", client_address=client_address)

            # Create connection object
            connection = TCPConnection(reader, writer, client_address)
            self.connections.add(connection)

            # Handle the connection
            await self._process_connection(connection)

        except Exception as e:
            self.logger.error(
                "Error handling TCP connection", client_address=client_address, error=str(e)
            )
        finally:
            # Clean up connection
            if connection:
                self.connections.discard(connection)
                await connection.close()
            self.logger.info("TCP connection closed", client_address=client_address)

    async def _process_connection(self, connection: TCPConnection) -> None:
        """Process messages from a TCP connection.

        Args:
            connection: The TCP connection to process

        """
        try:
            while True:
                # Read message length (first 4 bytes)
                length_data = await connection.reader.readexactly(4)
                if not length_data:
                    break

                message_length = int.from_bytes(length_data, byteorder="big")

                # Read message data
                message_data = await connection.reader.readexactly(message_length)
                if not message_data:
                    break

                # Parse JSON message
                try:
                    message = json.loads(message_data.decode("utf-8"))
                    connection.update_activity()

                    # Check rate limiting
                    if not connection.rate_limiter.is_allowed():
                        await self._send_error_response(connection, -32008, "Rate limit exceeded")
                        continue

                    # Process message (placeholder - will be implemented with MCP protocol)
                    await self._process_mcp_message(connection, message)

                except json.JSONDecodeError as e:
                    await self._send_error_response(connection, -32700, f"Invalid JSON: {e}")
                except Exception as e:
                    await self._send_error_response(connection, -32603, f"Internal error: {e}")

        except asyncio.IncompleteReadError:
            # Connection closed by client
            pass
        except Exception as e:
            self.logger.error(
                "Error processing TCP connection",
                client_address=connection.client_address,
                error=str(e),
            )

    async def _process_mcp_message(
        self, connection: TCPConnection, message: dict[str, Any]
    ) -> None:
        """Process an MCP protocol message.

        Args:
            connection: The TCP connection
            message: The MCP message to process

        """
        # This method is now handled by the EnhancedTCPServer
        # This is a placeholder for backward compatibility
        self.logger.debug(
            "Processing MCP message",
            client_address=connection.client_address,
            message_type=message.get("method", "unknown"),
        )

        # For now, send a simple response
        response = {
            "jsonrpc": "2.0",
            "id": message.get("id"),
            "result": {"status": "received"},
        }
        await self._send_response(connection, response)

    async def _send_response(self, connection: TCPConnection, response: dict[str, Any]) -> None:
        """Send a response to a TCP connection.

        Args:
            connection: The TCP connection
            response: The response to send

        """
        try:
            message_data = json.dumps(response).encode("utf-8")
            message_length = len(message_data)

            # Send message length
            connection.writer.write(message_length.to_bytes(4, byteorder="big"))
            # Send message data
            connection.writer.write(message_data)
            await connection.writer.drain()

        except Exception as e:
            self.logger.error(
                "Error sending TCP response", client_address=connection.client_address, error=str(e)
            )

    async def _send_error_response(
        self, connection: TCPConnection, error_code: int, error_message: str
    ) -> None:
        """Send an error response to a TCP connection.

        Args:
            connection: The TCP connection
            error_code: JSON-RPC error code
            error_message: Error message

        """
        error_response = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": error_code,
                "message": error_message,
            },
        }
        await self._send_response(connection, error_response)

    async def _cleanup_expired_connections(self) -> None:
        """Clean up expired connections.

        Runs periodically to remove connections that have timed out.
        """
        timeout_seconds = self.get_config("connection_timeout_seconds", 300)

        while self.is_running:
            try:
                await asyncio.sleep(60)  # Check every minute

                expired_connections = [
                    conn for conn in self.connections if conn.is_expired(timeout_seconds)
                ]

                for connection in expired_connections:
                    self.logger.info(
                        "Closing expired connection", client_address=connection.client_address
                    )
                    self.connections.discard(connection)
                    await connection.close()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in connection cleanup", error=str(e))

    def get_connection_count(self) -> int:
        """Get the number of active connections.

        Returns:
            Number of active connections

        """
        return len(self.connections)

    def get_connections_info(self) -> list[dict[str, Any]]:
        """Get information about active connections.

        Returns:
            List of connection information dictionaries

        """
        return [
            {
                "client_address": conn.client_address,
                "connected_at": conn.connected_at.isoformat(),
                "last_activity": conn.last_activity.isoformat(),
                "is_authenticated": conn.is_authenticated,
                "api_key": conn.api_key[:8] + "..." if conn.api_key else None,
            }
            for conn in self.connections
        ]
