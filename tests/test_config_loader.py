"""Tests for config_loader module."""

from unittest.mock import patch

from src.config_loader import ConfigError, get_config, get_error_handling_config


class TestConfigFunctions:
    """Test configuration functions."""

    @patch('src.config_loader._resolve_secrets')
    @patch('src.config_loader.yaml.safe_load')
    @patch('builtins.open')
    @patch('os.path.exists')
    def test_get_config(self, mock_exists, mock_open, mock_yaml, mock_resolve_secrets) -> None:
        """Test get_config function."""
        mock_exists.return_value = True
        mock_yaml.return_value = {"test": "config"}
        mock_resolve_secrets.return_value = {"test": "config"}
        config = get_config("test.yaml")
        assert config == {"test": "config"}

    @patch('src.config_loader._resolve_secrets')
    @patch('src.config_loader.yaml.safe_load')
    @patch('builtins.open')
    @patch('os.path.exists')
    def test_get_error_handling_config(
        self, mock_exists, mock_open, mock_yaml, mock_resolve_secrets
    ) -> None:
        """Test get_error_handling_config function."""
        mock_exists.return_value = True
        mock_yaml.return_value = {"error_handling": {"timeouts": {"tool_execution": 30}}}
        mock_resolve_secrets.return_value = {"error_handling": {"timeouts": {"tool_execution": 30}}}
        config = get_error_handling_config("test.yaml")
        assert config is not None


class TestConfigError:
    """Test ConfigError exception."""

    def test_config_error_creation(self) -> None:
        """Test ConfigError creation."""
        error = ConfigError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
