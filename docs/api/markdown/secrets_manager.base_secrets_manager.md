# base_secrets_manager

Base secrets manager abstraction for DShield MCP.

This module defines the abstract interface for secrets management providers,
allowing the system to work with different backends (1Password, HashiCorp Vault, etc.)
through a consistent interface.

The module provides:
- Abstract base class for secrets management providers
- Exception hierarchy for consistent error handling
- Data models for secrets and metadata
- Caching hooks for performance optimization
- Reference URI resolution and validation

## SecretsManagerError

Base exception for all secrets manager operations.

    This is the root exception class for all secrets management errors.
    All specific error types inherit from this class.

## SecretNotFoundError

Raised when a requested secret is not found.

    This exception is raised when attempting to retrieve, update, or delete
    a secret that doesn't exist in the backend.

## PermissionDeniedError

Raised when access to a secret is denied due to insufficient permissions.

    This exception is raised when the current user or service account
    doesn't have the necessary permissions to perform the requested operation.

## RateLimitedError

Raised when the secrets manager backend is rate limiting requests.

    This exception is raised when the backend service is throttling requests
    due to rate limits or quota restrictions.

## BackendUnavailableError

Raised when the secrets manager backend is unavailable.

    This exception is raised when the backend service is down, unreachable,
    or experiencing issues that prevent normal operation.

## InvalidReferenceError

Raised when a secret reference URI is invalid or malformed.

    This exception is raised when attempting to resolve a reference URI
    that doesn't match the expected format or contains invalid components.

## SecretMetadata

Metadata for a secret including tags, lifecycle, and audit information.

    Attributes:
        name: Human-readable name for the secret
        description: Optional description of the secret's purpose
        tags: Set of tags for categorization and filtering
        created_at: When the secret was created
        updated_at: When the secret was last updated
        expires_at: When the secret expires (None for no expiration)
        last_accessed_at: When the secret was last accessed (None if never accessed)
        access_count: Number of times the secret has been accessed
        created_by: User or service that created the secret
        updated_by: User or service that last updated the secret
        custom_attributes: Additional custom attributes specific to the backend

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
        algo_version: Algorithm version for hash verification
        needs_rotation: Whether the key needs rotation (missing plaintext)
        rps_limit: Rate limit in requests per second
        verifier: Server-side verifier hash (not stored in 1Password)

#### is_expired

```python
def is_expired(self)
```

Check if the API key has expired.

        Returns:
            True if the key has expired, False otherwise

#### is_valid

```python
def is_valid(self)
```

Check if the API key is valid (not expired and not needing rotation).

        Returns:
            True if the key is valid, False otherwise

#### is_active

```python
def is_active(self)
```

Check if the API key is active (not needing rotation).

        Returns:
            True if the key is active, False otherwise

#### update_usage

```python
def update_usage(self)
```

Update the usage statistics for this key.

        This is a placeholder method for compatibility with the connection manager.
        The canonical APIKey class doesn't track usage statistics, but this method
        is called by the connection manager for consistency.

## SecretReference

Represents a reference to a secret in a specific backend.

    This class handles the resolution and validation of secret reference URIs
    like 'op://vault/item/field' for 1Password or 'vault://path/to/secret' for Vault.

    Attributes:
        uri: The full reference URI
        backend: The backend type (e.g., 'op', 'vault', 'aws')
        vault: The vault or namespace identifier
        item: The item or secret identifier
        field: The specific field within the item (optional)
        is_valid: Whether the reference URI is valid

#### __post_init__

```python
def __post_init__(self)
```

Parse and validate the reference URI after initialization.

#### _parse_uri

```python
def _parse_uri(self)
```

Parse the reference URI and extract components.

        Supports formats like:
        - op://vault/item/field
        - vault://path/to/secret
        - aws://region/secret-name

## BaseSecretsManager

Abstract base class for secrets management providers.

    This class defines the interface that all secrets management providers
    must implement, ensuring consistent behavior across different backends.

    The class provides:
    - Abstract methods for CRUD operations on secrets
    - Error handling with proper exception translation
    - Caching hooks for performance optimization
    - Reference URI validation and resolution
    - Health checking and availability monitoring

#### __init__

```python
def __init__(self, enable_caching, cache_ttl_seconds)
```

Initialize the base secrets manager.

        Args:
            enable_caching: Whether to enable in-memory caching
            cache_ttl_seconds: Time-to-live for cached secrets in seconds

#### _normalize_cache_key

```python
def _normalize_cache_key(self, key)
```

Normalize a cache key for consistent storage and retrieval.

        Args:
            key: The original key to normalize

        Returns:
            Normalized cache key

#### _is_cache_valid

```python
def _is_cache_valid(self, cache_entry)
```

Check if a cache entry is still valid based on TTL.

        Args:
            cache_entry: Tuple of (value, timestamp)

        Returns:
            True if the cache entry is still valid, False otherwise

#### _get_from_cache

```python
def _get_from_cache(self, key)
```

Retrieve a value from the cache if valid.

        Args:
            key: The cache key to retrieve

        Returns:
            Cached value if valid, None otherwise

#### _set_cache

```python
def _set_cache(self, key, value)
```

Store a value in the cache.

        Args:
            key: The cache key
            value: The value to cache

#### _clear_cache

```python
def _clear_cache(self, key)
```

Clear cache entries.

        Args:
            key: Specific key to clear, or None to clear all

#### validate_reference

```python
def validate_reference(self, reference_uri)
```

Validate and parse a secret reference URI.

        Args:
            reference_uri: The reference URI to validate

        Returns:
            SecretReference object with parsed components

        Raises:
            InvalidReferenceError: If the reference URI is invalid

#### clear_cache

```python
def clear_cache(self)
```

Clear all cached secrets.

        This method can be called to force a refresh of all cached data.
