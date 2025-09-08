"""Tests for API key policy migration and new storage format.

This module tests the new API key storage policy that stores plaintext
in 1Password with metadata in the notes field, and includes migration
logic for existing hashed-only entries.
"""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.secrets_manager.base_secrets_manager import APIKey
from src.secrets_manager.onepassword_cli_manager import OnePasswordCLIManager


class TestAPIKeyPolicyMigration:
    """Test cases for API key policy migration."""

    @pytest.fixture
    def mock_op_manager(self) -> OnePasswordCLIManager:
        """Create a mock OnePasswordCLIManager for testing."""
        with patch.object(OnePasswordCLIManager, '_verify_op_cli'):
            manager = OnePasswordCLIManager(vault="test-vault")
            manager._run_op_command_with_retry = MagicMock()
            return manager

    @pytest.fixture
    def sample_api_key(self) -> APIKey:
        """Create a sample API key for testing."""
        return APIKey(
            key_id="test-key-123",
            key_value="dshield_test_key_value_12345",
            name="Test API Key",
            created_at=datetime.now(UTC),
            expires_at=datetime.now(UTC).replace(year=2025),
            permissions={"read_tools": True, "write_back": False, "admin_access": False},
            metadata={"test": "data"},
            algo_version="sha256-v1",
            needs_rotation=False,
            rps_limit=60,
            verifier="test_verifier_hash",
        )

    @pytest.mark.asyncio
    async def test_store_api_key_new_format(
        self, mock_op_manager: OnePasswordCLIManager, sample_api_key: APIKey
    ) -> None:
        """Test storing API key in new format with plaintext and metadata."""
        # Mock successful op command
        mock_op_manager._run_op_command_with_retry.return_value = {"success": True}

        # Test the store operation
        result = await mock_op_manager.store_api_key(sample_api_key)

        # Verify the command was called with correct format
        assert result is True
        mock_op_manager._run_op_command_with_retry.assert_called_once()

        # Get the call arguments
        call_args = mock_op_manager._run_op_command_with_retry.call_args[0][0]
        assert call_args[0] == "item"
        assert call_args[1] == "create"
        assert call_args[2] == "--vault"
        assert call_args[3] == "test-vault"

        # Parse the item data
        item_data = json.loads(call_args[4])

        # Verify the item structure
        assert item_data["title"] == "dshield-mcp-key-test-key-123"
        assert item_data["category"] == "API_CREDENTIAL"
        assert item_data["vault"]["name"] == "test-vault"
        assert "dshield-mcp" in item_data["tags"]

        # Verify fields
        fields = {field["id"]: field["value"] for field in item_data["fields"]}
        assert fields["secret"] == "dshield_test_key_value_12345"
        assert fields["name"] == "Test API Key"

        # Verify metadata in notes
        notes_data = json.loads(fields["notes"])
        assert notes_data["algo_version"] == "sha256-v1"
        assert notes_data["key_id"] == "test-key-123"
        assert (
            notes_data["permissions"]
            == '{"read_tools": true, "write_back": false, "admin_access": false}'
        )
        assert notes_data["rps_limit"] == "60"
        assert notes_data["needs_rotation"] == "false"

    @pytest.mark.asyncio
    async def test_retrieve_api_key_new_format(
        self, mock_op_manager: OnePasswordCLIManager
    ) -> None:
        """Test retrieving API key in new format."""
        # Mock 1Password response with new format
        mock_response = {
            "fields": [
                {"id": "secret", "value": "dshield_test_key_value_12345"},
                {"id": "name", "value": "Test API Key"},
                {
                    "id": "notes",
                    "value": json.dumps(
                        {
                            "algo_version": "sha256-v1",
                            "created_at": "2024-01-01T00:00:00+00:00",
                            "key_id": "test-key-123",
                            "permissions": '{"read_tools": true, "write_back": false}',
                            "rps_limit": "60",
                            "expiry": "2025-01-01T00:00:00+00:00",
                            "needs_rotation": "false",
                        }
                    ),
                },
            ]
        }
        mock_op_manager._run_op_command_with_retry.return_value = mock_response

        # Test retrieval
        result = await mock_op_manager.retrieve_api_key("test-key-123")

        # Verify the result
        assert result is not None
        assert result.key_id == "test-key-123"
        assert result.key_value == "dshield_test_key_value_12345"
        assert result.name == "Test API Key"
        assert result.algo_version == "sha256-v1"
        assert result.needs_rotation is False
        assert result.rps_limit == 60

    @pytest.mark.asyncio
    async def test_retrieve_api_key_old_format_migration(
        self, mock_op_manager: OnePasswordCLIManager
    ) -> None:
        """Test retrieving API key in old format triggers migration."""
        # Mock 1Password response with old format
        mock_response = {
            "fields": [
                {"id": "key_value", "value": "dshield_test_key_value_12345"},
                {"id": "key_name", "value": "Test API Key"},
                {"id": "permissions", "value": '{"read_tools": true, "write_back": false}'},
                {"id": "created_at", "value": "2024-01-01T00:00:00+00:00"},
                {"id": "expires_at", "value": "2025-01-01T00:00:00+00:00"},
                {"id": "metadata", "value": '{"test": "data"}'},
            ]
        }
        mock_op_manager._run_op_command_with_retry.return_value = mock_response

        # Test retrieval
        result = await mock_op_manager.retrieve_api_key("test-key-123")

        # Verify the result shows migration needed
        assert result is not None
        assert result.key_id == "test-key-123"
        assert result.key_value == "dshield_test_key_value_12345"
        assert result.name == "Test API Key"
        assert result.algo_version == "sha256-v1"
        assert result.needs_rotation is True  # Should be marked for rotation
        assert result.rps_limit == 60

    @pytest.mark.asyncio
    async def test_rotate_api_key(
        self, mock_op_manager: OnePasswordCLIManager, sample_api_key: APIKey
    ) -> None:
        """Test rotating an API key."""
        # Mock successful retrieval and rotation
        mock_op_manager.retrieve_api_key = AsyncMock(return_value=sample_api_key)
        mock_op_manager._run_op_command_with_retry.return_value = {"success": True}

        # Test rotation
        result = await mock_op_manager.rotate_api_key("test-key-123", "new_key_value")

        # Verify the result
        assert result is True
        mock_op_manager._run_op_command_with_retry.assert_called_once()

        # Verify the edit command was called
        call_args = mock_op_manager._run_op_command_with_retry.call_args[0][0]
        assert call_args[0] == "item"
        assert call_args[1] == "edit"
        assert call_args[2] == "dshield-mcp-key-test-key-123"

    @pytest.mark.asyncio
    async def test_list_api_keys_new_tag_format(
        self, mock_op_manager: OnePasswordCLIManager
    ) -> None:
        """Test listing API keys with new tag format."""
        # Mock 1Password list response
        mock_items = [
            {"title": "dshield-mcp-key-test-key-1"},
            {"title": "dshield-mcp-key-test-key-2"},
        ]
        mock_op_manager._run_op_command_with_retry.return_value = mock_items

        # Mock individual key retrieval
        mock_op_manager.retrieve_api_key = AsyncMock(
            return_value=APIKey(
                key_id="test-key-1",
                key_value="test_value_1",
                name="Test Key 1",
                created_at=datetime.now(UTC),
                expires_at=None,
                permissions={},
                metadata={},
            )
        )

        # Test listing
        await mock_op_manager.list_api_keys()

        # Verify the list command used new tag
        list_call = mock_op_manager._run_op_command_with_retry.call_args_list[0]
        assert "--tags" in list_call[0][0]
        assert "dshield-mcp" in list_call[0][0]

    def test_api_key_metadata_validation(self, sample_api_key: APIKey) -> None:
        """Test that API key metadata includes all required fields."""
        # Verify all new fields are present
        assert hasattr(sample_api_key, "algo_version")
        assert hasattr(sample_api_key, "needs_rotation")
        assert hasattr(sample_api_key, "rps_limit")
        assert hasattr(sample_api_key, "verifier")

        # Verify default values
        assert sample_api_key.algo_version == "sha256-v1"
        assert sample_api_key.needs_rotation is False
        assert sample_api_key.rps_limit == 60

    @pytest.mark.asyncio
    async def test_migration_detection_logic(self, mock_op_manager: OnePasswordCLIManager) -> None:
        """Test that migration is properly detected for old format keys."""
        # Test with old format (no secret field)
        old_format_response = {
            "fields": [
                {"id": "key_value", "value": "old_key"},
                {"id": "key_name", "value": "Old Key"},
                {"id": "permissions", "value": "{}"},
                {"id": "created_at", "value": "2024-01-01T00:00:00+00:00"},
                {"id": "expires_at", "value": ""},
                {"id": "metadata", "value": "{}"},
            ]
        }
        mock_op_manager._run_op_command_with_retry.return_value = old_format_response

        result = await mock_op_manager.retrieve_api_key("old-key")

        # Should be marked for rotation
        assert result.needs_rotation is True
        assert result.algo_version == "sha256-v1"

    @pytest.mark.asyncio
    async def test_no_plaintext_logging(
        self, mock_op_manager: OnePasswordCLIManager, sample_api_key: APIKey
    ) -> None:
        """Test that plaintext keys are never logged."""
        with patch.object(mock_op_manager, 'logger') as mock_logger:
            mock_op_manager._run_op_command_with_retry.return_value = {"success": True}

            await mock_op_manager.store_api_key(sample_api_key)

            # Verify no plaintext was logged
            for call in mock_logger.info.call_args_list:
                assert sample_api_key.key_value not in str(call)

            for call in mock_logger.error.call_args_list:
                assert sample_api_key.key_value not in str(call)

    def test_verifier_generation(self) -> None:
        """Test that verifiers are generated correctly for server-side storage."""
        from src.api_key_generator import APIKeyGenerator

        generator = APIKeyGenerator()
        key_value = "test_key_12345"

        # Generate verifier
        verifier_data = generator.hash_key(key_value)

        # Verify verifier structure
        assert "hash" in verifier_data
        assert "salt" in verifier_data
        assert "algorithm" in verifier_data
        assert verifier_data["algorithm"] == "sha256"

        # Verify verifier can be used for validation
        is_valid = generator.verify_key(key_value, verifier_data["hash"], verifier_data["salt"])
        assert is_valid is True

    @pytest.mark.asyncio
    async def test_algo_version_enforcement(self, mock_op_manager: OnePasswordCLIManager) -> None:
        """Test that algorithm version is enforced during validation."""
        # Test with unsupported version
        mock_response = {
            "fields": [
                {"id": "secret", "value": "test_key"},
                {"id": "name", "value": "Test Key"},
                {
                    "id": "notes",
                    "value": json.dumps(
                        {
                            "algo_version": "sha256-v0",  # Old version
                            "created_at": "2024-01-01T00:00:00+00:00",
                            "key_id": "test-key-123",
                            "permissions": '{}',
                            "rps_limit": "60",
                            "expiry": "",
                            "needs_rotation": "false",
                        }
                    ),
                },
            ]
        }
        mock_op_manager._run_op_command_with_retry.return_value = mock_response

        result = await mock_op_manager.retrieve_api_key("test-key-123")

        # Should be marked for rotation due to old version
        assert result.needs_rotation is True
        assert result.algo_version == "sha256-v0"
