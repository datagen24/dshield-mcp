#!/usr/bin/env python3
"""Connection manager for DShield MCP Server.

This module provides connection management functionality for TCP transport,
handling connection lifecycle, authentication, and monitoring.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

import structlog

from .op_secrets import OnePasswordAPIKeyManager, OnePasswordSecrets

logger = structlog.get_logger(__name__)


class APIKey:
    """Represents an API key with associated permissions and metadata.
    
    Attributes:
        key_id: Unique identifier for the API key
        key_value: The actual API key value
        permissions: Dictionary of permissions for this key
        created_at: Timestamp when the key was created
        expires_at: Timestamp when the key expires
        last_used: Timestamp of last usage
        usage_count: Number of times the key has been used
        is_active: Whether the key is currently active

    """

    def __init__(self, key_id: str, key_value: str, permissions: Dict[str, Any],
                 expires_days: int = 90) -> None:
        """Initialize an API key.
        
        Args:
            key_id: Unique identifier for the API key
            key_value: The actual API key value
            permissions: Dictionary of permissions for this key
            expires_days: Number of days until the key expires

        """
        self.key_id = key_id
        self.key_value = key_value
        self.permissions = permissions
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(days=expires_days)
        self.last_used = None
        self.usage_count = 0
        self.is_active = True

    def is_expired(self) -> bool:
        """Check if the API key has expired.
        
        Returns:
            True if the key has expired, False otherwise

        """
        return datetime.utcnow() > self.expires_at

    def is_valid(self) -> bool:
        """Check if the API key is valid (active and not expired).
        
        Returns:
            True if the key is valid, False otherwise

        """
        return self.is_active and not self.is_expired()

    def update_usage(self) -> None:
        """Update the usage statistics for this key."""
        self.last_used = datetime.utcnow()
        self.usage_count += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert the API key to a dictionary.
        
        Returns:
            Dictionary representation of the API key

        """
        return {
            "key_id": self.key_id,
            "key_value": self.key_value[:8] + "..." if self.key_value else None,  # Masked for security
            "permissions": self.permissions,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "usage_count": self.usage_count,
            "is_active": self.is_active,
            "is_expired": self.is_expired(),
            "is_valid": self.is_valid(),
        }


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

    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the connection manager.
        
        Args:
            config: Connection management configuration

        """
        self.config = config or {}
        self.op_secrets = OnePasswordSecrets()
        self.api_key_manager = OnePasswordAPIKeyManager(
            vault=config.get("vault", "DShield-MCP") if config else "DShield-MCP",
        )
        self.api_keys: Dict[str, APIKey] = {}
        self.connections: Set[Any] = set()  # Will store TCPConnection objects
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

    async def generate_api_key(self, name: str, permissions: Optional[Dict[str, Any]] = None,
                              expiration_days: Optional[int] = None, rate_limit: Optional[int] = None) -> Optional[APIKey]:
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
            # Generate API key using the new manager
            key_value = await self.api_key_manager.generate_api_key(
                name=name,
                permissions=permissions,
                expiration_days=expiration_days,
                rate_limit=rate_limit,
            )

            if key_value:
                # Retrieve the full API key info
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

                    self.logger.info("Generated new API key", key_id=key_info["key_id"], name=name)
                    return api_key

            return None

        except Exception as e:
            self.logger.error("Failed to generate API key", error=str(e))
            return None

    async def _store_api_key_in_1password(self, api_key: APIKey) -> None:
        """Store an API key in 1Password.
        
        Args:
            api_key: The API key to store

        """
        try:
            vault_path = self.config.get("api_key_management", {}).get("vault", "op://vault/item/field")

            # This is a placeholder - actual implementation would store the API key
            # in 1Password using the op_secrets manager
            self.logger.info("Storing API key in 1Password",
                           key_id=api_key.key_id, vault_path=vault_path)

        except Exception as e:
            self.logger.error("Failed to store API key in 1Password",
                            key_id=api_key.key_id, error=str(e))

    async def validate_api_key(self, key_value: str) -> Optional[APIKey]:
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
            self.logger.warning("API key is invalid",
                              key_id=api_key.key_id,
                              is_active=api_key.is_active,
                              is_expired=api_key.is_expired())
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
                    await self.close_connection(connection)

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
            vault_path = self.config.get("api_key_management", {}).get("vault", "op://vault/item/field")

            # This is a placeholder - actual implementation would remove the API key
            # from 1Password using the op_secrets manager
            self.logger.info("Removing API key from 1Password",
                           key_id=api_key.key_id, vault_path=vault_path)

        except Exception as e:
            self.logger.error("Failed to remove API key from 1Password",
                            key_id=api_key.key_id, error=str(e))

    def add_connection(self, connection: Any) -> None:
        """Add a connection to the manager.
        
        Args:
            connection: The connection to add

        """
        self.connections.add(connection)
        self.logger.info("Connection added",
                        client_address=getattr(connection, "client_address", "unknown"))

    def remove_connection(self, connection: Any) -> None:
        """Remove a connection from the manager.
        
        Args:
            connection: The connection to remove

        """
        self.connections.discard(connection)
        self.logger.info("Connection removed",
                        client_address=getattr(connection, "client_address", "unknown"))

    def get_connection_count(self) -> int:
        """Get the number of active connections.
        
        Returns:
            Number of active connections

        """
        return len(self.connections)

    def get_connections_info(self) -> List[Dict[str, Any]]:
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

    def get_api_keys_info(self) -> List[Dict[str, Any]]:
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
            key_value for key_value, api_key in self.api_keys.items()
            if api_key.is_expired()
        ]

        for key_value in expired_keys:
            del self.api_keys[key_value]

        if expired_keys:
            self.logger.info("Cleaned up expired API keys", count=len(expired_keys))

        return len(expired_keys)

    def get_statistics(self) -> Dict[str, Any]:
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
            "last_cleanup": datetime.utcnow().isoformat(),
        }
