"""Integration tests for API key persistence and management."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.connection_manager import ConnectionManager
from src.op_secrets import OnePasswordAPIKeyManager
from src.secrets_manager.base_secrets_manager import APIKey


class TestAPIKeyPersistence:
    """Integration tests for API key persistence across system components."""

    @pytest.fixture
    def mock_secrets_manager(self) -> Mock:
        """Create a mock secrets manager for testing."""
        manager = Mock()
        manager.store_api_key = AsyncMock(return_value=True)
        manager.retrieve_api_key = AsyncMock(return_value=None)
        manager.list_api_keys = AsyncMock(return_value=[])
        manager.delete_api_key = AsyncMock(return_value=True)
        manager.update_api_key = AsyncMock(return_value=True)
        manager.health_check = AsyncMock(return_value=True)
        return manager

    @pytest.fixture
    def api_key_manager(self, mock_secrets_manager: Mock) -> OnePasswordAPIKeyManager:
        """Create an API key manager with mocked secrets manager."""
        with patch('src.op_secrets.OnePasswordCLIManager') as mock_cli_manager:
            mock_cli_manager.return_value = mock_secrets_manager
            return OnePasswordAPIKeyManager("test-vault")

    @pytest.fixture
    def connection_manager(self, mock_secrets_manager: Mock) -> ConnectionManager:
        """Create a connection manager with mocked secrets manager."""
        with patch('src.connection_manager.OnePasswordCLIManager') as mock_cli_manager:
            mock_cli_manager.return_value = mock_secrets_manager
            return ConnectionManager({"vault": "test-vault"})

    @pytest.fixture
    def sample_api_key(self) -> APIKey:
        """Create a sample API key for testing."""
        now = datetime.utcnow()
        expires_at = now + timedelta(days=30)

        return APIKey(
            key_id="test_key_123",
            key_value="test_key_value",
            name="Test Key",
            created_at=now,
            expires_at=expires_at,
            permissions={"read": True, "write": False},
            metadata={"test": True},
        )

    @pytest.mark.asyncio
    async def test_api_key_generation_and_storage(
        self, api_key_manager: OnePasswordAPIKeyManager, mock_secrets_manager: Mock
    ) -> None:
        """Test API key generation and storage in 1Password."""
        # Mock the secrets manager to return a stored key
        mock_secrets_manager.store_api_key.return_value = True

        # Generate an API key
        key_value = await api_key_manager.generate_api_key(
            name="Test Key",
            permissions={"read": True, "write": False},
            expiration_days=30,
            rate_limit=60,
        )

        # Verify the key was generated
        assert key_value is not None
        assert key_value.startswith("dshield_")

        # Verify the secrets manager was called
        mock_secrets_manager.store_api_key.assert_called_once()
        stored_key = mock_secrets_manager.store_api_key.call_args[0][0]
        assert isinstance(stored_key, APIKey)
        assert stored_key.name == "Test Key"
        assert stored_key.permissions["read"] is True
        assert stored_key.permissions["write"] is False

    @pytest.mark.asyncio
    async def test_api_key_validation_and_retrieval(
        self,
        api_key_manager: OnePasswordAPIKeyManager,
        mock_secrets_manager: Mock,
        sample_api_key: APIKey,
    ) -> None:
        """Test API key validation and retrieval from 1Password."""
        # Mock the secrets manager to return the sample key
        mock_secrets_manager.list_api_keys.return_value = [sample_api_key]

        # Validate the API key
        key_info = await api_key_manager.validate_api_key(sample_api_key.key_value)

        # Verify the key was validated
        assert key_info is not None
        assert key_info["key_id"] == sample_api_key.key_id
        assert key_info["name"] == sample_api_key.name
        assert key_info["permissions"] == sample_api_key.permissions

        # Verify the secrets manager was called
        mock_secrets_manager.list_api_keys.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_key_deletion(
        self, api_key_manager: OnePasswordAPIKeyManager, mock_secrets_manager: Mock
    ) -> None:
        """Test API key deletion from 1Password."""
        # Delete an API key
        result = await api_key_manager.delete_api_key("test_key_123")

        # Verify the deletion was successful
        assert result is True

        # Verify the secrets manager was called
        mock_secrets_manager.delete_api_key.assert_called_once_with("test_key_123")

    @pytest.mark.asyncio
    async def test_connection_manager_integration(
        self, connection_manager: ConnectionManager, mock_secrets_manager: Mock
    ) -> None:
        """Test connection manager integration with API key management."""
        # Mock the secrets manager to return a stored key
        mock_secrets_manager.store_api_key.return_value = True

        # Generate an API key through the connection manager
        api_key = await connection_manager.generate_api_key(
            name="Connection Test Key",
            permissions={"read": True, "admin_access": True},
            expiration_days=90,
            rate_limit=120,
        )

        # Verify the key was generated
        assert api_key is not None
        assert api_key.name == "Connection Test Key"
        assert api_key.permissions["read"] is True
        assert api_key.permissions["admin_access"] is True

        # Verify the secrets manager was called
        mock_secrets_manager.store_api_key.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_key_validation_in_connection_manager(
        self,
        connection_manager: ConnectionManager,
        mock_secrets_manager: Mock,
        sample_api_key: APIKey,
    ) -> None:
        """Test API key validation in connection manager."""
        # Mock the secrets manager to return the sample key
        mock_secrets_manager.list_api_keys.return_value = [sample_api_key]

        # Validate the API key
        validated_key = await connection_manager.validate_api_key(sample_api_key.key_value)

        # Verify the key was validated
        assert validated_key is not None
        assert validated_key.key_id == sample_api_key.key_id
        assert validated_key.key_value == sample_api_key.key_value

        # Verify the secrets manager was called
        mock_secrets_manager.list_api_keys.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_key_deletion_in_connection_manager(
        self, connection_manager: ConnectionManager, mock_secrets_manager: Mock
    ) -> None:
        """Test API key deletion in connection manager."""
        # Delete an API key
        result = await connection_manager.delete_api_key("test_key_123")

        # Verify the deletion was successful
        assert result is True

        # Verify the secrets manager was called
        mock_secrets_manager.delete_api_key.assert_called_once_with("test_key_123")

    @pytest.mark.asyncio
    async def test_api_key_expiration_handling(
        self, api_key_manager: OnePasswordAPIKeyManager, mock_secrets_manager: Mock
    ) -> None:
        """Test handling of expired API keys."""
        # Create an expired API key
        expired_key = APIKey(
            key_id="expired_key_123",
            key_value="expired_key_value",
            name="Expired Key",
            created_at=datetime.utcnow() - timedelta(days=100),
            expires_at=datetime.utcnow() - timedelta(days=1),  # Expired yesterday
            permissions={"read": True},
            metadata={},
        )

        # Mock the secrets manager to return the expired key
        mock_secrets_manager.list_api_keys.return_value = [expired_key]

        # Try to validate the expired key
        key_info = await api_key_manager.validate_api_key(expired_key.key_value)

        # Verify the expired key was rejected
        assert key_info is None

        # Verify the secrets manager was called
        mock_secrets_manager.list_api_keys.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_key_listing(
        self,
        api_key_manager: OnePasswordAPIKeyManager,
        mock_secrets_manager: Mock,
        sample_api_key: APIKey,
    ) -> None:
        """Test API key listing functionality."""
        # Create multiple API keys
        key1 = sample_api_key
        key2 = APIKey(
            key_id="test_key_456",
            key_value="test_key_value_2",
            name="Another Test Key",
            created_at=datetime.utcnow(),
            expires_at=None,
            permissions={"read": True, "write": True},
            metadata={},
        )

        # Mock the secrets manager to return both keys
        mock_secrets_manager.list_api_keys.return_value = [key1, key2]

        # List all API keys
        keys = await api_key_manager.list_api_keys()

        # Verify both keys were returned
        assert len(keys) == 2

        key_names = [key["name"] for key in keys]
        assert "Test Key" in key_names
        assert "Another Test Key" in key_names

        # Verify the secrets manager was called
        mock_secrets_manager.list_api_keys.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_integration(
        self, api_key_manager: OnePasswordAPIKeyManager, mock_secrets_manager: Mock
    ) -> None:
        """Test health check integration."""
        # Test healthy state
        mock_secrets_manager.health_check.return_value = True

        result = await api_key_manager.health_check()

        assert result is True
        mock_secrets_manager.health_check.assert_called_once()

        # Test unhealthy state
        mock_secrets_manager.health_check.return_value = False

        result = await api_key_manager.health_check()

        assert result is False
        assert mock_secrets_manager.health_check.call_count == 2

    @pytest.mark.asyncio
    async def test_error_handling_in_api_key_generation(
        self, api_key_manager: OnePasswordAPIKeyManager, mock_secrets_manager: Mock
    ) -> None:
        """Test error handling in API key generation."""
        # Mock the secrets manager to fail
        mock_secrets_manager.store_api_key.return_value = False

        # Try to generate an API key
        key_value = await api_key_manager.generate_api_key(
            name="Test Key", permissions={"read": True}, expiration_days=30
        )

        # Verify the generation failed
        assert key_value is None

        # Verify the secrets manager was called
        mock_secrets_manager.store_api_key.assert_called_once()

    @pytest.mark.asyncio
    async def test_error_handling_in_api_key_deletion(
        self, api_key_manager: OnePasswordAPIKeyManager, mock_secrets_manager: Mock
    ) -> None:
        """Test error handling in API key deletion."""
        # Mock the secrets manager to fail
        mock_secrets_manager.delete_api_key.return_value = False

        # Try to delete an API key
        result = await api_key_manager.delete_api_key("test_key_123")

        # Verify the deletion failed
        assert result is False

        # Verify the secrets manager was called
        mock_secrets_manager.delete_api_key.assert_called_once_with("test_key_123")
