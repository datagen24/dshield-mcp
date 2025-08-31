#!/usr/bin/env python3
"""Server management panel for DShield MCP TUI.

This module provides a terminal UI panel for managing the MCP server,
including starting/stopping the server, viewing server status, and configuration.
"""

from datetime import datetime
from typing import Any, Dict, Optional
from textual.containers import Container, Vertical, Horizontal  # type: ignore
from textual.widgets import Static, Button, Input, Label  # type: ignore
from textual.message import Message  # type: ignore
from textual.reactive import reactive  # type: ignore
from textual.app import ComposeResult  # type: ignore
import structlog

logger = structlog.get_logger(__name__)


class ServerStart(Message):  # type: ignore
    """Message sent when server should be started."""
    pass


class ServerStop(Message):  # type: ignore
    """Message sent when server should be stopped."""
    pass


class ServerRestart(Message):  # type: ignore
    """Message sent when server should be restarted."""
    pass


class ServerConfigUpdate(Message):  # type: ignore
    """Message sent when server configuration should be updated."""
    
    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize server config update message.
        
        Args:
            config: New server configuration
        """
        super().__init__()
        self.config = config


class ServerPanel(Container):  # type: ignore
    """Panel for managing the MCP server.
    
    This panel provides controls for starting/stopping the server,
    viewing server status, and managing server configuration.
    """
    
    def __init__(self, id: str = "server-panel") -> None:
        """Initialize the server panel.
        
        Args:
            id: Panel ID
        """
        super().__init__(id=id)
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")
        
        # State
        self.server_running = reactive(False)
        self.server_status: Dict[str, Any] = {}
        self.server_config: Dict[str, Any] = {}
        self.uptime_start: Optional[datetime] = None
    
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
            
            # Configuration
            yield Static("Configuration:", classes="section-title")
            with Horizontal():
                yield Label("Port:")
                yield Input(placeholder="3000", id="port-input")
            with Horizontal():
                yield Label("Bind Address:")
                yield Input(placeholder="127.0.0.1", id="address-input")
            with Horizontal():
                yield Label("Max Connections:")
                yield Input(placeholder="10", id="max-connections-input")
            
            # Configuration controls
            with Horizontal(classes="config-controls"):
                yield Button("Apply Config", id="apply-config-btn", disabled=True)
                yield Button("Reset Config", id="reset-config-btn")
    
    def on_mount(self) -> None:
        """Handle panel mount event."""
        self.logger.debug("Server panel mounted")
        
        # Initialize configuration inputs
        self._initialize_config_inputs()
    
    def _initialize_config_inputs(self) -> None:
        """Initialize configuration input fields."""
        # Set default values
        port_input = self.query_one("#port-input", Input)
        address_input = self.query_one("#address-input", Input)
        max_connections_input = self.query_one("#max-connections-input", Input)
        
        port_input.value = "3000"
        address_input.value = "127.0.0.1"
        max_connections_input.value = "10"
    
    def update_server_status(self, running: bool) -> None:
        """Update server running status.
        
        Args:
            running: Whether the server is running
        """
        self.server_running = running
        
        # Update button states
        start_btn = self.query_one("#start-server-btn", Button)
        stop_btn = self.query_one("#stop-server-btn", Button)
        restart_btn = self.query_one("#restart-server-btn", Button)
        
        start_btn.disabled = running
        stop_btn.disabled = not running
        restart_btn.disabled = not running
        
        self.logger.debug("Updated server button states", 
                         running=running, 
                         start_disabled=start_btn.disabled,
                         stop_disabled=stop_btn.disabled,
                         restart_disabled=restart_btn.disabled)
        
        # Update status text
        status_text = self.query_one("#server-status-text", Static)
        if running:
            status_text.update("Status: Running")
            if not self.uptime_start:
                self.uptime_start = datetime.now()
        else:
            status_text.update("Status: Stopped")
            self.uptime_start = None
        
        self.logger.debug("Updated server status", running=running)
    
    def update_server_statistics(self, stats: Dict[str, Any]) -> None:
        """Update server statistics display.
        
        Args:
            stats: Server statistics dictionary
        """
        self.server_status = stats
        
        # Update uptime
        uptime_text = self.query_one("#server-uptime-text", Static)
        if self.uptime_start:
            uptime = datetime.now() - self.uptime_start
            uptime_str = str(uptime).split('.')[0]  # Remove microseconds
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
        elif button_id == "apply-config-btn":
            self._apply_config()
        elif button_id == "reset-config-btn":
            self._reset_config()
    
    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input field changes.
        
        Args:
            event: Input change event
        """
        # Enable apply config button when inputs change
        apply_btn = self.query_one("#apply-config-btn", Button)
        apply_btn.disabled = False
    
    def _start_server(self) -> None:
        """Start the server."""
        self.logger.info("Starting server")
        self.post_message(ServerStart())
    
    def _stop_server(self) -> None:
        """Stop the server."""
        self.logger.info("Stopping server")
        self.post_message(ServerStop())
    
    def _restart_server(self) -> None:
        """Restart the server."""
        self.logger.info("Restarting server")
        self.post_message(ServerRestart())
    
    def _apply_config(self) -> None:
        """Apply configuration changes."""
        try:
            # Get configuration from inputs
            port_input = self.query_one("#port-input", Input)
            address_input = self.query_one("#address-input", Input)
            max_connections_input = self.query_one("#max-connections-input", Input)
            
            config = {
                "port": int(port_input.value) if port_input.value else 3000,
                "bind_address": address_input.value or "127.0.0.1",
                "max_connections": int(max_connections_input.value) if max_connections_input.value else 10
            }
            
            # Validate configuration
            port = config["port"]
            max_connections = config["max_connections"]
            
            if isinstance(port, str):
                try:
                    port = int(port)
                except ValueError:
                    self.logger.error("Invalid port number", port=port)
                    return
            
            if isinstance(max_connections, str):
                try:
                    max_connections = int(max_connections)
                except ValueError:
                    self.logger.error("Invalid max connections", max_connections=max_connections)
                    return
            
            if port < 1 or port > 65535:
                self.logger.error("Invalid port number", port=port)
                return
            
            if max_connections < 1:
                self.logger.error("Invalid max connections", max_connections=max_connections)
                return
            
            self.logger.info("Applying server configuration", config=config)
            
            # Post configuration update message
            self.post_message(ServerConfigUpdate(config))
            
            # Disable apply button
            apply_btn = self.query_one("#apply-config-btn", Button)
            apply_btn.disabled = True
            
        except ValueError as e:
            self.logger.error("Invalid configuration value", error=str(e))
        except Exception as e:
            self.logger.error("Error applying configuration", error=str(e))
    
    def _reset_config(self) -> None:
        """Reset configuration to defaults."""
        self.logger.info("Resetting server configuration")
        self._initialize_config_inputs()
        
        # Disable apply button
        apply_btn = self.query_one("#apply-config-btn", Button)
        apply_btn.disabled = True
    
    def get_server_configuration(self) -> Dict[str, Any]:
        """Get current server configuration from inputs.
        
        Returns:
            Dictionary of server configuration
        """
        port_input = self.query_one("#port-input", Input)
        address_input = self.query_one("#address-input", Input)
        max_connections_input = self.query_one("#max-connections-input", Input)
        
        return {
            "port": int(port_input.value) if port_input.value else 3000,
            "bind_address": address_input.value or "127.0.0.1",
            "max_connections": int(max_connections_input.value) if max_connections_input.value else 10
        }
    
    def set_server_configuration(self, config: Dict[str, Any]) -> None:
        """Set server configuration in inputs.
        
        Args:
            config: Server configuration dictionary
        """
        port_input = self.query_one("#port-input", Input)
        address_input = self.query_one("#address-input", Input)
        max_connections_input = self.query_one("#max-connections-input", Input)
        
        port_input.value = str(config.get("port", 3000))
        address_input.value = str(config.get("bind_address", "127.0.0.1"))
        max_connections_input.value = str(config.get("max_connections", 10))
        
        # Disable apply button since we just set the values
        apply_btn = self.query_one("#apply-config-btn", Button)
        apply_btn.disabled = True
    
    def get_server_health(self) -> Dict[str, Any]:
        """Get server health information.
        
        Returns:
            Dictionary of server health information
        """
        return {
            "running": self.server_running,
            "uptime_seconds": (datetime.now() - self.uptime_start).total_seconds() if self.uptime_start else 0,
            "status": self.server_status,
            "configuration": self.get_server_configuration()
        }
