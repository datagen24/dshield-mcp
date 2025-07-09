# DShield MCP API Documentation

This document provides a comprehensive reference for the DShield MCP API, including all modules, classes, functions, and their usage patterns.

## Overview

The DShield MCP package provides a complete API for integrating with DShield's threat intelligence platform and Elasticsearch for SIEM operations. This documentation covers all public APIs and their usage patterns.

## Quick Start

### Installation

```bash
# Install the package
pip install -r requirements.txt

# Install development dependencies (includes pdoc)
pip install -r requirements-dev.txt
```

### Basic Usage

```python
from src import dshield_client, elasticsearch_client, campaign_analyzer

# Initialize clients
dshield = dshield_client.DShieldClient()
es_client = elasticsearch_client.ElasticsearchClient()

# Perform operations
campaigns = await campaign_analyzer.analyze_campaigns()
```

## API Reference

### Core Modules

#### MCP Server (`mcp_server.py`)
The main MCP server implementation that registers and exposes all available tools.

**Key Classes:**
- `MCPServer`: Main server class that handles MCP protocol communication
- `ToolRegistry`: Manages tool registration and execution

**Key Functions:**
- `register_tools()`: Registers all available MCP tools
- `handle_request()`: Processes incoming MCP requests

#### Configuration (`config_loader.py`)
Configuration management with YAML support and 1Password integration.

**Key Functions:**
- `get_config(config_path: str = None) -> dict`: Load and parse configuration
- `_resolve_secrets(config: dict) -> dict`: Resolve 1Password secrets

**Exceptions:**
- `ConfigError`: Raised when configuration loading fails

### Data Processing & Analysis

#### Campaign Analyzer (`campaign_analyzer.py`)
Campaign analysis and threat intelligence tools.

**Key Classes:**
- `CampaignAnalyzer`: Main analyzer for threat campaigns
- `CampaignMetrics`: Metrics calculation and analysis

**Key Functions:**
- `analyze_campaigns()`: Analyze threat campaigns
- `get_campaign_metrics()`: Calculate campaign metrics
- `identify_campaign_patterns()`: Identify patterns in campaigns

#### Data Processor (`data_processor.py`)
Data processing, validation, and transformation utilities.

**Key Classes:**
- `DataProcessor`: Main data processing engine
- `DataValidator`: Data validation utilities
- `DataTransformer`: Data transformation utilities

**Key Functions:**
- `process_security_events()`: Process security event data
- `validate_data()`: Validate data against schemas
- `transform_data()`: Transform data between formats

#### Data Dictionary (`data_dictionary.py`)
Security event data dictionary and schema management.

**Key Classes:**
- `DataDictionary`: Main data dictionary manager
- `SchemaValidator`: Schema validation utilities

**Key Functions:**
- `get_field_definitions()`: Get field definitions
- `validate_schema()`: Validate data against schemas
- `get_data_types()`: Get supported data types

### External Integrations

#### DShield Client (`dshield_client.py`)
DShield API client for threat intelligence.

**Key Classes:**
- `DShieldClient`: Main DShield API client
- `ThreatFeedManager`: Threat feed management

**Key Functions:**
- `get_threat_feeds()`: Retrieve threat feeds
- `submit_reports()`: Submit threat reports
- `get_attack_sources()`: Get attack source information

#### Elasticsearch Client (`elasticsearch_client.py`)
Elasticsearch client for SIEM data operations.

**Key Classes:**
- `ElasticsearchClient`: Main Elasticsearch client
- `QueryBuilder`: Query construction utilities
- `ResultProcessor`: Result processing utilities

**Key Functions:**
- `search_events()`: Search for security events
- `index_document()`: Index documents
- `get_indices()`: Get available indices
- `create_query()`: Create Elasticsearch queries

### Configuration & Security

#### 1Password Secrets (`op_secrets.py`)
1Password CLI integration for secure secrets management.

**Key Classes:**
- `OnePasswordSecrets`: Main secrets manager

**Key Functions:**
- `resolve_environment_variable()`: Resolve 1Password references
- `get_secret()`: Retrieve secrets from 1Password

#### User Configuration (`user_config.py`)
User configuration and preferences management.

**Key Classes:**
- `UserConfig`: User configuration manager
- `ConfigValidator`: Configuration validation

**Key Functions:**
- `load_user_config()`: Load user configuration
- `save_user_config()`: Save user configuration
- `validate_config()`: Validate configuration

### Utilities

#### Context Injector (`context_injector.py`)
Context injection utilities for AI interactions.

**Key Classes:**
- `ContextInjector`: Main context injection manager
- `ContextBuilder`: Context building utilities

**Key Functions:**
- `inject_context()`: Inject context into AI interactions
- `build_context()`: Build context from data
- `merge_contexts()`: Merge multiple contexts

#### Models (`models.py`)
Pydantic models for data validation and serialization.

**Key Models:**
- `SecurityEvent`: Security event data model
- `CampaignData`: Campaign data model
- `QueryResult`: Query result model
- `ConfigModel`: Configuration model

## Usage Examples

### Basic Campaign Analysis

```python
from src.campaign_analyzer import CampaignAnalyzer
from src.elasticsearch_client import ElasticsearchClient

# Initialize components
es_client = ElasticsearchClient()
analyzer = CampaignAnalyzer(es_client)

# Analyze campaigns
campaigns = await analyzer.analyze_campaigns(
    time_range="24h",
    min_events=10
)

# Process results
for campaign in campaigns:
    print(f"Campaign: {campaign.name}")
    print(f"Events: {campaign.event_count}")
    print(f"Sources: {campaign.source_count}")
```

### Data Processing Pipeline

```python
from src.data_processor import DataProcessor
from src.data_dictionary import DataDictionary

# Initialize components
processor = DataProcessor()
dictionary = DataDictionary()

# Process security events
events = await processor.process_security_events(
    raw_data=raw_events,
    schema=dictionary.get_schema("security_event")
)

# Validate processed data
valid_events = processor.validate_data(events)
```

### DShield Integration

```python
from src.dshield_client import DShieldClient

# Initialize client
client = DShieldClient()

# Get threat feeds
feeds = await client.get_threat_feeds(
    feed_type="attacks",
    limit=100
)

# Submit threat report
report_id = await client.submit_reports(
    reports=threat_reports,
    priority="high"
)
```

## Error Handling

All API functions include comprehensive error handling:

```python
from src.config_loader import ConfigError
from src.elasticsearch_client import ElasticsearchError

try:
    config = get_config()
    es_client = ElasticsearchClient(config)
    results = await es_client.search_events(query)
except ConfigError as e:
    print(f"Configuration error: {e}")
except ElasticsearchError as e:
    print(f"Elasticsearch error: {e}")
```

## Configuration

### Environment Variables

The following environment variables are supported:

- `DSHIELD_API_KEY`: DShield API key
- `ELASTICSEARCH_URL`: Elasticsearch server URL
- `ELASTICSEARCH_USERNAME`: Elasticsearch username
- `ELASTICSEARCH_PASSWORD`: Elasticsearch password

### Configuration File

Configuration can be loaded from YAML files with 1Password integration:

```yaml
dshield:
  api_key: op://vault/item/field
  base_url: https://dshield.org/api

elasticsearch:
  url: op://vault/item/url
  username: op://vault/item/username
  password: op://vault/item/password
```

## Testing

Run the test suite to verify API functionality:

```bash
# Run all tests
pytest

# Run specific test module
pytest tests/test_campaign_analysis.py

# Run with coverage
pytest --cov=src
```

## Contributing

When adding new features or modifying existing APIs:

1. Update docstrings following Google style format
2. Add type annotations to all functions and classes
3. Include usage examples in docstrings
4. Update this documentation
5. Run the API documentation generator:

```bash
# Generate updated API documentation
./scripts/build_api_docs.sh
```

## Generated Documentation

For the most up-to-date API documentation, see the generated HTML documentation:

- **Location**: `docs/api/index.html`
- **Build Command**: `./scripts/build_api_docs.sh`
- **Auto-generated**: Updates automatically when docstrings change

The generated documentation includes:
- Complete API reference
- Interactive search functionality
- Source code examples
- Type annotations
- Cross-references between modules 