"""Basic tests for OnePassword CLI Manager."""

from unittest.mock import patch

import pytest

from src.secrets_manager.base_secrets_manager import SecretsManagerError
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

    def test_run_op_command_success(self) -> None:
        """Test successful op command execution."""
        with (
            patch.object(OnePasswordCLIManager, '_verify_op_cli'),
            patch.object(OnePasswordCLIManager, '_run_op_command_sync') as mock_run,
        ):
            # Mock successful subprocess run
            mock_run.return_value = {"test": "data"}

            manager = OnePasswordCLIManager(vault="test_vault")
            result = manager._run_op_command_sync(['item', 'get', 'test'])

        assert result == {"test": "data"}
        mock_run.assert_called_once_with(['item', 'get', 'test'])

    def test_run_op_command_failure(self) -> None:
        """Test failed op command execution."""
        with (
            patch.object(OnePasswordCLIManager, '_verify_op_cli'),
            patch.object(OnePasswordCLIManager, '_run_op_command_sync') as mock_run,
        ):
            # Mock failed subprocess run
            mock_run.side_effect = SecretsManagerError("op command failed")

            manager = OnePasswordCLIManager(vault="test_vault")

            with pytest.raises(SecretsManagerError, match="op command failed"):
                manager._run_op_command_sync(['item', 'get', 'test'])

    def test_run_op_command_invalid_json(self) -> None:
        """Test op command with invalid JSON output."""
        with (
            patch.object(OnePasswordCLIManager, '_verify_op_cli'),
            patch.object(OnePasswordCLIManager, '_run_op_command_sync') as mock_run,
        ):
            # Mock subprocess run with invalid JSON
            mock_run.side_effect = SecretsManagerError("Failed to parse op CLI JSON output")

            manager = OnePasswordCLIManager(vault="test_vault")

            with pytest.raises(SecretsManagerError, match="Failed to parse op CLI JSON output"):
                manager._run_op_command_sync(['item', 'get', 'test'])
