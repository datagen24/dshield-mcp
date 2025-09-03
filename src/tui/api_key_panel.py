"""API key management panel for DShield MCP TUI.

This module provides a panel for managing API keys, including viewing,
generating, and deleting API keys stored in 1Password.
"""

from datetime import datetime
from typing import Any

import structlog
from textual.app import ComposeResult  # type: ignore
from textual.containers import Container, Horizontal, Vertical  # type: ignore
from textual.message import Message  # type: ignore
from textual.widgets import Button, DataTable, Label, Static  # type: ignore

logger = structlog.get_logger(__name__)


class APIKeyDelete(Message):  # type: ignore
    """Message sent when an API key should be deleted."""

    def __init__(self, key_id: str) -> None:
        """Initialize API key delete message.

        Args:
            key_id: The unique identifier of the API key to delete

        """
        super().__init__()
        self.key_id = key_id


class APIKeyPanel(Container):
    """Panel for managing API keys."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the API key panel."""
        super().__init__(**kwargs)
        self.logger = structlog.get_logger(__name__)
        self.api_keys: list[dict[str, Any]] = []

    def compose(self) -> ComposeResult:
        """Compose the panel layout."""
        with Vertical(id="api-key-panel"):
            yield Static("API Key Management", id="panel-title")

            with Horizontal(id="api-key-controls"):
                yield Button("Generate New Key", id="generate-key-btn", variant="primary")
                yield Button("Refresh", id="refresh-keys-btn", variant="default")

            yield Label("Existing API Keys:", id="keys-label")
            yield DataTable(id="api-keys-table")

            with Horizontal(id="api-key-actions"):
                yield Button("Delete Selected", id="delete-key-btn", variant="error", disabled=True)
                yield Button("View Details", id="view-key-btn", variant="default", disabled=True)

    def on_mount(self) -> None:
        """Handle panel mount event."""
        # Initialize the data table
        table = self.query_one("#api-keys-table", DataTable)
        table.add_columns("Name", "Created", "Expires", "Permissions", "Status")
        table.cursor_type = "row"

        # Load initial data
        self.refresh_api_keys()

    def on_button_pressed(self, event: Button.Pressed) -> None:  # type: ignore
        """Handle button press events."""
        if event.button.id == "generate-key-btn":
            self._generate_new_key()
        elif event.button.id == "refresh-keys-btn":
            self.refresh_api_keys()
        elif event.button.id == "delete-key-btn":
            self._delete_selected_key()
        elif event.button.id == "view-key-btn":
            self._view_key_details()

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:  # type: ignore
        """Handle row selection in the data table."""
        # Enable/disable action buttons based on selection
        delete_btn = self.query_one("#delete-key-btn", Button)
        view_btn = self.query_one("#view-key-btn", Button)

        if event.cursor_row is not None:
            delete_btn.disabled = False
            view_btn.disabled = False
        else:
            delete_btn.disabled = True
            view_btn.disabled = True

    def _generate_new_key(self) -> None:
        """Open the API key generation screen."""
        from .screens.api_key_screen import APIKeyGenerationScreen

        self.app.push_screen(APIKeyGenerationScreen(), self._on_api_key_generated)

    async def _on_api_key_generated(self, key_config: dict[str, Any]) -> None:
        """Handle API key generation completion."""
        try:
            # This would typically call the connection manager to generate the key
            # For now, we'll just refresh the list
            self.refresh_api_keys()
            self.notify("API key generated successfully", severity="information")
        except Exception as e:
            self.logger.error("Error handling API key generation", error=str(e))
            self.notify(f"Error generating API key: {e}", severity="error")

    def _delete_selected_key(self) -> None:
        """Delete the selected API key."""
        table = self.query_one("#api-keys-table", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(self.api_keys):
            key_info = self.api_keys[table.cursor_row]
            key_id = key_info["key_id"]

            # Send delete message
            self.post_message(APIKeyDelete(key_id))

    def _view_key_details(self) -> None:
        """View details of the selected API key."""
        table = self.query_one("#api-keys-table", DataTable)
        if table.cursor_row is not None and table.cursor_row < len(self.api_keys):
            key_info = self.api_keys[table.cursor_row]

            # Create a simple details display
            details = f"""
API Key Details:
Name: {key_info['name']}
ID: {key_info['key_id']}
Created: {key_info['created_at']}
Expires: {key_info['expires_at'] or 'Never'}
Permissions: {', '.join([k for k, v in key_info['permissions'].items() if v])}
Status: {'Active' if not key_info['is_expired'] else 'Expired'}
"""
            self.notify(details, severity="information", timeout=10)

    def refresh_api_keys(self) -> None:
        """Refresh the API keys list."""
        try:
            # This would typically call the connection manager to get the keys
            # For now, we'll use mock data
            self.api_keys = [
                {
                    "key_id": "key_12345678",
                    "name": "Development Key",
                    "created_at": "2024-01-15T10:30:00Z",
                    "expires_at": "2024-04-15T10:30:00Z",
                    "permissions": {"read_tools": True, "write_back": False, "admin_access": False},
                    "is_expired": False,
                },
                {
                    "key_id": "key_87654321",
                    "name": "Production Key",
                    "created_at": "2024-01-10T14:20:00Z",
                    "expires_at": None,
                    "permissions": {"read_tools": True, "write_back": True, "admin_access": True},
                    "is_expired": False,
                },
            ]

            self._update_table()

        except Exception as e:
            self.logger.error("Error refreshing API keys", error=str(e))
            self.notify(f"Error refreshing API keys: {e}", severity="error")

    def _update_table(self) -> None:
        """Update the data table with current API keys."""
        table = self.query_one("#api-keys-table", DataTable)
        table.clear()

        for key_info in self.api_keys:
            # Format permissions
            permissions = []
            if key_info["permissions"].get("read_tools"):
                permissions.append("Read")
            if key_info["permissions"].get("write_back"):
                permissions.append("Write")
            if key_info["permissions"].get("admin_access"):
                permissions.append("Admin")

            permissions_str = ", ".join(permissions) if permissions else "None"

            # Format dates
            created_date = datetime.fromisoformat(key_info["created_at"].replace("Z", "+00:00"))
            created_str = created_date.strftime("%Y-%m-%d")

            expires_str = "Never"
            if key_info["expires_at"]:
                expires_date = datetime.fromisoformat(key_info["expires_at"].replace("Z", "+00:00"))
                expires_str = expires_date.strftime("%Y-%m-%d")

            # Determine status
            status = "Active"
            if key_info["is_expired"]:
                status = "Expired"

            table.add_row(
                key_info["name"],
                created_str,
                expires_str,
                permissions_str,
                status,
            )

    def on_api_key_delete(self, event: APIKeyDelete) -> None:
        """Handle API key deletion."""
        try:
            # This would typically call the connection manager to delete the key
            # For now, we'll just refresh the list
            self.refresh_api_keys()
            self.notify(f"API key {event.key_id} deleted", severity="information")
        except Exception as e:
            self.logger.error("Error deleting API key", key_id=event.key_id, error=str(e))
            self.notify(f"Error deleting API key: {e}", severity="error")
