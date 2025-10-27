# onepassword_cli_manager

1Password CLI secrets manager implementation.

This module implements the BaseSecretsManager interface using the 1Password CLI (op)
for storing and retrieving API keys and other secrets.

The implementation provides:
- Secure subprocess execution with timeouts and proper argument quoting
- Robust JSON parsing with schema validation
- Comprehensive error mapping to SecretsManagerError subclasses
- Session/token renewal policy and environment discovery
- Metrics and logging for monitoring and debugging
- Retry logic with exponential backoff for transient errors

## OnePasswordCLIManager

1Password secrets manager using op CLI exclusively.

    This implementation uses the 1Password CLI tool to store and retrieve
    API keys and other secrets from a 1Password vault.

    Features:
    - Secure subprocess execution with proper argument quoting
    - Robust error handling with specific exception mapping
    - Session management and token renewal
    - Comprehensive logging and metrics
    - Retry logic for transient errors
    - Environment discovery for OP_SESSION_* variables

#### __init__

```python
def __init__(self, vault, timeout_seconds, max_retries, retry_delay_seconds, enable_metrics)
```

Initialize the 1Password CLI manager.

        Args:
            vault: The name of the 1Password vault to use
            timeout_seconds: Timeout for op CLI commands in seconds (default: 120s for auth)
            max_retries: Maximum number of retries for transient errors (default: 2)
            retry_delay_seconds: Base delay between retries in seconds (default: 10s)
            enable_metrics: Whether to enable metrics collection

        Raises:
            BackendUnavailableError: If op CLI is not installed or not authenticated
            SecretsManagerError: For other initialization errors

#### _discover_session

```python
def _discover_session(self)
```

Discover existing 1Password session from environment variables.

        Looks for OP_SESSION_* environment variables and extracts session tokens.

#### _is_session_valid

```python
def _is_session_valid(self)
```

Check if the current session is still valid.

        Returns:
            True if session is valid, False otherwise

#### _verify_op_cli

```python
def _verify_op_cli(self)
```

Verify op CLI is installed and authenticated.

        Raises:
            BackendUnavailableError: If op CLI is not available or not authenticated

#### _run_op_command_sync

```python
def _run_op_command_sync(self, args, timeout)
```

Run op CLI command synchronously and return JSON output.

        Args:
            args: List of arguments to pass to op CLI
            timeout: Override default timeout in seconds

        Returns:
            Parsed JSON output from the command

        Raises:
            SecretsManagerError: For various error conditions

#### _redact_sensitive_args

```python
def _redact_sensitive_args(self, cmd)
```

Redact sensitive information from command arguments for logging.

        Args:
            cmd: Command arguments to redact

        Returns:
            Command with sensitive information redacted

#### _map_op_error

```python
def _map_op_error(self, return_code, error_msg)
```

Map op CLI error codes and messages to appropriate SecretsManagerError subclasses.

        Args:
            return_code: The exit code from the op command
            error_msg: The error message from stderr

        Returns:
            Appropriate SecretsManagerError subclass or None for unmapped errors

#### _validate_op_output

```python
def _validate_op_output(self, output, command_args)
```

Validate op CLI output structure and content.

        Args:
            output: The parsed JSON output from op CLI
            command_args: The command arguments that were executed

        Raises:
            SecretsManagerError: If output validation fails

#### _update_metrics

```python
def _update_metrics(self, latency_ms, success)
```

Update internal metrics for monitoring.

        Args:
            latency_ms: Operation latency in milliseconds
            success: Whether the operation was successful

#### get_metrics

```python
def get_metrics(self)
```

Get current metrics for monitoring.

        Returns:
            Dictionary containing current metrics

#### reset_metrics

```python
def reset_metrics(self)
```

Reset all metrics to zero.

#### _run_op_command_with_retry

```python
def _run_op_command_with_retry(self, args, timeout)
```

Run op CLI command with retry logic for transient errors.

        Args:
            args: List of arguments to pass to op CLI
            timeout: Override default timeout in seconds

        Returns:
            Parsed JSON output from the command

        Raises:
            SecretsManagerError: For various error conditions

#### _should_retry

```python
def _should_retry(self, exception)
```

Determine if an operation should be retried based on the exception.

        Args:
            exception: The exception that occurred

        Returns:
            True if the operation should be retried, False otherwise
