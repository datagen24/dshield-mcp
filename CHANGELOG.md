# Changelog

All notable changes to the DShield MCP project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Data Dictionary Module**: Comprehensive data dictionary with field descriptions, query examples, and analysis guidelines
- **Model Optimization**: Initial prompts and data patterns to reduce trial and error for AI models
- **New MCP Tool**: `get_data_dictionary` - Provides data dictionary in prompt or JSON format
- **New MCP Resource**: `dshield://data-dictionary` - Access data dictionary as a resource
- **Server Initialization Enhancement**: Data dictionary included in experimental capabilities for model initialization
- **Example Script**: `examples/data_dictionary_usage.py` - Demonstrates data dictionary functionality
- **Test Script**: `test_data_dictionary.py` - Comprehensive tests for data dictionary features

### Changed
- **Index Pattern Optimization**: Removed non-existent index patterns from configuration to reduce connection retries
- **Updated Index Support**: Streamlined to focus on actual Cowrie and Zeek indices
- **Enhanced Documentation**: Updated README.md and USAGE.md with new features and optimizations

### Removed
- **Non-existent Index Patterns**: Removed patterns for indices that don't exist to optimize performance
- **Legacy DShield Index References**: Updated documentation to reflect actual supported indices

## [1.0.0] - 2024-01-15

### Added
- Initial release of DShield MCP server
- Elasticsearch integration for DShield SIEM data
- DShield threat intelligence enrichment
- Basic MCP tools for security analysis
- Configuration management and testing utilities
- Example scripts and documentation

### Features
- Query DShield events from Elasticsearch
- Enrich IP addresses with DShield reputation data
- Generate attack reports and security summaries
- Real-time context injection for AI conversations
- Comprehensive configuration management
- Development and testing tools

---

## Version History

- **1.0.0**: Initial release with basic DShield MCP functionality
- **Unreleased**: Enhanced with data dictionary and configuration optimizations 