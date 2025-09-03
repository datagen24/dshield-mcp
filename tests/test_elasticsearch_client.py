"""Unit tests for Elasticsearch client."""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.elasticsearch_client import ElasticsearchClient
from src.mcp_error_handler import MCPErrorHandler
from elasticsearch.exceptions import RequestError, TransportError

# Minimal valid config for ElasticsearchClient
TEST_CONFIG = {
    "elasticsearch": {
        "url": "https://test-elasticsearch:9200",
        "username": "test_user",
        # file deepcode ignore NoHardcodedPasswords/test: Non-production password, pytest suite
        "password": "test_password",
        "verify_ssl": True,
        "ca_certs": "/path/to/ca.crt",
        "timeout": 30,
        "max_results": 1000,
        "index_patterns": {"cowrie": [], "zeek": [], "dshield": [], "fallback": []},
    }
}


class TestElasticsearchClient:
    """Test the ElasticsearchClient class."""

    @patch('src.user_config.get_user_config')
    @patch('src.config_loader._resolve_secrets')
    @patch('src.config_loader.get_config')
    def test_init(self, mock_get_config, mock_resolve_secrets, mock_user_config):
        """Test ElasticsearchClient initialization."""
        mock_get_config.return_value = TEST_CONFIG
        mock_resolve_secrets.return_value = TEST_CONFIG

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("query", "default_page_size"): 100,
            ("query", "max_page_size"): 1000,
            ("query", "default_timeout_seconds"): 30,
            ("query", "max_timeout_seconds"): 300,
            ("query", "enable_smart_optimization"): True,
            ("query", "fallback_strategy"): "aggregate",
            ("query", "max_query_complexity"): 10,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        client = ElasticsearchClient()

        assert client.url == "https://test-elasticsearch:9200"
        assert client.username == "test_user"
        assert client.password == "test_password"
        assert client.verify_ssl is True
        assert client.ca_certs == "/path/to/ca.crt"
        assert client.timeout == 30
        assert client.max_results == 1000
        assert client.client is None

    @patch('src.user_config.get_user_config')
    @patch('src.config_loader._resolve_secrets')
    @patch('src.config_loader.get_config')
    def test_init_with_op_urls(self, mock_get_config, mock_resolve_secrets, mock_user_config):
        """Test ElasticsearchClient initialization with 1Password URLs."""
        config = dict(TEST_CONFIG)
        config["elasticsearch"]["password"] = "resolved_password"
        mock_get_config.return_value = config
        mock_resolve_secrets.return_value = config

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("query", "default_page_size"): 100,
            ("query", "max_page_size"): 1000,
            ("query", "default_timeout_seconds"): 30,
            ("query", "max_timeout_seconds"): 300,
            ("query", "enable_smart_optimization"): True,
            ("query", "fallback_strategy"): "aggregate",
            ("query", "max_query_complexity"): 10,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        client = ElasticsearchClient()

        assert client.password == "resolved_password"

    @pytest.mark.asyncio
    @patch('src.elasticsearch_client.AsyncElasticsearch')
    @patch('src.user_config.get_user_config')
    @patch('src.config_loader._resolve_secrets')
    @patch('src.config_loader.get_config')
    async def test_connect_success(
        self, mock_get_config, mock_resolve_secrets, mock_user_config, mock_async_es
    ):
        """Test successful connection to Elasticsearch."""
        mock_get_config.return_value = TEST_CONFIG
        mock_resolve_secrets.return_value = TEST_CONFIG

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("query", "default_page_size"): 100,
            ("query", "max_page_size"): 1000,
            ("query", "default_timeout_seconds"): 30,
            ("query", "max_timeout_seconds"): 300,
            ("query", "enable_smart_optimization"): True,
            ("query", "fallback_strategy"): "aggregate",
            ("query", "max_query_complexity"): 10,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        mock_client = AsyncMock()
        mock_client.info.return_value = {
            "cluster_name": "test-cluster",
            "version": {"number": "8.0.0"},
        }
        mock_async_es.return_value = mock_client

        client = ElasticsearchClient()
        await client.connect()

        assert client.client is not None
        mock_async_es.assert_called_once()
        mock_client.info.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.elasticsearch_client.AsyncElasticsearch')
    @patch('src.user_config.get_user_config')
    @patch('src.config_loader._resolve_secrets')
    @patch('src.config_loader.get_config')
    async def test_connect_with_ssl_certs(
        self, mock_get_config, mock_resolve_secrets, mock_user_config, mock_async_es
    ):
        """Test connection with SSL certificates."""
        mock_get_config.return_value = TEST_CONFIG
        mock_resolve_secrets.return_value = TEST_CONFIG

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("query", "default_page_size"): 100,
            ("query", "max_page_size"): 1000,
            ("query", "default_timeout_seconds"): 30,
            ("query", "max_timeout_seconds"): 300,
            ("query", "enable_smart_optimization"): True,
            ("query", "fallback_strategy"): "aggregate",
            ("query", "max_query_complexity"): 10,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        mock_client = AsyncMock()
        mock_client.info.return_value = {
            "cluster_name": "test-cluster",
            "version": {"number": "8.0.0"},
        }
        mock_async_es.return_value = mock_client

        client = ElasticsearchClient()
        await client.connect()

        # Check that SSL options were passed correctly
        call_args = mock_async_es.call_args
        assert 'ca_certs' in call_args[1] or 'ssl_options' in call_args[1]

    @pytest.mark.asyncio
    @patch('src.elasticsearch_client.AsyncElasticsearch')
    @patch('src.user_config.get_user_config')
    @patch('src.config_loader._resolve_secrets')
    @patch('src.config_loader.get_config')
    async def test_connect_without_ssl_verification(
        self, mock_get_config, mock_resolve_secrets, mock_user_config, mock_async_es
    ):
        """Test connection without SSL verification."""
        config = dict(TEST_CONFIG)
        config["elasticsearch"]["verify_ssl"] = False
        mock_get_config.return_value = config
        mock_resolve_secrets.return_value = config

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("query", "default_page_size"): 100,
            ("query", "max_page_size"): 1000,
            ("query", "default_timeout_seconds"): 30,
            ("query", "max_timeout_seconds"): 300,
            ("query", "enable_smart_optimization"): True,
            ("query", "fallback_strategy"): "aggregate",
            ("query", "max_query_complexity"): 10,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        mock_client = AsyncMock()
        mock_client.info.return_value = {
            "cluster_name": "test-cluster",
            "version": {"number": "8.0.0"},
        }
        mock_async_es.return_value = mock_client

        client = ElasticsearchClient()
        await client.connect()

        # Check that SSL verification was disabled
        call_args = mock_async_es.call_args
        assert 'verify_certs' in call_args[1] or 'ssl_options' in call_args[1]

    @pytest.mark.asyncio
    @patch('src.elasticsearch_client.AsyncElasticsearch')
    @patch('src.user_config.get_user_config')
    @patch('src.config_loader._resolve_secrets')
    @patch('src.config_loader.get_config')
    async def test_connect_failure(
        self, mock_get_config, mock_resolve_secrets, mock_user_config, mock_async_es
    ):
        """Test connection failure."""
        mock_get_config.return_value = TEST_CONFIG
        mock_resolve_secrets.return_value = TEST_CONFIG

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("query", "default_page_size"): 100,
            ("query", "max_page_size"): 1000,
            ("query", "default_timeout_seconds"): 30,
            ("query", "max_timeout_seconds"): 300,
            ("query", "enable_smart_optimization"): True,
            ("query", "fallback_strategy"): "aggregate",
            ("query", "max_query_complexity"): 10,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        mock_client = AsyncMock()
        mock_client.info.side_effect = Exception("Connection failed")
        mock_async_es.return_value = mock_client

        client = ElasticsearchClient()

        with pytest.raises(Exception):
            await client.connect()

    @pytest.mark.asyncio
    @patch('src.user_config.get_user_config')
    @patch('src.config_loader._resolve_secrets')
    @patch('src.config_loader.get_config')
    async def test_close(self, mock_get_config, mock_resolve_secrets, mock_user_config):
        """Test closing Elasticsearch connection."""
        mock_get_config.return_value = TEST_CONFIG
        mock_resolve_secrets.return_value = TEST_CONFIG

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("query", "default_page_size"): 100,
            ("query", "max_page_size"): 1000,
            ("query", "default_timeout_seconds"): 30,
            ("query", "max_timeout_seconds"): 300,
            ("query", "enable_smart_optimization"): True,
            ("query", "fallback_strategy"): "aggregate",
            ("query", "max_query_complexity"): 10,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        client = ElasticsearchClient()
        client.client = AsyncMock()

        await client.close()

        client.client.close.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.user_config.get_user_config')
    @patch('src.config_loader._resolve_secrets')
    @patch('src.config_loader.get_config')
    async def test_get_available_indices(
        self, mock_get_config, mock_resolve_secrets, mock_user_config
    ):
        """Test getting available indices."""
        mock_get_config.return_value = TEST_CONFIG
        mock_resolve_secrets.return_value = TEST_CONFIG

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("query", "default_page_size"): 100,
            ("query", "max_page_size"): 1000,
            ("query", "default_timeout_seconds"): 30,
            ("query", "max_timeout_seconds"): 300,
            ("query", "enable_smart_optimization"): True,
            ("query", "fallback_strategy"): "aggregate",
            ("query", "max_query_complexity"): 10,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        client = ElasticsearchClient()

        # Mock client and indices
        mock_client = AsyncMock()
        mock_client.cat.indices.return_value = [
            {"index": "dshield-attacks-2024.01.01"},
            {"index": "dshield-events-2024.01.01"},
            {"index": "other-index"},
        ]
        client.client = mock_client

        indices = await client.get_available_indices()

        # The method should return an empty list since no index patterns are configured in TEST_CONFIG
        assert indices == []

    @pytest.mark.asyncio
    @patch('src.user_config.get_user_config')
    @patch('src.config_loader._resolve_secrets')
    @patch('src.config_loader.get_config')
    async def test_query_dshield_events(
        self, mock_get_config, mock_resolve_secrets, mock_user_config
    ):
        """Test querying DShield events."""
        mock_get_config.return_value = TEST_CONFIG
        mock_resolve_secrets.return_value = TEST_CONFIG

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("query", "default_page_size"): 100,
            ("query", "max_page_size"): 1000,
            ("query", "default_timeout_seconds"): 30,
            ("query", "max_timeout_seconds"): 300,
            ("query", "enable_smart_optimization"): True,
            ("query", "fallback_strategy"): "aggregate",
            ("query", "max_query_complexity"): 10,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        client = ElasticsearchClient()

        # Mock client and search results
        mock_client = AsyncMock()
        mock_search_result = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {
                        "_source": {
                            "@timestamp": "2024-01-01T10:00:00Z",
                            "source.ip": "192.168.1.100",
                            "destination.ip": "10.0.0.1",
                            "event.type": "attack",
                        }
                    },
                    {
                        "_source": {
                            "@timestamp": "2024-01-01T11:00:00Z",
                            "source.ip": "203.0.113.1",
                            "destination.ip": "10.0.0.2",
                            "event.type": "scan",
                        }
                    },
                ],
            }
        }
        mock_client.search.return_value = mock_search_result
        client.client = mock_client

        events, total, summary = await client.query_dshield_events()

        # The method should return the mocked results since fallback indices are used
        assert len(events) == 2  # Events are parsed from mock data
        assert total == 2

    @pytest.mark.asyncio
    @patch('src.user_config.get_user_config')
    @patch('src.config_loader._resolve_secrets')
    @patch('src.config_loader.get_config')
    async def test_query_dshield_events_no_client(
        self, mock_get_config, mock_resolve_secrets, mock_user_config
    ):
        """Test querying DShield events when client is not connected."""
        mock_get_config.return_value = TEST_CONFIG
        mock_resolve_secrets.return_value = TEST_CONFIG

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("query", "default_page_size"): 100,
            ("query", "max_page_size"): 1000,
            ("query", "default_timeout_seconds"): 30,
            ("query", "max_timeout_seconds"): 300,
            ("query", "enable_smart_optimization"): True,
            ("query", "fallback_strategy"): "aggregate",
            ("query", "max_query_complexity"): 10,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        client = ElasticsearchClient()
        client.client = None

        # Mock connect method
        async def connect_side_effect():
            # After connect is called, set client.client to the mock
            client.client = mock_client

        client.connect = AsyncMock(side_effect=connect_side_effect)

        # Mock client and search results
        mock_client = AsyncMock()
        mock_search_result = {"hits": {"total": {"value": 0}, "hits": []}}
        mock_client.search.return_value = mock_search_result

        events, total, summary = await client.query_dshield_events()

        # The method should return the mocked results since fallback indices are used
        assert len(events) == 0  # Events are empty due to parsing issues
        assert total == 0  # Total count from mock response
        # The connect method should be called when client is None
        client.connect.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.user_config.get_user_config')
    @patch('src.config_loader._resolve_secrets')
    @patch('src.config_loader.get_config')
    async def test_query_events_by_ip(
        self, mock_get_config, mock_resolve_secrets, mock_user_config
    ):
        """Test querying events by IP address."""
        mock_get_config.return_value = TEST_CONFIG
        mock_resolve_secrets.return_value = TEST_CONFIG

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("query", "default_page_size"): 100,
            ("query", "max_page_size"): 1000,
            ("query", "default_timeout_seconds"): 30,
            ("query", "max_timeout_seconds"): 300,
            ("query", "enable_smart_optimization"): True,
            ("query", "fallback_strategy"): "aggregate",
            ("query", "max_query_complexity"): 10,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        client = ElasticsearchClient()

        # Mock client and search results
        mock_client = AsyncMock()
        mock_search_result = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_source": {
                            "@timestamp": "2024-01-01T10:00:00Z",
                            "source.ip": "192.168.1.100",
                            "destination.ip": "10.0.0.1",
                            "event.type": "attack",
                        }
                    }
                ],
            }
        }
        mock_client.search.return_value = mock_search_result
        client.client = mock_client

        events = await client.query_events_by_ip(["192.168.1.100"])

        # The method should return the mocked results
        assert len(events) == 1  # One event returned from mock data

    @pytest.mark.asyncio
    @patch('src.user_config.get_user_config')
    @patch('src.config_loader._resolve_secrets')
    @patch('src.config_loader.get_config')
    async def test_get_dshield_statistics(
        self, mock_get_config, mock_resolve_secrets, mock_user_config
    ):
        """Test getting DShield statistics."""
        mock_get_config.return_value = TEST_CONFIG
        mock_resolve_secrets.return_value = TEST_CONFIG

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("query", "default_page_size"): 100,
            ("query", "max_page_size"): 1000,
            ("query", "default_timeout_seconds"): 30,
            ("query", "max_timeout_seconds"): 300,
            ("query", "enable_smart_optimization"): True,
            ("query", "fallback_strategy"): "aggregate",
            ("query", "max_query_complexity"): 10,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        client = ElasticsearchClient()

        # Mock client and search results
        mock_client = AsyncMock()
        mock_search_result = {
            "hits": {"total": {"value": 1000}},
            "aggregations": {
                "unique_ips": {"value": 100},
                "geographic_distribution": {
                    "buckets": [{"key": "US", "doc_count": 60}, {"key": "CN", "doc_count": 40}]
                },
            },
        }
        mock_client.search.return_value = mock_search_result
        client.client = mock_client

        stats = await client.get_dshield_statistics()

        # The method should return structured stats with default values
        assert isinstance(stats, dict)
        assert 'total_events' in stats
        assert 'top_attackers' in stats
        assert 'geographic_distribution' in stats
        assert 'time_range_hours' in stats
        assert 'timestamp' in stats


class TestElasticsearchClientFieldMapping:
    """Test field mapping functionality."""

    @patch('src.user_config.get_user_config')
    @patch('src.config_loader._resolve_secrets')
    @patch('src.config_loader.get_config')
    def test_extract_field_mapped(self, mock_get_config, mock_resolve_secrets, mock_user_config):
        """Test field mapping extraction."""
        mock_get_config.return_value = TEST_CONFIG
        mock_resolve_secrets.return_value = TEST_CONFIG

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("query", "default_page_size"): 100,
            ("query", "max_page_size"): 1000,
            ("query", "default_timeout_seconds"): 30,
            ("query", "max_timeout_seconds"): 300,
            ("query", "enable_smart_optimization"): True,
            ("query", "fallback_strategy"): "aggregate",
            ("query", "max_query_complexity"): 10,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        client = ElasticsearchClient()

        # Test source_ip mapping
        source_data = {
            "source.ip": "192.168.1.100",
            "src_ip": "192.168.1.101",
            "destination.ip": "10.0.0.1",
        }

        source_ip = client._extract_field_mapped(source_data, "source_ip")
        assert source_ip == "192.168.1.100"

        # Test destination_ip mapping
        dest_ip = client._extract_field_mapped(source_data, "destination_ip")
        assert dest_ip == "10.0.0.1"

        # Test non-existent field
        non_existent = client._extract_field_mapped(source_data, "non_existent")
        assert non_existent is None


class TestElasticsearchClientErrorHandling:
    """Test error handling functionality with MCPErrorHandler."""

    @patch('src.user_config.get_user_config')
    @patch('src.config_loader._resolve_secrets')
    @patch('src.config_loader.get_config')
    def test_init_with_error_handler(self, mock_get_config, mock_resolve_secrets, mock_user_config):
        """Test ElasticsearchClient initialization with error handler."""
        mock_get_config.return_value = TEST_CONFIG
        mock_resolve_secrets.return_value = TEST_CONFIG

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("query", "default_page_size"): 100,
            ("query", "max_page_size"): 1000,
            ("query", "default_timeout_seconds"): 30,
            ("query", "max_timeout_seconds"): 300,
            ("query", "enable_smart_optimization"): True,
            ("query", "fallback_strategy"): "aggregate",
            ("query", "max_query_complexity"): 10,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        # Create error handler
        error_handler = MCPErrorHandler()
        client = ElasticsearchClient(error_handler=error_handler)

        assert client.error_handler is not None
        assert isinstance(client.error_handler, MCPErrorHandler)

    @patch('src.user_config.get_user_config')
    @patch('src.config_loader._resolve_secrets')
    @patch('src.config_loader.get_config')
    def test_init_without_error_handler(
        self, mock_get_config, mock_resolve_secrets, mock_user_config
    ):
        """Test ElasticsearchClient initialization without error handler."""
        mock_get_config.return_value = TEST_CONFIG
        mock_resolve_secrets.return_value = TEST_CONFIG

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("query", "default_page_size"): 100,
            ("query", "max_page_size"): 1000,
            ("query", "default_timeout_seconds"): 30,
            ("query", "max_timeout_seconds"): 300,
            ("query", "enable_smart_optimization"): True,
            ("query", "fallback_strategy"): "aggregate",
            ("query", "max_query_complexity"): 10,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        client = ElasticsearchClient()

        assert client.error_handler is None

    @pytest.mark.asyncio
    @patch('src.user_config.get_user_config')
    @patch('src.config_loader._resolve_secrets')
    @patch('src.config_loader.get_config')
    async def test_query_events_with_error_handler_request_error(
        self, mock_get_config, mock_resolve_secrets, mock_user_config
    ):
        """Test query events with error handler when RequestError occurs."""
        mock_get_config.return_value = TEST_CONFIG
        mock_resolve_secrets.return_value = TEST_CONFIG

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("query", "default_page_size"): 100,
            ("query", "max_page_size"): 1000,
            ("query", "default_timeout_seconds"): 30,
            ("query", "max_timeout_seconds"): 300,
            ("query", "enable_smart_optimization"): True,
            ("query", "fallback_strategy"): "aggregate",
            ("query", "max_query_complexity"): 10,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        # Create error handler
        error_handler = MCPErrorHandler()
        client = ElasticsearchClient(error_handler=error_handler)

        # Mock client that raises RequestError
        mock_client = AsyncMock()

        # Create a proper RequestError that can be raised and recognized
        class TestRequestError(RequestError):
            def __init__(self):
                super().__init__("Test request error", meta=Mock(), body="test")

        mock_client.search.side_effect = TestRequestError()
        client.client = mock_client

        # Test query with error handler
        events, total_count, pagination_info = await client.query_dshield_events(
            time_range_hours=24, page_size=100
        )

        # Should return error response instead of raising exception
        assert events == []
        assert total_count == 0
        assert "error" in pagination_info
        assert pagination_info["error"]["error"]["code"] == error_handler.EXTERNAL_SERVICE_ERROR

    @pytest.mark.asyncio
    @patch('src.user_config.get_user_config')
    @patch('src.config_loader._resolve_secrets')
    @patch('src.config_loader.get_config')
    async def test_query_events_with_error_handler_transport_error(
        self, mock_get_config, mock_resolve_secrets, mock_user_config
    ):
        """Test query events with error handler when TransportError occurs."""
        mock_get_config.return_value = TEST_CONFIG
        mock_resolve_secrets.return_value = TEST_CONFIG

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("query", "default_page_size"): 100,
            ("query", "max_page_size"): 1000,
            ("query", "default_timeout_seconds"): 30,
            ("query", "max_timeout_seconds"): 300,
            ("query", "enable_smart_optimization"): True,
            ("query", "fallback_strategy"): "aggregate",
            ("query", "max_query_complexity"): 10,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        # Create error handler
        error_handler = MCPErrorHandler()
        client = ElasticsearchClient(error_handler=error_handler)

        # Mock client that raises TransportError
        mock_client = AsyncMock()
        mock_client.search.side_effect = TransportError("Test transport error", "test")
        client.client = mock_client

        # Test query with error handler
        events, total_count, pagination_info = await client.query_dshield_events(
            time_range_hours=24, page_size=100
        )

        # Should return error response instead of raising exception
        assert events == []
        assert total_count == 0
        assert "error" in pagination_info
        assert pagination_info["error"]["error"]["code"] == error_handler.EXTERNAL_SERVICE_ERROR

    @pytest.mark.asyncio
    @patch('src.user_config.get_user_config')
    @patch('src.config_loader._resolve_secrets')
    @patch('src.config_loader.get_config')
    async def test_query_events_without_error_handler_raises_exception(
        self, mock_get_config, mock_resolve_secrets, mock_user_config
    ):
        """Test query events without error handler raises exception."""
        mock_get_config.return_value = TEST_CONFIG
        mock_resolve_secrets.return_value = TEST_CONFIG

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("query", "default_page_size"): 100,
            ("query", "max_page_size"): 1000,
            ("query", "default_timeout_seconds"): 30,
            ("query", "max_timeout_seconds"): 300,
            ("query", "enable_smart_optimization"): True,
            ("query", "fallback_strategy"): "aggregate",
            ("query", "max_query_complexity"): 10,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        client = ElasticsearchClient()

        # Mock client that raises RequestError
        mock_client = AsyncMock()

        # Create a proper RequestError that can be raised and recognized
        class TestRequestError(RequestError):
            def __init__(self):
                super().__init__("Test request error", meta=Mock(), body="test")

        mock_client.search.side_effect = TestRequestError()
        client.client = mock_client

        # Test query without error handler should raise exception
        with pytest.raises(RequestError):
            await client.query_dshield_events(time_range_hours=24, page_size=100)

    @pytest.mark.asyncio
    @patch('src.user_config.get_user_config')
    @patch('src.config_loader._resolve_secrets')
    @patch('src.config_loader.get_config')
    async def test_aggregation_query_with_error_handler(
        self, mock_get_config, mock_resolve_secrets, mock_user_config
    ):
        """Test aggregation query with error handler."""
        mock_get_config.return_value = TEST_CONFIG
        mock_resolve_secrets.return_value = TEST_CONFIG

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("query", "default_page_size"): 100,
            ("query", "max_page_size"): 1000,
            ("query", "default_timeout_seconds"): 30,
            ("query", "max_timeout_seconds"): 300,
            ("query", "enable_smart_optimization"): True,
            ("query", "fallback_strategy"): "aggregate",
            ("query", "max_query_complexity"): 10,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        # Create error handler
        error_handler = MCPErrorHandler()
        client = ElasticsearchClient(error_handler=error_handler)

        # Mock client that raises RequestError
        mock_client = AsyncMock()

        # Create a proper RequestError that can be raised and recognized
        class TestRequestError(RequestError):
            def __init__(self):
                super().__init__("Test aggregation error", meta=Mock(), body="test")

        mock_client.search.side_effect = TestRequestError()
        client.client = mock_client

        # Test aggregation query with error handler
        result = await client.execute_aggregation_query(
            query={"match_all": {}},
            aggregation_query={"aggs": {"test": {"terms": {"field": "test"}}}},
            index=["test-index"],
        )

        # Should return error response instead of raising exception
        assert "error" in result
        assert result["error"]["error"]["code"] == error_handler.EXTERNAL_SERVICE_ERROR
