API Reference
=============

This section contains the API reference for DShield MCP modules.

.. note::
   The DShield MCP codebase uses relative imports extensively. For detailed API documentation,
   please refer to the source code docstrings or use the pdoc-generated HTML documentation
   in ``docs/api/``.

Core Architecture
-----------------

The DShield MCP server follows a modular architecture with the following key components:

**MCP Server**
   Main entry point and orchestration (``mcp_server.py``)

**Tool System**
   Dynamic tool registration and execution (``src/mcp_tools/tools/``)

**Data Layer**
   * Elasticsearch client for SIEM data
   * DShield API client for threat intelligence
   * Data processing and normalization

**Intelligence Layer**
   * Campaign analysis and correlation
   * Threat intelligence aggregation
   * Statistical anomaly detection

**Error Handling & Security**
   * JSON-RPC 2.0 compliant error handling
   * Circuit breaker implementation
   * Rate limiting and input validation

Module Overview
---------------

For detailed module documentation, see the following sections:

* :doc:`tools` - MCP Tools Reference
* :doc:`core-components` - Core Components Reference
* :doc:`clients` - Data Client Reference
* :doc:`analyzers` - Intelligence Analyzer Reference
* :doc:`utilities` - Utility Module Reference
