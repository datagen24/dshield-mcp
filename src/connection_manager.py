#!/usr/bin/env python3
"""Connection manager for DShield MCP Server.

This module provides connection management functionality for TCP transport,
handling connection lifecycle, authentication, and monitoring.
"""

import asyncio
import secrets
import string
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
import structlog

from .op_secrets import OnePasswordSecrets

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
            "is_valid": self.is_valid()
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
            vault_path = self.config.get("api_key_management", {}).get("vault", "op://vault/item/field")
            
            # This is a placeholder - actual implementation would query 1Password
            # for stored API keys and restore them
            self.logger.info("Loading API keys from 1Password", vault_path=vault_path)
            
        except Exception as e:
            self.logger.error("Failed to load API keys from 1Password", error=str(e))
    
    def generate_api_key(self, permissions: Optional[Dict[str, Any]] = None, 
                        key_length: int = 32) -> APIKey:
        """Generate a new API key.
        
        Args:
            permissions: Permissions for the new API key
            key_length: Length of the generated key
            
        Returns:
            New API key instance
        """
        # Generate secure random key
        alphabet = string.ascii_letters + string.digits
        key_value = ''.join(secrets.choice(alphabet) for _ in range(key_length))
        
        # Generate unique key ID
        key_id = f"key_{secrets.token_hex(8)}"
        
        # Get default permissions from config
        default_permissions = self.config.get("permissions", {})
        if permissions is None:
            permissions = default_permissions.copy()
        else:
            # Merge with defaults
            merged_permissions = default_permissions.copy()
            merged_permissions.update(permissions)
            permissions = merged_permissions
        
        # Create API key
        expires_days = self.config.get("api_key_management", {}).get("key_expiry_days", 90)
        api_key = APIKey(key_id, key_value, permissions, expires_days)
        
        # Store in memory
        self.api_keys[key_value] = api_key
        
        # Store in 1Password (async)
        asyncio.create_task(self._store_api_key_in_1password(api_key))
        
        self.logger.info("Generated new API key", 
                        key_id=key_id, permissions=permissions)
        
        return api_key
    
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
    
    def validate_api_key(self, key_value: str) -> Optional[APIKey]:
        """Validate an API key.
        
        Args:
            key_value: The API key value to validate
            
        Returns:
            APIKey instance if valid, None if invalid
        """
        api_key = self.api_keys.get(key_value)
        
        if api_key is None:
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
                        client_address=getattr(connection, 'client_address', 'unknown'))
    
    def remove_connection(self, connection: Any) -> None:
        """Remove a connection from the manager.
        
        Args:
            connection: The connection to remove
        """
        self.connections.discard(connection)
        self.logger.info("Connection removed", 
                        client_address=getattr(connection, 'client_address', 'unknown'))
    
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
                "client_address": getattr(connection, 'client_address', 'unknown'),
                "connected_at": getattr(connection, 'connected_at', None),
                "last_activity": getattr(connection, 'last_activity', None),
                "is_authenticated": getattr(connection, 'is_authenticated', False),
                "api_key_id": None
            }
            
            # Add API key information if available
            if hasattr(connection, 'api_key') and connection.api_key:
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
                "total": len(self.connections)
            },
            "api_keys": {
                "total": total_keys,
                "active": active_keys,
                "expired": expired_keys
            },
            "last_cleanup": datetime.utcnow().isoformat()
        }
