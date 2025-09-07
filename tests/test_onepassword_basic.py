"""Basic tests for OnePassword CLI Manager."""

from unittest.mock import Mock, patch

import pytest

from src.secrets_manager.onepassword_cli_manager import OnePasswordCLIManager


class TestOnePasswordCLIManagerBasic:
    """Basic tests for OnePasswordCLIManager."""

    def test_init(self) -> None:
        """Test OnePasswordCLIManager initialization."""
        with patch.object(OnePasswordCLIManager, '_verify_op_cli'):
            manager = OnePasswordCLIManager(vault="test_vault")
            assert manager is not None
            assert hasattr(manager, 'vault')
            assert manager.vault == "test_vault"

    @patch('subprocess.run')
    def test_run_op_command_success(self, mock_run: Mock) -> None:
        """Test successful op command execution."""
        # Mock successful subprocess run
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = '{"test": "data"}'
        mock_run.return_value = mock_result

        with patch.object(OnePasswordCLIManager, '_verify_op_cli'):
            manager = OnePasswordCLIManager(vault="test_vault")
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

        with patch.object(OnePasswordCLIManager, '_verify_op_cli'):
            manager = OnePasswordCLIManager(vault="test_vault")

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

        with patch.object(OnePasswordCLIManager, '_verify_op_cli'):
            manager = OnePasswordCLIManager(vault="test_vault")

            with pytest.raises(RuntimeError, match="Failed to parse op CLI JSON output"):
                manager._run_op_command(['item', 'get', 'test'])
