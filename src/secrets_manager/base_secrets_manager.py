"""Base secrets manager abstraction for DShield MCP.

This module defines the abstract interface for secrets management providers,
allowing the system to work with different backends (1Password, HashiCorp Vault, etc.)
through a consistent interface.

The module provides:
- Abstract base class for secrets management providers
- Exception hierarchy for consistent error handling
- Data models for secrets and metadata
- Caching hooks for performance optimization
- Reference URI resolution and validation
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


class SecretsManagerError(Exception):
    """Base exception for all secrets manager operations.

    This is the root exception class for all secrets management errors.
    All specific error types inherit from this class.
    """

    pass


class SecretNotFoundError(SecretsManagerError):
    """Raised when a requested secret is not found.

    This exception is raised when attempting to retrieve, update, or delete
    a secret that doesn't exist in the backend.
    """

    pass


class PermissionDeniedError(SecretsManagerError):
    """Raised when access to a secret is denied due to insufficient permissions.

    This exception is raised when the current user or service account
    doesn't have the necessary permissions to perform the requested operation.
    """

    pass


class RateLimitedError(SecretsManagerError):
    """Raised when the secrets manager backend is rate limiting requests.

    This exception is raised when the backend service is throttling requests
    due to rate limits or quota restrictions.
    """

    pass


class BackendUnavailableError(SecretsManagerError):
    """Raised when the secrets manager backend is unavailable.

    This exception is raised when the backend service is down, unreachable,
    or experiencing issues that prevent normal operation.
    """

    pass


class InvalidReferenceError(SecretsManagerError):
    """Raised when a secret reference URI is invalid or malformed.

    This exception is raised when attempting to resolve a reference URI
    that doesn't match the expected format or contains invalid components.
    """

    pass


@dataclass
class SecretMetadata:
    """Metadata for a secret including tags, lifecycle, and audit information.

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
    """

    name: str
    description: str | None = None
    tags: set[str] = field(default_factory=set)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    last_accessed_at: datetime | None = None
    access_count: int = 0
    created_by: str | None = None
    updated_by: str | None = None
    custom_attributes: dict[str, Any] = field(default_factory=dict)


@dataclass
class APIKey:
    """Represents an API key with metadata and permissions.

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

    """

    key_id: str
    key_value: str
    name: str
    created_at: datetime
    expires_at: datetime | None
    permissions: dict[str, Any]
    metadata: dict[str, Any]
    algo_version: str = "sha256-v1"
    needs_rotation: bool = False
    rps_limit: int = 60
    verifier: str | None = None

    def is_expired(self) -> bool:
        """Check if the API key has expired.

        Returns:
            True if the key has expired, False otherwise

        """
        if self.expires_at is None:
            return False
        return datetime.now(UTC) > self.expires_at

    def is_valid(self) -> bool:
        """Check if the API key is valid (not expired and not needing rotation).

        Returns:
            True if the key is valid, False otherwise

        """
        return not self.is_expired() and not self.needs_rotation

    @property
    def is_active(self) -> bool:
        """Check if the API key is active (not needing rotation).

        Returns:
            True if the key is active, False otherwise

        """
        return not self.needs_rotation

    def update_usage(self) -> None:
        """Update the usage statistics for this key.

        This is a placeholder method for compatibility with the connection manager.
        The canonical APIKey class doesn't track usage statistics, but this method
        is called by the connection manager for consistency.
        """
        pass


@dataclass
class SecretReference:
    """Represents a reference to a secret in a specific backend.

    This class handles the resolution and validation of secret reference URIs
    like 'op://vault/item/field' for 1Password or 'vault://path/to/secret' for Vault.

    Attributes:
        uri: The full reference URI
        backend: The backend type (e.g., 'op', 'vault', 'aws')
        vault: The vault or namespace identifier
        item: The item or secret identifier
        field: The specific field within the item (optional)
        is_valid: Whether the reference URI is valid
    """

    uri: str
    backend: str | None = None
    vault: str | None = None
    item: str | None = None
    field: str | None = None
    is_valid: bool = False

    def __post_init__(self) -> None:
        """Parse and validate the reference URI after initialization."""
        self._parse_uri()

    def _parse_uri(self) -> None:
        """Parse the reference URI and extract components.

        Supports formats like:
        - op://vault/item/field
        - vault://path/to/secret
        - aws://region/secret-name
        """
        if not self.uri:
            self.is_valid = False
            return

        # Pattern for op://vault/item/field format
        op_pattern = r'^op://([^/]+)/([^/]+)(?:/(.+))?$'
        op_match = re.match(op_pattern, self.uri)
        if op_match:
            self.backend = 'op'
            self.vault = op_match.group(1)
            self.item = op_match.group(2)
            self.field = op_match.group(3)
            self.is_valid = True
            return

        # Pattern for vault://path/to/secret format
        vault_pattern = r'^vault://([^/]+(?:/.*)?)$'
        vault_match = re.match(vault_pattern, self.uri)
        if vault_match:
            self.backend = 'vault'
            self.item = vault_match.group(1)
            self.is_valid = True
            return

        # Pattern for aws://region/secret-name format
        aws_pattern = r'^aws://([^/]+)/(.+)$'
        aws_match = re.match(aws_pattern, self.uri)
        if aws_match:
            self.backend = 'aws'
            self.vault = aws_match.group(1)  # region
            self.item = aws_match.group(2)  # secret name
            self.is_valid = True
            return

        self.is_valid = False


class BaseSecretsManager(ABC):
    """Abstract base class for secrets management providers.

    This class defines the interface that all secrets management providers
    must implement, ensuring consistent behavior across different backends.

    The class provides:
    - Abstract methods for CRUD operations on secrets
    - Error handling with proper exception translation
    - Caching hooks for performance optimization
    - Reference URI validation and resolution
    - Health checking and availability monitoring
    """

    def __init__(self, enable_caching: bool = True, cache_ttl_seconds: int = 300) -> None:
        """Initialize the base secrets manager.

        Args:
            enable_caching: Whether to enable in-memory caching
            cache_ttl_seconds: Time-to-live for cached secrets in seconds
        """
        self._enable_caching = enable_caching
        self._cache_ttl_seconds = cache_ttl_seconds
        self._cache: dict[str, tuple[Any, datetime]] = {}

    def _normalize_cache_key(self, key: str) -> str:
        """Normalize a cache key for consistent storage and retrieval.

        Args:
            key: The original key to normalize

        Returns:
            Normalized cache key
        """
        return key.lower().strip()

    def _is_cache_valid(self, cache_entry: tuple[Any, datetime]) -> bool:
        """Check if a cache entry is still valid based on TTL.

        Args:
            cache_entry: Tuple of (value, timestamp)

        Returns:
            True if the cache entry is still valid, False otherwise
        """
        if not self._enable_caching:
            return False
        value, timestamp = cache_entry
        age = (datetime.now(UTC) - timestamp).total_seconds()
        return age < self._cache_ttl_seconds

    def _get_from_cache(self, key: str) -> Any | None:
        """Retrieve a value from the cache if valid.

        Args:
            key: The cache key to retrieve

        Returns:
            Cached value if valid, None otherwise
        """
        if not self._enable_caching:
            return None

        normalized_key = self._normalize_cache_key(key)
        if normalized_key in self._cache:
            cache_entry = self._cache[normalized_key]
            if self._is_cache_valid(cache_entry):
                return cache_entry[0]
            else:
                # Remove expired entry
                del self._cache[normalized_key]
        return None

    def _set_cache(self, key: str, value: Any) -> None:
        """Store a value in the cache.

        Args:
            key: The cache key
            value: The value to cache
        """
        if not self._enable_caching:
            return

        normalized_key = self._normalize_cache_key(key)
        self._cache[normalized_key] = (value, datetime.now(UTC))

    def _clear_cache(self, key: str | None = None) -> None:
        """Clear cache entries.

        Args:
            key: Specific key to clear, or None to clear all
        """
        if not self._enable_caching:
            return

        if key is None:
            self._cache.clear()
        else:
            normalized_key = self._normalize_cache_key(key)
            self._cache.pop(normalized_key, None)

    def validate_reference(self, reference_uri: str) -> SecretReference:
        """Validate and parse a secret reference URI.

        Args:
            reference_uri: The reference URI to validate

        Returns:
            SecretReference object with parsed components

        Raises:
            InvalidReferenceError: If the reference URI is invalid
        """
        reference = SecretReference(uri=reference_uri)
        if not reference.is_valid:
            raise InvalidReferenceError(f"Invalid reference URI: {reference_uri}")
        return reference

    @abstractmethod
    async def store_api_key(self, api_key: APIKey) -> bool:
        """Store an API key in the secrets manager.

        Args:
            api_key: The API key object to store

        Returns:
            True if the key was stored successfully, False otherwise

        Raises:
            PermissionDeniedError: If insufficient permissions to store the key
            BackendUnavailableError: If the secrets manager backend is unavailable
            SecretsManagerError: For other storage-related errors

        """
        pass

    @abstractmethod
    async def retrieve_api_key(self, key_id: str) -> APIKey | None:
        """Retrieve an API key by ID.

        Args:
            key_id: The unique identifier of the API key

        Returns:
            The API key object if found, None otherwise

        Raises:
            SecretNotFoundError: If the key is not found
            PermissionDeniedError: If insufficient permissions to retrieve the key
            BackendUnavailableError: If the secrets manager backend is unavailable
            RateLimitedError: If the request is rate limited
            SecretsManagerError: For other retrieval-related errors

        """
        pass

    @abstractmethod
    async def list_api_keys(self) -> list[APIKey]:
        """List all API keys stored in the secrets manager.

        Returns:
            List of all API key objects

        Raises:
            PermissionDeniedError: If insufficient permissions to list keys
            BackendUnavailableError: If the secrets manager backend is unavailable
            RateLimitedError: If the request is rate limited
            SecretsManagerError: For other listing-related errors

        """
        pass

    @abstractmethod
    async def delete_api_key(self, key_id: str) -> bool:
        """Delete an API key from the secrets manager.

        Args:
            key_id: The unique identifier of the API key to delete

        Returns:
            True if the key was deleted successfully, False otherwise

        Raises:
            SecretNotFoundError: If the key is not found
            PermissionDeniedError: If insufficient permissions to delete the key
            BackendUnavailableError: If the secrets manager backend is unavailable
            SecretsManagerError: For other deletion-related errors

        """
        pass

    @abstractmethod
    async def update_api_key(self, api_key: APIKey) -> bool:
        """Update an existing API key in the secrets manager.

        Args:
            api_key: The updated API key object

        Returns:
            True if the key was updated successfully, False otherwise

        Raises:
            SecretNotFoundError: If the key is not found
            PermissionDeniedError: If insufficient permissions to update the key
            BackendUnavailableError: If the secrets manager backend is unavailable
            SecretsManagerError: For other update-related errors

        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the secrets manager is available and properly configured.

        Returns:
            True if the secrets manager is healthy, False otherwise

        Raises:
            BackendUnavailableError: If the backend is completely unavailable
            SecretsManagerError: For other health check errors

        """
        pass

    async def get_secret_by_reference(self, reference_uri: str) -> str | None:
        """Retrieve a secret value by reference URI.

        This is a convenience method that validates the reference URI and
        delegates to the backend-specific implementation.

        Args:
            reference_uri: The reference URI to resolve

        Returns:
            The secret value if found, None otherwise

        Raises:
            InvalidReferenceError: If the reference URI is invalid
            SecretNotFoundError: If the secret is not found
            PermissionDeniedError: If insufficient permissions
            BackendUnavailableError: If the backend is unavailable
            RateLimitedError: If the request is rate limited
            SecretsManagerError: For other errors
        """
        reference = self.validate_reference(reference_uri)
        return await self._get_secret_by_reference_impl(reference)

    @abstractmethod
    async def _get_secret_by_reference_impl(self, reference: SecretReference) -> str | None:
        """Backend-specific implementation for retrieving secrets by reference.

        Args:
            reference: The parsed secret reference

        Returns:
            The secret value if found, None otherwise

        Raises:
            SecretNotFoundError: If the secret is not found
            PermissionDeniedError: If insufficient permissions
            BackendUnavailableError: If the backend is unavailable
            RateLimitedError: If the request is rate limited
            SecretsManagerError: For other errors
        """
        pass

    def clear_cache(self) -> None:
        """Clear all cached secrets.

        This method can be called to force a refresh of all cached data.
        """
        self._clear_cache()
