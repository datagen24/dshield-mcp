# config_loader

Configuration loader for DShield MCP server.

This module provides utilities for loading and resolving configuration
from YAML files with support for 1Password CLI secret resolution.
It handles config file validation, secret resolution, and error handling.

Features:
- YAML configuration file loading
- 1Password CLI secret resolution
- Configuration validation
- Error handling with custom exceptions
- Error handling configuration loading and validation

Example:
    >>> from src.config_loader import get_config, get_error_handling_config
    >>> config = get_config()
    >>> error_config = get_error_handling_config()
    >>> print(config['elasticsearch']['url'])
    >>> print(error_config.timeouts['tool_execution'])

## ConfigError

Exception raised for configuration-related errors.

    This exception is raised when there are issues with loading,
    parsing, or validating configuration files.

### get_config

```python
def get_config(config_path)
```

Load the MCP YAML config file.

    Loads and validates a YAML configuration file, resolving any
    1Password CLI secrets in the process. By default, looks for
    'mcp_config.yaml' in the project root.

    Args:
        config_path: Path to the configuration file (default: auto-detected)

    Returns:
        Dictionary containing the resolved configuration

    Raises:
        ConfigError: If config file is missing, invalid, or cannot be loaded

### _resolve_secrets

```python
def _resolve_secrets(config)
```

Recursively resolve op:// URLs in config values using 1Password CLI.

    This function traverses the configuration dictionary and resolves
    any 1Password CLI references (op:// URLs) to their actual values.

    Args:
        config: Configuration dictionary to process

    Returns:
        Configuration dictionary with resolved secrets

### get_error_handling_config

```python
def get_error_handling_config(config_path)
```

Load and validate error handling configuration.

    Loads error handling configuration from the user configuration file
    and returns a validated ErrorHandlingConfig object. If no error
    handling section is found, returns default configuration.

    Args:
        config_path: Path to the configuration file (default: auto-detected)

    Returns:
        ErrorHandlingConfig object with validated settings

    Raises:
        ConfigError: If error handling configuration is invalid

### validate_error_handling_config

```python
def validate_error_handling_config(config)
```

Validate error handling configuration values.

    Args:
        config: Configuration dictionary to validate

    Raises:
        ConfigError: If configuration values are invalid
