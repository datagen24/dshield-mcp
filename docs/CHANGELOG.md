# Changelog

All notable changes to the DShield MCP project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Future enhancements and features in development

## [1.5.0] - 2025-07-06

### Added
- **Campaign Analysis Engine**: Advanced threat hunting and investigation capabilities for coordinated attack campaigns
  - Multi-stage correlation pipeline (7 stages: IP, infrastructure, behavioral, temporal, geospatial, signature, network)
  - 7 MCP tools for campaign investigation and analysis
  - Enhanced behavioral analysis with attack sequence detection, user agent patterns, and payload signatures
  - Network correlation with subnet-based analysis using `ipaddress` module
  - Campaign data models (Campaign, CampaignEvent, IndicatorRelationship)
  - IOC expansion with multiple strategies (comprehensive, infrastructure, temporal, network)
  - Timeline building with configurable granularity and TTP analysis
  - Campaign comparison and similarity analysis
  - Real-time campaign detection with configurable thresholds
  - User configuration integration for campaign settings
  - Production-ready for enterprise-scale event volumes (10,000+ events)
  - Comprehensive documentation: [CAMPAIGN_ANALYSIS_IMPLEMENTATION.md](docs/CAMPAIGN_ANALYSIS_IMPLEMENTATION.md)
  - Test coverage: 11/11 tests passing (100% success rate)
  - **PR**: [#23](https://github.com/datagen24/dsheild-mcp/pull/23) - Campaign Analysis Engine & Docs

- **Smart Chunking with Session Context**: Stream and chunk events by session context for better event correlation
  - Groups events by session context (source.ip, user.name, session.id)
  - Ensures related events stay together in the same chunk
  - Session summaries and performance metrics included in response
  - Fully integrated with MCP server and client
  - Extensible for future session-aware analytics
  - **Implementation**: [docs/smart_chunking_session_context.md](docs/smart_chunking_session_context.md)

- **Query Performance Metrics**: Track and return detailed query performance metrics for all queries
  - Tracks query time, indices scanned, documents examined, query complexity, optimizations applied
  - Metrics included in `pagination_metadata` and aggregation responses
  - Works for all query types: simple, complex, paginated, cursor-based, and aggregation
  - Enables visibility into backend performance and optimization effectiveness
  - **Implementation**: [docs/performance_metrics.md](docs/performance_metrics.md)

- **Smart Query Optimization**: Automatically optimize queries based on data volume
  - Automatic size estimation using count queries
  - Field optimization reducing to essential fields when results are too large
  - Page size reduction with minimum 10 events
  - Fallback strategies: aggregate, sample, error
  - Configuration: `max_result_size_mb` (default: 10.0), `query_timeout_seconds` (default: 30)
  - MCP integration with enhanced response formatting
  - Test coverage: Comprehensive test script in `dev_tools/test_smart_query_optimization.py`

- **Field Mapping Bug Fix**: Fix mismatch between display fields and query fields (Issue #17)
  - Intelligent field mapping automatically converts user-friendly field names to ECS dot notation
  - Comprehensive coverage: Maps 50+ common field variations
  - Backward compatibility: ECS dot notation continues to work unchanged
  - Helpful logging with field mapping suggestions
  - Query consistency: Both formats return identical results
  - Test coverage: Comprehensive test script in `dev_tools/test_field_mapping.py`

- **Pagination Support**: Robust pagination for large datasets
  - Both page-based and cursor-based (search_after) strategies
  - Sorting on single field (@timestamp) for Elasticsearch compatibility
  - Pagination metadata: page_size, page_number, total_available, has_more, total_pages, has_previous, has_next, sort_by, sort_order, next_page_token
  - Field selection, sorting, and time range queries fully supported
  - Test script: `dev_tools/test_enhanced_pagination_fixed.py`

- **Field Selection/Projection**: Enhanced query capabilities
  - Support for field selection in queries
  - Optimized data retrieval with specific field projection
  - Integration with pagination and sorting

- **Enhanced Time Range Handling**: Flexible time range queries
  - Absolute time ranges with start/end timestamps
  - Relative time ranges (e.g., "last_6_hours")
  - Time windows around specific events
  - Integration with all query types

- **Aggregation Queries**: Advanced data aggregation capabilities
  - Group by multiple fields (source_ip, destination_port, etc.)
  - Multiple metrics (count, unique_sessions, etc.)
  - Time range support with top_n results
  - Integration with performance metrics

- **Data Dictionary Module**: Comprehensive data dictionary with field descriptions, query examples, and analysis guidelines
- **Model Optimization**: Initial prompts and data patterns to reduce trial and error for AI models
- **New MCP Tool**: `get_data_dictionary` - Provides data dictionary in prompt or JSON format
- **New MCP Resource**: `dshield://data-dictionary` - Access data dictionary as a resource
- **Server Initialization Enhancement**: Data dictionary included in experimental capabilities for model initialization
- **Example Script**: `examples/data_dictionary_usage.py` - Demonstrates data dictionary functionality
- **Test Script**: `test_data_dictionary.py` - Comprehensive tests for data dictionary features

### Changed
- **User Configuration Management**: Robust user configuration system with layered approach
  - Support for user_config.yaml files in multiple locations
  - Environment variable overrides for all settings
  - Validation and runtime update support
  - Integration with all core MCP components
  - Test script: `dev_tools/test_user_configuration.py`

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
- **1.5.0**: Major feature release with comprehensive feature set including pagination, performance metrics, smart optimization, field mapping fixes, session context chunking, campaign analysis, and data dictionary capabilities
- **Unreleased**: Future enhancements and features in development

## Completed Features Summary

### High Priority Enhancements (All Complete in v1.5.0)
1. ✅ **Pagination Support** - Robust pagination for large datasets
2. ✅ **Field Selection/Projection** - Enhanced query capabilities  
3. ✅ **Enhanced Time Range Handling** - Flexible time range queries
4. ✅ **Aggregation Queries** - Advanced data aggregation capabilities
5. ✅ **Smart Query Optimization** - Automatic query optimization based on data volume
6. ✅ **Query Performance Metrics** - Detailed performance tracking for all queries
7. ✅ **Smart Chunking with Session Context** - Session-aware event streaming
8. ✅ **Field Mapping Bug Fix** - Intelligent field mapping (Issue #17)
9. ✅ **Campaign Analysis** - Advanced threat hunting and investigation capabilities

### Additional Completed Features (v1.5.0)
- ✅ **User Configuration Management** - Layered configuration system
- ✅ **Data Dictionary Module** - Comprehensive field documentation and examples
- ✅ **Model Optimization** - AI model prompts and data patterns
- ✅ **Index Pattern Optimization** - Performance improvements for Elasticsearch connections

### Production Readiness (v1.5.0)
All completed features are production-ready and tested with:
- Comprehensive test coverage (100% pass rates)
- Enterprise-scale data handling (10,000+ events)
- Performance optimization and monitoring
- Error handling and logging
- Documentation and usage examples
- MCP protocol compliance 