"""
Unit tests for 1Password secrets integration.
"""

import pytest
import subprocess
from unittest.mock import Mock, patch, AsyncMock
from src.op_secrets import OnePasswordSecrets


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