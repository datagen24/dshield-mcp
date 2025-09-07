"""Tests for TUI API key one-time reveal functionality.

This module tests the TUI components that handle the one-time
reveal of API keys with proper security cleanup.
"""

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from textual.widgets import Input

from src.tui.api_key_panel import APIKeyPanel
from src.tui.screens.api_key_screen import APIKeyGenerated, APIKeyGenerationScreen

if TYPE_CHECKING:
    pass


class TestAPIKeyGenerationScreen:
    """Test the API key generation screen functionality."""

    def test_screen_initialization(self) -> None:
        """Test that the screen initializes correctly."""
        screen = APIKeyGenerationScreen()

        assert screen.generated_key is None
        assert screen.key_config is None
        assert screen.showing_key is False

    def test_generate_api_key_success(self) -> None:
        """Test successful API key generation."""
        screen = APIKeyGenerationScreen()

        # Mock the API key generator
        with patch('src.api_key_generator.APIKeyGenerator') as mock_generator_class:
            mock_generator = MagicMock()
            mock_generator_class.return_value = mock_generator

            # Mock the generate_api_key method
            mock_key_data = {
                "key_id": "test_key_123",
                "plaintext_key": "dshield_test123456789",
                "hashed_key": "a" * 64,  # Mock SHA-256 hash
                "salt": "b" * 32,  # Mock salt
                "algorithm": "sha256",
                "name": "Test Key",
                "permissions": {"read_tools": True, "write_back": False},
                "expires_at": "2024-12-31T23:59:59Z",
                "rate_limit": 60,
                "metadata": {"generated_by": "dshield-mcp"},
                "created_at": "2024-01-01T00:00:00Z",
            }
            mock_generator.generate_api_key.return_value = mock_key_data

            # Mock the form inputs
            with patch.object(screen, 'query_one') as mock_query:

                def mock_query_side_effect(selector, widget_type):
                    if selector == "#key-name":
                        mock_input = MagicMock(spec=Input)
                        mock_input.value = "Test Key"
                        return mock_input
                    elif selector == "#perm-read":
                        mock_checkbox = MagicMock()
                        mock_checkbox.value = True
                        return mock_checkbox
                    elif selector == "#perm-write":
                        mock_checkbox = MagicMock()
                        mock_checkbox.value = False
                        return mock_checkbox
                    elif selector == "#perm-admin":
                        mock_checkbox = MagicMock()
                        mock_checkbox.value = False
                        return mock_checkbox
                    elif selector == "#rate-limit":
                        mock_input = MagicMock(spec=Input)
                        mock_input.value = "60"
                        return mock_input
                    elif selector == "#expiration":
                        mock_select = MagicMock()
                        mock_select.value = 30
                        return mock_select
                    else:
                        return MagicMock()

                mock_query.side_effect = mock_query_side_effect

                # Mock the refresh method
                with patch.object(screen, 'refresh'):
                    screen._generate_api_key()

                # Verify the key was generated and stored
                assert screen.generated_key == "dshield_test123456789"
                assert screen.key_config is not None
                assert screen.key_config["key_id"] == "test_key_123"
                assert screen.key_config["name"] == "Test Key"
                assert screen.key_config["permissions"]["read_tools"] is True
                assert screen.key_config["permissions"]["write_back"] is False
                assert screen.showing_key is True

    def test_generate_api_key_validation_error(self) -> None:
        """Test API key generation with validation error."""
        screen = APIKeyGenerationScreen()

        # Mock form inputs with empty key name
        with patch.object(screen, 'query_one') as mock_query:

            def mock_query_side_effect(selector, widget_type):
                if selector == "#key-name":
                    mock_input = MagicMock(spec=Input)
                    mock_input.value = ""  # Empty name
                    return mock_input
                else:
                    return MagicMock()

            mock_query.side_effect = mock_query_side_effect

            # Mock the notify method
            with patch.object(screen, 'notify') as mock_notify:
                screen._generate_api_key()

                # Should show error notification
                mock_notify.assert_called_once_with("Key name is required", severity="error")

    def test_generate_api_key_exception_handling(self) -> None:
        """Test exception handling during API key generation."""
        screen = APIKeyGenerationScreen()

        # Mock form inputs
        with patch.object(screen, 'query_one') as mock_query:

            def mock_query_side_effect(selector, widget_type):
                if selector == "#key-name":
                    mock_input = MagicMock(spec=Input)
                    mock_input.value = "Test Key"
                    return mock_input
                elif selector == "#perm-read":
                    mock_checkbox = MagicMock()
                    mock_checkbox.value = True
                    return mock_checkbox
                elif selector == "#perm-write":
                    mock_checkbox = MagicMock()
                    mock_checkbox.value = False
                    return mock_checkbox
                elif selector == "#perm-admin":
                    mock_checkbox = MagicMock()
                    mock_checkbox.value = False
                    return mock_checkbox
                elif selector == "#rate-limit":
                    mock_input = MagicMock(spec=Input)
                    mock_input.value = "60"
                    return mock_input
                elif selector == "#expiration":
                    mock_select = MagicMock()
                    mock_select.value = 30
                    return mock_select
                else:
                    return MagicMock()

            mock_query.side_effect = mock_query_side_effect

            # Mock the API key generator to raise an exception
            with patch('src.tui.screens.api_key_screen.APIKeyGenerator') as mock_generator_class:
                mock_generator = MagicMock()
                mock_generator_class.return_value = mock_generator
                mock_generator.generate_api_key.side_effect = Exception("Test error")

                # Mock the notify method
                with patch.object(screen, 'notify') as mock_notify:
                    screen._generate_api_key()

                    # Should show error notification
                    mock_notify.assert_called_once_with(
                        "Error generating API key: Test error", severity="error"
                    )

    def test_confirm_key_generation_success(self) -> None:
        """Test successful key generation confirmation."""
        screen = APIKeyGenerationScreen()
        screen.generated_key = "dshield_test123456789"
        screen.key_config = {
            "key_id": "test_key_123",
            "name": "Test Key",
            "permissions": {"read_tools": True},
        }

        # Mock the post_message method
        with patch.object(screen, 'post_message') as mock_post_message:
            # Mock the dismiss method
            with patch.object(screen, 'dismiss') as mock_dismiss:
                screen._confirm_key_generation()

                # Should post the APIKeyGenerated message
                mock_post_message.assert_called_once()
                message = mock_post_message.call_args[0][0]
                assert isinstance(message, APIKeyGenerated)
                assert message.key_config == screen.key_config

                # Should dismiss the screen
                mock_dismiss.assert_called_once()

    def test_confirm_key_generation_no_key(self) -> None:
        """Test key generation confirmation with no key."""
        screen = APIKeyGenerationScreen()
        screen.generated_key = None
        screen.key_config = None

        # Mock the notify method
        with patch.object(screen, 'notify') as mock_notify:
            screen._confirm_key_generation()

            # Should show error notification
            mock_notify.assert_called_once_with("No key to confirm", severity="error")

    def test_clear_plaintext_key(self) -> None:
        """Test clearing plaintext key from memory."""
        screen = APIKeyGenerationScreen()
        screen.generated_key = "dshield_test123456789"

        screen._clear_plaintext_key()

        # Key should be cleared
        assert screen.generated_key is None

    def test_clear_plaintext_key_when_none(self) -> None:
        """Test clearing plaintext key when already None."""
        screen = APIKeyGenerationScreen()
        screen.generated_key = None

        # Should not raise an exception
        screen._clear_plaintext_key()

        # Should still be None
        assert screen.generated_key is None

    def test_on_dismiss_clears_key(self) -> None:
        """Test that on_dismiss clears the plaintext key."""
        screen = APIKeyGenerationScreen()
        screen.generated_key = "dshield_test123456789"

        # Call on_dismiss directly (it's a custom method we added)
        screen.on_dismiss()

        # Key should be cleared
        assert screen.generated_key is None


class TestAPIKeyPanel:
    """Test the API key panel functionality."""

    def test_panel_initialization(self) -> None:
        """Test that the panel initializes correctly."""
        panel = APIKeyPanel()

        assert panel.api_keys == []
        assert hasattr(panel, 'logger')

    def test_on_api_key_generated_success(self) -> None:
        """Test successful API key generation handling."""
        panel = APIKeyPanel()

        # Mock the app and connection manager
        mock_app = MagicMock()
        mock_tcp_server = MagicMock()
        mock_connection_manager = AsyncMock()
        mock_api_key = MagicMock()
        mock_api_key.key_id = "test_key_123"
        mock_api_key.name = "Test Key"

        mock_connection_manager.generate_api_key.return_value = mock_api_key
        mock_tcp_server.connection_manager = mock_connection_manager
        mock_app.tcp_server = mock_tcp_server

        # Use patch to set the app attribute
        with patch.object(panel, 'app', mock_app):
            # Mock the refresh_api_keys method
            with patch.object(panel, 'refresh_api_keys') as mock_refresh:
                # Mock the notify method
                with patch.object(panel, 'notify') as mock_notify:
                    key_config = {
                        "name": "Test Key",
                        "permissions": {"read_tools": True},
                        "expiration_days": 30,
                        "rate_limit": 60,
                    }

                    # Run the async method
                    import asyncio

                    asyncio.run(panel._on_api_key_generated(key_config))

                    # Should call the connection manager
                    mock_connection_manager.generate_api_key.assert_called_once_with(
                        name="Test Key",
                        permissions={"read_tools": True},
                        expiration_days=30,
                        rate_limit=60,
                    )

                    # Should refresh the API keys
                    mock_refresh.assert_called_once()

                    # Should show success notification
                    mock_notify.assert_called_once_with(
                        "API key generated successfully", severity="information"
                    )

    def test_on_api_key_generated_no_connection_manager(self) -> None:
        """Test API key generation when connection manager is not available."""
        panel = APIKeyPanel()

        # Mock the app without connection manager
        mock_app = MagicMock()
        mock_tcp_server = MagicMock()
        mock_tcp_server.connection_manager = None
        mock_app.tcp_server = mock_tcp_server

        # Use patch to set the app attribute
        with patch.object(panel, 'app', mock_app):
            # Mock the notify method
            with patch.object(panel, 'notify') as mock_notify:
                key_config = {"name": "Test Key"}

                # Run the async method
                import asyncio

                asyncio.run(panel._on_api_key_generated(key_config))

                # Should show error notification
                mock_notify.assert_called_once_with(
                    "Connection manager not available", severity="error"
                )

    def test_on_api_key_generated_no_server(self) -> None:
        """Test API key generation when server is not running."""
        panel = APIKeyPanel()

        # Mock the app without server
        mock_app = MagicMock()
        mock_app.tcp_server = None

        # Use patch to set the app attribute
        with patch.object(panel, 'app', mock_app):
            # Mock the notify method
            with patch.object(panel, 'notify') as mock_notify:
                key_config = {"name": "Test Key"}

                # Run the async method
                import asyncio

                asyncio.run(panel._on_api_key_generated(key_config))

                # Should show error notification
                mock_notify.assert_called_once_with("Server not running", severity="error")

    def test_on_api_key_generated_failure(self) -> None:
        """Test API key generation failure handling."""
        panel = APIKeyPanel()

        # Mock the app and connection manager
        mock_app = MagicMock()
        mock_tcp_server = MagicMock()
        mock_connection_manager = AsyncMock()
        mock_connection_manager.generate_api_key.return_value = None  # Failure
        mock_tcp_server.connection_manager = mock_connection_manager
        mock_app.tcp_server = mock_tcp_server

        # Use patch to set the app attribute
        with patch.object(panel, 'app', mock_app):
            # Mock the notify method
            with patch.object(panel, 'notify') as mock_notify:
                key_config = {"name": "Test Key"}

                # Run the async method
                import asyncio

                asyncio.run(panel._on_api_key_generated(key_config))

                # Should show error notification
                mock_notify.assert_called_once_with("Failed to generate API key", severity="error")

    def test_refresh_api_keys_with_connection_manager(self) -> None:
        """Test refreshing API keys with connection manager."""
        panel = APIKeyPanel()

        # Mock the app and connection manager
        mock_app = MagicMock()
        mock_tcp_server = MagicMock()
        mock_connection_manager = MagicMock()

        # Mock API key objects
        mock_api_key1 = MagicMock()
        mock_api_key1.key_id = "key1"
        mock_api_key1.name = "Key 1"
        mock_api_key1.created_at = "2024-01-01T00:00:00Z"
        mock_api_key1.expires_at = None
        mock_api_key1.permissions = {"read_tools": True}

        mock_api_key2 = MagicMock()
        mock_api_key2.key_id = "key2"
        mock_api_key2.name = "Key 2"
        mock_api_key2.created_at = "2024-01-02T00:00:00Z"
        mock_api_key2.expires_at = "2024-12-31T23:59:59Z"
        mock_api_key2.permissions = {"read_tools": True, "write_back": True}

        mock_connection_manager.api_keys = {"hash1": mock_api_key1, "hash2": mock_api_key2}
        mock_tcp_server.connection_manager = mock_connection_manager
        mock_app.tcp_server = mock_tcp_server

        # Use patch to set the app attribute
        with patch.object(panel, 'app', mock_app):
            # Mock the _update_table method
            with patch.object(panel, '_update_table') as mock_update_table:
                panel.refresh_api_keys()

                # Should have loaded the API keys
                assert len(panel.api_keys) == 2
                assert panel.api_keys[0]["key_id"] == "key1"
                assert panel.api_keys[1]["key_id"] == "key2"

                # Should update the table
                mock_update_table.assert_called_once()

    def test_refresh_api_keys_no_connection_manager(self) -> None:
        """Test refreshing API keys without connection manager."""
        panel = APIKeyPanel()

        # Mock the app without connection manager
        mock_app = MagicMock()
        mock_tcp_server = MagicMock()
        mock_tcp_server.connection_manager = None
        mock_app.tcp_server = mock_tcp_server

        # Use patch to set the app attribute
        with patch.object(panel, 'app', mock_app):
            # Mock the _update_table method
            with patch.object(panel, '_update_table') as mock_update_table:
                panel.refresh_api_keys()

                # Should have empty list
                assert panel.api_keys == []

                # Should still update the table
                mock_update_table.assert_called_once()

    def test_refresh_api_keys_exception_handling(self) -> None:
        """Test exception handling during API key refresh."""
        panel = APIKeyPanel()

        # Mock the app to raise an exception
        mock_app = MagicMock()
        mock_app.tcp_server = MagicMock()
        mock_app.tcp_server.connection_manager = MagicMock()
        mock_app.tcp_server.connection_manager.api_keys = {}

        # Use patch to set the app attribute
        with patch.object(panel, 'app', mock_app):
            # Mock the _update_table method to raise an exception
            with patch.object(panel, '_update_table', side_effect=Exception("Test error")):
                # Mock the notify method
                with patch.object(panel, 'notify') as mock_notify:
                    panel.refresh_api_keys()

                    # Should show error notification
                    mock_notify.assert_called_once_with(
                        "Error refreshing API keys: Test error", severity="error"
                    )


class TestAPIKeySecurity:
    """Test security aspects of the TUI API key functionality."""

    def test_plaintext_key_cleared_on_confirm(self) -> None:
        """Test that plaintext key is cleared when confirming generation."""
        screen = APIKeyGenerationScreen()
        screen.generated_key = "dshield_test123456789"
        screen.key_config = {"key_id": "test_key_123"}

        # Mock the post_message and dismiss methods
        with patch.object(screen, 'post_message'), patch.object(screen, 'dismiss'):
            screen._confirm_key_generation()

            # Key should be cleared
            assert screen.generated_key is None

    def test_plaintext_key_cleared_on_dismiss(self) -> None:
        """Test that plaintext key is cleared when dismissing the screen."""
        screen = APIKeyGenerationScreen()
        screen.generated_key = "dshield_test123456789"

        # Call on_dismiss directly
        screen.on_dismiss()

        # Key should be cleared
        assert screen.generated_key is None

    def test_plaintext_key_not_logged(self) -> None:
        """Test that plaintext keys are not logged."""
        screen = APIKeyGenerationScreen()

        # Mock the logger
        with patch.object(screen, 'logger') as mock_logger:
            screen.generated_key = "dshield_test123456789"
            screen.key_config = {"key_id": "test_key_123"}

            # Mock the post_message and dismiss methods
            with patch.object(screen, 'post_message'), patch.object(screen, 'dismiss'):
                screen._confirm_key_generation()

                # Check that no log calls contain the plaintext key
                for call in mock_logger.method_calls:
                    if hasattr(call, 'args'):
                        for arg in call.args:
                            if isinstance(arg, str) and "dshield_test123456789" in arg:
                                pytest.fail("Plaintext key found in log call")

    def test_key_config_contains_hashed_data(self) -> None:
        """Test that key config contains hashed data, not plaintext."""
        screen = APIKeyGenerationScreen()

        # Mock the API key generator
        with patch('src.api_key_generator.APIKeyGenerator') as mock_generator_class:
            mock_generator = MagicMock()
            mock_generator_class.return_value = mock_generator

            # Mock the generate_api_key method
            mock_key_data = {
                "key_id": "test_key_123",
                "plaintext_key": "dshield_test123456789",
                "hashed_key": "a" * 64,  # Mock SHA-256 hash
                "salt": "b" * 32,  # Mock salt
                "algorithm": "sha256",
                "name": "Test Key",
                "permissions": {"read_tools": True},
                "expires_at": None,
                "rate_limit": 60,
                "metadata": {"generated_by": "dshield-mcp"},
                "created_at": "2024-01-01T00:00:00Z",
            }
            mock_generator.generate_api_key.return_value = mock_key_data

            # Mock the form inputs
            with patch.object(screen, 'query_one') as mock_query:

                def mock_query_side_effect(selector, widget_type):
                    if selector == "#key-name":
                        mock_input = MagicMock(spec=Input)
                        mock_input.value = "Test Key"
                        return mock_input
                    elif selector == "#perm-read":
                        mock_checkbox = MagicMock()
                        mock_checkbox.value = True
                        return mock_checkbox
                    elif selector == "#perm-write":
                        mock_checkbox = MagicMock()
                        mock_checkbox.value = False
                        return mock_checkbox
                    elif selector == "#perm-admin":
                        mock_checkbox = MagicMock()
                        mock_checkbox.value = False
                        return mock_checkbox
                    elif selector == "#rate-limit":
                        mock_input = MagicMock(spec=Input)
                        mock_input.value = "60"
                        return mock_input
                    elif selector == "#expiration":
                        mock_select = MagicMock()
                        mock_select.value = None
                        return mock_select
                    else:
                        return MagicMock()

                mock_query.side_effect = mock_query_side_effect

                # Mock the refresh method
                with patch.object(screen, 'refresh'):
                    screen._generate_api_key()

                # Verify the key config contains hashed data
                assert screen.key_config is not None
                assert screen.key_config["hashed_key"] == "a" * 64
                assert screen.key_config["salt"] == "b" * 32
                assert screen.key_config["algorithm"] == "sha256"

                # Verify plaintext is not in the config
                assert "plaintext_key" not in screen.key_config
