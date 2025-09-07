#!/usr/bin/env python3
"""Server management panel for DShield MCP TUI.

This module provides a terminal UI panel for managing the MCP server,
including starting/stopping the server, viewing server status, and configuration.
"""

from datetime import datetime
from typing import Any

import structlog
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Static

from .server_process_manager import ServerProcessManager, ServerStatusUpdate

logger = structlog.get_logger(__name__)


class ServerStart(Message):
    """Message sent when server should be started."""


class ServerStop(Message):
    """Message sent when server should be stopped."""


class ServerRestart(Message):
    """Message sent when server should be restarted."""


class ServerConfigUpdate(Message):
    """Message sent when server configuration should be updated."""

    def __init__(self, config: dict[str, Any]) -> None:
        """Initialize server config update message.

        Args:
            config: New server configuration

        """
        super().__init__()
        self.config = config


class ServerPanel(Container):
    """Panel for managing the MCP server.

    This panel provides controls for starting/stopping the server,
    viewing server status, and managing server configuration.
    """

    def __init__(self, id: str = "server-panel", config_path: str | None = None) -> None:
        """Initialize the server panel.

        Args:
            id: Panel ID
            config_path: Optional path to configuration file

        """
        super().__init__(id=id)
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")

        # State
        self.server_running = reactive(False)
        self.server_status: dict[str, Any] = {}
        self.server_config: dict[str, Any] = {}
        self.uptime_start: datetime | None = None

        # Process manager
        self.process_manager = ServerProcessManager(config_path)
        self.process_manager.add_status_handler(self._on_server_status_update)

    def compose(self) -> ComposeResult:
        """Compose the server panel layout.

        Returns:
            ComposeResult: The composed UI elements

        """
        yield Static("Server Management", classes="panel-title")

        with Vertical(classes="panel"):
            # Server controls
            with Horizontal(classes="server-controls"):
                yield Button("Start Server", id="start-server-btn")
                yield Button("Stop Server", id="stop-server-btn", disabled=True)
                yield Button("Restart Server", id="restart-server-btn", disabled=True)

            # Server status
            yield Static("Server Status:", classes="section-title")
            yield Static("Status: Stopped", id="server-status-text")
            yield Static("Uptime: N/A", id="server-uptime-text")
            yield Static("Port: N/A", id="server-port-text")
            yield Static("Address: N/A", id="server-address-text")

            # Server statistics
            yield Static("Server Statistics:", classes="section-title")
            yield Static("Active Connections: 0", id="active-connections-text")
            yield Static("Total Requests: 0", id="total-requests-text")
            yield Static("Error Rate: 0%", id="error-rate-text")

            # Configuration (Read-only display)
            yield Static("Effective Configuration:", classes="section-title")
            yield Static("Port: N/A", id="config-port-text")
            yield Static("Bind Address: N/A", id="config-address-text")
            yield Static("Max Connections: N/A", id="config-max-connections-text")
            yield Static("Graceful Shutdown Timeout: N/A", id="config-timeout-text")
            yield Static("API Key Management: N/A", id="config-api-keys-text")
            yield Static("Rate Limit per Key: N/A", id="config-rate-limit-text")

    def on_mount(self) -> None:
        """Handle panel mount event."""
        self.logger.debug("Server panel mounted")

        # Initialize configuration display
        self._initialize_config_display()

        # Update initial status
        self._update_server_status()

    def _initialize_config_display(self) -> None:
        """Initialize configuration display with effective configuration."""
        try:
            config = self.process_manager.get_effective_configuration()

            # Update configuration display
            port_text = self.query_one("#config-port-text", Static)
            address_text = self.query_one("#config-address-text", Static)
            max_connections_text = self.query_one("#config-max-connections-text", Static)
            timeout_text = self.query_one("#config-timeout-text", Static)
            api_keys_text = self.query_one("#config-api-keys-text", Static)
            rate_limit_text = self.query_one("#config-rate-limit-text", Static)

            port_text.update(f"Port: {config.get('port', 'N/A')}")
            address_text.update(f"Bind Address: {config.get('bind_address', 'N/A')}")
            max_connections_text.update(f"Max Connections: {config.get('max_connections', 'N/A')}")
            timeout_text.update(
                f"Graceful Shutdown Timeout: {config.get('graceful_shutdown_timeout', 'N/A')}s"
            )

            api_key_mgmt = config.get("api_key_management", {})
            enabled_status = "Enabled" if api_key_mgmt.get("enabled", False) else "Disabled"
            api_keys_text.update(f"API Key Management: {enabled_status}")
            rate_limit_text.update(
                f"Rate Limit per Key: {api_key_mgmt.get('rate_limit_per_key', 'N/A')} req/min"
            )

            self.logger.debug("Initialized configuration display", config=config)

        except Exception as e:
            self.logger.error("Error initializing configuration display", error=str(e))

    def _update_server_status(self) -> None:
        """Update server status from process manager."""
        try:
            status = self.process_manager.get_server_status()
            self.server_running = status.get("running", False)
            self.server_status = status

            # Update button states
            start_btn = self.query_one("#start-server-btn", Button)
            stop_btn = self.query_one("#stop-server-btn", Button)
            restart_btn = self.query_one("#restart-server-btn", Button)

            start_btn.disabled = bool(self.server_running)
            stop_btn.disabled = not self.server_running
            restart_btn.disabled = not self.server_running

            # Update status text
            status_text = self.query_one("#server-status-text", Static)
            if self.server_running:
                status_text.update("Status: Running")
                if not self.uptime_start:
                    self.uptime_start = datetime.now()
            else:
                status_text.update("Status: Stopped")
                self.uptime_start = None

            # Update uptime
            uptime_text = self.query_one("#server-uptime-text", Static)
            if self.server_running and self.uptime_start:
                uptime = datetime.now() - self.uptime_start
                uptime_str = str(uptime).split(".")[0]  # Remove microseconds
                uptime_text.update(f"Uptime: {uptime_str}")
            else:
                uptime_text.update("Uptime: N/A")

            # Update port and address
            port_text = self.query_one("#server-port-text", Static)
            address_text = self.query_one("#server-address-text", Static)

            config = status.get("configuration", {})
            port_text.update(f"Port: {config.get('port', 'N/A')}")
            address_text.update(f"Address: {config.get('bind_address', 'N/A')}")

            self.logger.debug("Updated server status", running=self.server_running, status=status)

        except Exception as e:
            self.logger.error("Error updating server status", error=str(e))

    def _on_server_status_update(self, message: ServerStatusUpdate) -> None:
        """Handle server status update from process manager.

        Args:
            message: Server status update message

        """
        self.server_status = message.status
        self.server_running = message.status.get("running", False)

        # Update button states
        start_btn = self.query_one("#start-server-btn", Button)
        stop_btn = self.query_one("#stop-server-btn", Button)
        restart_btn = self.query_one("#restart-server-btn", Button)

        start_btn.disabled = bool(self.server_running)
        stop_btn.disabled = not self.server_running
        restart_btn.disabled = not self.server_running

        # Update status text
        status_text = self.query_one("#server-status-text", Static)
        if self.server_running:
            status_text.update("Status: Running")
            if not self.uptime_start:
                self.uptime_start = datetime.now()
        else:
            status_text.update("Status: Stopped")
            self.uptime_start = None

        # Update uptime
        uptime_text = self.query_one("#server-uptime-text", Static)
        if self.server_running and self.uptime_start:
            uptime = datetime.now() - self.uptime_start
            uptime_str = str(uptime).split(".")[0]  # Remove microseconds
            uptime_text.update(f"Uptime: {uptime_str}")
        else:
            uptime_text.update("Uptime: N/A")

        # Update port and address
        port_text = self.query_one("#server-port-text", Static)
        address_text = self.query_one("#server-address-text", Static)

        config = message.status.get("configuration", {})
        port_text.update(f"Port: {config.get('port', 'N/A')}")
        address_text.update(f"Address: {config.get('bind_address', 'N/A')}")

        self.logger.debug("Handled server status update", status=message.status)

    def update_server_statistics(self, stats: dict[str, Any]) -> None:
        """Update server statistics display.

        Args:
            stats: Server statistics dictionary

        """
        self.server_status = stats

        # Update uptime
        uptime_text = self.query_one("#server-uptime-text", Static)
        if self.uptime_start:
            uptime = datetime.now() - self.uptime_start
            uptime_str = str(uptime).split(".")[0]  # Remove microseconds
            uptime_text.update(f"Uptime: {uptime_str}")
        else:
            uptime_text.update("Uptime: N/A")

        # Update port and address
        port_text = self.query_one("#server-port-text", Static)
        address_text = self.query_one("#server-address-text", Static)

        server_info = stats.get("server", {})
        port_text.update(f"Port: {server_info.get('port', 'N/A')}")
        address_text.update(f"Address: {server_info.get('bind_address', 'N/A')}")

        # Update statistics
        connections_info = stats.get("connections", {})
        active_connections_text = self.query_one("#active-connections-text", Static)
        active_connections_text.update(f"Active Connections: {connections_info.get('active', 0)}")

        # Update other statistics (these would come from the actual server)
        total_requests_text = self.query_one("#total-requests-text", Static)
        error_rate_text = self.query_one("#error-rate-text", Static)

        total_requests_text.update(f"Total Requests: {stats.get('total_requests', 0)}")
        error_rate_text.update(f"Error Rate: {stats.get('error_rate', 0):.1f}%")

        self.logger.debug("Updated server statistics", stats=stats)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: Button press event

        """
        button_id = event.button.id

        if button_id == "start-server-btn":
            self.logger.debug("Start server button pressed")
            self._start_server()
        elif button_id == "stop-server-btn":
            self.logger.debug("Stop server button pressed")
            self._stop_server()
        elif button_id == "restart-server-btn":
            self.logger.debug("Restart server button pressed")
            self._restart_server()

    def _start_server(self) -> None:
        """Start the server."""
        self.logger.info("Starting server")
        
        # Disable buttons during operation
        start_btn = self.query_one("#start-server-btn", Button)
        stop_btn = self.query_one("#stop-server-btn", Button)
        restart_btn = self.query_one("#restart-server-btn", Button)
        
        start_btn.disabled = True
        stop_btn.disabled = True
        restart_btn.disabled = True
        
        # Start server asynchronously
        import asyncio
        asyncio.create_task(self._async_start_server())

    def _stop_server(self) -> None:
        """Stop the server."""
        self.logger.info("Stopping server")
        
        # Disable buttons during operation
        start_btn = self.query_one("#start-server-btn", Button)
        stop_btn = self.query_one("#stop-server-btn", Button)
        restart_btn = self.query_one("#restart-server-btn", Button)
        
        start_btn.disabled = True
        stop_btn.disabled = True
        restart_btn.disabled = True
        
        # Stop server asynchronously
        import asyncio
        asyncio.create_task(self._async_stop_server())

    def _restart_server(self) -> None:
        """Restart the server."""
        self.logger.info("Restarting server")
        
        # Disable buttons during operation
        start_btn = self.query_one("#start-server-btn", Button)
        stop_btn = self.query_one("#stop-server-btn", Button)
        restart_btn = self.query_one("#restart-server-btn", Button)
        
        start_btn.disabled = True
        stop_btn.disabled = True
        restart_btn.disabled = True
        
        # Restart server asynchronously
        import asyncio
        asyncio.create_task(self._async_restart_server())

    async def _async_start_server(self) -> None:
        """Asynchronously start the server."""
        try:
            success = await self.process_manager.start_server()
            if success:
                self.logger.info("Server started successfully")
            else:
                self.logger.error("Failed to start server")
        except Exception as e:
            self.logger.error("Error starting server", error=str(e))
        finally:
            # Re-enable buttons
            self._update_server_status()

    async def _async_stop_server(self) -> None:
        """Asynchronously stop the server."""
        try:
            success = await self.process_manager.stop_server()
            if success:
                self.logger.info("Server stopped successfully")
            else:
                self.logger.error("Failed to stop server")
        except Exception as e:
            self.logger.error("Error stopping server", error=str(e))
        finally:
            # Re-enable buttons
            self._update_server_status()

    async def _async_restart_server(self) -> None:
        """Asynchronously restart the server."""
        try:
            success = await self.process_manager.restart_server()
            if success:
                self.logger.info("Server restarted successfully")
            else:
                self.logger.error("Failed to restart server")
        except Exception as e:
            self.logger.error("Error restarting server", error=str(e))
        finally:
            # Re-enable buttons
            self._update_server_status()

    def get_server_health(self) -> dict[str, Any]:
        """Get server health information.

        Returns:
            Dictionary of server health information

        """
        return {
            "running": self.server_running,
            "uptime_seconds": (datetime.now() - self.uptime_start).total_seconds()
            if self.uptime_start
            else 0,
            "status": self.server_status,
            "configuration": self.process_manager.get_effective_configuration(),
        }
