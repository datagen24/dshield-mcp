"""Base secrets manager abstraction for DShield MCP.

This module defines the abstract interface for secrets management providers,
allowing the system to work with different backends (1Password, HashiCorp Vault, etc.)
through a consistent interface.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


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

    """

    key_id: str
    key_value: str
    name: str
    created_at: datetime
    expires_at: Optional[datetime]
    permissions: Dict[str, Any]
    metadata: Dict[str, Any]


class BaseSecretsManager(ABC):
    """Abstract base class for secrets management providers.
    
    This class defines the interface that all secrets management providers
    must implement, ensuring consistent behavior across different backends.
    """

    @abstractmethod
    async def store_api_key(self, api_key: APIKey) -> bool:
        """Store an API key in the secrets manager.
        
        Args:
            api_key: The API key object to store
            
        Returns:
            True if the key was stored successfully, False otherwise
            
        Raises:
            RuntimeError: If the secrets manager is not available or configured

        """

    @abstractmethod
    async def retrieve_api_key(self, key_id: str) -> Optional[APIKey]:
        """Retrieve an API key by ID.
        
        Args:
            key_id: The unique identifier of the API key
            
        Returns:
            The API key object if found, None otherwise
            
        Raises:
            RuntimeError: If the secrets manager is not available or configured

        """

    @abstractmethod
    async def list_api_keys(self) -> List[APIKey]:
        """List all API keys stored in the secrets manager.
        
        Returns:
            List of all API key objects
            
        Raises:
            RuntimeError: If the secrets manager is not available or configured

        """

    @abstractmethod
    async def delete_api_key(self, key_id: str) -> bool:
        """Delete an API key from the secrets manager.
        
        Args:
            key_id: The unique identifier of the API key to delete
            
        Returns:
            True if the key was deleted successfully, False otherwise
            
        Raises:
            RuntimeError: If the secrets manager is not available or configured

        """

    @abstractmethod
    async def update_api_key(self, api_key: APIKey) -> bool:
        """Update an existing API key in the secrets manager.
        
        Args:
            api_key: The updated API key object
            
        Returns:
            True if the key was updated successfully, False otherwise
            
        Raises:
            RuntimeError: If the secrets manager is not available or configured

        """

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the secrets manager is available and properly configured.
        
        Returns:
            True if the secrets manager is healthy, False otherwise

        """
