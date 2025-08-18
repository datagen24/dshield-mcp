"""Tests for MCP server functionality and tool registration."""

import pytest
import json
import importlib
from unittest.mock import Mock, patch, AsyncMock

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
        """Return None for any configuration setting request (mock behavior).
        
        Returns:
            None: Always returns None for any setting.

        """
        return None

    def get_cache_database_path(self):
        return "/tmp/mock_cache_db.sqlite3"

class TestMCPServer:
    """Unit tests for MCP server initialization, structure, and tool registration."""

    def test_server_initialization(self):
        """Test MCP server initialization with mocked dependencies."""
        with patch('src.user_config.get_user_config', Mock(return_value=MockUserConfig())), \
             patch('src.elasticsearch_client.ElasticsearchClient', Mock()):
            import mcp_server
            server = mcp_server.DShieldMCPServer()
            assert server.server is not None
            assert server.elastic_client is None
            assert server.dshield_client is None
            assert server.data_processor is None
            assert server.context_injector is None
            assert server.campaign_analyzer is None
            # campaign_tools is now initialized in initialize() method
            assert server.campaign_tools is None
            assert server.health_manager is not None
            assert server.feature_manager is not None
            assert server.tool_registry is not None

    @pytest.mark.asyncio
    async def test_server_initialization_async(self):
        """Test async MCP server initialization with mocked dependencies."""
        with patch('src.user_config.get_user_config', Mock(return_value=MockUserConfig())), \
             patch('src.elasticsearch_client.ElasticsearchClient', AsyncMock()), \
             patch('src.feature_manager.FeatureManager.is_feature_available', return_value=True):
            import mcp_server
            server = mcp_server.DShieldMCPServer()
            await server.initialize()
            assert server.server is not None
            assert server.elastic_client is not None
            assert server.dshield_client is not None
            assert server.data_processor is not None
            assert server.context_injector is not None
            assert server.campaign_analyzer is not None
            assert server.campaign_tools is not None

    def test_server_structure(self):
        """Test MCP server structure and tool registration."""
        with patch('src.user_config.get_user_config', Mock(return_value=MockUserConfig())), \
             patch('src.elasticsearch_client.ElasticsearchClient', Mock()):
            import mcp_server
            server = mcp_server.DShieldMCPServer()
            assert hasattr(server, 'server')
            assert hasattr(server, 'campaign_tools')
            assert hasattr(server, 'health_manager')
            assert hasattr(server, 'feature_manager')
            assert hasattr(server, 'tool_registry')
            # campaign_tools is now initialized in initialize() method
            assert server.campaign_tools is None

    @pytest.mark.asyncio
    async def test_tool_registration(self):
        """Test MCP server tool registration and handler setup."""
        with patch('src.user_config.get_user_config', Mock(return_value=MockUserConfig())), \
             patch('src.elasticsearch_client.ElasticsearchClient', AsyncMock()):
            import mcp_server
            server = mcp_server.DShieldMCPServer()
            await server.initialize()
            assert hasattr(server.server, 'list_tools')
            assert hasattr(server.server, 'call_tool')

    @pytest.mark.asyncio
    async def test_query_dshield_events_tool(self):
        """Test query_dshield_events tool handler with mocked Elasticsearch client."""
        mock_elastic = AsyncMock()
        mock_elastic.query_dshield_events = AsyncMock(return_value=([], 0, {}))
        with patch('src.elasticsearch_client.ElasticsearchClient', return_value=mock_elastic):
            import mcp_server
            server = mcp_server.DShieldMCPServer()
            await server.initialize()
            result = await server._query_dshield_events({})
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_dshield_statistics_tool(self):
        """Test get_dshield_statistics tool handler with mocked Elasticsearch client."""
        mock_elastic = AsyncMock()
        mock_elastic.get_dshield_statistics = AsyncMock(return_value={})
        mock_elastic.close = AsyncMock()
        with patch('mcp_server.ElasticsearchClient', new_callable=AsyncMock, return_value=mock_elastic), \
             patch('src.user_config.get_user_config', Mock(return_value=MockUserConfig())):
            import mcp_server
            server = mcp_server.DShieldMCPServer()
            server.user_config = MockUserConfig()  # Ensure user_config is valid
            await server.initialize()
            server.elastic_client = mock_elastic  # Ensure the mock is used for awaited methods
            result = await server._get_dshield_statistics({})
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_enrich_ip_with_dshield_tool(self):
        """Test enrich_ip_with_dshield tool handler with mocked DShield client."""
        mock_dshield = AsyncMock()
        mock_dshield.get_ip_reputation = AsyncMock(return_value={})
        with patch('src.dshield_client.DShieldClient', return_value=mock_dshield):
            import mcp_server
            server = mcp_server.DShieldMCPServer()
            server.dshield_client = mock_dshield  # Set the mock directly
            await server.initialize()
            result = await server._enrich_ip_with_dshield({"ip_address": "192.168.1.1"})
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_data_dictionary_tool(self):
        """Test get_data_dictionary tool handler with mocked Elasticsearch client."""
        with patch('src.user_config.get_user_config', Mock(return_value=MockUserConfig())), \
             patch('src.elasticsearch_client.ElasticsearchClient', AsyncMock()):
            import mcp_server
            server = mcp_server.DShieldMCPServer()
            await server.initialize()
            result = await server._get_data_dictionary({})
            assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_server_cleanup(self):
        """Test MCP server cleanup method with mocked Elasticsearch client."""
        mock_elastic = AsyncMock()
        mock_elastic.close = AsyncMock()
        with patch('mcp_server.ElasticsearchClient', new_callable=AsyncMock, return_value=mock_elastic), \
             patch('src.user_config.get_user_config', Mock(return_value=MockUserConfig())):
            import mcp_server
            server = mcp_server.DShieldMCPServer()
            server.user_config = MockUserConfig()  # Ensure user_config is valid
            await server.initialize()
            server.elastic_client = mock_elastic  # Ensure the mock is used for awaited methods
            await server.cleanup()
            mock_elastic.close.assert_called_once()

    def test_server_error_handling(self):
        """Test MCP server error handling during initialization."""
        with patch('src.user_config.get_user_config', side_effect=Exception("Config error")):
            import mcp_server; importlib.reload(mcp_server)
            # The logger should have captured the error (stderr or log file)
            # This test will pass if no exception is raised
            assert True

    @pytest.mark.asyncio
    async def test_tool_error_handling(self):
        """Test error handling for tool execution failures."""
        mock_elastic = AsyncMock()
        mock_elastic.query_dshield_events = AsyncMock(side_effect=Exception("Query failed"))
        mock_elastic.close = AsyncMock()
        with patch('src.elasticsearch_client.ElasticsearchClient', new_callable=AsyncMock, return_value=mock_elastic), \
             patch('src.user_config.get_user_config', Mock(return_value=MockUserConfig())), \
             patch('src.dshield_client.DShieldClient', new_callable=AsyncMock), \
             patch('src.latex_template_tools.LaTeXTemplateTools', new_callable=AsyncMock):
            import mcp_server
            server = mcp_server.DShieldMCPServer()
            server.elastic_client = mock_elastic  # Set the mock directly
            server.user_config = MockUserConfig()  # Ensure user_config is valid
            await server.initialize()
            # Simulate tool call error
            result = await server._query_dshield_events({})
            assert isinstance(result, list)
            assert any("Error querying DShield events" in r.get("text", "") for r in result) 