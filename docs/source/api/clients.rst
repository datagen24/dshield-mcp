Client Reference
================

This section describes the data client modules used by DShield MCP.

Data Clients
------------

Elasticsearch Client
~~~~~~~~~~~~~~~~~~~~

**Location**: ``src/elasticsearch_client.py`` (1200+ lines)

The Elasticsearch client provides a unified interface for all SIEM queries:

* **Multi-Index Support**: Cowrie honeypot, Zeek network data, DShield indices
* **Query Optimization**: Auto-detects large result sets and uses aggregation
* **Pagination**: Both offset-based and cursor-based pagination
* **Circuit Breaker**: Integrated circuit breaker for resilience
* **Smart Queries**: Automatic query optimization based on result set size

Key Classes:

* ``ElasticsearchClient``: Main client class
* ``PaginationMethod``: Enum for pagination strategies

DShield Client
~~~~~~~~~~~~~~

**Location**: ``src/dshield_client.py`` (350+ lines)

The DShield API client integrates with DShield's threat intelligence platform:

* **IP Reputation**: Query IP address reputation and attack history
* **Attack Data**: Retrieve attack data and statistics
* **Caching**: TTL-based caching of API responses
* **Rate Limiting**: Respects API rate limits
* **Error Handling**: Comprehensive error handling and retry logic

Key Classes:

* ``DShieldClient``: Main API client
* Response models for structured data

Data Processing
---------------

Data Processor
~~~~~~~~~~~~~~

**Location**: ``src/data_processor.py`` (1000+ lines)

The data processor normalizes and enriches SIEM data:

* **Normalization**: Convert different SIEM formats to common schema
* **Enrichment**: Add threat intelligence and context
* **Validation**: Validate data integrity and format
* **Security Summaries**: Generate security summaries from events

Data Dictionary
~~~~~~~~~~~~~~~

**Location**: ``src/data_dictionary.py`` (500+ lines)

The data dictionary manages field definitions and schemas:

* **Schema Management**: Define and validate field schemas
* **Field Mapping**: Map between different index formats
* **Documentation**: Provide field descriptions and examples
* **Validation**: Validate field values against schemas
