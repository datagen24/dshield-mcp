"""Tests for API key generator functionality.

This module contains comprehensive tests for the API key generator,
including key generation, hashing, validation, and metadata handling.
"""

from datetime import UTC, datetime

import pytest

from src.api_key_generator import APIKeyGenerator


class TestAPIKeyGenerator:
    """Test cases for APIKeyGenerator class."""

    def test_init_defaults(self) -> None:
        """Test APIKeyGenerator initialization with default values."""
        generator = APIKeyGenerator()
        
        assert generator.default_length == 32
        assert generator.default_charset == "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        assert generator.salt_length == 16

    def test_init_custom_values(self) -> None:
        """Test APIKeyGenerator initialization with custom values."""
        generator = APIKeyGenerator(
            default_length=64,
            default_charset="abc123",
            salt_length=32
        )
        
        assert generator.default_length == 64
        assert generator.default_charset == "abc123"
        assert generator.salt_length == 32

    def test_generate_key_defaults(self) -> None:
        """Test key generation with default parameters."""
        generator = APIKeyGenerator()
        key = generator.generate_key()
        
        assert isinstance(key, str)
        assert key.startswith("dshield_")
        assert len(key) == 32 + len("dshield_")  # 32 chars + prefix

    def test_generate_key_custom_length(self) -> None:
        """Test key generation with custom length."""
        generator = APIKeyGenerator()
        key = generator.generate_key(length=16)
        
        assert isinstance(key, str)
        assert key.startswith("dshield_")
        assert len(key) == 16 + len("dshield_")

    def test_generate_key_custom_charset(self) -> None:
        """Test key generation with custom character set."""
        generator = APIKeyGenerator()
        charset = "abc"
        key = generator.generate_key(charset=charset)
        
        assert isinstance(key, str)
        assert key.startswith("dshield_")
        # Check that all characters after prefix are from the charset
        key_part = key[len("dshield_"):]
        assert all(c in charset for c in key_part)

    def test_generate_key_custom_prefix(self) -> None:
        """Test key generation with custom prefix."""
        generator = APIKeyGenerator()
        prefix = "test_"
        key = generator.generate_key(prefix=prefix)
        
        assert isinstance(key, str)
        assert key.startswith(prefix)

    def test_generate_key_invalid_length(self) -> None:
        """Test key generation with invalid length."""
        generator = APIKeyGenerator()
        
        with pytest.raises(ValueError, match="Key length must be positive"):
            generator.generate_key(length=0)
        
        with pytest.raises(ValueError, match="Key length must be positive"):
            generator.generate_key(length=-1)

    def test_generate_key_empty_charset(self) -> None:
        """Test key generation with empty character set."""
        generator = APIKeyGenerator()
        
        with pytest.raises(ValueError, match="Character set cannot be empty"):
            generator.generate_key(charset="")

    def test_generate_key_with_metadata(self) -> None:
        """Test key generation with metadata."""
        generator = APIKeyGenerator()
        name = "Test Key"
        permissions = {"read_tools": True, "write_back": False}
        expiration_days = 30
        rate_limit = 100
        
        result = generator.generate_key_with_metadata(
            name=name,
            permissions=permissions,
            expiration_days=expiration_days,
            rate_limit=rate_limit
        )
        
        assert isinstance(result, dict)
        assert "key_value" in result
        assert "name" in result
        assert "permissions" in result
        assert "expires_at" in result
        assert "rate_limit" in result
        assert "metadata" in result
        assert "created_at" in result
        
        assert result["name"] == name
        assert result["permissions"] == permissions
        assert result["rate_limit"] == rate_limit
        assert result["key_value"].startswith("dshield_")
        
        # Check expiration date
        expires_at = datetime.fromisoformat(result["expires_at"])
        now = datetime.now(UTC)
        assert (expires_at - now).days <= 30

    def test_generate_key_with_metadata_no_expiration(self) -> None:
        """Test key generation with no expiration."""
        generator = APIKeyGenerator()
        
        result = generator.generate_key_with_metadata(
            name="Test Key",
            permissions={"read_tools": True},
            expiration_days=None
        )
        
        assert result["expires_at"] is None

    def test_generate_key_with_metadata_invalid_name(self) -> None:
        """Test key generation with invalid name."""
        generator = APIKeyGenerator()
        
        with pytest.raises(ValueError, match="Key name cannot be empty"):
            generator.generate_key_with_metadata(name="", permissions={})
        
        with pytest.raises(ValueError, match="Key name cannot be empty"):
            generator.generate_key_with_metadata(name="   ", permissions={})

    def test_generate_key_with_metadata_invalid_permissions(self) -> None:
        """Test key generation with invalid permissions."""
        generator = APIKeyGenerator()
        
        with pytest.raises(ValueError, match="Permissions must be a dictionary"):
            generator.generate_key_with_metadata(name="Test", permissions="invalid")

    def test_generate_key_with_metadata_invalid_expiration(self) -> None:
        """Test key generation with invalid expiration."""
        generator = APIKeyGenerator()
        
        with pytest.raises(ValueError, match="Expiration days must be positive"):
            generator.generate_key_with_metadata(
                name="Test", 
                permissions={}, 
                expiration_days=0
            )
        
        with pytest.raises(ValueError, match="Expiration days must be positive"):
            generator.generate_key_with_metadata(
                name="Test", 
                permissions={}, 
                expiration_days=-1
            )

    def test_generate_key_with_metadata_invalid_rate_limit(self) -> None:
        """Test key generation with invalid rate limit."""
        generator = APIKeyGenerator()
        
        with pytest.raises(ValueError, match="Rate limit must be positive"):
            generator.generate_key_with_metadata(
                name="Test", 
                permissions={}, 
                rate_limit=0
            )
        
        with pytest.raises(ValueError, match="Rate limit must be positive"):
            generator.generate_key_with_metadata(
                name="Test", 
                permissions={}, 
                rate_limit=-1
            )

    def test_hash_key(self) -> None:
        """Test key hashing functionality."""
        generator = APIKeyGenerator()
        key_value = "test_key_123"
        
        result = generator.hash_key(key_value)
        
        assert isinstance(result, dict)
        assert "hash" in result
        assert "salt" in result
        assert "algorithm" in result
        
        assert result["algorithm"] == "sha256"
        assert len(result["salt"]) == 32  # 16 bytes * 2 (hex)
        assert len(result["hash"]) == 64  # SHA-256 hex length

    def test_hash_key_with_salt(self) -> None:
        """Test key hashing with provided salt."""
        generator = APIKeyGenerator()
        key_value = "test_key_123"
        salt = b"test_salt_12345"
        
        result = generator.hash_key(key_value, salt)
        
        assert result["salt"] == salt.hex()
        assert result["algorithm"] == "sha256"

    def test_verify_key_valid(self) -> None:
        """Test key verification with valid key."""
        generator = APIKeyGenerator()
        key_value = "test_key_123"
        
        # Hash the key
        hash_result = generator.hash_key(key_value)
        
        # Verify the key
        is_valid = generator.verify_key(
            key_value, 
            hash_result["hash"], 
            hash_result["salt"]
        )
        
        assert is_valid is True

    def test_verify_key_invalid(self) -> None:
        """Test key verification with invalid key."""
        generator = APIKeyGenerator()
        key_value = "test_key_123"
        wrong_key = "wrong_key_456"
        
        # Hash the key
        hash_result = generator.hash_key(key_value)
        
        # Verify with wrong key
        is_valid = generator.verify_key(
            wrong_key, 
            hash_result["hash"], 
            hash_result["salt"]
        )
        
        assert is_valid is False

    def test_verify_key_invalid_salt(self) -> None:
        """Test key verification with invalid salt."""
        generator = APIKeyGenerator()
        key_value = "test_key_123"
        
        # Hash the key
        hash_result = generator.hash_key(key_value)
        
        # Verify with invalid salt
        is_valid = generator.verify_key(
            key_value, 
            hash_result["hash"], 
            "invalid_salt"
        )
        
        assert is_valid is False

    def test_validate_permissions_valid(self) -> None:
        """Test permission validation with valid permissions."""
        generator = APIKeyGenerator()
        
        valid_permissions = {
            "read_tools": True,
            "write_back": False,
            "admin_access": True,
            "rate_limit": 60
        }
        
        assert generator.validate_permissions(valid_permissions) is True

    def test_validate_permissions_invalid_type(self) -> None:
        """Test permission validation with invalid type."""
        generator = APIKeyGenerator()
        
        assert generator.validate_permissions("invalid") is False
        assert generator.validate_permissions(123) is False
        assert generator.validate_permissions(None) is False

    def test_validate_permissions_invalid_key(self) -> None:
        """Test permission validation with invalid key."""
        generator = APIKeyGenerator()
        
        invalid_permissions = {
            "read_tools": True,
            "invalid_key": False
        }
        
        assert generator.validate_permissions(invalid_permissions) is False

    def test_validate_permissions_invalid_rate_limit(self) -> None:
        """Test permission validation with invalid rate limit."""
        generator = APIKeyGenerator()
        
        invalid_permissions = {
            "read_tools": True,
            "rate_limit": "invalid"
        }
        
        assert generator.validate_permissions(invalid_permissions) is False
        
        invalid_permissions = {
            "read_tools": True,
            "rate_limit": 0
        }
        
        assert generator.validate_permissions(invalid_permissions) is False

    def test_validate_permissions_invalid_boolean(self) -> None:
        """Test permission validation with invalid boolean values."""
        generator = APIKeyGenerator()
        
        invalid_permissions = {
            "read_tools": "invalid",
            "write_back": 123
        }
        
        assert generator.validate_permissions(invalid_permissions) is False

    def test_sanitize_metadata(self) -> None:
        """Test metadata sanitization."""
        generator = APIKeyGenerator()
        test_object = object()  # Create a single object instance
        
        raw_metadata = {
            "generated_by": "test",
            "version": "1.0",
            "invalid_key": "should_be_removed",
            "description": "Test key",
            "tags": ["test", "api"],
            "key_type": test_object  # Should be converted to string
        }
        
        sanitized = generator.sanitize_metadata(raw_metadata)
        
        assert "generated_by" in sanitized
        assert "version" in sanitized
        assert "description" in sanitized
        assert "tags" in sanitized
        assert "invalid_key" not in sanitized
        # The key_type should be converted to string and included
        assert "key_type" in sanitized
        assert sanitized["key_type"] == str(test_object)

    def test_sanitize_metadata_invalid_type(self) -> None:
        """Test metadata sanitization with invalid type."""
        generator = APIKeyGenerator()
        
        assert generator.sanitize_metadata("invalid") == {}
        assert generator.sanitize_metadata(123) == {}
        assert generator.sanitize_metadata(None) == {}

    def test_create_key_id(self) -> None:
        """Test key ID creation."""
        generator = APIKeyGenerator()
        
        key_id = generator.create_key_id()
        
        assert isinstance(key_id, str)
        assert len(key_id) > 0

    def test_get_key_statistics(self) -> None:
        """Test key statistics retrieval."""
        generator = APIKeyGenerator()
        
        stats = generator.get_key_statistics()
        
        assert isinstance(stats, dict)
        assert "default_length" in stats
        assert "default_charset_length" in stats
        assert "salt_length" in stats
        assert "generator_version" in stats
        
        assert stats["default_length"] == 32
        assert stats["default_charset_length"] == 62
        assert stats["salt_length"] == 16
        assert stats["generator_version"] == "1.0"

    def test_key_uniqueness(self) -> None:
        """Test that generated keys are unique."""
        generator = APIKeyGenerator()
        keys = set()
        
        # Generate 100 keys and check for uniqueness
        for _ in range(100):
            key = generator.generate_key()
            assert key not in keys, "Generated duplicate key"
            keys.add(key)

    def test_key_cryptographic_strength(self) -> None:
        """Test that generated keys have good cryptographic properties."""
        generator = APIKeyGenerator()
        key = generator.generate_key(length=32)
        
        # Check that key contains various character types
        key_part = key[len("dshield_"):]
        has_upper = any(c.isupper() for c in key_part)
        has_lower = any(c.islower() for c in key_part)
        has_digit = any(c.isdigit() for c in key_part)
        
        # With 32 characters from a 62-character set, we should have good distribution
        assert has_upper or has_lower or has_digit, "Key lacks character diversity"

    def test_metadata_consistency(self) -> None:
        """Test that metadata is consistent across key generation."""
        generator = APIKeyGenerator()
        
        result1 = generator.generate_key_with_metadata("Test1", {"read_tools": True})
        result2 = generator.generate_key_with_metadata("Test2", {"read_tools": True})
        
        # Check that metadata structure is consistent
        assert set(result1.keys()) == set(result2.keys())
        
        # Check that metadata values are appropriate
        for key in ["generated_by", "version", "key_type"]:
            assert result1["metadata"][key] == result2["metadata"][key]
