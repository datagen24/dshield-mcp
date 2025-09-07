"""Cryptographically secure API key generator for DShield MCP.

This module provides secure API key generation with configurable length,
character sets, and metadata handling. All keys are generated using
cryptographically secure random number generators.

Features:
- Configurable key length and character sets
- SHA-256 hashing with salt for storage
- Metadata validation and sanitization
- Rate limiting and permission enforcement
- Expiration date handling
"""

import hashlib
import secrets
import string
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class APIKeyGenerator:
    """Cryptographically secure API key generator.

    This class provides methods for generating secure API keys with
    configurable parameters and metadata handling.

    Attributes:
        default_length: Default key length in characters
        default_charset: Default character set for key generation
        salt_length: Length of salt for hashing (bytes)
    """

    def __init__(
        self,
        default_length: int = 32,
        default_charset: str = string.ascii_letters + string.digits,
        salt_length: int = 16,
    ) -> None:
        """Initialize the API key generator.

        Args:
            default_length: Default key length in characters
            default_charset: Default character set for key generation
            salt_length: Length of salt for hashing (bytes)

        """
        self.default_length = default_length
        self.default_charset = default_charset
        self.salt_length = salt_length
        self.logger = structlog.get_logger(__name__)

    def generate_key(
        self,
        length: int | None = None,
        charset: str | None = None,
        prefix: str = "dshield_",
    ) -> str:
        """Generate a cryptographically secure API key.

        Args:
            length: Key length in characters (defaults to self.default_length)
            charset: Character set to use (defaults to self.default_charset)
            prefix: Prefix to add to the key

        Returns:
            Generated API key string

        Raises:
            ValueError: If length is invalid or charset is empty

        """
        if length is None:
            length = self.default_length
        if charset is None:
            charset = self.default_charset

        if length <= 0:
            raise ValueError("Key length must be positive")
        if not charset:
            raise ValueError("Character set cannot be empty")

        # Generate random key using cryptographically secure random
        key_part = "".join(secrets.choice(charset) for _ in range(length))
        full_key = f"{prefix}{key_part}"

        self.logger.debug(
            "Generated API key",
            length=len(full_key),
            prefix=prefix,
            charset_length=len(charset),
        )

        return full_key

    def generate_key_with_metadata(
        self,
        name: str,
        permissions: dict[str, Any],
        expiration_days: int | None = None,
        rate_limit: int | None = None,
        length: int | None = None,
        charset: str | None = None,
        prefix: str = "dshield_",
    ) -> dict[str, Any]:
        """Generate an API key with associated metadata.

        Args:
            name: Human-readable name for the key
            permissions: Dictionary of permissions
            expiration_days: Days until expiration (None for no expiration)
            rate_limit: Rate limit in requests per minute
            length: Key length in characters
            charset: Character set to use
            prefix: Prefix to add to the key

        Returns:
            Dictionary containing the key and metadata

        Raises:
            ValueError: If parameters are invalid

        """
        # Validate inputs
        if not name or not name.strip():
            raise ValueError("Key name cannot be empty")
        if not isinstance(permissions, dict):
            raise ValueError("Permissions must be a dictionary")
        if expiration_days is not None and expiration_days <= 0:
            raise ValueError("Expiration days must be positive")
        if rate_limit is not None and rate_limit <= 0:
            raise ValueError("Rate limit must be positive")

        # Generate the key
        key_value = self.generate_key(length, charset, prefix)

        # Calculate expiration date
        expires_at = None
        if expiration_days:
            expires_at = datetime.now(UTC) + timedelta(days=expiration_days)

        # Set default rate limit
        if rate_limit is None:
            rate_limit = permissions.get("rate_limit", 60)

        # Create metadata
        metadata = {
            "generated_by": "dshield-mcp",
            "version": "1.0",
            "generated_at": datetime.now(UTC).isoformat(),
            "key_type": "api_key",
        }

        # Create the result
        result = {
            "key_value": key_value,
            "name": name.strip(),
            "permissions": permissions,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "rate_limit": rate_limit,
            "metadata": metadata,
            "created_at": datetime.now(UTC),
        }

        self.logger.info(
            "Generated API key with metadata",
            name=name,
            key_length=len(key_value),
            expiration_days=expiration_days,
            rate_limit=rate_limit,
        )

        return result

    def hash_key(self, key_value: str, salt: bytes | None = None) -> dict[str, str]:
        """Hash an API key for secure storage.

        Args:
            key_value: The API key to hash
            salt: Optional salt (generated if not provided)

        Returns:
            Dictionary containing the hash and salt

        """
        if salt is None:
            salt = secrets.token_bytes(self.salt_length)

        # Create hash using SHA-256
        hash_obj = hashlib.sha256()
        hash_obj.update(salt)
        hash_obj.update(key_value.encode("utf-8"))
        key_hash = hash_obj.hexdigest()

        return {
            "hash": key_hash,
            "salt": salt.hex(),
            "algorithm": "sha256",
        }

    def verify_key(self, key_value: str, stored_hash: str, salt_hex: str) -> bool:
        """Verify an API key against its stored hash.

        Args:
            key_value: The API key to verify
            stored_hash: The stored hash to compare against
            salt_hex: The salt used for hashing (hex encoded)

        Returns:
            True if the key matches the hash, False otherwise

        """
        try:
            salt = bytes.fromhex(salt_hex)
            computed_hash = self.hash_key(key_value, salt)["hash"]
            return secrets.compare_digest(computed_hash, stored_hash)
        except (ValueError, TypeError) as e:
            self.logger.warning("Error verifying key", error=str(e))
            return False

    def validate_permissions(self, permissions: dict[str, Any]) -> bool:
        """Validate API key permissions.

        Args:
            permissions: Dictionary of permissions to validate

        Returns:
            True if permissions are valid, False otherwise

        """
        if not isinstance(permissions, dict):
            return False

        # Define allowed permission keys
        allowed_permissions = {
            "read_tools",
            "write_back",
            "admin_access",
            "rate_limit",
        }

        # Check if all keys are allowed
        for key in permissions.keys():
            if key not in allowed_permissions:
                self.logger.warning("Invalid permission key", key=key)
                return False

        # Validate rate limit if present
        if "rate_limit" in permissions:
            rate_limit = permissions["rate_limit"]
            if not isinstance(rate_limit, int) or rate_limit <= 0:
                self.logger.warning("Invalid rate limit", rate_limit=rate_limit)
                return False

        # Validate boolean permissions
        boolean_permissions = {"read_tools", "write_back", "admin_access"}
        for perm in boolean_permissions:
            if perm in permissions:
                if not isinstance(permissions[perm], bool):
                    self.logger.warning("Invalid boolean permission", permission=perm)
                    return False

        return True

    def sanitize_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Sanitize metadata for safe storage.

        Args:
            metadata: Raw metadata dictionary

        Returns:
            Sanitized metadata dictionary

        """
        if not isinstance(metadata, dict):
            return {}

        # Define allowed metadata keys
        allowed_keys = {
            "generated_by",
            "version",
            "generated_at",
            "key_type",
            "description",
            "tags",
        }

        # Filter and sanitize metadata
        sanitized = {}
        for key, value in metadata.items():
            if key in allowed_keys:
                if isinstance(value, (str, int, float, bool, list, dict)):
                    sanitized[key] = value
                else:
                    # Convert to string for safety
                    sanitized[key] = str(value)

        return sanitized

    def create_key_id(self) -> str:
        """Create a unique key ID.

        Returns:
            Unique key identifier

        """
        return secrets.token_urlsafe(16)

    def get_key_statistics(self) -> dict[str, Any]:
        """Get statistics about key generation.

        Returns:
            Dictionary of key generation statistics

        """
        return {
            "default_length": self.default_length,
            "default_charset_length": len(self.default_charset),
            "salt_length": self.salt_length,
            "generator_version": "1.0",
        }
