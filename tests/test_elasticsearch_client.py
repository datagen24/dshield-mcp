"""
Unit tests for Elasticsearch client.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from src.elasticsearch_client import ElasticsearchClient


class TestElasticsearchClient:
    """Test the ElasticsearchClient class."""
    
    @patch('src.elasticsearch_client.get_env_with_op_resolution')
    def test_init(self, mock_get_env):
        """Test ElasticsearchClient initialization."""
        mock_get_env.side_effect = lambda key, default=None: {
            "ELASTICSEARCH_URL": "https://test-elasticsearch:9200",
            "ELASTICSEARCH_USERNAME": "test_user",
            "ELASTICSEARCH_PASSWORD": "test_password",
            "ELASTICSEARCH_VERIFY_SSL": "true",
            "ELASTICSEARCH_CA_CERTS": "/path/to/ca.crt",
            "QUERY_TIMEOUT_SECONDS": "30",
            "MAX_QUERY_RESULTS": "1000"
        }.get(key, default)
        
        client = ElasticsearchClient()
        
        assert client.url == "https://test-elasticsearch:9200"
        assert client.username == "test_user"
        assert client.password == "test_password"
        assert client.verify_ssl is True
        assert client.ca_certs == "/path/to/ca.crt"
        assert client.timeout == 30
        assert client.max_results == 1000
        assert client.client is None
    
    @patch('src.elasticsearch_client.get_env_with_op_resolution')
    def test_init_with_op_urls(self, mock_get_env):
        """Test ElasticsearchClient initialization with 1Password URLs."""
        mock_get_env.side_effect = lambda key, default=None: {
            "ELASTICSEARCH_URL": "https://test-elasticsearch:9200",
            "ELASTICSEARCH_USERNAME": "test_user",
            "ELASTICSEARCH_PASSWORD": "resolved_password",
            "ELASTICSEARCH_VERIFY_SSL": "true",
            "ELASTICSEARCH_CA_CERTS": None,
            "QUERY_TIMEOUT_SECONDS": "30",
            "MAX_QUERY_RESULTS": "1000"
        }.get(key, default)
        
        client = ElasticsearchClient()
        
        assert client.password == "resolved_password"
    
    @pytest.mark.asyncio
    @patch('src.elasticsearch_client.AsyncElasticsearch')
    @patch('src.elasticsearch_client.get_env_with_op_resolution')
    async def test_connect_success(self, mock_get_env, mock_async_es):
        """Test successful connection to Elasticsearch."""
        mock_get_env.side_effect = lambda key, default=None: {
            "ELASTICSEARCH_URL": "https://test-elasticsearch:9200",
            "ELASTICSEARCH_USERNAME": "test_user",
            "ELASTICSEARCH_PASSWORD": "test_password",
            "ELASTICSEARCH_VERIFY_SSL": "true",
            "ELASTICSEARCH_CA_CERTS": None,
            "QUERY_TIMEOUT_SECONDS": "30",
            "MAX_QUERY_RESULTS": "1000"
        }.get(key, default)
        
        mock_client = AsyncMock()
        mock_client.info.return_value = {
            "cluster_name": "test-cluster",
            "version": {"number": "8.0.0"}
        }
        mock_async_es.return_value = mock_client
        
        client = ElasticsearchClient()
        await client.connect()
        
        assert client.client is not None
        mock_async_es.assert_called_once()
        mock_client.info.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.elasticsearch_client.AsyncElasticsearch')
    @patch('src.elasticsearch_client.get_env_with_op_resolution')
    async def test_connect_with_ssl_certs(self, mock_get_env, mock_async_es):
        """Test connection with SSL certificates."""
        mock_get_env.side_effect = lambda key, default=None: {
            "ELASTICSEARCH_URL": "https://test-elasticsearch:9200",
            "ELASTICSEARCH_USERNAME": "test_user",
            "ELASTICSEARCH_PASSWORD": "test_password",
            "ELASTICSEARCH_VERIFY_SSL": "true",
            "ELASTICSEARCH_CA_CERTS": "/path/to/ca.crt",
            "QUERY_TIMEOUT_SECONDS": "30",
            "MAX_QUERY_RESULTS": "1000"
        }.get(key, default)
        
        mock_client = AsyncMock()
        mock_client.info.return_value = {
            "cluster_name": "test-cluster",
            "version": {"number": "8.0.0"}
        }
        mock_async_es.return_value = mock_client
        
        client = ElasticsearchClient()
        await client.connect()
        
        # Check that SSL options were passed correctly
        call_args = mock_async_es.call_args
        assert 'ca_certs' in call_args[1] or 'ssl_options' in call_args[1]
    
    @pytest.mark.asyncio
    @patch('src.elasticsearch_client.AsyncElasticsearch')
    @patch('src.elasticsearch_client.get_env_with_op_resolution')
    async def test_connect_without_ssl_verification(self, mock_get_env, mock_async_es):
        """Test connection without SSL verification."""
        mock_get_env.side_effect = lambda key, default=None: {
            "ELASTICSEARCH_URL": "https://test-elasticsearch:9200",
            "ELASTICSEARCH_USERNAME": "test_user",
            "ELASTICSEARCH_PASSWORD": "test_password",
            "ELASTICSEARCH_VERIFY_SSL": "false",
            "ELASTICSEARCH_CA_CERTS": None,
            "QUERY_TIMEOUT_SECONDS": "30",
            "MAX_QUERY_RESULTS": "1000"
        }.get(key, default)
        
        mock_client = AsyncMock()
        mock_client.info.return_value = {
            "cluster_name": "test-cluster",
            "version": {"number": "8.0.0"}
        }
        mock_async_es.return_value = mock_client
        
        client = ElasticsearchClient()
        await client.connect()
        
        # Check that SSL verification was disabled
        call_args = mock_async_es.call_args
        assert 'verify_certs' in call_args[1] or 'ssl_options' in call_args[1]
    
    @pytest.mark.asyncio
    @patch('src.elasticsearch_client.AsyncElasticsearch')
    @patch('src.elasticsearch_client.get_env_with_op_resolution')
    async def test_connect_failure(self, mock_get_env, mock_async_es):
        """Test connection failure."""
        mock_get_env.side_effect = lambda key, default=None: {
            "ELASTICSEARCH_URL": "https://test-elasticsearch:9200",
            "ELASTICSEARCH_USERNAME": "test_user",
            "ELASTICSEARCH_PASSWORD": "test_password",
            "ELASTICSEARCH_VERIFY_SSL": "true",
            "ELASTICSEARCH_CA_CERTS": None,
            "QUERY_TIMEOUT_SECONDS": "30",
            "MAX_QUERY_RESULTS": "1000"
        }.get(key, default)
        
        mock_async_es.side_effect = Exception("Connection failed")
        
        client = ElasticsearchClient()
        
        with pytest.raises(Exception, match="Connection failed"):
            await client.connect()
    
    @pytest.mark.asyncio
    async def test_close(self):
        """Test closing the Elasticsearch connection."""
        client = ElasticsearchClient()
        client.client = AsyncMock()
        
        await client.close()
        
        client.client.close.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.elasticsearch_client.get_env_with_op_resolution')
    async def test_get_available_indices(self, mock_get_env):
        """Test getting available DShield indices."""
        mock_get_env.side_effect = lambda key, default=None: {
            "ELASTICSEARCH_URL": "https://test-elasticsearch:9200",
            "ELASTICSEARCH_USERNAME": "test_user",
            "ELASTICSEARCH_PASSWORD": "test_password",
            "ELASTICSEARCH_VERIFY_SSL": "true",
            "ELASTICSEARCH_CA_CERTS": None,
            "QUERY_TIMEOUT_SECONDS": "30",
            "MAX_QUERY_RESULTS": "1000"
        }.get(key, default)
        
        client = ElasticsearchClient()
        client.client = AsyncMock()
        
        # Mock indices response
        client.client.cat.indices.return_value = [
            {"index": "dshield-attacks-2024.01.01"},
            {"index": "dshield-reputation-2024.01.01"},
            {"index": "logs-2024.01.01"},
            {"index": "other-index"}
        ]
        
        indices = await client.get_available_indices()
        
        assert "dshield-attacks-2024.01.01" in indices
        assert "dshield-reputation-2024.01.01" in indices
        assert "logs-2024.01.01" not in indices  # Not a DShield index
        assert "other-index" not in indices  # Not a DShield index
    
    @pytest.mark.asyncio
    @patch('src.elasticsearch_client.get_env_with_op_resolution')
    async def test_query_dshield_events(self, mock_get_env):
        """Test querying DShield events."""
        mock_get_env.side_effect = lambda key, default=None: {
            "ELASTICSEARCH_URL": "https://test-elasticsearch:9200",
            "ELASTICSEARCH_USERNAME": "test_user",
            "ELASTICSEARCH_PASSWORD": "test_password",
            "ELASTICSEARCH_VERIFY_SSL": "true",
            "ELASTICSEARCH_CA_CERTS": None,
            "QUERY_TIMEOUT_SECONDS": "30",
            "MAX_QUERY_RESULTS": "1000"
        }.get(key, default)
        
        client = ElasticsearchClient()
        client.client = AsyncMock()
        
        # Mock search response with _id field
        mock_response = {
            "hits": {
                "total": {"value": 2},
                "hits": [
                    {
                        "_id": "1",
                        "_source": {
                            "@timestamp": "2024-01-01T10:00:00Z",
                            "source.ip": "192.168.1.100",
                            "destination.ip": "10.0.0.1",
                            "event.type": "attack",
                            "event.severity": "high"
                        }
                    },
                    {
                        "_id": "2",
                        "_source": {
                            "@timestamp": "2024-01-01T11:00:00Z",
                            "source.ip": "203.0.113.1",
                            "destination.ip": "10.0.0.2",
                            "event.type": "scan",
                            "event.severity": "medium"
                        }
                    }
                ]
            }
        }
        client.client.search.return_value = mock_response
        
        # Mock available indices
        client.get_available_indices = AsyncMock(return_value=["dshield-events-2024.01.01"])
        
        events = await client.query_dshield_events(time_range_hours=24, size=10)
        
        assert len(events) == 2
        assert events[0]["source_ip"] == "192.168.1.100"
        assert events[1]["source_ip"] == "203.0.113.1"
        
        # Verify search was called with correct parameters
        client.client.search.assert_called_once()
        call_args = client.client.search.call_args
        assert call_args[1]["size"] == 10
        assert call_args[1]["timeout"] == "30s"
    
    @pytest.mark.asyncio
    @patch('src.elasticsearch_client.get_env_with_op_resolution')
    async def test_query_dshield_events_no_client(self, mock_get_env):
        """Test querying DShield events without connected client."""
        mock_get_env.side_effect = lambda key, default=None: {
            "ELASTICSEARCH_URL": "https://test-elasticsearch:9200",
            "ELASTICSEARCH_USERNAME": "test_user",
            "ELASTICSEARCH_PASSWORD": "test_password",
            "ELASTICSEARCH_VERIFY_SSL": "true",
            "ELASTICSEARCH_CA_CERTS": None,
            "QUERY_TIMEOUT_SECONDS": "30",
            "MAX_QUERY_RESULTS": "1000"
        }.get(key, default)
        
        client = ElasticsearchClient()
        client.client = None
        
        with pytest.raises(RuntimeError, match="Elasticsearch client not connected"):
            await client.query_dshield_events()
    
    @pytest.mark.asyncio
    @patch('src.elasticsearch_client.get_env_with_op_resolution')
    async def test_query_events_by_ip(self, mock_get_env):
        """Test querying events by IP addresses."""
        mock_get_env.side_effect = lambda key, default=None: {
            "ELASTICSEARCH_URL": "https://test-elasticsearch:9200",
            "ELASTICSEARCH_USERNAME": "test_user",
            "ELASTICSEARCH_PASSWORD": "test_password",
            "ELASTICSEARCH_VERIFY_SSL": "true",
            "ELASTICSEARCH_CA_CERTS": None,
            "QUERY_TIMEOUT_SECONDS": "30",
            "MAX_QUERY_RESULTS": "1000"
        }.get(key, default)
        
        client = ElasticsearchClient()
        client.client = AsyncMock()
        
        # Mock search response with _id field
        mock_response = {
            "hits": {
                "total": {"value": 1},
                "hits": [
                    {
                        "_id": "1",
                        "_source": {
                            "@timestamp": "2024-01-01T10:00:00Z",
                            "source.ip": "192.168.1.100",
                            "destination.ip": "10.0.0.1",
                            "event.type": "attack"
                        }
                    }
                ]
            }
        }
        client.client.search.return_value = mock_response
        
        events = await client.query_events_by_ip(
            ip_addresses=["192.168.1.100"],
            time_range_hours=24
        )
        
        assert len(events) == 1
        assert events[0]["source_ip"] == "192.168.1.100"
    
    @pytest.mark.asyncio
    @patch('src.elasticsearch_client.get_env_with_op_resolution')
    async def test_get_dshield_statistics(self, mock_get_env):
        """Test getting DShield statistics."""
        mock_get_env.side_effect = lambda key, default=None: {
            "ELASTICSEARCH_URL": "https://test-elasticsearch:9200",
            "ELASTICSEARCH_USERNAME": "test_user",
            "ELASTICSEARCH_PASSWORD": "test_password",
            "ELASTICSEARCH_VERIFY_SSL": "true",
            "ELASTICSEARCH_CA_CERTS": None,
            "QUERY_TIMEOUT_SECONDS": "30",
            "MAX_QUERY_RESULTS": "1000"
        }.get(key, default)
        
        client = ElasticsearchClient()
        client.client = AsyncMock()
        
        # Mock the dependent methods that get_dshield_statistics calls
        client.query_dshield_events = AsyncMock(return_value=[
            {"event_id": "1", "source_ip": "192.168.1.100"},
            {"event_id": "2", "source_ip": "203.0.113.1"}
        ])
        client.query_dshield_top_attackers = AsyncMock(return_value=[
            {"ip_address": "192.168.1.100", "attack_count": 1000},
            {"ip_address": "203.0.113.1", "attack_count": 500}
        ])
        client.query_dshield_geographic_data = AsyncMock(return_value=[
            {"country": "US", "count": 60},
            {"country": "CN", "count": 40}
        ])
        
        # Mock the _compile_geo_stats method
        client._compile_geo_stats = lambda geo_data: {"US": 60, "CN": 40}
        
        stats = await client.get_dshield_statistics(time_range_hours=24)
        
        assert "total_events" in stats
        assert "top_attackers" in stats
        assert "geographic_distribution" in stats
        assert stats["total_events"] == 2
        assert len(stats["top_attackers"]) == 2
        assert stats["geographic_distribution"]["US"] == 60


class TestElasticsearchClientFieldMapping:
    """Test field mapping functionality."""
    
    @patch('src.elasticsearch_client.get_env_with_op_resolution')
    def test_extract_field_mapped(self, mock_get_env):
        """Test field mapping extraction."""
        mock_get_env.side_effect = lambda key, default=None: {
            "ELASTICSEARCH_URL": "https://test-elasticsearch:9200",
            "ELASTICSEARCH_USERNAME": "test_user",
            "ELASTICSEARCH_PASSWORD": "test_password",
            "ELASTICSEARCH_VERIFY_SSL": "true",
            "ELASTICSEARCH_CA_CERTS": None,
            "QUERY_TIMEOUT_SECONDS": "30",
            "MAX_QUERY_RESULTS": "1000"
        }.get(key, default)
        
        client = ElasticsearchClient()
        
        # Test source_ip mapping
        source = {
            "source.ip": "192.168.1.100",
            "src_ip": "192.168.1.101",
            "other_field": "value"
        }
        
        result = client._extract_field_mapped(source, "source_ip")
        assert result == "192.168.1.100"
        
        # Test with fallback field
        source = {
            "src_ip": "192.168.1.101",
            "other_field": "value"
        }
        
        result = client._extract_field_mapped(source, "source_ip")
        assert result == "192.168.1.101"
        
        # Test with no matching field
        source = {"other_field": "value"}
        result = client._extract_field_mapped(source, "source_ip", default="unknown")
        assert result == "unknown" 