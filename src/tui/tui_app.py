#!/usr/bin/env python3
"""Main TUI application for DShield MCP Server.

This module provides the main terminal user interface application using textual,
including layout management, event handling, and integration with the TCP server.
"""

import asyncio
import subprocess
import threading
from typing import Any, Dict, List, Optional, Union
from textual.app import App, ComposeResult  # type: ignore
from textual.containers import Container  # type: ignore
from textual.widgets import Header, Footer  # type: ignore
from textual.binding import Binding  # type: ignore
from textual.message import Message  # type: ignore
from textual.reactive import reactive  # type: ignore
import structlog

from .connection_panel import ConnectionPanel
from .server_panel import ServerPanel, ServerStart, ServerStop, ServerRestart
from .log_panel import LogPanel
from .status_bar import StatusBar
from ..user_config import UserConfigManager
from ..tcp_server import EnhancedTCPServer

logger = structlog.get_logger(__name__)


class ServerStatusUpdate(Message):  # type: ignore
    """Message sent when server status is updated."""
    
    def __init__(self, status: Dict[str, Any]) -> None:
        """Initialize server status update message.
        
        Args:
            status: Server status information
        """
        super().__init__()
        self.status = status


class ConnectionUpdate(Message):  # type: ignore
    """Message sent when connection information is updated."""
    
    def __init__(self, connections: List[Dict[str, Any]]) -> None:
        """Initialize connection update message.
        
        Args:
            connections: List of connection information
        """
        super().__init__()
        self.connections = connections


class LogUpdate(Message):  # type: ignore
    """Message sent when new log entries are available."""
    
    def __init__(self, log_entries: List[Dict[str, Any]]) -> None:
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
    
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "restart_server", "Restart Server"),
        Binding("s", "stop_server", "Stop Server"),
        Binding("g", "generate_api_key", "Generate API Key"),
        Binding("c", "clear_logs", "Clear Logs"),
        Binding("t", "test_log", "Test Log"),
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
        self.user_config = UserConfigManager(config_path)
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")
        
        # Server components
        self.tcp_server: Optional[EnhancedTCPServer] = None
        self.server_process: Optional[subprocess.Popen[bytes]] = None
        self.server_running = reactive(False)
        self.server_port = reactive(self.user_config.tcp_transport_settings.port)
        
        # UI state
        self._mounted = False
        self.server_address = reactive(self.user_config.tcp_transport_settings.bind_address)
        self.current_panel = 0
        self.log_entries: List[Dict[str, Any]] = []
        self.connections: List[Dict[str, Any]] = []
        self.server_status: Dict[str, Any] = {}
        
        # Update tasks
        self._update_task: Optional[Union[asyncio.Task[Any], threading.Thread]] = None
    
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
        
        # Mark UI as mounted
        self._mounted = True
        
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
        
        # Stop update task
        if self._update_task and hasattr(self._update_task, 'is_alive') and self._update_task.is_alive():
            # The thread will stop when the daemon process exits
            pass
        
        # Stop server
        if self.server_running:
            self.action_stop_server()
    
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
            if not hasattr(self, '_mounted') or not self._mounted:
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
            self.logger.debug("Available server panels", count=len(all_panels), panels=[p.id for p in all_panels])
            
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
                    "error_rate": 0.0
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
                # Update API keys
                api_keys = getattr(self, 'generated_api_keys', [])
                self.logger.debug("Updating connection panel", api_keys_count=len(api_keys), api_keys=api_keys)
                connection_panel.update_api_keys(api_keys)
                self.logger.debug("Connection panel update_api_keys called")
                
                # Update connections (empty for now in simulation)
                connections: List[Dict[str, Any]] = []
                connection_panel.update_connections(connections)
                
                self.logger.debug("Updated connection panel successfully", api_keys_count=len(api_keys))
            
        except Exception as e:
            self.logger.error("Error updating connection panel", error=str(e))
    
    def _add_log_entry(self, level: str, message: str) -> None:
        """Add a log entry to the log panel."""
        try:
            # Debug: List all available log panels
            all_log_panels = self.query(LogPanel)
            self.logger.debug("Available log panels", count=len(all_log_panels), panels=[p.id for p in all_log_panels])
            
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
                    "source": "tui"
                }
                
                # Add the log entry
                self.logger.debug("Adding log entry to panel", level=level, message=message, log_entry=log_entry)
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
    
    def action_generate_api_key(self) -> None:
        """Generate a new API key."""
        self.logger.info("Generating new API key")
        self._generate_api_key()
    
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
    
    def on_server_start(self, event: ServerStart) -> None:
        """Handle server start message from server panel."""
        self.logger.info("Received server start message")
        self.action_restart_server()
    
    def on_server_stop(self, event: ServerStop) -> None:
        """Handle server stop message from server panel."""
        self.logger.info("Received server stop message")
        self.action_stop_server()
    
    def on_server_restart(self, event: ServerRestart) -> None:
        """Handle server restart message from server panel."""
        self.logger.info("Received server restart message")
        self.action_restart_server()
    
    def _start_server(self) -> None:
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
            
            # For now, simulate server startup to avoid async issues
            # TODO: Integrate with actual process manager from TUI launcher
            self.logger.info("Simulating TCP server startup")
            self.server_running = True
            self.logger.info("TCP server started successfully (simulation)")
            self.notify("Server started successfully", timeout=3)
            
            # Update server panel status
            self._update_server_panel_status()
            
            # Add log entry
            self._add_log_entry("info", "TCP server started successfully (simulation)")
            
        except Exception as e:
            self.logger.error("Failed to start TCP server", error=str(e))
            self.notify(f"Failed to start server: {e}", timeout=5)
    
    def _stop_server(self) -> None:
        """Stop the TCP server."""
        try:
            # For now, simulate server stop to avoid async issues
            self.logger.info("Simulating TCP server stop")
            self.server_running = False
            self.logger.info("TCP server stopped (simulation)")
            self.notify("Server stopped", timeout=3)
            
            # Update server panel status
            self._update_server_panel_status()
            
            # Add log entry
            self._add_log_entry("info", "TCP server stopped (simulation)")
            
        except Exception as e:
            self.logger.error("Error stopping TCP server", error=str(e))
            self.notify(f"Error stopping server: {e}", timeout=5)
    
    def _generate_api_key(self) -> None:
        """Generate a new API key."""
        try:
            if not self.server_running:
                self.notify("Server must be running to generate API keys", timeout=3)
                return
            
            # For now, simulate API key generation
            import uuid
            from datetime import datetime, timedelta
            
            api_key_id = f"key_{uuid.uuid4().hex[:8]}"
            api_key_value = uuid.uuid4().hex
            
            # Store the generated key
            if not hasattr(self, 'generated_api_keys'):
                self.generated_api_keys = []
            
            key_data = {
                "key_id": api_key_id,
                "key_value": api_key_value,
                "created_at": datetime.now().isoformat(),
                "expires_at": (datetime.now() + timedelta(days=30)).isoformat(),
                "permissions": {"read": True, "write": True},
                "active_sessions": 0
            }
            
            self.generated_api_keys.append(key_data)
            
            self.logger.info("Generated new API key (simulation)", api_key_id=api_key_id)
            self.notify(f"API Key generated: {api_key_id}", timeout=5)
            
            # Add log entry for API key generation
            self._add_log_entry("info", f"API Key generated: {api_key_id}")
            
            # Update the connection panel with the new key
            self.logger.debug("Updating connection panel with new API key", key_id=api_key_id)
            self._update_connection_panel()
            
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
