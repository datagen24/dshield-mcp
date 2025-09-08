"""Tests for connection manager API key policy updates.

This module tests the connection manager's integration with the new
API key storage policy and rotation functionality.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.connection_manager import ConnectionManager
from src.secrets_manager.base_secrets_manager import APIKey


class TestConnectionManagerPolicy:
    """Test cases for connection manager API key policy."""

    @pytest.fixture
    def mock_connection_manager(self) -> ConnectionManager:
        """Create a mock ConnectionManager for testing."""
        with patch("src.connection_manager.OnePasswordAPIKeyManager"):
            with patch("src.connection_manager.OnePasswordSecrets"):
                with patch("asyncio.create_task") as mock_create_task:
                    # Mock the create_task call to prevent event loop issues
                    mock_create_task.return_value = MagicMock()
                    manager = ConnectionManager()
                    manager.secrets_manager = MagicMock()
                    manager.api_keys = {}
                    manager.logger = MagicMock()
                    return manager

    @pytest.fixture
    def sample_key_data(self) -> dict:
        """Create sample key generation data."""
        return {
            "key_id": "test-key-123",
            "key_value": "dshield_test_key_value_12345",
            "name": "Test API Key",
            "created_at": datetime.now(UTC),
            "expires_at": "2025-01-01T00:00:00+00:00",
            "permissions": {"read_tools": True, "write_back": False, "admin_access": False},
            "metadata": {"test": "data"},
            "verifier": "test_verifier_hash",
            "algo_version": "sha256-v1",
            "needs_rotation": False,
            "rps_limit": 60,
        }

    @pytest.mark.asyncio
    async def test_generate_api_key_new_policy(
        self, mock_connection_manager: ConnectionManager, sample_key_data: dict
    ) -> None:
        """Test generating API key with new policy."""
        # Mock the API key generator
        with patch("src.api_key_generator.APIKeyGenerator") as mock_generator_class:
            mock_generator = MagicMock()
            mock_generator.generate_key_with_metadata.return_value = sample_key_data
            mock_generator_class.return_value = mock_generator

            # Mock successful storage
            mock_connection_manager.secrets_manager.store_api_key = AsyncMock(return_value=True)

            # Test generation
            result = await mock_connection_manager.generate_api_key(
                name="Test API Key",
                permissions={"read_tools": True},
                expiration_days=90,
                rate_limit=60,
            )

            # Verify the result
            assert result is not None
            assert result.key_id == "test-key-123"
            assert result.key_value == "dshield_test_key_value_12345"
            assert result.name == "Test API Key"
            assert result.algo_version == "sha256-v1"
            assert result.needs_rotation is False
            assert result.rps_limit == 60
            assert result.verifier == "test_verifier_hash"

            # Verify storage was called
            mock_connection_manager.secrets_manager.store_api_key.assert_called_once()

            # Verify in-memory cache was updated
            assert "dshield_test_key_value_12345" in mock_connection_manager.api_keys

    @pytest.mark.asyncio
    async def test_rotate_api_key(self, mock_connection_manager: ConnectionManager) -> None:
        """Test rotating an API key."""
        # Create existing key
        existing_key = APIKey(
            key_id="test-key-123",
            key_value="old_key_value",
            name="Test Key",
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC).replace(year=2025),
            permissions={"read_tools": True},
            metadata={},
            algo_version="sha256-v1",
            needs_rotation=True,
            rps_limit=60,
            verifier="old_verifier",
        )

        # Mock retrieval and rotation
        mock_connection_manager.secrets_manager.retrieve_api_key = AsyncMock(
            return_value=existing_key
        )
        mock_connection_manager.secrets_manager.rotate_api_key = AsyncMock(return_value=True)

        # Mock API key generator
        with patch("src.api_key_generator.APIKeyGenerator") as mock_generator_class:
            mock_generator = MagicMock()
            mock_generator.generate_key.return_value = "new_key_value"
            mock_generator.hash_key.return_value = {"hash": "new_verifier_hash"}
            mock_generator_class.return_value = mock_generator

            # Test rotation
            result = await mock_connection_manager.rotate_api_key("test-key-123")

            # Verify the result
            assert result is not None
            assert result.key_id == "test-key-123"
            assert result.key_value == "new_key_value"
            assert result.needs_rotation is False  # Should be cleared
            assert result.verifier == "new_verifier_hash"

            # Verify rotation was called
            mock_connection_manager.secrets_manager.rotate_api_key.assert_called_once_with(
                "test-key-123", "new_key_value"
            )

            # Verify cache was updated
            assert "new_key_value" in mock_connection_manager.api_keys
            assert "old_key_value" not in mock_connection_manager.api_keys

    @pytest.mark.asyncio
    async def test_rotate_api_key_not_found(
        self, mock_connection_manager: ConnectionManager
    ) -> None:
        """Test rotating a non-existent API key."""
        # Mock key not found
        mock_connection_manager.secrets_manager.retrieve_api_key = AsyncMock(return_value=None)

        # Test rotation
        result = await mock_connection_manager.rotate_api_key("non-existent-key")

        # Should return None
        assert result is None

        # Should log error
        mock_connection_manager.logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_rotate_api_key_storage_failure(
        self, mock_connection_manager: ConnectionManager
    ) -> None:
        """Test rotation when storage fails."""
        # Create existing key
        existing_key = APIKey(
            key_id="test-key-123",
            key_value="old_key_value",
            name="Test Key",
            created_at=datetime.now(UTC),
            expires_at=None,
            permissions={},
            metadata={},
        )

        # Mock retrieval success but rotation failure
        mock_connection_manager.secrets_manager.retrieve_api_key = AsyncMock(
            return_value=existing_key
        )
        mock_connection_manager.secrets_manager.rotate_api_key = AsyncMock(return_value=False)

        # Mock API key generator
        with patch("src.api_key_generator.APIKeyGenerator") as mock_generator_class:
            mock_generator = MagicMock()
            mock_generator.generate_key.return_value = "new_key_value"
            mock_generator.hash_key.return_value = {"hash": "new_verifier_hash"}
            mock_generator_class.return_value = mock_generator

            # Test rotation
            result = await mock_connection_manager.rotate_api_key("test-key-123")

            # Should return None due to storage failure
            assert result is None

            # Should log error
            mock_connection_manager.logger.error.assert_called_once()

    @pytest.mark.asyncio
    async def test_api_key_validation_with_verifier(
        self, mock_connection_manager: ConnectionManager
    ) -> None:
        """Test API key validation using verifier."""
        # Create key with verifier
        api_key = APIKey(
            key_id="test-key-123",
            key_value="test_key_value",
            name="Test Key",
            created_at=datetime.now(UTC),
            expires_at=None,
            permissions={"read_tools": True},
            metadata={},
            algo_version="sha256-v1",
            needs_rotation=False,
            rps_limit=60,
            verifier="test_verifier_hash",
        )

        # Add to cache
        mock_connection_manager.api_keys["test_key_value"] = api_key

        # Test validation
        result = await mock_connection_manager.validate_api_key("test_key_value")

        # Should return the key
        assert result is not None
        assert result.key_id == "test-key-123"
        assert result.verifier == "test_verifier_hash"

    @pytest.mark.asyncio
    async def test_api_key_validation_missing_key(
        self, mock_connection_manager: ConnectionManager
    ) -> None:
        """Test API key validation for missing key."""
        # Mock empty cache and no retrieval
        mock_connection_manager.api_keys = {}
        mock_connection_manager.api_key_manager = MagicMock()
        mock_connection_manager.api_key_manager.validate_api_key = AsyncMock(return_value=None)

        # Test validation
        result = await mock_connection_manager.validate_api_key("missing_key")

        # Should return None
        assert result is None

    @pytest.mark.asyncio
    async def test_api_key_validation_expired_key(
        self, mock_connection_manager: ConnectionManager
    ) -> None:
        """Test API key validation for expired key."""
        # Create expired key
        expired_key = APIKey(
            key_id="test-key-123",
            key_value="test_key_value",
            name="Test Key",
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC).replace(year=2020),  # Expired
            permissions={},
            metadata={},
        )

        # Add to cache
        mock_connection_manager.api_keys["test_key_value"] = expired_key

        # Test validation
        result = await mock_connection_manager.validate_api_key("test_key_value")

        # Should return None due to expiration
        assert result is None

    @pytest.mark.asyncio
    async def test_api_key_metadata_preservation(
        self, mock_connection_manager: ConnectionManager
    ) -> None:
        """Test that API key metadata is preserved during operations."""
        # Create key with specific metadata
        original_key = APIKey(
            key_id="test-key-123",
            key_value="test_key_value",
            name="Test Key",
            created_at=datetime.now(UTC),
            expires_at=None,
            permissions={"read_tools": True, "admin_access": True},
            metadata={"custom_field": "custom_value"},
            algo_version="sha256-v1",
            needs_rotation=False,
            rps_limit=120,
            verifier="test_verifier",
        )

        # Mock retrieval and rotation
        mock_connection_manager.secrets_manager.retrieve_api_key = AsyncMock(
            return_value=original_key
        )
        mock_connection_manager.secrets_manager.rotate_api_key = AsyncMock(return_value=True)

        # Mock API key generator
        with patch("src.api_key_generator.APIKeyGenerator") as mock_generator_class:
            mock_generator = MagicMock()
            mock_generator.generate_key.return_value = "new_key_value"
            mock_generator.hash_key.return_value = {"hash": "new_verifier_hash"}
            mock_generator_class.return_value = mock_generator

            # Test rotation
            result = await mock_connection_manager.rotate_api_key("test-key-123")

            # Verify metadata is preserved
            assert result is not None
            assert result.name == "Test Key"
            assert result.permissions == {"read_tools": True, "admin_access": True}
            assert result.metadata == {"custom_field": "custom_value"}
            assert result.rps_limit == 120
            assert result.algo_version == "sha256-v1"

    @pytest.mark.asyncio
    async def test_no_plaintext_logging_in_rotation(
        self, mock_connection_manager: ConnectionManager
    ) -> None:
        """Test that plaintext keys are never logged during rotation."""
        # Create existing key
        existing_key = APIKey(
            key_id="test-key-123",
            key_value="sensitive_key_value",
            name="Test Key",
            created_at=datetime.now(UTC),
            expires_at=None,
            permissions={},
            metadata={},
        )

        # Mock retrieval and rotation
        mock_connection_manager.secrets_manager.retrieve_api_key = AsyncMock(
            return_value=existing_key
        )
        mock_connection_manager.secrets_manager.rotate_api_key = AsyncMock(return_value=True)

        # Mock API key generator
        with patch("src.api_key_generator.APIKeyGenerator") as mock_generator_class:
            mock_generator = MagicMock()
            mock_generator.generate_key.return_value = "new_sensitive_key_value"
            mock_generator.hash_key.return_value = {"hash": "new_verifier_hash"}
            mock_generator_class.return_value = mock_generator

            # Test rotation
            await mock_connection_manager.rotate_api_key("test-key-123")

            # Verify no plaintext was logged
            for call in mock_connection_manager.logger.info.call_args_list:
                assert "sensitive_key_value" not in str(call)
                assert "new_sensitive_key_value" not in str(call)

            for call in mock_connection_manager.logger.error.call_args_list:
                assert "sensitive_key_value" not in str(call)
                assert "new_sensitive_key_value" not in str(call)
