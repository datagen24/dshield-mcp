# onepassword_cli_manager

1Password CLI secrets manager implementation.

This module implements the BaseSecretsManager interface using the 1Password CLI (op)
for storing and retrieving API keys and other secrets.

## OnePasswordCLIManager

1Password secrets manager using op CLI exclusively.

    This implementation uses the 1Password CLI tool to store and retrieve
    API keys and other secrets from a 1Password vault.

#### __init__

```python
def __init__(self, vault)
```

Initialize the 1Password CLI manager.

        Args:
            vault: The name of the 1Password vault to use

        Raises:
            RuntimeError: If op CLI is not installed or not authenticated

#### _verify_op_cli

```python
def _verify_op_cli(self)
```

Verify op CLI is installed and authenticated.

        Raises:
            RuntimeError: If op CLI is not available or not authenticated

#### _run_op_command

```python
def _run_op_command(self, args)
```

Run op CLI command and return JSON output.

        Args:
            args: List of arguments to pass to op CLI

        Returns:
            Parsed JSON output from the command

        Raises:
            RuntimeError: If the op command fails
