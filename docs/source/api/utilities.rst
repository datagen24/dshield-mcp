Utilities Reference
===================

This section describes utility modules for configuration, security, and monitoring.

Configuration Management
------------------------

Config Loader
~~~~~~~~~~~~~

**Location**: ``src/config_loader.py`` (400+ lines)

YAML configuration loader with 1Password integration:

* Loads main configuration from ``mcp_config.yaml``
* Resolves 1Password secrets using ``op://`` references
* Validates configuration values
* Provides configuration merge and override capabilities

User Configuration
~~~~~~~~~~~~~~~~~~

**Location**: ``src/user_config.py`` (1500+ lines)

Comprehensive user configuration system:

* **Layered Configuration**: Environment variables > user_config.yaml > defaults
* **Validation**: All settings validated on load and update
* **Runtime Updates**: Dynamic configuration updates
* **Type Safety**: Pydantic-based validation

Configuration sections:

* Query settings (page size, optimization, timeouts)
* Pagination settings (methods, cursors, limits)
* Streaming settings (chunk size, session context)
* Performance settings (concurrency, caching)
* Security settings (rate limits, validation)
* Logging settings (levels, formats, outputs)

Secrets Management
------------------

1Password Integration
~~~~~~~~~~~~~~~~~~~~~

**Location**: ``src/op_secrets.py`` (350+ lines)

Secure secrets management via 1Password CLI:

* **Secret Resolution**: Resolve ``op://vault/item/field`` references
* **Async Resolution**: Non-blocking secret retrieval
* **Caching**: Intelligent caching of resolved secrets
* **Fallback**: Graceful degradation when 1Password unavailable

Error Handling
--------------

MCP Error Handler
~~~~~~~~~~~~~~~~~

**Location**: ``src/mcp_error_handler.py`` (900+ lines)

JSON-RPC 2.0 compliant error handling system:

* **Circuit Breaker**: CLOSED, OPEN, HALF_OPEN states
* **Retry Logic**: Exponential backoff with jitter
* **Error Aggregation**: Track and report error patterns
* **Rate Limiting**: Prevent error storms
* **Timeout Handling**: Configurable timeout management

Health & Features
-----------------

Health Check Manager
~~~~~~~~~~~~~~~~~~~~

**Location**: ``src/health_check_manager.py`` (400+ lines)

System health monitoring and reporting:

* **Dependency Health**: Monitor Elasticsearch, DShield API, 1Password
* **Status Reporting**: Detailed health status reports
* **Metrics Collection**: Track availability and performance
* **Alerting**: Health degradation notifications

Feature Manager
~~~~~~~~~~~~~~~

**Location**: ``src/feature_manager.py`` (300+ lines)

Feature availability and graceful degradation:

* **Feature Tracking**: Map tools to required dependencies
* **Health-Based Availability**: Disable features when dependencies fail
* **Graceful Degradation**: Continue operation with reduced functionality
* **Status Reporting**: Feature availability status

Data Models
-----------

**Location**: ``src/models.py`` (600+ lines)

Pydantic data models for type safety and validation:

* Event models for SIEM data
* Campaign and indicator models
* Configuration models
* Request/response models

Reporting
---------

LaTeX Template Tools
~~~~~~~~~~~~~~~~~~~~

**Location**: ``src/latex_template_tools.py`` (800+ lines)

PDF report generation using LaTeX templates:

* **Template Rendering**: Jinja2-based template rendering
* **PDF Compilation**: Automatic LaTeX to PDF compilation
* **Attack Reports**: Generate comprehensive attack reports
* **Campaign Summaries**: Campaign analysis report generation
* **Custom Templates**: Support for custom report templates
