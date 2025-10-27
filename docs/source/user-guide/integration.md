# Integration Guide

This guide covers the complete setup and integration of DShield MCP with your security infrastructure.

## Prerequisites

### System Requirements

- **Python**: 3.10 or higher
- **Operating System**: Linux, macOS, or Windows (WSL recommended)
- **Memory**: Minimum 4GB RAM, 8GB+ recommended
- **Disk Space**: 1GB for application and logs

### Required Services

- **Elasticsearch**: Version 7.x, 8.x, or 9.x
  - Running and accessible instance
  - Valid credentials with read access to security indices
- **DShield API**: Valid API key from [DShield.org](https://dshield.org)
- **1Password CLI**: For secure secrets management (recommended)
- **LaTeX** (optional): For PDF report generation
  - macOS: MacTeX
  - Linux: TeX Live
  - Windows: MiKTeX

## Installation

### Step 1: Install UV Package Manager

UV is the recommended package manager for this project:

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installation
uv --version
```

### Step 2: Clone Repository

```bash
git clone https://github.com/datagen24/dshield-mcp.git
cd dshield-mcp
```

### Step 3: Install Dependencies

```bash
# Install all dependencies (including dev)
uv sync

# Or install just runtime dependencies
uv sync --no-dev
```

## Configuration

### Step 1: Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Elasticsearch Configuration
ELASTICSEARCH_URL=https://your-elasticsearch:9200
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=op://DevSecOps/es-data01-elastic/password
ELASTICSEARCH_VERIFY_SSL=true

# DShield API Configuration
DSHIELD_API_KEY=op://Security/dshield-api/api-key
DSHIELD_API_URL=https://dshield.org/api

# Logging Configuration
LOG_LEVEL=INFO
LOG_FILE_PATH=logs/dshield-mcp.log

# Optional: Output directory for reports
DMC_OUTPUT_DIRECTORY=~/dshield-mcp-output
```

**Important**: Use 1Password CLI references (`op://vault/item/field`) for all secrets to avoid storing credentials in plain text.

### Step 2: 1Password CLI Setup (Recommended)

Install and configure 1Password CLI for secure secrets management:

```bash
# macOS
brew install 1password-cli

# Linux
# Follow instructions at: https://developer.1password.com/docs/cli/get-started/

# Authenticate
op signin
```

Test the integration:

```bash
cd dev_tools
python test_op_integration.py
```

### Step 3: User Configuration (Optional)

Create `user_config.yaml` in the project root for custom settings:

```yaml
# Output directory for generated files
output_directory: ~/dshield-mcp-output

# Query settings
query:
  default_page_size: 100
  max_page_size: 1000
  enable_smart_optimization: true
  fallback_strategy: "aggregate"
  query_timeout_seconds: 30

# Pagination settings
pagination:
  default_method: "page"
  cursor_enabled: true

# Streaming settings
streaming:
  default_chunk_size: 100
  max_chunk_size: 500

# Performance settings
performance:
  max_result_size_mb: 10.0
  connection_pool_size: 10
  request_timeout_seconds: 30
```

See `user_config.example.yaml` for all available options.

### Step 4: Validate Configuration

```bash
# Test Elasticsearch connection
cd dev_tools
python debug_elasticsearch.py

# Test DShield API connection
python test_dshield_client.py
```

## Running the Server

### STDIO Mode (Default)

For MCP client integration (Claude Desktop, etc.):

```bash
uv run python mcp_server.py
```

This mode uses standard input/output for JSON-RPC communication.

### TCP Mode

For network-accessible server:

```bash
uv run python -m src.server_launcher --transport tcp
```

Configuration in `mcp_config.yaml`:

```yaml
tcp:
  host: "0.0.0.0"
  port: 8765
  auth:
    enabled: true
    require_client_auth: true
```

### TUI Mode (Interactive)

For interactive testing and monitoring:

```bash
uv run python -m src.tui_launcher
```

## MCP Client Integration

### Claude Desktop

Add to your Claude Desktop MCP configuration (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "dshield-mcp": {
      "command": "uv",
      "args": ["run", "python", "mcp_server.py"],
      "cwd": "/path/to/dshield-mcp",
      "env": {
        "ELASTICSEARCH_URL": "https://your-elasticsearch:9200",
        "ELASTICSEARCH_USERNAME": "elastic",
        "ELASTICSEARCH_PASSWORD": "op://vault/item/field"
      }
    }
  }
}
```

**macOS Location**: `~/Library/Application Support/Claude/claude_desktop_config.json`

**Linux Location**: `~/.config/Claude/claude_desktop_config.json`

### Other MCP Clients

For clients that support the MCP protocol:

1. **Set command**: `uv run python mcp_server.py`
2. **Set working directory**: Path to dshield-mcp
3. **Configure environment variables**: Elasticsearch and DShield credentials

## Elasticsearch Setup

### Version Compatibility

Match your Python client to your Elasticsearch server version:

| Elasticsearch Server | Python Client | Installation |
|---------------------|---------------|--------------|
| 7.x | elasticsearch7 | `uv add elasticsearch7>=7.17,<8.0` |
| 8.x | elasticsearch | `uv add elasticsearch>=8.7,<9.0` |
| 9.x | elasticsearch | `uv add elasticsearch>=9.0,<10.0` |

### Compatibility Mode

If using a v9 client with v8 server, enable compatibility mode in `mcp_config.yaml`:

```yaml
elasticsearch:
  compatibility_mode: true
```

### Index Configuration

Ensure your Elasticsearch instance has the required indices:

**Honeypot Data**:
- `cowrie-*`
- `cowrie.dshield-*`
- `cowrie.vt_data-*`
- `cowrie.webhoneypot-*`

**Network Data**:
- `filebeat-zeek-*`
- `zeek.connection*`
- `zeek.dns*`
- `zeek.http*`
- `zeek.ssl*`

### Required Permissions

The Elasticsearch user needs these permissions:

```json
{
  "indices": [
    {
      "names": ["cowrie-*", "zeek.*", "filebeat-zeek-*"],
      "privileges": ["read", "view_index_metadata"]
    }
  ]
}
```

## DShield API Setup

### Obtain API Key

1. Visit [DShield.org](https://dshield.org)
2. Create an account or log in
3. Navigate to API section
4. Generate API key

### Store in 1Password

```bash
# Create 1Password item
op item create \
  --category=api-credential \
  --title="DShield API" \
  --vault="Security" \
  --field label=api-key,type=concealed,value=YOUR_API_KEY
```

### Configure in Environment

```bash
DSHIELD_API_KEY=op://Security/DShield API/api-key
```

## Firewall Configuration

### Outbound Requirements

Allow outbound connections to:

- **Elasticsearch**: Your ES cluster URL (typically port 9200)
- **DShield API**: `https://dshield.org/api` (port 443)
- **1Password**: `https://*.1password.com` (port 443)

### Inbound Requirements (TCP Mode Only)

Allow inbound connections to:

- **TCP Server**: Configured port (default: 8765)

## Security Hardening

### TLS/SSL Configuration

For Elasticsearch with self-signed certificates:

```yaml
elasticsearch:
  verify_ssl: true
  ca_certs: /path/to/ca-cert.pem
```

### Rate Limiting

Configure in `mcp_config.yaml`:

```yaml
security:
  rate_limit:
    requests_per_minute: 60
    burst_size: 10
```

### Authentication (TCP Mode)

Enable client authentication:

```yaml
tcp:
  auth:
    enabled: true
    require_client_auth: true
    allowed_clients:
      - client_id: "client1"
        client_secret: "op://Security/tcp-client1/secret"
```

## Verification

### Run Health Check

```bash
# Using the MCP tool
{
  "tool": "get_health_status",
  "arguments": {}
}
```

Expected response:

```json
{
  "status": "healthy",
  "elasticsearch": {
    "status": "connected",
    "version": "8.x.x"
  },
  "dshield_api": {
    "status": "available"
  },
  "features": {
    "query_tools": "available",
    "campaign_analysis": "available",
    "statistical_analysis": "available"
  }
}
```

### Run Test Query

```bash
# Query last 24 hours
{
  "tool": "query_dshield_events",
  "arguments": {
    "time_range_hours": 24,
    "page_size": 10
  }
}
```

### Run Tests

```bash
# Unit tests
uv run pytest -m unit

# Integration tests (requires Elasticsearch)
uv run pytest -m integration

# Full test suite
uv run pytest
```

## Troubleshooting

### Elasticsearch Connection Issues

**Problem**: Cannot connect to Elasticsearch

**Solutions**:
1. Verify Elasticsearch is running: `curl -k https://your-elasticsearch:9200`
2. Check credentials in `.env`
3. Verify SSL/TLS settings
4. Check firewall rules
5. Review logs: `tail -f logs/dshield-mcp.log`

### 1Password Issues

**Problem**: Cannot resolve secrets

**Solutions**:
1. Verify 1Password CLI is installed: `op --version`
2. Check authentication: `op whoami`
3. Test secret resolution: `op read "op://vault/item/field"`
4. Review logs for 1Password errors

### Missing Index Issues

**Problem**: Elasticsearch queries return no results

**Solutions**:
1. Verify indices exist: `GET /_cat/indices?v`
2. Check index patterns in `mcp_config.yaml`
3. Verify user permissions on indices
4. Use data dictionary tool to see available fields

### Performance Issues

**Problem**: Queries are slow

**Solutions**:
1. Enable smart optimization: `optimization: "auto"`
2. Reduce page size: `page_size: 100`
3. Use field filtering: `fields: ["@timestamp", "source_ip"]`
4. Use cursor pagination for large datasets
5. Adjust timeout settings in `user_config.yaml`

## Monitoring

### Logs

Logs are written to:
- Console (stdout/stderr)
- File: `logs/dshield-mcp.log` (if LOG_FILE_PATH is set)

Log format: JSON structured logging with:
- Timestamp
- Level
- Message
- Context (operation, request_id, etc.)

### Metrics

Monitor these metrics:
- Query latency (avg, p95, p99)
- Circuit breaker status
- Error rates by tool
- Elasticsearch connection pool usage

### Health Monitoring

Use the `get_health_status` tool regularly to monitor:
- Elasticsearch connectivity
- DShield API availability
- Feature status
- Circuit breaker state

## Next Steps

- Read the [Usage Guide](usage.md) for tool examples
- Review [Configuration Guide](configuration.md) for advanced settings
- See [Error Handling Guide](error-handling.md) for troubleshooting
- Explore [API Reference](../api/tools.rst) for tool documentation

## Support

For issues or questions:

1. Check [Troubleshooting](#troubleshooting) section
2. Review logs: `logs/dshield-mcp.log`
3. Run health check: `get_health_status` tool
4. Open an issue: [GitHub Issues](https://github.com/datagen24/dshield-mcp/issues)
