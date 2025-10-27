"""DShield MCP - Elastic SIEM Integration Package.

This package provides a Model Context Protocol (MCP) server that integrates with
DShield's threat intelligence platform and Elasticsearch for security information
and event management (SIEM) operations.

## Overview

The DShield MCP package enables AI assistants to interact with security data
through a standardized protocol, providing tools for:

- Campaign analysis and threat intelligence
- Elasticsearch querying and data retrieval
- DShield API integration for threat feeds
- Data dictionary management for security events
- Context injection for enhanced AI interactions

## Main Components

### Core MCP Server
- `mcp_server.py`: Main MCP server implementation with tool registration

### Data Processing & Analysis
- `campaign_analyzer.py`: Campaign analysis and threat intelligence tools
- `data_processor.py`: Data processing, validation, and transformation utilities
- `data_dictionary.py`: Security event data dictionary and schema management

### External Integrations
- `dshield_client.py`: DShield API client for threat intelligence
- `elasticsearch_client.py`: Elasticsearch client for SIEM data operations

### Configuration & Security
- `config_loader.py`: Configuration management with YAML support
- `op_secrets.py`: 1Password CLI integration for secure secrets management
- `user_config.py`: User configuration and preferences management

### Utilities
- `context_injector.py`: Context injection utilities for AI interactions
- `models.py`: Pydantic models for data validation and serialization

## Usage

The package is designed to be used as an MCP server that can be integrated
with AI assistants supporting the Model Context Protocol. It provides a
comprehensive set of tools for security analysis and threat intelligence.

## Configuration

Configuration is managed through YAML files with support for 1Password CLI
integration for secure secrets management. See `config_loader.py` for details.

## Security

All sensitive information is managed through 1Password CLI integration,
ensuring no secrets are stored in plain text in configuration files.
"""

# DShield MCP - Elastic SIEM Integration Package
