# DShield MCP - Elastic SIEM Integration

This MCP (Model Context Protocol) utility connects your DShield SIEM with ChatGPT to enhance security analysis and threat intelligence workflows. It's specifically optimized for DShield SIEM data structures and patterns.

## Features

- **DShield SIEM Integration**: Query DShield-specific indices and data from Elasticsearch
- **DShield Threat Intelligence**: Correlate IP addresses with DShield reputation and attack data
- **DShield Attack Analysis**: Analyze attack patterns, top attackers, and geographic distribution
- **DShield Statistics**: Generate comprehensive DShield-specific security statistics
- **Structured Data Export**: Format DShield security data for ChatGPT analysis
- **Real-time Context Injection**: Provide relevant DShield security context to AI conversations
- **Comprehensive Data Dictionary**: Built-in data dictionary with field descriptions, query examples, and analysis guidelines
- **Model Optimization**: Initial prompts and data patterns to reduce trial and error for AI models
- **Config Optimization**: Streamlined index patterns to minimize connection retries
- **LaTeX Template Automation**: Generate professional security reports using customizable LaTeX templates with variable substitution and PDF compilation
- **Data Availability Diagnostics**: Comprehensive troubleshooting tools for data availability issues with actionable recommendations
- **Persistent API Key Management**: Secure API key storage and management with 1Password integration, configurable permissions, and expiration handling

## DShield-Specific Capabilities

### DShield Indices Support
The following index patterns are supported and optimized for minimal retries:

**Cowrie Honeypot Data:**
- `cowrie-*` - General Cowrie honeypot data
- `cowrie.dshield-*` - DShield-specific Cowrie data
- `cowrie.vt_data-*` - VirusTotal integration data
- `cowrie.webhoneypot-*` - Web honeypot data

**Zeek Network Data:**
- `filebeat-zeek-*` - Filebeat Zeek logs
- `zeek.connection*` - Zeek connection logs
- `zeek.dns*` - Zeek DNS logs
- `zeek.files*` - Zeek file logs
- `zeek.http*` - Zeek HTTP logs
- `zeek.ssl*` - Zeek SSL/TLS logs

*Note: Non-existent index patterns have been removed to optimize performance and reduce connection retries.*

### DShield Data Models
- **DShieldAttack**: Structured attack event data
- **DShieldReputation**: IP reputation and threat intelligence
- **DShieldTopAttacker**: Top attacker analysis
- **DShieldGeographicData**: Geographic attack distribution
- **DShieldPortData**: Port-based attack analysis
- **DShieldStatistics**: Comprehensive DShield statistics

### API Key Management
The system provides comprehensive API key management with persistent storage and security features:

**Key Features:**
- **Persistent Storage**: API keys stored securely in 1Password using the `op` CLI
- **Configurable Permissions**: Granular permission control (read tools, write back, admin access)
- **Expiration Management**: Configurable expiration periods with automatic validation
- **Rate Limiting**: Per-key rate limiting to prevent abuse
- **TUI Management**: Visual interface for key generation, management, and deletion
- **Session Management**: Automatic session termination when keys are revoked

**Configuration:**
```yaml
api_key_management:
  storage_provider: "1password_cli"
  onepassword_cli:
    vault: "DShield-MCP"  # Your 1Password vault name
    cache_ttl: 60
    sync_interval: 60
  defaults:
    expiration_days: 90
    rate_limit_per_minute: 60
    permissions:
      read_tools: true
      write_back: false
      admin_access: false
```

**Usage:**
- Generate keys through the TUI interface or programmatically
- Keys are automatically loaded on server startup
- Expired keys are automatically rejected
- Keys can be deleted with automatic session termination

### Diagnostic & Troubleshooting
The system includes comprehensive diagnostic capabilities to help troubleshoot data availability issues:

- **Data Availability Diagnostics**: Identify why queries return empty results
- **Index Pattern Validation**: Verify configured index patterns match available indices
- **Field Mapping Analysis**: Examine index mappings and field availability
- **Data Freshness Checks**: Validate data availability across different time ranges
- **Query Pattern Testing**: Test various index patterns to find working configurations
- **Actionable Recommendations**: Get specific steps to resolve common issues

**Available as MCP Tool**: `diagnose_data_availability`

**Usage Example**:
```python
# Run comprehensive diagnostics
diagnosis = await threat_manager.diagnose_data_availability(
    check_indices=True,      # Check available indices
    check_mappings=True,     # Check field mappings
    check_recent_data=True,  # Check data freshness
    sample_query=True        # Test query patterns
)

# Review results and follow recommendations
for rec in diagnosis['recommendations']:
    print(f"- {rec}")
```

### Data Dictionary & Model Optimization
The system includes a comprehensive data dictionary that helps AI models understand DShield data structures:

- **Field Descriptions**: Detailed explanations of all available fields with examples
- **Query Examples**: Pre-built query patterns for common security analysis tasks
- **Data Patterns**: Recognition patterns for attack types, threat levels, and time-based analysis
- **Analysis Guidelines**: Correlation rules and response priorities for threat assessment
- **Initial Prompts**: Built-in prompts provided to models during initialization to reduce trial and error

**Available as:**
- MCP Tool: `get_data_dictionary`
- MCP Resource: `dshield://data-dictionary`
- Server Initialization: Included in experimental capabilities

## Documentation

### API Documentation
Comprehensive API documentation is available for developers and integrators:

- **[API Reference](docs/API_DOCUMENTATION.md)**: Complete API reference with usage examples
- **[Generated HTML Docs](docs/api/index.html)**: Auto-generated HTML documentation
- **[Build Script](scripts/build_api_docs.sh)**: Generate updated API documentation

To generate the latest API documentation:
```bash
# Install development dependencies (includes pdoc)
pip install -r requirements-dev.txt

# Generate API documentation
./scripts/build_api_docs.sh
```

### Implementation Documentation
For detailed implementation information and development history:

- **[Implementation Docs](docs/)**: Comprehensive implementation documentation
- **[Enhancements](docs/Enhancements.md)**: Feature additions and improvements
- **[Changelog](docs/CHANGELOG.md)**: Version history and changes

## Quick Start

### Prerequisites

- Python 3.10 or higher (UV will install the correct version if needed)
- UV package manager
- Access to Elasticsearch cluster with DShield data
- DShield API key (optional, for threat intelligence enrichment)
- LaTeX distribution (optional, for PDF report generation)
  - **macOS**: Install MacTeX or BasicTeX via `brew install --cask mactex` or `brew install --cask basictex`
  - **Linux**: Install TeX Live via `sudo apt-get install texlive-full` (Ubuntu/Debian) or `sudo yum install texlive-scheme-full` (RHEL/CentOS)
  - **Windows**: Install MiKTeX from https://miktex.org/download

### UV Package Manager Installation

**Install UV first:**
```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pip
pip install uv
```

### Environment Setup

#### Option 1: Automated Setup (Recommended)

**Linux/macOS:**
```bash
# Make setup script executable (if needed)
chmod +x setup_venv.sh

# Run automated setup
./setup_venv.sh
```

**Windows:**
```cmd
# Run automated setup
setup_venv.bat
```

#### Option 2: Manual UV Setup

**All platforms:**
```bash
# Install project dependencies
uv sync

# Install development dependencies
uv sync --group dev

# Copy environment template
cp .env.example .env
```

#### Option 3: Traditional pip Setup (Legacy)

**Linux/macOS:**
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env
```

**Windows:**
```cmd
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate.bat

# Upgrade pip
python -m pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt

# Copy environment template
copy .env.example .env
```

### Configuration

1. **Edit Environment Variables**:
   ```bash
   # Edit the .env file with your configuration
   nano .env  # or use your preferred editor
   ```

2. **Required Configuration**:
   ```bash
   # Elasticsearch Configuration
   ELASTICSEARCH_URL=https://your-elasticsearch-cluster:9200
   ELASTICSEARCH_USERNAME=elastic
   ELASTICSEARCH_PASSWORD=your-password

   # DShield API Configuration (optional)
   DSHIELD_API_KEY=your-dshield-api-key
   DSHIELD_API_URL=https://dshield.org/api
   ```

### Advanced User Configuration

See [docs/README.md](docs/README.md) (User Configuration Management section) for advanced settings, environment variable overrides, and runtime customization.

#### Output Directory Configuration

Generated files (PDF reports, LaTeX outputs, etc.) are written to a configurable output directory:

- **Default**: `~/dshield-mcp-output` (cross-platform)
- **YAML Config**: Add `output_directory: /path/to/outputs` to your `user_config.yaml`
- **Environment Variable**: Set `DMC_OUTPUT_DIRECTORY=/path/to/outputs`

The output directory is created automatically if it doesn't exist.

### Running the Application

#### Option 1: Using UV (Recommended)

**All platforms:**
```bash
# Run the MCP server directly with UV
uv run python mcp_server.py

# Run the TUI interface
uv run python -m src.tui_launcher

# Run the TCP server
uv run python -m src.server_launcher --transport tcp

# Run examples
uv run python examples/basic_usage.py

# Run tests
uv run pytest
```

#### Option 2: Traditional Virtual Environment

**Linux/macOS:**
```bash
# Use the activation script
./activate_venv.sh

# Or manually activate
source .venv/bin/activate

# Run the MCP server
python mcp_server.py
```

**Windows:**
```cmd
.venv\Scripts\activate.bat
python mcp_server.py
```

#### Run the MCP Server (STDIO default)
```bash
# Using UV (recommended)
uv run python mcp_server.py

# Or with traditional virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate.bat  # Windows
python mcp_server.py

STDIO is the default and recommended mode for analyst workstations. Advanced modes include TCP server and the optional Textual-based TUI.
```

#### Run Examples
```bash
# Using UV (recommended)
uv run python examples/basic_usage.py
uv run python examples/data_dictionary_usage.py
uv run python examples/latex_template_usage.py
uv run python examples/enhanced_threat_intelligence_usage.py
uv run python examples/statistical_anomaly_detection_usage.py

# Or with traditional virtual environment
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate.bat  # Windows

python examples/basic_usage.py
python examples/data_dictionary_usage.py
python examples/latex_template_usage.py
python examples/enhanced_threat_intelligence_usage.py
python examples/statistical_anomaly_detection_usage.py
```

#### Deactivate Virtual Environment
```bash
deactivate
```

## 📚 Documentation

For comprehensive documentation, see the [docs/](docs/) folder:

- **[Documentation Index](docs/README.md)** - Complete documentation overview
- **[Usage Guide](docs/USAGE.md)** - Detailed usage examples and API reference
- **[Changelog](docs/CHANGELOG.md)** - Version history and changes
- **[Release Notes](docs/RELEASE_NOTES_v1.0.md)** - Current release information
- **[Enhancements](docs/Enhancements.md)** - Planned features and roadmap
- **[Implementation Guides](docs/)** - Technical implementation details

## Development Setup

For development work, install additional development dependencies:

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate.bat  # Windows

# Install development dependencies
pip install -r requirements-dev.txt
```

### Development Tools

- **Testing**: `pytest`
- **Code Formatting**: `black`
- **Linting**: `flake8`
- **Type Checking**: `mypy`
- **Documentation**: `sphinx`

### Development Scripts

Development and testing scripts are located in the `dev_tools/` folder:

```bash
# Navigate to development tools
cd dev_tools

# Run core functionality tests
python test_mcp_server.py
python test_installation.py

# Run feature tests
python test_enhanced_features.py
python test_streaming.py

# Debug tools
python debug_elasticsearch.py
```

**Note**: The `dev_tools/` folder is excluded from releases and contains scripts for development and debugging purposes only. See `dev_tools/README.md` for detailed documentation.

## Configuration

### Environment Variables

- `ELASTICSEARCH_URL`: Your Elasticsearch cluster URL
- `ELASTICSEARCH_USERNAME`: Elasticsearch username
- `ELASTICSEARCH_PASSWORD`: Elasticsearch password
- `DSHIELD_API_KEY`: DShield API key for threat intelligence
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `LOG_FILE_PATH`: Optional path to a log file (recommended). JSON-RPC protocol messages are sent on stdout; logs are written to stderr and to the configured file.

### 1Password Integration

The DShield MCP supports 1Password CLI integration for secure secret management. You can use `op://` URLs in your environment variables to automatically resolve secrets from 1Password.

#### Setup 1Password CLI

1. **Install 1Password CLI**:
   ```bash
   # macOS (using Homebrew)
   brew install 1password-cli

   # Linux
   # Download from: https://1password.com/downloads/command-line/

   # Windows
   # Download from: https://1password.com/downloads/command-line/
   ```

2. **Authenticate with 1Password**:
   ```bash
   op signin
   ```

#### Using op:// URLs

Replace sensitive values in your `.env` file with 1Password URLs:

```bash
# Instead of plain text passwords/keys:
ELASTICSEARCH_PASSWORD=your-password-here
DSHIELD_API_KEY=your-api-key-here

# Use 1Password URLs:
ELASTICSEARCH_PASSWORD=op://vault/elasticsearch/password
DSHIELD_API_KEY=op://vault/dshield/api-key
```

#### 1Password URL Format

- **Format**: `op://vault-name/item-name/field-name`
- **Examples**:
  - `op://vault/elasticsearch/password` - Password from Elasticsearch item
  - `op://vault/dshield/api-key` - API key from DShield item
  - `op://vault/credentials/username` - Username from credentials item

#### Testing 1Password Integration

Test your 1Password setup:
```bash
# Activate virtual environment
source venv/bin/activate

# Test 1Password integration (in dev_tools folder)
cd dev_tools && python test_op_integration.py
```

#### Security Benefits

- **No plain text secrets** in configuration files
- **Centralized secret management** in 1Password
- **Automatic secret rotation** through 1Password
- **Audit trail** for secret access
- **Team collaboration** on secret management

#### Fallback Behavior

If 1Password CLI is not available or fails to resolve a URL:
- The system will log a warning
- The original `op://` URL will be used as-is
- This prevents application crashes if 1Password is unavailable

### Transports and OS Targets

- Default: STDIO (analyst workstations)
- Advanced: TCP server and TUI
- TCP targets: macOS hosts and Red Hat UBI-based container (planned; container support will be finalized in a future iteration)

### DShield Elasticsearch Indices

The utility is specifically configured to work with DShield SIEM indices:
- Automatically discovers available DShield indices
- Falls back to general SIEM indices if DShield-specific ones don't exist
- Supports DShield field mappings and data structures

## Usage Examples

### Query DShield Events
```python
# Get DShield events from the last 24 hours
events = query_dshield_events(hours=24)

# Get DShield attack data specifically
attacks = query_dshield_attacks(hours=24)

# Get DShield top attackers
top_attackers = query_dshield_top_attackers(hours=24, limit=100)

# Get DShield geographic data
geo_data = query_dshield_geographic_data()

# Get DShield port data
port_data = query_dshield_port_data()
```

### DShield Reputation and Threat Intelligence
```python
# Query DShield reputation data for IP addresses
reputation = query_dshield_reputation(ip_addresses=["192.168.1.100"])

# Enrich IP with DShield threat intelligence
threat_data = enrich_ip_with_dshield("192.168.1.100")

# Get DShield statistics
stats = get_dshield_statistics(time_range_hours=24)
```

### Generate DShield Attack Report
```python
# Generate structured attack report with DShield data
report = generate_attack_report(events=events, threat_intelligence=ti_data)

# Get security summary with DShield enrichment
summary = get_security_summary(include_threat_intelligence=True)
```

### LaTeX Template Automation
```python
# List available templates
templates = list_latex_templates()

# Get template schema and requirements
schema = get_latex_template_schema(template_name="Attack_Report")

# Validate document data
validation = validate_latex_document_data(
    template_name="Attack_Report",
    document_data={"title": "Security Incident Report", "author": "Security Team"}
)

# Generate LaTeX document with PDF compilation
result = generate_latex_document(
    template_name="Attack_Report",
    document_data={
        "title": "DShield Attack Analysis Report",
        "author": "Security Operations Center",
        "date": "2025-01-27",
        "executive_summary": "Critical security incident detected...",
        "threat_actors": ["APT29", "Lazarus Group"],
        "affected_systems": ["Web Server", "Database"],
        "recommendations": ["Implement MFA", "Update firewall rules"]
    },
    output_format="pdf",
    output_directory="./reports"
)
```

## DShield-Specific Tools

### Available MCP Tools

1. **query_dshield_events** - Query DShield events from Elasticsearch
2. **query_dshield_attacks** - Query DShield attack data specifically
3. **query_dshield_reputation** - Query DShield reputation data for IP addresses
4. **query_dshield_top_attackers** - Query DShield top attackers data
5. **query_dshield_geographic_data** - Query DShield geographic attack data
6. **query_dshield_port_data** - Query DShield port attack data
7. **get_dshield_statistics** - Get comprehensive DShield statistics
8. **enrich_ip_with_dshield** - Enrich IP with DShield threat intelligence
9. **generate_attack_report** - Generate attack report with DShield data
10. **query_events_by_ip** - Query DShield events for specific IP addresses
11. **get_security_summary** - Get security summary with DShield enrichment
12. **list_latex_templates** - List available LaTeX templates
13. **get_latex_template_schema** - Get schema and variable requirements for a template
14. **validate_latex_document_data** - Validate document data against template schema
15. **generate_latex_document** - Generate LaTeX document with variable substitution

### Available Resources

- `dshield://events` - Recent DShield events
- `dshield://attacks` - Recent DShield attack data
- `dshield://top-attackers` - DShield top attackers data
- `dshield://statistics` - DShield statistics and summary data
- `dshield://threat-intelligence` - DShield threat intelligence data

## DShield Data Analysis

### Attack Pattern Detection
The utility detects DShield-specific attack patterns:
- Brute force attacks
- Port scanning
- SQL injection
- Cross-site scripting (XSS)
- DDoS attacks
- Malware activity
- Phishing attempts
- Reconnaissance
- Exploits
- Backdoors
- Data exfiltration
- Privilege escalation
- Persistence mechanisms

### Geographic Analysis
- Attack distribution by country
- Top attacking countries
- Geographic threat intelligence
- Country-based reputation scoring

### Network Analysis
- Port-based attack analysis
- Protocol usage patterns
- ASN-based threat analysis
- Organization-based threat analysis

### Reputation Analysis
- DShield reputation scoring
- Threat level assessment
- Historical attack data
- First/last seen timestamps
- Attack type categorization

## Architecture

### Core Components

1. **ElasticsearchClient** - Optimized for DShield SIEM queries
2. **DShieldClient** - DShield API integration for threat intelligence
3. **DataProcessor** - DShield-specific data processing and analysis
4. **ContextInjector** - Prepare DShield context for ChatGPT
5. **MCP Server** - Protocol communication and tool coordination

### Data Flow

1. **Query DShield Data**: Query DShield-specific indices in Elasticsearch
2. **Enrich with Threat Intelligence**: Correlate with DShield API data
3. **Process and Analyze**: Apply DShield-specific analysis patterns
4. **Generate Reports**: Create structured DShield attack reports
5. **Inject Context**: Provide DShield context to ChatGPT

## Security Considerations

- **API Key Management**: Store DShield API keys securely
- **Rate Limiting**: Respect DShield API rate limits
- **Data Privacy**: Ensure compliance with data protection regulations
- **Network Security**: Use secure connections to Elasticsearch and DShield APIs
- **Access Control**: Implement proper access controls for the MCP server

## Performance Optimization

- **Index Discovery**: Automatically discover available DShield indices
- **Field Mapping**: Optimized DShield field mappings for efficient queries
- **Caching**: Implement caching for frequently accessed DShield data
- **Batch Processing**: Process DShield data in batches for efficiency
- **Connection Pooling**: Reuse connections to Elasticsearch and DShield APIs

## Troubleshooting

### Common Issues

1. **Virtual Environment Issues**:
   - Ensure Python 3.8+ is installed
   - Check that `python3 -m venv` is available
   - Verify virtual environment is activated before running commands

2. **DShield Indices Not Found**: Check if DShield indices exist in your Elasticsearch cluster
3. **API Rate Limiting**: Implement proper rate limiting for DShield API calls
4. **Field Mapping Issues**: Verify DShield field mappings match your data structure
5. **Connection Timeouts**: Adjust timeout settings for large DShield queries

### Debug Mode

Enable debug logging to troubleshoot issues:
```bash
# Activate virtual environment first
source venv/bin/activate

# Set debug logging
export LOG_LEVEL=DEBUG

# Run with debug output
python mcp_server.py
```

### Virtual Environment Management

**Check if virtual environment is active:**
```bash
# Should show path to venv/bin/python
which python
```

**Recreate virtual environment if needed:**
```bash
# Remove old environment
rm -rf venv

# Run setup again
./setup_venv.sh
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Set up development environment:
   ```bash
   ./setup_venv.sh
   pip install -r requirements-dev.txt
   ```
4. Make your changes
5. Add tests for new DShield functionality
6. Run tests: `pytest`
7. Format code: `black .`
8. Submit a pull request

## License

This project is licensed under the BSD 4-Clause License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions about DShield integration:
- Check the [USAGE.md](USAGE.md) for detailed usage instructions
- Review the examples in the `examples/` directory
- Open an issue on GitHub for bugs or feature requests

## DShield Integration Credits

This utility is specifically designed to work with the [DShield-SIEM](https://github.com/bruneaug/DShield-SIEM) project and follows DShield data patterns and structures.
## TUI Tests: Headless Mode and Manual Checks

Unit tests for the Textual TUI run in a headless mode to avoid spawning real
terminal I/O threads during CI. This improves reliability and prevents stray
background processes.

- The test helper uses a headless/null driver and disables costly UI refreshes.
- Some heavy UI loop tests (e.g. memory‑usage stress) are shortened or skipped
  in CI via `TUI_HEADLESS=1` / `TUI_FAST=1` to avoid long redraw loops and
  potential driver stalls in sandboxed runners.

Manual validation:
- To manually validate full UI behavior, unset headless flags and run specific
  tests locally:
  - `unset TUI_HEADLESS TUI_FAST && pytest -q tests/tui/test_status_bar.py::TestStatusBar::test_status_bar_memory_usage`
- Or run the TUI application normally and exercise the status bar updates.

Note: The headless mode is test‑only and does not affect production behavior.
