# api_key_generator

Cryptographically secure API key generator for DShield MCP.

This module provides secure API key generation with configurable length,
character sets, and metadata handling. All keys are generated using
cryptographically secure random number generators.

Features:
- Configurable key length and character sets
- SHA-256 hashing with salt for storage
- Metadata validation and sanitization
- Rate limiting and permission enforcement
- Expiration date handling

## APIKeyGenerator

Cryptographically secure API key generator.

    This class provides methods for generating secure API keys with
    configurable parameters and metadata handling.

    Attributes:
        default_length: Default key length in characters
        default_charset: Default character set for key generation
        salt_length: Length of salt for hashing (bytes)

#### __init__

```python
def __init__(self, default_length, default_charset, salt_length)
```

Initialize the API key generator.

        Args:
            default_length: Default key length in characters
            default_charset: Default character set for key generation
            salt_length: Length of salt for hashing (bytes)

#### generate_key

```python
def generate_key(self, length, charset, prefix)
```

Generate a cryptographically secure API key.

        Args:
            length: Key length in characters (defaults to self.default_length)
            charset: Character set to use (defaults to self.default_charset)
            prefix: Prefix to add to the key

        Returns:
            Generated API key string

        Raises:
            ValueError: If length is invalid or charset is empty

#### generate_key_with_metadata

```python
def generate_key_with_metadata(self, name, permissions, expiration_days, rate_limit, length, charset, prefix)
```

Generate an API key with associated metadata.

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

#### hash_key

```python
def hash_key(self, key_value, salt)
```

Hash an API key for secure storage.

        Args:
            key_value: The API key to hash
            salt: Optional salt (generated if not provided)

        Returns:
            Dictionary containing the hash and salt

#### verify_key

```python
def verify_key(self, key_value, stored_hash, salt_hex)
```

Verify an API key against its stored hash.

        Args:
            key_value: The API key to verify
            stored_hash: The stored hash to compare against
            salt_hex: The salt used for hashing (hex encoded)

        Returns:
            True if the key matches the hash, False otherwise

#### validate_permissions

```python
def validate_permissions(self, permissions)
```

Validate API key permissions.

        Args:
            permissions: Dictionary of permissions to validate

        Returns:
            True if permissions are valid, False otherwise

#### sanitize_metadata

```python
def sanitize_metadata(self, metadata)
```

Sanitize metadata for safe storage.

        Args:
            metadata: Raw metadata dictionary

        Returns:
            Sanitized metadata dictionary

#### create_key_id

```python
def create_key_id(self)
```

Create a unique key ID.

        Returns:
            Unique key identifier

#### get_key_statistics

```python
def get_key_statistics(self)
```

Get statistics about key generation.

        Returns:
            Dictionary of key generation statistics
