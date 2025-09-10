"""1Password CLI secrets manager implementation.

This module implements the BaseSecretsManager interface using the 1Password CLI (op)
for storing and retrieving API keys and other secrets.

The implementation provides:
- Secure subprocess execution with timeouts and proper argument quoting
- Robust JSON parsing with schema validation
- Comprehensive error mapping to SecretsManagerError subclasses
- Session/token renewal policy and environment discovery
- Metrics and logging for monitoring and debugging
- Retry logic with exponential backoff for transient errors
"""

import json
import logging
import os
import subprocess
import time
from datetime import UTC, datetime
from typing import Any

from .base_secrets_manager import (
    APIKey,
    BackendUnavailableError,
    BaseSecretsManager,
    InvalidReferenceError,
    PermissionDeniedError,
    RateLimitedError,
    SecretNotFoundError,
    SecretReference,
    SecretsManagerError,
)


class OnePasswordCLIManager(BaseSecretsManager):
    """1Password secrets manager using op CLI exclusively.

    This implementation uses the 1Password CLI tool to store and retrieve
    API keys and other secrets from a 1Password vault.

    Features:
    - Secure subprocess execution with proper argument quoting
    - Robust error handling with specific exception mapping
    - Session management and token renewal
    - Comprehensive logging and metrics
    - Retry logic for transient errors
    - Environment discovery for OP_SESSION_* variables
    """

    def __init__(
        self,
        vault: str,
        timeout_seconds: int = 120,  # Increased from 30 to 120 seconds for authentication
        max_retries: int = 2,  # Reduced from 3 to 2 to prevent spam
        retry_delay_seconds: float = 10.0,  # Increased from 1.0 to 10.0 seconds
        enable_metrics: bool = True,
    ) -> None:
        """Initialize the 1Password CLI manager.

        Args:
            vault: The name of the 1Password vault to use
            timeout_seconds: Timeout for op CLI commands in seconds (default: 120s for auth)
            max_retries: Maximum number of retries for transient errors (default: 2)
            retry_delay_seconds: Base delay between retries in seconds (default: 10s)
            enable_metrics: Whether to enable metrics collection

        Raises:
            BackendUnavailableError: If op CLI is not installed or not authenticated
            SecretsManagerError: For other initialization errors

        """
        super().__init__()
        self.vault = vault
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.retry_delay_seconds = retry_delay_seconds
        self.enable_metrics = enable_metrics

        self.logger = logging.getLogger(__name__)
        self._metrics = {
            "successful_operations": 0,
            "failed_operations": 0,
            "total_latency_ms": 0.0,
            "retry_attempts": 0,
        }

        self._session_token: str | None = None
        self._session_expires_at: datetime | None = None

        self._discover_session()
        self._verify_op_cli()

    def _discover_session(self) -> None:
        """Discover existing 1Password session from environment variables.

        Looks for OP_SESSION_* environment variables and extracts session tokens.
        """
        session_vars = {k: v for k, v in os.environ.items() if k.startswith("OP_SESSION_")}

        if session_vars:
            # Use the first available session
            session_var, session_token = next(iter(session_vars.items()))
            self._session_token = session_token
            self.logger.debug(f"Discovered session from {session_var}")

            # Try to get session expiry info
            try:
                result = self._run_op_command_sync(["whoami"], timeout=5)
                if result and "expires_at" in result:
                    self._session_expires_at = datetime.fromisoformat(
                        result["expires_at"].replace("Z", "+00:00")
                    )
            except Exception:
                # If we can't get expiry info, assume session is valid for now
                self._session_expires_at = datetime.now(UTC).replace(hour=23, minute=59, second=59)
        else:
            self.logger.debug("No OP_SESSION_* environment variables found")

    def _is_session_valid(self) -> bool:
        """Check if the current session is still valid.

        Returns:
            True if session is valid, False otherwise
        """
        if not self._session_token:
            return False

        if self._session_expires_at and datetime.now(UTC) >= self._session_expires_at:
            return False

        return True

    def _verify_op_cli(self) -> None:
        """Verify op CLI is installed and authenticated.

        Raises:
            BackendUnavailableError: If op CLI is not available or not authenticated

        """
        try:
            # Check if op CLI is installed
            result = self._run_op_command_sync(["--version"], timeout=10)
            if not result:
                raise BackendUnavailableError("op CLI not installed or not working properly")

            # Check if user is authenticated
            result = self._run_op_command_sync(["account", "list"], timeout=10)
            if not result:
                raise BackendUnavailableError(
                    "op CLI not authenticated. Run 'op signin' to authenticate"
                )

            self.logger.info("1Password CLI verified and authenticated")

        except FileNotFoundError:
            raise BackendUnavailableError(
                "op CLI not found. Install from https://1password.com/downloads/command-line"
            ) from None
        except subprocess.TimeoutExpired:
            raise BackendUnavailableError("op CLI command timed out") from None

    def _run_op_command_sync(self, args: list[str], timeout: int | None = None) -> Any:
        """Run op CLI command synchronously and return JSON output.

        Args:
            args: List of arguments to pass to op CLI
            timeout: Override default timeout in seconds

        Returns:
            Parsed JSON output from the command

        Raises:
            SecretsManagerError: For various error conditions

        """
        timeout_seconds = timeout or self.timeout_seconds
        cmd = ["op", *args]

        # Only add --format json for commands that support it
        if args and args[0] not in ["--version", "completion"]:
            cmd.extend(["--format", "json"])

        # Add session token if available
        if self._session_token:
            cmd.extend(["--session", self._session_token])

        start_time = time.time()
        latency_ms = 0.0
        result = None

        try:
            # Log command with redacted sensitive information
            safe_cmd = self._redact_sensitive_args(cmd)
            self.logger.debug(f"Running op command: {' '.join(safe_cmd)}")

            result = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                shell=False,  # Security: prevent shell injection
            )

            latency_ms = (time.time() - start_time) * 1000

            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Unknown op CLI error"
                self.logger.error(f"op command failed (exit {result.returncode}): {error_msg}")

                # Map specific error conditions to appropriate exceptions
                mapped_error = self._map_op_error(result.returncode, error_msg)
                if mapped_error:
                    raise mapped_error
                else:
                    raise SecretsManagerError(f"op command failed: {error_msg}")

            if not result.stdout.strip():
                return {}

            # For non-JSON commands, return the raw output
            if args and args[0] in ["--version", "completion"]:
                return result.stdout.strip()

            # Parse and validate JSON output
            try:
                json_output = json.loads(result.stdout)
                self._validate_op_output(json_output, args)
                return json_output
            except json.JSONDecodeError as e:
                self.logger.error(f"Failed to parse op CLI JSON output: {e}")
                self.logger.debug(f"Raw output: {result.stdout}")
                raise SecretsManagerError(f"Failed to parse op CLI JSON output: {e}") from e

        except subprocess.TimeoutExpired:
            self.logger.error(f"op CLI command timed out after {timeout_seconds}s")
            raise BackendUnavailableError("op CLI command timed out") from None
        except FileNotFoundError:
            self.logger.error("op CLI not found in PATH")
            raise BackendUnavailableError("op CLI not found") from None
        finally:
            # Update metrics
            if self.enable_metrics:
                success = result is not None and result.returncode == 0
                self._update_metrics(latency_ms, success)

    def _redact_sensitive_args(self, cmd: list[str]) -> list[str]:
        """Redact sensitive information from command arguments for logging.

        Args:
            cmd: Command arguments to redact

        Returns:
            Command with sensitive information redacted
        """
        redacted = []
        skip_next = False

        for i, arg in enumerate(cmd):
            if skip_next:
                redacted.append("[REDACTED]")
                skip_next = False
            elif arg in ["--session", "-s"] and i + 1 < len(cmd):
                redacted.append(arg)
                skip_next = True
            elif arg.startswith("--session=") or arg.startswith("-s="):
                redacted.append(arg.split("=")[0] + "=[REDACTED]")
            else:
                redacted.append(arg)

        return redacted

    def _map_op_error(self, return_code: int, error_msg: str) -> SecretsManagerError | None:
        """Map op CLI error codes and messages to appropriate SecretsManagerError subclasses.

        Args:
            return_code: The exit code from the op command
            error_msg: The error message from stderr

        Returns:
            Appropriate SecretsManagerError subclass or None for unmapped errors
        """
        error_msg_lower = error_msg.lower()

        # Common 1Password CLI error patterns
        if return_code == 1:
            if "not found" in error_msg_lower or "no such" in error_msg_lower:
                return SecretNotFoundError(f"Secret not found: {error_msg}")
            elif "permission denied" in error_msg_lower or "unauthorized" in error_msg_lower:
                return PermissionDeniedError(f"Permission denied: {error_msg}")
            elif "rate limit" in error_msg_lower or "too many requests" in error_msg_lower:
                return RateLimitedError(f"Rate limited: {error_msg}")
            elif "session expired" in error_msg_lower or "not signed in" in error_msg_lower:
                return PermissionDeniedError(f"Session expired: {error_msg}")
            elif "vault not found" in error_msg_lower:
                return SecretNotFoundError(f"Vault not found: {error_msg}")
            elif "item not found" in error_msg_lower:
                return SecretNotFoundError(f"Item not found: {error_msg}")
            elif "field not found" in error_msg_lower:
                return SecretNotFoundError(f"Field not found: {error_msg}")

        elif return_code == 2:
            # Usually indicates authentication issues
            return PermissionDeniedError(f"Authentication failed: {error_msg}")

        elif return_code == 3:
            # Usually indicates network or service issues
            return BackendUnavailableError(f"Service unavailable: {error_msg}")

        return None

    def _validate_op_output(self, output: Any, command_args: list[str]) -> None:
        """Validate op CLI output structure and content.

        Args:
            output: The parsed JSON output from op CLI
            command_args: The command arguments that were executed

        Raises:
            SecretsManagerError: If output validation fails
        """
        if not isinstance(output, dict | list):
            raise SecretsManagerError(
                f"Invalid op CLI output format: expected dict or list, got {type(output)}"
            )

        # Additional validation based on command type
        if "item" in command_args and "get" in command_args:
            if isinstance(output, dict) and "fields" not in output:
                self.logger.warning("op item get output missing 'fields' key")
        elif "item" in command_args and "list" in command_args:
            if not isinstance(output, list):
                self.logger.warning("op item list output is not a list")

    def _update_metrics(self, latency_ms: float, success: bool) -> None:
        """Update internal metrics for monitoring.

        Args:
            latency_ms: Operation latency in milliseconds
            success: Whether the operation was successful
        """
        if not self.enable_metrics:
            return

        if success:
            self._metrics["successful_operations"] += 1
        else:
            self._metrics["failed_operations"] += 1

        self._metrics["total_latency_ms"] += latency_ms

    def get_metrics(self) -> dict[str, Any]:
        """Get current metrics for monitoring.

        Returns:
            Dictionary containing current metrics
        """
        metrics = self._metrics.copy()
        if metrics["successful_operations"] + metrics["failed_operations"] > 0:
            metrics["average_latency_ms"] = metrics["total_latency_ms"] / (
                metrics["successful_operations"] + metrics["failed_operations"]
            )
        else:
            metrics["average_latency_ms"] = 0.0
        return metrics

    def reset_metrics(self) -> None:
        """Reset all metrics to zero."""
        self._metrics = {
            "successful_operations": 0,
            "failed_operations": 0,
            "total_latency_ms": 0.0,
            "retry_attempts": 0,
        }

    def _run_op_command_with_retry(self, args: list[str], timeout: int | None = None) -> Any:
        """Run op CLI command with retry logic for transient errors.

        Args:
            args: List of arguments to pass to op CLI
            timeout: Override default timeout in seconds

        Returns:
            Parsed JSON output from the command

        Raises:
            SecretsManagerError: For various error conditions
        """
        last_exception = None

        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    # Check if we should retry based on the last exception
                    if not self._should_retry(last_exception):  # type: ignore[arg-type]
                        raise last_exception

                    # Calculate exponential backoff delay
                    delay = self.retry_delay_seconds * (2 ** (attempt - 1))
                    self.logger.debug(
                        f"Retrying op command in {delay}s (attempt {attempt + 1}/"
                        f"{self.max_retries + 1})"
                    )
                    time.sleep(delay)

                    # Update retry metrics
                    if self.enable_metrics:
                        self._metrics["retry_attempts"] += 1

                return self._run_op_command_sync(args, timeout)

            except (RateLimitedError, BackendUnavailableError) as e:
                last_exception = e
                if attempt == self.max_retries:
                    self.logger.error(f"Max retries ({self.max_retries}) exceeded for op command")
                    raise
                else:
                    self.logger.warning(f"Transient error on attempt {attempt + 1}: {e}")

            except (SecretNotFoundError, PermissionDeniedError, InvalidReferenceError):
                # These errors are not transient, don't retry
                raise

            except SecretsManagerError as e:
                last_exception = e
                if attempt == self.max_retries:
                    raise
                else:
                    self.logger.warning(f"Error on attempt {attempt + 1}: {e}")

        # This should never be reached, but just in case
        raise last_exception or SecretsManagerError("Unknown error in retry logic")

    def _should_retry(self, exception: Exception) -> bool:
        """Determine if an operation should be retried based on the exception.

        Args:
            exception: The exception that occurred

        Returns:
            True if the operation should be retried, False otherwise
        """
        if isinstance(exception, RateLimitedError | BackendUnavailableError):
            return True
        return False

    async def store_api_key(self, api_key: APIKey) -> bool:
        """Store API key as a structured item in 1Password.

        Args:
            api_key: The API key object to store

        Returns:
            True if the key was stored successfully, False otherwise

        Raises:
            PermissionDeniedError: If insufficient permissions to store the key
            BackendUnavailableError: If the secrets manager backend is unavailable
            SecretsManagerError: For other storage-related errors

        """
        try:
            # Create metadata for notes field
            metadata_notes = {
                "algo_version": api_key.algo_version,
                "created_at": api_key.created_at.isoformat(),
                "key_id": api_key.key_id,
                "permissions": json.dumps(api_key.permissions),
                "rps_limit": str(api_key.rps_limit),
                "expiry": api_key.expires_at.isoformat() if api_key.expires_at else "",
                "needs_rotation": str(api_key.needs_rotation).lower(),
            }

            # Create item with custom fields using API Credential template
            item_data = {
                "title": f"dshield-mcp-key-{api_key.key_id}",
                "category": "API_CREDENTIAL",
                "vault": {"name": self.vault},
                "tags": ["dshield-mcp"],
                "fields": [
                    {
                        "id": "secret",
                        "type": "CONCEALED",
                        "value": api_key.key_value,
                        "label": "API Key",
                    },
                    {
                        "id": "name",
                        "type": "STRING",
                        "value": api_key.name,
                        "label": "Name",
                    },
                    {
                        "id": "notes",
                        "type": "STRING",
                        "value": json.dumps(metadata_notes),
                        "label": "Notes",
                    },
                ],
            }

            # Create the item using op CLI with retry logic
            args = [
                "item",
                "create",
                "--vault",
                self.vault,
                json.dumps(item_data),
            ]

            result = self._run_op_command_with_retry(args)

            if result:
                self.logger.info(f"Successfully stored API key: {api_key.key_id}")
                return True
            self.logger.error(f"Failed to store API key: {api_key.key_id}")
            return False

        except (PermissionDeniedError, BackendUnavailableError, SecretsManagerError):
            # Re-raise specific exceptions
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error storing API key {api_key.key_id}: {e}")
            raise SecretsManagerError(f"Unexpected error storing API key: {e}") from e

    async def retrieve_api_key(self, key_id: str) -> APIKey | None:
        """Retrieve an API key by ID.

        Args:
            key_id: The unique identifier of the API key

        Returns:
            The API key object if found, None otherwise

        Raises:
            SecretNotFoundError: If the key is not found
            PermissionDeniedError: If insufficient permissions to retrieve the key
            BackendUnavailableError: If the secrets manager backend is unavailable
            RateLimitedError: If the request is rate limited
            SecretsManagerError: For other retrieval-related errors

        """
        try:
            # Search for the item by title
            args = [
                "item",
                "get",
                f"dshield-mcp-key-{key_id}",
                "--vault",
                self.vault,
            ]

            result = self._run_op_command_with_retry(args)

            if not result:
                raise SecretNotFoundError(f"API key not found: {key_id}")

            # Parse the item fields
            fields = {field["id"]: field["value"] for field in result.get("fields", [])}

            # Check if this is the new format (with secret field) or old format
            if "secret" in fields:
                # New format: secret field contains plaintext, metadata in notes
                key_value = fields.get("secret", "")
                name = fields.get("name", "")
                notes_data = json.loads(fields.get("notes", "{}"))

                # Extract metadata from notes
                algo_version = notes_data.get("algo_version", "sha256-v1")
                created_at = datetime.fromisoformat(notes_data.get("created_at", ""))
                permissions = json.loads(notes_data.get("permissions", "{}"))
                rps_limit = int(notes_data.get("rps_limit", "60"))
                expiry_str = notes_data.get("expiry", "")
                expires_at = datetime.fromisoformat(expiry_str) if expiry_str else None
                needs_rotation = notes_data.get("needs_rotation", "false").lower() == "true"

                # Check if version is outdated and needs rotation
                if algo_version != "sha256-v1":
                    needs_rotation = True

                # Create metadata dict
                metadata = {
                    "algo_version": algo_version,
                    "rps_limit": rps_limit,
                    "needs_rotation": needs_rotation,
                }

                return APIKey(
                    key_id=key_id,
                    key_value=key_value,
                    name=name,
                    created_at=created_at,
                    expires_at=expires_at,
                    permissions=permissions,
                    metadata=metadata,
                    algo_version=algo_version,
                    needs_rotation=needs_rotation,
                    rps_limit=rps_limit,
                )
            else:
                # Old format: migrate to new format
                key_value = fields.get("key_value", "")
                name = fields.get("key_name", "")
                permissions = json.loads(fields.get("permissions", "{}"))
                created_at = datetime.fromisoformat(fields.get("created_at", ""))
                expires_at_str = fields.get("expires_at", "")
                expires_at = datetime.fromisoformat(expires_at_str) if expires_at_str else None
                metadata = json.loads(fields.get("metadata", "{}"))

                # Mark as needing rotation since it's missing plaintext
                needs_rotation = True

                return APIKey(
                    key_id=key_id,
                    key_value=key_value,
                    name=name,
                    created_at=created_at,
                    expires_at=expires_at,
                    permissions=permissions,
                    metadata=metadata,
                    algo_version="sha256-v1",
                    needs_rotation=needs_rotation,
                    rps_limit=60,
                )

        except (
            SecretNotFoundError,
            PermissionDeniedError,
            BackendUnavailableError,
            RateLimitedError,
            SecretsManagerError,
        ):
            # Re-raise specific exceptions
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error retrieving API key {key_id}: {e}")
            raise SecretsManagerError(f"Unexpected error retrieving API key: {e}") from e

    async def list_api_keys(self) -> list[APIKey]:
        """List all API keys stored in 1Password.

        Returns:
            List of all API key objects

        Raises:
            PermissionDeniedError: If insufficient permissions to list keys
            BackendUnavailableError: If the secrets manager backend is unavailable
            RateLimitedError: If the request is rate limited
            SecretsManagerError: For other listing-related errors

        """
        try:
            # List all items with the dshield-mcp tag (new format)
            args = [
                "item",
                "list",
                "--vault",
                self.vault,
                "--tags",
                "dshield-mcp",
            ]

            items = self._run_op_command_with_retry(args)

            api_keys = []
            for item in items:
                # Extract key_id from title (dshield-mcp-key-{key_id})
                title = item.get("title", "")
                if title.startswith("dshield-mcp-key-"):
                    key_id = title[16:]  # Remove 'dshield-mcp-key-' prefix
                    try:
                        api_key = await self.retrieve_api_key(key_id)
                        if api_key:
                            api_keys.append(api_key)
                    except SecretNotFoundError:
                        # Skip items that can't be retrieved
                        self.logger.warning(
                            f"Skipping API key {key_id} - not found during retrieval"
                        )
                        continue

            self.logger.info(f"Retrieved {len(api_keys)} API keys from 1Password")
            return api_keys

        except (
            PermissionDeniedError,
            BackendUnavailableError,
            RateLimitedError,
            SecretsManagerError,
        ):
            # Re-raise specific exceptions
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error listing API keys: {e}")
            raise SecretsManagerError(f"Unexpected error listing API keys: {e}") from e

    async def rotate_api_key(self, key_id: str, new_key_value: str) -> bool:
        """Rotate an API key by updating it with a new value.

        Args:
            key_id: The unique identifier of the API key to rotate
            new_key_value: The new API key value

        Returns:
            True if the key was rotated successfully, False otherwise

        Raises:
            SecretNotFoundError: If the key is not found
            PermissionDeniedError: If insufficient permissions to update the key
            BackendUnavailableError: If the secrets manager backend is unavailable
            SecretsManagerError: For other rotation-related errors

        """
        try:
            # Get the existing key to preserve metadata
            existing_key = await self.retrieve_api_key(key_id)
            if not existing_key:
                raise SecretNotFoundError(f"API key not found: {key_id}")

            # Create updated key with new value
            APIKey(
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
            )

            # Update the item in 1Password
            item_data = {
                "title": f"dshield-mcp-key-{key_id}",
                "category": "API_CREDENTIAL",
                "vault": {"name": self.vault},
                "tags": ["dshield-mcp"],
                "fields": [
                    {
                        "id": "secret",
                        "type": "CONCEALED",
                        "value": new_key_value,
                        "label": "API Key",
                    },
                    {
                        "id": "name",
                        "type": "STRING",
                        "value": existing_key.name,
                        "label": "Name",
                    },
                    {
                        "id": "notes",
                        "type": "STRING",
                        "value": json.dumps(
                            {
                                "algo_version": existing_key.algo_version,
                                "created_at": existing_key.created_at.isoformat(),
                                "key_id": existing_key.key_id,
                                "permissions": json.dumps(existing_key.permissions),
                                "rps_limit": str(existing_key.rps_limit),
                                "expiry": existing_key.expires_at.isoformat()
                                if existing_key.expires_at
                                else "",
                                "needs_rotation": "false",
                            }
                        ),
                        "label": "Notes",
                    },
                ],
            }

            # Update the item using op CLI
            args = [
                "item",
                "edit",
                f"dshield-mcp-key-{key_id}",
                "--vault",
                self.vault,
                json.dumps(item_data),
            ]

            result = self._run_op_command_with_retry(args)

            if result:
                self.logger.info(f"Successfully rotated API key: {key_id}")
                return True
            else:
                self.logger.error(f"Failed to rotate API key: {key_id}")
                return False

        except (
            SecretNotFoundError,
            PermissionDeniedError,
            BackendUnavailableError,
            SecretsManagerError,
        ):
            # Re-raise specific exceptions
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error rotating API key {key_id}: {e}")
            raise SecretsManagerError(f"Unexpected error rotating API key: {e}") from e

    async def delete_api_key(self, key_id: str) -> bool:
        """Delete an API key from 1Password.

        Args:
            key_id: The unique identifier of the API key to delete

        Returns:
            True if the key was deleted successfully, False otherwise

        Raises:
            SecretNotFoundError: If the key is not found
            PermissionDeniedError: If insufficient permissions to delete the key
            BackendUnavailableError: If the secrets manager backend is unavailable
            SecretsManagerError: For other deletion-related errors

        """
        try:
            # Delete the item by title
            args = [
                "item",
                "delete",
                f"dshield-mcp-key-{key_id}",
                "--vault",
                self.vault,
            ]

            result = self._run_op_command_with_retry(args)

            if result is not None:
                self.logger.info(f"Successfully deleted API key: {key_id}")
                return True
            self.logger.error(f"Failed to delete API key: {key_id}")
            return False

        except (
            SecretNotFoundError,
            PermissionDeniedError,
            BackendUnavailableError,
            SecretsManagerError,
        ):
            # Re-raise specific exceptions
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error deleting API key {key_id}: {e}")
            raise SecretsManagerError(f"Unexpected error deleting API key: {e}") from e

    async def update_api_key(self, api_key: APIKey) -> bool:
        """Update an existing API key in 1Password.

        Args:
            api_key: The updated API key object

        Returns:
            True if the key was updated successfully, False otherwise

        Raises:
            SecretNotFoundError: If the key is not found
            PermissionDeniedError: If insufficient permissions to update the key
            BackendUnavailableError: If the secrets manager backend is unavailable
            SecretsManagerError: For other update-related errors

        """
        try:
            # First delete the old item, then create a new one
            # (op CLI doesn't have a direct update command for custom fields)
            await self.delete_api_key(api_key.key_id)
            return await self.store_api_key(api_key)

        except (
            SecretNotFoundError,
            PermissionDeniedError,
            BackendUnavailableError,
            SecretsManagerError,
        ):
            # Re-raise specific exceptions
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error updating API key {api_key.key_id}: {e}")
            raise SecretsManagerError(f"Unexpected error updating API key: {e}") from e

    async def health_check(self) -> bool:
        """Check if the 1Password CLI is available and properly configured.

        Returns:
            True if the secrets manager is healthy, False otherwise

        Raises:
            BackendUnavailableError: If the backend is completely unavailable
            SecretsManagerError: For other health check errors

        """
        try:
            # Try to list items in the vault to verify access
            args = ["item", "list", "--vault", self.vault]
            self._run_op_command_with_retry(args)
            return True

        except (BackendUnavailableError, SecretsManagerError):
            # Re-raise specific exceptions
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in health check: {e}")
            raise SecretsManagerError(f"Unexpected error in health check: {e}") from e

    async def _get_secret_by_reference_impl(self, reference: SecretReference) -> str | None:
        """Backend-specific implementation for retrieving secrets by reference.

        Args:
            reference: The parsed secret reference

        Returns:
            The secret value if found, None otherwise

        Raises:
            SecretNotFoundError: If the secret is not found
            PermissionDeniedError: If insufficient permissions
            BackendUnavailableError: If the backend is unavailable
            RateLimitedError: If the request is rate limited
            SecretsManagerError: For other errors

        """
        try:
            if reference.backend != 'op':
                raise InvalidReferenceError(f"Unsupported backend: {reference.backend}")

            if not reference.item:
                raise InvalidReferenceError("No item specified in reference")

            # Build the op CLI command to get the secret
            args = ["item", "get", reference.item, "--vault", reference.vault or self.vault]

            if reference.field:
                args.extend(["--field", reference.field])
            else:
                # If no field specified, get the password field by default
                args.extend(["--field", "password"])

            result = self._run_op_command_with_retry(args)

            if result:
                return str(result.strip())
            return None

        except (
            SecretNotFoundError,
            PermissionDeniedError,
            BackendUnavailableError,
            RateLimitedError,
            InvalidReferenceError,
            SecretsManagerError,
        ):
            # Re-raise specific exceptions
            raise
        except Exception as e:
            self.logger.error(
                f"Unexpected error retrieving secret by reference {reference.uri}: {e}"
            )
            raise SecretsManagerError(
                f"Unexpected error retrieving secret by reference: {e}"
            ) from e
