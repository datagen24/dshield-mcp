"""Tests for dshield_client module."""

import pytest
from unittest.mock import Mock, patch, AsyncMock

from src.dshield_client import DShieldClient


class TestDShieldClient:
    """Test DShieldClient class."""

    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_user_config')
    def test_init(self, mock_user_config, mock_op_secrets, mock_get_config) -> None:
        """Test DShieldClient initialization."""
        mock_get_config.return_value = {
            "secrets": {
                "dshield_api_key": "test-key",
                "dshield_api_url": "https://api.dshield.org"
            }
        }
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "test-key"
        mock_op_secrets.return_value = mock_op_instance
        mock_user_config.return_value = Mock()

        client = DShieldClient()
        assert client.api_key == "test-key"
        assert client.base_url == "https://api.dshield.org"

    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_user_config')
    @pytest.mark.asyncio
    async def test_connect(self, mock_user_config, mock_op_secrets, mock_get_config) -> None:
        """Test DShieldClient connection."""
        mock_get_config.return_value = {
            "secrets": {
                "dshield_api_key": "test-key",
                "dshield_api_url": "https://api.dshield.org"
            }
        }
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "test-key"
        mock_op_secrets.return_value = mock_op_instance
        mock_user_config.return_value = Mock()

        client = DShieldClient()
        with patch('aiohttp.ClientSession') as mock_session:
            await client.connect()
            assert client.session is not None

    @patch('src.dshield_client.get_config')
    @patch('src.dshield_client.OnePasswordSecrets')
    @patch('src.dshield_client.get_user_config')
    @pytest.mark.asyncio
    async def test_get_ip_reputation(self, mock_user_config, mock_op_secrets, mock_get_config) -> None:
        """Test IP reputation retrieval."""
        mock_get_config.return_value = {
            "secrets": {
                "dshield_api_key": "test-key",
                "dshield_api_url": "https://api.dshield.org"
            }
        }
        mock_op_instance = Mock()
        mock_op_instance.resolve_environment_variable.return_value = "test-key"
        mock_op_secrets.return_value = mock_op_instance
        mock_user_config.return_value = Mock()

        client = DShieldClient()
        mock_session = AsyncMock()
        mock_response = AsyncMock()
        mock_response.json.return_value = {"ip": "192.168.1.1", "reputation": 0.8}
        mock_response.status = 200
        mock_session.get.return_value.__aenter__.return_value = mock_response
        client.session = mock_session

        result = await client.get_ip_reputation("192.168.1.1")
        assert result["ip"] == "192.168.1.1"
        assert result["reputation"] == 0.8