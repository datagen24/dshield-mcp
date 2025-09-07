#!/usr/bin/env python3
"""Tests for server panel lifecycle management.

This module tests the server panel's lifecycle management functionality,
including start/stop/restart buttons, status reflection, and timeout handling.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.tui.server_panel import ServerPanel
from src.tui.server_process_manager import ServerProcessManager, ServerStatusUpdate


class TestServerProcessManager:
    """Test cases for ServerProcessManager."""

    @pytest.fixture
    def mock_user_config(self) -> MagicMock:
        """Create a mock user configuration."""
        mock_config = MagicMock()
        mock_config.tui_settings.server_management = {
            "graceful_shutdown_timeout": 30,
            "auto_start_server": True,
        }
        mock_config.tcp_transport_settings.port = 3000
        mock_config.tcp_transport_settings.bind_address = "127.0.0.1"
        mock_config.tcp_transport_settings.max_connections = 10
        mock_config.tcp_transport_settings.connection_timeout_seconds = 30
        mock_config.tcp_transport_settings.api_key_management = {
            "enabled": True,
            "rate_limit_per_key": 60,
            "max_keys": 100,
        }
        mock_config.tcp_transport_settings.permissions = {}
        return mock_config

    @pytest.fixture
    def process_manager(self, mock_user_config: MagicMock) -> ServerProcessManager:
        """Create a ServerProcessManager instance with mocked dependencies."""
        with patch(
            "src.tui.server_process_manager.UserConfigManager",
            return_value=mock_user_config,
        ):
            with patch("src.tui_launcher.TUIProcessManager"):
                return ServerProcessManager("test_config.yaml")

    def test_init(self, process_manager: ServerProcessManager) -> None:
        """Test ServerProcessManager initialization."""
        assert process_manager.config_path == "test_config.yaml"
        assert process_manager.server_running is False
        assert process_manager.server_start_time is None
        assert process_manager.graceful_shutdown_timeout == 30
        assert len(process_manager._status_handlers) == 0

    def test_add_remove_status_handler(self, process_manager: ServerProcessManager) -> None:
        """Test adding and removing status handlers."""
        handler1 = MagicMock()
        handler2 = MagicMock()

        # Add handlers
        process_manager.add_status_handler(handler1)
        process_manager.add_status_handler(handler2)
        assert len(process_manager._status_handlers) == 2

        # Remove handler
        process_manager.remove_status_handler(handler1)
        assert len(process_manager._status_handlers) == 1
        assert handler2 in process_manager._status_handlers

    def test_emit_status_update(self, process_manager: ServerProcessManager) -> None:
        """Test status update emission."""
        handler1 = MagicMock()
        handler2 = MagicMock()
        process_manager.add_status_handler(handler1)
        process_manager.add_status_handler(handler2)

        status = {"running": True, "uptime_seconds": 100}
        process_manager._emit_status_update(status)

        # Verify handlers were called with ServerStatusUpdate message
        handler1.assert_called_once()
        handler2.assert_called_once()

        # Check the message type
        call1 = handler1.call_args[0][0]
        call2 = handler2.call_args[0][0]
        assert isinstance(call1, ServerStatusUpdate)
        assert isinstance(call2, ServerStatusUpdate)
        assert call1.status == status
        assert call2.status == status

    @pytest.mark.asyncio
    async def test_start_server_success(self, process_manager: ServerProcessManager) -> None:
        """Test successful server start."""
        # Mock the underlying process manager
        process_manager.process_manager.start_server = AsyncMock(return_value=True)

        # Add a status handler to verify emission
        status_handler = MagicMock()
        process_manager.add_status_handler(status_handler)

        result = await process_manager.start_server()

        assert result is True
        assert process_manager.server_running is True
        assert process_manager.server_start_time is not None
        assert isinstance(process_manager.server_start_time, datetime)

        # Verify status update was emitted
        status_handler.assert_called_once()
        call_args = status_handler.call_args[0][0]
        assert isinstance(call_args, ServerStatusUpdate)
        assert call_args.status["running"] is True

    @pytest.mark.asyncio
    async def test_start_server_failure(self, process_manager: ServerProcessManager) -> None:
        """Test server start failure."""
        # Mock the underlying process manager to return False
        process_manager.process_manager.start_server = AsyncMock(return_value=False)

        result = await process_manager.start_server()

        assert result is False
        assert process_manager.server_running is False
        assert process_manager.server_start_time is None

    @pytest.mark.asyncio
    async def test_stop_server_success(self, process_manager: ServerProcessManager) -> None:
        """Test successful server stop."""
        # Set up running state
        process_manager.server_running = True
        process_manager.server_start_time = datetime.now()

        # Mock the underlying process manager
        process_manager.process_manager.stop_server = AsyncMock(return_value=True)

        # Add a status handler to verify emission
        status_handler = MagicMock()
        process_manager.add_status_handler(status_handler)

        result = await process_manager.stop_server()

        assert result is True
        assert process_manager.server_running is False
        assert process_manager.server_start_time is None

        # Verify status update was emitted
        status_handler.assert_called_once()
        call_args = status_handler.call_args[0][0]
        assert isinstance(call_args, ServerStatusUpdate)
        assert call_args.status["running"] is False

    @pytest.mark.asyncio
    async def test_stop_server_not_running(self, process_manager: ServerProcessManager) -> None:
        """Test stopping server when not running."""
        # Mock the underlying process manager
        process_manager.process_manager.stop_server = AsyncMock(return_value=True)

        result = await process_manager.stop_server()

        assert result is True
        assert process_manager.server_running is False

    @pytest.mark.asyncio
    async def test_restart_server(self, process_manager: ServerProcessManager) -> None:
        """Test server restart."""
        # Set up running state
        process_manager.server_running = True
        process_manager.server_start_time = datetime.now()

        # Mock the underlying process manager
        process_manager.process_manager.stop_server = AsyncMock(return_value=True)
        process_manager.process_manager.start_server = AsyncMock(return_value=True)

        result = await process_manager.restart_server()

        assert result is True
        assert process_manager.server_running is True
        assert process_manager.server_start_time is not None

    def test_is_server_running(self, process_manager: ServerProcessManager) -> None:
        """Test server running status check."""
        # Test when not running
        process_manager.server_running = False
        process_manager.process_manager.is_server_running = MagicMock(return_value=False)
        assert process_manager.is_server_running() is False

        # Test when running
        process_manager.server_running = True
        process_manager.process_manager.is_server_running = MagicMock(return_value=True)
        assert process_manager.is_server_running() is True

    def test_get_server_status(self, process_manager: ServerProcessManager) -> None:
        """Test getting server status."""
        # Set up running state
        process_manager.server_running = True
        process_manager.server_start_time = datetime.now()
        process_manager.process_manager.server_process = MagicMock()
        process_manager.process_manager.server_process.pid = 12345

        status = process_manager.get_server_status()

        assert status["running"] is True
        assert status["uptime_seconds"] >= 0
        assert status["start_time"] is not None
        assert status["pid"] == 12345
        assert "configuration" in status
        assert "graceful_shutdown_timeout" in status

    def test_get_effective_configuration(self, process_manager: ServerProcessManager) -> None:
        """Test getting effective configuration."""
        config = process_manager.get_effective_configuration()

        assert config["port"] == 3000
        assert config["bind_address"] == "127.0.0.1"
        assert config["max_connections"] == 10
        assert config["connection_timeout_seconds"] == 30
        assert config["graceful_shutdown_timeout"] == 30
        assert "api_key_management" in config
        assert "permissions" in config
        assert "security" in config

    @pytest.mark.asyncio
    async def test_cleanup(self, process_manager: ServerProcessManager) -> None:
        """Test cleanup functionality."""
        # Set up running state
        process_manager.server_running = True
        process_manager.stop_server = AsyncMock(return_value=True)

        await process_manager.cleanup()

        process_manager.stop_server.assert_called_once()


class TestServerPanel:
    """Test cases for ServerPanel lifecycle management."""

    def test_init(self) -> None:
        """Test ServerPanel initialization."""
        with patch("src.tui.server_panel.ServerProcessManager"):
            panel = ServerPanel("test-panel", "test_config.yaml")
            assert panel.id == "test-panel"
            # Check that server_running is a reactive object
            assert hasattr(panel.server_running, '__class__')
            assert panel.server_status == {}
            assert panel.server_config == {}
            assert panel.uptime_start is None

    def test_get_server_health(self) -> None:
        """Test getting server health information."""
        with patch("src.tui.server_panel.ServerProcessManager"):
            panel = ServerPanel("test-panel", "test_config.yaml")

            # Set up state
            panel.server_running = True
            panel.uptime_start = datetime.now()
            panel.server_status = {"test": "status"}
            panel.process_manager.get_effective_configuration = MagicMock(
                return_value={"test": "config"}
            )

            health = panel.get_server_health()

            assert health["running"] is True
            assert health["uptime_seconds"] >= 0
            assert health["status"] == {"test": "status"}
            assert health["configuration"] == {"test": "config"}


class TestServerPanelIntegration:
    """Integration tests for server panel lifecycle management."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self) -> None:
        """Test complete server lifecycle with mocked subprocess."""
        with patch("src.tui_launcher.TUIProcessManager") as mock_tui_manager:
            # Set up mock process manager
            mock_tui_instance = MagicMock()
            mock_tui_instance.start_server = AsyncMock(return_value=True)
            mock_tui_instance.stop_server = AsyncMock(return_value=True)
            mock_tui_instance.is_server_running = MagicMock(return_value=True)
            mock_tui_instance.server_process = MagicMock()
            mock_tui_instance.server_process.pid = 12345
            mock_tui_manager.return_value = mock_tui_instance

            # Create process manager
            with patch("src.tui.server_process_manager.UserConfigManager"):
                process_manager = ServerProcessManager("test_config.yaml")

                # Test start
                result = await process_manager.start_server()
                assert result is True
                assert process_manager.server_running is True

                # Test status
                status = process_manager.get_server_status()
                assert status["running"] is True
                assert status["pid"] == 12345

                # Test stop
                result = await process_manager.stop_server()
                assert result is True
                assert process_manager.server_running is False

    @pytest.mark.asyncio
    async def test_timeout_handling(self) -> None:
        """Test timeout handling during server operations."""
        with patch("src.tui_launcher.TUIProcessManager") as mock_tui_manager:
            # Set up mock process manager with timeout
            mock_tui_instance = MagicMock()
            mock_tui_instance.start_server = AsyncMock(
                side_effect=TimeoutError("Operation timed out")
            )
            mock_tui_manager.return_value = mock_tui_instance

            # Create process manager
            with patch("src.tui.server_process_manager.UserConfigManager"):
                process_manager = ServerProcessManager("test_config.yaml")

                # Test timeout handling
                result = await process_manager.start_server()
                assert result is False
                assert process_manager.server_running is False

    def test_status_handler_error_handling(self) -> None:
        """Test error handling in status handlers."""
        with patch("src.tui_launcher.TUIProcessManager"):
            with patch("src.tui.server_process_manager.UserConfigManager"):
                process_manager = ServerProcessManager("test_config.yaml")

                # Add a handler that raises an exception
                error_handler = MagicMock(side_effect=Exception("Handler error"))
                error_handler.__name__ = "error_handler"  # Add __name__ attribute
                process_manager.add_status_handler(error_handler)

                # Add a normal handler
                normal_handler = MagicMock()
                normal_handler.__name__ = "normal_handler"  # Add __name__ attribute
                process_manager.add_status_handler(normal_handler)

                # Emit status update - should not raise exception
                process_manager._emit_status_update({"running": True})

                # Both handlers should have been called
                error_handler.assert_called_once()
                normal_handler.assert_called_once()
