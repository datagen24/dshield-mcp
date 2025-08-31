#!/usr/bin/env python3
"""Connection management panel for DShield MCP TUI.

This module provides a terminal UI panel for managing TCP connections,
including viewing active connections, disconnecting clients, and managing API keys.
"""

from typing import Any, Dict, List, Optional
from textual.containers import Container, Vertical, Horizontal  # type: ignore
from textual.widgets import Static, Button, DataTable  # type: ignore
from textual.message import Message  # type: ignore
from textual.app import ComposeResult  # type: ignore
import structlog

logger = structlog.get_logger(__name__)


class ConnectionDisconnect(Message):  # type: ignore
    """Message sent when a connection should be disconnected."""
    
    def __init__(self, client_address: str) -> None:
        """Initialize connection disconnect message.
        
        Args:
            client_address: Address of the client to disconnect
        """
        super().__init__()
        self.client_address = client_address


class APIKeyGenerate(Message):  # type: ignore
    """Message sent when a new API key should be generated."""
    
    def __init__(self, permissions: Optional[Dict[str, Any]] = None) -> None:
        """Initialize API key generation message.
        
        Args:
            permissions: Optional permissions for the new API key
        """
        super().__init__()
        self.permissions = permissions or {}


class APIKeyRevoke(Message):  # type: ignore
    """Message sent when an API key should be revoked."""
    
    def __init__(self, api_key_id: str) -> None:
        """Initialize API key revocation message.
        
        Args:
            api_key_id: ID of the API key to revoke
        """
        super().__init__()
        self.api_key_id = api_key_id


class ConnectionPanel(Container):  # type: ignore
    """Panel for managing TCP connections and API keys.
    
    This panel displays active connections, allows disconnecting clients,
    and provides API key management functionality.
    """
    
    def __init__(self, id: str = "connection-panel") -> None:
        """Initialize the connection panel.
        
        Args:
            id: Panel ID
        """
        super().__init__(id=id)
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")
        
        # State
        self.connections: List[Dict[str, Any]] = []
        self.api_keys: List[Dict[str, Any]] = []
        self.selected_connection: Optional[str] = None
    
    def compose(self) -> ComposeResult:
        """Compose the connection panel layout.
        
        Returns:
            ComposeResult: The composed UI elements
        """
        yield Static("Connection Management", classes="panel-title")
        
        with Vertical(classes="panel"):
            # Connection controls
            with Horizontal(classes="connection-controls"):
                yield Button("Disconnect Selected", id="disconnect-btn", disabled=True)
                yield Button("Disconnect All", id="disconnect-all-btn")
                yield Button("Refresh", id="refresh-connections-btn")
            
            # Connections table
            yield Static("Active Connections:", classes="section-title")
            yield DataTable(id="connections-table")
            
            # API Key controls
            with Horizontal(classes="api-key-controls"):
                yield Button("Generate API Key", id="generate-api-key-btn")
                yield Button("Revoke Selected", id="revoke-api-key-btn", disabled=True)
                yield Button("Refresh Keys", id="refresh-keys-btn")
            
            # API Keys table
            yield Static("API Keys:", classes="section-title")
            yield DataTable(id="api-keys-table")
    
    def on_mount(self) -> None:
        """Handle panel mount event."""
        self.logger.debug("Connection panel mounted")
        
        # Initialize connections table
        connections_table = self.query_one("#connections-table", DataTable)
        connections_table.add_columns(
            "Client Address",
            "Authenticated",
            "API Key",
            "Last Activity",
            "Initialized"
        )
        
        # Initialize API keys table
        api_keys_table = self.query_one("#api-keys-table", DataTable)
        api_keys_table.add_columns(
            "Key ID",
            "Created",
            "Expires",
            "Permissions",
            "Active Sessions"
        )
    
    def update_connections(self, connections: List[Dict[str, Any]]) -> None:
        """Update the connections display.
        
        Args:
            connections: List of connection information
        """
        self.connections = connections
        connections_table = self.query_one("#connections-table", DataTable)
        
        # Clear existing data
        connections_table.clear()
        
        # Add connection data
        for conn in connections:
            connections_table.add_row(
                str(conn.get("client_address", "Unknown")),
                "Yes" if conn.get("is_authenticated", False) else "No",
                conn.get("api_key", "N/A"),
                conn.get("last_activity", "Unknown"),
                "Yes" if conn.get("is_initialized", False) else "No"
            )
        
        self.logger.debug("Updated connections display", count=len(connections))
    
    def update_api_keys(self, api_keys: List[Dict[str, Any]]) -> None:
        """Update the API keys display.
        
        Args:
            api_keys: List of API key information
        """
        self.logger.debug("update_api_keys called", api_keys_count=len(api_keys), api_keys=api_keys)
        self.api_keys = api_keys
        
        try:
            api_keys_table = self.query_one("#api-keys-table", DataTable)
            self.logger.debug("Found API keys table")
            
            # Clear existing data
            api_keys_table.clear()
            self.logger.debug("Cleared API keys table")
            
            # Add API key data
            for key in api_keys:
                permissions = key.get("permissions", {})
                permissions_str = ", ".join([
                    f"{k}: {v}" for k, v in permissions.items() if v
                ])
                
                api_keys_table.add_row(
                    key.get("key_id", "Unknown"),
                    key.get("created_at", "Unknown"),
                    key.get("expires_at", "Unknown"),
                    permissions_str or "None",
                    str(key.get("active_sessions", 0))
                )
                self.logger.debug("Added API key row", key_id=key.get("key_id"))
            
            self.logger.debug("Updated API keys display", count=len(api_keys))
            
        except Exception as e:
            self.logger.error("Error updating API keys display", error=str(e))
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.
        
        Args:
            event: Button press event
        """
        button_id = event.button.id
        
        if button_id == "disconnect-btn":
            self._disconnect_selected_connection()
        elif button_id == "disconnect-all-btn":
            self._disconnect_all_connections()
        elif button_id == "refresh-connections-btn":
            self._refresh_connections()
        elif button_id == "generate-api-key-btn":
            self._generate_api_key()
        elif button_id == "revoke-api-key-btn":
            self._revoke_selected_api_key()
        elif button_id == "refresh-keys-btn":
            self._refresh_api_keys()
    
    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        """Handle data table row selection.
        
        Args:
            event: Row selection event
        """
        table_id = event.data_table.id
        
        if table_id == "connections-table":
            self._select_connection(event.row_key)
        elif table_id == "api-keys-table":
            self._select_api_key(event.row_key)
    
    def _disconnect_selected_connection(self) -> None:
        """Disconnect the selected connection."""
        if not self.selected_connection:
            return
        
        self.logger.info("Disconnecting selected connection", 
                        client_address=self.selected_connection)
        
        # Post disconnect message
        self.post_message(ConnectionDisconnect(self.selected_connection))
        
        # Clear selection
        self.selected_connection = None
        self.query_one("#disconnect-btn", Button).disabled = True
    
    def _disconnect_all_connections(self) -> None:
        """Disconnect all active connections."""
        self.logger.info("Disconnecting all connections")
        
        # Post disconnect messages for all connections
        for conn in self.connections:
            client_address = conn.get("client_address")
            if client_address:
                self.post_message(ConnectionDisconnect(str(client_address)))
    
    def _refresh_connections(self) -> None:
        """Refresh the connections display."""
        self.logger.debug("Refreshing connections")
        # This would trigger a refresh from the parent application
        # For now, we'll just log the action
    
    def _generate_api_key(self) -> None:
        """Generate a new API key."""
        self.logger.info("Generating new API key")
        
        # Post API key generation message
        self.post_message(APIKeyGenerate())
    
    def _revoke_selected_api_key(self) -> None:
        """Revoke the selected API key."""
        # This would be implemented to revoke a selected API key
        self.logger.info("Revoking selected API key")
    
    def _refresh_api_keys(self) -> None:
        """Refresh the API keys display."""
        self.logger.debug("Refreshing API keys")
        # This would trigger a refresh from the parent application
    
    def _select_connection(self, row_key: Any) -> None:
        """Select a connection.
        
        Args:
            row_key: Row key of the selected connection
        """
        if row_key < len(self.connections):
            conn = self.connections[row_key]
            self.selected_connection = str(conn.get("client_address", ""))
            
            # Enable disconnect button
            self.query_one("#disconnect-btn", Button).disabled = False
            
            self.logger.debug("Selected connection", 
                            client_address=self.selected_connection)
    
    def _select_api_key(self, row_key: Any) -> None:
        """Select an API key.
        
        Args:
            row_key: Row key of the selected API key
        """
        if row_key < len(self.api_keys):
            key = self.api_keys[row_key]
            key_id = key.get("key_id", "")
            
            # Enable revoke button
            self.query_one("#revoke-api-key-btn", Button).disabled = False
            
            self.logger.debug("Selected API key", key_id=key_id)
    
    def get_connection_statistics(self) -> Dict[str, Any]:
        """Get connection statistics.
        
        Returns:
            Dictionary of connection statistics
        """
        total_connections = len(self.connections)
        authenticated_connections = len([
            conn for conn in self.connections 
            if conn.get("is_authenticated", False)
        ])
        initialized_connections = len([
            conn for conn in self.connections 
            if conn.get("is_initialized", False)
        ])
        
        return {
            "total_connections": total_connections,
            "authenticated_connections": authenticated_connections,
            "initialized_connections": initialized_connections,
            "unauthenticated_connections": total_connections - authenticated_connections,
            "uninitialized_connections": total_connections - initialized_connections
        }
    
    def get_api_key_statistics(self) -> Dict[str, Any]:
        """Get API key statistics.
        
        Returns:
            Dictionary of API key statistics
        """
        total_keys = len(self.api_keys)
        active_keys = len([
            key for key in self.api_keys 
            if key.get("active_sessions", 0) > 0
        ])
        
        return {
            "total_api_keys": total_keys,
            "active_api_keys": active_keys,
            "inactive_api_keys": total_keys - active_keys
        }
