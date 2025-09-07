#!/usr/bin/env python3
"""Connection management panel for DShield MCP TUI.

This module provides a terminal UI panel for managing TCP connections,
including viewing active connections, disconnecting clients, and managing API keys.
"""

import asyncio
from datetime import datetime
from typing import Any

import structlog
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, DataTable, Input, Static

logger = structlog.get_logger(__name__)


class ConnectionDisconnect(Message):
    """Message sent when a connection should be disconnected."""

    def __init__(self, client_address: str) -> None:
        """Initialize connection disconnect message.

        Args:
            client_address: Address of the client to disconnect

        """
        super().__init__()
        self.client_address = client_address


class APIKeyGenerate(Message):
    """Message sent when a new API key should be generated."""

    def __init__(self, permissions: dict[str, Any] | None = None) -> None:
        """Initialize API key generation message.

        Args:
            permissions: Optional permissions for the new API key

        """
        super().__init__()
        self.permissions = permissions or {}


class APIKeyRevoke(Message):
    """Message sent when an API key should be revoked."""

    def __init__(self, api_key_id: str) -> None:
        """Initialize API key revocation message.

        Args:
            api_key_id: ID of the API key to revoke

        """
        super().__init__()
        self.api_key_id = api_key_id


class ConnectionRefresh(Message):
    """Message sent when connections should be refreshed."""

    def __init__(self) -> None:
        """Initialize connection refresh message."""
        super().__init__()


class ConnectionFilter(Message):
    """Message sent when connection filter changes."""

    def __init__(self, filter_text: str) -> None:
        """Initialize connection filter message.

        Args:
            filter_text: Text to filter connections by

        """
        super().__init__()
        self.filter_text = filter_text


class ConnectionPanel(Container):
    """Panel for managing TCP connections and API keys.

    This panel displays active connections, allows disconnecting clients,
    and provides API key management functionality.
    """

    def __init__(self, id: str = "connection-panel", refresh_interval: float = 5.0) -> None:
        """Initialize the connection panel.

        Args:
            id: Panel ID
            refresh_interval: Refresh interval in seconds

        """
        super().__init__(id=id)
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")

        # State
        self.connections: list[dict[str, Any]] = []
        self.api_keys: list[dict[str, Any]] = []
        self.filtered_connections: list[dict[str, Any]] = []
        self.selected_connection: str | None = None
        self.selected_api_key_id: str | None = None
        
        # Filtering and pagination
        self.filter_text: str = ""
        self.current_page: int = 0
        self.page_size: int = 20
        
        # Refresh management
        self.refresh_interval: float = refresh_interval
        self.refresh_task: asyncio.Task[None] | None = None
        self.is_refreshing: bool = False

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
                yield Button("Auto Refresh", id="auto-refresh-btn")

            # Connection filter
            with Horizontal(classes="connection-filter"):
                yield Static("Filter:", classes="filter-label")
                yield Input(
                    placeholder="Filter by address or key ID...", 
                    id="connection-filter-input"
                )

            # Connections table
            yield Static("Active Connections:", classes="section-title")
            yield DataTable(id="connections-table")

            # Pagination controls
            with Horizontal(classes="pagination-controls"):
                yield Button("Previous", id="prev-page-btn", disabled=True)
                yield Static("Page 1 of 1", id="page-info")
                yield Button("Next", id="next-page-btn", disabled=True)

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

        # Initialize connections table with enhanced columns
        connections_table = self.query_one("#connections-table", DataTable)
        connections_table.add_columns(
            "Client Address",
            "Key ID",
            "Permissions",
            "RPS",
            "Violations",
            "Connected At",
            "Status",
        )

        # Initialize API keys table
        api_keys_table = self.query_one("#api-keys-table", DataTable)
        api_keys_table.add_columns(
            "Key ID",
            "Created",
            "Expires",
            "Permissions",
            "Active Sessions",
        )

        # Start auto-refresh if enabled
        self._start_auto_refresh()

    def update_connections(self, connections: list[dict[str, Any]]) -> None:
        """Update the connections display.

        Args:
            connections: List of connection information

        """
        self.connections = connections
        self._apply_filter()
        self._update_connections_display()

    def _apply_filter(self) -> None:
        """Apply current filter to connections."""
        if not self.filter_text:
            self.filtered_connections = self.connections.copy()
        else:
            filter_lower = self.filter_text.lower()
            self.filtered_connections = [
                conn for conn in self.connections
                if (filter_lower in str(conn.get("client_address", "")).lower() or
                    filter_lower in str(conn.get("api_key_id", "")).lower() or
                    filter_lower in str(conn.get("key_id", "")).lower())
            ]

    def _update_connections_display(self) -> None:
        """Update the connections table display."""
        connections_table = self.query_one("#connections-table", DataTable)
        
        # Clear existing data
        connections_table.clear()

        # Calculate pagination
        total_pages = max(
            1, (len(self.filtered_connections) + self.page_size - 1) // self.page_size
        )
        self.current_page = min(self.current_page, total_pages - 1)
        
        start_idx = self.current_page * self.page_size
        end_idx = start_idx + self.page_size
        page_connections = self.filtered_connections[start_idx:end_idx]

        # Add connection data with enhanced information
        for conn in page_connections:
            # Format permissions
            permissions = conn.get("permissions", {})
            if isinstance(permissions, dict):
                perm_str = ", ".join([f"{k}: {v}" for k, v in permissions.items() if v])
            else:
                perm_str = str(permissions) if permissions else "None"

            # Format connected_at timestamp
            connected_at = conn.get("connected_at")
            if connected_at:
                if isinstance(connected_at, str):
                    try:
                        dt = datetime.fromisoformat(connected_at.replace('Z', '+00:00'))
                        connected_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        connected_str = str(connected_at)
                else:
                    connected_str = str(connected_at)
            else:
                connected_str = "Unknown"

            # Determine status
            status = "Active"
            if not conn.get("is_authenticated", False):
                status = "Unauthenticated"
            elif conn.get("violations", 0) > 0:
                status = "Violations"

            connections_table.add_row(
                str(conn.get("client_address", "Unknown")),
                str(conn.get("api_key_id", conn.get("key_id", "N/A"))),
                perm_str,
                str(conn.get("rps", conn.get("requests_per_second", 0))),
                str(conn.get("violations", 0)),
                connected_str,
                status,
            )

        # Update pagination controls
        self._update_pagination_controls(total_pages)

        self.logger.debug(
            "Updated connections display", 
            total=len(self.connections),
            filtered=len(self.filtered_connections),
            page=self.current_page + 1,
            total_pages=total_pages
        )

    def _update_pagination_controls(self, total_pages: int) -> None:
        """Update pagination control states.

        Args:
            total_pages: Total number of pages

        """
        try:
            prev_btn = self.query_one("#prev-page-btn", Button)
            next_btn = self.query_one("#next-page-btn", Button)
            page_info = self.query_one("#page-info", Static)

            # Update button states
            prev_btn.disabled = self.current_page <= 0
            next_btn.disabled = self.current_page >= total_pages - 1

            # Update page info
            page_info.update(f"Page {self.current_page + 1} of {total_pages}")
        except Exception as e:
            self.logger.warning("Error updating pagination controls", error=str(e))

    def _start_auto_refresh(self) -> None:
        """Start auto-refresh task."""
        if self.refresh_task and not self.refresh_task.done():
            self.refresh_task.cancel()
        
        self.refresh_task = asyncio.create_task(self._auto_refresh_loop())

    def _stop_auto_refresh(self) -> None:
        """Stop auto-refresh task."""
        if self.refresh_task and not self.refresh_task.done():
            self.refresh_task.cancel()
            self.refresh_task = None

    async def _auto_refresh_loop(self) -> None:
        """Auto-refresh loop."""
        while True:
            try:
                await asyncio.sleep(self.refresh_interval)
                if not self.is_refreshing:
                    self.post_message(ConnectionRefresh())
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in auto-refresh loop", error=str(e))

    def update_api_keys(self, api_keys: list[dict[str, Any]]) -> None:
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
                permissions_str = ", ".join([f"{k}: {v}" for k, v in permissions.items() if v])

                api_keys_table.add_row(
                    key.get("key_id", "Unknown"),
                    key.get("created_at", "Unknown"),
                    key.get("expires_at", "Unknown"),
                    permissions_str or "None",
                    str(key.get("active_sessions", 0)),
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
        elif button_id == "auto-refresh-btn":
            self._toggle_auto_refresh()
        elif button_id == "prev-page-btn":
            self._previous_page()
        elif button_id == "next-page-btn":
            self._next_page()
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

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input change events.

        Args:
            event: Input change event

        """
        if event.input.id == "connection-filter-input":
            self.filter_text = event.value
            self.current_page = 0  # Reset to first page when filtering
            self._apply_filter()
            self._update_connections_display()
            self.logger.debug("Filter applied", filter_text=self.filter_text)

    def _disconnect_selected_connection(self) -> None:
        """Disconnect the selected connection."""
        if not self.selected_connection:
            return

        self.logger.info(
            "Disconnecting selected connection", client_address=self.selected_connection
        )

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
        self.is_refreshing = True
        try:
            # Post refresh message to parent application
            self.post_message(ConnectionRefresh())
        finally:
            self.is_refreshing = False

    def _toggle_auto_refresh(self) -> None:
        """Toggle auto-refresh functionality."""
        if self.refresh_task and not self.refresh_task.done():
            self._stop_auto_refresh()
            self.query_one("#auto-refresh-btn", Button).label = "Auto Refresh"
            self.logger.debug("Auto-refresh stopped")
        else:
            self._start_auto_refresh()
            self.query_one("#auto-refresh-btn", Button).label = "Stop Auto"
            self.logger.debug("Auto-refresh started")

    def _previous_page(self) -> None:
        """Go to previous page."""
        if self.current_page > 0:
            self.current_page -= 1
            self._update_connections_display()
            self.logger.debug("Moved to previous page", page=self.current_page + 1)

    def _next_page(self) -> None:
        """Go to next page."""
        total_pages = max(
            1, (len(self.filtered_connections) + self.page_size - 1) // self.page_size
        )
        if self.current_page < total_pages - 1:
            self.current_page += 1
            self._update_connections_display()
            self.logger.debug("Moved to next page", page=self.current_page + 1)

    def _generate_api_key(self) -> None:
        """Generate a new API key."""
        self.logger.info("Generating new API key")

        # Post API key generation message
        self.post_message(APIKeyGenerate())

    def _revoke_selected_api_key(self) -> None:
        """Revoke the selected API key."""
        if not hasattr(self, 'selected_api_key_id') or not self.selected_api_key_id:
            self.notify("No API key selected", severity="error")
            return

        self.logger.info("Revoking selected API key", key_id=self.selected_api_key_id)
        
        # Post API key revocation message
        self.post_message(APIKeyRevoke(self.selected_api_key_id))
        
        # Clear selection
        self.selected_api_key_id = None
        self.query_one("#revoke-api-key-btn", Button).disabled = True

    def _refresh_api_keys(self) -> None:
        """Refresh the API keys display."""
        self.logger.debug("Refreshing API keys")
        # This would trigger a refresh from the parent application

    def _select_connection(self, row_key: Any) -> None:
        """Select a connection.

        Args:
            row_key: Row key of the selected connection

        """
        # Calculate actual index in filtered connections
        start_idx = self.current_page * self.page_size
        actual_idx = start_idx + row_key
        
        if 0 <= actual_idx < len(self.filtered_connections):
            conn = self.filtered_connections[actual_idx]
            self.selected_connection = str(conn.get("client_address", ""))

            # Enable disconnect button
            self.query_one("#disconnect-btn", Button).disabled = False

            self.logger.debug("Selected connection", client_address=self.selected_connection)

    def _select_api_key(self, row_key: Any) -> None:
        """Select an API key.

        Args:
            row_key: Row key of the selected API key

        """
        if row_key < len(self.api_keys):
            key = self.api_keys[row_key]
            key_id = key.get("key_id", "")
            
            # Store the selected key ID
            self.selected_api_key_id = key_id

            # Enable revoke button
            self.query_one("#revoke-api-key-btn", Button).disabled = False

            self.logger.debug("Selected API key", key_id=key_id)

    def get_connection_statistics(self) -> dict[str, Any]:
        """Get connection statistics.

        Returns:
            Dictionary of connection statistics

        """
        total_connections = len(self.connections)
        authenticated_connections = len(
            [conn for conn in self.connections if conn.get("is_authenticated", False)]
        )
        initialized_connections = len(
            [conn for conn in self.connections if conn.get("is_initialized", False)]
        )
        connections_with_violations = len(
            [conn for conn in self.connections if conn.get("violations", 0) > 0]
        )
        
        # Calculate average RPS
        total_rps = sum(
            conn.get("rps", conn.get("requests_per_second", 0)) 
            for conn in self.connections
        )
        avg_rps = total_rps / total_connections if total_connections > 0 else 0

        return {
            "total_connections": total_connections,
            "authenticated_connections": authenticated_connections,
            "initialized_connections": initialized_connections,
            "unauthenticated_connections": total_connections - authenticated_connections,
            "uninitialized_connections": total_connections - initialized_connections,
            "connections_with_violations": connections_with_violations,
            "average_rps": round(avg_rps, 2),
            "filtered_connections": len(self.filtered_connections),
        }

    def get_api_key_statistics(self) -> dict[str, Any]:
        """Get API key statistics.

        Returns:
            Dictionary of API key statistics

        """
        total_keys = len(self.api_keys)
        active_keys = len([key for key in self.api_keys if key.get("active_sessions", 0) > 0])

        return {
            "total_api_keys": total_keys,
            "active_api_keys": active_keys,
            "inactive_api_keys": total_keys - active_keys,
        }

    def cleanup(self) -> None:
        """Cleanup resources when panel is destroyed."""
        self._stop_auto_refresh()
        self.logger.debug("Connection panel cleaned up")

    def on_unmount(self) -> None:
        """Handle panel unmount event."""
        self.cleanup()
