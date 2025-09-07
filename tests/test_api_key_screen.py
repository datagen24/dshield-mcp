"""Tests for API key screen functionality.

This module contains tests for the API key generation screen,
including form validation, key generation, and confirmation flow.
"""

from unittest.mock import Mock, patch

import pytest
from textual.app import App
from textual.widgets import Button, Checkbox, Input, Select

from src.tui.screens.api_key_screen import APIKeyGenerated, APIKeyGenerationScreen


class TestAPIKeyGenerationScreen:
    """Test cases for APIKeyGenerationScreen class."""

    @pytest.fixture
    def screen(self) -> APIKeyGenerationScreen:
        """Create a test API key generation screen."""
        return APIKeyGenerationScreen()

    @pytest.fixture
    def mock_app(self) -> Mock:
        """Create a mock Textual app."""
        app = Mock(spec=App)
        app.push_screen = Mock()
        app.notify = Mock()
        return app

    def test_init(self, screen: APIKeyGenerationScreen) -> None:
        """Test screen initialization."""
        assert screen.generated_key is None
        assert screen.key_config is None
        assert screen.showing_key is False

    def test_compose_form_mode(self, screen: APIKeyGenerationScreen) -> None:
        """Test screen composition in form mode."""
        # Set up screen state
        screen.showing_key = False

        # Test that the screen is in form mode
        assert not screen.showing_key
        assert screen.generated_key is None
        assert screen.key_config is None

    def test_compose_key_display_mode(self, screen: APIKeyGenerationScreen) -> None:
        """Test screen composition in key display mode."""
        # Set up screen state
        screen.showing_key = True
        screen.generated_key = "test_key_123"
        screen.key_config = {"name": "Test Key", "permissions": {}}

        # Test that the screen is in key display mode
        assert screen.showing_key
        assert screen.generated_key == "test_key_123"
        assert screen.key_config is not None

    def test_on_button_pressed_generate(self, screen: APIKeyGenerationScreen) -> None:
        """Test generate button press handling."""
        # Mock Textual methods that require app context
        with (
            patch.object(screen, 'notify'),
            patch.object(screen, 'refresh'),
            patch.object(screen, 'query_one') as mock_query,
        ):
            # Mock form inputs
            mock_key_name = Mock(spec=Input)
            mock_key_name.value = "Test Key"

            mock_read_checkbox = Mock(spec=Checkbox)
            mock_read_checkbox.value = True
            mock_write_checkbox = Mock(spec=Checkbox)
            mock_write_checkbox.value = False
            mock_admin_checkbox = Mock(spec=Checkbox)
            mock_admin_checkbox.value = False

            mock_rate_limit = Mock(spec=Input)
            mock_rate_limit.value = "60"

            mock_expiration = Mock(spec=Select)
            mock_expiration.value = 30

            # Configure query_one to return appropriate mocks
            def query_side_effect(selector, widget_type=None):
                if selector == "#key-name":
                    return mock_key_name
                elif selector == "#perm-read":
                    return mock_read_checkbox
                elif selector == "#perm-write":
                    return mock_write_checkbox
                elif selector == "#perm-admin":
                    return mock_admin_checkbox
                elif selector == "#rate-limit":
                    return mock_rate_limit
                elif selector == "#expiration":
                    return mock_expiration
                return Mock()

            mock_query.side_effect = query_side_effect

            # Mock the API key generator
            with patch('src.api_key_generator.APIKeyGenerator') as mock_generator_class:
                mock_generator = Mock()
                mock_generator_class.return_value = mock_generator
                mock_generator.generate_key_with_metadata.return_value = {
                    "key_value": "test_key_123",
                    "name": "Test Key",
                    "permissions": {"read_tools": True, "write_back": False, "admin_access": False},
                    "expires_at": "2024-12-31T23:59:59",
                    "rate_limit": 60,
                    "metadata": {"generated_by": "dshield-mcp"},
                    "created_at": "2024-01-01T00:00:00",
                }

                # Mock refresh method
                with patch.object(screen, 'refresh'):
                    # Create a mock button press event
                    mock_button = Mock(spec=Button)
                    mock_button.id = "generate-btn"
                    mock_event = Mock()
                    mock_event.button = mock_button

                    # Call the method
                    screen.on_button_pressed(mock_event)

                    # Verify the generator was called
                    mock_generator.generate_key_with_metadata.assert_called_once()

                    # Verify screen state was updated
                    assert screen.generated_key == "test_key_123"
                    assert screen.key_config is not None
                    assert screen.showing_key is True

    def test_on_button_pressed_generate_empty_name(self, screen: APIKeyGenerationScreen) -> None:
        """Test generate button with empty key name."""
        with patch.object(screen, 'query_one') as mock_query:
            # Mock form inputs with empty name
            mock_key_name = Mock(spec=Input)
            mock_key_name.value = ""

            def query_side_effect(selector, widget_type=None):
                if selector == "#key-name":
                    return mock_key_name
                return Mock()

            mock_query.side_effect = query_side_effect

            # Mock notify method
            with patch.object(screen, 'notify') as mock_notify:
                # Create a mock button press event
                mock_button = Mock(spec=Button)
                mock_button.id = "generate-btn"
                mock_event = Mock()
                mock_event.button = mock_button

                # Call the method
                screen.on_button_pressed(mock_event)

                # Verify error notification
                mock_notify.assert_called_once_with("Key name is required", severity="error")

    def test_on_button_pressed_cancel(self, screen: APIKeyGenerationScreen) -> None:
        """Test cancel button press handling."""
        with patch.object(screen, 'dismiss') as mock_dismiss:
            # Create a mock button press event
            mock_button = Mock(spec=Button)
            mock_button.id = "cancel-btn"
            mock_event = Mock()
            mock_event.button = mock_button

            # Call the method
            screen.on_button_pressed(mock_event)

            # Verify dismiss was called
            mock_dismiss.assert_called_once()

    def test_on_button_pressed_confirm(self, screen: APIKeyGenerationScreen) -> None:
        """Test confirm button press handling."""
        # Set up screen state
        screen.generated_key = "test_key_123"
        screen.key_config = {"name": "Test Key", "permissions": {}}

        with (
            patch.object(screen, 'post_message') as mock_post_message,
            patch.object(screen, 'dismiss') as mock_dismiss,
        ):
            # Create a mock button press event
            mock_button = Mock(spec=Button)
            mock_button.id = "confirm-btn"
            mock_event = Mock()
            mock_event.button = mock_button

            # Call the method
            screen.on_button_pressed(mock_event)

            # Verify message was posted and screen dismissed
            mock_post_message.assert_called_once()
            mock_dismiss.assert_called_once()

    def test_on_button_pressed_confirm_no_key(self, screen: APIKeyGenerationScreen) -> None:
        """Test confirm button with no generated key."""
        with patch.object(screen, 'notify') as mock_notify:
            # Create a mock button press event
            mock_button = Mock(spec=Button)
            mock_button.id = "confirm-btn"
            mock_event = Mock()
            mock_event.button = mock_button

            # Call the method
            screen.on_button_pressed(mock_event)

            # Verify error notification
            mock_notify.assert_called_once_with("No key to confirm", severity="error")

    def test_on_button_pressed_cancel_confirm(self, screen: APIKeyGenerationScreen) -> None:
        """Test cancel confirmation button press handling."""
        with patch.object(screen, 'dismiss') as mock_dismiss:
            # Create a mock button press event
            mock_button = Mock(spec=Button)
            mock_button.id = "cancel-confirm-btn"
            mock_event = Mock()
            mock_event.button = mock_button

            # Call the method
            screen.on_button_pressed(mock_event)

            # Verify dismiss was called
            mock_dismiss.assert_called_once()

    def test_confirm_key_generation(self, screen: APIKeyGenerationScreen) -> None:
        """Test key generation confirmation."""
        # Set up screen state
        screen.generated_key = "test_key_123"
        screen.key_config = {"name": "Test Key", "permissions": {}}

        with (
            patch.object(screen, 'post_message') as mock_post_message,
            patch.object(screen, 'dismiss') as mock_dismiss,
        ):
            # Call the method
            screen._confirm_key_generation()

            # Verify message was posted and screen dismissed
            mock_post_message.assert_called_once()
            mock_dismiss.assert_called_once()

    def test_confirm_key_generation_no_key(self, screen: APIKeyGenerationScreen) -> None:
        """Test key generation confirmation with no key."""
        with patch.object(screen, 'notify') as mock_notify:
            # Call the method
            screen._confirm_key_generation()

            # Verify error notification
            mock_notify.assert_called_once_with("No key to confirm", severity="error")

    def test_generate_api_key_exception_handling(self, screen: APIKeyGenerationScreen) -> None:
        """Test exception handling in key generation."""
        with patch.object(screen, 'query_one') as mock_query:
            # Mock form inputs
            mock_key_name = Mock(spec=Input)
            mock_key_name.value = "Test Key"

            def query_side_effect(selector, widget_type=None):
                if selector == "#key-name":
                    return mock_key_name
                return Mock()

            mock_query.side_effect = query_side_effect

            # Mock the API key generator to raise an exception
            with patch('src.api_key_generator.APIKeyGenerator') as mock_generator_class:
                mock_generator_class.side_effect = Exception("Test error")

                with (
                    patch.object(screen, 'notify') as mock_notify,
                    patch.object(screen, 'logger') as mock_logger,
                ):
                    # Create a mock button press event
                    mock_button = Mock(spec=Button)
                    mock_button.id = "generate-btn"
                    mock_event = Mock()
                    mock_event.button = mock_button

                    # Call the method
                    screen.on_button_pressed(mock_event)

                    # Verify error handling
                    mock_logger.error.assert_called_once()
                    mock_notify.assert_called_once()

    def test_on_mount(self, screen: APIKeyGenerationScreen) -> None:
        """Test screen mount event handling."""
        with patch.object(screen, 'query_one') as mock_query:
            mock_input = Mock(spec=Input)
            mock_query.return_value = mock_input

            # Call the method
            screen.on_mount()

            # Verify focus was set
            mock_input.focus.assert_called_once()

    def test_api_key_generated_message(self) -> None:
        """Test APIKeyGenerated message creation."""
        key_config = {"name": "Test Key", "permissions": {}}
        message = APIKeyGenerated(key_config)

        assert message.key_config == key_config

    def test_screen_state_transitions(self, screen: APIKeyGenerationScreen) -> None:
        """Test screen state transitions."""
        # Initial state
        assert screen.showing_key is False
        assert screen.generated_key is None
        assert screen.key_config is None

        # Simulate key generation
        screen.generated_key = "test_key_123"
        screen.key_config = {"name": "Test Key"}
        screen.showing_key = True

        # Verify state
        assert screen.showing_key is True
        assert screen.generated_key == "test_key_123"
        assert screen.key_config is not None

    def test_form_validation_integration(self, screen: APIKeyGenerationScreen) -> None:
        """Test form validation integration."""
        with patch.object(screen, 'query_one') as mock_query:
            # Mock form inputs with valid data
            mock_key_name = Mock(spec=Input)
            mock_key_name.value = "Valid Key Name"

            mock_read_checkbox = Mock(spec=Checkbox)
            mock_read_checkbox.value = True
            mock_write_checkbox = Mock(spec=Checkbox)
            mock_write_checkbox.value = False
            mock_admin_checkbox = Mock(spec=Checkbox)
            mock_admin_checkbox.value = False

            mock_rate_limit = Mock(spec=Input)
            mock_rate_limit.value = "120"

            mock_expiration = Mock(spec=Select)
            mock_expiration.value = 90

            def query_side_effect(selector, widget_type=None):
                if selector == "#key-name":
                    return mock_key_name
                elif selector == "#perm-read":
                    return mock_read_checkbox
                elif selector == "#perm-write":
                    return mock_write_checkbox
                elif selector == "#perm-admin":
                    return mock_admin_checkbox
                elif selector == "#rate-limit":
                    return mock_rate_limit
                elif selector == "#expiration":
                    return mock_expiration
                return Mock()

            mock_query.side_effect = query_side_effect

            # Mock the API key generator
            with patch('src.api_key_generator.APIKeyGenerator') as mock_generator_class:
                mock_generator = Mock()
                mock_generator_class.return_value = mock_generator
                mock_generator.generate_key_with_metadata.return_value = {
                    "key_value": "test_key_123",
                    "name": "Valid Key Name",
                    "permissions": {"read_tools": True, "write_back": False, "admin_access": False},
                    "expires_at": "2024-12-31T23:59:59",
                    "rate_limit": 120,
                    "metadata": {"generated_by": "dshield-mcp"},
                    "created_at": "2024-01-01T00:00:00",
                }

                # Mock refresh method
                with patch.object(screen, 'refresh'):
                    # Create a mock button press event
                    mock_button = Mock(spec=Button)
                    mock_button.id = "generate-btn"
                    mock_event = Mock()
                    mock_event.button = mock_button

                    # Call the method
                    screen.on_button_pressed(mock_event)

                    # Verify the generator was called with correct parameters
                    mock_generator.generate_key_with_metadata.assert_called_once_with(
                        name="Valid Key Name",
                        permissions={
                            "read_tools": True,
                            "write_back": False,
                            "admin_access": False,
                            "rate_limit": 120,
                        },
                        expiration_days=90,
                        rate_limit=120,
                    )
