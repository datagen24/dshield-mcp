#!/usr/bin/env python3
"""Tests for configuration loader functionality.

This module provides comprehensive testing for the configuration loader,
ensuring proper loading and validation of configuration files including
error handling configuration sections.
"""

import os
import pytest
import tempfile
import yaml

from src.config_loader import (
    get_config,
    get_error_handling_config,
    validate_error_handling_config,
    ConfigError,
)


class TestConfigLoader:
    """Test configuration loader functionality."""

    def test_get_config_with_valid_file(self) -> None:
        """Test loading configuration from a valid YAML file."""
        # Create a temporary config file
        config_data = {
            'elasticsearch': {'url': 'http://localhost:9200', 'index_pattern': 'dshield-*'},
            'dshield': {'api_key': 'test_key'},
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            config = get_config(config_path)

            assert config['elasticsearch']['url'] == 'http://localhost:9200'
            assert config['elasticsearch']['index_pattern'] == 'dshield-*'
            assert config['dshield']['api_key'] == 'test_key'
        finally:
            os.unlink(config_path)

    def test_get_config_file_not_found(self) -> None:
        """Test that ConfigError is raised when config file is not found."""
        with pytest.raises(ConfigError, match="Config file not found"):
            get_config('/nonexistent/path/config.yaml')

    def test_get_config_invalid_yaml(self) -> None:
        """Test that ConfigError is raised when YAML is invalid."""
        # Create a temporary invalid YAML file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            config_path = f.name

        try:
            with pytest.raises(ConfigError, match="Failed to load config"):
                get_config(config_path)
        finally:
            os.unlink(config_path)

    def test_get_config_not_dict(self) -> None:
        """Test that ConfigError is raised when config is not a dictionary."""
        # Create a temporary config file with list content
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(['item1', 'item2'], f)
            config_path = f.name

        try:
            with pytest.raises(ConfigError, match="Config file is not a valid YAML mapping"):
                get_config(config_path)
        finally:
            os.unlink(config_path)


class TestErrorHandlingConfigLoader:
    """Test error handling configuration loading functionality."""

    def test_get_error_handling_config_defaults(self) -> None:
        """Test that default error handling configuration is returned when no config exists."""
        # Create a minimal config file without error_handling section
        config_data = {'elasticsearch': {'url': 'http://localhost:9200'}}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            error_config = get_error_handling_config(config_path)

            # Check default values
            assert error_config.timeouts['elasticsearch_operations'] == 30.0
            assert error_config.timeouts['dshield_api_calls'] == 10.0
            assert error_config.timeouts['latex_compilation'] == 60.0
            assert error_config.timeouts['tool_execution'] == 120.0

            assert error_config.retry_settings['max_retries'] == 3
            assert error_config.retry_settings['base_delay'] == 1.0
            assert error_config.retry_settings['max_delay'] == 30.0
            assert error_config.retry_settings['exponential_base'] == 2.0

            assert error_config.logging['include_stack_traces'] is True
            assert error_config.logging['include_request_context'] is True
            assert error_config.logging['include_user_parameters'] is True
            assert error_config.logging['log_level'] == 'INFO'
        finally:
            os.unlink(config_path)

    def test_get_error_handling_config_custom_timeouts(self) -> None:
        """Test loading custom timeout values."""
        config_data = {
            'error_handling': {'timeouts': {'elasticsearch_operations': 60, 'tool_execution': 300}}
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            error_config = get_error_handling_config(config_path)

            # Check custom values
            assert error_config.timeouts['elasticsearch_operations'] == 60.0
            assert error_config.timeouts['tool_execution'] == 300.0

            # Check that other defaults remain
            assert error_config.timeouts['dshield_api_calls'] == 10.0
            assert error_config.timeouts['latex_compilation'] == 60.0
        finally:
            os.unlink(config_path)

    def test_get_error_handling_config_custom_retry_settings(self) -> None:
        """Test loading custom retry settings."""
        config_data = {
            'error_handling': {
                'retry_settings': {
                    'max_retries': 5,
                    'base_delay': 2.0,
                    'max_delay': 60.0,
                    'exponential_base': 3.0,
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            error_config = get_error_handling_config(config_path)

            # Check custom values
            assert error_config.retry_settings['max_retries'] == 5
            assert error_config.retry_settings['base_delay'] == 2.0
            assert error_config.retry_settings['max_delay'] == 60.0
            assert error_config.retry_settings['exponential_base'] == 3.0
        finally:
            os.unlink(config_path)

    def test_get_error_handling_config_custom_logging(self) -> None:
        """Test loading custom logging settings."""
        config_data = {
            'error_handling': {
                'logging': {
                    'include_stack_traces': False,
                    'include_request_context': False,
                    'include_user_parameters': False,
                    'log_level': 'DEBUG',
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            error_config = get_error_handling_config(config_path)

            # Check custom values
            assert error_config.logging['include_stack_traces'] is False
            assert error_config.logging['include_request_context'] is False
            assert error_config.logging['include_user_parameters'] is False
            assert error_config.logging['log_level'] == 'DEBUG'
        finally:
            os.unlink(config_path)

    def test_get_error_handling_config_invalid_timeout(self) -> None:
        """Test that invalid timeout values raise ConfigError."""
        config_data = {
            'error_handling': {
                'timeouts': {
                    'tool_execution': 0  # Invalid: must be positive
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            with pytest.raises(ConfigError, match="Invalid timeout value for tool_execution"):
                get_error_handling_config(config_path)
        finally:
            os.unlink(config_path)

    def test_get_error_handling_config_invalid_retry_settings(self) -> None:
        """Test that invalid retry settings raise ConfigError."""
        config_data = {
            'error_handling': {
                'retry_settings': {
                    'max_retries': -1,  # Invalid: must be non-negative
                    'base_delay': 0,  # Invalid: must be positive
                    'exponential_base': 1.0,  # Invalid: must be > 1
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            with pytest.raises(ConfigError, match="Invalid max_retries value"):
                get_error_handling_config(config_path)
        finally:
            os.unlink(config_path)

    def test_get_error_handling_config_invalid_log_level(self) -> None:
        """Test that invalid log level raises ConfigError."""
        config_data = {'error_handling': {'logging': {'log_level': 'INVALID_LEVEL'}}}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            with pytest.raises(ConfigError, match="Invalid log_level value"):
                get_error_handling_config(config_path)
        finally:
            os.unlink(config_path)

    def test_get_error_handling_config_invalid_boolean_values(self) -> None:
        """Test that invalid boolean values raise ConfigError."""
        config_data = {'error_handling': {'logging': {'include_stack_traces': 'not_a_boolean'}}}

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            with pytest.raises(ConfigError, match="Invalid include_stack_traces value"):
                get_error_handling_config(config_path)
        finally:
            os.unlink(config_path)


class TestErrorHandlingConfigValidation:
    """Test error handling configuration validation functionality."""

    def test_validate_error_handling_config_valid(self) -> None:
        """Test validation of valid error handling configuration."""
        config = {
            'error_handling': {
                'timeouts': {'tool_execution': 120, 'elasticsearch_operations': 30},
                'retry_settings': {
                    'max_retries': 3,
                    'base_delay': 1.0,
                    'max_delay': 30.0,
                    'exponential_base': 2.0,
                },
                'logging': {
                    'include_stack_traces': True,
                    'include_request_context': False,
                    'include_user_parameters': True,
                    'log_level': 'WARNING',
                },
            }
        }

        # Should not raise any exception
        validate_error_handling_config(config)

    def test_validate_error_handling_config_invalid_timeout(self) -> None:
        """Test validation failure for invalid timeout values."""
        config = {
            'error_handling': {
                'timeouts': {
                    'tool_execution': -1  # Invalid: negative value
                }
            }
        }

        with pytest.raises(ConfigError, match="Invalid timeout value for tool_execution"):
            validate_error_handling_config(config)

    def test_validate_error_handling_config_invalid_retry_settings(self) -> None:
        """Test validation failure for invalid retry settings."""
        config = {
            'error_handling': {
                'retry_settings': {
                    'max_retries': -5,  # Invalid: negative value
                    'base_delay': 0,  # Invalid: zero value
                    'exponential_base': 0.5,  # Invalid: <= 1
                }
            }
        }

        with pytest.raises(ConfigError, match="Invalid max_retries value"):
            validate_error_handling_config(config)

    def test_validate_error_handling_config_invalid_logging(self) -> None:
        """Test validation failure for invalid logging settings."""
        config = {
            'error_handling': {
                'logging': {
                    'log_level': 'INVALID'  # Invalid: not a valid log level
                }
            }
        }

        with pytest.raises(ConfigError, match="Invalid log_level value"):
            validate_error_handling_config(config)

    def test_validate_error_handling_config_no_error_handling_section(self) -> None:
        """Test validation when no error_handling section exists."""
        config = {'elasticsearch': {'url': 'http://localhost:9200'}}

        # Should not raise any exception (no validation needed)
        validate_error_handling_config(config)

    def test_validate_error_handling_config_partial_section(self) -> None:
        """Test validation with partial error_handling section."""
        config = {
            'error_handling': {
                'timeouts': {'tool_execution': 60}
                # Missing other sections - should be fine
            }
        }

        # Should not raise any exception
        validate_error_handling_config(config)


class TestConfigLoaderIntegration:
    """Integration tests for configuration loader."""

    def test_full_config_with_error_handling(self) -> None:
        """Test loading a complete configuration with error handling section."""
        config_data = {
            'elasticsearch': {'url': 'http://localhost:9200', 'index_pattern': 'dshield-*'},
            'dshield': {'api_key': 'test_key'},
            'error_handling': {
                'timeouts': {'tool_execution': 180, 'elasticsearch_operations': 45},
                'retry_settings': {'max_retries': 5, 'base_delay': 2.0},
                'logging': {'log_level': 'DEBUG', 'include_stack_traces': False},
            },
        }

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(config_data, f)
            config_path = f.name

        try:
            # Test main config loading
            config = get_config(config_path)
            assert config['elasticsearch']['url'] == 'http://localhost:9200'
            assert config['dshield']['api_key'] == 'test_key'

            # Test error handling config loading
            error_config = get_error_handling_config(config_path)
            assert error_config.timeouts['tool_execution'] == 180.0
            assert error_config.timeouts['elasticsearch_operations'] == 45.0
            assert error_config.retry_settings['max_retries'] == 5
            assert error_config.retry_settings['base_delay'] == 2.0
            assert error_config.logging['log_level'] == 'DEBUG'
            assert error_config.logging['include_stack_traces'] is False

            # Test validation
            validate_error_handling_config(config)
        finally:
            os.unlink(config_path)

    def test_config_loader_error_propagation(self) -> None:
        """Test that errors in main config loading propagate to error handling config loading."""
        # Create a config file that will cause an error in main config loading
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: content: [")
            config_path = f.name

        try:
            with pytest.raises(ConfigError, match="Failed to load config"):
                get_error_handling_config(config_path)
        finally:
            os.unlink(config_path)
