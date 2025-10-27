Analyzer Reference
==================

This section describes the intelligence analysis modules.

Campaign Analyzer
-----------------

**Location**: ``src/campaign_analyzer.py`` (1000+ lines)

The campaign analyzer provides advanced threat campaign correlation:

* **7 Correlation Methods**: IP, behavioral, temporal, geographic, protocol, command, and hybrid correlation
* **Confidence Scoring**: Low, Medium, High, Critical confidence levels
* **Event Grouping**: Group related events into campaigns
* **Indicator Tracking**: Track and expand indicators of compromise (IOCs)
* **Relationship Mapping**: Map relationships between events and indicators

Key Classes:

* ``CampaignAnalyzer``: Main analysis engine
* ``Campaign``: Campaign data model
* ``CorrelationMethod``: Enum for correlation strategies

Campaign MCP Tools
------------------

**Location**: ``src/campaign_mcp_tools.py`` (800+ lines)

High-level MCP tools that wrap the campaign analyzer:

* ``analyze_campaign``: Analyze events and identify campaigns
* ``expand_campaign_indicators``: Expand and enrich campaign indicators
* ``get_campaign_timeline``: Generate campaign timeline visualization

Threat Intelligence Manager
----------------------------

**Location**: ``src/threat_intelligence_manager.py`` (1600+ lines)

Multi-source threat intelligence aggregation and management:

* **Multi-Source Aggregation**: Combine data from DShield, ElasticSearch, and other sources
* **Enrichment**: Enrich events with threat intelligence context
* **Reputation Scoring**: Calculate and track IP reputation scores
* **Data Availability**: Diagnose data availability across sources
* **Caching**: Intelligent caching of threat intelligence data

Key Classes:

* ``ThreatIntelligenceManager``: Main intelligence aggregator
* ``ThreatIndicator``: Threat indicator data model

Statistical Analysis
--------------------

**Location**: ``src/statistical_analysis_tools.py`` (1000+ lines)

Statistical anomaly detection using Z-score analysis:

* **Z-Score Calculation**: Identify statistical outliers in event data
* **Multi-Field Analysis**: Analyze multiple fields simultaneously
* **Time-Based Analysis**: Detect temporal anomalies
* **Configurable Thresholds**: Adjustable sensitivity levels
* **Visualization Support**: Generate analysis reports

Key Functions:

* ``detect_statistical_anomalies``: Main anomaly detection function
* Z-score calculation and threshold evaluation
* Report generation and visualization
