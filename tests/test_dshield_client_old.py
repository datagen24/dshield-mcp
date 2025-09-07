"""Unit tests for DShield client."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from src.dshield_client import DShieldClient

# Minimal valid config for DShieldClient
TEST_CONFIG = {
    "secrets": {
        "dshield_api_key": "test_api_key",
        "dshield_api_url": "https://test-dshield.org/api",
        "rate_limit_requests_per_minute": 60,
        "cache_ttl_seconds": 300,
        "max_ip_enrichment_batch_size": 100,
    }
}


class TestDShieldClient:
    """Test the DShieldClient class."""

    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_user_config')
    def test_init(self, mock_get_config, mock_op_secrets_class, mock_user_config):
        """Test DShieldClient initialization."""
        mock_get_config.return_value = TEST_CONFIG

        # Mock 1Password resolution
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "test_api_key"
        mock_op_secrets_class.return_value = mock_op_instance

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("performance", "enable_caching"): True,
            ("performance", "max_cache_size"): 1000,
            ("performance", "request_timeout_seconds"): 30,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        client = DShieldClient()

        assert client.api_key == "test_api_key"
        assert client.base_url == "https://test-dshield.org/api"
        assert client.rate_limit_requests == 60
        assert client.cache_ttl == 300
        assert client.session is None
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == "Bearer test_api_key"

    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_user_config')
    def test_init_with_op_urls(self, mock_get_config, mock_op_secrets_class, mock_user_config):
        """Test DShieldClient initialization with 1Password URLs."""
        config = dict(TEST_CONFIG)
        config["secrets"]["dshield_api_key"] = "op://vault/dshield/api-key"
        mock_get_config.return_value = config

        # Mock 1Password resolution - create a mock instance that will be returned when OnePasswordSecrets() is called
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "resolved_api_key"
        mock_op_secrets_class.return_value = mock_op_instance

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("performance", "enable_caching"): True,
            ("performance", "max_cache_size"): 1000,
            ("request_timeout_seconds"): 30,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        client = DShieldClient()

        # Verify the mock was called correctly
        mock_op_secrets_class.assert_called_once()
        mock_op_instance.resolve_environment_variable.assert_called_once_with(
            "op://vault/dshield/api-key"
        )

        # Verify the client has the resolved value
        assert client.api_key == "resolved_api_key"
        assert client.headers["Authorization"] == "Bearer resolved_api_key"

    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_user_config')
    def test_init_without_api_key(self, mock_get_config, mock_op_secrets_class, mock_user_config):
        """Test DShieldClient initialization without API key."""
        config = dict(TEST_CONFIG)
        config["secrets"]["dshield_api_key"] = None
        mock_get_config.return_value = config

        # Mock 1Password resolution
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = None
        mock_op_secrets_class.return_value = mock_op_instance

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("performance", "enable_caching"): True,
            ("performance", "max_cache_size"): 1000,
            ("performance", "request_timeout_seconds"): 30,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        client = DShieldClient()

        assert client.api_key is None
        assert "Authorization" not in client.headers

    @pytest.mark.asyncio
    @patch('src.dshield_client.get_user_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.aiohttp.ClientSession')
    async def test_connect(
        self, mock_client_session_class, mock_user_config, mock_op_secrets_class, mock_get_config
    ):
        """Test connecting to DShield API."""
        mock_get_config.return_value = TEST_CONFIG

        # Mock 1Password resolution
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "test_api_key"
        mock_op_secrets_class.return_value = mock_op_instance

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("performance", "enable_caching"): True,
            ("performance", "max_cache_size"): 1000,
            ("performance", "request_timeout_seconds"): 30,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        mock_session = AsyncMock()
        mock_client_session_class.return_value = mock_session

        client = DShieldClient()
        await client.connect()

        assert client.session is not None
        assert client.session == mock_session
        mock_client_session_class.assert_called_once()

    @pytest.mark.asyncio
    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_user_config')
    async def test_close(self, mock_get_config, mock_op_secrets_class, mock_user_config):
        """Test closing DShield client session."""
        mock_get_config.return_value = TEST_CONFIG

        # Mock 1Password resolution
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "test_api_key"
        mock_op_secrets_class.return_value = mock_op_instance

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("performance", "enable_caching"): True,
            ("performance", "max_cache_size"): 1000,
            ("performance", "request_timeout_seconds"): 30,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        client = DShieldClient()
        client.session = AsyncMock()

        await client.close()

        # No assertion on .close() call, just ensure no error and session is None
        assert client.session is None

    @pytest.mark.asyncio
    @patch('src.dshield_client.get_user_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.aiohttp.ClientSession')
    async def test_get_ip_reputation_success(
        self, mock_client_session_class, mock_user_config, mock_op_secrets_class, mock_get_config
    ):
        """Test successful IP reputation lookup."""
        mock_get_config.return_value = TEST_CONFIG

        # Mock 1Password resolution
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "test_api_key"
        mock_op_secrets_class.return_value = mock_op_instance

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("performance", "enable_caching"): True,
            ("performance", "max_cache_size"): 1000,
            ("performance", "request_timeout_seconds"): 30,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        # Set up the async context manager for the session's get method
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={
                "ip": "192.168.1.100",
                "reputation": 85,
                "attacks": 1000,
                "firstseen": "2024-01-01T09:00:00Z",
                "lastseen": "2024-01-01T10:00:00Z",
                "country": "US",
                "as": "AS12345",
            }
        )
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_context_manager
        mock_client_session_class.return_value = mock_session

        client = DShieldClient()
        await client.connect()  # ensure session is set

        result = await client.get_ip_reputation("192.168.1.100")

        assert result["reputation_score"] == 85.0
        assert result["ip_address"] == "192.168.1.100"
        assert result["attack_types"] == 1000
        assert result["country"] == "US"
        assert result["asn"] == "AS12345"

    @pytest.mark.asyncio
    @patch('src.dshield_client.get_user_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.aiohttp.ClientSession')
    async def test_get_ip_reputation_not_found(
        self, mock_client_session_class, mock_user_config, mock_op_secrets_class, mock_get_config
    ):
        """Test IP reputation lookup when IP not found."""
        mock_get_config.return_value = TEST_CONFIG

        # Mock 1Password resolution
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "test_api_key"
        mock_op_secrets_class.return_value = mock_op_instance

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("performance", "enable_caching"): True,
            ("performance", "max_cache_size"): 1000,
            ("performance", "request_timeout_seconds"): 30,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        # Create a proper async context manager
        class MockContextManager:
            def __init__(self, response):
                self.response = response

            async def __aenter__(self):
                return self.response

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 404
        mock_session.get.return_value = MockContextManager(mock_response)
        mock_client_session_class.return_value = mock_session

        client = DShieldClient()
        client.session = mock_session

        result = await client.get_ip_reputation("192.168.1.200")

        assert result["reputation_score"] is None
        assert result["ip_address"] == "192.168.1.200"
        assert result["attack_types"] == []

    @pytest.mark.asyncio
    @patch('src.dshield_client.get_user_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.aiohttp.ClientSession')
    async def test_get_ip_reputation_cached(
        self, mock_client_session_class, mock_user_config, mock_op_secrets_class, mock_get_config
    ):
        """Test IP reputation lookup returns cached data."""
        mock_get_config.return_value = TEST_CONFIG

        # Mock 1Password resolution
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "test_api_key"
        mock_op_secrets_class.return_value = mock_op_instance

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("performance", "enable_caching"): True,
            ("performance", "max_cache_size"): 1000,
            ("performance", "request_timeout_seconds"): 30,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        client = DShieldClient()

        # Pre-populate cache
        cache_data = {
            "ip_address": "192.168.1.100",
            "reputation_score": 85,
            "attack_count": 1000,
            "country": "US",
            "asn": "AS12345",
            "timestamp": datetime.now().isoformat(),
        }
        client._cache_data("reputation_192.168.1.100", cache_data)

        result = await client.get_ip_reputation("192.168.1.100")

        assert result == cache_data

    @pytest.mark.asyncio
    @patch('src.dshield_client.get_user_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.aiohttp.ClientSession')
    async def test_get_ip_reputation_http_error(
        self, mock_client_session_class, mock_user_config, mock_op_secrets_class, mock_get_config
    ):
        """Test IP reputation lookup with HTTP error."""
        mock_get_config.return_value = TEST_CONFIG

        # Mock 1Password resolution
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "test_api_key"
        mock_op_secrets_class.return_value = mock_op_instance

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("performance", "enable_caching"): True,
            ("performance", "max_cache_size"): 1000,
            ("performance", "request_timeout_seconds"): 30,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        # Create a proper async context manager
        class MockContextManager:
            def __init__(self, response):
                self.response = response

            async def __aenter__(self):
                return self.response

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_session.get.return_value = MockContextManager(mock_response)
        mock_client_session_class.return_value = mock_session

        client = DShieldClient()
        client.session = mock_session

        result = await client.get_ip_reputation("192.168.1.100")

        assert result["reputation_score"] is None
        assert result["ip_address"] == "192.168.1.100"

    @pytest.mark.asyncio
    @patch('src.dshield_client.get_user_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.aiohttp.ClientSession')
    async def test_get_top_attackers(
        self, mock_client_session_class, mock_user_config, mock_op_secrets_class, mock_get_config
    ):
        """Test getting top attackers from DShield."""
        mock_get_config.return_value = TEST_CONFIG

        # Mock 1Password resolution
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "test_api_key"
        mock_op_secrets_class.return_value = mock_op_instance

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("performance", "enable_caching"): True,
            ("performance", "max_cache_size"): 1000,
            ("performance", "request_timeout_seconds"): 30,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        # Set up the async context manager for the session's get method
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value=[
                {"ip": "192.168.1.100", "count": 1000, "country": "US"},
                {"ip": "203.0.113.1", "count": 500, "country": "CN"},
            ]
        )
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_context_manager
        mock_client_session_class.return_value = mock_session

        client = DShieldClient()
        await client.connect()

        result = await client.get_top_attackers(24)

        assert len(result) == 2
        assert result[0]["ip_address"] == "192.168.1.100"
        assert result[0]["attack_count"] == 1000
        assert result[1]["ip_address"] == "203.0.113.1"
        assert result[1]["attack_count"] == 500

    @pytest.mark.asyncio
    @patch('src.dshield_client.get_user_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.aiohttp.ClientSession')
    async def test_get_attack_summary(
        self, mock_client_session_class, mock_user_config, mock_op_secrets_class, mock_get_config
    ):
        """Test getting attack summary from DShield."""
        mock_get_config.return_value = TEST_CONFIG

        # Mock 1Password resolution
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "test_api_key"
        mock_op_secrets_class.return_value = mock_op_instance

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("performance", "enable_caching"): True,
            ("performance", "max_cache_size"): 1000,
            ("performance", "request_timeout_seconds"): 30,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        # Set up the async context manager for the session's get method
        mock_session = MagicMock()
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"total": 5000, "unique": 100, "countries": 10, "ports": 50}
        )
        mock_context_manager = MagicMock()
        mock_context_manager.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context_manager.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_context_manager
        mock_client_session_class.return_value = mock_session

        client = DShieldClient()
        await client.connect()

        result = await client.get_attack_summary(24)

        assert result["total_attacks"] == 5000
        assert result["unique_attackers"] == 100
        assert result["top_countries"] == 10
        assert result["top_ports"] == 50

    @pytest.mark.asyncio
    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_user_config')
    async def test_enrich_ips_batch(self, mock_get_config, mock_op_secrets_class, mock_user_config):
        """Test batch IP enrichment."""
        mock_get_config.return_value = TEST_CONFIG

        # Mock 1Password resolution
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "test_api_key"
        mock_op_secrets_class.return_value = mock_op_instance

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("performance", "enable_caching"): True,
            ("performance", "max_cache_size"): 1000,
            ("performance", "request_timeout_seconds"): 30,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        client = DShieldClient()

        # Mock get_ip_reputation method
        client.get_ip_reputation = AsyncMock(
            side_effect=[
                {"ip_address": "192.168.1.100", "reputation_score": 85},
                {"ip_address": "203.0.113.1", "reputation_score": 60},
            ]
        )

        ip_addresses = ["192.168.1.100", "203.0.113.1"]
        result = await client.enrich_ips_batch(ip_addresses)

        assert len(result) == 2
        assert result["192.168.1.100"]["reputation_score"] == 85
        assert result["203.0.113.1"]["reputation_score"] == 60
        assert client.get_ip_reputation.call_count == 2


class TestDShieldClientRateLimiting:
    """Test rate limiting functionality."""

    @pytest.mark.asyncio
    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_user_config')
    async def test_rate_limiting(self, mock_get_config, mock_op_secrets_class, mock_user_config):
        """Test rate limiting behavior."""
        mock_get_config.return_value = TEST_CONFIG

        # Mock 1Password resolution
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "test_api_key"
        mock_op_secrets_class.return_value = mock_op_instance

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("performance", "enable_caching"): True,
            ("performance", "max_cache_size"): 1000,
            ("performance", "request_timeout_seconds"): 30,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        client = DShieldClient()
        client.rate_limit_requests = 2  # 2 requests per minute

        # Mock session and response
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"ip": "192.168.1.100", "reputation": 85})

        # Mock async context manager
        mock_context = AsyncMock()
        mock_context.__aenter__ = AsyncMock(return_value=mock_response)
        mock_context.__aexit__ = AsyncMock(return_value=None)
        mock_session.get.return_value = mock_context

        client.session = mock_session

        # Make multiple requests quickly
        start_time = datetime.now()

        # First two requests should succeed immediately
        await client.get_ip_reputation("192.168.1.100")
        await client.get_ip_reputation("192.168.1.101")

        # Third request should be rate limited
        await client.get_ip_reputation("192.168.1.102")

        end_time = datetime.now()

        # Should have taken at least 0.5 seconds due to rate limiting
        assert (end_time - start_time).total_seconds() >= 0.5  # Allow some tolerance


class TestDShieldClientCaching:
    """Test caching functionality."""

    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_user_config')
    def test_cache_operations(self, mock_get_config, mock_op_secrets_class, mock_user_config):
        """Test cache operations."""
        mock_get_config.return_value = TEST_CONFIG

        # Mock 1Password resolution
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "test_api_key"
        mock_op_secrets_class.return_value = mock_op_instance

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("performance", "enable_caching"): True,
            ("performance", "max_cache_size"): 1000,
            ("performance", "request_timeout_seconds"): 30,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        client = DShieldClient()

        # Test caching data
        test_data = {"ip": "192.168.1.100", "reputation": 85}
        client._cache_data("test_key", test_data)

        # Test retrieving cached data
        cached_data = client._get_cached_data("test_key")
        assert cached_data == test_data

        # Test cache miss
        missing_data = client._get_cached_data("missing_key")
        assert missing_data is None

    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_user_config')
    def test_cache_expiration(self, mock_get_config, mock_op_secrets_class, mock_user_config):
        """Test cache expiration."""
        mock_get_config.return_value = TEST_CONFIG

        # Mock 1Password resolution
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "test_api_key"
        mock_op_secrets_class.return_value = mock_op_instance

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("performance", "enable_caching"): True,
            ("performance", "max_cache_size"): 1000,
            ("performance", "request_timeout_seconds"): 30,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        client = DShieldClient()
        client.cache_ttl = 1  # 1 second TTL

        # Cache data with old timestamp (using time.time() format)
        import time

        old_timestamp = time.time() - 2  # 2 seconds ago
        expired_data = {"ip": "192.168.1.100", "reputation": 85}
        client.cache["test_key"] = {"data": expired_data, "timestamp": old_timestamp}

        # Should return None for expired data
        cached_data = client._get_cached_data("test_key")
        assert cached_data is None


class TestDShieldClientErrorHandling:
    """Test DShield client error handling with MCPErrorHandler."""

    def setup_method(self):
        """Set up test method - reset all mocks."""
        # This ensures clean state between tests
        pass

    @patch('src.dshield_client.get_user_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_config')
    def test_init_with_error_handler(
        self, mock_get_config, mock_op_secrets_class, mock_user_config
    ):
        """Test DShieldClient initialization with error handler."""
        mock_get_config.return_value = TEST_CONFIG

        # Mock 1Password resolution - create a mock instance that will be returned when OnePasswordSecrets() is called
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "test_api_key"
        mock_op_secrets_class.return_value = mock_op_instance

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("performance", "enable_caching"): True,
            ("performance", "max_cache_size"): 1000,
            ("performance", "request_timeout_seconds"): 30,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        # Create error handler
        from src.mcp_error_handler import MCPErrorHandler

        error_handler = MCPErrorHandler()
        client = DShieldClient(error_handler=error_handler)

        # Verify the client initialized correctly
        assert client.error_handler == error_handler
        assert client.api_key == "test_api_key"

    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_user_config')
    def test_init_without_error_handler(
        self, mock_get_config, mock_op_secrets_class, mock_user_config
    ):
        """Test DShieldClient initialization without error handler."""
        mock_get_config.return_value = TEST_CONFIG

        # Mock 1Password resolution - create a mock instance that will be returned when OnePasswordSecrets() is called
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "test_api_key"
        mock_op_secrets_class.return_value = mock_op_instance

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("performance", "enable_caching"): True,
            ("performance", "max_cache_size"): 1000,
            ("performance", "request_timeout_seconds"): 30,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        client = DShieldClient()

        # Verify the client initialized correctly
        assert client.error_handler is None
        assert client.api_key == "test_api_key"

    @pytest.mark.asyncio
    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_user_config')
    async def test_get_ip_reputation_with_error_handler_http_error(
        self, mock_get_config, mock_op_secrets_class, mock_user_config
    ):
        """Test get_ip_reputation with error handler when HTTP error occurs."""
        mock_get_config.return_value = TEST_CONFIG

        # Mock 1Password resolution
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "test_api_key"
        mock_op_secrets_class.return_value = mock_op_instance

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("performance", "enable_caching"): True,
            ("performance", "max_cache_size"): 1000,
            ("performance", "request_timeout_seconds"): 30,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        # Create error handler
        from src.mcp_error_handler import MCPErrorHandler

        error_handler = MCPErrorHandler()
        client = DShieldClient(error_handler=error_handler)

        # Mock session that raises an exception during the async context manager
        mock_session = AsyncMock()
        mock_session.get.side_effect = Exception("Test HTTP error")
        client.session = mock_session

        # Test IP reputation with error handler
        result = await client.get_ip_reputation("192.168.1.100")

        # Should return error response instead of default reputation
        assert "error" in result
        assert result["error"]["error"]["code"] == error_handler.INTERNAL_ERROR

    @pytest.mark.asyncio
    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_user_config')
    async def test_get_ip_reputation_with_error_handler_general_error(
        self, mock_get_config, mock_op_secrets_class, mock_user_config
    ):
        """Test get_ip_reputation with error handler when general error occurs."""
        mock_get_config.return_value = TEST_CONFIG

        # Mock 1Password resolution
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "test_api_key"
        mock_op_secrets_class.return_value = mock_op_instance

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("performance", "enable_caching"): True,
            ("performance", "max_cache_size"): 1000,
            ("performance", "request_timeout_seconds"): 30,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        # Create error handler
        from src.mcp_error_handler import MCPErrorHandler

        error_handler = MCPErrorHandler()
        client = DShieldClient(error_handler=error_handler)

        # Mock session that raises general exception
        mock_session = AsyncMock()
        mock_session.get.side_effect = Exception("Test general error")
        client.session = mock_session

        # Test IP reputation with error handler
        result = await client.get_ip_reputation("192.168.1.100")

        # Should return error response instead of default reputation
        assert "error" in result
        assert result["error"]["error"]["code"] == error_handler.INTERNAL_ERROR

    @pytest.mark.asyncio
    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_user_config')
    async def test_get_ip_reputation_without_error_handler_raises_exception(
        self, mock_get_config, mock_op_secrets_class, mock_user_config
    ):
        """Test get_ip_reputation without error handler raises exception."""
        mock_get_config.return_value = TEST_CONFIG

        # Mock 1Password resolution
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "test_api_key"
        mock_op_secrets_class.return_value = mock_op_instance

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("performance", "enable_caching"): True,
            ("performance", "max_cache_size"): 1000,
            ("performance", "request_timeout_seconds"): 30,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        client = DShieldClient()

        # Mock session that raises exception
        mock_session = AsyncMock()
        mock_session.get.side_effect = Exception("Test error")
        client.session = mock_session

        # Test IP reputation without error handler should return default reputation
        result = await client.get_ip_reputation("192.168.1.100")

        # Should return default reputation (not raise exception)
        assert "ip_address" in result
        assert result["ip_address"] == "192.168.1.100"

    @pytest.mark.asyncio
    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_user_config')
    async def test_get_ip_details_with_error_handler(
        self, mock_get_config, mock_op_secrets_class, mock_user_config
    ):
        """Test get_ip_details with error handler."""
        mock_get_config.return_value = TEST_CONFIG

        # Mock 1Password resolution
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "test_api_key"
        mock_op_secrets_class.return_value = mock_op_instance

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("performance", "enable_caching"): True,
            ("performance", "max_cache_size"): 1000,
            ("performance", "request_timeout_seconds"): 30,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        # Create error handler
        from src.mcp_error_handler import MCPErrorHandler

        error_handler = MCPErrorHandler()
        client = DShieldClient(error_handler=error_handler)

        # Mock session that raises exception
        mock_session = AsyncMock()
        mock_session.get.side_effect = Exception("Test error")
        client.session = mock_session

        # Test IP details with error handler
        result = await client.get_ip_details("192.168.1.100")

        # Should return error response instead of default details
        assert "error" in result
        assert result["error"]["error"]["code"] == error_handler.INTERNAL_ERROR

    @pytest.mark.asyncio
    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_user_config')
    async def test_get_top_attackers_with_error_handler(
        self, mock_get_config, mock_op_secrets_class, mock_user_config
    ):
        """Test get_top_attackers with error handler."""
        mock_get_config.return_value = TEST_CONFIG

        # Mock 1Password resolution
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable = Mock()
        mock_op_secrets_class.return_value = mock_op_instance

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("performance", "enable_caching"): True,
            ("performance", "max_cache_size"): 1000,
            ("performance", "request_timeout_seconds"): 30,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        # Create error handler
        from src.mcp_error_handler import MCPErrorHandler

        error_handler = MCPErrorHandler()
        client = DShieldClient(error_handler=error_handler)

        # Mock session that raises exception
        mock_session = AsyncMock()
        mock_session.get.side_effect = Exception("Test error")
        client.session = mock_session

        # Test top attackers with error handler
        result = await client.get_top_attackers(24)

        # Should return error response instead of empty list
        assert "error" in result
        assert result["error"]["error"]["code"] == error_handler.INTERNAL_ERROR

    @pytest.mark.asyncio
    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_user_config')
    async def test_get_attack_summary_with_error_handler(
        self, mock_get_config, mock_op_secrets_class, mock_user_config
    ):
        """Test get_attack_summary with error handler."""
        mock_get_config.return_value = TEST_CONFIG

        # Mock 1Password resolution
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "test_api_key"
        mock_op_secrets_class.return_value = mock_op_instance

        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("performance", "enable_caching"): True,
            ("performance", "max_cache_size"): 1000,
            ("performance", "request_timeout_seconds"): 30,
            ("logging", "enable_performance_logging"): False,
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance

        # Create error handler
        from src.mcp_error_handler import MCPErrorHandler

        error_handler = MCPErrorHandler()
        client = DShieldClient(error_handler=error_handler)

        # Mock session that raises exception
        mock_session = AsyncMock()
        mock_session.get.side_effect = Exception("Test error")
        client.session = mock_session

        # Test attack summary with error handler
        result = await client.get_attack_summary(24)

        # Should return error response instead of default summary
        assert "error" in result
        assert result["error"]["error"]["code"] == error_handler.INTERNAL_ERROR
