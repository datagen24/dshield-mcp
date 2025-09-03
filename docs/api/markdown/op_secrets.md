# op_secrets

1Password CLI integration for secret management in DShield MCP.

This module provides integration with the 1Password CLI for secure secret
management. It handles op:// URLs in configuration values by resolving
them using the 1Password CLI tool.

Features:
- 1Password CLI availability detection
- op:// URL resolution
- Environment variable resolution
- Complex value processing with embedded URLs
- Error handling and logging
- Backward compatibility with existing API

Example:
    >>> from src.op_secrets import OnePasswordSecrets
    >>> op = OnePasswordSecrets()
    >>> secret = op.resolve_environment_variable("op://vault/item/field")
    >>> print(secret)

## OnePasswordSecrets

Handle 1Password secret resolution for config values.

    This class provides methods to resolve 1Password CLI references (op:// URLs)
    in configuration values. It automatically detects 1Password CLI availability
    and provides fallback behavior when the CLI is not available.

    Attributes:
        op_available: Whether the 1Password CLI is available and working

    Example:
        >>> op = OnePasswordSecrets()
        >>> if op.op_available:
        ...     secret = op.resolve_op_url("op://vault/item/field")
        ...     print(secret)

#### __init__

```python
def __init__(self)
```

Initialize the OnePasswordSecrets manager.

        Checks for 1Password CLI availability and logs a warning if it's not
        available. This affects the behavior of URL resolution methods.

#### _check_op_cli

```python
def _check_op_cli(self)
```

Check if 1Password CLI is available.

        Attempts to run the 1Password CLI version command to verify
        that the tool is installed and accessible.

        Returns:
            True if 1Password CLI is available, False otherwise

#### resolve_op_url

```python
def resolve_op_url(self, op_url)
```

Resolve a 1Password URL (op://) to its actual value.

        Uses the 1Password CLI to retrieve the secret value referenced
        by the op:// URL. Handles various error conditions gracefully.

        Args:
            op_url: The 1Password URL (e.g., "op://vault/item/field")

        Returns:
            The resolved secret value or None if resolution failed

        Raises:
            subprocess.TimeoutExpired: If the CLI command times out
            subprocess.CalledProcessError: If the CLI command fails

#### resolve_environment_variable

```python
def resolve_environment_variable(self, value)
```

Resolve config value, handling op:// URLs.

        Processes a configuration value that may contain 1Password CLI
        references. Handles both simple op:// URLs and complex values
        with embedded URLs.

        Args:
            value: The config value to resolve

        Returns:
            The resolved value (original if not an op:// URL or resolution failed)

## OnePasswordAPIKeyManager

Enhanced 1Password integration for API key management.

    This class provides comprehensive API key management using the new
    secrets abstraction layer while maintaining compatibility with
    existing op:// URL resolution functionality.

    Attributes:
        secrets_manager: The underlying OnePasswordCLIManager instance
        op_secrets: The legacy OnePasswordSecrets instance for URL resolution

#### __init__

```python
def __init__(self, vault)
```

Initialize the API key manager.

        Args:
            vault: The 1Password vault to use for API key storage

#### resolve_environment_variable

```python
def resolve_environment_variable(self, value)
```

Resolve config value, handling op:// URLs (backward compatibility).

        This method provides backward compatibility with the existing
        OnePasswordSecrets.resolve_environment_variable method.

        Args:
            value: The config value to resolve

        Returns:
            The resolved value
