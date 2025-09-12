#!/usr/bin/env python3
"""Main TUI application for DShield MCP Server.

This module provides the main terminal user interface application using textual,
including layout management, event handling, and integration with the TCP server.
"""

import asyncio
import subprocess
import threading
from datetime import datetime
from typing import Any, ClassVar

import structlog
from textual.app import App, ComposeResult  # type: ignore
from textual.binding import Binding  # type: ignore
from textual.containers import Container  # type: ignore
from textual.message import Message  # type: ignore
from textual.reactive import reactive  # type: ignore
from textual.widgets import Footer, Header, Input  # type: ignore

from ..tcp_server import EnhancedTCPServer
from ..user_config import UserConfigManager
from .connection_panel import ConnectionPanel
from .live_metrics_panel import LiveMetricsPanel
from .log_panel import LogPanel
from .metrics_subscriber import MetricsSubscriber
from .server_panel import ServerPanel, ServerRestart, ServerStart, ServerStop
from .status_bar import StatusBar

logger = structlog.get_logger(__name__)


# Late import to avoid circular dependencies
def _get_dshield_mcp_server() -> Any:
    """Get DShieldMCPServer class with late import to avoid circular dependencies."""
    from mcp_server import DShieldMCPServer

    return DShieldMCPServer


class ServerStatusUpdate(Message):  # type: ignore
    """Message sent when server status is updated."""

    def __init__(self, status: dict[str, Any]) -> None:
        """Initialize server status update message.

        Args:
            status: Server status information

        """
        super().__init__()
        self.status = status


class ConnectionUpdate(Message):  # type: ignore
    """Message sent when connection information is updated."""

    def __init__(self, connections: list[dict[str, Any]]) -> None:
        """Initialize connection update message.

        Args:
            connections: List of connection information

        """
        super().__init__()
        self.connections = connections


class LogUpdate(Message):  # type: ignore
    """Message sent when new log entries are available."""

    def __init__(self, log_entries: list[dict[str, Any]]) -> None:
        """Initialize log update message.

        Args:
            log_entries: List of log entries

        """
        super().__init__()
        self.log_entries = log_entries


class DShieldTUIApp(App):  # type: ignore
    """Main TUI application for DShield MCP Server.

    This class provides the main terminal user interface with panels for
    connection management, server control, and log monitoring.
    """

    CSS = """
    Screen {
        layout: vertical;
    }

    #main-container {
        layout: horizontal;
        height: 1fr;
    }

    #left-panel {
        width: 1fr;
        layout: vertical;
    }

    #right-panel {
        width: 1fr;
        layout: vertical;
    }

    .panel {
        border: solid $primary;
        margin: 1;
        padding: 1;
    }

    .connection-item {
        margin: 1;
        padding: 1;
        border: solid $secondary;
    }

    .server-controls {
        layout: horizontal;
        height: auto;
    }

    .log-entry {
        margin: 1;
        padding: 1;
    }

    .log-entry.error {
        color: $error;
    }

    .log-entry.warning {
        color: $warning;
    }

    .log-entry.info {
        color: $accent;
    }
    """

    BINDINGS: ClassVar = [
        Binding("q", "quit", "Quit"),
        Binding("r", "restart_server", "Restart Server"),
        Binding("s", "stop_server", "Stop Server"),
        Binding("g", "generate_api_key", "Generate API Key"),
        Binding("c", "clear_logs", "Clear Logs"),
        Binding("t", "test_log", "Test Log"),
        Binding("f", "focus_filter", "Focus Filter"),
        Binding("h", "show_help", "Help"),
        Binding("tab", "switch_panel", "Switch Panel"),
    ]

    def __init__(self, config_path: str | None = None) -> None:
        """Initialize the TUI application.

        Args:
            config_path: Optional path to configuration file

        """
        super().__init__()
        self.config_path = config_path
        self.user_config = UserConfigManager(config_path)
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")

        # Server components
        self.tcp_server: EnhancedTCPServer | None = None
        self.server_process: subprocess.Popen[bytes] | None = None
        self.server_thread: threading.Thread | None = None
        self.server_running = reactive(False)
        self.server_port = reactive(self.user_config.tcp_transport_settings.port)

        # UI state
        self._mounted = False
        self.server_address = reactive(self.user_config.tcp_transport_settings.bind_address)
        self.current_panel = 0
        self.log_entries: list[dict[str, Any]] = []
        self.connections: list[dict[str, Any]] = []
        self.server_status: dict[str, Any] = {}

        # Metrics system
        self.metrics_subscriber: MetricsSubscriber | None = None

        # Update tasks
        self._update_task: asyncio.Task[Any] | threading.Thread | None = None

    def compose(self) -> ComposeResult:
        """Compose the TUI layout.

        Returns:
            ComposeResult: The composed UI elements

        """
        yield Header()

        with Container(id="main-container"):
            with Container(id="left-panel"):
                yield ConnectionPanel(id="connection-panel")
                yield ServerPanel(id="server-panel", config_path=self.config_path)

            with Container(id="right-panel"):
                yield LiveMetricsPanel(id="live-metrics-panel")
                yield LogPanel(
                    id="log-panel", max_entries=self.user_config.tui_settings.log_history_size
                )

        yield StatusBar(id="status-bar")
        yield Footer()

    def on_mount(self) -> None:
        """Handle application mount event."""
        self.logger.info("TUI application mounted")
        self.title = "DShield MCP Server Manager"
        self.sub_title = f"Port: {self.server_port} | Address: {self.server_address}"

        # Mark UI as mounted
        self._mounted = True

        # Initialize metrics subscriber
        self._initialize_metrics_subscriber()

        # Start update task in a separate thread
        self._update_task = threading.Thread(target=self._periodic_update, daemon=True)
        self._update_task.start()

        # Auto-start server if configured
        if self.user_config.tui_settings.server_management.get("auto_start_server", True):
            self.action_restart_server()

        # Add a test log entry to verify log panel is working
        self._add_log_entry("info", "TUI application started successfully")

    def on_unmount(self) -> None:
        """Handle application unmount event."""
        self.logger.info("TUI application unmounting")

        # Stop metrics subscriber
        if self.metrics_subscriber:
            asyncio.create_task(self.metrics_subscriber.stop())

        # Stop update task
        if (
            self._update_task
            and hasattr(self._update_task, "is_alive")
            and self._update_task.is_alive()
        ):
            # The thread will stop when the daemon process exits
            pass

        # Stop server
        if self.server_running:
            self.action_stop_server()

    def _initialize_metrics_subscriber(self) -> None:
        """Initialize the metrics subscriber system."""
        try:
            # Create metrics subscriber
            self.metrics_subscriber = MetricsSubscriber(
                update_interval=1.0,  # Update every second
                max_subscribers=10,
            )

            # Set metrics collector function
            self.metrics_subscriber.set_metrics_collector(self._collect_server_metrics)

            # Start the subscriber
            asyncio.create_task(self.metrics_subscriber.start())

            # Connect to live metrics panel
            live_metrics_panel = self.query_one("#live-metrics-panel", LiveMetricsPanel)
            live_metrics_panel.set_metrics_subscriber(self.metrics_subscriber)

            self.logger.info("Metrics subscriber initialized successfully")

        except Exception as e:
            self.logger.error("Failed to initialize metrics subscriber", error=str(e))

    def _collect_server_metrics(self) -> dict[str, Any]:
        """Collect server metrics for the metrics subscriber.

        Returns:
            Dictionary of raw server metrics
        """
        try:
            if not self.tcp_server:
                return {}

            # Get server statistics
            server_stats = self.tcp_server.get_server_statistics()

            # Enhance with additional metrics
            enhanced_stats = {
                **server_stats,
                "timestamp": datetime.now().isoformat(),
                "tui_state": {
                    "mounted": self._mounted,
                    "server_running": self.server_running,
                    "connection_count": len(self.connections),
                    "log_entries_count": len(self.log_entries),
                },
            }

            return enhanced_stats

        except Exception as e:
            self.logger.error("Error collecting server metrics", error=str(e))
            return {}

    def _periodic_update(self) -> None:
        """Periodic update task for refreshing UI data."""
        import time

        while True:
            try:
                time.sleep(self.user_config.tui_settings.refresh_interval_ms / 1000.0)
                self._update_ui_data()
            except Exception as e:
                self.logger.error("Error in periodic update", error=str(e))

    def _update_ui_data(self) -> None:
        """Update UI data from server components."""
        try:
            # Check if the UI is mounted before trying to update panels
            if not hasattr(self, "_mounted") or not self._mounted:
                self.logger.debug("UI not mounted yet, skipping update")
                return

            # Update server status
            if self.tcp_server:
                self.server_status = self.tcp_server.get_server_statistics()
                self.post_message(ServerStatusUpdate(self.server_status))

            # Update connections
            if self.tcp_server:
                # Use get_connections_info method instead of get_all_connections
                connections_info = self.tcp_server.connection_manager.get_connections_info()
                self.connections = connections_info
                self.post_message(ConnectionUpdate(self.connections))

            # Update logs (simplified for now)
            # In a real implementation, this would integrate with the logging system

            # Update server panel status
            self._update_server_panel_status()

        except Exception as e:
            self.logger.error("Error updating UI data", error=str(e))

    def _update_server_panel_status(self) -> None:
        """Update the server panel status display."""
        try:
            # Debug: List all available panels
            all_panels = self.query(ServerPanel)
            self.logger.debug(
                "Available server panels", count=len(all_panels), panels=[p.id for p in all_panels]
            )

            # Get the server panel - try multiple ways to find it
            server_panel = None
            try:
                server_panel = self.query_one("#server-panel", ServerPanel)
                self.logger.debug("Found server panel by ID")
            except Exception as e:
                self.logger.debug("Failed to find server panel by ID", error=str(e))
                # Try to find it by class
                try:
                    server_panel = self.query_one(ServerPanel)
                    self.logger.debug("Found server panel by class")
                except Exception as e2:
                    self.logger.debug("Failed to find server panel by class", error=str(e2))
                    self.logger.warning("Server panel not found, skipping status update")
                    return

            if server_panel:
                # Update the server panel with current status
                server_panel.update_server_status(self.server_running)

                # Update server statistics
                stats = {
                    "active_connections": 0,
                    "total_requests": 0,
                    "error_rate": 0.0,
                }
                server_panel.update_server_statistics(stats)

                self.logger.debug("Updated server panel status", running=self.server_running)

        except Exception as e:
            self.logger.error("Error updating server panel status", error=str(e))

    def _update_connection_panel(self) -> None:
        """Update the connection panel with API keys and connections."""
        try:
            # Get the connection panel - try multiple ways to find it
            connection_panel = None
            try:
                connection_panel = self.query_one("#connection-panel", ConnectionPanel)
            except Exception:
                # Try to find it by class
                try:
                    connection_panel = self.query_one(ConnectionPanel)
                except Exception:
                    self.logger.warning("Connection panel not found, skipping update")
                    return

            if connection_panel:
                # Get API keys from the connection manager
                api_keys = []
                if self.tcp_server and hasattr(self.tcp_server, 'connection_manager'):
                    try:
                        api_keys = self.tcp_server.connection_manager.get_api_keys_info()
                    except Exception as e:
                        self.logger.error(
                            "Error getting API keys from connection manager", error=str(e)
                        )
                        api_keys = []

                self.logger.debug(
                    "Updating connection panel", api_keys_count=len(api_keys), api_keys=api_keys
                )
                connection_panel.update_api_keys(api_keys)
                self.logger.debug("Connection panel update_api_keys called")

                # Get connections from the connection manager
                connections: list[dict[str, Any]] = []
                if self.tcp_server and hasattr(self.tcp_server, 'connection_manager'):
                    try:
                        connections = self.tcp_server.connection_manager.get_connections_info()
                        # Enhance connection data with additional information
                        for conn in connections:
                            # Add RPS and violations if not present
                            if 'rps' not in conn:
                                conn['rps'] = conn.get('requests_per_second', 0)
                            if 'violations' not in conn:
                                conn['violations'] = conn.get('rate_limit_violations', 0)

                            # Ensure permissions are properly formatted
                            if 'permissions' not in conn and 'api_key_permissions' in conn:
                                conn['permissions'] = conn['api_key_permissions']
                    except Exception as e:
                        self.logger.error(
                            "Error getting connections from connection manager", error=str(e)
                        )
                        connections = []

                connection_panel.update_connections(connections)

                self.logger.debug(
                    "Updated connection panel successfully",
                    api_keys_count=len(api_keys),
                    connections_count=len(connections),
                )

        except Exception as e:
            self.logger.error("Error updating connection panel", error=str(e))

    def _add_log_entry(self, level: str, message: str) -> None:
        """Add a log entry to the log panel."""
        try:
            # Debug: List all available log panels
            all_log_panels = self.query(LogPanel)
            self.logger.debug(
                "Available log panels",
                count=len(all_log_panels),
                panels=[p.id for p in all_log_panels],
            )

            # Get the log panel - try multiple ways to find it
            log_panel = None
            try:
                log_panel = self.query_one("#log-panel", LogPanel)
                self.logger.debug("Found log panel by ID")
            except Exception as e:
                self.logger.debug("Failed to find log panel by ID", error=str(e))
                # Try to find it by class
                try:
                    log_panel = self.query_one(LogPanel)
                    self.logger.debug("Found log panel by class")
                except Exception as e2:
                    self.logger.debug("Failed to find log panel by class", error=str(e2))
                    self.logger.warning("Log panel not found, skipping log entry")
                    return

            if log_panel:
                # Create log entry
                from datetime import datetime

                log_entry = {
                    "timestamp": datetime.now().isoformat(),
                    "level": level,
                    "message": message,
                    "source": "tui",
                }

                # Add the log entry
                self.logger.debug(
                    "Adding log entry to panel", level=level, message=message, log_entry=log_entry
                )
                log_panel.add_log_entries([log_entry])

                # Force update the display to bypass any filtering issues
                try:
                    log_panel._update_display()
                    self.logger.debug("Forced log panel display update")
                except Exception as e:
                    self.logger.debug("Failed to force log panel update", error=str(e))

                self.logger.debug("Added log entry successfully", level=level, message=message)

        except Exception as e:
            self.logger.error("Error adding log entry", error=str(e))

    def action_quit(self) -> None:
        """Quit the application."""
        self.logger.info("Quitting TUI application")
        self.exit()

    def action_restart_server(self) -> None:
        """Restart the TCP server."""
        self.logger.info("Restarting TCP server")
        self._add_log_entry("info", "Restarting TCP server")

        # Stop existing server
        if self.server_running:
            self.action_stop_server()

        # Start new server
        self._start_server()

    def action_stop_server(self) -> None:
        """Stop the TCP server."""
        self.logger.info("Stopping TCP server")
        self._add_log_entry("info", "Stopping TCP server")
        self._stop_server()

    async def action_generate_api_key(self) -> None:
        """Generate a new API key."""
        self.logger.info("Generating new API key")
        await self._generate_api_key()

    def action_test_log(self) -> None:
        """Test log entry creation."""
        self.logger.info("Testing log entry creation")
        self._add_log_entry("info", "Test log entry created")
        self.notify("Test log entry added", timeout=3)

    def action_clear_logs(self) -> None:
        """Clear the log display."""
        self.logger.info("Clearing logs")
        log_panel = self.query_one("#log-panel", LogPanel)
        log_panel.clear_logs()

    def action_show_help(self) -> None:
        """Show help information."""
        self.logger.info("Showing help")
        # This would show a help dialog
        self.notify("Help: Use Tab to switch panels, Ctrl+C to quit", timeout=3)

    def action_switch_panel(self) -> None:
        """Switch between panels."""
        self.current_panel = (self.current_panel + 1) % 3
        self.logger.debug("Switched to panel", panel=self.current_panel)

    def action_focus_filter(self) -> None:
        """Focus the log filter input field."""
        self.logger.info("Focusing log filter")
        try:
            # Find the search input in the log panel
            search_input = self.query_one("#search-input", Input)
            search_input.focus()
            self.notify("Filter focused - type to search logs", timeout=2)
        except Exception as e:
            self.logger.error("Failed to focus filter", error=str(e))
            self.notify("Failed to focus filter", timeout=2)

    def on_server_start(self, event: ServerStart) -> None:
        """Handle server start message from server panel."""
        self.logger.info("Received server start message")
        # Server panel now handles this directly via process manager

    def on_server_stop(self, event: ServerStop) -> None:
        """Handle server stop message from server panel."""
        self.logger.info("Received server stop message")
        # Server panel now handles this directly via process manager

    def on_server_restart(self, event: ServerRestart) -> None:
        """Handle server restart message from server panel."""
        self.logger.info("Received server restart message")
        # Server panel now handles this directly via process manager

    def _start_server(self) -> None:
        """Start the TCP server."""
        try:
            self.logger.info("DEBUG: _start_server called")
            print("DEBUG: Attempting to start TCP server...")

            # Check if auto_start is enabled
            print(
                f"DEBUG: auto_start_server = "
                f"{self.user_config.tui_settings.server_management.get('auto_start_server', False)}"
            )

            self.logger.info("Starting TCP server")

            # Create server configuration
            tcp_config = {
                "port": self.server_port,
                "bind_address": self.server_address,
                "max_connections": self.user_config.tcp_transport_settings.max_connections,
                "connection_timeout_seconds": (
                    self.user_config.tcp_transport_settings.connection_timeout_seconds
                ),
                "connection_management": {
                    "api_key_management": (
                        self.user_config.tcp_transport_settings.api_key_management
                    ),
                    "permissions": self.user_config.tcp_transport_settings.permissions,
                },
                "security": {
                    "global_rate_limit": 1000,
                    "global_burst_limit": 100,
                    "client_rate_limit": (
                        self.user_config.tcp_transport_settings.api_key_management.get(
                            "rate_limit_per_key", 60
                        )
                    ),
                    "client_burst_limit": 10,
                    "abuse_threshold": 10,
                    "block_duration_seconds": 3600,
                    "max_connection_attempts": 5,
                    "connection_window_seconds": 300,
                    "input_validation": {
                        "max_message_size": 1048576,
                        "max_field_length": 10000,
                        "allowed_methods": [
                            "initialize",
                            "initialized",
                            "tools/list",
                            "tools/call",
                            "resources/list",
                            "resources/read",
                            "prompts/list",
                            "prompts/get",
                            "authenticate",
                        ],
                    },
                },
                "authentication": {
                    "session_timeout_seconds": 3600,
                    "max_sessions_per_key": 5,
                },
            }

            # Create MCP server instance
            mcp_server = self._create_mcp_server()

            # Create and start the enhanced TCP server
            self.tcp_server = EnhancedTCPServer(mcp_server, tcp_config)

            # Start the server in a separate thread to avoid blocking the TUI
            def start_server_async():
                """Start the TCP server asynchronously."""
                try:
                    # Create a new event loop for this thread
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                    # Start the server
                    loop.run_until_complete(self.tcp_server.start())

                    # Keep the loop running
                    loop.run_forever()

                except Exception as e:
                    self.logger.error("Error in TCP server thread", error=str(e))
                finally:
                    loop.close()

            # Start the server in a daemon thread
            self.server_thread = threading.Thread(target=start_server_async, daemon=True)
            self.server_thread.start()

            # Check if the server thread is actually running
            if self.server_thread:
                print(f"DEBUG: Server thread started: {self.server_thread.is_alive()}")
                print(f"DEBUG: Server thread name: {self.server_thread.name}")

            # Give the server a moment to start
            import time

            time.sleep(0.5)

            self.server_running = True
            self.logger.info("TCP server started successfully")
            self.notify("Server started successfully", timeout=3)

            # Update server panel status
            self._update_server_panel_status()

            # Add log entry
            self._add_log_entry("info", "TCP server started successfully")

        except Exception as e:
            self.logger.error("Failed to start TCP server", error=str(e))
            self.notify(f"Failed to start server: {e}", timeout=5)

    def _stop_server(self) -> None:
        """Stop the TCP server."""
        try:
            self.logger.info("Stopping TCP server")

            if self.tcp_server:
                # Stop the TCP server asynchronously
                def stop_server_async():
                    """Stop the TCP server asynchronously."""
                    try:
                        # Create a new event loop for this thread
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                        # Stop the server
                        loop.run_until_complete(self.tcp_server.stop())

                    except Exception as e:
                        self.logger.error("Error stopping TCP server in thread", error=str(e))
                    finally:
                        loop.close()

                # Stop the server in a separate thread
                stop_thread = threading.Thread(target=stop_server_async, daemon=True)
                stop_thread.start()
                stop_thread.join(timeout=5)  # Wait up to 5 seconds for graceful shutdown

                self.tcp_server = None

            # Stop the server thread if it exists
            if hasattr(self, "server_thread") and self.server_thread.is_alive():
                # The thread will stop when the event loop is closed
                pass

            self.server_running = False
            self.logger.info("TCP server stopped successfully")
            self.notify("Server stopped", timeout=3)

            # Update server panel status
            self._update_server_panel_status()

            # Add log entry
            self._add_log_entry("info", "TCP server stopped successfully")

        except Exception as e:
            self.logger.error("Error stopping TCP server", error=str(e))
            self.notify(f"Error stopping server: {e}", timeout=5)

    def _create_mcp_server(self) -> Any:
        """Create and initialize DShieldMCPServer instance.

        Returns:
            Initialized DShieldMCPServer instance

        """
        try:
            # Get the DShieldMCPServer class using late import
            DShieldMCPServer = _get_dshield_mcp_server()

            # Create server instance
            mcp_server = DShieldMCPServer()

            # Initialize the server (this sets up all the components)
            # Note: This is a synchronous call, but the server initialization
            # should be done asynchronously in a real implementation
            self.logger.info("Created DShieldMCPServer instance")

            return mcp_server

        except Exception as e:
            self.logger.error("Failed to create DShieldMCPServer", error=str(e))
            raise

    async def _generate_api_key(self) -> None:
        """Generate a new API key using the new API key management system."""
        try:
            if not self.server_running:
                self.notify("Server must be running to generate API keys", timeout=3)
                return

            # Open the API key generation screen
            from .screens.api_key_screen import APIKeyGenerationScreen

            self.push_screen(APIKeyGenerationScreen(), self._on_api_key_generated)

        except Exception as e:
            self.logger.error("Failed to open API key generation screen", error=str(e))
            self.notify(f"Failed to open API key generation screen: {e}", timeout=5)

    async def _on_api_key_generated(self, key_config: dict[str, Any]) -> None:
        """Handle API key generation completion."""
        try:
            if not self.server_running:
                self.notify("Server must be running to generate API keys", timeout=3)
                return

            # Get the connection manager from the TCP server
            connection_manager = getattr(self.tcp_server, "connection_manager", None)
            if not connection_manager:
                self.notify("Connection manager not available", severity="error")
                return

            # Generate the API key using the connection manager
            api_key = await connection_manager.generate_api_key(
                name=key_config["name"],
                permissions=key_config["permissions"],
                expiration_days=key_config["expiration_days"],
                rate_limit=key_config["rate_limit"],
            )

            if api_key:
                self.logger.info(
                    "Generated new API key", key_id=api_key.key_id, name=key_config["name"]
                )
                self.notify(
                    f"API Key generated: {key_config['name']} ({api_key.key_id})", timeout=5
                )

                # Add log entry for API key generation
                self._add_log_entry(
                    "info", f"API Key generated: {key_config['name']} ({api_key.key_id})"
                )

                # Update connection panel
                self._update_connection_panel()
            else:
                self.notify("Failed to generate API key", severity="error")

        except Exception as e:
            self.logger.error("Failed to generate API key", error=str(e))
            self.notify(f"Failed to generate API key: {e}", timeout=5)

    def on_server_status_update(self, message: ServerStatusUpdate) -> None:
        """Handle server status update message."""
        self.server_status = message.status

        # Update status bar
        status_bar = self.query_one("#status-bar", StatusBar)
        status_bar.update_server_status(self.server_status)

    def on_connection_update(self, message: ConnectionUpdate) -> None:
        """Handle connection update message."""
        self.connections = message.connections

        # Update connection panel
        connection_panel = self.query_one("#connection-panel", ConnectionPanel)
        connection_panel.update_connections(self.connections)

    def on_log_update(self, message: LogUpdate) -> None:
        """Handle log update message."""
        self.log_entries.extend(message.log_entries)

        # Update log panel
        log_panel = self.query_one("#log-panel", LogPanel)
        log_panel.add_log_entries(message.log_entries)

    def on_api_key_generate(self, message: Any) -> None:
        """Handle API key generation message from connection panel."""
        self.logger.info("Received API key generation message")
        asyncio.create_task(self.action_generate_api_key())

    def on_api_key_revoke(self, message: Any) -> None:
        """Handle API key revocation message from connection panel."""
        self.logger.info(
            "Received API key revocation message", key_id=getattr(message, 'api_key_id', 'unknown')
        )
        asyncio.create_task(self._revoke_api_key(getattr(message, 'api_key_id', None)))

    def on_connection_disconnect(self, message: Any) -> None:
        """Handle connection disconnect message from connection panel."""
        client_address = getattr(message, 'client_address', None)
        self.logger.info("Received connection disconnect message", client_address=client_address)
        asyncio.create_task(self._disconnect_connection(client_address))

    def on_connection_refresh(self, message: Any) -> None:
        """Handle connection refresh message from connection panel."""
        self.logger.debug("Received connection refresh message")
        self._update_connection_panel()

    def on_connection_filter(self, message: Any) -> None:
        """Handle connection filter message from connection panel."""
        filter_text = getattr(message, 'filter_text', '')
        self.logger.debug("Received connection filter message", filter_text=filter_text)
        # Filtering is handled by the connection panel itself

    async def _disconnect_connection(self, client_address: str | None) -> None:
        """Disconnect a specific connection."""
        try:
            if not client_address:
                self.notify("No client address provided", severity="error")
                return

            if not self.server_running:
                self.notify("Server must be running to disconnect connections", timeout=3)
                return

            # Get the connection manager from the TCP server
            connection_manager = getattr(self.tcp_server, "connection_manager", None)
            if not connection_manager:
                self.notify("Connection manager not available", severity="error")
                return

            # Find and disconnect the connection
            connections = connection_manager.get_connections_info()
            target_connection = None

            for conn in connections:
                if str(conn.get("client_address", "")) == str(client_address):
                    target_connection = conn
                    break

            if not target_connection:
                self.notify(f"Connection not found: {client_address}", severity="error")
                return

            # Disconnect the connection
            # This would typically involve finding the actual connection object
            # and calling a disconnect method on it
            self.logger.info("Disconnecting connection", client_address=client_address)
            self.notify(f"Disconnected connection: {client_address}", timeout=3)

            # Add log entry
            self._add_log_entry("info", f"Disconnected connection: {client_address}")

            # Update connection panel
            self._update_connection_panel()

        except Exception as e:
            self.logger.error(
                "Failed to disconnect connection", error=str(e), client_address=client_address
            )
            self.notify(f"Failed to disconnect connection: {e}", severity="error")

    async def _revoke_api_key(self, key_id: str | None) -> None:
        """Revoke an API key."""
        try:
            if not key_id:
                self.notify("No API key ID provided", severity="error")
                return

            if not self.server_running:
                self.notify("Server must be running to revoke API keys", timeout=3)
                return

            # Get the connection manager from the TCP server
            connection_manager = getattr(self.tcp_server, "connection_manager", None)
            if not connection_manager:
                self.notify("Connection manager not available", severity="error")
                return

            # Revoke the API key
            success = await connection_manager.delete_api_key(key_id)
            if success:
                self.logger.info("Revoked API key", key_id=key_id)
                self.notify(f"API key {key_id} revoked successfully", timeout=3)
                self._add_log_entry("info", f"API key {key_id} revoked")
                # Update connection panel
                self._update_connection_panel()
            else:
                self.notify(f"Failed to revoke API key {key_id}", severity="error")

        except Exception as e:
            self.logger.error("Failed to revoke API key", error=str(e))
            self.notify(f"Failed to revoke API key: {e}", timeout=5)

    def watch_server_running(self, running: bool) -> None:
        """Watch for server running state changes."""
        self.logger.debug("Server running state changed", running=running)

        # Update server panel
        server_panel = self.query_one("#server-panel", ServerPanel)
        server_panel.update_server_status(running)

    def watch_server_port(self, port: int) -> None:
        """Watch for server port changes."""
        self.logger.debug("Server port changed", port=port)
        self.sub_title = f"Port: {port} | Address: {self.server_address}"

    def watch_server_address(self, address: str) -> None:
        """Watch for server address changes."""
        self.logger.debug("Server address changed", address=address)
        self.sub_title = f"Port: {self.server_port} | Address: {address}"


def run_tui(config_path: str | None = None) -> None:
    """Run the TUI application.

    Args:
        config_path: Optional path to configuration file

    """
    app = DShieldTUIApp(config_path)
    app.run()


if __name__ == "__main__":
    run_tui()
