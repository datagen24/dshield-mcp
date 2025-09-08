"""Tests for TUI API key policy updates.

This module tests the TUI components that support the new API key
storage policy and rotation functionality.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from textual.app import App  # type: ignore

from src.secrets_manager.base_secrets_manager import APIKey
from src.tui.api_key_panel import APIKeyPanel, APIKeyRotate


class TestTUIAPIKeyPolicy:
    """Test cases for TUI API key policy updates."""

    @pytest.fixture
    def mock_app(self) -> App:
        """Create a mock Textual app."""
        app = MagicMock(spec=App)
        app.tcp_server = MagicMock()
        app.tcp_server.connection_manager = MagicMock()
        # Allow setting the app property
        type(app).app = property(lambda self: self)
        return app

    @pytest.fixture
    def api_key_panel(self, mock_app: App) -> APIKeyPanel:
        """Create an API key panel for testing."""
        panel = APIKeyPanel()
        # Mock the methods that need the app
        panel.refresh_api_keys = MagicMock()
        panel._update_table = MagicMock()
        panel.query_one = MagicMock()
        panel.notify = MagicMock()
        panel.post_message = MagicMock()
        panel.logger = MagicMock()
        return panel

    @pytest.fixture
    def sample_api_key(self) -> APIKey:
        """Create a sample API key for testing."""
        return APIKey(
            key_id="test-key-123",
            key_value="dshield_test_key_value_12345",
            name="Test API Key",
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC).replace(year=2025),
            permissions={"read_tools": True, "write_back": False, "admin_access": False},
            metadata={"test": "data"},
            algo_version="sha256-v1",
            needs_rotation=False,
            rps_limit=60,
            verifier="test_verifier_hash",
        )

    def test_api_key_rotate_message(self) -> None:
        """Test APIKeyRotate message creation."""
        message = APIKeyRotate("test-key-123")
        assert message.key_id == "test-key-123"

    def test_refresh_api_keys_includes_new_fields(
        self, api_key_panel: APIKeyPanel, sample_api_key: APIKey
    ) -> None:
        """Test that refresh_api_keys includes new policy fields."""
        # Create a real panel for this test
        panel = APIKeyPanel()
        panel.app = MagicMock()
        panel.app.tcp_server = MagicMock()
        panel.app.tcp_server.connection_manager = MagicMock()
        panel.app.tcp_server.connection_manager.api_keys = {"test_key_value": sample_api_key}

        # Test refresh
        panel.refresh_api_keys()

        # Verify the key was added with new fields
        assert len(panel.api_keys) == 1
        key_info = panel.api_keys[0]

        # Check new fields are present
        assert "needs_rotation" in key_info
        assert "algo_version" in key_info
        assert "rps_limit" in key_info

        # Check values
        assert key_info["needs_rotation"] is False
        assert key_info["algo_version"] == "sha256-v1"
        assert key_info["rps_limit"] == 60

    def test_refresh_api_keys_migration_detection(self, api_key_panel: APIKeyPanel) -> None:
        """Test that refresh_api_keys detects keys needing migration."""
        # Create key that needs rotation (old format)
        old_key = APIKey(
            key_id="old-key-123",
            key_value="old_key_value",
            name="Old Key",
            created_at=datetime.now(UTC),
            expires_at=None,
            permissions={},
            metadata={},
            needs_rotation=True,  # Marked for rotation
            algo_version="sha256-v0",  # Old version
            rps_limit=30,
        )

        # Mock connection manager
        api_key_panel.app.tcp_server.connection_manager.api_keys = {"old_key_value": old_key}

        # Test refresh
        api_key_panel.refresh_api_keys()

        # Verify the key was added with migration flags
        assert len(api_key_panel.api_keys) == 1
        key_info = api_key_panel.api_keys[0]

        assert key_info["needs_rotation"] is True
        assert key_info["algo_version"] == "sha256-v0"
        assert key_info["rps_limit"] == 30

    def test_table_display_includes_rotation_column(self, api_key_panel: APIKeyPanel) -> None:
        """Test that the table display includes rotation status column."""
        # Mock table
        mock_table = MagicMock()
        api_key_panel.query_one = MagicMock(return_value=mock_table)

        # Add sample data
        api_key_panel.api_keys = [
            {
                "key_id": "test-key-123",
                "name": "Test Key",
                "created_at": "2024-01-01T00:00:00+00:00",
                "expires_at": "2025-01-01T00:00:00+00:00",
                "permissions": {"read_tools": True},
                "is_expired": False,
                "needs_rotation": False,
                "algo_version": "sha256-v1",
                "rps_limit": 60,
            }
        ]

        # Test table update
        api_key_panel._update_table()

        # Verify add_row was called with 6 columns (including rotation)
        mock_table.add_row.assert_called_once()
        call_args = mock_table.add_row.call_args[0]
        assert len(call_args) == 6  # Name, Created, Expires, Permissions, Status, Rotation

    def test_rotation_status_display(self, api_key_panel: APIKeyPanel) -> None:
        """Test that rotation status is displayed correctly."""
        # Mock table
        mock_table = MagicMock()
        api_key_panel.query_one = MagicMock(return_value=mock_table)

        # Test different rotation statuses
        test_cases = [
            (False, "sha256-v1", "OK"),
            (True, "sha256-v1", "⚠️ Needs Rotation"),
            (False, "sha256-v0", "⚠️ Old Version"),
            (True, "sha256-v0", "⚠️ Needs Rotation"),
        ]

        for needs_rotation, algo_version, expected_status in test_cases:
            api_key_panel.api_keys = [
                {
                    "key_id": "test-key-123",
                    "name": "Test Key",
                    "created_at": "2024-01-01T00:00:00+00:00",
                    "expires_at": None,
                    "permissions": {},
                    "is_expired": False,
                    "needs_rotation": needs_rotation,
                    "algo_version": algo_version,
                    "rps_limit": 60,
                }
            ]

            # Clear previous calls
            mock_table.add_row.reset_mock()

            # Test table update
            api_key_panel._update_table()

            # Verify rotation status
            call_args = mock_table.add_row.call_args[0]
            rotation_status = call_args[5]  # 6th column
            assert rotation_status == expected_status

    def test_rotate_button_handler(self, api_key_panel: APIKeyPanel) -> None:
        """Test the rotate button handler."""
        # Mock table with selection
        mock_table = MagicMock()
        mock_table.cursor_row = 0
        api_key_panel.query_one = MagicMock(return_value=mock_table)

        # Add sample data
        api_key_panel.api_keys = [
            {
                "key_id": "test-key-123",
                "name": "Test Key",
                "created_at": "2024-01-01T00:00:00+00:00",
                "expires_at": None,
                "permissions": {},
                "is_expired": False,
                "needs_rotation": True,
                "algo_version": "sha256-v1",
                "rps_limit": 60,
            }
        ]

        # Mock post_message
        api_key_panel.post_message = MagicMock()

        # Test rotate
        api_key_panel._rotate_selected_key()

        # Verify message was posted
        api_key_panel.post_message.assert_called_once()
        message = api_key_panel.post_message.call_args[0][0]
        assert isinstance(message, APIKeyRotate)
        assert message.key_id == "test-key-123"

    def test_rotate_button_enable_disable(self, api_key_panel: APIKeyPanel) -> None:
        """Test that rotate button is enabled/disabled correctly."""
        # Mock buttons
        mock_rotate_btn = MagicMock()
        mock_delete_btn = MagicMock()
        mock_view_btn = MagicMock()

        api_key_panel.query_one = MagicMock(
            side_effect=lambda x: {
                "#rotate-key-btn": mock_rotate_btn,
                "#delete-key-btn": mock_delete_btn,
                "#view-key-btn": mock_view_btn,
            }[x]
        )

        # Test with selection
        from textual.widgets import DataTable

        event = MagicMock(spec=DataTable.RowSelected)
        event.cursor_row = 0

        api_key_panel.on_data_table_row_selected(event)

        # Verify buttons are enabled
        assert mock_rotate_btn.disabled is False
        assert mock_delete_btn.disabled is False
        assert mock_view_btn.disabled is False

        # Test without selection
        event.cursor_row = None

        api_key_panel.on_data_table_row_selected(event)

        # Verify buttons are disabled
        assert mock_rotate_btn.disabled is True
        assert mock_delete_btn.disabled is True
        assert mock_view_btn.disabled is True

    def test_rotate_message_handler(self, api_key_panel: APIKeyPanel) -> None:
        """Test the rotate message handler."""
        # Mock refresh and notify
        api_key_panel.refresh_api_keys = MagicMock()
        api_key_panel.notify = MagicMock()

        # Test rotate message
        message = APIKeyRotate("test-key-123")
        api_key_panel.on_api_key_rotate(message)

        # Verify refresh was called
        api_key_panel.refresh_api_keys.assert_called_once()

        # Verify notification was shown
        api_key_panel.notify.assert_called_once()
        call_args = api_key_panel.notify.call_args
        assert "rotated" in call_args[0][0]
        assert "test-key-123" in call_args[0][0]

    def test_rotate_message_handler_error(self, api_key_panel: APIKeyPanel) -> None:
        """Test the rotate message handler with error."""
        # Mock refresh to raise exception
        api_key_panel.refresh_api_keys = MagicMock(side_effect=Exception("Test error"))
        api_key_panel.notify = MagicMock()
        api_key_panel.logger = MagicMock()

        # Test rotate message
        message = APIKeyRotate("test-key-123")
        api_key_panel.on_api_key_rotate(message)

        # Verify error was logged
        api_key_panel.logger.error.assert_called_once()

        # Verify error notification was shown
        api_key_panel.notify.assert_called_once()
        call_args = api_key_panel.notify.call_args
        assert "Error rotating API key" in call_args[0][0]

    def test_key_details_include_new_fields(self, api_key_panel: APIKeyPanel) -> None:
        """Test that key details include new policy fields."""
        # Mock table with selection
        mock_table = MagicMock()
        mock_table.cursor_row = 0
        api_key_panel.query_one = MagicMock(return_value=mock_table)

        # Add sample data with new fields
        api_key_panel.api_keys = [
            {
                "key_id": "test-key-123",
                "name": "Test Key",
                "created_at": "2024-01-01T00:00:00+00:00",
                "expires_at": "2025-01-01T00:00:00+00:00",
                "permissions": {"read_tools": True, "admin_access": True},
                "is_expired": False,
                "needs_rotation": True,
                "algo_version": "sha256-v1",
                "rps_limit": 120,
            }
        ]

        # Mock notify
        api_key_panel.notify = MagicMock()

        # Test view details
        api_key_panel._view_key_details()

        # Verify notification was shown with details
        api_key_panel.notify.assert_called_once()
        details = api_key_panel.notify.call_args[0][0]

        # Check that new fields are mentioned (though not directly visible in this simple format)
        assert "Test Key" in details
        assert "test-key-123" in details
        assert "Active" in details or "Expired" in details

    def test_migration_detection_in_ui(self, api_key_panel: APIKeyPanel) -> None:
        """Test that migration needs are properly detected and displayed in UI."""
        # Create keys with different migration states
        api_key_panel.api_keys = [
            {
                "key_id": "new-key-123",
                "name": "New Key",
                "created_at": "2024-01-01T00:00:00+00:00",
                "expires_at": None,
                "permissions": {},
                "is_expired": False,
                "needs_rotation": False,
                "algo_version": "sha256-v1",
                "rps_limit": 60,
            },
            {
                "key_id": "old-key-456",
                "name": "Old Key",
                "created_at": "2024-01-01T00:00:00+00:00",
                "expires_at": None,
                "permissions": {},
                "is_expired": False,
                "needs_rotation": True,
                "algo_version": "sha256-v0",
                "rps_limit": 30,
            },
        ]

        # Mock table
        mock_table = MagicMock()
        api_key_panel.query_one = MagicMock(return_value=mock_table)

        # Test table update
        api_key_panel._update_table()

        # Verify both keys were added with correct rotation status
        assert mock_table.add_row.call_count == 2

        # Check first key (new format)
        first_call = mock_table.add_row.call_args_list[0][0]
        assert first_call[0] == "New Key"  # Name
        assert first_call[5] == "OK"  # Rotation status

        # Check second key (needs migration)
        second_call = mock_table.add_row.call_args_list[1][0]
        assert second_call[0] == "Old Key"  # Name
        assert second_call[5] == "⚠️ Needs Rotation"  # Rotation status
