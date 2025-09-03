# base_secrets_manager

Base secrets manager abstraction for DShield MCP.

This module defines the abstract interface for secrets management providers,
allowing the system to work with different backends (1Password, HashiCorp Vault, etc.)
through a consistent interface.

## APIKey

Represents an API key with metadata and permissions.

    Attributes:
        key_id: Unique identifier for the API key
        key_value: The actual API key value
        name: Human-readable name for the key
        created_at: When the key was created
        expires_at: When the key expires (None for no expiration)
        permissions: Dictionary of permissions granted to this key
        metadata: Additional metadata for the key

## BaseSecretsManager

Abstract base class for secrets management providers.

    This class defines the interface that all secrets management providers
    must implement, ensuring consistent behavior across different backends.
