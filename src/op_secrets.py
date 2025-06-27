#!/usr/bin/env python3
"""
1Password CLI integration for secret management in DShield MCP.
Handles op:// URLs in environment variables by resolving them using the 1Password CLI.
"""

import os
import subprocess
import re
from typing import Optional, Dict, Any
import structlog
from unittest.mock import MagicMock, AsyncMock

logger = structlog.get_logger(__name__)


class OnePasswordSecrets:
    """Handle 1Password secret resolution for environment variables."""
    
    def __init__(self):
        self.op_available = self._check_op_cli()
        if not self.op_available:
            logger.warning("1Password CLI (op) not available. op:// URLs will not be resolved.")
    
    def _check_op_cli(self) -> bool:
        """Check if 1Password CLI is available."""
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
        """
        Resolve a 1Password URL (op://) to its actual value.
        
        Args:
            op_url: The 1Password URL (e.g., "op://vault/item/field")
            
        Returns:
            The resolved secret value or None if resolution failed
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
                timeout=10,
                check=True
            )
            
            secret_value = result.stdout.strip()
            logger.debug("Successfully resolved 1Password URL", op_url=op_url)
            return secret_value
            
        except subprocess.TimeoutExpired:
            logger.error("Timeout resolving 1Password URL", op_url=op_url)
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
        """
        Resolve environment variable value, handling op:// URLs.
        
        Args:
            value: The environment variable value
            
        Returns:
            The resolved value (original if not an op:// URL)
        """
        if not value or not isinstance(value, str):
            return value
        
        # Check if the value is an op:// URL
        if value.startswith("op://"):
            resolved = self.resolve_op_url(value)
            if resolved is not None:
                return resolved
            else:
                logger.warning("Failed to resolve op:// URL, using original value", 
                             original_value=value)
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
    
    def resolve_environment_variables(self, env_dict: Dict[str, str]) -> Dict[str, str]:
        """
        Resolve all op:// URLs in a dictionary of environment variables.
        
        Args:
            env_dict: Dictionary of environment variables
            
        Returns:
            Dictionary with resolved values
        """
        resolved_dict = {}
        
        for key, value in env_dict.items():
            resolved_value = self.resolve_environment_variable(value)
            resolved_dict[key] = resolved_value
            
            if value != resolved_value:
                logger.debug("Resolved environment variable", 
                           key=key, 
                           original_value=value[:10] + "..." if len(value) > 10 else value)
        
        return resolved_dict


# Global instance
op_secrets = OnePasswordSecrets()


def get_env_with_op_resolution(key: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get environment variable with 1Password URL resolution.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        
    Returns:
        Resolved environment variable value
    """
    value = os.getenv(key, default)
    if value is None:
        return None
    
    return op_secrets.resolve_environment_variable(value)


def load_env_with_op_resolution() -> Dict[str, str]:
    """
    Load all environment variables with 1Password URL resolution.
    
    Returns:
        Dictionary of resolved environment variables
    """
    env_dict = dict(os.environ)
    return op_secrets.resolve_environment_variables(env_dict) 