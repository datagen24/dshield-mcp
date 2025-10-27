MCP Tools Reference
===================

This section documents all available MCP tools that provide security analysis capabilities through the Model Context Protocol.

.. note::
   All tools are defined in the ``src/mcp_tools/tools/`` directory and follow the MCP specification.
   Tools are automatically registered and available through the DShield MCP server.

Overview
--------

DShield MCP provides 8+ specialized tools organized into the following categories:

* **Query Tools** - Retrieve and filter security event data
* **Campaign Analysis Tools** - Correlate and analyze threat campaigns
* **Statistical Analysis Tools** - Detect anomalies and patterns
* **Reporting Tools** - Generate comprehensive security reports
* **Utility Tools** - Access system health and data dictionary

Query Tools
-----------

query_dshield_events
~~~~~~~~~~~~~~~~~~~~

Query DShield events from Elasticsearch with advanced filtering, pagination, and optimization.

**Purpose**: Retrieve security events with flexible time ranges, filters, and field selection.

**Key Features**:

* Multiple time range options (hours, absolute, relative, window)
* Smart query optimization for large result sets
* Cursor-based and offset pagination
* Field selection to reduce payload size
* Configurable fallback strategies

**Parameters**:

.. list-table::
   :widths: 20 15 65
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - ``time_range_hours``
     - integer
     - Time range in hours (default: 24)
   * - ``time_range``
     - object
     - Exact time range with start/end timestamps
   * - ``relative_time``
     - string
     - Relative time (e.g., 'last_6_hours', 'last_7_days')
   * - ``indices``
     - array
     - Elasticsearch indices to query
   * - ``filters``
     - object
     - Additional query filters (field/value pairs)
   * - ``fields``
     - array
     - Specific fields to return
   * - ``page``
     - integer
     - Page number (default: 1)
   * - ``page_size``
     - integer
     - Results per page (default: 100, max: 1000)
   * - ``sort_by``
     - string
     - Sort field (default: '@timestamp')
   * - ``sort_order``
     - string
     - Sort order: 'asc' or 'desc'
   * - ``cursor``
     - string
     - Cursor token for pagination
   * - ``optimization``
     - string
     - Optimization mode: 'auto' or 'none'

**Usage Example**:

.. code-block:: python

   # Query last 24 hours with filters
   result = await query_dshield_events(
       time_range_hours=24,
       filters={"source_ip": "192.168.1.1"},
       fields=["@timestamp", "source_ip", "destination_port"],
       page_size=100
   )

**API Reference**:

.. automodule:: mcp_tools.tools.query_dshield_events
   :members:
   :undoc-members:
   :show-inheritance:

stream_dshield_events_with_session_context
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Stream large result sets with session context management for handling datasets too large for single responses.

**Purpose**: Handle large query results by streaming data in manageable chunks with session tracking.

**Key Features**:

* Automatic chunking for large datasets
* Session state management
* Context preservation across chunks
* Memory-efficient streaming
* Progress tracking

**Parameters**:

.. list-table::
   :widths: 20 15 65
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - ``session_id``
     - string
     - Session identifier for tracking
   * - ``chunk_size``
     - integer
     - Events per chunk (default: 100)
   * - ``time_range_hours``
     - integer
     - Time range in hours
   * - ``filters``
     - object
     - Query filters
   * - ``fields``
     - array
     - Fields to return

**Usage Example**:

.. code-block:: python

   # Stream large dataset
   result = await stream_dshield_events_with_session_context(
       session_id="analysis-001",
       chunk_size=100,
       time_range_hours=72,
       filters={"severity": "high"}
   )

**API Reference**:

.. automodule:: mcp_tools.tools.stream_dshield_events_with_session_context
   :members:
   :undoc-members:
   :show-inheritance:

Campaign Analysis Tools
-----------------------

analyze_campaign
~~~~~~~~~~~~~~~~

Analyze and correlate security events to identify coordinated attack campaigns.

**Purpose**: Detect multi-stage attacks by correlating events using 7 different correlation methods.

**Correlation Methods**:

1. **IP Correlation** - Group events by source IP
2. **Behavioral Patterns** - Identify similar attack behaviors
3. **Temporal Relationships** - Detect time-based patterns
4. **Target Patterns** - Group by attacked targets
5. **Session Correlation** - Track session relationships
6. **Credential Patterns** - Correlate credential usage
7. **Geographic Patterns** - Identify geographic relationships

**Confidence Scoring**:

* **Low (0.0-0.3)** - Weak correlation, possible coincidence
* **Medium (0.3-0.6)** - Moderate correlation, likely related
* **High (0.6-0.8)** - Strong correlation, probably coordinated
* **Critical (0.8-1.0)** - Very strong correlation, highly coordinated

**Parameters**:

.. list-table::
   :widths: 20 15 65
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - ``seed_event``
     - object
     - Initial event to start campaign analysis
   * - ``time_range_hours``
     - integer
     - Time window for correlation
   * - ``correlation_methods``
     - array
     - Methods to use (default: all 7)
   * - ``min_confidence``
     - float
     - Minimum confidence threshold (0.0-1.0)
   * - ``max_events``
     - integer
     - Maximum events to analyze

**Usage Example**:

.. code-block:: python

   # Analyze campaign from seed event
   campaign = await analyze_campaign(
       seed_event={"source_ip": "10.0.0.1", "@timestamp": "2025-01-01T00:00:00Z"},
       time_range_hours=48,
       min_confidence=0.6
   )

**API Reference**:

.. automodule:: mcp_tools.tools.analyze_campaign
   :members:
   :undoc-members:
   :show-inheritance:

expand_campaign_indicators
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Expand campaign analysis by finding additional indicators of compromise (IOCs).

**Purpose**: Discover related IOCs and expand understanding of attack scope.

**API Reference**:

.. automodule:: mcp_tools.tools.expand_campaign_indicators
   :members:
   :undoc-members:
   :show-inheritance:

get_campaign_timeline
~~~~~~~~~~~~~~~~~~~~~

Generate a chronological timeline of campaign events.

**Purpose**: Visualize attack progression and identify attack stages.

**API Reference**:

.. automodule:: mcp_tools.tools.get_campaign_timeline
   :members:
   :undoc-members:
   :show-inheritance:

Statistical Analysis Tools
--------------------------

detect_statistical_anomalies
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Detect statistical anomalies in security data using Z-score analysis.

**Purpose**: Identify unusual patterns that may indicate security threats.

**Detection Methods**:

* Z-score analysis for numerical fields
* Frequency analysis for categorical data
* Time-series anomaly detection
* Baseline comparison

**Parameters**:

.. list-table::
   :widths: 20 15 65
   :header-rows: 1

   * - Parameter
     - Type
     - Description
   * - ``field``
     - string
     - Field to analyze
   * - ``threshold``
     - float
     - Z-score threshold (default: 3.0)
   * - ``time_range_hours``
     - integer
     - Analysis time window
   * - ``baseline_hours``
     - integer
     - Baseline calculation window

**Usage Example**:

.. code-block:: python

   # Detect port scanning anomalies
   anomalies = await detect_statistical_anomalies(
       field="destination_port",
       threshold=3.0,
       time_range_hours=24
   )

**API Reference**:

.. automodule:: mcp_tools.tools.detect_statistical_anomalies
   :members:
   :undoc-members:
   :show-inheritance:

Reporting Tools
---------------

generate_attack_report
~~~~~~~~~~~~~~~~~~~~~~

Generate comprehensive LaTeX-formatted attack reports with visualizations.

**Purpose**: Create professional security reports for stakeholders.

**Report Sections**:

* Executive summary
* Attack timeline
* IOC list
* Affected systems
* Recommendations

**Requirements**:

* LaTeX distribution installed (MacTeX, MiKTeX, or TeX Live)
* Templates in ``templates/`` directory
* Output directory configured

**API Reference**:

.. automodule:: mcp_tools.tools.generate_attack_report
   :members:
   :undoc-members:
   :show-inheritance:

Utility Tools
-------------

get_data_dictionary
~~~~~~~~~~~~~~~~~~~

Retrieve comprehensive data dictionary for all SIEM fields.

**Purpose**: Understand available fields, data types, and descriptions.

**Returns**: Complete field mapping including:

* Field names and paths
* Data types
* Descriptions
* Example values
* Index patterns

**API Reference**:

.. automodule:: mcp_tools.tools.get_data_dictionary
   :members:
   :undoc-members:
   :show-inheritance:

get_health_status
~~~~~~~~~~~~~~~~~

Check system health and feature availability.

**Purpose**: Monitor MCP server health and dependency status.

**Health Checks**:

* Elasticsearch connectivity
* DShield API availability
* Feature dependencies
* Circuit breaker status

**API Reference**:

.. automodule:: mcp_tools.tools.get_health_status
   :members:
   :undoc-members:
   :show-inheritance:

Tool System Architecture
------------------------

Base Classes
~~~~~~~~~~~~

.. automodule:: mcp_tools.tools.base
   :members:
   :undoc-members:
   :show-inheritance:

Tool Dispatcher
~~~~~~~~~~~~~~~

The dispatcher routes tool calls to handlers with timeout management.

.. automodule:: mcp_tools.tools.dispatcher
   :members:
   :undoc-members:
   :show-inheritance:

Tool Loader
~~~~~~~~~~~

The loader dynamically registers tools at server startup.

.. automodule:: mcp_tools.tools.loader
   :members:
   :undoc-members:
   :show-inheritance:

See Also
--------

* :doc:`../user-guide/usage` - Detailed usage examples
* :doc:`../developer-guide/architecture` - System architecture
* :doc:`clients` - Client components
* :doc:`analyzers` - Analysis components
