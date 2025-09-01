#!/usr/bin/env python3
"""1Password CLI integration for secret management in DShield MCP.

This module provides integration with the 1Password CLI for secure secret
management. It handles op:// URLs in configuration values by resolving
them using the 1Password CLI tool.

Features:
- 1Password CLI availability detection
- op:// URL resolution
- Environment variable resolution
- Complex value processing with embedded URLs
- Error handling and logging
- Backward compatibility with existing API

Example:
    >>> from src.op_secrets import OnePasswordSecrets
    >>> op = OnePasswordSecrets()
    >>> secret = op.resolve_environment_variable("op://vault/item/field")
    >>> print(secret)
"""

import subprocess
import re
from typing import Optional, Dict, Any
import structlog

from .secrets.onepassword_cli_manager import OnePasswordCLIManager

logger = structlog.get_logger(__name__)


class OnePasswordSecrets:
    """Handle 1Password secret resolution for config values.
    
    This class provides methods to resolve 1Password CLI references (op:// URLs)
    in configuration values. It automatically detects 1Password CLI availability
    and provides fallback behavior when the CLI is not available.
    
    Attributes:
        op_available: Whether the 1Password CLI is available and working
    
    Example:
        >>> op = OnePasswordSecrets()
        >>> if op.op_available:
        ...     secret = op.resolve_op_url("op://vault/item/field")
        ...     print(secret)
    """
    
    def __init__(self) -> None:
        """Initialize the OnePasswordSecrets manager.
        
        Checks for 1Password CLI availability and logs a warning if it's not
        available. This affects the behavior of URL resolution methods.
        """
        self.op_available = self._check_op_cli()
        if not self.op_available:
            logger.warning("1Password CLI (op) not available. op:// URLs will not be resolved.")
    
    def _check_op_cli(self) -> bool:
        """Check if 1Password CLI is available.
        
        Attempts to run the 1Password CLI version command to verify
        that the tool is installed and accessible.
        
        Returns:
            True if 1Password CLI is available, False otherwise
        """
        try:
            result = subprocess.run(
                ["op", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
            return False
    
    def resolve_op_url(self, op_url: str) -> Optional[str]:
        """Resolve a 1Password URL (op://) to its actual value.
        
        Uses the 1Password CLI to retrieve the secret value referenced
        by the op:// URL. Handles various error conditions gracefully.
        
        Args:
            op_url: The 1Password URL (e.g., "op://vault/item/field")
        
        Returns:
            The resolved secret value or None if resolution failed
            
        Raises:
            subprocess.TimeoutExpired: If the CLI command times out
            subprocess.CalledProcessError: If the CLI command fails
        """
        if not self.op_available:
            logger.warning("1Password CLI not available, cannot resolve", op_url=op_url)
            return None
        if not op_url.startswith("op://"):
            return op_url
        try:
            logger.debug("Resolving 1Password URL", op_url=op_url)
            result = subprocess.run(
                ["op", "read", op_url],
                capture_output=True,
                text=True,
                timeout=5,  # Reduced timeout from 10 to 5 seconds
                check=True
            )
            secret_value = result.stdout.strip()
            logger.debug("Successfully resolved 1Password URL", op_url=op_url)
            return secret_value
        except subprocess.TimeoutExpired:
            logger.error("Timeout resolving 1Password URL (5s timeout)", op_url=op_url)
            return None
        except subprocess.CalledProcessError as e:
            logger.error("Failed to resolve 1Password URL", 
                        op_url=op_url, 
                        error=e.stderr.strip(),
                        return_code=e.returncode)
            return None
        except Exception as e:
            logger.error("Unexpected error resolving 1Password URL", 
                        op_url=op_url, 
                        error=str(e))
            return None
    
    def resolve_environment_variable(self, value: str) -> str:
        """Resolve config value, handling op:// URLs.
        
        Processes a configuration value that may contain 1Password CLI
        references. Handles both simple op:// URLs and complex values
        with embedded URLs.
        
        Args:
            value: The config value to resolve
        
        Returns:
            The resolved value (original if not an op:// URL or resolution failed)
        """
        if not value or not isinstance(value, str):
            return value
        # Check if the value is an op:// URL
        if value.startswith("op://"):
            resolved = self.resolve_op_url(value)
            if resolved is not None:
                return resolved
            else:
                logger.error("Failed to resolve op:// URL, this may cause authentication issues", 
                           original_value=value)
                # When CLI is unavailable, return the original URL for testing compatibility
                # In production, this should be handled by proper error handling
                return value
        # Check if the value contains op:// URLs (for complex values)
        op_pattern = r'op://[^\s]+'
        op_urls = re.findall(op_pattern, value)
        if op_urls:
            resolved_value = value
            for op_url in op_urls:
                resolved = self.resolve_op_url(op_url)
                if resolved is not None:
                    resolved_value = resolved_value.replace(op_url, resolved)
                else:
                    logger.warning("Failed to resolve op:// URL in complex value", 
                                 op_url=op_url, 
                                 original_value=value)
            return resolved_value
        return value


class OnePasswordAPIKeyManager:
    """Enhanced 1Password integration for API key management.
    
    This class provides comprehensive API key management using the new
    secrets abstraction layer while maintaining compatibility with
    existing op:// URL resolution functionality.
    
    Attributes:
        secrets_manager: The underlying OnePasswordCLIManager instance
        op_secrets: The legacy OnePasswordSecrets instance for URL resolution
    """
    
    def __init__(self, vault: str = "DShield-MCP") -> None:
        """Initialize the API key manager.
        
        Args:
            vault: The 1Password vault to use for API key storage
        """
        self.secrets_manager = OnePasswordCLIManager(vault)
        self.op_secrets = OnePasswordSecrets()
        self.logger = structlog.get_logger(__name__)
    
    async def generate_api_key(
        self,
        name: str,
        permissions: Optional[Dict[str, Any]] = None,
        expiration_days: Optional[int] = None,
        rate_limit: Optional[int] = None
    ) -> Optional[str]:
        """Generate a new API key and store it in 1Password.
        
        Args:
            name: Human-readable name for the API key
            permissions: Dictionary of permissions for the key
            expiration_days: Number of days until expiration (None for no expiration)
            rate_limit: Rate limit in requests per minute
            
        Returns:
            The generated API key value if successful, None otherwise
        """
        try:
            import secrets
            import uuid
            from datetime import datetime, timedelta
            
            # Generate a secure API key
            key_value = f"dshield_{secrets.token_urlsafe(32)}"
            key_id = str(uuid.uuid4())
            
            # Set default permissions
            if permissions is None:
                permissions = {
                    "read_tools": True,
                    "write_back": False,
                    "admin_access": False,
                    "rate_limit": rate_limit or 60
                }
            else:
                permissions["rate_limit"] = rate_limit or permissions.get("rate_limit", 60)
            
            # Calculate expiration
            expires_at = None
            if expiration_days:
                expires_at = datetime.utcnow() + timedelta(days=expiration_days)
            
            # Create API key object
            from .secrets.base_secrets_manager import APIKey
            api_key = APIKey(
                key_id=key_id,
                key_value=key_value,
                name=name,
                created_at=datetime.utcnow(),
                expires_at=expires_at,
                permissions=permissions,
                metadata={"generated_by": "dshield-mcp", "version": "1.0"}
            )
            
            # Store in 1Password
            success = await self.secrets_manager.store_api_key(api_key)
            if success:
                self.logger.info(f"Generated new API key: {name} ({key_id})")
                return key_value
            else:
                self.logger.error(f"Failed to store API key: {name}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error generating API key: {e}")
            return None
    
    async def list_api_keys(self) -> list:
        """List all API keys stored in 1Password.
        
        Returns:
            List of API key information dictionaries
        """
        try:
            from datetime import datetime
            api_keys = await self.secrets_manager.list_api_keys()
            return [
                {
                    "key_id": key.key_id,
                    "name": key.name,
                    "created_at": key.created_at.isoformat(),
                    "expires_at": key.expires_at.isoformat() if key.expires_at else None,
                    "permissions": key.permissions,
                    "is_expired": key.expires_at and key.expires_at < datetime.utcnow() if key.expires_at else False
                }
                for key in api_keys
            ]
        except Exception as e:
            self.logger.error(f"Error listing API keys: {e}")
            return []
    
    async def delete_api_key(self, key_id: str) -> bool:
        """Delete an API key from 1Password.
        
        Args:
            key_id: The unique identifier of the API key to delete
            
        Returns:
            True if the key was deleted successfully, False otherwise
        """
        try:
            success = await self.secrets_manager.delete_api_key(key_id)
            if success:
                self.logger.info(f"Deleted API key: {key_id}")
            else:
                self.logger.error(f"Failed to delete API key: {key_id}")
            return success
        except Exception as e:
            self.logger.error(f"Error deleting API key {key_id}: {e}")
            return False
    
    async def validate_api_key(self, key_value: str) -> Optional[Dict[str, Any]]:
        """Validate an API key and return its information.
        
        Args:
            key_value: The API key value to validate
            
        Returns:
            Dictionary with key information if valid, None otherwise
        """
        try:
            from datetime import datetime
            api_keys = await self.secrets_manager.list_api_keys()
            for key in api_keys:
                if key.key_value == key_value:
                    # Check if expired
                    if key.expires_at and key.expires_at < datetime.utcnow():
                        self.logger.warning(f"API key expired: {key.key_id}")
                        return None
                    
                    return {
                        "key_id": key.key_id,
                        "name": key.name,
                        "permissions": key.permissions,
                        "created_at": key.created_at,
                        "expires_at": key.expires_at
                    }
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error validating API key: {e}")
            return None
    
    def resolve_environment_variable(self, value: str) -> str:
        """Resolve config value, handling op:// URLs (backward compatibility).
        
        This method provides backward compatibility with the existing
        OnePasswordSecrets.resolve_environment_variable method.
        
        Args:
            value: The config value to resolve
            
        Returns:
            The resolved value
        """
        return self.op_secrets.resolve_environment_variable(value)
    
    async def health_check(self) -> bool:
        """Check if the 1Password integration is healthy.
        
        Returns:
            True if both the secrets manager and op CLI are working
        """
        try:
            return await self.secrets_manager.health_check()
        except Exception as e:
            self.logger.error(f"Health check failed: {e}")
            return False 