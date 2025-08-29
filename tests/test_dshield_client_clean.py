"""
Clean DShieldClient tests with correct patch patterns for relative imports.

PATCH PATHS FOR DSHIELDCLIENT:
- OnePasswordSecrets: 'src.dshield_client.OnePasswordSecrets' 
- get_config: 'src.dshield_client.get_config'
- get_user_config: 'src.dshield_client.get_user_config'

CORRECT PATCH ORDER:
@patch('src.dshield_client.get_user_config')      # 1st patch → 1st parameter: mock_get_config
@patch('src.dshield_client.OnePasswordSecrets')   # 2nd patch → 2nd parameter: mock_op_secrets_class
@patch('src.dshield_client.get_config')           # 3rd patch → 3rd parameter: mock_user_config
def test_method(self, mock_get_config, mock_op_secrets_class, mock_user_config):
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
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
    
    @patch('src.dshield_client.get_user_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_config')
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
            ("logging", "enable_performance_logging"): False
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
    
    @patch('src.dshield_client.get_user_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_config')
    def test_init_with_op_urls(self, mock_get_config, mock_op_secrets_class, mock_user_config):
        """Test DShieldClient initialization with 1Password URLs."""
        config = dict(TEST_CONFIG)
        config["secrets"]["dshield_api_key"] = "op://vault/dshield/api-key"
        mock_get_config.return_value = config
        
        # Mock 1Password resolution
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "resolved_api_key"
        mock_op_secrets_class.return_value = mock_op_instance
        
        # Mock user config
        mock_user_config_instance = Mock()
        mock_user_config_instance.get_setting.side_effect = lambda section, key: {
            ("performance", "enable_caching"): True,
            ("performance", "max_cache_size"): 1000,
            ("performance", "request_timeout_seconds"): 30,
            ("logging", "enable_performance_logging"): False
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance
        
        client = DShieldClient()
        
        # Verify the mock was called correctly
        mock_op_secrets_class.assert_called_once()
        mock_op_instance.resolve_environment_variable.assert_called_once_with("op://vault/dshield/api-key")
        
        # Verify the client has the resolved value
        assert client.api_key == "resolved_api_key"
        assert client.headers["Authorization"] == "Bearer resolved_api_key"
    
    @patch('src.dshield_client.get_user_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_config')
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
            ("logging", "enable_performance_logging"): False
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance
        
        client = DShieldClient()
        
        assert client.api_key is None
        assert "Authorization" not in client.headers
    
    @pytest.mark.asyncio
    @patch('src.dshield_client.get_user_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_config')
    async def test_connect(self, mock_get_config, mock_op_secrets_class, mock_user_config):
        """Test DShieldClient connection."""
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
            ("logging", "enable_performance_logging"): False
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance
        
        client = DShieldClient()
        
        # Mock session
        mock_session = AsyncMock()
        client.session = mock_session
        
        await client.connect()
        
        assert client.session is not None
    
    @pytest.mark.asyncio
    @patch('src.dshield_client.get_user_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_config')
    async def test_close(self, mock_get_config, mock_op_secrets_class, mock_user_config):
        """Test DShieldClient close."""
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
            ("logging", "enable_performance_logging"): False
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance
        
        client = DShieldClient()
        
        # Mock session
        mock_session = AsyncMock()
        client.session = mock_session
        
        await client.close()
        
        assert client.session is None
        mock_session.close.assert_called_once()


class TestDShieldClientErrorHandling:
    """Test DShield client error handling with MCPErrorHandler."""
    
    @patch('src.dshield_client.get_user_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_config')
    def test_init_with_error_handler(self, mock_get_config, mock_op_secrets_class, mock_user_config):
        """Test DShieldClient initialization with error handler."""
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
            ("logging", "enable_performance_logging"): False
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance
        
        # Create error handler
        from src.mcp_error_handler import MCPErrorHandler
        error_handler = MCPErrorHandler()
        client = DShieldClient(error_handler=error_handler)
        
        # Verify the client initialized correctly
        assert client.error_handler == error_handler
        assert client.api_key == "test_api_key"
    
    @patch('src.dshield_client.get_user_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_config')
    def test_init_without_error_handler(self, mock_get_config, mock_op_secrets_class, mock_user_config):
        """Test DShieldClient initialization without error handler."""
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
            ("logging", "enable_performance_logging"): False
        }.get((section, key), None)
        mock_user_config.return_value = mock_user_config_instance
        
        client = DShieldClient()
        
        # Verify the client initialized correctly
        assert client.error_handler is None
        assert client.api_key == "test_api_key"
    
    @pytest.mark.asyncio
    @patch('src.dshield_client.get_user_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_config')
    async def test_get_ip_reputation_with_error_handler_http_error(self, mock_get_config, mock_op_secrets_class, mock_user_config):
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
            ("logging", "enable_performance_logging"): False
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
