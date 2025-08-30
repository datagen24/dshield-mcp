#!/usr/bin/env python3
"""Main TUI application for DShield MCP Server.

This module provides the main terminal user interface application using textual,
including layout management, event handling, and integration with the TCP server.
"""

import asyncio
import subprocess
from typing import Any, Dict, List, Optional
from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer
from textual.binding import Binding
from textual.message import Message
from textual.reactive import reactive
import structlog

from .connection_panel import ConnectionPanel
from .server_panel import ServerPanel
from .log_panel import LogPanel
from .status_bar import StatusBar
from ..user_config import get_user_config
from ..tcp_server import EnhancedTCPServer

logger = structlog.get_logger(__name__)


class ServerStatusUpdate(Message):
    """Message sent when server status is updated."""
    
    def __init__(self, status: Dict[str, Any]) -> None:
        """Initialize server status update message.
        
        Args:
            status: Server status information
        """
        super().__init__()
        self.status = status


class ConnectionUpdate(Message):
    """Message sent when connection information is updated."""
    
    def __init__(self, connections: List[Dict[str, Any]]) -> None:
        """Initialize connection update message.
        
        Args:
            connections: List of connection information
        """
        super().__init__()
        self.connections = connections


class LogUpdate(Message):
    """Message sent when new log entries are available."""
    
    def __init__(self, log_entries: List[Dict[str, Any]]) -> None:
        """Initialize log update message.
        
        Args:
            log_entries: List of log entries
        """
        super().__init__()
        self.log_entries = log_entries


class DShieldTUIApp(App):
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
        color: $info;
    }
    """
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "restart_server", "Restart Server"),
        Binding("s", "stop_server", "Stop Server"),
        Binding("g", "generate_api_key", "Generate API Key"),
        Binding("c", "clear_logs", "Clear Logs"),
        Binding("h", "show_help", "Help"),
        Binding("tab", "switch_panel", "Switch Panel"),
    ]
    
    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize the TUI application.
        
        Args:
            config_path: Optional path to configuration file
        """
        super().__init__()
        self.config_path = config_path
        self.user_config = get_user_config(config_path)
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")
        
        # Server components
        self.tcp_server: Optional[EnhancedTCPServer] = None
        self.server_process: Optional[subprocess.Popen] = None
        self.server_running = reactive(False)
        self.server_port = reactive(self.user_config.tcp_transport_settings.port)
        self.server_address = reactive(self.user_config.tcp_transport_settings.bind_address)
        
        # UI state
        self.current_panel = 0
        self.log_entries: List[Dict[str, Any]] = []
        self.connections: List[Dict[str, Any]] = []
        self.server_status: Dict[str, Any] = {}
        
        # Update tasks
        self._update_task: Optional[asyncio.Task] = None
    
    def compose(self) -> ComposeResult:
        """Compose the TUI layout.
        
        Returns:
            ComposeResult: The composed UI elements
        """
        yield Header()
        
        with Container(id="main-container"):
            with Container(id="left-panel"):
                yield ConnectionPanel(id="connection-panel")
                yield ServerPanel(id="server-panel")
            
            with Container(id="right-panel"):
                yield LogPanel(id="log-panel")
        
        yield StatusBar(id="status-bar")
        yield Footer()
    
    def on_mount(self) -> None:
        """Handle application mount event."""
        self.logger.info("TUI application mounted")
        self.title = "DShield MCP Server Manager"
        self.sub_title = f"Port: {self.server_port} | Address: {self.server_address}"
        
        # Start update task
        self._update_task = asyncio.create_task(self._periodic_update())
        
        # Auto-start server if configured
        if self.user_config.tui_settings.auto_start_server:
            self.action_restart_server()
    
    def on_unmount(self) -> None:
        """Handle application unmount event."""
        self.logger.info("TUI application unmounting")
        
        # Cancel update task
        if self._update_task:
            self._update_task.cancel()
        
        # Stop server
        if self.server_running:
            self.action_stop_server()
    
    async def _periodic_update(self) -> None:
        """Periodic update task for refreshing UI data."""
        while True:
            try:
                await asyncio.sleep(self.user_config.tui_settings.refresh_interval)
                await self._update_ui_data()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in periodic update", error=str(e))
    
    async def _update_ui_data(self) -> None:
        """Update UI data from server components."""
        try:
            # Update server status
            if self.tcp_server:
                self.server_status = self.tcp_server.get_server_statistics()
                self.post_message(ServerStatusUpdate(self.server_status))
            
            # Update connections
            if self.tcp_server:
                connections = self.tcp_server.connection_manager.get_all_connections()
                self.connections = [
                    {
                        "client_address": conn.client_address,
                        "is_authenticated": conn.is_authenticated,
                        "api_key": conn.api_key[:8] + "..." if conn.api_key else None,
                        "last_activity": conn.last_activity.isoformat(),
                        "is_initialized": conn.is_initialized
                    }
                    for conn in connections
                ]
                self.post_message(ConnectionUpdate(self.connections))
            
            # Update logs (simplified for now)
            # In a real implementation, this would integrate with the logging system
            
        except Exception as e:
            self.logger.error("Error updating UI data", error=str(e))
    
    def action_quit(self) -> None:
        """Quit the application."""
        self.logger.info("Quitting TUI application")
        self.exit()
    
    def action_restart_server(self) -> None:
        """Restart the TCP server."""
        self.logger.info("Restarting TCP server")
        
        # Stop existing server
        if self.server_running:
            self.action_stop_server()
        
        # Start new server
        asyncio.create_task(self._start_server())
    
    def action_stop_server(self) -> None:
        """Stop the TCP server."""
        self.logger.info("Stopping TCP server")
        asyncio.create_task(self._stop_server())
    
    def action_generate_api_key(self) -> None:
        """Generate a new API key."""
        self.logger.info("Generating new API key")
        asyncio.create_task(self._generate_api_key())
    
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
    
    async def _start_server(self) -> None:
        """Start the TCP server."""
        try:
            self.logger.info("Starting TCP server")
            
            # Create server configuration
            tcp_config = {
                "port": self.server_port,
                "bind_address": self.server_address,
                "max_connections": self.user_config.tcp_transport_settings.max_connections,
                "connection_timeout_seconds": self.user_config.tcp_transport_settings.connection_timeout_seconds,
                "connection_management": {
                    "api_key_management": self.user_config.tcp_transport_settings.api_key_management,
                    "permissions": self.user_config.tcp_transport_settings.permissions
                },
                "security": {
                    "global_rate_limit": 1000,
                    "global_burst_limit": 100,
                    "client_rate_limit": self.user_config.tcp_transport_settings.api_key_management.get("rate_limit_per_key", 60),
                    "client_burst_limit": 10,
                    "abuse_threshold": 10,
                    "block_duration_seconds": 3600,
                    "max_connection_attempts": 5,
                    "connection_window_seconds": 300,
                    "input_validation": {
                        "max_message_size": 1048576,
                        "max_field_length": 10000,
                        "allowed_methods": [
                            "initialize", "initialized", "tools/list", "tools/call",
                            "resources/list", "resources/read", "prompts/list", "prompts/get",
                            "authenticate"
                        ]
                    }
                },
                "authentication": {
                    "session_timeout_seconds": 3600,
                    "max_sessions_per_key": 5
                }
            }
            
            # Create and start the TCP server
            # Note: This is a simplified version - in practice, we'd need to integrate
            # with the actual MCP server instance
            self.tcp_server = EnhancedTCPServer(None, tcp_config)  # Placeholder
            await self.tcp_server.start()
            
            self.server_running = True
            self.logger.info("TCP server started successfully")
            self.notify("Server started successfully", timeout=3)
            
        except Exception as e:
            self.logger.error("Failed to start TCP server", error=str(e))
            self.notify(f"Failed to start server: {e}", timeout=5)
    
    async def _stop_server(self) -> None:
        """Stop the TCP server."""
        try:
            if self.tcp_server:
                await self.tcp_server.stop()
                self.tcp_server = None
            
            self.server_running = False
            self.logger.info("TCP server stopped")
            self.notify("Server stopped", timeout=3)
            
        except Exception as e:
            self.logger.error("Error stopping TCP server", error=str(e))
            self.notify(f"Error stopping server: {e}", timeout=5)
    
    async def _generate_api_key(self) -> None:
        """Generate a new API key."""
        try:
            if not self.tcp_server:
                self.notify("Server must be running to generate API keys", timeout=3)
                return
            
            # Generate API key through connection manager
            api_key = self.tcp_server.connection_manager.generate_api_key()
            
            self.logger.info("Generated new API key", api_key_id=api_key.key_id)
            self.notify(f"API Key generated: {api_key.key_id}", timeout=5)
            
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


def run_tui(config_path: Optional[str] = None) -> None:
    """Run the TUI application.
    
    Args:
        config_path: Optional path to configuration file
    """
    app = DShieldTUIApp(config_path)
    app.run()


if __name__ == "__main__":
    run_tui()
