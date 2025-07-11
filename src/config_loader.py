"""Configuration loader for DShield MCP server.

This module provides utilities for loading and resolving configuration
from YAML files with support for 1Password CLI secret resolution.
It handles config file validation, secret resolution, and error handling.

Features:
- YAML configuration file loading
- 1Password CLI secret resolution
- Configuration validation
- Error handling with custom exceptions

Example:
    >>> from src.config_loader import get_config
    >>> config = get_config()
    >>> print(config['elasticsearch']['url'])
"""

import os
import yaml
from typing import Any, Dict, Union, List
from .op_secrets import OnePasswordSecrets


class ConfigError(Exception):
    """Exception raised for configuration-related errors.
    
    This exception is raised when there are issues with loading,
    parsing, or validating configuration files.
    """
    pass


def get_config(config_path: str = None) -> Dict[str, Any]:
    """Load the MCP YAML config file.
    
    Loads and validates a YAML configuration file, resolving any
    1Password CLI secrets in the process. By default, looks for
    'mcp_config.yaml' in the project root.
    
    Args:
        config_path: Path to the configuration file (default: auto-detected)
    
    Returns:
        Dictionary containing the resolved configuration
        
    Raises:
        ConfigError: If config file is missing, invalid, or cannot be loaded
    """
    if config_path is None:
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'mcp_config.yaml')
    if not os.path.exists(config_path):
        raise ConfigError(f"Config file not found: {config_path}")
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        if not isinstance(config, dict):
            raise ConfigError("Config file is not a valid YAML mapping.")
        
        # Resolve secrets using 1Password CLI
        config = _resolve_secrets(config)
        
        return config
    except Exception as e:
        raise ConfigError(f"Failed to load config: {e}")


def _resolve_secrets(config: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively resolve op:// URLs in config values using 1Password CLI.
    
    This function traverses the configuration dictionary and resolves
    any 1Password CLI references (op:// URLs) to their actual values.
    
    Args:
        config: Configuration dictionary to process
    
    Returns:
        Configuration dictionary with resolved secrets
    """
    op_secrets = OnePasswordSecrets()
    
    def _resolve_value(value: Union[str, Dict[str, Any], List[Any], Any]) -> Union[str, Dict[str, Any], List[Any], Any]:
        """Resolve a single value or recursively process nested structures.
        
        Args:
            value: Value to resolve (string, dict, list, or other)
        
        Returns:
            Resolved value with any op:// URLs replaced
        """
        if isinstance(value, str):
            return op_secrets.resolve_environment_variable(value)
        elif isinstance(value, dict):
            return {k: _resolve_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [_resolve_value(v) for v in value]
        else:
            return value
    
    return _resolve_value(config) 