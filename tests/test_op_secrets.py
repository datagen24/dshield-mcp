"""
Unit tests for 1Password secrets integration.
"""

import pytest
import subprocess
from unittest.mock import Mock, patch, AsyncMock
from src.op_secrets import OnePasswordSecrets, get_env_with_op_resolution, load_env_with_op_resolution


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
                ["op", "--version"],
                capture_output=True,
                text=True,
                timeout=5
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
                timeout=10,
                check=True
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
    
    def test_resolve_environment_variables_dict(self):
        """Test resolving all environment variables in a dictionary."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "resolved_secret\n"
            
            op_secrets = OnePasswordSecrets()
            op_secrets.op_available = True
            
            env_dict = {
                "REGULAR_VAR": "regular_value",
                "OP_VAR": "op://vault/item/field"
            }
            
            result = op_secrets.resolve_environment_variables(env_dict)
            
            assert result["REGULAR_VAR"] == "regular_value"
            assert result["OP_VAR"] == "resolved_secret"
    
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


class TestOpSecretsFunctions:
    """Test the module-level functions."""
    
    @patch('os.getenv')
    @patch('src.op_secrets.op_secrets')
    def test_get_env_with_op_resolution(self, mock_op_secrets, mock_getenv):
        """Test get_env_with_op_resolution function."""
        mock_getenv.return_value = "op://vault/item/field"
        mock_op_secrets.resolve_environment_variable.return_value = "resolved_value"
        
        result = get_env_with_op_resolution("TEST_VAR", "default")
        
        assert result == "resolved_value"
        mock_getenv.assert_called_once_with("TEST_VAR", "default")
        mock_op_secrets.resolve_environment_variable.assert_called_once_with("op://vault/item/field")
    
    @patch('os.getenv')
    @patch('src.op_secrets.op_secrets')
    def test_get_env_with_op_resolution_none(self, mock_op_secrets, mock_getenv):
        """Test get_env_with_op_resolution function with None value."""
        mock_getenv.return_value = None
        
        result = get_env_with_op_resolution("TEST_VAR", "default")
        
        assert result is None
        mock_op_secrets.resolve_environment_variable.assert_not_called()
    
    @patch('os.environ')
    @patch('src.op_secrets.op_secrets')
    def test_load_env_with_op_resolution(self, mock_op_secrets, mock_environ):
        """Test load_env_with_op_resolution function."""
        mock_environ.__iter__.return_value = ["VAR1", "VAR2"]
        mock_environ.__getitem__.side_effect = lambda x: {
            "VAR1": "value1",
            "VAR2": "op://vault/item/field"
        }[x]
        
        mock_op_secrets.resolve_environment_variables.return_value = {
            "VAR1": "value1",
            "VAR2": "resolved_value"
        }
        
        result = load_env_with_op_resolution()
        
        assert result == {"VAR1": "value1", "VAR2": "resolved_value"}
        mock_op_secrets.resolve_environment_variables.assert_called_once()


class TestOpSecretsIntegration:
    """Integration tests for 1Password secrets."""
    
    @patch('subprocess.run')
    def test_full_op_url_resolution_workflow(self, mock_run):
        """Test the complete workflow of op:// URL resolution."""
        # Mock successful CLI check
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "secret_password\n"
        
        op_secrets = OnePasswordSecrets()
        
        # Test resolution
        result = op_secrets.resolve_op_url("op://vault/elasticsearch/password")
        
        assert result == "secret_password"
        assert mock_run.call_count == 2  # One for version check, one for resolution
    
    @patch('subprocess.run')
    def test_error_handling_workflow(self, mock_run):
        """Test error handling in the resolution workflow."""
        # Mock CLI check success but resolution failure
        mock_run.side_effect = [
            Mock(returncode=0, stdout="1.0.0"),  # Version check
            subprocess.CalledProcessError(1, "op", stderr="Item not found")
        ]
        
        op_secrets = OnePasswordSecrets()
        
        # Test resolution failure
        result = op_secrets.resolve_op_url("op://vault/nonexistent/item")
        
        assert result is None 