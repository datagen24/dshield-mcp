"""Configuration loader for DShield MCP server.

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

"""

import os
from typing import Any

import yaml

from .mcp_error_handler import ErrorHandlingConfig
from .op_secrets import OnePasswordSecrets


class ConfigError(Exception):
    """Exception raised for configuration-related errors.

    This exception is raised when there are issues with loading,
    parsing, or validating configuration files.
    """


def get_config(config_path: str | None = None) -> dict[str, Any]:
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
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "mcp_config.yaml")
    if not os.path.exists(config_path):
        raise ConfigError(f"Config file not found: {config_path}")
    try:
        with open(config_path) as f:
            config = yaml.safe_load(f)
        if not isinstance(config, dict):
            raise ConfigError("Config file is not a valid YAML mapping.")

        # Resolve secrets using 1Password CLI
        config = _resolve_secrets(config)

        return config
    except Exception as e:
        raise ConfigError(f"Failed to load config: {e}") from e


def _resolve_secrets(config: dict[str, Any]) -> dict[str, Any]:
    """Recursively resolve op:// URLs in config values using 1Password CLI.

    This function traverses the configuration dictionary and resolves
    any 1Password CLI references (op:// URLs) to their actual values.

    Args:
        config: Configuration dictionary to process

    Returns:
        Configuration dictionary with resolved secrets

    """
    op_secrets = OnePasswordSecrets()

    def _resolve_value(
        value: str | dict[str, Any] | list[Any] | Any,
    ) -> str | dict[str, Any] | list[Any] | Any:
        """Resolve a single value or recursively process nested structures.

        Args:
            value: Value to resolve (string, dict, list, or other)

        Returns:
            Resolved value with any op:// URLs replaced

        """
        if isinstance(value, str):
            return op_secrets.resolve_environment_variable(value)
        if isinstance(value, dict):
            return {k: _resolve_value(v) for k, v in value.items()}
        if isinstance(value, list):
            return [_resolve_value(v) for v in value]
        return value

    resolved = _resolve_value(config)
    if isinstance(resolved, dict):
        return resolved
    else:
        # If the config itself is not a dict, wrap it
        return {"config": resolved}


def get_error_handling_config(config_path: str | None = None) -> ErrorHandlingConfig:
    """Load and validate error handling configuration.

    Loads error handling configuration from the user configuration file
    and returns a validated ErrorHandlingConfig object. If no error
    handling section is found, returns default configuration.

    Args:
        config_path: Path to the configuration file (default: auto-detected)

    Returns:
        ErrorHandlingConfig object with validated settings

    Raises:
        ConfigError: If error handling configuration is invalid

    """
    try:
        # Load the full configuration
        config = get_config(config_path)

        # Extract error handling section
        error_config = config.get("error_handling", {})

        # Create ErrorHandlingConfig with custom values if provided
        custom_config = ErrorHandlingConfig()

        # Update timeouts if provided
        if "timeouts" in error_config:
            for key, value in error_config["timeouts"].items():
                if key in custom_config.timeouts:
                    if not isinstance(value, int | float) or value <= 0:
                        raise ConfigError(
                            f"Invalid timeout value for {key}: {value}. Must be positive number."
                        )
                    custom_config.timeouts[key] = float(value)

        # Update retry settings if provided
        if "retry_settings" in error_config:
            retry_config = error_config["retry_settings"]

            if "max_retries" in retry_config:
                value = retry_config["max_retries"]
                if not isinstance(value, int) or value < 0:
                    raise ConfigError(
                        f"Invalid max_retries value: {value}. Must be non-negative integer."
                    )
                custom_config.retry_settings["max_retries"] = value

            if "base_delay" in retry_config:
                value = retry_config["base_delay"]
                if not isinstance(value, int | float) or value <= 0:
                    raise ConfigError(
                        f"Invalid base_delay value: {value}. Must be positive number."
                    )
                custom_config.retry_settings["base_delay"] = float(value)

            if "max_delay" in retry_config:
                value = retry_config["max_delay"]
                if not isinstance(value, int | float) or value <= 0:
                    raise ConfigError(f"Invalid max_delay value: {value}. Must be positive number.")
                custom_config.retry_settings["max_delay"] = float(value)

            if "exponential_base" in retry_config:
                value = retry_config["exponential_base"]
                if not isinstance(value, int | float) or value <= 1:
                    raise ConfigError(
                        f"Invalid exponential_base value: {value}. Must be greater than 1."
                    )
                custom_config.retry_settings["exponential_base"] = float(value)

        # Update logging settings if provided
        if "logging" in error_config:
            logging_config = error_config["logging"]

            if "include_stack_traces" in logging_config:
                value = logging_config["include_stack_traces"]
                if not isinstance(value, bool):
                    raise ConfigError(
                        f"Invalid include_stack_traces value: {value}. Must be boolean."
                    )
                custom_config.logging["include_stack_traces"] = value

            if "include_request_context" in logging_config:
                value = logging_config["include_request_context"]
                if not isinstance(value, bool):
                    raise ConfigError(
                        f"Invalid include_request_context value: {value}. Must be boolean."
                    )
                custom_config.logging["include_request_context"] = value

            if "include_user_parameters" in logging_config:
                value = logging_config["include_user_parameters"]
                if not isinstance(value, bool):
                    raise ConfigError(
                        f"Invalid include_user_parameters value: {value}. Must be boolean."
                    )
                custom_config.logging["include_user_parameters"] = value

            if "log_level" in logging_config:
                value = logging_config["log_level"]
                valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
                if not isinstance(value, str) or value.upper() not in valid_levels:
                    raise ConfigError(
                        f"Invalid log_level value: {value}. Must be one of: {', '.join(valid_levels)}"
                    )
                custom_config.logging["log_level"] = value.upper()

        return custom_config

    except Exception as e:
        if isinstance(e, ConfigError):
            raise
        raise ConfigError(f"Failed to load error handling configuration: {e}") from e


def validate_error_handling_config(config: dict[str, Any]) -> None:
    """Validate error handling configuration values.

    Args:
        config: Configuration dictionary to validate

    Raises:
        ConfigError: If configuration values are invalid

    """
    error_config = config.get("error_handling", {})

    # Validate timeouts
    if "timeouts" in error_config:
        for key, value in error_config["timeouts"].items():
            if not isinstance(value, int | float) or value <= 0:
                raise ConfigError(
                    f"Invalid timeout value for {key}: {value}. Must be positive number."
                )

    # Validate retry settings
    if "retry_settings" in error_config:
        retry_config = error_config["retry_settings"]

        if "max_retries" in retry_config:
            value = retry_config["max_retries"]
            if not isinstance(value, int) or value < 0:
                raise ConfigError(
                    f"Invalid max_retries value: {value}. Must be non-negative integer."
                )

        if "base_delay" in retry_config:
            value = retry_config["base_delay"]
            if not isinstance(value, int | float) or value <= 0:
                raise ConfigError(f"Invalid base_delay value: {value}. Must be positive number.")

        if "max_delay" in retry_config:
            value = retry_config["max_delay"]
            if not isinstance(value, int | float) or value <= 0:
                raise ConfigError(f"Invalid max_delay value: {value}. Must be positive number.")

        if "exponential_base" in retry_config:
            value = retry_config["exponential_base"]
            if not isinstance(value, int | float) or value <= 1:
                raise ConfigError(
                    f"Invalid exponential_base value: {value}. Must be greater than 1."
                )

    # Validate logging settings
    if "logging" in error_config:
        logging_config = error_config["logging"]

        for key in ["include_stack_traces", "include_request_context", "include_user_parameters"]:
            if key in logging_config:
                value = logging_config[key]
                if not isinstance(value, bool):
                    raise ConfigError(f"Invalid {key} value: {value}. Must be boolean.")

        if "log_level" in logging_config:
            value = logging_config["log_level"]
            valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
            if not isinstance(value, str) or value.upper() not in valid_levels:
                raise ConfigError(
                    f"Invalid log_level value: {value}. Must be one of: {', '.join(valid_levels)}"
                )
