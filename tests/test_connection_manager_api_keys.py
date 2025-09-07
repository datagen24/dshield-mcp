"""Tests for connection manager API key functionality.

This module contains tests for API key management in the connection manager,
including generation, validation, deletion, and storage operations.
"""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest
import pytest_asyncio

from src.connection_manager import APIKey, ConnectionManager


class TestConnectionManagerAPIKeys:
    """Test cases for ConnectionManager API key functionality."""

    @pytest_asyncio.fixture
    async def connection_manager(self) -> ConnectionManager:
        """Create a test connection manager."""
        config = {
            "vault": "test-vault",
            "api_key_management": {"vault": "op://test-vault/item/field"},
        }

        # Mock the 1Password CLI manager to avoid actual CLI calls
        with patch('src.connection_manager.OnePasswordAPIKeyManager') as mock_manager_class:
            mock_manager = Mock()
            mock_manager_class.return_value = mock_manager
            manager = ConnectionManager(config)
            # Wait for the async initialization to complete
            await asyncio.sleep(0.01)  # Small delay to let the task complete
            return manager

    @pytest.fixture
    def mock_api_key_manager(self) -> Mock:
        """Create a mock API key manager."""
        manager = Mock()
        manager.generate_api_key = AsyncMock()
        manager.validate_api_key = AsyncMock()
        manager.list_api_keys = AsyncMock()
        manager.delete_api_key = AsyncMock()
        return manager

    def test_api_key_init(self) -> None:
        """Test APIKey initialization."""
        key_id = "test_key_123"
        key_value = "dshield_test_key_456"
        permissions = {"read_tools": True, "write_back": False}
        expires_days = 30

        api_key = APIKey(
            key_id=key_id, key_value=key_value, permissions=permissions, expires_days=expires_days
        )

        assert api_key.key_id == key_id
        assert api_key.key_value == key_value
        assert api_key.permissions == permissions
        assert api_key.is_active is True
        assert api_key.usage_count == 0
        assert api_key.last_used is None

    def test_api_key_expiration(self) -> None:
        """Test API key expiration logic."""
        # Create an expired key
        expired_key = APIKey(
            key_id="expired",
            key_value="expired_key",
            permissions={},
            expires_days=-1,  # Expired
        )

        # Create a valid key
        valid_key = APIKey(key_id="valid", key_value="valid_key", permissions={}, expires_days=30)

        assert expired_key.is_expired() is True
        assert valid_key.is_expired() is False

    def test_api_key_validity(self) -> None:
        """Test API key validity logic."""
        # Create a valid key
        valid_key = APIKey(key_id="valid", key_value="valid_key", permissions={}, expires_days=30)

        # Create an inactive key
        inactive_key = APIKey(
            key_id="inactive", key_value="inactive_key", permissions={}, expires_days=30
        )
        inactive_key.is_active = False

        # Create an expired key
        expired_key = APIKey(
            key_id="expired", key_value="expired_key", permissions={}, expires_days=-1
        )

        assert valid_key.is_valid() is True
        assert inactive_key.is_valid() is False
        assert expired_key.is_valid() is False

    def test_api_key_usage_update(self) -> None:
        """Test API key usage statistics update."""
        api_key = APIKey(key_id="test", key_value="test_key", permissions={}, expires_days=30)

        initial_count = api_key.usage_count
        initial_last_used = api_key.last_used

        # Update usage
        api_key.update_usage()

        assert api_key.usage_count == initial_count + 1
        assert api_key.last_used is not None
        if initial_last_used is not None:
            assert api_key.last_used > initial_last_used

    def test_api_key_to_dict(self) -> None:
        """Test API key dictionary conversion."""
        api_key = APIKey(
            key_id="test_key_123",
            key_value="dshield_test_key_456",
            permissions={"read_tools": True},
            expires_days=30,
        )

        result = api_key.to_dict()

        assert isinstance(result, dict)
        assert result["key_id"] == "test_key_123"
        assert result["key_value"] == "dshield_test_key_456"[:8] + "..."
        assert result["permissions"] == {"read_tools": True}
        assert result["is_active"] is True
        assert result["is_expired"] is False
        assert result["is_valid"] is True

    @pytest.mark.asyncio
    async def test_generate_api_key_success(self, connection_manager: ConnectionManager) -> None:
        """Test successful API key generation."""
        # Mock the API key manager
        with patch.object(connection_manager, 'api_key_manager') as mock_manager:
            mock_manager.generate_api_key = AsyncMock(return_value="test_key_123")
            mock_manager.validate_api_key = AsyncMock(
                return_value={
                    "key_id": "test_id_123",
                    "permissions": {"read_tools": True},
                    "created_at": datetime.now(UTC),
                    "expires_at": datetime.now(UTC) + timedelta(days=30),
                }
            )

            # Generate API key
            result = await connection_manager.generate_api_key(
                name="Test Key", permissions={"read_tools": True}, expiration_days=30, rate_limit=60
            )

            # Verify result
            assert result is not None
            assert result.key_id == "test_id_123"
            assert result.key_value == "test_key_123"
            assert result.permissions == {"read_tools": True}

            # Verify manager was called
            mock_manager.generate_api_key.assert_called_once_with(
                name="Test Key", permissions={"read_tools": True}, expiration_days=30, rate_limit=60
            )

    @pytest.mark.asyncio
    async def test_generate_api_key_failure(self, connection_manager: ConnectionManager) -> None:
        """Test API key generation failure."""
        # Mock the API key manager to return None
        with patch.object(connection_manager, 'api_key_manager') as mock_manager:
            mock_manager.generate_api_key.return_value = None

            # Generate API key
            result = await connection_manager.generate_api_key(
                name="Test Key", permissions={"read_tools": True}
            )

            # Verify result
            assert result is None

    @pytest.mark.asyncio
    async def test_generate_api_key_exception(self, connection_manager: ConnectionManager) -> None:
        """Test API key generation with exception."""
        # Mock the API key manager to raise an exception
        with patch.object(connection_manager, 'api_key_manager') as mock_manager:
            mock_manager.generate_api_key.side_effect = Exception("Test error")

            # Generate API key
            result = await connection_manager.generate_api_key(
                name="Test Key", permissions={"read_tools": True}
            )

            # Verify result
            assert result is None

    @pytest.mark.asyncio
    async def test_validate_api_key_success(self, connection_manager: ConnectionManager) -> None:
        """Test successful API key validation."""
        # Mock the API key manager
        with patch.object(connection_manager, 'api_key_manager') as mock_manager:
            mock_manager.validate_api_key = AsyncMock(
                return_value={
                    "key_id": "test_id_123",
                    "permissions": {"read_tools": True},
                    "created_at": datetime.now(UTC),
                    "expires_at": datetime.now(UTC) + timedelta(days=30),
                }
            )

            # Validate API key
            result = await connection_manager.validate_api_key("test_key_123")

            # Verify result
            assert result is not None
            assert result.key_id == "test_id_123"
            assert result.key_value == "test_key_123"

            # Verify manager was called
            mock_manager.validate_api_key.assert_called_once_with("test_key_123")

    @pytest.mark.asyncio
    async def test_validate_api_key_not_found(self, connection_manager: ConnectionManager) -> None:
        """Test API key validation when key not found."""
        # Mock the API key manager to return None
        with patch.object(connection_manager, 'api_key_manager') as mock_manager:
            mock_manager.validate_api_key = AsyncMock(return_value=None)

            # Validate API key
            result = await connection_manager.validate_api_key("nonexistent_key")

            # Verify result
            assert result is None

    @pytest.mark.asyncio
    async def test_validate_api_key_cached(self, connection_manager: ConnectionManager) -> None:
        """Test API key validation with cached key."""
        # Create a cached API key
        cached_key = APIKey(
            key_id="cached_id",
            key_value="cached_key",
            permissions={"read_tools": True},
            expires_days=30,
        )
        connection_manager.api_keys["cached_key"] = cached_key

        # Validate API key
        result = await connection_manager.validate_api_key("cached_key")

        # Verify result
        assert result is not None
        assert result.key_id == "cached_id"
        assert result.usage_count == 1  # Should be incremented

    @pytest.mark.asyncio
    async def test_validate_api_key_expired(self, connection_manager: ConnectionManager) -> None:
        """Test API key validation with expired key."""
        # Create an expired API key
        expired_key = APIKey(
            key_id="expired_id",
            key_value="expired_key",
            permissions={"read_tools": True},
            expires_days=-1,  # Expired
        )
        connection_manager.api_keys["expired_key"] = expired_key

        # Validate API key
        result = await connection_manager.validate_api_key("expired_key")

        # Verify result
        assert result is None

    @pytest.mark.asyncio
    async def test_delete_api_key_success(self, connection_manager: ConnectionManager) -> None:
        """Test successful API key deletion."""
        # Mock the API key manager
        with patch.object(connection_manager, 'api_key_manager') as mock_manager:
            mock_manager.delete_api_key = AsyncMock(return_value=True)

            # Create a test API key in memory
            test_key = APIKey(
                key_id="test_id", key_value="test_key", permissions={}, expires_days=30
            )
            connection_manager.api_keys["test_key"] = test_key

            # Delete API key
            result = await connection_manager.delete_api_key("test_id")

            # Verify result
            assert result is True
            assert "test_key" not in connection_manager.api_keys

            # Verify manager was called
            mock_manager.delete_api_key.assert_called_once_with("test_id")

    @pytest.mark.asyncio
    async def test_delete_api_key_failure(self, connection_manager: ConnectionManager) -> None:
        """Test API key deletion failure."""
        # Mock the API key manager to return False
        with patch.object(connection_manager, 'api_key_manager') as mock_manager:
            mock_manager.delete_api_key.return_value = False

            # Delete API key
            result = await connection_manager.delete_api_key("nonexistent_id")

            # Verify result
            assert result is False

    @pytest.mark.asyncio
    async def test_delete_api_key_exception(self, connection_manager: ConnectionManager) -> None:
        """Test API key deletion with exception."""
        # Mock the API key manager to raise an exception
        with patch.object(connection_manager, 'api_key_manager') as mock_manager:
            mock_manager.delete_api_key.side_effect = Exception("Test error")

            # Delete API key
            result = await connection_manager.delete_api_key("test_id")

            # Verify result
            assert result is False

    @pytest.mark.asyncio
    async def test_revoke_api_key_success(self, connection_manager: ConnectionManager) -> None:
        """Test successful API key revocation."""
        # Create a test API key in memory
        test_key = APIKey(key_id="test_id", key_value="test_key", permissions={}, expires_days=30)
        connection_manager.api_keys["test_key"] = test_key

        # Revoke API key
        result = connection_manager.revoke_api_key("test_key")

        # Verify result
        assert result is True
        assert test_key.is_active is False

    @pytest.mark.asyncio
    async def test_revoke_api_key_not_found(self, connection_manager: ConnectionManager) -> None:
        """Test API key revocation when key not found."""
        # Revoke non-existent API key
        result = connection_manager.revoke_api_key("nonexistent_key")

        # Verify result
        assert result is False

    @pytest.mark.asyncio
    async def test_get_api_keys_info(self, connection_manager: ConnectionManager) -> None:
        """Test getting API keys information."""
        # Create test API keys
        key1 = APIKey(
            key_id="key1", key_value="value1", permissions={"read_tools": True}, expires_days=30
        )
        key2 = APIKey(
            key_id="key2", key_value="value2", permissions={"write_back": True}, expires_days=60
        )

        connection_manager.api_keys["value1"] = key1
        connection_manager.api_keys["value2"] = key2

        # Get API keys info
        result = connection_manager.get_api_keys_info()

        # Verify result
        assert len(result) == 2
        assert any(key["key_id"] == "key1" for key in result)
        assert any(key["key_id"] == "key2" for key in result)

    @pytest.mark.asyncio
    async def test_get_active_api_keys_count(self, connection_manager: ConnectionManager) -> None:
        """Test getting active API keys count."""
        # Create test API keys
        active_key = APIKey(
            key_id="active", key_value="active_key", permissions={}, expires_days=30
        )
        expired_key = APIKey(
            key_id="expired",
            key_value="expired_key",
            permissions={},
            expires_days=-1,  # Expired
        )
        inactive_key = APIKey(
            key_id="inactive", key_value="inactive_key", permissions={}, expires_days=30
        )
        inactive_key.is_active = False

        connection_manager.api_keys["active_key"] = active_key
        connection_manager.api_keys["expired_key"] = expired_key
        connection_manager.api_keys["inactive_key"] = inactive_key

        # Get active count
        count = connection_manager.get_active_api_keys_count()

        # Verify result
        assert count == 1

    @pytest.mark.asyncio
    async def test_cleanup_expired_keys(self, connection_manager: ConnectionManager) -> None:
        """Test cleanup of expired keys."""
        # Create test API keys
        active_key = APIKey(
            key_id="active", key_value="active_key", permissions={}, expires_days=30
        )
        expired_key = APIKey(
            key_id="expired",
            key_value="expired_key",
            permissions={},
            expires_days=-1,  # Expired
        )

        connection_manager.api_keys["active_key"] = active_key
        connection_manager.api_keys["expired_key"] = expired_key

        # Cleanup expired keys
        cleaned_count = connection_manager.cleanup_expired_keys()

        # Verify result
        assert cleaned_count == 1
        assert "active_key" in connection_manager.api_keys
        assert "expired_key" not in connection_manager.api_keys

    @pytest.mark.asyncio
    async def test_get_statistics(self, connection_manager: ConnectionManager) -> None:
        """Test getting connection manager statistics."""
        # Create test API keys
        active_key = APIKey(
            key_id="active", key_value="active_key", permissions={}, expires_days=30
        )
        expired_key = APIKey(
            key_id="expired",
            key_value="expired_key",
            permissions={},
            expires_days=-1,  # Expired
        )

        connection_manager.api_keys["active_key"] = active_key
        connection_manager.api_keys["expired_key"] = expired_key

        # Get statistics
        stats = connection_manager.get_statistics()

        # Verify result
        assert isinstance(stats, dict)
        assert "connections" in stats
        assert "api_keys" in stats
        assert "last_cleanup" in stats

        assert stats["api_keys"]["total"] == 2
        assert stats["api_keys"]["active"] == 1
        assert stats["api_keys"]["expired"] == 1

    @pytest.mark.asyncio
    async def test_load_api_keys(self, connection_manager: ConnectionManager) -> None:
        """Test loading API keys from 1Password."""
        # Mock the API key manager
        with patch.object(connection_manager, 'api_key_manager') as mock_manager:
            mock_manager.list_api_keys = AsyncMock(
                return_value=[
                    {
                        "key_id": "loaded_id",
                        "permissions": {"read_tools": True},
                        "created_at": datetime.now(UTC).isoformat(),
                        "expires_at": (datetime.now(UTC) + timedelta(days=30)).isoformat(),
                    }
                ]
            )

            # Load API keys
            await connection_manager._load_api_keys()

            # Verify API key was loaded
            assert len(connection_manager.api_keys) == 1
            assert "loaded_id" in [key.key_id for key in connection_manager.api_keys.values()]

            # Verify manager was called
            mock_manager.list_api_keys.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_api_keys_exception(self, connection_manager: ConnectionManager) -> None:
        """Test loading API keys with exception."""
        # Mock the API key manager to raise an exception
        with patch.object(connection_manager, 'api_key_manager') as mock_manager:
            mock_manager.list_api_keys.side_effect = Exception("Test error")

            # Load API keys
            await connection_manager._load_api_keys()

            # Verify no keys were loaded
            assert len(connection_manager.api_keys) == 0
