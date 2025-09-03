"""Unit tests for 1Password secrets integration."""

import pytest
import subprocess
import yaml
from unittest.mock import patch
from src.op_secrets import OnePasswordSecrets
from src.config_loader import get_config, _resolve_secrets, ConfigError


class TestOnePasswordSecrets:
    """Test the OnePasswordSecrets class."""

    def test_init_with_op_cli_available(self):
        """Test initialization when 1Password CLI is available."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "1.0.0"

            op_secrets = OnePasswordSecrets()

            assert op_secrets.op_available is True
            mock_run.assert_called_once_with(
                ["op", "--version"], check=False, capture_output=True, text=True, timeout=5
            )

    def test_init_with_op_cli_unavailable(self):
        """Test initialization when 1Password CLI is not available."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = FileNotFoundError()

            op_secrets = OnePasswordSecrets()

            assert op_secrets.op_available is False

    def test_init_with_op_cli_timeout(self):
        """Test initialization when 1Password CLI times out."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("op", 5)

            op_secrets = OnePasswordSecrets()

            assert op_secrets.op_available is False

    def test_resolve_op_url_success(self):
        """Test successful op:// URL resolution."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "secret_value\n"

            op_secrets = OnePasswordSecrets()
            op_secrets.op_available = True

            result = op_secrets.resolve_op_url("op://vault/item/field")

            assert result == "secret_value"
            # Check that the read command was called (second call after version check)
            mock_run.assert_any_call(
                ["op", "read", "op://vault/item/field"],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )

    def test_resolve_op_url_not_op_url(self):
        """Test resolution of non-op:// URLs."""
        op_secrets = OnePasswordSecrets()
        op_secrets.op_available = True

        result = op_secrets.resolve_op_url("not-an-op-url")

        assert result == "not-an-op-url"

    def test_resolve_op_url_cli_unavailable(self):
        """Test op:// URL resolution when CLI is unavailable."""
        op_secrets = OnePasswordSecrets()
        op_secrets.op_available = False

        result = op_secrets.resolve_op_url("op://vault/item/field")

        assert result is None

    def test_resolve_op_url_timeout(self):
        """Test op:// URL resolution timeout."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired("op", 10)

            op_secrets = OnePasswordSecrets()
            op_secrets.op_available = True

            result = op_secrets.resolve_op_url("op://vault/item/field")

            assert result is None

    def test_resolve_op_url_error(self):
        """Test op:// URL resolution error."""
        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, "op", stderr="Error")

            op_secrets = OnePasswordSecrets()
            op_secrets.op_available = True

            result = op_secrets.resolve_op_url("op://vault/item/field")

            assert result is None

    def test_resolve_environment_variable_op_url(self):
        """Test environment variable resolution with op:// URL."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "resolved_secret\n"

            op_secrets = OnePasswordSecrets()
            op_secrets.op_available = True

            result = op_secrets.resolve_environment_variable("op://vault/item/field")

            assert result == "resolved_secret"

    def test_resolve_environment_variable_regular_value(self):
        """Test environment variable resolution with regular value."""
        op_secrets = OnePasswordSecrets()
        op_secrets.op_available = True

        result = op_secrets.resolve_environment_variable("regular_value")

        assert result == "regular_value"

    def test_resolve_environment_variable_complex_value(self):
        """Test environment variable resolution with complex value containing op:// URLs."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "secret1\n"

            op_secrets = OnePasswordSecrets()
            op_secrets.op_available = True

            complex_value = "prefix op://vault/item/field suffix"
            result = op_secrets.resolve_environment_variable(complex_value)

            assert result == "prefix secret1 suffix"

    def test_resolve_environment_variable_none_value(self):
        """Test environment variable resolution with None value."""
        op_secrets = OnePasswordSecrets()
        op_secrets.op_available = True

        result = op_secrets.resolve_environment_variable(None)

        assert result is None

    def test_resolve_environment_variable_empty_string(self):
        """Test environment variable resolution with empty string."""
        op_secrets = OnePasswordSecrets()
        op_secrets.op_available = True

        result = op_secrets.resolve_environment_variable("")

        assert result == ""


class TestOnePasswordSecretsIntegration:
    """Test 1Password secrets integration with config loading."""

    def test_config_loading_with_secrets_resolution(self):
        """Test config loading with secrets resolution."""
        # Mock config file content
        mock_config_content = {
            'elasticsearch': {
                'host': 'localhost',
                'port': 9200,
                'username': 'op://vault/item/username',
                'password': 'op://vault/item/password',
            },
            'dshield': {
                'api_key': 'op://vault/item/api_key',
                'base_url': 'https://api.dshield.org',
            },
        }

        with (
            patch('builtins.open', create=True) as mock_open,
            patch('yaml.safe_load') as mock_yaml_load,
            patch('subprocess.run') as mock_run,
        ):
            # Mock file operations
            mock_open.return_value.__enter__.return_value.read.return_value = "mock content"
            mock_yaml_load.return_value = mock_config_content

            # Mock 1Password CLI responses
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "resolved_secret\n"

            # Test config loading
            config = get_config()

            # Verify secrets were resolved
            assert config['elasticsearch']['username'] == 'resolved_secret'
            assert config['elasticsearch']['password'] == 'resolved_secret'
            assert config['dshield']['api_key'] == 'resolved_secret'
            assert config['elasticsearch']['host'] == 'localhost'  # Non-secret unchanged
            assert (
                config['dshield']['base_url'] == 'https://api.dshield.org'
            )  # Non-secret unchanged

    def test_config_loading_with_nested_structures(self):
        """Test config loading with nested dictionaries and lists."""
        mock_config_content = {
            'services': {
                'elasticsearch': {
                    'credentials': {
                        'username': 'op://vault/item/es_user',
                        'password': 'op://vault/item/es_pass',
                    },
                    'hosts': ['localhost', 'op://vault/item/es_host2'],
                },
                'redis': {'password': 'op://vault/item/redis_pass'},
            }
        }

        with (
            patch('builtins.open', create=True) as mock_open,
            patch('yaml.safe_load') as mock_yaml_load,
            patch('subprocess.run') as mock_run,
        ):
            mock_open.return_value.__enter__.return_value.read.return_value = "mock content"
            mock_yaml_load.return_value = mock_config_content
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "resolved_value\n"

            config = get_config()

            # Verify nested resolution
            assert (
                config['services']['elasticsearch']['credentials']['username'] == 'resolved_value'
            )
            assert (
                config['services']['elasticsearch']['credentials']['password'] == 'resolved_value'
            )
            assert (
                config['services']['elasticsearch']['hosts'][0] == 'localhost'
            )  # Non-secret unchanged
            assert config['services']['elasticsearch']['hosts'][1] == 'resolved_value'
            assert config['services']['redis']['password'] == 'resolved_value'

    def test_config_loading_with_op_cli_unavailable(self):
        """Test config loading when 1Password CLI is unavailable."""
        mock_config_content = {
            'elasticsearch': {
                'username': 'op://vault/item/username',
                'password': 'op://vault/item/password',
            }
        }

        with (
            patch('builtins.open', create=True) as mock_open,
            patch('yaml.safe_load') as mock_yaml_load,
            patch('subprocess.run') as mock_run,
        ):
            mock_open.return_value.__enter__.return_value.read.return_value = "mock content"
            mock_yaml_load.return_value = mock_config_content
            mock_run.side_effect = FileNotFoundError()  # 1Password CLI not available

            config = get_config()

            # Verify op:// URLs are not resolved when CLI unavailable - returns original values
            assert config['elasticsearch']['username'] == 'op://vault/item/username'
            assert config['elasticsearch']['password'] == 'op://vault/item/password'

    def test_config_loading_with_op_cli_errors(self):
        """Test config loading when 1Password CLI returns errors."""
        mock_config_content = {
            'elasticsearch': {
                'username': 'op://vault/item/username',
                'password': 'op://vault/item/password',
            }
        }

        with (
            patch('builtins.open', create=True) as mock_open,
            patch('yaml.safe_load') as mock_yaml_load,
            patch('subprocess.run') as mock_run,
        ):
            mock_open.return_value.__enter__.return_value.read.return_value = "mock content"
            mock_yaml_load.return_value = mock_config_content
            mock_run.side_effect = subprocess.CalledProcessError(
                1, "op", stderr="Authentication failed"
            )

            config = get_config()

            # Verify op:// URLs are not resolved when CLI errors - returns original values
            assert config['elasticsearch']['username'] == 'op://vault/item/username'
            assert config['elasticsearch']['password'] == 'op://vault/item/password'

    def test_resolve_secrets_function(self):
        """Test the _resolve_secrets function directly."""
        test_config = {
            'simple': 'op://vault/item/simple',
            'nested': {'value': 'op://vault/item/nested'},
            'list': ['item1', 'op://vault/item/list_item', 'item3'],
            'mixed': 'prefix op://vault/item/mixed suffix',
        }

        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "resolved\n"

            resolved_config = _resolve_secrets(test_config)

            assert resolved_config['simple'] == 'resolved'
            assert resolved_config['nested']['value'] == 'resolved'
            assert resolved_config['list'][0] == 'item1'
            assert resolved_config['list'][1] == 'resolved'
            assert resolved_config['list'][2] == 'item3'
            assert resolved_config['mixed'] == 'prefix resolved suffix'

    def test_config_loading_with_no_secrets(self):
        """Test config loading when no op:// URLs are present."""
        mock_config_content = {
            'elasticsearch': {
                'host': 'localhost',
                'port': 9200,
                'username': 'admin',
                # file deepcode ignore NoHardcodedPasswords/test: python test, ot valid password
                'password': 'password123',
            }
        }

        with (
            patch('builtins.open', create=True) as mock_open,
            patch('yaml.safe_load') as mock_yaml_load,
        ):
            mock_open.return_value.__enter__.return_value.read.return_value = "mock content"
            mock_yaml_load.return_value = mock_config_content

            config = get_config()

            # Verify no 1Password calls were made
            assert config['elasticsearch']['host'] == 'localhost'
            assert config['elasticsearch']['port'] == 9200
            assert config['elasticsearch']['username'] == 'admin'
            # file deepcode ignore NoHardcodedPasswords/test: python test, ot valid password
            assert config['elasticsearch']['password'] == 'password123'

    def test_config_file_not_found(self):
        """Test config loading when config file doesn't exist."""
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False

            with pytest.raises(ConfigError, match="Config file not found"):
                get_config("/nonexistent/config.yaml")

    def test_config_file_invalid_yaml(self):
        """Test config loading with invalid YAML."""
        with (
            patch('builtins.open', create=True) as mock_open,
            patch('yaml.safe_load') as mock_yaml_load,
        ):
            mock_open.return_value.__enter__.return_value.read.return_value = "invalid yaml content"
            mock_yaml_load.side_effect = yaml.YAMLError("Invalid YAML")

            with pytest.raises(ConfigError, match="Failed to load config"):
                get_config()

    def test_config_file_not_dict(self):
        """Test config loading when YAML doesn't parse to a dict."""
        with (
            patch('builtins.open', create=True) as mock_open,
            patch('yaml.safe_load') as mock_yaml_load,
        ):
            mock_open.return_value.__enter__.return_value.read.return_value = "mock content"
            mock_yaml_load.return_value = "not a dict"  # YAML parses to string, not dict

            with pytest.raises(ConfigError, match="Config file is not a valid YAML mapping"):
                get_config()
