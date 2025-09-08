# DShield MCP API Documentation

This directory contains the complete API documentation for the DShield MCP package in
Markdown format.

## Overview

The DShield MCP package provides a Model Context Protocol (MCP) server that integrates
with DShield's threat intelligence platform and Elasticsearch for security information and
event management (SIEM) operations.

## Documentation Structure

- `src/` - Main package documentation
  - `index.md` - Package overview and main entry point
  - `campaign_analyzer.md` - Campaign analysis tools
  - `data_processor.md` - Data processing utilities
  - `elasticsearch_client.md` - Elasticsearch integration
  - `dshield_client.md` - DShield API integration
  - And more...

## Usage

This Markdown documentation is designed for:
- AI ingestion and analysis
- Version control integration
- Plain text processing
- Documentation generation tools

## Quick Reference

### Core Modules

- **MCP Server**: Main server implementation (`mcp_server.py`)
- **Campaign Analyzer**: Threat campaign analysis (`campaign_analyzer.py`)
- **Data Processor**: Data processing and validation (`data_processor.py`)
- **Elasticsearch Client**: SIEM data operations (`elasticsearch_client.py`)
- **DShield Client**: Threat intelligence integration (`dshield_client.py`)

### Configuration

- **Config Loader**: YAML configuration with 1Password integration (`config_loader.py`)
- **User Config**: User preferences and settings (`user_config.py`)
- **1Password Secrets**: Secure secrets management (`op_secrets.py`)

### Utilities

- **Data Dictionary**: Schema management (`data_dictionary.py`)
- **Context Injector**: AI context utilities (`context_injector.py`)
- **Models**: Pydantic data models (`models.py`)

## Building Documentation

To regenerate this documentation:

```bash
./scripts/build_api_docs.sh
```

This will create both HTML and Markdown versions of the API documentation.
