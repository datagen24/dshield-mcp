"""Secrets management module for DShield MCP.

This module provides an abstraction layer for managing API keys and other secrets
across different secrets management providers (1Password, HashiCorp Vault, etc.).
"""

from .base_secrets_manager import (
    APIKey,
    BackendUnavailableError,
    BaseSecretsManager,
    InvalidReferenceError,
    PermissionDeniedError,
    RateLimitedError,
    SecretMetadata,
    SecretNotFoundError,
    SecretReference,
    SecretsManagerError,
)
from .onepassword_cli_manager import OnePasswordCLIManager

__all__ = [
    "APIKey",
    "BackendUnavailableError",
    "BaseSecretsManager",
    "InvalidReferenceError",
    "OnePasswordCLIManager",
    "PermissionDeniedError",
    "RateLimitedError",
    "SecretMetadata",
    "SecretNotFoundError",
    "SecretReference",
    "SecretsManagerError",
]
