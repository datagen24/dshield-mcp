"""Focused tests for OnePassword CLI Manager."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.secrets_manager.onepassword_cli_manager import OnePasswordCLIManager


class TestOnePasswordCLIManagerFocused:
    """Focused tests for OnePasswordCLIManager."""

    def test_init(self) -> None:
        """Test OnePasswordCLIManager initialization."""
        manager = OnePasswordCLIManager()
        assert manager is not None
        assert hasattr(manager, 'store_name')
        assert hasattr(manager, 'vault_name')

    @patch('subprocess.run')
    def test_run_op_command_success(self, mock_run: Mock) -> None:
        """Test successful op command execution."""
        # Mock successful subprocess run
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '{"test": "data"}'
        mock_run.return_value = mock_result

        manager = OnePasswordCLIManager()
        result = manager._run_op_command(['item', 'get', 'test'])

        assert result == {"test": "data"}
        mock_run.assert_called_once()

    @patch('subprocess.run')
    def test_run_op_command_failure(self, mock_run: Mock) -> None:
        """Test failed op command execution."""
        # Mock failed subprocess run
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stderr = 'Error message'
        mock_run.return_value = mock_result

        manager = OnePasswordCLIManager()
        
        with pytest.raises(RuntimeError, match="op command failed"):
            manager._run_op_command(['item', 'get', 'test'])

    @patch('subprocess.run')
    def test_run_op_command_invalid_json(self, mock_run: Mock) -> None:
        """Test op command with invalid JSON output."""
        # Mock subprocess run with invalid JSON
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = 'invalid json'
        mock_run.return_value = mock_result

        manager = OnePasswordCLIManager()
        
        with pytest.raises(RuntimeError, match="Failed to parse op command output"):
            manager._run_op_command(['item', 'get', 'test'])

    def test_get_secret_success(self) -> None:
        """Test successful secret retrieval."""
        manager = OnePasswordCLIManager()
        
        with patch.object(manager, '_run_op_command', return_value={"value": "secret_value"}):
            result = manager.get_secret("op://vault/item/field")
            assert result == "secret_value"

    def test_get_secret_failure(self) -> None:
        """Test failed secret retrieval."""
        manager = OnePasswordCLIManager()
        
        with patch.object(manager, '_run_op_command', side_effect=RuntimeError("op command failed")):
            with pytest.raises(RuntimeError, match="op command failed"):
                manager.get_secret("op://vault/item/field")

    def test_store_api_key_success(self) -> None:
        """Test successful API key storage."""
        manager = OnePasswordCLIManager()
        
        with patch.object(manager, '_run_op_command', return_value={"uuid": "test-uuid"}):
            result = manager.store_api_key("test-key", "test-secret", 30)
            assert result is True

    def test_store_api_key_failure(self) -> None:
        """Test failed API key storage."""
        manager = OnePasswordCLIManager()
        
        with patch.object(manager, '_run_op_command', side_effect=RuntimeError("op command failed")):
            result = manager.store_api_key("test-key", "test-secret", 30)
            assert result is False

    def test_retrieve_api_key_success(self) -> None:
        """Test successful API key retrieval."""
        manager = OnePasswordCLIManager()
        
        mock_key_data = {
            "fields": [
                {"id": "api_key", "value": "test-api-key"},
                {"id": "secret", "value": "test-secret"}
            ]
        }
        
        with patch.object(manager, '_run_op_command', return_value=mock_key_data):
            result = manager.retrieve_api_key("test-key")
            assert result is not None
            assert result.api_key == "test-api-key"
            assert result.secret == "test-secret"

    def test_retrieve_api_key_not_found(self) -> None:
        """Test API key retrieval when key doesn't exist."""
        manager = OnePasswordCLIManager()
        
        with patch.object(manager, '_run_op_command', side_effect=RuntimeError("op command failed")):
            result = manager.retrieve_api_key("nonexistent-key")
            assert result is None

    def test_list_api_keys_success(self) -> None:
        """Test successful API key listing."""
        manager = OnePasswordCLIManager()
        
        mock_list_data = [
            {"uuid": "key1", "title": "API Key 1"},
            {"uuid": "key2", "title": "API Key 2"}
        ]
        
        with patch.object(manager, '_run_op_command', return_value=mock_list_data):
            result = manager.list_api_keys()
            assert len(result) == 2
            assert result[0]["title"] == "API Key 1"
            assert result[1]["title"] == "API Key 2"

    def test_list_api_keys_failure(self) -> None:
        """Test failed API key listing."""
        manager = OnePasswordCLIManager()
        
        with patch.object(manager, '_run_op_command', side_effect=RuntimeError("op command failed")):
            result = manager.list_api_keys()
            assert result == []

    def test_delete_api_key_success(self) -> None:
        """Test successful API key deletion."""
        manager = OnePasswordCLIManager()
        
        with patch.object(manager, '_run_op_command', return_value={}):
            result = manager.delete_api_key("test-key")
            assert result is True

    def test_delete_api_key_failure(self) -> None:
        """Test failed API key deletion."""
        manager = OnePasswordCLIManager()
        
        with patch.object(manager, '_run_op_command', side_effect=RuntimeError("op command failed")):
            result = manager.delete_api_key("test-key")
            assert result is False

    def test_update_api_key_success(self) -> None:
        """Test successful API key update."""
        manager = OnePasswordCLIManager()
        
        with patch.object(manager, '_run_op_command', return_value={}):
            result = manager.update_api_key("test-key", "new-secret", 60)
            assert result is True

    def test_update_api_key_failure(self) -> None:
        """Test failed API key update."""
        manager = OnePasswordCLIManager()
        
        with patch.object(manager, '_run_op_command', side_effect=RuntimeError("op command failed")):
            result = manager.update_api_key("test-key", "new-secret", 60)
            assert result is False
