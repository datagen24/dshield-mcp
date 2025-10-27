# Configuration Guide

This guide covers configuration and user settings for DShield MCP.

## User Configuration Management

DShield MCP supports robust user configuration management, allowing you to customize query, pagination, streaming, performance, security, and logging settings. This system uses a layered approach:

- **user_config.yaml**: Place this file in the project root, `config/`, or `~/.dshield-mcp/`. See `user_config.example.yaml` for all available options and documentation.
- **Environment Variables**: Any setting in `user_config.yaml` can be overridden by an environment variable (see the example file for variable names).
- **Precedence**: Environment variables > user_config.yaml > built-in defaults.
- **Validation**: All settings are validated for correctness. Invalid values are rejected with clear errors.

### Example: user_config.yaml

```yaml
# Output directory for generated files (PDF reports, LaTeX outputs, etc.)
output_directory: ~/dshield-mcp-output

query:
  default_page_size: 100
  max_page_size: 1000
  enable_smart_optimization: true
  fallback_strategy: "aggregate"
  # ...
pagination:
  default_method: "page"
  # ...
# See user_config.example.yaml for all options
```

### Example: Environment Variable Override

```bash
# Output directory
export DMC_OUTPUT_DIRECTORY=/custom/path/to/outputs

# Query settings
export DEFAULT_PAGE_SIZE=50
export ENABLE_SMART_OPTIMIZATION=false
```

## Secrets Management

All secrets are managed through 1Password CLI integration to ensure security.

### 1Password CLI Integration

**All secrets resolved at runtime** via `op_secrets.py`:
- Format: `op://vault-name/item-name/field-name`
- Example: `ELASTICSEARCH_PASSWORD=op://DevSecOps/es-data01-elastic/password`
- **No plain text secrets in configuration files**
- Async secret resolution with fallback behavior

**Setup 1Password CLI**:
```bash
# macOS
brew install 1password-cli

# Authenticate
op signin
```

## Configuration Files

### mcp_config.yaml

Main configuration file for Elasticsearch, DShield API, and error handling settings.

### Environment Variables (.env)

- `ELASTICSEARCH_URL`: Elasticsearch cluster URL
- `ELASTICSEARCH_USERNAME`: Username (or `op://` reference)
- `ELASTICSEARCH_PASSWORD`: Password (or `op://` reference)
- `DSHIELD_API_KEY`: DShield API key (or `op://` reference)
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `LOG_FILE_PATH`: Optional log file path

## Elasticsearch Configuration

The Python Elasticsearch client version must match the major version of your Elasticsearch server for best compatibility.

### Version Compatibility

| Elasticsearch Server | Python Client Package | Version Constraint Example |
|---------------------|----------------------|----------------------------|
| 7.x                 | elasticsearch7       | elasticsearch7>=7.17,<8.0 |
| 8.x                 | elasticsearch        | elasticsearch>=8.7,<9.0   |
| 9.x                 | elasticsearch        | elasticsearch>=9.0,<10.0  |

### Compatibility Mode

The `elasticsearch` section in `mcp_config.yaml` supports:

- `compatibility_mode` (bool, default: false):
  - Set to `true` if using a v9 client with v8 Elasticsearch server
  - Uses compatibility headers for cross-version support

```yaml
elasticsearch:
  url: "https://your-es-server:9200"
  username: "..."
  password: "..."
  verify_ssl: true
  compatibility_mode: true
```
