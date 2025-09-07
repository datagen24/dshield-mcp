#!/usr/bin/env python3
"""Server Process Manager for DShield MCP TUI.

This module provides a process manager wrapper that handles TCP server lifecycle
management with proper timeout handling and event emission for the TUI.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Any

import structlog
from textual.message import Message

from ..user_config import UserConfigManager

logger = structlog.get_logger(__name__)


class ServerStatusUpdate(Message):
    """Message sent when server status is updated."""

    def __init__(self, status: dict[str, Any]) -> None:
        """Initialize server status update message.

        Args:
            status: Server status information

        """
        super().__init__()
        self.status = status


class ServerProcessManager:
    """Manages the MCP server process with timeout handling and event emission.

    This class provides a wrapper around the TUIProcessManager that adds:
    - Proper timeout handling for graceful shutdown
    - Event emission for status updates
    - Configuration display
    - Status monitoring

    Attributes:
        config_path: Path to configuration file
        user_config: User configuration manager
        process_manager: Underlying TUI process manager
        server_running: Whether the server is currently running
        server_start_time: When the server was started
        graceful_shutdown_timeout: Timeout for graceful shutdown in seconds

    """

    def __init__(self, config_path: str | None = None) -> None:
        """Initialize the server process manager.

        Args:
            config_path: Optional path to configuration file

        """
        self.config_path = config_path
        self.user_config = UserConfigManager(config_path)
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")

        # Import here to avoid circular imports
        from ..tui_launcher import TUIProcessManager

        self.process_manager = TUIProcessManager(config_path)
        self.server_running = False
        self.server_start_time: datetime | None = None
        self.graceful_shutdown_timeout = self.user_config.tui_settings.server_management.get(
            "graceful_shutdown_timeout", 30
        )

        # Event handlers
        self._status_handlers: list[Callable] = []

    def add_status_handler(self, handler: Callable) -> None:
        """Add a status update handler.

        Args:
            handler: Function to call when status updates

        """
        self._status_handlers.append(handler)

    def remove_status_handler(self, handler: Callable) -> None:
        """Remove a status update handler.

        Args:
            handler: Handler to remove

        """
        if handler in self._status_handlers:
            self._status_handlers.remove(handler)

    def _emit_status_update(self, status: dict[str, Any]) -> None:
        """Emit a status update to all handlers.

        Args:
            status: Status information to emit

        """
        for handler in self._status_handlers:
            try:
                handler(ServerStatusUpdate(status))
            except Exception as e:
                self.logger.error("Error in status handler", error=str(e), handler=handler.__name__)

    async def start_server(self) -> bool:
        """Start the MCP server process with timeout handling.

        Returns:
            True if server started successfully, False otherwise

        """
        try:
            self.logger.info("Starting MCP server process")

            # Start the server using the underlying process manager
            success = await self.process_manager.start_server()

            if success:
                self.server_running = True
                self.server_start_time = datetime.now()

                # Get server status
                status = self._get_server_status()

                # Emit status update
                self._emit_status_update(status)

                self.logger.info("MCP server process started successfully")
                return True
            else:
                self.logger.error("Failed to start MCP server process")
                return False

        except Exception as e:
            self.logger.error("Error starting MCP server process", error=str(e))
            return False

    async def stop_server(self) -> bool:
        """Stop the MCP server process with graceful shutdown timeout.

        Returns:
            True if server stopped successfully, False otherwise

        """
        try:
            self.logger.info("Stopping MCP server process")

            if not self.server_running:
                self.logger.warning("Server is not running")
                return True

            # Stop the server using the underlying process manager
            success = await self.process_manager.stop_server()

            if success:
                self.server_running = False
                self.server_start_time = None

                # Get server status
                status = self._get_server_status()

                # Emit status update
                self._emit_status_update(status)

                self.logger.info("MCP server process stopped successfully")
                return True
            else:
                self.logger.error("Failed to stop MCP server process")
                return False

        except Exception as e:
            self.logger.error("Error stopping MCP server process", error=str(e))
            return False

    async def restart_server(self) -> bool:
        """Restart the MCP server process.

        Returns:
            True if server restarted successfully, False otherwise

        """
        try:
            self.logger.info("Restarting MCP server process")

            # Stop existing server
            if self.server_running:
                await self.stop_server()

            # Start new server
            return await self.start_server()

        except Exception as e:
            self.logger.error("Error restarting MCP server process", error=str(e))
            return False

    def is_server_running(self) -> bool:
        """Check if the server process is running.

        Returns:
            True if server is running, False otherwise

        """
        return self.server_running and self.process_manager.is_server_running()

    def get_server_status(self) -> dict[str, Any]:
        """Get comprehensive server status information.

        Returns:
            Dictionary of server status information

        """
        return self._get_server_status()

    def get_effective_configuration(self) -> dict[str, Any]:
        """Get the effective server configuration.

        Returns:
            Dictionary of effective server configuration

        """
        return {
            "port": self.user_config.tcp_transport_settings.port,
            "bind_address": self.user_config.tcp_transport_settings.bind_address,
            "max_connections": self.user_config.tcp_transport_settings.max_connections,
            "connection_timeout_seconds": (
                self.user_config.tcp_transport_settings.connection_timeout_seconds
            ),
            "graceful_shutdown_timeout": self.graceful_shutdown_timeout,
            "api_key_management": {
                "enabled": self.user_config.tcp_transport_settings.api_key_management.get(
                    "enabled", True
                ),
                "rate_limit_per_key": (
                    self.user_config.tcp_transport_settings.api_key_management.get(
                        "rate_limit_per_key", 60
                    )
                ),
                "max_keys": self.user_config.tcp_transport_settings.api_key_management.get(
                    "max_keys", 100
                ),
            },
            "permissions": self.user_config.tcp_transport_settings.permissions,
            "security": {
                "global_rate_limit": 1000,
                "global_burst_limit": 100,
                "client_rate_limit": self.user_config.tcp_transport_settings.api_key_management.get(
                    "rate_limit_per_key", 60
                ),
                "client_burst_limit": 10,
                "abuse_threshold": 10,
                "block_duration_seconds": 3600,
                "max_connection_attempts": 5,
                "connection_window_seconds": 300,
            },
        }

    def _get_server_status(self) -> dict[str, Any]:
        """Get internal server status.

        Returns:
            Dictionary of server status information

        """
        uptime_seconds = 0
        if self.server_start_time:
            uptime_seconds = int((datetime.now() - self.server_start_time).total_seconds())

        return {
            "running": self.server_running,
            "uptime_seconds": uptime_seconds,
            "start_time": self.server_start_time.isoformat() if self.server_start_time else None,
            "pid": (
                self.process_manager.server_process.pid
                if self.process_manager.server_process
                else None
            ),
            "configuration": self.get_effective_configuration(),
            "graceful_shutdown_timeout": self.graceful_shutdown_timeout,
        }

    async def cleanup(self) -> None:
        """Clean up resources and stop server if running."""
        try:
            if self.server_running:
                self.logger.info("Cleaning up server process manager")
                await self.stop_server()
        except Exception as e:
            self.logger.error("Error during cleanup", error=str(e))
