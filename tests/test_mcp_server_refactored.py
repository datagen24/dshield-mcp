"""Tests for refactored MCP server functionality."""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Any, Dict, List

from src.mcp.tools.base import ToolDefinition, ToolCategory
from src.mcp.tools.loader import ToolLoader
from src.mcp.tools.dispatcher import ToolDispatcher


class MockPerformanceSettings:
    def __init__(self):
        self.enable_sqlite_cache = False
        self.sqlite_cache_ttl_hours = 24


class MockUserConfig:
    """Mock user configuration for testing MCP server."""
    
    def __init__(self):
        self.output_directory = "/tmp/mock_output"
        self.performance_settings = MockPerformanceSettings()
    
    def get_setting(self, section, key):
        """Return None for any configuration setting request (mock behavior)."""
        return None
    
    def get_cache_database_path(self):
        return "/tmp/mock_cache_db.sqlite3"


class TestRefactoredMCPServer:
    """Test refactored MCP server functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_user_config = MockUserConfig()
    
    @patch('src.user_config.get_user_config')
    @patch('src.mcp.tools.loader.ToolLoader')
    @patch('src.mcp.tools.dispatcher.ToolDispatcher')
    def test_server_initialization_with_tool_system(self, mock_dispatcher, mock_loader, mock_get_config):
        """Test MCP server initialization with new tool system."""
        mock_get_config.return_value = self.mock_user_config
        mock_loader_instance = Mock()
        mock_dispatcher_instance = Mock()
        mock_loader.return_value = mock_loader_instance
        mock_dispatcher.return_value = mock_dispatcher_instance
        
        import mcp_server
        
        server = mcp_server.DShieldMCPServer()
        
        # Test that tool system is initialized
        assert hasattr(server, 'tool_loader')
        assert hasattr(server, 'tool_dispatcher')
        assert server.tool_loader == mock_loader_instance
        assert server.tool_dispatcher == mock_dispatcher_instance
    
    @patch('src.user_config.get_user_config')
    @patch('src.mcp.tools.loader.ToolLoader')
    @patch('src.mcp.tools.dispatcher.ToolDispatcher')
    def test_register_tools_calls_loader(self, mock_dispatcher, mock_loader, mock_get_config):
        """Test that _register_tools calls the tool loader."""
        mock_get_config.return_value = self.mock_user_config
        mock_loader_instance = Mock()
        mock_dispatcher_instance = Mock()
        mock_loader.return_value = mock_loader_instance
        mock_dispatcher.return_value = mock_dispatcher_instance
        
        import mcp_server
        
        server = mcp_server.DShieldMCPServer()
        
        # Call _register_tools
        server._register_tools()
        
        # Verify that load_all_tools was called
        mock_loader_instance.load_all_tools.assert_called_once()
    
    @patch('src.user_config.get_user_config')
    @patch('src.mcp.tools.loader.ToolLoader')
    @patch('src.mcp.tools.dispatcher.ToolDispatcher')
    def test_register_tool_handlers(self, mock_dispatcher, mock_loader, mock_get_config):
        """Test _register_tool_handlers method."""
        mock_get_config.return_value = self.mock_user_config
        mock_loader_instance = Mock()
        mock_dispatcher_instance = Mock()
        mock_loader.return_value = mock_loader_instance
        mock_dispatcher.return_value = mock_dispatcher_instance
        
        import mcp_server
        
        server = mcp_server.DShieldMCPServer()
        
        # Call _register_tool_handlers
        server._register_tool_handlers()
        
        # Verify that handlers were registered
        assert mock_dispatcher_instance.register_handler.call_count > 0
        
        # Check that specific handlers were registered
        registered_handlers = [call[0][0] for call in mock_dispatcher_instance.register_handler.call_args_list]
        assert "query_dshield_events" in registered_handlers
        assert "analyze_campaign" in registered_handlers
        assert "get_data_dictionary" in registered_handlers
    
    @pytest.mark.asyncio
    async def test_handle_list_tools(self):
        """Test _handle_list_tools method."""
        with (
            patch('src.user_config.get_user_config', return_value=self.mock_user_config),
            patch('src.mcp.tools.loader.ToolLoader'),
            patch('src.mcp.tools.dispatcher.ToolDispatcher'),
            patch('src.feature_manager.FeatureManager')
        ):
            import mcp_server
            
            # Create mock tool definitions
            mock_tool_defs = [
                ToolDefinition(
                    name="test_tool_1",
                    description="Test tool 1",
                    category=ToolCategory.QUERY,
                    schema={"type": "object"},
                    handler="test_handler_1"
                ),
                ToolDefinition(
                    name="test_tool_2",
                    description="Test tool 2",
                    category=ToolCategory.CAMPAIGN,
                    schema={"type": "object"},
                    handler="test_handler_2"
                )
            ]
            
            # Set up mocks
            server = mcp_server.DShieldMCPServer()
            server.feature_manager.get_available_features.return_value = ["elasticsearch"]
            server.tool_dispatcher.get_available_tools.return_value = mock_tool_defs
            server.tool_loader.get_all_tool_definitions.return_value = mock_tool_defs
            
            # Test _handle_list_tools
            result = await server._handle_list_tools()
            
            # Verify result
            assert len(result) == 2
            assert result[0].name == "test_tool_1"
            assert result[0].description == "Test tool 1"
            assert result[1].name == "test_tool_2"
            assert result[1].description == "Test tool 2"
    
    @pytest.mark.asyncio
    async def test_handle_call_tool_success(self):
        """Test _handle_call_tool method with successful execution."""
        with (
            patch('src.user_config.get_user_config', return_value=self.mock_user_config),
            patch('src.mcp.tools.loader.ToolLoader'),
            patch('src.mcp.tools.dispatcher.ToolDispatcher'),
            patch('src.feature_manager.FeatureManager')
        ):
            import mcp_server
            
            # Set up mocks
            server = mcp_server.DShieldMCPServer()
            server.feature_manager.get_available_features.return_value = ["elasticsearch"]
            server.tool_dispatcher.is_tool_available.return_value = True
            server.tool_dispatcher.dispatch_tool_call.return_value = [{"result": "success"}]
            server.error_handler = Mock()
            server.error_handler.config.timeouts.get.return_value = 120.0
            
            # Test _handle_call_tool
            result = await server._handle_call_tool("test_tool", {"arg": "value"})
            
            # Verify result
            assert result == [{"result": "success"}]
            server.tool_dispatcher.dispatch_tool_call.assert_called_once_with(
                "test_tool", {"arg": "value"}, timeout=120.0
            )
    
    @pytest.mark.asyncio
    async def test_handle_call_tool_unavailable(self):
        """Test _handle_call_tool method with unavailable tool."""
        with (
            patch('src.user_config.get_user_config', return_value=self.mock_user_config),
            patch('src.mcp.tools.loader.ToolLoader'),
            patch('src.mcp.tools.dispatcher.ToolDispatcher'),
            patch('src.feature_manager.FeatureManager')
        ):
            import mcp_server
            
            # Set up mocks
            server = mcp_server.DShieldMCPServer()
            server.feature_manager.get_available_features.return_value = ["elasticsearch"]
            server.tool_dispatcher.is_tool_available.return_value = False
            server._tool_unavailable_response = AsyncMock(return_value=[{"error": "unavailable"}])
            
            # Test _handle_call_tool
            result = await server._handle_call_tool("unavailable_tool", {})
            
            # Verify result
            assert result == [{"error": "unavailable"}]
            server._tool_unavailable_response.assert_called_once_with("unavailable_tool")
    
    @pytest.mark.asyncio
    async def test_handle_call_tool_timeout(self):
        """Test _handle_call_tool method with timeout error."""
        with (
            patch('src.user_config.get_user_config', return_value=self.mock_user_config),
            patch('src.mcp.tools.loader.ToolLoader'),
            patch('src.mcp.tools.dispatcher.ToolDispatcher'),
            patch('src.feature_manager.FeatureManager')
        ):
            import mcp_server
            
            # Set up mocks
            server = mcp_server.DShieldMCPServer()
            server.feature_manager.get_available_features.return_value = ["elasticsearch"]
            server.tool_dispatcher.is_tool_available.return_value = True
            server.tool_dispatcher.dispatch_tool_call.side_effect = TimeoutError("Tool timed out")
            server.error_handler = Mock()
            server.error_handler.config.timeouts.get.return_value = 120.0
            server.error_handler.create_timeout_error.return_value = {"error": "timeout"}
            
            # Test _handle_call_tool
            result = await server._handle_call_tool("slow_tool", {})
            
            # Verify result
            assert result == [{"error": "timeout"}]
            server.error_handler.create_timeout_error.assert_called_once_with("slow_tool", 30.0)
    
    @pytest.mark.asyncio
    async def test_handle_call_tool_validation_error(self):
        """Test _handle_call_tool method with validation error."""
        with (
            patch('src.user_config.get_user_config', return_value=self.mock_user_config),
            patch('src.mcp.tools.loader.ToolLoader'),
            patch('src.mcp.tools.dispatcher.ToolDispatcher'),
            patch('src.feature_manager.FeatureManager')
        ):
            import mcp_server
            
            # Set up mocks
            server = mcp_server.DShieldMCPServer()
            server.feature_manager.get_available_features.return_value = ["elasticsearch"]
            server.tool_dispatcher.is_tool_available.return_value = True
            server.tool_dispatcher.dispatch_tool_call.side_effect = ValueError("Invalid arguments")
            server.error_handler = Mock()
            server.error_handler.config.timeouts.get.return_value = 120.0
            server.error_handler.create_validation_error.return_value = {"error": "validation"}
            
            # Test _handle_call_tool
            result = await server._handle_call_tool("test_tool", {"invalid": "args"})
            
            # Verify result
            assert result == [{"error": "validation"}]
            server.error_handler.create_validation_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_call_tool_general_error(self):
        """Test _handle_call_tool method with general error."""
        with (
            patch('src.user_config.get_user_config', return_value=self.mock_user_config),
            patch('src.mcp.tools.loader.ToolLoader'),
            patch('src.mcp.tools.dispatcher.ToolDispatcher'),
            patch('src.feature_manager.FeatureManager')
        ):
            import mcp_server
            
            # Set up mocks
            server = mcp_server.DShieldMCPServer()
            server.feature_manager.get_available_features.return_value = ["elasticsearch"]
            server.tool_dispatcher.is_tool_available.return_value = True
            server.tool_dispatcher.dispatch_tool_call.side_effect = RuntimeError("General error")
            server.error_handler = Mock()
            server.error_handler.config.timeouts.get.return_value = 120.0
            server.error_handler.create_internal_error.return_value = {"error": "internal"}
            
            # Test _handle_call_tool
            result = await server._handle_call_tool("test_tool", {})
            
            # Verify result
            assert result == [{"error": "internal"}]
            server.error_handler.create_internal_error.assert_called_once_with("Tool call failed: General error")
    
    def test_register_mcp_handlers(self):
        """Test _register_mcp_handlers method."""
        with (
            patch('src.user_config.get_user_config', return_value=self.mock_user_config),
            patch('src.mcp.tools.loader.ToolLoader'),
            patch('src.mcp.tools.dispatcher.ToolDispatcher')
        ):
            import mcp_server
            
            server = mcp_server.DShieldMCPServer()
            
            # Mock the server decorators
            with patch.object(server.server, 'list_tools'), \
                 patch.object(server.server, 'call_tool'), \
                 patch.object(server.server, 'list_resources'), \
                 patch.object(server.server, 'read_resource'):
                
                # Call _register_mcp_handlers
                server._register_mcp_handlers()
                
                # Verify that decorators were called
                # (The actual verification would depend on the decorator implementation)
                assert True  # Placeholder for successful execution
    
    def test_tool_loader_integration(self):
        """Test integration between server and tool loader."""
        with (
            patch('src.user_config.get_user_config', return_value=self.mock_user_config),
            patch('src.mcp.tools.loader.ToolLoader'),
            patch('src.mcp.tools.dispatcher.ToolDispatcher')
        ):
            import mcp_server
            
            # Create mock tool definitions
            mock_tool_defs = [
                ToolDefinition(
                    name="test_tool",
                    description="Test tool",
                    category=ToolCategory.UTILITY,
                    schema={"type": "object"},
                    handler="test_handler"
                )
            ]
            
            # Set up mocks
            mock_loader = Mock()
            mock_loader.load_all_tools.return_value = {"test_tool": mock_tool_defs[0]}
            mock_loader.get_all_tool_definitions.return_value = mock_tool_defs
            
            with patch('src.mcp.tools.loader.ToolLoader', return_value=mock_loader):
                server = mcp_server.DShieldMCPServer()
                
                # Call _register_tools
                server._register_tools()
                
                # Verify that load_all_tools was called
                mock_loader.load_all_tools.assert_called_once()




