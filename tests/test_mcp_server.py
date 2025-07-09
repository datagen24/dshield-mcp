"""
Tests for MCP server functionality and tool registration.
"""

import pytest
import json
import importlib
from unittest.mock import Mock, patch, AsyncMock

class MockUserConfig:
    def get_setting(self, *args, **kwargs):
        return None

class TestMCPServer:
    def test_server_initialization(self):
        with patch('src.user_config.get_user_config', Mock(return_value=MockUserConfig())), \
             patch('src.elasticsearch_client.ElasticsearchClient', Mock()), \
             patch('src.dshield_client.DShieldClient', Mock()), \
             patch('src.data_processor.DataProcessor', Mock()), \
             patch('src.context_injector.ContextInjector', Mock()), \
             patch('src.campaign_analyzer.CampaignAnalyzer', Mock()), \
             patch('src.campaign_mcp_tools.CampaignMCPTools', Mock()):
            import mcp_server; importlib.reload(mcp_server)
            from mcp_server import DShieldMCPServer
            server = DShieldMCPServer()
            assert hasattr(server, 'server')
            assert hasattr(server, 'user_config')
            assert hasattr(server, 'elastic_client')
            assert hasattr(server, 'dshield_client')
            assert hasattr(server, 'data_processor')
            assert hasattr(server, 'context_injector')
            assert hasattr(server, 'campaign_analyzer')
            assert hasattr(server, 'campaign_tools')
            assert server.elastic_client is None
            assert server.dshield_client is None
            assert server.data_processor is None
            assert server.context_injector is None
            assert server.campaign_analyzer is None
            assert server.campaign_tools is None
            assert isinstance(server.user_config, MockUserConfig)

    @pytest.mark.asyncio
    async def test_server_initialization_async(self):
        with patch('src.user_config.get_user_config', Mock(return_value=MockUserConfig())), \
             patch('src.elasticsearch_client.ElasticsearchClient', AsyncMock()), \
             patch('src.dshield_client.DShieldClient', AsyncMock()), \
             patch('src.data_processor.DataProcessor', Mock()), \
             patch('src.context_injector.ContextInjector', Mock()), \
             patch('src.campaign_analyzer.CampaignAnalyzer', Mock()), \
             patch('src.campaign_mcp_tools.CampaignMCPTools', Mock()):
            import mcp_server; importlib.reload(mcp_server)
            from mcp_server import DShieldMCPServer
            server = DShieldMCPServer()
            await server.initialize()
            assert server.elastic_client is not None
            assert server.dshield_client is not None
            assert server.data_processor is not None
            assert server.context_injector is not None
            assert server.campaign_analyzer is not None
            assert server.campaign_tools is not None

    def test_server_structure(self):
        with patch('src.user_config.get_user_config', Mock(return_value=MockUserConfig())), \
             patch('src.elasticsearch_client.ElasticsearchClient', Mock()), \
             patch('src.dshield_client.DShieldClient', Mock()), \
             patch('src.data_processor.DataProcessor', Mock()), \
             patch('src.context_injector.ContextInjector', Mock()), \
             patch('src.campaign_analyzer.CampaignAnalyzer', Mock()), \
             patch('src.campaign_mcp_tools.CampaignMCPTools', Mock()):
            import mcp_server; importlib.reload(mcp_server)
            from mcp_server import DShieldMCPServer
            server = DShieldMCPServer()
            assert hasattr(server, 'server')
            assert hasattr(server, 'user_config')
            assert hasattr(server, 'elastic_client')
            assert hasattr(server, 'dshield_client')
            assert hasattr(server, 'data_processor')
            assert hasattr(server, 'context_injector')
            assert hasattr(server, 'campaign_analyzer')
            assert hasattr(server, 'campaign_tools')

    @pytest.mark.asyncio
    async def test_tool_registration(self):
        with patch('src.user_config.get_user_config', Mock(return_value=MockUserConfig())), \
             patch('src.elasticsearch_client.ElasticsearchClient', AsyncMock()), \
             patch('src.dshield_client.DShieldClient', AsyncMock()), \
             patch('src.data_processor.DataProcessor', Mock()), \
             patch('src.context_injector.ContextInjector', Mock()), \
             patch('src.campaign_analyzer.CampaignAnalyzer', Mock()), \
             patch('src.campaign_mcp_tools.CampaignMCPTools', Mock()):
            import mcp_server; importlib.reload(mcp_server)
            from mcp_server import DShieldMCPServer
            server = DShieldMCPServer()
            assert hasattr(server.server, 'list_tools')
            assert hasattr(server.server, 'call_tool')
            assert hasattr(server.server, 'list_resources')
            assert hasattr(server.server, 'read_resource')

    @pytest.mark.asyncio
    async def test_query_dshield_events_tool(self):
        mock_elastic = AsyncMock()
        mock_elastic.query_dshield_events = AsyncMock(return_value=(
            [{'id': 'test-1', 'timestamp': '2024-01-01T12:00:00Z', 'event_type': 'test'}],
            1,
            {'page_number': 1, 'total_pages': 1, 'total_available': 1, 'page_size': 1, 'sort_by': '@timestamp', 'sort_order': 'desc', 'has_previous': False, 'has_next': False}
        ))
        with patch('src.user_config.get_user_config', Mock(return_value=MockUserConfig())), \
             patch('src.elasticsearch_client.ElasticsearchClient', return_value=mock_elastic), \
             patch('src.dshield_client.DShieldClient', AsyncMock()), \
             patch('src.data_processor.DataProcessor', Mock()), \
             patch('src.context_injector.ContextInjector', Mock()), \
             patch('src.campaign_analyzer.CampaignAnalyzer', Mock()), \
             patch('src.campaign_mcp_tools.CampaignMCPTools', Mock()):
            import mcp_server; importlib.reload(mcp_server)
            from mcp_server import DShieldMCPServer
            server = DShieldMCPServer()
            await server.initialize()
            arguments = {'time_range_hours': 24, 'size': 5}
            result = await server._query_dshield_events(arguments)
            assert isinstance(result, list)
            assert len(result) > 0
            assert 'type' in result[0]
            assert 'text' in result[0]
            mock_elastic.query_dshield_events.assert_called()

    @pytest.mark.asyncio
    async def test_get_dshield_statistics_tool(self):
        mock_elastic = AsyncMock()
        mock_elastic.get_dshield_statistics = AsyncMock(return_value={
            'total_events': 100,
            'unique_ips': 50,
            'time_range_hours': 24
        })
        with patch('src.user_config.get_user_config', Mock(return_value=MockUserConfig())), \
             patch('src.elasticsearch_client.ElasticsearchClient', return_value=mock_elastic), \
             patch('src.dshield_client.DShieldClient', AsyncMock()), \
             patch('src.data_processor.DataProcessor', Mock()), \
             patch('src.context_injector.ContextInjector', Mock()), \
             patch('src.campaign_analyzer.CampaignAnalyzer', Mock()), \
             patch('src.campaign_mcp_tools.CampaignMCPTools', Mock()):
            import mcp_server; importlib.reload(mcp_server)
            from mcp_server import DShieldMCPServer
            server = DShieldMCPServer()
            await server.initialize()
            arguments = {'time_range_hours': 24}
            result = await server._get_dshield_statistics(arguments)
            assert isinstance(result, list)
            assert len(result) > 0
            assert 'type' in result[0]
            assert 'text' in result[0]
            mock_elastic.get_dshield_statistics.assert_called_with(time_range_hours=24)

    @pytest.mark.asyncio
    async def test_enrich_ip_with_dshield_tool(self):
        mock_dshield = AsyncMock()
        mock_dshield.get_ip_reputation = AsyncMock(return_value={
            'ip_address': '8.8.8.8',
            'threat_level': 'low',
            'country': 'US',
            'reputation_score': 10
        })
        with patch('src.user_config.get_user_config', Mock(return_value=MockUserConfig())), \
             patch('src.elasticsearch_client.ElasticsearchClient', AsyncMock()), \
             patch('src.dshield_client.DShieldClient', return_value=mock_dshield), \
             patch('src.data_processor.DataProcessor', Mock()), \
             patch('src.context_injector.ContextInjector', Mock()), \
             patch('src.campaign_analyzer.CampaignAnalyzer', Mock()), \
             patch('src.campaign_mcp_tools.CampaignMCPTools', Mock()):
            import mcp_server; importlib.reload(mcp_server)
            from mcp_server import DShieldMCPServer
            server = DShieldMCPServer()
            await server.initialize()
            arguments = {'ip_address': '8.8.8.8'}
            result = await server._enrich_ip_with_dshield(arguments)
            assert isinstance(result, list)
            assert len(result) > 0
            assert 'type' in result[0]
            assert 'text' in result[0]
            mock_dshield.get_ip_reputation.assert_called_with('8.8.8.8')

    @pytest.mark.asyncio
    async def test_get_data_dictionary_tool(self):
        with patch('src.user_config.get_user_config', Mock(return_value=MockUserConfig())), \
             patch('src.elasticsearch_client.ElasticsearchClient', AsyncMock()), \
             patch('src.dshield_client.DShieldClient', AsyncMock()), \
             patch('src.data_processor.DataProcessor', Mock()), \
             patch('src.context_injector.ContextInjector', Mock()), \
             patch('src.campaign_analyzer.CampaignAnalyzer', Mock()), \
             patch('src.campaign_mcp_tools.CampaignMCPTools', Mock()):
            import mcp_server; importlib.reload(mcp_server)
            from mcp_server import DShieldMCPServer
            server = DShieldMCPServer()
            await server.initialize()
            arguments = {}
            result = await server._get_data_dictionary(arguments)
            assert isinstance(result, list)
            assert len(result) > 0
            assert 'type' in result[0]
            assert 'text' in result[0]
            content = result[0]['text']
            assert 'field descriptions' in content.lower() or 'data dictionary' in content.lower()

    @pytest.mark.asyncio
    async def test_server_cleanup(self):
        mock_elastic = AsyncMock()
        mock_elastic.close = AsyncMock()
        with patch('src.user_config.get_user_config', Mock(return_value=MockUserConfig())), \
             patch('src.elasticsearch_client.ElasticsearchClient', return_value=mock_elastic), \
             patch('src.dshield_client.DShieldClient', AsyncMock()), \
             patch('src.data_processor.DataProcessor', Mock()), \
             patch('src.context_injector.ContextInjector', Mock()), \
             patch('src.campaign_analyzer.CampaignAnalyzer', Mock()), \
             patch('src.campaign_mcp_tools.CampaignMCPTools', Mock()):
            import mcp_server; importlib.reload(mcp_server)
            from mcp_server import DShieldMCPServer
            server = DShieldMCPServer()
            await server.initialize()
            await server.cleanup()
            mock_elastic.close.assert_called()

    def test_server_error_handling(self, caplog):
        with patch('src.user_config.get_user_config', side_effect=Exception("Config error")):
            import mcp_server; importlib.reload(mcp_server)
            from mcp_server import DShieldMCPServer
            server = DShieldMCPServer()
            assert hasattr(server, 'user_config')
            assert server.user_config is None

    @pytest.mark.asyncio
    async def test_tool_error_handling(self):
        mock_elastic = AsyncMock()
        mock_elastic.query_dshield_events = AsyncMock(side_effect=Exception("Query failed"))
        with patch('src.user_config.get_user_config', Mock(return_value=MockUserConfig())), \
             patch('src.elasticsearch_client.ElasticsearchClient', return_value=mock_elastic), \
             patch('src.dshield_client.DShieldClient', AsyncMock()), \
             patch('src.data_processor.DataProcessor', Mock()), \
             patch('src.context_injector.ContextInjector', Mock()), \
             patch('src.campaign_analyzer.CampaignAnalyzer', Mock()), \
             patch('src.campaign_mcp_tools.CampaignMCPTools', Mock()):
            import mcp_server; importlib.reload(mcp_server)
            from mcp_server import DShieldMCPServer
            server = DShieldMCPServer()
            await server.initialize()
            arguments = {'time_range_hours': 24, 'size': 5}
            result = await server._query_dshield_events(arguments)
            assert isinstance(result, list)
            assert len(result) > 0
            assert 'type' in result[0]
            assert 'text' in result[0]
            assert 'Error querying DShield events' in result[0]['text']
            assert 'Query failed' in result[0]['text'] 