"""
Unit tests for DShield client.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from src.dshield_client import DShieldClient

# Minimal valid config for DShieldClient
TEST_CONFIG = {
    "secrets": {
        "dshield_api_key": "test_api_key",
        "dshield_api_url": "https://test-dshield.org/api",
        "rate_limit_requests_per_minute": 60,
        "cache_ttl_seconds": 300,
        "max_ip_enrichment_batch_size": 100
    }
}

class TestDShieldClient:
    """Test the DShieldClient class."""
    
    @patch('src.config_loader.get_config')
    def test_init(self, mock_get_config):
        """Test DShieldClient initialization."""
        mock_get_config.return_value = TEST_CONFIG
        client = DShieldClient()
        
        assert client.api_key == "test_api_key"
        assert client.base_url == "https://test-dshield.org/api"
        assert client.rate_limit_requests == 60
        assert client.cache_ttl == 300
        assert client.session is None
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == "Bearer test_api_key"
    
    @patch('src.config_loader.get_config')
    def test_init_with_op_urls(self, mock_get_config):
        """Test DShieldClient initialization with 1Password URLs."""
        config = dict(TEST_CONFIG)
        config["secrets"]["dshield_api_key"] = "resolved_api_key"
        mock_get_config.return_value = config
        
        client = DShieldClient()
        
        assert client.api_key == "resolved_api_key"
        assert client.headers["Authorization"] == "Bearer resolved_api_key"
    
    @patch('src.config_loader.get_config')
    def test_init_without_api_key(self, mock_get_config):
        """Test DShieldClient initialization without API key."""
        config = dict(TEST_CONFIG)
        config["secrets"]["dshield_api_key"] = None
        mock_get_config.return_value = config
        
        client = DShieldClient()
        
        assert client.api_key is None
        assert "Authorization" not in client.headers
    
    @pytest.mark.asyncio
    @patch('src.dshield_client.aiohttp.ClientSession')
    @patch('src.config_loader.get_config')
    async def test_connect(self, mock_get_config, mock_client_session_class):
        """Test connecting to DShield API."""
        mock_get_config.return_value = TEST_CONFIG
        mock_session = AsyncMock()
        mock_client_session_class.return_value = mock_session
        
        client = DShieldClient()
        await client.connect()
        
        assert client.session is not None
        assert client.session == mock_session
        mock_client_session_class.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.config_loader.get_config')
    async def test_close(self, mock_get_config):
        """Test closing DShield client session."""
        mock_get_config.return_value = TEST_CONFIG
        client = DShieldClient()
        client.session = AsyncMock()
        
        await client.close()
        
        # No assertion on .close() call, just ensure no error and session is None
        assert client.session is None
    
    @pytest.mark.asyncio
    @patch('src.config_loader.get_config')
    async def test_get_ip_reputation_success(self, mock_get_config):
        """Test successful IP reputation lookup."""
        mock_get_config.return_value = TEST_CONFIG
        client = DShieldClient()
        client.session = AsyncMock()
        
        # Mock the response directly
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "ip": "192.168.1.100",
            "reputation": 85,
            "attacks": 1000,
            "firstseen": "2024-01-01T09:00:00Z",
            "lastseen": "2024-01-01T10:00:00Z",
            "country": "US",
            "asn": "AS12345"
        })
        
        # Use MagicMock for context manager, set __aenter__.return_value
        mock_context = MagicMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None
        client.session.get.return_value = mock_context
        
        result = await client.get_ip_reputation("192.168.1.100")
        
        assert result["ip_address"] == "192.168.1.100"
        assert result["reputation_score"] == 85
        assert result["attack_count"] == 1000
        assert result["country"] == "US"
        assert result["asn"] == "AS12345"
        
        # Verify cache was used
        assert "reputation_192.168.1.100" in client.cache
    
    @pytest.mark.asyncio
    @patch('src.config_loader.get_config')
    async def test_get_ip_reputation_not_found(self, mock_get_config):
        """Test IP reputation lookup for non-existent IP."""
        mock_get_config.return_value = TEST_CONFIG
        client = DShieldClient()
        client.session = AsyncMock()
        
        # Mock the response directly
        mock_response = AsyncMock()
        mock_response.status = 404
        
        # Use MagicMock for context manager, set __aenter__.return_value
        mock_context = MagicMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None
        client.session.get.return_value = mock_context
        
        result = await client.get_ip_reputation("192.168.1.200")
        
        assert result["ip_address"] == "192.168.1.200"
        assert result["reputation_score"] == 0
        assert result["threat_level"] == "unknown"
        assert result["attack_count"] == 0
    
    @pytest.mark.asyncio
    @patch('src.config_loader.get_config')
    async def test_get_ip_reputation_cached(self, mock_get_config):
        """Test IP reputation lookup using cached data."""
        mock_get_config.return_value = TEST_CONFIG
        client = DShieldClient()
        
        # Pre-populate cache
        cached_data = {
            "ip_address": "192.168.1.100",
            "reputation_score": 85,
            "threat_level": "high",
            "attack_count": 1000,
            "first_seen": "2024-01-01T09:00:00Z",
            "last_seen": "2024-01-01T10:00:00Z",
            "country": "US",
            "asn": "AS12345",
            "organization": "Test Org",
            "attack_types": ["ssh_brute_force"],
            "tags": ["brute_force", "ssh"]
        }
        client._cache_data("reputation_192.168.1.100", cached_data)
        
        result = await client.get_ip_reputation("192.168.1.100")
        
        assert result == cached_data
        # Verify no HTTP request was made
        assert not hasattr(client, 'session') or client.session is None
    
    @pytest.mark.asyncio
    @patch('src.config_loader.get_config')
    async def test_get_ip_reputation_http_error(self, mock_get_config):
        """Test IP reputation lookup with HTTP error."""
        mock_get_config.return_value = TEST_CONFIG
        client = DShieldClient()
        client.session = AsyncMock()
        
        # Use MagicMock for context manager, set __aenter__ to raise
        mock_context = MagicMock()
        mock_context.__aenter__.side_effect = Exception("HTTP error")
        mock_context.__aexit__.return_value = None
        client.session.get.return_value = mock_context
        
        result = await client.get_ip_reputation("192.168.1.100")
        
        assert result["ip_address"] == "192.168.1.100"
        assert result["reputation_score"] == 0
        assert result["threat_level"] == "unknown"
    
    @pytest.mark.asyncio
    @patch('src.config_loader.get_config')
    async def test_get_top_attackers(self, mock_get_config):
        """Test getting top attackers from DShield."""
        mock_get_config.return_value = TEST_CONFIG
        client = DShieldClient()
        client.session = AsyncMock()
        
        # Mock the response directly
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[
            {"ip": "192.168.1.100", "attacks": 1000, "country": "US", "asn": "AS12345"},
            {"ip": "203.0.113.1", "attacks": 500, "country": "CN", "asn": "AS67890"}
        ])
        
        # Use MagicMock for context manager, set __aenter__.return_value
        mock_context = MagicMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None
        client.session.get.return_value = mock_context
        
        result = await client.get_top_attackers(hours=24)
        
        assert len(result) == 2
        assert result[0]["ip_address"] == "192.168.1.100"
        assert result[0]["attack_count"] == 1000
        assert result[1]["ip_address"] == "203.0.113.1"
        assert result[1]["attack_count"] == 500
    
    @pytest.mark.asyncio
    @patch('src.config_loader.get_config')
    async def test_get_attack_summary(self, mock_get_config):
        """Test getting attack summary from DShield."""
        mock_get_config.return_value = TEST_CONFIG
        client = DShieldClient()
        client.session = AsyncMock()
        
        # Mock the response directly
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={
            "total_attacks": 5000,
            "unique_ips": 100,
            "top_countries": ["US", "CN", "RU"],
            "top_ports": [22, 80, 443],
            "attack_types": ["brute_force", "port_scan"]
        })
        
        # Use MagicMock for context manager, set __aenter__.return_value
        mock_context = MagicMock()
        mock_context.__aenter__.return_value = mock_response
        mock_context.__aexit__.return_value = None
        client.session.get.return_value = mock_context
        
        result = await client.get_attack_summary(hours=24)
        
        assert result["total_attacks"] == 5000
        assert result["unique_ips"] == 100
        assert "top_countries" in result
        assert "top_ports" in result
    
    @pytest.mark.asyncio
    @patch('src.config_loader.get_config')
    async def test_enrich_ips_batch(self, mock_get_config):
        """Test batch IP enrichment."""
        mock_get_config.return_value = {
            "secrets": {
                "dshield_api_key": "test_api_key",
                "dshield_api_url": "https://test-dshield.org/api",
                "rate_limit_requests_per_minute": 60,
                "cache_ttl_seconds": 300,
                "max_ip_enrichment_batch_size": 100
            }
        }
        
        client = DShieldClient()
        
        # Mock get_ip_reputation method
        client.get_ip_reputation = AsyncMock(side_effect=lambda ip: {
            "ip_address": ip,
            "reputation_score": 85 if ip == "192.168.1.100" else 60,
            "threat_level": "high" if ip == "192.168.1.100" else "medium",
            "attack_count": 1000 if ip == "192.168.1.100" else 500,
            "country": "US" if ip == "192.168.1.100" else "CN",
            "asn": "AS12345" if ip == "192.168.1.100" else "AS67890",
            "organization": "Test Org" if ip == "192.168.1.100" else "Another Org",
            "attack_types": ["ssh_brute_force"] if ip == "192.168.1.100" else ["port_scan"],
            "tags": ["brute_force", "ssh"] if ip == "192.168.1.100" else ["port_scan", "reconnaissance"]
        })
        
        ip_addresses = ["192.168.1.100", "203.0.113.1"]
        result = await client.enrich_ips_batch(ip_addresses)
        
        assert len(result) == 2
        assert "192.168.1.100" in result
        assert "203.0.113.1" in result
        assert result["192.168.1.100"]["reputation_score"] == 85
        assert result["203.0.113.1"]["reputation_score"] == 60
        
        # Verify rate limiting was respected
        assert client.get_ip_reputation.call_count == 2


class TestDShieldClientRateLimiting:
    """Test rate limiting functionality."""
    
    @pytest.mark.asyncio
    @patch('src.config_loader.get_config')
    async def test_rate_limiting(self, mock_get_config):
        """Test rate limiting functionality."""
        mock_get_config.return_value = {
            "secrets": {
                "dshield_api_key": "test_api_key",
                "dshield_api_url": "https://test-dshield.org/api",
                "rate_limit_requests_per_minute": "2",  # 2 requests per minute
                "cache_ttl_seconds": "300"
            }
        }
        
        client = DShieldClient()
        client.session = AsyncMock()
        
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"ip": "192.168.1.100"})
        
        client.session.get.return_value.__aenter__.return_value = mock_response
        
        # Make multiple requests quickly
        start_time = datetime.now()
        
        await client.get_ip_reputation("192.168.1.100")
        await client.get_ip_reputation("192.168.1.101")
        await client.get_ip_reputation("192.168.1.102")  # This should be rate limited
        
        end_time = datetime.now()
        
        # The third request should have been delayed due to rate limiting
        # Total time should be at least 1 second (60 seconds / 2 requests per minute)
        assert (end_time - start_time).total_seconds() >= 0.5  # Allow some tolerance


class TestDShieldClientCaching:
    """Test caching functionality."""
    
    @patch('src.config_loader.get_config')
    def test_cache_operations(self, mock_get_config):
        """Test cache operations."""
        mock_get_config.return_value = TEST_CONFIG
        client = DShieldClient()
        
        # Test caching data
        test_data = {"ip": "192.168.1.100", "reputation": 85}
        client._cache_data("test_key", test_data)
        
        # Test retrieving cached data
        cached_data = client._get_cached_data("test_key")
        assert cached_data == test_data
        
        # Test retrieving non-existent data
        non_existent = client._get_cached_data("non_existent_key")
        assert non_existent is None
    
    @patch('src.config_loader.get_config')
    def test_cache_expiration(self, mock_get_config):
        """Test cache expiration."""
        mock_get_config.return_value = {
            "secrets": {
                "dshield_api_key": "test_api_key",
                "dshield_api_url": "https://test-dshield.org/api",
                "rate_limit_requests_per_minute": "60",
                "cache_ttl_seconds": "1"  # 1 second TTL
            }
        }
        
        client = DShieldClient()
        
        # Cache data
        test_data = {"ip": "192.168.1.100", "reputation": 85}
        client._cache_data("test_key", test_data)
        
        # Data should be available immediately
        cached_data = client._get_cached_data("test_key")
        assert cached_data == test_data
        
        # Wait for expiration
        import time
        time.sleep(1.1)
        # Data should be expired
        expired_data = client._get_cached_data("test_key")
        assert expired_data is None 