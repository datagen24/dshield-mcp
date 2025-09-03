#!/usr/bin/env python3
"""Test TCP server integration with TUI application.

This module tests the integration between the TUI application and the TCP server,
ensuring that the server can be started, stopped, and processes messages correctly.
"""

import asyncio
from unittest.mock import Mock, patch

import pytest
import structlog

from src.tui.tui_app import DShieldTUIApp, _get_dshield_mcp_server
from src.tcp_server import EnhancedTCPServer


class TestTCPTUIIntegration:
    """Test TCP server integration with TUI application."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.logger = structlog.get_logger(__name__)

        # Mock the user config to avoid file system dependencies
        self.mock_config = Mock()
        self.mock_config.tcp_transport_settings.port = 3001
        self.mock_config.tcp_transport_settings.bind_address = "127.0.0.1"
        self.mock_config.tcp_transport_settings.max_connections = 5
        self.mock_config.tcp_transport_settings.connection_timeout_seconds = 300
        self.mock_config.tcp_transport_settings.api_key_management = {"rate_limit_per_key": 60}
        self.mock_config.tcp_transport_settings.permissions = {}
        self.mock_config.tui_settings.server_management = {"auto_start_server": False}
        self.mock_config.tui_settings.refresh_interval_ms = 1000

    def test_get_dshield_mcp_server_import(self) -> None:
        """Test that DShieldMCPServer can be imported without circular dependencies."""
        try:
            DShieldMCPServer = _get_dshield_mcp_server()
            assert DShieldMCPServer is not None
            self.logger.info("Successfully imported DShieldMCPServer")
        except Exception as e:
            pytest.fail(f"Failed to import DShieldMCPServer: {e}")

    def test_create_mcp_server_instance(self) -> None:
        """Test that DShieldMCPServer instance can be created."""
        try:
            DShieldMCPServer = _get_dshield_mcp_server()
            mcp_server = DShieldMCPServer()
            assert mcp_server is not None
            self.logger.info("Successfully created DShieldMCPServer instance")
        except Exception as e:
            pytest.fail(f"Failed to create DShieldMCPServer instance: {e}")

    @patch('src.tui.tui_app.UserConfigManager')
    def test_tui_app_initialization(self, mock_config_manager: Mock) -> None:
        """Test that TUI app can be initialized with TCP server components."""
        mock_config_manager.return_value = self.mock_config

        try:
            app = DShieldTUIApp()
            assert app.tcp_server is None
            assert app.server_thread is None
            # Check that server_running is a reactive attribute (we can't easily test its value)
            assert hasattr(app, 'server_running')
            self.logger.info("Successfully initialized TUI app")
        except Exception as e:
            pytest.fail(f"Failed to initialize TUI app: {e}")

    @patch('src.tui.tui_app.UserConfigManager')
    def test_create_mcp_server_method(self, mock_config_manager: Mock) -> None:
        """Test the _create_mcp_server method."""
        mock_config_manager.return_value = self.mock_config

        app = DShieldTUIApp()

        try:
            mcp_server = app._create_mcp_server()
            assert mcp_server is not None
            self.logger.info("Successfully created MCP server via TUI app method")
        except Exception as e:
            pytest.fail(f"Failed to create MCP server via TUI app method: {e}")

    @patch('src.tui.tui_app.UserConfigManager')
    @pytest.mark.asyncio
    async def test_enhanced_tcp_server_creation(self, mock_config_manager: Mock) -> None:
        """Test that EnhancedTCPServer can be created with MCP server."""
        mock_config_manager.return_value = self.mock_config

        app = DShieldTUIApp()
        mcp_server = app._create_mcp_server()

        tcp_config = {
            "port": 3002,
            "bind_address": "127.0.0.1",
            "max_connections": 5,
            "connection_timeout_seconds": 300,
            "connection_management": {
                "api_key_management": {"rate_limit_per_key": 60},
                "permissions": {},
            },
            "security": {
                "global_rate_limit": 1000,
                "global_burst_limit": 100,
                "client_rate_limit": 60,
                "client_burst_limit": 10,
                "abuse_threshold": 10,
                "block_duration_seconds": 3600,
                "max_connection_attempts": 5,
                "connection_window_seconds": 300,
                "input_validation": {
                    "max_message_size": 1048576,
                    "max_field_length": 10000,
                    "allowed_methods": [
                        "initialize",
                        "initialized",
                        "tools/list",
                        "tools/call",
                        "resources/list",
                        "resources/read",
                        "prompts/list",
                        "prompts/get",
                        "authenticate",
                    ],
                },
            },
            "authentication": {"session_timeout_seconds": 3600, "max_sessions_per_key": 5},
        }

        try:
            tcp_server = EnhancedTCPServer(mcp_server, tcp_config)
            assert tcp_server is not None
            assert tcp_server.mcp_server == mcp_server
            self.logger.info("Successfully created EnhancedTCPServer with MCP server")
        except Exception as e:
            pytest.fail(f"Failed to create EnhancedTCPServer: {e}")

    @pytest.mark.asyncio
    async def test_tcp_server_start_stop_cycle(self) -> None:
        """Test that TCP server can be started and stopped."""
        # Create a simple mock MCP server
        mock_mcp_server = Mock()
        mock_mcp_server.get_capabilities.return_value = {"tools": True}
        mock_mcp_server.get_available_tools.return_value = []
        mock_mcp_server.get_available_resources.return_value = []
        mock_mcp_server.get_available_prompts.return_value = []

        tcp_config = {
            "port": 3003,
            "bind_address": "127.0.0.1",
            "max_connections": 5,
            "connection_timeout_seconds": 300,
            "connection_management": {
                "api_key_management": {"rate_limit_per_key": 60},
                "permissions": {},
            },
            "security": {
                "global_rate_limit": 1000,
                "global_burst_limit": 100,
                "client_rate_limit": 60,
                "client_burst_limit": 10,
                "abuse_threshold": 10,
                "block_duration_seconds": 3600,
                "max_connection_attempts": 5,
                "connection_window_seconds": 300,
                "input_validation": {
                    "max_message_size": 1048576,
                    "max_field_length": 10000,
                    "allowed_methods": [
                        "initialize",
                        "initialized",
                        "tools/list",
                        "tools/call",
                        "resources/list",
                        "resources/read",
                        "prompts/list",
                        "prompts/get",
                        "authenticate",
                    ],
                },
            },
            "authentication": {"session_timeout_seconds": 3600, "max_sessions_per_key": 5},
        }

        tcp_server = EnhancedTCPServer(mock_mcp_server, tcp_config)

        try:
            # Start the server
            await tcp_server.start()
            assert tcp_server.is_running is True
            self.logger.info("TCP server started successfully")

            # Give it a moment to fully start
            await asyncio.sleep(0.1)

            # Stop the server
            await tcp_server.stop()
            assert tcp_server.is_running is False
            self.logger.info("TCP server stopped successfully")

        except Exception as e:
            pytest.fail(f"Server lifecycle test failed: {e}")

    @pytest.mark.asyncio
    async def test_tcp_server_message_processing(self) -> None:
        """Test that TCP server can process MCP messages."""
        # Create a mock MCP server with proper methods
        mock_mcp_server = Mock()
        mock_mcp_server.get_capabilities.return_value = {
            "tools": True,
            "resources": True,
            "prompts": True,
        }
        mock_mcp_server.get_available_tools.return_value = [
            {
                "name": "test_tool",
                "description": "A test tool",
                "inputSchema": {"type": "object", "properties": {"message": {"type": "string"}}},
            }
        ]
        mock_mcp_server.get_available_resources.return_value = [
            {"uri": "test://resource", "name": "Test Resource", "description": "A test resource"}
        ]
        mock_mcp_server.get_available_prompts.return_value = [
            {"name": "test_prompt", "description": "A test prompt"}
        ]

        tcp_config = {
            "port": 3004,
            "bind_address": "127.0.0.1",
            "max_connections": 5,
            "connection_timeout_seconds": 300,
            "connection_management": {
                "api_key_management": {"rate_limit_per_key": 60},
                "permissions": {},
            },
            "security": {
                "global_rate_limit": 1000,
                "global_burst_limit": 100,
                "client_rate_limit": 60,
                "client_burst_limit": 10,
                "abuse_threshold": 10,
                "block_duration_seconds": 3600,
                "max_connection_attempts": 5,
                "connection_window_seconds": 300,
                "input_validation": {
                    "max_message_size": 1048576,
                    "max_field_length": 10000,
                    "allowed_methods": [
                        "initialize",
                        "initialized",
                        "tools/list",
                        "tools/call",
                        "resources/list",
                        "resources/read",
                        "prompts/list",
                        "prompts/get",
                        "authenticate",
                    ],
                },
            },
            "authentication": {"session_timeout_seconds": 3600, "max_sessions_per_key": 5},
        }

        tcp_server = EnhancedTCPServer(mock_mcp_server, tcp_config)

        try:
            # Start the server
            await tcp_server.start()
            assert tcp_server.is_running is True

            # Test the MCP adapter directly
            adapter = tcp_server.mcp_adapter

            # Create a mock connection
            mock_connection = Mock()
            mock_connection.is_authenticated = True
            mock_connection.is_initialized = True
            mock_connection.client_address = ("127.0.0.1", 12345)

            # Test initialize message
            init_message = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "1.0.0"},
                },
            }

            response = await adapter.process_mcp_message(mock_connection, init_message)
            assert response is not None
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 1
            assert "result" in response
            assert "capabilities" in response["result"]

            # Test tools/list message
            tools_message = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}

            response = await adapter.process_mcp_message(mock_connection, tools_message)
            assert response is not None
            assert response["jsonrpc"] == "2.0"
            assert response["id"] == 2
            assert "result" in response
            assert "tools" in response["result"]

            self.logger.info("Message processing test completed successfully")

            # Stop the server
            await tcp_server.stop()
            assert tcp_server.is_running is False

        except Exception as e:
            pytest.fail(f"Message processing test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
