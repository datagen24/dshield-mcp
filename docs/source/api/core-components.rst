Core Components
===============

This section documents the core components that power the DShield MCP server. These components provide the foundational services for data access, analysis, error handling, and system management.

Overview
--------

The DShield MCP architecture consists of several key components:

* **DShieldMCPServer** - Central orchestration and MCP protocol implementation
* **Data Layer** - Elasticsearch client, data processing, and dictionary management
* **Analysis Layer** - Campaign analysis and threat intelligence
* **Tool System** - Tool registration, dispatch, and execution
* **Error Handling** - Circuit breakers, error responses, and resilience
* **Feature Management** - Health checks and graceful degradation
* **Security** - Validation, rate limiting, and secret management

Server Core
-----------

DShieldMCPServer
~~~~~~~~~~~~~~~~

The central orchestration point that implements the MCP protocol and coordinates all subsystems.

**Responsibilities**:

* MCP protocol implementation (tools, resources, prompts)
* Component initialization and lifecycle management
* Request routing and response handling
* Tool registration and dispatch
* Resource management

**Design Patterns**:

* **Facade Pattern** - Provides simplified interface to complex subsystems
* **Dependency Injection** - Components accept optional dependencies for testability
* **Async/Await** - All I/O operations are asynchronous

**Key Features**:

* Automatic tool loading and registration
* Dynamic feature availability based on health
* Circuit breaker integration
* Structured logging with operation tracking
* Graceful shutdown handling

**Architecture**::

    Client Request (JSON-RPC 2.0)
           ↓
    DShieldMCPServer
           ↓
    Tool Dispatcher → Handler Methods
           ↓
    Component Layer (ES, Campaign, etc.)
           ↓
    Response (JSON-RPC 2.0)

See :doc:`../developer-guide/architecture` for detailed architecture diagrams.

Data Layer Components
---------------------

ElasticsearchClient
~~~~~~~~~~~~~~~~~~~

Unified interface for all SIEM queries with optimization and resilience features.

**Key Features**:

* Multi-index pattern support (Cowrie, Zeek, DShield-specific)
* Smart query optimization for large result sets
* Pagination (offset-based and cursor-based)
* Circuit breaker integration
* Connection pooling and retry logic

**Supported Index Patterns**:

.. list-table::
   :widths: 30 70
   :header-rows: 1

   * - Data Source
     - Index Patterns
   * - Cowrie Honeypot
     - ``cowrie-*``, ``cowrie.dshield-*``, ``cowrie.vt_data-*``, ``cowrie.webhoneypot-*``
   * - Zeek Network Data
     - ``filebeat-zeek-*``, ``zeek.connection*``, ``zeek.dns*``, ``zeek.http*``, ``zeek.ssl*``

**Query Optimization**:

The client automatically detects large result sets and applies optimizations:

* Aggregation fallback for datasets > 10MB
* Sampling strategies for statistical analysis
* Field filtering to reduce payload size
* Smart pagination method selection

**API Reference**:

.. automodule:: elasticsearch_client
   :members:
   :undoc-members:
   :show-inheritance:
   :exclude-members: __dict__,__weakref__

DataProcessor
~~~~~~~~~~~~~

Normalizes and enriches security event data from multiple sources.

**Responsibilities**:

* Data normalization across index patterns
* Field mapping and standardization
* Timestamp parsing and timezone handling
* Missing field handling
* Data validation

**API Reference**:

.. automodule:: data_processor
   :members:
   :undoc-members:
   :show-inheritance:

DataDictionary
~~~~~~~~~~~~~~

Provides comprehensive field definitions and metadata for all SIEM data sources.

**Features**:

* Field name and path definitions
* Data type information
* Field descriptions and examples
* Index pattern associations
* Query helper methods

**API Reference**:

.. automodule:: data_dictionary
   :members:
   :undoc-members:
   :show-inheritance:

Analysis Layer Components
-------------------------

CampaignAnalyzer
~~~~~~~~~~~~~~~~

Advanced threat campaign correlation engine with 7 correlation methods.

**Correlation Methods**:

1. **IP Correlation**: Groups events by source IP addresses
2. **Behavioral Patterns**: Identifies similar attack behaviors and techniques
3. **Temporal Relationships**: Detects time-based patterns and sequences
4. **Target Patterns**: Groups attacks by targeted systems
5. **Session Correlation**: Tracks persistent connections and sessions
6. **Credential Patterns**: Correlates credential usage patterns
7. **Geographic Patterns**: Identifies geographic attack relationships

**Confidence Scoring Algorithm**:

.. code-block:: python

   confidence = (
       0.3 * ip_correlation_score +
       0.2 * behavioral_score +
       0.15 * temporal_score +
       0.15 * target_score +
       0.1 * session_score +
       0.05 * credential_score +
       0.05 * geographic_score
   )

**Confidence Levels**:

* **Low (0.0-0.3)**: Weak correlation, events may be unrelated
* **Medium (0.3-0.6)**: Moderate correlation, events likely related
* **High (0.6-0.8)**: Strong correlation, campaign likely coordinated
* **Critical (0.8-1.0)**: Very strong correlation, highly sophisticated campaign

**API Reference**:

.. automodule:: campaign_analyzer
   :members:
   :undoc-members:
   :show-inheritance:

ThreatIntelligenceManager
~~~~~~~~~~~~~~~~~~~~~~~~~

Multi-source threat intelligence aggregation and enrichment.

**Features**:

* DShield API integration
* IP reputation lookup
* Attack data correlation
* Geographic threat mapping
* Threat trend analysis

**API Reference**:

.. automodule:: threat_intelligence_manager
   :members:
   :undoc-members:
   :show-inheritance:

StatisticalAnalysisTools
~~~~~~~~~~~~~~~~~~~~~~~~

Statistical anomaly detection using Z-score and other methods.

**Detection Methods**:

* **Z-score Analysis**: Identifies numerical outliers (default threshold: 3.0)
* **Frequency Analysis**: Detects unusual categorical patterns
* **Time-Series Analysis**: Identifies temporal anomalies
* **Baseline Comparison**: Compares current to historical baselines

**API Reference**:

.. automodule:: statistical_analysis_tools
   :members:
   :undoc-members:
   :show-inheritance:

Error Handling & Resilience
----------------------------

MCPErrorHandler
~~~~~~~~~~~~~~~

JSON-RPC 2.0 compliant error handling with circuit breaker pattern.

**Features**:

* **Circuit Breaker**: Prevents cascading failures

  - States: CLOSED (normal), OPEN (failing), HALF_OPEN (testing recovery)
  - Configurable failure threshold and timeout
  - Automatic recovery testing

* **Error Response Generation**: Proper JSON-RPC 2.0 error codes
* **Error Aggregation**: Tracks error patterns
* **Rate Limiting**: Prevents error storms
* **Retry Logic**: Exponential backoff for transient failures

**Circuit Breaker States**::

    CLOSED (Normal Operation)
         ↓ (failures exceed threshold)
    OPEN (Rejecting Requests)
         ↓ (after timeout period)
    HALF_OPEN (Testing Recovery)
         ↓ (success) or ↓ (failure)
    CLOSED          OPEN

**Error Code Mapping**:

.. list-table::
   :widths: 15 25 60
   :header-rows: 1

   * - Code
     - Error Type
     - Description
   * - -32600
     - Invalid Request
     - Malformed JSON-RPC request
   * - -32601
     - Method Not Found
     - Tool does not exist
   * - -32602
     - Invalid Params
     - Invalid parameters provided
   * - -32603
     - Internal Error
     - Server-side error
   * - -32000
     - Server Error
     - Application-specific error

**API Reference**:

.. automodule:: mcp_error_handler
   :members:
   :undoc-members:
   :show-inheritance:

Feature Management
------------------

FeatureManager
~~~~~~~~~~~~~~

Manages feature availability and graceful degradation.

**Responsibilities**:

* Track feature dependencies (Elasticsearch, DShield API, etc.)
* Health check orchestration
* Feature enablement/disablement
* Dependency mapping

**Graceful Degradation**:

When a dependency fails, the FeatureManager:

1. Marks dependent tools as unavailable
2. Removes tools from tool list responses
3. Returns clear error messages when tools are called
4. Continues serving available tools

**Example**: If Elasticsearch is down:

* Query tools: Disabled
* Campaign analysis: Disabled
* Health status: Still available
* Data dictionary: Still available (cached)

**API Reference**:

.. automodule:: feature_manager
   :members:
   :undoc-members:
   :show-inheritance:

HealthCheckManager
~~~~~~~~~~~~~~~~~~

Performs health checks on all system dependencies.

**Health Checks**:

* Elasticsearch connectivity and version
* DShield API availability
* Circuit breaker status
* Memory and resource usage

**API Reference**:

.. automodule:: health_check_manager
   :members:
   :undoc-members:
   :show-inheritance:

Security Components
-------------------

SecurityValidator
~~~~~~~~~~~~~~~~~

Validates and sanitizes all inputs for security.

**Validation Types**:

* JSON schema validation
* Input sanitization
* Parameter bounds checking
* Injection prevention

**API Reference**:

.. automodule:: security_validator
   :members:
   :undoc-members:
   :show-inheritance:

Secrets Management
~~~~~~~~~~~~~~~~~~

All secrets are resolved from 1Password CLI at runtime. No plain text secrets in configuration files.

**OnePasswordCLIManager**:

.. automodule:: secrets_manager.onepassword_cli_manager
   :members:
   :undoc-members:
   :show-inheritance:

**BaseSecretsManager**:

.. automodule:: secrets_manager.base_secrets_manager
   :members:
   :undoc-members:
   :show-inheritance:

Rate Limiting
~~~~~~~~~~~~~

.. automodule:: security.rate_limiter
   :members:
   :undoc-members:
   :show-inheritance:

Configuration Management
------------------------

ConfigLoader
~~~~~~~~~~~~

Hierarchical configuration loading with validation.

**Configuration Sources** (in order of precedence):

1. Environment variables
2. User configuration file (``user_config.yaml``)
3. Main configuration file (``mcp_config.yaml``)
4. Built-in defaults

**API Reference**:

.. automodule:: config_loader
   :members:
   :undoc-members:
   :show-inheritance:

UserConfig
~~~~~~~~~~

User-specific configuration management with validation.

**API Reference**:

.. automodule:: user_config
   :members:
   :undoc-members:
   :show-inheritance:

Additional Components
---------------------

ConnectionManager
~~~~~~~~~~~~~~~~~

Manages Elasticsearch connections with pooling and health monitoring.

.. automodule:: connection_manager
   :members:
   :undoc-members:
   :show-inheritance:

OperationTracker
~~~~~~~~~~~~~~~~

Tracks operation execution for observability.

.. automodule:: operation_tracker
   :members:
   :undoc-members:
   :show-inheritance:

ResourceManager
~~~~~~~~~~~~~~~

Manages MCP resources (data sources exposed to clients).

.. automodule:: resource_manager
   :members:
   :undoc-members:
   :show-inheritance:

See Also
--------

* :doc:`tools` - MCP Tools documentation
* :doc:`../developer-guide/architecture` - Detailed architecture
* :doc:`../developer-guide/testing` - Testing guide
* :doc:`../user-guide/configuration` - Configuration guide
