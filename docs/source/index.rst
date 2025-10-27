DShield MCP Documentation
==========================

Welcome to the DShield MCP (Model Context Protocol) Server documentation. This project integrates DShield threat intelligence and Elasticsearch SIEM capabilities, enabling AI assistants to perform intelligent security analysis.

.. image:: https://img.shields.io/badge/python-3.10%2B-blue
   :alt: Python Version

.. image:: https://img.shields.io/badge/license-MIT-green
   :alt: License

Overview
--------

DShield MCP is a sophisticated SIEM analysis platform that leverages the Model Context Protocol to provide AI assistants with security intelligence capabilities. The architecture emphasizes:

* **Modularity**: Clean separation of concerns with well-defined component boundaries
* **Resilience**: Circuit breakers, graceful degradation, and comprehensive error handling
* **Security**: 1Password integration for secrets, no hardcoded credentials
* **Observability**: Structured logging with detailed operation tracking
* **Testability**: Dependency injection and comprehensive test coverage
* **Extensibility**: Easy to add new tools and data sources

Quick Start
-----------

Installation
~~~~~~~~~~~~

.. code-block:: bash

   # Install UV package manager
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Clone repository and install dependencies
   git clone https://github.com/datagen24/dshield-mcp.git
   cd dshield-mcp
   uv sync

   # Copy environment template
   cp .env.example .env

Running the Server
~~~~~~~~~~~~~~~~~~

.. code-block:: bash

   # Run MCP server (STDIO mode - default)
   uv run python mcp_server.py

   # Run TUI interface
   uv run python -m src.tui_launcher

   # Run TCP server
   uv run python -m src.server_launcher --transport tcp

Table of Contents
-----------------

.. toctree::
   :maxdepth: 2
   :caption: User Documentation

   user-guide/integration
   user-guide/usage
   user-guide/configuration
   user-guide/error-handling
   user-guide/output-directory

.. toctree::
   :maxdepth: 2
   :caption: Developer Documentation

   developer-guide/architecture
   developer-guide/testing
   developer-guide/contributing
   developer-guide/changelog

.. toctree::
   :maxdepth: 2
   :caption: Implementation Guides

   implementation/pagination
   implementation/streaming
   implementation/campaign-analysis
   implementation/statistical-analysis
   implementation/threat-intelligence

.. toctree::
   :maxdepth: 3
   :caption: API Reference

   api/modules
   api/tools
   api/clients
   api/analyzers
   api/utilities

.. toctree::
   :maxdepth: 1
   :caption: Additional Resources

   release-notes
   enhancements

Features
--------

MCP Tools
~~~~~~~~~

The server provides 8+ MCP tools for security analysis:

* **Query Tools**: ``query_dshield_events``, ``stream_dshield_events_with_session_context``
* **Campaign Tools**: ``analyze_campaign``, ``expand_campaign_indicators``, ``get_campaign_timeline``
* **Report Tools**: ``generate_attack_report``
* **Utility Tools**: ``get_data_dictionary``, ``get_health_status``
* **Analysis Tools**: ``detect_statistical_anomalies``

Campaign Analysis
~~~~~~~~~~~~~~~~~

Advanced threat campaign correlation with:

* 7 correlation methods (IP, behavioral, temporal, etc.)
* Confidence scoring (Low, Medium, High, Critical)
* Event grouping and indicator relationship tracking
* Multi-stage campaign detection

Data Sources
~~~~~~~~~~~~

Supports multiple SIEM data sources:

* **Cowrie Honeypot**: ``cowrie-*``, ``cowrie.dshield-*``
* **Zeek Network Data**: ``zeek.connection*``, ``zeek.dns*``, ``zeek.http*``
* **DShield API**: IP reputation, attack data, threat intelligence

Architecture
------------

High-Level Components
~~~~~~~~~~~~~~~~~~~~~

* **DShieldMCPServer**: Central orchestration point (Facade pattern)
* **Tool System**: Dispatcher with Strategy pattern for tool execution
* **ElasticsearchClient**: Unified SIEM query interface with circuit breaker
* **Campaign Analyzer**: Correlation engine with 7 correlation methods
* **Threat Intelligence**: Multi-source aggregation and enrichment
* **Error Handling**: JSON-RPC 2.0 compliant with circuit breaker
* **Feature Management**: Graceful degradation with health checks

Security & Configuration
~~~~~~~~~~~~~~~~~~~~~~~~

* **1Password Integration**: All secrets resolved from 1Password CLI at runtime
* **Configuration Hierarchy**: YAML config → User config → Environment variables
* **No Plain Text Secrets**: Uses ``op://vault/item/field`` references
* **Rate Limiting**: Protects against API abuse
* **Input Validation**: JSON schema validation for all tool inputs

Testing
-------

.. code-block:: bash

   # Run all tests
   uv run pytest

   # Run tests with coverage
   uv run pytest --cov=src --cov-report=html

   # Run by marker
   uv run pytest -m unit          # Unit tests only
   uv run pytest -m integration   # Integration tests only

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
