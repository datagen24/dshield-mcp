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
                # For critical credentials, return None instead of the raw URL
                if "password" in value.lower() or "username" in value.lower():
                    logger.error("Critical credential resolution failed - returning None", 
                               credential_type="username" if "username" in value.lower() else "password")
                    return None
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