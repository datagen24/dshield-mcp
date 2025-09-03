"""API key generation screen for DShield MCP TUI.

This module provides a modal screen for generating and configuring API keys
with permissions, expiration, and rate limiting options.
"""

from typing import Any

import structlog
from textual.app import ComposeResult  # type: ignore
from textual.containers import Container, Horizontal, Vertical  # type: ignore
from textual.message import Message  # type: ignore
from textual.screen import ModalScreen  # type: ignore
from textual.widgets import (  # type: ignore
    Button,
    Checkbox,
    Input,
    Label,
    Select,
    Static,
)

logger = structlog.get_logger(__name__)


class APIKeyGenerated(Message):  # type: ignore
    """Message sent when an API key has been generated."""

    def __init__(self, key_config: dict[str, Any]) -> None:
        """Initialize API key generated message.

        Args:
            key_config: Configuration for the generated API key

        """
        super().__init__()
        self.key_config = key_config


class APIKeyGenerationScreen(ModalScreen):
    """Modal screen for API key configuration and generation."""

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the API key generation screen."""
        super().__init__(**kwargs)
        self.logger = structlog.get_logger(__name__)

    def compose(self) -> ComposeResult:
        """Compose the screen layout."""
        with Container(id="api-key-dialog"):
            yield Static("Generate API Key", id="title")

            with Vertical(id="form-container"):
                yield Label("Key Name:")
                yield Input(placeholder="Enter a name for this API key", id="key-name")

                yield Label("Permissions:")
                with Vertical(id="permissions-container"):
                    yield Checkbox("Read Tools", id="perm-read", value=True)
                    yield Checkbox("Write Back", id="perm-write")
                    yield Checkbox("Admin Access", id="perm-admin")

                yield Label("Rate Limit (requests per minute):")
                yield Input(placeholder="60", id="rate-limit", value="60")

                yield Label("Expiration:")
                yield Select(
                    [
                        ("30 days", 30),
                        ("90 days", 90),
                        ("1 year", 365),
                        ("Never", None),
                    ],
                    prompt="Select expiration period",
                    id="expiration",
                )

            with Horizontal(id="button-container"):
                yield Button("Generate", id="generate-btn", variant="primary")
                yield Button("Cancel", id="cancel-btn", variant="default")

    def on_button_pressed(self, event: Button.Pressed) -> None:  # type: ignore
        """Handle button press events."""
        if event.button.id == "generate-btn":
            self._generate_api_key()
        elif event.button.id == "cancel-btn":
            self.dismiss()

    def _generate_api_key(self) -> None:
        """Generate API key with the configured settings."""
        try:
            # Get form values
            key_name_input = self.query_one("#key-name", Input)
            key_name = key_name_input.value.strip()

            if not key_name:
                self.notify("Key name is required", severity="error")
                return

            # Get permissions
            permissions = {}
            read_checkbox = self.query_one("#perm-read", Checkbox)
            write_checkbox = self.query_one("#perm-write", Checkbox)
            admin_checkbox = self.query_one("#perm-admin", Checkbox)

            permissions["read_tools"] = read_checkbox.value
            permissions["write_back"] = write_checkbox.value
            permissions["admin_access"] = admin_checkbox.value

            # Get rate limit
            rate_limit_input = self.query_one("#rate-limit", Input)
            try:
                rate_limit = int(rate_limit_input.value) if rate_limit_input.value else 60
            except ValueError:
                rate_limit = 60

            permissions["rate_limit"] = rate_limit

            # Get expiration
            expiration_select = self.query_one("#expiration", Select)
            expiration_days = expiration_select.value

            # Create key configuration
            key_config = {
                "name": key_name,
                "permissions": permissions,
                "expiration_days": expiration_days,
                "rate_limit": rate_limit,
            }

            # Send message with configuration
            self.post_message(APIKeyGenerated(key_config))
            self.dismiss()

        except Exception as e:
            self.logger.error("Error generating API key", error=str(e))
            self.notify(f"Error generating API key: {e}", severity="error")

    def on_mount(self) -> None:
        """Handle screen mount event."""
        # Focus on the key name input
        key_name_input = self.query_one("#key-name", Input)
        key_name_input.focus()
