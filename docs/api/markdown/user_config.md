# user_config

User Configuration Management for DShield MCP.

This module provides comprehensive user configuration management for the DShield MCP
server. It extends the base configuration system with user-customizable settings,
validation, environment variable support, and multiple configuration sources.

Features:
- User-configurable settings with validation
- Environment variable overrides
- Multiple configuration file sources
- Setting categories (query, pagination, streaming, etc.)
- Configuration export and import
- 1Password CLI integration

Example:
    >>> from src.user_config import get_user_config
    >>> config = get_user_config()
    >>> page_size = config.get_setting("query", "default_page_size")
    >>> print(page_size)

## QuerySettings

User-configurable query settings.

    Attributes:
        default_page_size: Default number of results per page
        max_page_size: Maximum allowed page size
        default_timeout_seconds: Default query timeout in seconds
        max_timeout_seconds: Maximum allowed timeout in seconds
        enable_smart_optimization: Whether to enable smart query optimization
        fallback_strategy: Strategy for handling query failures
        max_query_complexity: Maximum query complexity threshold

## PaginationSettings

User-configurable pagination settings.

    Attributes:
        default_method: Default pagination method (page or cursor)
        max_pages_per_request: Maximum pages per request
        cursor_timeout_seconds: Cursor timeout in seconds
        enable_metadata: Whether to include pagination metadata
        include_performance_metrics: Whether to include performance metrics

## StreamingSettings

User-configurable streaming settings.

    Attributes:
        default_chunk_size: Default chunk size for streaming
        max_chunk_size: Maximum allowed chunk size
        session_context_fields: Fields to use for session context
        enable_session_summaries: Whether to enable session summaries
        session_timeout_minutes: Session timeout in minutes

## PerformanceSettings

User-configurable performance settings.

    Attributes:
        enable_caching: Whether to enable caching
        cache_ttl_seconds: Cache time-to-live in seconds
        max_cache_size: Maximum cache size
        enable_connection_pooling: Whether to enable connection pooling
        connection_pool_size: Connection pool size
        request_timeout_seconds: Request timeout in seconds
        enable_sqlite_cache: Whether to enable SQLite persistent caching
        sqlite_cache_ttl_hours: SQLite cache time-to-live in hours
        sqlite_cache_db_name: SQLite database filename

## SecuritySettings

User-configurable security settings.

    Attributes:
        rate_limit_requests_per_minute: Rate limit for requests per minute
        max_query_results: Maximum query results
        enable_field_validation: Whether to enable field validation
        allowed_field_patterns: Regex patterns for allowed fields
        block_sensitive_fields: Whether to block sensitive fields
        sensitive_field_patterns: Regex patterns for sensitive fields

## LoggingSettings

User-configurable logging settings.

    Attributes:
        log_level: Logging level
        log_format: Log format (json, text)
        enable_query_logging: Whether to enable query logging
        enable_performance_logging: Whether to enable performance logging
        log_sensitive_data: Whether to log sensitive data
        max_log_size_mb: Maximum log size in MB

## CampaignSettings

User-configurable campaign analysis settings.

    Attributes:
        correlation_window_minutes: Correlation window in minutes
        min_confidence_threshold: Minimum confidence threshold
        max_campaign_events: Maximum campaign events
        enable_geospatial_correlation: Whether to enable geospatial correlation
        enable_infrastructure_correlation: Whether to enable infrastructure correlation
        enable_behavioral_correlation: Whether to enable behavioral correlation
        enable_temporal_correlation: Whether to enable temporal correlation
        enable_ip_correlation: Whether to enable IP correlation
        max_expansion_depth: Maximum expansion depth
        expansion_timeout_seconds: Expansion timeout in seconds

## TCPTransportSettings

User-configurable TCP transport settings.

    Attributes:
        enabled: Whether TCP transport is enabled (default: False for STDIO mode)
        port: TCP port to bind to (default: 3000)
        bind_address: IP address to bind to (default: 127.0.0.1 for localhost)
        max_connections: Maximum number of concurrent connections
        connection_timeout_seconds: Connection timeout in seconds
        api_key_management: API key management configuration
        permissions: Default permissions for new API keys

## APIKeyManagementSettings

User-configurable API key management settings.

    Attributes:
        storage_provider: Secrets management provider (1password_cli, vault_cli, etc.)
        onepassword_cli: 1Password CLI specific settings
        defaults: Default settings for new API keys
        cache_ttl: Cache time-to-live in seconds
        auto_cleanup_expired: Whether to automatically cleanup expired keys

## TUISettings

User-configurable TUI settings.

    Attributes:
        enabled: Whether TUI is enabled (default: False for headless mode)
        refresh_interval_ms: UI refresh interval in milliseconds
        log_history_size: Number of log entries to keep in history
        server_management: Server management configuration
        panels: Panel configuration

## UserConfigManager

Manages user-configurable settings with validation and environment variable support.

    This class provides a comprehensive configuration management system that
    supports multiple configuration sources with precedence ordering:
    1. Environment variables (highest priority)
    2. User configuration file
    3. Base configuration
    4. Default values (lowest priority)

    Attributes:
        config_path: Path to the configuration file
        op_secrets: OnePassword secrets manager
        base_config: Base configuration dictionary
        query_settings: Query-related settings
        pagination_settings: Pagination-related settings
        streaming_settings: Streaming-related settings
        performance_settings: Performance-related settings
        security_settings: Security-related settings
        logging_settings: Logging-related settings
        campaign_settings: Campaign analysis settings
        tcp_transport_settings: TCP transport settings
        api_key_management_settings: API key management settings
        tui_settings: TUI settings
        output_directory: Directory for generated outputs
            (default: ~/dshield-mcp-output, configurable)

    Example:
        >>> manager = UserConfigManager()
        >>> output_dir = manager.output_directory
        >>> print(output_dir)

#### __init__

```python
def __init__(self, config_path)
```

Initialize the UserConfigManager.

        Args:
            config_path: Optional path to the configuration file

#### _load_user_config

```python
def _load_user_config(self)
```

Load user configuration from multiple sources with precedence.

        Loads configuration from environment variables, user config file,
        and base config, applying them in order of precedence.

#### _load_user_config_file

```python
def _load_user_config_file(self)
```

Load user configuration from file.

        If a specific config path was provided, use that. Otherwise, searches for
        user configuration files in multiple locations:
        - Current directory: user_config.yaml
        - Config directory: config/user_config.yaml
        - Home directory: ~/.dshield-mcp/user_config.yaml

        Returns:
            Dictionary containing user configuration or empty dict if not found

#### _apply_env_overrides

```python
def _apply_env_overrides(self)
```

Apply environment variable overrides to settings.

        Reads environment variables and applies them to the appropriate
        settings categories, overriding file-based configuration.

#### _apply_user_config

```python
def _apply_user_config(self, user_config)
```

Apply user configuration file settings.

        Args:
            user_config: User configuration dictionary

#### _validate_settings

```python
def _validate_settings(self)
```

Validate all settings for consistency and correctness.

        Performs validation checks on all configuration settings to ensure
        they are within acceptable ranges and consistent with each other.

        Raises:
            ValueError: If settings are invalid or inconsistent

#### get_setting

```python
def get_setting(self, category, setting)
```

Get a specific setting value.

        Args:
            category: Setting category (query, pagination, streaming, etc.)
            setting: Setting name within the category

        Returns:
            Setting value

        Raises:
            KeyError: If category or setting does not exist

#### update_setting

```python
def update_setting(self, category, setting, value)
```

Update a specific setting value.

        Args:
            category: Setting category (query, pagination, streaming, etc.)
            setting: Setting name within the category
            value: New value for the setting

        Raises:
            KeyError: If category or setting does not exist
            ValueError: If value is invalid for the setting

#### export_config

```python
def export_config(self)
```

Export current configuration as a dictionary.

        Returns:
            Dictionary containing all current configuration settings

#### save_user_config

```python
def save_user_config(self, file_path)
```

Save current configuration to a file.

        Args:
            file_path: Path to save the configuration file (default: auto-detected)

#### get_environment_variables

```python
def get_environment_variables(self)
```

Get environment variables that can be used to override settings.

        Returns:
            Dictionary mapping setting names to environment variable names

#### get_database_directory

```python
def get_database_directory(self)
```

Get the database directory path.

        Returns:
            str: Path to the database directory (~/dshield-mcp-output/db)

#### get_cache_database_path

```python
def get_cache_database_path(self)
```

Get the full path to the cache database file.

        Returns:
            str: Full path to the cache database file

### get_user_config

```python
def get_user_config()
```

Get the global user configuration manager instance.

    Returns:
        UserConfigManager: The global configuration manager instance

### reset_user_config

```python
def reset_user_config()
```

Reset the global user configuration manager instance.

    This function clears the global configuration manager, forcing
    a reload of configuration on the next get_user_config() call.
