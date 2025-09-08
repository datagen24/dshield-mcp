#!/usr/bin/env python3
"""Connection manager for DShield MCP Server.

This module provides connection management functionality for TCP transport,
handling connection lifecycle, authentication, and monitoring.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

import structlog

from .op_secrets import OnePasswordAPIKeyManager, OnePasswordSecrets
from .secrets_manager.base_secrets_manager import APIKey

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """Manages TCP connections and API keys for the MCP server.

    This class handles the lifecycle of TCP connections, API key management,
    authentication, and connection monitoring.

    Attributes:
        op_secrets: OnePassword secrets manager
        api_keys: Dictionary of API keys by key value
        connections: Set of active connections
        config: Connection management configuration

    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the connection manager.

        Args:
            config: Connection management configuration

        """
        self.config = config or {}
        self.op_secrets = OnePasswordSecrets()
        self.api_key_manager = OnePasswordAPIKeyManager(
            vault=config.get("vault", "DShield-MCP") if config else "DShield-MCP",
        )
        self.api_keys: dict[str, APIKey] = {}
        self.connections: set[Any] = set()  # Will store TCPConnection objects
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")

        # Load existing API keys from 1Password
        asyncio.create_task(self._load_api_keys())

    async def _load_api_keys(self) -> None:
        """Load existing API keys from 1Password.

        This method loads API keys that were previously stored in 1Password
        and restores them to the in-memory cache.
        """
        try:
            # Load API keys from the new API key manager
            api_key_list = await self.api_key_manager.list_api_keys()

            for key_info in api_key_list:
                # Convert the API key info to our local APIKey format
                api_key = APIKey(
                    key_id=key_info["key_id"],
                    key_value=key_info["key_id"],  # We'll need to retrieve the actual value
                    permissions=key_info["permissions"],
                    expires_days=90,  # Default, will be overridden
                )

                # Update timestamps
                api_key.created_at = datetime.fromisoformat(key_info["created_at"])
                if key_info["expires_at"]:
                    api_key.expires_at = datetime.fromisoformat(key_info["expires_at"])

                # Store in memory cache
                self.api_keys[api_key.key_value] = api_key

            self.logger.info(f"Loaded {len(api_key_list)} API keys from 1Password")

        except Exception as e:
            self.logger.error("Failed to load API keys from 1Password", error=str(e))

    async def generate_api_key(
        self,
        name: str,
        permissions: dict[str, Any] | None = None,
        expiration_days: int | None = None,
        rate_limit: int | None = None,
    ) -> APIKey | None:
        """Generate a new API key and store it in 1Password.

        Args:
            name: Human-readable name for the API key
            permissions: Permissions for the new API key
            expiration_days: Number of days until expiration
            rate_limit: Rate limit in requests per minute

        Returns:
            New API key instance if successful, None otherwise

        """
        try:
            # Generate API key using the secure generator
            from .api_key_generator import APIKeyGenerator

            generator = APIKeyGenerator()
            key_data = generator.generate_key_with_metadata(
                name=name,
                permissions=permissions or {},
                expiration_days=expiration_days,
                rate_limit=rate_limit,
            )

            # Create APIKey object with plaintext key for 1Password storage
            api_key = APIKey(
                key_id=key_data["key_id"],
                key_value=key_data["key_value"],  # Store plaintext in 1Password
                name=key_data["name"],
                created_at=key_data["created_at"],
                expires_at=datetime.fromisoformat(key_data["expires_at"])
                if key_data["expires_at"]
                else None,
                permissions=key_data["permissions"],
                metadata=key_data["metadata"],
                algo_version=key_data["algo_version"],
                needs_rotation=key_data["needs_rotation"],
                rps_limit=key_data["rps_limit"],
                verifier=key_data["verifier"],  # Store verifier server-side only
            )

            # Store in 1Password using the secrets manager
            success = await self.secrets_manager.store_api_key(api_key)
            if success:
                # Store in memory cache (using plaintext key as the key)
                self.api_keys[key_data["key_value"]] = api_key

                self.logger.info(
                    "Generated new API key", key_id=key_data["key_id"], name=name, plaintext=True
                )
                return api_key
            else:
                self.logger.error("Failed to store API key in 1Password", key_id=key_data["key_id"])
                return None

        except Exception as e:
            self.logger.error("Failed to generate API key", error=str(e))
            return None

    async def rotate_api_key(self, key_id: str) -> APIKey | None:
        """Rotate an API key by generating a new value.

        Args:
            key_id: The unique identifier of the API key to rotate

        Returns:
            Updated API key instance if successful, None otherwise

        """
        try:
            # Get the existing key
            existing_key = await self.secrets_manager.retrieve_api_key(key_id)
            if not existing_key:
                self.logger.error("API key not found for rotation", key_id=key_id)
                return None

            # Generate new key value
            from .api_key_generator import APIKeyGenerator

            generator = APIKeyGenerator()
            new_key_value = generator.generate_key()

            # Generate new verifier
            verifier_data = generator.hash_key(new_key_value)
            new_verifier = verifier_data["hash"]

            # Update the key in 1Password
            success = await self.secrets_manager.rotate_api_key(key_id, new_key_value)
            if success:
                # Update the in-memory cache
                updated_key = APIKey(
                    key_id=existing_key.key_id,
                    key_value=new_key_value,
                    name=existing_key.name,
                    created_at=existing_key.created_at,
                    expires_at=existing_key.expires_at,
                    permissions=existing_key.permissions,
                    metadata=existing_key.metadata,
                    algo_version=existing_key.algo_version,
                    needs_rotation=False,  # Clear rotation flag
                    rps_limit=existing_key.rps_limit,
                    verifier=new_verifier,
                )

                # Update cache
                self.api_keys[new_key_value] = updated_key
                # Remove old key from cache if it exists
                if existing_key.key_value in self.api_keys:
                    del self.api_keys[existing_key.key_value]

                self.logger.info("Successfully rotated API key", key_id=key_id)
                return updated_key
            else:
                self.logger.error("Failed to rotate API key in 1Password", key_id=key_id)
                return None

        except Exception as e:
            self.logger.error("Failed to rotate API key", key_id=key_id, error=str(e))
            return None

    async def _store_api_key_in_1password(self, api_key: APIKey) -> None:
        """Store an API key in 1Password.

        Args:
            api_key: The API key to store

        """
        try:
            vault_path = self.config.get("api_key_management", {}).get(
                "vault", "op://vault/item/field"
            )

            # This is a placeholder - actual implementation would store the API key
            # in 1Password using the op_secrets manager
            self.logger.info(
                "Storing API key in 1Password", key_id=api_key.key_id, vault_path=vault_path
            )

        except Exception as e:
            self.logger.error(
                "Failed to store API key in 1Password", key_id=api_key.key_id, error=str(e)
            )

    async def validate_api_key(self, key_value: str) -> APIKey | None:
        """Validate an API key.

        Args:
            key_value: The API key value to validate

        Returns:
            APIKey instance if valid, None if invalid

        """
        # First check the in-memory cache
        api_key = self.api_keys.get(key_value)

        if api_key is None:
            # Try to validate using the API key manager
            key_info = await self.api_key_manager.validate_api_key(key_value)
            if key_info:
                # Create local APIKey instance
                api_key = APIKey(
                    key_id=key_info["key_id"],
                    key_value=key_value,
                    permissions=key_info["permissions"],
                    expires_days=90,  # Will be overridden
                )

                # Update timestamps
                api_key.created_at = key_info["created_at"]
                if key_info["expires_at"]:
                    api_key.expires_at = key_info["expires_at"]

                # Store in memory cache
                self.api_keys[key_value] = api_key
            else:
                self.logger.warning("API key not found", key_value=key_value[:8] + "...")
                return None

        if not api_key.is_valid():
            self.logger.warning(
                "API key is invalid",
                key_id=api_key.key_id,
                is_active=api_key.is_active,
                is_expired=api_key.is_expired(),
            )
            return None

        # Update usage statistics
        api_key.update_usage()

        return api_key

    async def delete_api_key(self, key_id: str) -> bool:
        """Delete an API key from 1Password and memory cache.

        Args:
            key_id: The unique identifier of the API key to delete

        Returns:
            True if the key was deleted successfully, False otherwise

        """
        try:
            # Delete from 1Password
            success = await self.api_key_manager.delete_api_key(key_id)

            if success:
                # Remove from memory cache
                keys_to_remove = [k for k, v in self.api_keys.items() if v.key_id == key_id]
                for key_value in keys_to_remove:
                    del self.api_keys[key_value]

                # Disconnect any active sessions using this key
                connections_to_close = []
                for connection in self.connections:
                    if hasattr(connection, "api_key") and connection.api_key.key_id == key_id:
                        connections_to_close.append(connection)

                for connection in connections_to_close:
                    self.remove_connection(connection)

                self.logger.info("Deleted API key and disconnected sessions", key_id=key_id)
                return True
            self.logger.error("Failed to delete API key from 1Password", key_id=key_id)
            return False

        except Exception as e:
            self.logger.error("Error deleting API key", key_id=key_id, error=str(e))
            return False

    def revoke_api_key(self, key_value: str) -> bool:
        """Revoke an API key.

        Args:
            key_value: The API key value to revoke

        Returns:
            True if key was revoked, False if not found

        """
        api_key = self.api_keys.get(key_value)

        if api_key is None:
            return False

        api_key.is_active = False
        self.logger.info("API key revoked", key_id=api_key.key_id)

        # Remove from 1Password (async)
        asyncio.create_task(self._remove_api_key_from_1password(api_key))

        return True

    async def _remove_api_key_from_1password(self, api_key: APIKey) -> None:
        """Remove an API key from 1Password.

        Args:
            api_key: The API key to remove

        """
        try:
            vault_path = self.config.get("api_key_management", {}).get(
                "vault", "op://vault/item/field"
            )

            # This is a placeholder - actual implementation would remove the API key
            # from 1Password using the op_secrets manager
            self.logger.info(
                "Removing API key from 1Password", key_id=api_key.key_id, vault_path=vault_path
            )

        except Exception as e:
            self.logger.error(
                "Failed to remove API key from 1Password", key_id=api_key.key_id, error=str(e)
            )

    def add_connection(self, connection: Any) -> None:
        """Add a connection to the manager.

        Args:
            connection: The connection to add

        """
        self.connections.add(connection)
        self.logger.info(
            "Connection added", client_address=getattr(connection, "client_address", "unknown")
        )

    def remove_connection(self, connection: Any) -> None:
        """Remove a connection from the manager.

        Args:
            connection: The connection to remove

        """
        self.connections.discard(connection)
        self.logger.info(
            "Connection removed", client_address=getattr(connection, "client_address", "unknown")
        )

    def get_connection_count(self) -> int:
        """Get the number of active connections.

        Returns:
            Number of active connections

        """
        return len(self.connections)

    def get_connections_info(self) -> list[dict[str, Any]]:
        """Get information about active connections.

        Returns:
            List of connection information dictionaries

        """
        connections_info = []

        for connection in self.connections:
            info = {
                "client_address": getattr(connection, "client_address", "unknown"),
                "connected_at": getattr(connection, "connected_at", None),
                "last_activity": getattr(connection, "last_activity", None),
                "is_authenticated": getattr(connection, "is_authenticated", False),
                "api_key_id": None,
            }

            # Add API key information if available
            if hasattr(connection, "api_key") and connection.api_key:
                api_key = self.api_keys.get(connection.api_key)
                if api_key:
                    info["api_key_id"] = api_key.key_id
                    info["api_key_permissions"] = api_key.permissions

            connections_info.append(info)

        return connections_info

    def get_api_keys_info(self) -> list[dict[str, Any]]:
        """Get information about all API keys.

        Returns:
            List of API key information dictionaries

        """
        return [api_key.to_dict() for api_key in self.api_keys.values()]

    def get_active_api_keys_count(self) -> int:
        """Get the number of active API keys.

        Returns:
            Number of active API keys

        """
        return sum(1 for api_key in self.api_keys.values() if api_key.is_valid())

    def cleanup_expired_keys(self) -> int:
        """Clean up expired API keys.

        Returns:
            Number of keys cleaned up

        """
        expired_keys = [
            key_value for key_value, api_key in self.api_keys.items() if api_key.is_expired()
        ]

        for key_value in expired_keys:
            del self.api_keys[key_value]

        if expired_keys:
            self.logger.info("Cleaned up expired API keys", count=len(expired_keys))

        return len(expired_keys)

    def get_statistics(self) -> dict[str, Any]:
        """Get connection manager statistics.

        Returns:
            Dictionary of statistics

        """
        total_keys = len(self.api_keys)
        active_keys = self.get_active_api_keys_count()
        expired_keys = total_keys - active_keys

        return {
            "connections": {
                "active": self.get_connection_count(),
                "total": len(self.connections),
            },
            "api_keys": {
                "total": total_keys,
                "active": active_keys,
                "expired": expired_keys,
            },
            "last_cleanup": datetime.now(UTC).isoformat(),
        }
