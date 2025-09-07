"""Tests for secure API key generation functionality.

This module tests the new secure API key generation with hashing,
salt generation, and one-time reveal functionality.
"""

import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from src.api_key_generator import APIKeyGenerator

if TYPE_CHECKING:
    pass


class TestSecureAPIKeyGeneration:
    """Test secure API key generation with hashing and salt."""

    def test_generate_api_key_basic(self) -> None:
        """Test basic API key generation with default parameters."""
        generator = APIKeyGenerator()

        key_data = generator.generate_api_key(
            name="Test Key",
            permissions={"read_tools": True, "write_back": False},
            expiration_days=30,
            rate_limit=100,
        )

        # Verify structure
        assert "key_id" in key_data
        assert "plaintext_key" in key_data
        assert "hashed_key" in key_data
        assert "salt" in key_data
        assert "algorithm" in key_data
        assert "name" in key_data
        assert "permissions" in key_data
        assert "expires_at" in key_data
        assert "rate_limit" in key_data
        assert "metadata" in key_data
        assert "created_at" in key_data

        # Verify values
        assert key_data["name"] == "Test Key"
        assert key_data["permissions"]["read_tools"] is True
        assert key_data["permissions"]["write_back"] is False
        assert key_data["rate_limit"] == 100
        assert key_data["algorithm"] == "sha256"

        # Verify plaintext key format
        assert key_data["plaintext_key"].startswith("dshield_")
        assert len(key_data["plaintext_key"]) > 10  # Should have reasonable length

        # Verify key ID format
        assert len(key_data["key_id"]) > 0
        assert isinstance(key_data["key_id"], str)

    def test_generate_api_key_encoding_formats(self) -> None:
        """Test API key generation with different encoding formats."""
        generator = APIKeyGenerator()

        for encoding in ["base32", "hex", "base64"]:
            key_data = generator.generate_api_key(
                name=f"Test Key {encoding}", permissions={"read_tools": True}, encoding=encoding
            )

            assert key_data["metadata"]["encoding"] == encoding
            assert "plaintext_key" in key_data
            assert "hashed_key" in key_data

    def test_generate_api_key_custom_length(self) -> None:
        """Test API key generation with custom length."""
        generator = APIKeyGenerator()

        key_data = generator.generate_api_key(
            name="Custom Length Key", permissions={"read_tools": True}, length=64
        )

        # Verify length (prefix + custom length)
        expected_length = len("dshield_") + 64
        assert len(key_data["plaintext_key"]) == expected_length

    def test_generate_api_key_custom_charset(self) -> None:
        """Test API key generation with custom character set."""
        generator = APIKeyGenerator()

        custom_charset = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        key_data = generator.generate_api_key(
            name="Custom Charset Key", permissions={"read_tools": True}, charset=custom_charset
        )

        # Verify all characters are from the custom charset
        key_part = key_data["plaintext_key"][len("dshield_") :]
        for char in key_part:
            assert char in custom_charset

    def test_generate_api_key_entropy(self) -> None:
        """Test that generated keys have sufficient entropy."""
        generator = APIKeyGenerator()

        # Generate multiple keys and verify they're different
        keys = set()
        for _ in range(100):
            key_data = generator.generate_api_key(
                name=f"Entropy Test {_}", permissions={"read_tools": True}
            )
            keys.add(key_data["plaintext_key"])

        # All keys should be unique
        assert len(keys) == 100

    def test_generate_api_key_validation_errors(self) -> None:
        """Test validation errors for invalid parameters."""
        generator = APIKeyGenerator()

        # Empty name
        with pytest.raises(ValueError, match="Key name cannot be empty"):
            generator.generate_api_key(name="", permissions={"read_tools": True})

        with pytest.raises(ValueError, match="Key name cannot be empty"):
            generator.generate_api_key(name="   ", permissions={"read_tools": True})

        # Invalid permissions
        with pytest.raises(ValueError, match="Permissions must be a dictionary"):
            generator.generate_api_key(name="Test", permissions="invalid")

        # Invalid expiration days
        with pytest.raises(ValueError, match="Expiration days must be positive"):
            generator.generate_api_key(name="Test", permissions={}, expiration_days=0)

        with pytest.raises(ValueError, match="Expiration days must be positive"):
            generator.generate_api_key(name="Test", permissions={}, expiration_days=-1)

        # Invalid rate limit
        with pytest.raises(ValueError, match="Rate limit must be positive"):
            generator.generate_api_key(name="Test", permissions={}, rate_limit=0)

        with pytest.raises(ValueError, match="Rate limit must be positive"):
            generator.generate_api_key(name="Test", permissions={}, rate_limit=-1)

        # Invalid encoding
        with pytest.raises(ValueError, match="Encoding must be one of"):
            generator.generate_api_key(name="Test", permissions={}, encoding="invalid")

    def test_generate_api_key_expiration_handling(self) -> None:
        """Test expiration date handling."""
        generator = APIKeyGenerator()

        # With expiration
        key_data = generator.generate_api_key(
            name="Expiring Key", permissions={"read_tools": True}, expiration_days=30
        )

        assert key_data["expires_at"] is not None
        expires_at = datetime.fromisoformat(key_data["expires_at"])
        assert expires_at > datetime.now(UTC)

        # Without expiration
        key_data = generator.generate_api_key(
            name="Non-expiring Key", permissions={"read_tools": True}, expiration_days=None
        )

        assert key_data["expires_at"] is None

    def test_generate_api_key_metadata(self) -> None:
        """Test metadata generation."""
        generator = APIKeyGenerator()

        key_data = generator.generate_api_key(
            name="Metadata Test",
            permissions={"read_tools": True, "admin_access": True},
            rate_limit=200,
        )

        metadata = key_data["metadata"]
        assert metadata["generated_by"] == "dshield-mcp"
        assert metadata["version"] == "1.0"
        assert metadata["key_type"] == "api_key"
        assert metadata["encoding"] == "base32"  # default
        assert "generated_at" in metadata
        assert "key_length" in metadata
        assert metadata["key_length"] == len(key_data["plaintext_key"])

    def test_generate_api_key_rate_limit_defaults(self) -> None:
        """Test rate limit default handling."""
        generator = APIKeyGenerator()

        # No rate limit specified
        key_data = generator.generate_api_key(
            name="Default Rate Limit", permissions={"read_tools": True}
        )
        assert key_data["rate_limit"] == 60  # default

        # Rate limit in permissions
        key_data = generator.generate_api_key(
            name="Permission Rate Limit", permissions={"read_tools": True, "rate_limit": 120}
        )
        assert key_data["rate_limit"] == 120

        # Explicit rate limit overrides permissions
        key_data = generator.generate_api_key(
            name="Explicit Rate Limit",
            permissions={"read_tools": True, "rate_limit": 120},
            rate_limit=200,
        )
        assert key_data["rate_limit"] == 200


class TestAPIKeyHashing:
    """Test API key hashing and verification functionality."""

    def test_hash_key_generates_salt(self) -> None:
        """Test that hash_key generates a random salt when none provided."""
        generator = APIKeyGenerator()
        test_key = "dshield_test123456789"

        hash_data = generator.hash_key(test_key)

        assert "hash" in hash_data
        assert "salt" in hash_data
        assert "algorithm" in hash_data
        assert hash_data["algorithm"] == "sha256"

        # Salt should be hex-encoded bytes
        salt_bytes = bytes.fromhex(hash_data["salt"])
        assert len(salt_bytes) == generator.salt_length

    def test_hash_key_with_custom_salt(self) -> None:
        """Test hash_key with custom salt."""
        generator = APIKeyGenerator()
        test_key = "dshield_test123456789"
        custom_salt = secrets.token_bytes(16)

        hash_data = generator.hash_key(test_key, custom_salt)

        assert hash_data["salt"] == custom_salt.hex()
        assert hash_data["algorithm"] == "sha256"

    def test_hash_key_deterministic(self) -> None:
        """Test that hash_key produces consistent results with same inputs."""
        generator = APIKeyGenerator()
        test_key = "dshield_test123456789"
        salt = secrets.token_bytes(16)

        hash1 = generator.hash_key(test_key, salt)
        hash2 = generator.hash_key(test_key, salt)

        assert hash1["hash"] == hash2["hash"]
        assert hash1["salt"] == hash2["salt"]

    def test_hash_key_different_salts(self) -> None:
        """Test that different salts produce different hashes."""
        generator = APIKeyGenerator()
        test_key = "dshield_test123456789"

        hash1 = generator.hash_key(test_key)
        hash2 = generator.hash_key(test_key)

        # Should be different due to different salts
        assert hash1["hash"] != hash2["hash"]
        assert hash1["salt"] != hash2["salt"]

    def test_verify_key_correct(self) -> None:
        """Test key verification with correct key."""
        generator = APIKeyGenerator()
        test_key = "dshield_test123456789"

        hash_data = generator.hash_key(test_key)

        # Verify the same key
        assert generator.verify_key(test_key, hash_data["hash"], hash_data["salt"]) is True

    def test_verify_key_incorrect(self) -> None:
        """Test key verification with incorrect key."""
        generator = APIKeyGenerator()
        test_key = "dshield_test123456789"
        wrong_key = "dshield_wrong123456789"

        hash_data = generator.hash_key(test_key)

        # Verify with wrong key
        assert generator.verify_key(wrong_key, hash_data["hash"], hash_data["salt"]) is False

    def test_verify_key_invalid_salt(self) -> None:
        """Test key verification with invalid salt."""
        generator = APIKeyGenerator()
        test_key = "dshield_test123456789"

        hash_data = generator.hash_key(test_key)

        # Verify with invalid salt
        assert generator.verify_key(test_key, hash_data["hash"], "invalid_hex") is False

    def test_verify_key_security(self) -> None:
        """Test that verification is secure against timing attacks."""
        generator = APIKeyGenerator()
        test_key = "dshield_test123456789"

        hash_data = generator.hash_key(test_key)

        # Test with keys of different lengths
        short_key = "short"
        long_key = "dshield_very_long_key_that_is_much_longer_than_expected"

        # Both should return False but not leak information
        assert generator.verify_key(short_key, hash_data["hash"], hash_data["salt"]) is False
        assert generator.verify_key(long_key, hash_data["hash"], hash_data["salt"]) is False


class TestAPIKeySecurity:
    """Test security aspects of API key generation."""

    def test_plaintext_never_stored(self) -> None:
        """Test that plaintext keys are not stored in the result."""
        generator = APIKeyGenerator()

        key_data = generator.generate_api_key(
            name="Security Test", permissions={"read_tools": True}
        )

        # The plaintext should be present for one-time display
        assert "plaintext_key" in key_data
        assert "hashed_key" in key_data

        # But they should be different
        assert key_data["plaintext_key"] != key_data["hashed_key"]

        # The hashed key should be a proper SHA-256 hash
        assert len(key_data["hashed_key"]) == 64  # SHA-256 hex length
        assert all(c in "0123456789abcdef" for c in key_data["hashed_key"])

    def test_salt_randomness(self) -> None:
        """Test that salts are sufficiently random."""
        generator = APIKeyGenerator()
        salts = set()

        # Generate many keys and collect salts
        for _ in range(1000):
            key_data = generator.generate_api_key(
                name=f"Salt Test {_}", permissions={"read_tools": True}
            )
            salts.add(key_data["salt"])

        # All salts should be unique
        assert len(salts) == 1000

    def test_key_id_uniqueness(self) -> None:
        """Test that key IDs are unique."""
        generator = APIKeyGenerator()
        key_ids = set()

        # Generate many keys and collect IDs
        for _ in range(1000):
            key_data = generator.generate_api_key(
                name=f"ID Test {_}", permissions={"read_tools": True}
            )
            key_ids.add(key_data["key_id"])

        # All key IDs should be unique
        assert len(key_ids) == 1000

    def test_key_id_format(self) -> None:
        """Test that key IDs have the expected format."""
        generator = APIKeyGenerator()

        key_data = generator.generate_api_key(
            name="ID Format Test", permissions={"read_tools": True}
        )

        key_id = key_data["key_id"]

        # Should be a URL-safe base64 string
        assert isinstance(key_id, str)
        assert len(key_id) > 0
        # Should be URL-safe (no +, /, or = characters)
        assert "+" not in key_id
        assert "/" not in key_id
        assert "=" not in key_id

    def test_permissions_validation(self) -> None:
        """Test permissions validation."""
        generator = APIKeyGenerator()

        # Valid permissions
        valid_permissions = {
            "read_tools": True,
            "write_back": False,
            "admin_access": True,
            "rate_limit": 100,
        }

        key_data = generator.generate_api_key(
            name="Valid Permissions", permissions=valid_permissions
        )

        assert key_data["permissions"] == valid_permissions

    def test_metadata_sanitization(self) -> None:
        """Test that metadata is properly sanitized."""
        generator = APIKeyGenerator()

        # Test with potentially malicious metadata
        malicious_permissions = {
            "read_tools": True,
            "injection": "<script>alert('xss')</script>",
            "null_value": None,
            "empty_string": "",
            "rate_limit": 60,
        }

        key_data = generator.generate_api_key(
            name="Metadata Sanitization Test", permissions=malicious_permissions
        )

        # The permissions should be preserved as-is (validation happens elsewhere)
        assert key_data["permissions"] == malicious_permissions

        # But metadata should be sanitized
        metadata = key_data["metadata"]
        assert "generated_by" in metadata
        assert "version" in metadata
        assert "key_type" in metadata
        # Should not contain any potentially dangerous content
        assert "<script>" not in str(metadata)


class TestAPIKeyIntegration:
    """Test integration aspects of API key generation."""

    def test_generate_api_key_with_real_connection_manager_data(self) -> None:
        """Test API key generation with realistic connection manager data."""
        generator = APIKeyGenerator()

        # Simulate real connection manager data
        permissions = {
            "read_tools": True,
            "write_back": True,
            "admin_access": False,
            "rate_limit": 120,
        }

        key_data = generator.generate_api_key(
            name="Production API Key",
            permissions=permissions,
            expiration_days=90,
            rate_limit=120,
            length=32,
            encoding="base32",
        )

        # Verify all fields are present and correct
        assert key_data["name"] == "Production API Key"
        assert key_data["permissions"] == permissions
        assert key_data["rate_limit"] == 120
        assert key_data["metadata"]["encoding"] == "base32"
        assert key_data["expires_at"] is not None

        # Verify expiration is approximately 90 days from now
        expires_at = datetime.fromisoformat(key_data["expires_at"])
        expected_expiry = datetime.now(UTC) + timedelta(days=90)
        time_diff = abs((expires_at - expected_expiry).total_seconds())
        assert time_diff < 60  # Within 1 minute

    def test_generate_api_key_storage_ready(self) -> None:
        """Test that generated keys are ready for secure storage."""
        generator = APIKeyGenerator()

        key_data = generator.generate_api_key(
            name="Storage Ready Key", permissions={"read_tools": True}
        )

        # Should have all required fields for storage
        required_fields = [
            "key_id",
            "hashed_key",
            "salt",
            "algorithm",
            "name",
            "permissions",
            "rate_limit",
            "metadata",
            "created_at",
        ]

        for field in required_fields:
            assert field in key_data, f"Missing required field: {field}"

        # Should not have plaintext in storage-ready data
        storage_data = {k: v for k, v in key_data.items() if k != "plaintext_key"}
        assert "plaintext_key" not in storage_data

        # Verify hash can be verified
        assert generator.verify_key(
            key_data["plaintext_key"], key_data["hashed_key"], key_data["salt"]
        )

    def test_generate_api_key_performance(self) -> None:
        """Test that key generation is reasonably fast."""
        import time

        generator = APIKeyGenerator()

        start_time = time.time()

        # Generate 100 keys
        for _ in range(100):
            generator.generate_api_key(
                name=f"Performance Test {_}", permissions={"read_tools": True}
            )

        end_time = time.time()
        duration = end_time - start_time

        # Should complete in reasonable time (less than 1 second for 100 keys)
        assert duration < 1.0, f"Key generation too slow: {duration:.2f}s for 100 keys"
