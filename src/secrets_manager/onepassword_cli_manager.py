"""1Password CLI secrets manager implementation.

This module implements the BaseSecretsManager interface using the 1Password CLI (op)
for storing and retrieving API keys and other secrets.
"""

import json
import logging
import subprocess
from datetime import datetime
from typing import Any

from .base_secrets_manager import APIKey, BaseSecretsManager


class OnePasswordCLIManager(BaseSecretsManager):
    """1Password secrets manager using op CLI exclusively.

    This implementation uses the 1Password CLI tool to store and retrieve
    API keys and other secrets from a 1Password vault.
    """

    def __init__(self, vault: str) -> None:
        """Initialize the 1Password CLI manager.

        Args:
            vault: The name of the 1Password vault to use

        Raises:
            RuntimeError: If op CLI is not installed or not authenticated

        """
        self.vault = vault
        self.logger = logging.getLogger(__name__)
        self._verify_op_cli()

    def _verify_op_cli(self) -> None:
        """Verify op CLI is installed and authenticated.

        Raises:
            RuntimeError: If op CLI is not available or not authenticated

        """
        try:
            # Check if op CLI is installed
            result = subprocess.run(
                ["op", "--version"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                raise RuntimeError("op CLI not installed or not working properly")

            # Check if user is authenticated
            result = subprocess.run(
                ["op", "account", "list"],
                check=False,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    "op CLI not authenticated. Run 'op signin' to authenticate",
                )

            self.logger.info("1Password CLI verified and authenticated")

        except FileNotFoundError:
            raise RuntimeError(
                "op CLI not found. Install from https://1password.com/downloads/command-line",
            ) from None
        except subprocess.TimeoutExpired:
            raise RuntimeError("op CLI command timed out") from None

    def _run_op_command(self, args: list[str]) -> Any:
        """Run op CLI command and return JSON output.

        Args:
            args: List of arguments to pass to op CLI

        Returns:
            Parsed JSON output from the command

        Raises:
            RuntimeError: If the op command fails

        """
        cmd = ["op"] + args + ["--format", "json"]

        try:
            result = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Unknown op CLI error"
                raise RuntimeError(f"op command failed: {error_msg}")

            if not result.stdout.strip():
                return {}

            return json.loads(result.stdout)

        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse op CLI JSON output: {e}") from e
        except subprocess.TimeoutExpired:
            raise RuntimeError("op CLI command timed out") from None

    async def store_api_key(self, api_key: APIKey) -> bool:
        """Store API key as a structured item in 1Password.

        Args:
            api_key: The API key object to store

        Returns:
            True if the key was stored successfully, False otherwise

        """
        try:
            # Create item with custom fields
            item_data = {
                "title": f"dshield-mcp-key-{api_key.key_id}",
                "category": "API_CREDENTIAL",
                "vault": {"name": self.vault},
                "tags": ["dshield-mcp-api-key"],
                "fields": [
                    {
                        "id": "key_value",
                        "type": "CONCEALED",
                        "value": api_key.key_value,
                        "label": "API Key Value",
                    },
                    {
                        "id": "key_name",
                        "type": "STRING",
                        "value": api_key.name,
                        "label": "Key Name",
                    },
                    {
                        "id": "permissions",
                        "type": "STRING",
                        "value": json.dumps(api_key.permissions),
                        "label": "Permissions",
                    },
                    {
                        "id": "created_at",
                        "type": "STRING",
                        "value": api_key.created_at.isoformat(),
                        "label": "Created At",
                    },
                    {
                        "id": "expires_at",
                        "type": "STRING",
                        "value": api_key.expires_at.isoformat() if api_key.expires_at else "",
                        "label": "Expires At",
                    },
                    {
                        "id": "metadata",
                        "type": "STRING",
                        "value": json.dumps(api_key.metadata),
                        "label": "Metadata",
                    },
                ],
            }

            # Create the item using op CLI
            args = [
                "item",
                "create",
                "--vault",
                self.vault,
                json.dumps(item_data),
            ]

            result = self._run_op_command(args)

            if result:
                self.logger.info(f"Successfully stored API key: {api_key.key_id}")
                return True
            self.logger.error(f"Failed to store API key: {api_key.key_id}")
            return False

        except Exception as e:
            self.logger.error(f"Error storing API key {api_key.key_id}: {e}")
            return False

    async def retrieve_api_key(self, key_id: str) -> APIKey | None:
        """Retrieve an API key by ID.

        Args:
            key_id: The unique identifier of the API key

        Returns:
            The API key object if found, None otherwise

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

            result = self._run_op_command(args)

            if not result:
                return None

            # Parse the item fields
            fields = {field["id"]: field["value"] for field in result.get("fields", [])}

            # Extract API key data
            key_value = fields.get("key_value", "")
            name = fields.get("key_name", "")
            permissions = json.loads(fields.get("permissions", "{}"))
            created_at = datetime.fromisoformat(fields.get("created_at", ""))
            expires_at_str = fields.get("expires_at", "")
            expires_at = datetime.fromisoformat(expires_at_str) if expires_at_str else None
            metadata = json.loads(fields.get("metadata", "{}"))

            return APIKey(
                key_id=key_id,
                key_value=key_value,
                name=name,
                created_at=created_at,
                expires_at=expires_at,
                permissions=permissions,
                metadata=metadata,
            )

        except Exception as e:
            self.logger.error(f"Error retrieving API key {key_id}: {e}")
            return None

    async def list_api_keys(self) -> list[APIKey]:
        """List all API keys stored in 1Password.

        Returns:
            List of all API key objects

        """
        try:
            # List all items with the dshield-mcp-api-key tag
            args = [
                "item",
                "list",
                "--vault",
                self.vault,
                "--tags",
                "dshield-mcp-api-key",
            ]

            items = self._run_op_command(args)

            api_keys = []
            for item in items:
                # Extract key_id from title (dshield-mcp-key-{key_id})
                title = item.get("title", "")
                if title.startswith("dshield-mcp-key-"):
                    key_id = title[16:]  # Remove 'dshield-mcp-key-' prefix
                    api_key = await self.retrieve_api_key(key_id)
                    if api_key:
                        api_keys.append(api_key)

            self.logger.info(f"Retrieved {len(api_keys)} API keys from 1Password")
            return api_keys

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
            # Delete the item by title
            args = [
                "item",
                "delete",
                f"dshield-mcp-key-{key_id}",
                "--vault",
                self.vault,
            ]

            result = self._run_op_command(args)

            if result is not None:
                self.logger.info(f"Successfully deleted API key: {key_id}")
                return True
            self.logger.error(f"Failed to delete API key: {key_id}")
            return False

        except Exception as e:
            self.logger.error(f"Error deleting API key {key_id}: {e}")
            return False

    async def update_api_key(self, api_key: APIKey) -> bool:
        """Update an existing API key in 1Password.

        Args:
            api_key: The updated API key object

        Returns:
            True if the key was updated successfully, False otherwise

        """
        try:
            # First delete the old item, then create a new one
            # (op CLI doesn't have a direct update command for custom fields)
            await self.delete_api_key(api_key.key_id)
            return await self.store_api_key(api_key)

        except Exception as e:
            self.logger.error(f"Error updating API key {api_key.key_id}: {e}")
            return False

    async def health_check(self) -> bool:
        """Check if the 1Password CLI is available and properly configured.

        Returns:
            True if the secrets manager is healthy, False otherwise

        """
        try:
            # Try to list items in the vault to verify access
            args = ["item", "list", "--vault", self.vault]
            self._run_op_command(args)
            return True

        except Exception as e:
            self.logger.error(f"1Password CLI health check failed: {e}")
            return False
