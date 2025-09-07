"""Tests for OnePassword CLI manager implementation.

This module contains comprehensive tests for the OnePasswordCLIManager class,
covering all error paths, success scenarios, and edge cases.
"""

import os
import subprocess
from datetime import UTC, datetime
from unittest.mock import Mock, patch

import pytest

from src.secrets_manager.base_secrets_manager import (
    APIKey,
    BackendUnavailableError,
    InvalidReferenceError,
    PermissionDeniedError,
    RateLimitedError,
    SecretNotFoundError,
    SecretReference,
    SecretsManagerError,
)
from src.secrets_manager.onepassword_cli_manager import OnePasswordCLIManager


class TestOnePasswordCLIManager:
    """Test cases for OnePasswordCLIManager."""

    @pytest.fixture
    def manager(self) -> OnePasswordCLIManager:
        """Create a OnePasswordCLIManager instance for testing."""
        with patch.object(OnePasswordCLIManager, '_verify_op_cli'):
            return OnePasswordCLIManager(vault="test-vault")

    @pytest.fixture
    def sample_api_key(self) -> APIKey:
        """Create a sample API key for testing."""
        return APIKey(
            key_id="test-key-123",
            key_value="test-api-key-value",
            name="Test API Key",
            created_at=datetime.now(UTC),
            expires_at=None,
            permissions={"read": True, "write": False},
            metadata={"environment": "test"},
        )

    @pytest.fixture
    def sample_op_item(self) -> dict:
        """Create a sample 1Password item response."""
        return {
            "id": "test-item-id",
            "title": "dshield-mcp-key-test-key-123",
            "vault": {"id": "test-vault-id", "name": "test-vault"},
            "fields": [
                {
                    "id": "key_value",
                    "type": "CONCEALED",
                    "value": "test-api-key-value",
                    "label": "API Key Value",
                },
                {
                    "id": "key_name",
                    "type": "STRING",
                    "value": "Test API Key",
                    "label": "Key Name",
                },
                {
                    "id": "permissions",
                    "type": "STRING",
                    "value": '{"read": true, "write": false}',
                    "label": "Permissions",
                },
                {
                    "id": "created_at",
                    "type": "STRING",
                    "value": datetime.now(UTC).isoformat(),
                    "label": "Created At",
                },
                {
                    "id": "expires_at",
                    "type": "STRING",
                    "value": "",
                    "label": "Expires At",
                },
                {
                    "id": "metadata",
                    "type": "STRING",
                    "value": '{"environment": "test"}',
                    "label": "Metadata",
                },
            ],
        }

    def test_init_with_defaults(self) -> None:
        """Test initialization with default parameters."""
        with patch.object(OnePasswordCLIManager, '_verify_op_cli'):
            manager = OnePasswordCLIManager(vault="test-vault")
            assert manager.vault == "test-vault"
            assert manager.timeout_seconds == 30
            assert manager.max_retries == 3
            assert manager.retry_delay_seconds == 1.0
            assert manager.enable_metrics is True

    def test_init_with_custom_params(self) -> None:
        """Test initialization with custom parameters."""
        with patch.object(OnePasswordCLIManager, '_verify_op_cli'):
            manager = OnePasswordCLIManager(
                vault="custom-vault",
                timeout_seconds=60,
                max_retries=5,
                retry_delay_seconds=2.0,
                enable_metrics=False,
            )
            assert manager.vault == "custom-vault"
            assert manager.timeout_seconds == 60
            assert manager.max_retries == 5
            assert manager.retry_delay_seconds == 2.0
            assert manager.enable_metrics is False

    def test_discover_session_with_existing_session(self, manager: OnePasswordCLIManager) -> None:
        """Test session discovery with existing OP_SESSION_* environment variable."""
        with patch.dict(os.environ, {"OP_SESSION_test": "test-session-token"}):
            with patch.object(
                manager, '_run_op_command_sync', return_value={"expires_at": "2024-12-31T23:59:59Z"}
            ):
                manager._discover_session()
                assert manager._session_token == "test-session-token"
                assert manager._session_expires_at is not None

    def test_discover_session_without_session(self, manager: OnePasswordCLIManager) -> None:
        """Test session discovery without existing session."""
        with patch.dict(os.environ, {}, clear=True):
            manager._discover_session()
            assert manager._session_token is None
            assert manager._session_expires_at is None

    def test_is_session_valid_with_valid_session(self, manager: OnePasswordCLIManager) -> None:
        """Test session validation with valid session."""
        manager._session_token = "test-token"
        manager._session_expires_at = datetime.now(UTC).replace(hour=23, minute=59, second=59)
        assert manager._is_session_valid() is True

    def test_is_session_valid_with_expired_session(self, manager: OnePasswordCLIManager) -> None:
        """Test session validation with expired session."""
        manager._session_token = "test-token"
        manager._session_expires_at = datetime.now(UTC).replace(hour=0, minute=0, second=0)
        assert manager._is_session_valid() is False

    def test_is_session_valid_without_token(self, manager: OnePasswordCLIManager) -> None:
        """Test session validation without token."""
        manager._session_token = None
        assert manager._is_session_valid() is False

    def test_redact_sensitive_args(self, manager: OnePasswordCLIManager) -> None:
        """Test redaction of sensitive command arguments."""
        cmd = ["op", "item", "get", "test-item", "--session", "secret-token"]
        redacted = manager._redact_sensitive_args(cmd)
        assert redacted == ["op", "item", "get", "test-item", "--session", "[REDACTED]"]

    def test_redact_sensitive_args_with_equals(self, manager: OnePasswordCLIManager) -> None:
        """Test redaction of sensitive command arguments with equals sign."""
        cmd = ["op", "item", "get", "test-item", "--session=secret-token"]
        redacted = manager._redact_sensitive_args(cmd)
        assert redacted == ["op", "item", "get", "test-item", "--session=[REDACTED]"]

    def test_map_op_error_not_found(self, manager: OnePasswordCLIManager) -> None:
        """Test error mapping for not found errors."""
        error = manager._map_op_error(1, "item not found")
        assert isinstance(error, SecretNotFoundError)
        assert "not found" in str(error)

    def test_map_op_error_permission_denied(self, manager: OnePasswordCLIManager) -> None:
        """Test error mapping for permission denied errors."""
        error = manager._map_op_error(1, "permission denied")
        assert isinstance(error, PermissionDeniedError)
        assert "Permission denied" in str(error)

    def test_map_op_error_rate_limited(self, manager: OnePasswordCLIManager) -> None:
        """Test error mapping for rate limit errors."""
        error = manager._map_op_error(1, "rate limit exceeded")
        assert isinstance(error, RateLimitedError)
        assert "Rate limited" in str(error)

    def test_map_op_error_session_expired(self, manager: OnePasswordCLIManager) -> None:
        """Test error mapping for session expired errors."""
        error = manager._map_op_error(1, "session expired")
        assert isinstance(error, PermissionDeniedError)
        assert "Session expired" in str(error)

    def test_map_op_error_authentication_failed(self, manager: OnePasswordCLIManager) -> None:
        """Test error mapping for authentication failed errors."""
        error = manager._map_op_error(2, "authentication failed")
        assert isinstance(error, PermissionDeniedError)
        assert "Authentication failed" in str(error)

    def test_map_op_error_service_unavailable(self, manager: OnePasswordCLIManager) -> None:
        """Test error mapping for service unavailable errors."""
        error = manager._map_op_error(3, "service unavailable")
        assert isinstance(error, BackendUnavailableError)
        assert "Service unavailable" in str(error)

    def test_map_op_error_unknown(self, manager: OnePasswordCLIManager) -> None:
        """Test error mapping for unknown errors."""
        error = manager._map_op_error(99, "unknown error")
        assert error is None

    def test_validate_op_output_dict(self, manager: OnePasswordCLIManager) -> None:
        """Test output validation for dict output."""
        output = {"fields": []}
        manager._validate_op_output(output, ["item", "get"])
        # Should not raise

    def test_validate_op_output_list(self, manager: OnePasswordCLIManager) -> None:
        """Test output validation for list output."""
        output = [{"id": "item1"}, {"id": "item2"}]
        manager._validate_op_output(output, ["item", "list"])
        # Should not raise

    def test_validate_op_output_invalid_type(self, manager: OnePasswordCLIManager) -> None:
        """Test output validation for invalid output type."""
        with pytest.raises(SecretsManagerError, match="Invalid op CLI output format"):
            manager._validate_op_output("invalid", ["item", "get"])

    def test_update_metrics_success(self, manager: OnePasswordCLIManager) -> None:
        """Test metrics update for successful operation."""
        manager._update_metrics(100.0, True)
        assert manager._metrics["successful_operations"] == 1
        assert manager._metrics["total_latency_ms"] == 100.0

    def test_update_metrics_failure(self, manager: OnePasswordCLIManager) -> None:
        """Test metrics update for failed operation."""
        manager._update_metrics(50.0, False)
        assert manager._metrics["failed_operations"] == 1
        assert manager._metrics["total_latency_ms"] == 50.0

    def test_get_metrics(self, manager: OnePasswordCLIManager) -> None:
        """Test getting metrics."""
        manager._update_metrics(100.0, True)
        manager._update_metrics(200.0, True)
        metrics = manager.get_metrics()
        assert metrics["successful_operations"] == 2
        assert metrics["average_latency_ms"] == 150.0

    def test_reset_metrics(self, manager: OnePasswordCLIManager) -> None:
        """Test resetting metrics."""
        manager._update_metrics(100.0, True)
        manager.reset_metrics()
        assert manager._metrics["successful_operations"] == 0
        assert manager._metrics["failed_operations"] == 0

    def test_should_retry_rate_limited(self, manager: OnePasswordCLIManager) -> None:
        """Test retry decision for rate limited error."""
        error = RateLimitedError("Rate limited")
        assert manager._should_retry(error) is True

    def test_should_retry_backend_unavailable(self, manager: OnePasswordCLIManager) -> None:
        """Test retry decision for backend unavailable error."""
        error = BackendUnavailableError("Backend unavailable")
        assert manager._should_retry(error) is True

    def test_should_retry_other_errors(self, manager: OnePasswordCLIManager) -> None:
        """Test retry decision for other error types."""
        error = SecretNotFoundError("Not found")
        assert manager._should_retry(error) is False

    @pytest.mark.asyncio
    async def test_store_api_key_success(
        self, manager: OnePasswordCLIManager, sample_api_key: APIKey
    ) -> None:
        """Test successful API key storage."""
        with patch.object(
            manager, '_run_op_command_with_retry', return_value={"id": "test-item-id"}
        ):
            result = await manager.store_api_key(sample_api_key)
            assert result is True

    @pytest.mark.asyncio
    async def test_store_api_key_failure(
        self, manager: OnePasswordCLIManager, sample_api_key: APIKey
    ) -> None:
        """Test failed API key storage."""
        with patch.object(manager, '_run_op_command_with_retry', return_value=None):
            result = await manager.store_api_key(sample_api_key)
            assert result is False

    @pytest.mark.asyncio
    async def test_store_api_key_permission_denied(
        self, manager: OnePasswordCLIManager, sample_api_key: APIKey
    ) -> None:
        """Test API key storage with permission denied error."""
        with patch.object(
            manager,
            '_run_op_command_with_retry',
            side_effect=PermissionDeniedError("Permission denied"),
        ):
            with pytest.raises(PermissionDeniedError):
                await manager.store_api_key(sample_api_key)

    @pytest.mark.asyncio
    async def test_retrieve_api_key_success(
        self, manager: OnePasswordCLIManager, sample_op_item: dict
    ) -> None:
        """Test successful API key retrieval."""
        with patch.object(manager, '_run_op_command_with_retry', return_value=sample_op_item):
            result = await manager.retrieve_api_key("test-key-123")
            assert result is not None
            assert result.key_id == "test-key-123"
            assert result.key_value == "test-api-key-value"

    @pytest.mark.asyncio
    async def test_retrieve_api_key_not_found(self, manager: OnePasswordCLIManager) -> None:
        """Test API key retrieval when not found."""
        with patch.object(manager, '_run_op_command_with_retry', return_value=None):
            with pytest.raises(SecretNotFoundError):
                await manager.retrieve_api_key("nonexistent-key")

    @pytest.mark.asyncio
    async def test_retrieve_api_key_permission_denied(self, manager: OnePasswordCLIManager) -> None:
        """Test API key retrieval with permission denied error."""
        with patch.object(
            manager,
            '_run_op_command_with_retry',
            side_effect=PermissionDeniedError("Permission denied"),
        ):
            with pytest.raises(PermissionDeniedError):
                await manager.retrieve_api_key("test-key-123")

    @pytest.mark.asyncio
    async def test_list_api_keys_success(
        self, manager: OnePasswordCLIManager, sample_op_item: dict
    ) -> None:
        """Test successful API key listing."""
        items = [{"title": "dshield-mcp-key-test-key-123", "id": "test-item-id"}]
        with patch.object(manager, '_run_op_command_with_retry', return_value=items):
            with patch.object(
                manager,
                'retrieve_api_key',
                return_value=APIKey(
                    key_id="test-key-123",
                    key_value="test-value",
                    name="Test Key",
                    created_at=datetime.now(UTC),
                    expires_at=None,
                    permissions={},
                    metadata={},
                ),
            ):
                result = await manager.list_api_keys()
                assert len(result) == 1
                assert result[0].key_id == "test-key-123"

    @pytest.mark.asyncio
    async def test_list_api_keys_permission_denied(self, manager: OnePasswordCLIManager) -> None:
        """Test API key listing with permission denied error."""
        with patch.object(
            manager,
            '_run_op_command_with_retry',
            side_effect=PermissionDeniedError("Permission denied"),
        ):
            with pytest.raises(PermissionDeniedError):
                await manager.list_api_keys()

    @pytest.mark.asyncio
    async def test_delete_api_key_success(self, manager: OnePasswordCLIManager) -> None:
        """Test successful API key deletion."""
        with patch.object(
            manager, '_run_op_command_with_retry', return_value={"id": "deleted-item-id"}
        ):
            result = await manager.delete_api_key("test-key-123")
            assert result is True

    @pytest.mark.asyncio
    async def test_delete_api_key_failure(self, manager: OnePasswordCLIManager) -> None:
        """Test failed API key deletion."""
        with patch.object(manager, '_run_op_command_with_retry', return_value=None):
            result = await manager.delete_api_key("test-key-123")
            assert result is False

    @pytest.mark.asyncio
    async def test_delete_api_key_not_found(self, manager: OnePasswordCLIManager) -> None:
        """Test API key deletion when not found."""
        with patch.object(
            manager, '_run_op_command_with_retry', side_effect=SecretNotFoundError("Not found")
        ):
            with pytest.raises(SecretNotFoundError):
                await manager.delete_api_key("nonexistent-key")

    @pytest.mark.asyncio
    async def test_update_api_key_success(
        self, manager: OnePasswordCLIManager, sample_api_key: APIKey
    ) -> None:
        """Test successful API key update."""
        with patch.object(manager, 'delete_api_key', return_value=True):
            with patch.object(manager, 'store_api_key', return_value=True):
                result = await manager.update_api_key(sample_api_key)
                assert result is True

    @pytest.mark.asyncio
    async def test_update_api_key_delete_fails(
        self, manager: OnePasswordCLIManager, sample_api_key: APIKey
    ) -> None:
        """Test API key update when delete fails."""
        with patch.object(manager, 'delete_api_key', side_effect=SecretNotFoundError("Not found")):
            with pytest.raises(SecretNotFoundError):
                await manager.update_api_key(sample_api_key)

    @pytest.mark.asyncio
    async def test_health_check_success(self, manager: OnePasswordCLIManager) -> None:
        """Test successful health check."""
        with patch.object(manager, '_run_op_command_with_retry', return_value=[]):
            result = await manager.health_check()
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, manager: OnePasswordCLIManager) -> None:
        """Test failed health check."""
        with patch.object(
            manager,
            '_run_op_command_with_retry',
            side_effect=BackendUnavailableError("Unavailable"),
        ):
            with pytest.raises(BackendUnavailableError):
                await manager.health_check()

    @pytest.mark.asyncio
    async def test_get_secret_by_reference_success(self, manager: OnePasswordCLIManager) -> None:
        """Test successful secret retrieval by reference."""
        reference = SecretReference(uri="op://test-vault/test-item/password")
        with patch.object(manager, '_run_op_command_with_retry', return_value="secret-value"):
            result = await manager._get_secret_by_reference_impl(reference)
            assert result == "secret-value"

    @pytest.mark.asyncio
    async def test_get_secret_by_reference_unsupported_backend(
        self, manager: OnePasswordCLIManager
    ) -> None:
        """Test secret retrieval with unsupported backend."""
        reference = SecretReference(uri="vault://test-path")
        with pytest.raises(InvalidReferenceError, match="Unsupported backend"):
            await manager._get_secret_by_reference_impl(reference)

    @pytest.mark.asyncio
    async def test_get_secret_by_reference_no_item(self, manager: OnePasswordCLIManager) -> None:
        """Test secret retrieval with no item specified."""
        reference = SecretReference(uri="op://test-vault/test-item")
        reference.item = None  # Simulate no item
        with pytest.raises(InvalidReferenceError, match="No item specified"):
            await manager._get_secret_by_reference_impl(reference)

    @pytest.mark.asyncio
    async def test_get_secret_by_reference_not_found(self, manager: OnePasswordCLIManager) -> None:
        """Test secret retrieval when not found."""
        reference = SecretReference(uri="op://test-vault/test-item/password")
        with patch.object(
            manager, '_run_op_command_with_retry', side_effect=SecretNotFoundError("Not found")
        ):
            with pytest.raises(SecretNotFoundError):
                await manager._get_secret_by_reference_impl(reference)

    def test_run_op_command_sync_success(self, manager: OnePasswordCLIManager) -> None:
        """Test successful op command execution."""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = '{"test": "data"}'
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            result = manager._run_op_command_sync(["item", "list"])
            assert result == {"test": "data"}

    def test_run_op_command_sync_failure(self, manager: OnePasswordCLIManager) -> None:
        """Test failed op command execution."""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "item not found"
            mock_run.return_value = mock_result

            with pytest.raises(SecretNotFoundError, match="Secret not found"):
                manager._run_op_command_sync(["item", "get", "nonexistent"])

    def test_run_op_command_sync_timeout(self, manager: OnePasswordCLIManager) -> None:
        """Test op command execution timeout."""
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired("op", 30)):
            with pytest.raises(BackendUnavailableError, match="timed out"):
                manager._run_op_command_sync(["item", "list"])

    def test_run_op_command_sync_file_not_found(self, manager: OnePasswordCLIManager) -> None:
        """Test op command execution when op CLI not found."""
        with patch('subprocess.run', side_effect=FileNotFoundError()):
            with pytest.raises(BackendUnavailableError, match="not found"):
                manager._run_op_command_sync(["item", "list"])

    def test_run_op_command_sync_invalid_json(self, manager: OnePasswordCLIManager) -> None:
        """Test op command execution with invalid JSON output."""
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "invalid json"
            mock_result.stderr = ""
            mock_run.return_value = mock_result

            with pytest.raises(SecretsManagerError, match="Failed to parse op CLI JSON output"):
                manager._run_op_command_sync(["item", "list"])

    def test_run_op_command_with_retry_success_first_attempt(
        self, manager: OnePasswordCLIManager
    ) -> None:
        """Test retry logic with success on first attempt."""
        with patch.object(
            manager, '_run_op_command_sync', return_value={"success": True}
        ) as mock_sync:
            result = manager._run_op_command_with_retry(["item", "list"])
            assert result == {"success": True}
            assert mock_sync.call_count == 1

    def test_run_op_command_with_retry_success_after_retry(
        self, manager: OnePasswordCLIManager
    ) -> None:
        """Test retry logic with success after retry."""
        with patch.object(manager, '_run_op_command_sync') as mock_sync:
            mock_sync.side_effect = [RateLimitedError("Rate limited"), {"success": True}]
            with patch('time.sleep'):  # Mock sleep to speed up test
                result = manager._run_op_command_with_retry(["item", "list"])
                assert result == {"success": True}
                assert mock_sync.call_count == 2

    def test_run_op_command_with_retry_max_retries_exceeded(
        self, manager: OnePasswordCLIManager
    ) -> None:
        """Test retry logic when max retries exceeded."""
        with patch.object(
            manager, '_run_op_command_sync', side_effect=RateLimitedError("Rate limited")
        ):
            with patch('time.sleep'):  # Mock sleep to speed up test
                with pytest.raises(RateLimitedError, match="Rate limited"):
                    manager._run_op_command_with_retry(["item", "list"])

    def test_run_op_command_with_retry_non_retryable_error(
        self, manager: OnePasswordCLIManager
    ) -> None:
        """Test retry logic with non-retryable error."""
        with patch.object(
            manager, '_run_op_command_sync', side_effect=SecretNotFoundError("Not found")
        ):
            with pytest.raises(SecretNotFoundError):
                manager._run_op_command_with_retry(["item", "get", "nonexistent"])

    def test_verify_op_cli_success(self, manager: OnePasswordCLIManager) -> None:
        """Test successful op CLI verification."""
        with patch.object(manager, '_run_op_command_sync') as mock_sync:
            mock_sync.side_effect = [{"version": "2.0.0"}, [{"id": "test-account"}]]
            manager._verify_op_cli()
            # Should not raise

    def test_verify_op_cli_not_installed(self, manager: OnePasswordCLIManager) -> None:
        """Test op CLI verification when not installed."""
        with patch.object(manager, '_run_op_command_sync', return_value=None):
            with pytest.raises(BackendUnavailableError, match="not installed"):
                manager._verify_op_cli()

    def test_verify_op_cli_not_authenticated(self, manager: OnePasswordCLIManager) -> None:
        """Test op CLI verification when not authenticated."""
        with patch.object(manager, '_run_op_command_sync') as mock_sync:
            mock_sync.side_effect = [{"version": "2.0.0"}, None]
            with pytest.raises(BackendUnavailableError, match="not authenticated"):
                manager._verify_op_cli()

    def test_verify_op_cli_timeout(self, manager: OnePasswordCLIManager) -> None:
        """Test op CLI verification timeout."""
        with patch.object(
            manager, '_run_op_command_sync', side_effect=subprocess.TimeoutExpired("op", 10)
        ):
            with pytest.raises(BackendUnavailableError, match="timed out"):
                manager._verify_op_cli()

    def test_verify_op_cli_file_not_found(self, manager: OnePasswordCLIManager) -> None:
        """Test op CLI verification when op CLI not found."""
        with patch.object(manager, '_run_op_command_sync', side_effect=FileNotFoundError()):
            with pytest.raises(BackendUnavailableError, match="not found"):
                manager._verify_op_cli()
