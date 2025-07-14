<a id="campaign_analyzer"></a>

# campaign\_analyzer

Campaign Analysis Engine for DShield MCP.

Core campaign correlation and analysis engine for identifying coordinated attack campaigns.

<a id="campaign_analyzer.CorrelationMethod"></a>

## CorrelationMethod Objects

```python
class CorrelationMethod(Enum)
```

Correlation methods for campaign analysis.

<a id="campaign_analyzer.CampaignConfidence"></a>

## CampaignConfidence Objects

```python
class CampaignConfidence(Enum)
```

Campaign confidence levels.

<a id="campaign_analyzer.CampaignEvent"></a>

## CampaignEvent Objects

```python
@dataclass
class CampaignEvent()
```

Individual event within a campaign.

<a id="campaign_analyzer.IndicatorRelationship"></a>

## IndicatorRelationship Objects

```python
@dataclass
class IndicatorRelationship()
```

Relationship between indicators in a campaign.

<a id="campaign_analyzer.Campaign"></a>

## Campaign Objects

```python
@dataclass
class Campaign()
```

Campaign data model.

<a id="campaign_analyzer.CampaignAnalyzer"></a>

## CampaignAnalyzer Objects

```python
class CampaignAnalyzer()
```

Core campaign analysis and correlation engine.

Provides methods for correlating security events, expanding indicators,
and building campaign timelines for coordinated attack detection.

<a id="campaign_analyzer.CampaignAnalyzer.__init__"></a>

#### \_\_init\_\_

```python
def __init__(es_client: Optional[ElasticsearchClient] = None) -> None
```

Initialize the CampaignAnalyzer.

**Arguments**:

- `es_client` - Optional ElasticsearchClient instance. If not provided, a new one is created.

<a id="campaign_analyzer.CampaignAnalyzer.correlate_events"></a>

#### correlate\_events

```python
async def correlate_events(seed_events: List[Dict[str, Any]],
                           correlation_criteria: List[CorrelationMethod],
                           time_window_hours: int = 48,
                           min_confidence: float = 0.7) -> Campaign
```

Correlate events based on specified criteria to identify campaigns.

**Arguments**:

- `seed_events` - List of seed event dictionaries to start correlation from.
- `correlation_criteria` - List of CorrelationMethod enums to use for correlation.
- `time_window_hours` - Time window in hours to consider for correlation (default: 48).
- `min_confidence` - Minimum confidence threshold for campaign inclusion (default: 0.7).
  

**Returns**:

- `Campaign` - The resulting Campaign object with correlated events and metadata.
  

**Raises**:

- `Exception` - If campaign correlation fails.

<a id="campaign_analyzer.CampaignAnalyzer.expand_indicators"></a>

#### expand\_indicators

```python
async def expand_indicators(seed_iocs: List[str],
                            expansion_strategy: str = "comprehensive",
                            max_depth: int = 3) -> List[IndicatorRelationship]
```

Expand IOCs to find related indicators.

**Arguments**:

- `seed_iocs` - List of seed indicators (IOCs) to expand.
- `expansion_strategy` - Strategy for expansion ('comprehensive', 'infrastructure', etc.).
- `max_depth` - Maximum expansion depth (default: 3).
  

**Returns**:

  List of IndicatorRelationship objects representing discovered relationships.

<a id="campaign_analyzer.CampaignAnalyzer.build_campaign_timeline"></a>

#### build\_campaign\_timeline

```python
async def build_campaign_timeline(
        correlated_events: List[CampaignEvent],
        timeline_granularity: str = "hourly") -> Dict[str, Any]
```

Build chronological timeline of campaign events.

**Arguments**:

- `correlated_events` - List of CampaignEvent objects to build timeline from.
- `timeline_granularity` - Granularity of timeline ('hourly', 'daily', 'minute').
  

**Returns**:

  Dictionary containing timeline data with events grouped by time periods.

<a id="campaign_analyzer.CampaignAnalyzer.score_campaign"></a>

#### score\_campaign

```python
async def score_campaign(campaign_data: Campaign) -> float
```

Score campaign based on sophistication and impact.

**Arguments**:

- `campaign_data` - Campaign object to score.
  

**Returns**:

  Float score between 0.0 and 1.0 representing campaign sophistication.

<a id="campaign_mcp_tools"></a>

# campaign\_mcp\_tools

Campaign Analysis MCP Tools.

MCP tools for campaign analysis and correlation.

<a id="campaign_mcp_tools.CampaignMCPTools"></a>

## CampaignMCPTools Objects

```python
class CampaignMCPTools()
```

MCP tools for campaign analysis and correlation.

<a id="campaign_mcp_tools.CampaignMCPTools.__init__"></a>

#### \_\_init\_\_

```python
def __init__(es_client: Optional[ElasticsearchClient] = None)
```

Initialize CampaignMCPTools.

**Arguments**:

- `es_client` - Optional ElasticsearchClient instance. If not provided, a new one is created.

<a id="campaign_mcp_tools.CampaignMCPTools.analyze_campaign"></a>

#### analyze\_campaign

```python
async def analyze_campaign(
        seed_indicators: List[str],
        time_range_hours: int = 168,
        correlation_methods: Optional[List[str]] = None,
        min_confidence: float = 0.7,
        include_timeline: bool = True,
        include_relationships: bool = True) -> Dict[str, Any]
```

Analyze attack campaigns from seed indicators.

**Arguments**:

- `seed_indicators` - List of seed indicators (IPs, domains, etc.)
- `time_range_hours` - Time range to analyze (default: 168 hours = 1 week)
- `correlation_methods` - List of correlation methods to use
- `min_confidence` - Minimum confidence threshold for campaign inclusion
- `include_timeline` - Whether to include detailed timeline
- `include_relationships` - Whether to include indicator relationships
  

**Returns**:

  Campaign analysis results with metadata

<a id="campaign_mcp_tools.CampaignMCPTools.expand_campaign_indicators"></a>

#### expand\_campaign\_indicators

```python
async def expand_campaign_indicators(
        campaign_id: str,
        expansion_depth: int = 3,
        expansion_strategy: str = "comprehensive",
        include_passive_dns: bool = True,
        include_threat_intel: bool = True) -> Dict[str, Any]
```

Expand IOCs to find related indicators.

**Arguments**:

- `campaign_id` - Campaign ID to expand
- `expansion_depth` - Maximum expansion depth
- `expansion_strategy` - Expansion strategy (comprehensive, infrastructure, temporal)
- `include_passive_dns` - Whether to include passive DNS data
- `include_threat_intel` - Whether to include threat intelligence data
  

**Returns**:

  Expanded indicators and relationships

<a id="campaign_mcp_tools.CampaignMCPTools.get_campaign_timeline"></a>

#### get\_campaign\_timeline

```python
async def get_campaign_timeline(
        campaign_id: str,
        timeline_granularity: str = "hourly",
        include_event_details: bool = True,
        include_ttp_analysis: bool = True) -> Dict[str, Any]
```

Build detailed attack timelines.

**Arguments**:

- `campaign_id` - Campaign ID to analyze
- `timeline_granularity` - Timeline granularity (minute, hourly, daily)
- `include_event_details` - Whether to include detailed event information
- `include_ttp_analysis` - Whether to include TTP analysis
  

**Returns**:

  Detailed campaign timeline

<a id="campaign_mcp_tools.CampaignMCPTools.compare_campaigns"></a>

#### compare\_campaigns

```python
async def compare_campaigns(
        campaign_ids: List[str],
        comparison_metrics: Optional[List[str]] = None,
        include_visualization_data: bool = True) -> Dict[str, Any]
```

Compare multiple campaigns for similarities.

**Arguments**:

- `campaign_ids` - List of campaign IDs to compare
- `comparison_metrics` - Metrics to compare (ttps, infrastructure, timing, etc.)
- `include_visualization_data` - Whether to include visualization data
  

**Returns**:

  Campaign comparison results

<a id="campaign_mcp_tools.CampaignMCPTools.detect_ongoing_campaigns"></a>

#### detect\_ongoing\_campaigns

```python
async def detect_ongoing_campaigns(
        time_window_hours: int = 24,
        min_event_threshold: int = 15,
        correlation_threshold: float = 0.8,
        include_alert_data: bool = True) -> Dict[str, Any]
```

Real-time detection of active campaigns.

**Arguments**:

- `time_window_hours` - Time window for detection (default: 24 hours)
- `min_event_threshold` - Minimum events for campaign detection
- `correlation_threshold` - Minimum correlation threshold
- `include_alert_data` - Whether to include alert data
  

**Returns**:

  Detected ongoing campaigns

<a id="campaign_mcp_tools.CampaignMCPTools.search_campaigns"></a>

#### search\_campaigns

```python
async def search_campaigns(search_criteria: Dict[str, Any],
                           time_range_hours: int = 168,
                           max_results: int = 50,
                           include_summaries: bool = True) -> Dict[str, Any]
```

Search existing campaigns by criteria.

**Arguments**:

- `search_criteria` - Search criteria (indicators, time_range, confidence, etc.)
- `time_range_hours` - Time range for search
- `max_results` - Maximum results to return
- `include_summaries` - Whether to include campaign summaries
  

**Returns**:

  Matching campaigns

<a id="campaign_mcp_tools.CampaignMCPTools.get_campaign_details"></a>

#### get\_campaign\_details

```python
async def get_campaign_details(
        campaign_id: str,
        include_full_timeline: bool = False,
        include_relationships: bool = True,
        include_threat_intel: bool = True) -> Dict[str, Any]
```

Comprehensive campaign information.

**Arguments**:

- `campaign_id` - Campaign ID to retrieve
- `include_full_timeline` - Whether to include full timeline
- `include_relationships` - Whether to include indicator relationships
- `include_threat_intel` - Whether to include threat intelligence
  

**Returns**:

  Comprehensive campaign details

<a id="config_loader"></a>

# config\_loader

Configuration loader for DShield MCP server.

This module provides utilities for loading and resolving configuration
from YAML files with support for 1Password CLI secret resolution.
It handles config file validation, secret resolution, and error handling.

Features:
- YAML configuration file loading
- 1Password CLI secret resolution
- Configuration validation
- Error handling with custom exceptions

**Example**:

  >>> from src.config_loader import get_config
  >>> config = get_config()
  >>> print(config['elasticsearch']['url'])

<a id="config_loader.ConfigError"></a>

## ConfigError Objects

```python
class ConfigError(Exception)
```

Exception raised for configuration-related errors.

This exception is raised when there are issues with loading,
parsing, or validating configuration files.

<a id="config_loader.get_config"></a>

#### get\_config

```python
def get_config(config_path: str = None) -> Dict[str, Any]
```

Load the MCP YAML config file.

Loads and validates a YAML configuration file, resolving any
1Password CLI secrets in the process. By default, looks for
'mcp_config.yaml' in the project root.

**Arguments**:

- `config_path` - Path to the configuration file (default: auto-detected)
  

**Returns**:

  Dictionary containing the resolved configuration
  

**Raises**:

- `ConfigError` - If config file is missing, invalid, or cannot be loaded

<a id="context_injector"></a>

# context\_injector

Context injector for preparing data for ChatGPT context injection.

This module provides utilities for preparing and formatting security data
for injection into ChatGPT conversations. It handles various data types
including security events, threat intelligence, attack reports, and query
results, formatting them appropriately for AI consumption.

Features:
- Security context preparation and formatting
- Attack report context injection
- Query result formatting
- MCP-compatible context injection
- Multiple output formats (structured, summary, raw)
- ChatGPT-optimized formatting

**Example**:

  >>> from src.context_injector import ContextInjector
  >>> injector = ContextInjector()
  >>> context = injector.prepare_security_context(events, threat_intel)
  >>> formatted = injector.inject_context_for_chatgpt(context)

<a id="context_injector.ContextInjector"></a>

## ContextInjector Objects

```python
class ContextInjector()
```

Prepare and inject security context for ChatGPT analysis.

This class provides methods to prepare and format various types of
security data for injection into ChatGPT conversations. It supports
multiple output formats and optimizes data for AI consumption.

**Attributes**:

- `max_context_size` - Maximum context size in characters
- `include_raw_data` - Whether to include raw data in context
- `context_format` - Output format (structured, summary, or raw)
  

**Example**:

  >>> injector = ContextInjector()
  >>> context = injector.prepare_security_context(events)
  >>> formatted = injector.inject_context_for_chatgpt(context)

<a id="context_injector.ContextInjector.__init__"></a>

#### \_\_init\_\_

```python
def __init__() -> None
```

Initialize the ContextInjector.

Loads configuration from environment variables for context
formatting preferences and size limits.

<a id="context_injector.ContextInjector.prepare_security_context"></a>

#### prepare\_security\_context

```python
def prepare_security_context(
        events: List[Dict[str, Any]],
        threat_intelligence: Optional[Dict[str, Any]] = None,
        summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]
```

Prepare security context for injection.

Creates a comprehensive security context from events, threat
intelligence, and summary data, formatted according to the
configured context format preference.

**Arguments**:

- `events` - List of security event dictionaries
- `threat_intelligence` - Optional threat intelligence data
- `summary` - Optional summary data
  

**Returns**:

  Dictionary containing formatted security context

<a id="context_injector.ContextInjector.prepare_attack_report_context"></a>

#### prepare\_attack\_report\_context

```python
def prepare_attack_report_context(report: Dict[str, Any]) -> Dict[str, Any]
```

Prepare attack report context for injection.

Formats an attack report for injection into ChatGPT conversations,
including metadata and confidence information.

**Arguments**:

- `report` - Attack report dictionary
  

**Returns**:

  Dictionary containing formatted attack report context

<a id="context_injector.ContextInjector.prepare_query_context"></a>

#### prepare\_query\_context

```python
def prepare_query_context(query_type: str, parameters: Dict[str, Any],
                          results: List[Dict[str, Any]]) -> Dict[str, Any]
```

Prepare query context for injection.

Formats query results and parameters for injection into ChatGPT
conversations, including metadata about the query execution.

**Arguments**:

- `query_type` - Type of query that was executed
- `parameters` - Query parameters that were used
- `results` - Query results to format
  

**Returns**:

  Dictionary containing formatted query context

<a id="context_injector.ContextInjector.inject_context_for_chatgpt"></a>

#### inject\_context\_for\_chatgpt

```python
def inject_context_for_chatgpt(context: Dict[str, Any]) -> str
```

Format context for ChatGPT consumption.

Converts a context dictionary into a string format optimized
for ChatGPT consumption, handling different context types
appropriately.

**Arguments**:

- `context` - Context dictionary to format
  

**Returns**:

  String formatted for ChatGPT consumption

<a id="context_injector.ContextInjector.create_mcp_context_injection"></a>

#### create\_mcp\_context\_injection

```python
def create_mcp_context_injection(context: Dict[str, Any]) -> Dict[str, Any]
```

Create MCP-compatible context injection.

Formats context data for use with the Model Context Protocol (MCP),
including proper metadata and version information.

**Arguments**:

- `context` - Context dictionary to format
  

**Returns**:

  Dictionary formatted for MCP protocol

<a id="data_dictionary"></a>

# data\_dictionary

Data Dictionary for DShield MCP Elastic SIEM Integration.

This module provides comprehensive field descriptions, query examples, and
analysis guidelines to help AI models understand DShield SIEM data structures
and their meanings. It serves as a reference for data interpretation and
query construction.

Features:
- Comprehensive field descriptions and types
- Query examples for common use cases
- Data patterns and analysis guidelines
- Initial prompt generation for AI models
- Structured data reference for DShield SIEM

**Example**:

  >>> from src.data_dictionary import DataDictionary
  >>> fields = DataDictionary.get_field_descriptions()
  >>> examples = DataDictionary.get_query_examples()
  >>> prompt = DataDictionary.get_initial_prompt()

<a id="data_dictionary.DataDictionary"></a>

## DataDictionary Objects

```python
class DataDictionary()
```

Comprehensive data dictionary for DShield SIEM data.

This class provides static methods to access comprehensive information
about DShield SIEM data structures, including field descriptions,
query examples, data patterns, and analysis guidelines.

The class serves as a central reference for understanding DShield
data formats and constructing effective queries and analysis.

**Example**:

  >>> fields = DataDictionary.get_field_descriptions()
  >>> examples = DataDictionary.get_query_examples()
  >>> prompt = DataDictionary.get_initial_prompt()

<a id="data_dictionary.DataDictionary.get_field_descriptions"></a>

#### get\_field\_descriptions

```python
@staticmethod
def get_field_descriptions() -> Dict[str, Any]
```

Get comprehensive field descriptions for DShield data.

Returns a detailed dictionary containing descriptions, types,
examples, and usage information for all DShield SIEM fields.

**Returns**:

  Dictionary containing field descriptions organized by category:
  - core_fields: Basic event fields (timestamp, id)
  - network_fields: Network-related fields (IPs, ports, protocols)
  - event_fields: Event classification fields (type, severity, category)
  - dshield_specific_fields: DShield-specific threat intelligence
  - geographic_fields: Geographic location data
  - service_fields: Service and application data

<a id="data_dictionary.DataDictionary.get_query_examples"></a>

#### get\_query\_examples

```python
@staticmethod
def get_query_examples() -> Dict[str, Any]
```

Get example queries for common use cases.

Returns a collection of example queries demonstrating how to
use the DShield MCP tools for various security analysis scenarios.

**Returns**:

  Dictionary containing query examples with descriptions,
  parameters, and expected fields for each use case

<a id="data_dictionary.DataDictionary.get_data_patterns"></a>

#### get\_data\_patterns

```python
@staticmethod
def get_data_patterns() -> Dict[str, Any]
```

Get common data patterns and their interpretations.

Returns patterns that commonly appear in DShield data and
their security implications for analysis.

**Returns**:

  Dictionary containing data patterns with descriptions
  and security context

<a id="data_dictionary.DataDictionary.get_analysis_guidelines"></a>

#### get\_analysis\_guidelines

```python
@staticmethod
def get_analysis_guidelines() -> Dict[str, Any]
```

Get guidelines for analyzing DShield SIEM data.

Returns best practices and guidelines for interpreting
and analyzing DShield security data effectively.

**Returns**:

  Dictionary containing analysis guidelines and best practices

<a id="data_dictionary.DataDictionary.get_initial_prompt"></a>

#### get\_initial\_prompt

```python
@staticmethod
def get_initial_prompt() -> str
```

Get the initial prompt for AI models.

Generates a comprehensive initial prompt that provides AI models
with all the necessary context about DShield SIEM data structures,
field meanings, and analysis guidelines.

**Returns**:

  String containing the complete initial prompt for AI models

<a id="data_processor"></a>

# data\_processor

Data processor for formatting and structuring DShield SIEM data for AI consumption.

This module provides utilities for processing, normalizing, and structuring
DShield SIEM data for downstream AI analysis and reporting. It includes
functions for event normalization, attack pattern detection, enrichment,
summarization, and report generation.

Features:
- Security event normalization and enrichment
- Attack pattern detection
- DShield-specific data mapping
- Summary and report generation
- Utility methods for extracting and analyzing event data

**Example**:

  >>> from src.data_processor import DataProcessor
  >>> processor = DataProcessor()
  >>> processed = processor.process_security_events(events)
  >>> print(processed)

<a id="data_processor.DataProcessor"></a>

## DataProcessor Objects

```python
class DataProcessor()
```

Process and structure DShield SIEM data for AI analysis.

This class provides methods to normalize, enrich, and summarize DShield SIEM
data for use in AI-driven analytics and reporting. It includes attack pattern
detection, severity/category mapping, and report generation utilities.

**Attributes**:

- `dshield_attack_patterns` - Mapping of attack pattern names to keywords
- `dshield_severity_mapping` - Mapping of severity labels to EventSeverity
- `dshield_category_mapping` - Mapping of category labels to EventCategory
  

**Example**:

  >>> processor = DataProcessor()
  >>> summary = processor.generate_security_summary(events)

<a id="data_processor.DataProcessor.__init__"></a>

#### \_\_init\_\_

```python
def __init__() -> None
```

Initialize the DataProcessor.

Sets up DShield-specific mappings for attack patterns, severity, and category.

<a id="data_processor.DataProcessor.process_security_events"></a>

#### process\_security\_events

```python
def process_security_events(
        events: List[Dict[str, Any]]) -> List[Dict[str, Any]]
```

Process and normalize security events from DShield SIEM.

Normalizes, enriches, and detects attack patterns in a list of security events.
Handles error logging and skips events that cannot be processed.

**Arguments**:

- `events` - List of raw event dictionaries
  

**Returns**:

  List of processed and normalized event dictionaries

<a id="data_processor.DataProcessor.process_dshield_attacks"></a>

#### process\_dshield\_attacks

```python
def process_dshield_attacks(
        attacks: List[Dict[str, Any]]) -> List[DShieldAttack]
```

Process DShield attack events into structured format.

Converts raw attack event dictionaries into DShieldAttack model instances.
Handles error logging and skips attacks that cannot be processed.

**Arguments**:

- `attacks` - List of raw attack event dictionaries
  

**Returns**:

  List of DShieldAttack model instances

<a id="data_processor.DataProcessor.process_dshield_reputation"></a>

#### process\_dshield\_reputation

```python
def process_dshield_reputation(
        reputation_data: List[Dict[str, Any]]) -> Dict[str, DShieldReputation]
```

Process DShield reputation data into structured format.

Converts raw reputation data dictionaries into DShieldReputation model instances.
Handles error logging and skips entries that cannot be processed.

**Arguments**:

- `reputation_data` - List of raw reputation data dictionaries
  

**Returns**:

  Dictionary mapping IP addresses to DShieldReputation model instances

<a id="data_processor.DataProcessor.process_dshield_top_attackers"></a>

#### process\_dshield\_top\_attackers

```python
def process_dshield_top_attackers(
        attackers: List[Dict[str, Any]]) -> List[DShieldTopAttacker]
```

Process DShield top attackers data into structured format.

<a id="data_processor.DataProcessor.generate_dshield_summary"></a>

#### generate\_dshield\_summary

```python
def generate_dshield_summary(
        events: List[Dict[str, Any]]) -> DShieldStatistics
```

Generate DShield-specific security summary.

<a id="data_processor.DataProcessor.generate_security_summary"></a>

#### generate\_security\_summary

```python
def generate_security_summary(events: List[Dict[str, Any]]) -> Dict[str, Any]
```

Generate security summary statistics with DShield enrichment.

<a id="data_processor.DataProcessor.generate_attack_report"></a>

#### generate\_attack\_report

```python
def generate_attack_report(
        events: List[Dict[str, Any]],
        threat_intelligence: Optional[Dict[str,
                                           Any]] = None) -> Dict[str, Any]
```

Generate structured attack report with DShield data.

<a id="data_processor.DataProcessor.extract_unique_ips"></a>

#### extract\_unique\_ips

```python
def extract_unique_ips(events: List[Dict[str, Any]]) -> List[str]
```

Extract unique IP addresses from events.

<a id="dshield_client"></a>

# dshield\_client

DShield client for threat intelligence and IP reputation lookup.

This module provides a client for interacting with the DShield threat intelligence API.
It supports IP reputation lookups, attack summaries, batch enrichment, and detailed
IP information retrieval. The client handles authentication, rate limiting, caching,
and error handling for robust integration with DShield services.

Features:
- IP reputation and details lookup
- Attack summary retrieval
- Batch enrichment of IPs
- Caching and rate limiting
- Async context management

**Example**:

  >>> from src.dshield_client import DShieldClient
  >>> async with DShieldClient() as client:
  ...     rep = await client.get_ip_reputation("8.8.8.8")
  ...     print(rep)

<a id="dshield_client.DShieldClient"></a>

## DShieldClient Objects

```python
class DShieldClient()
```

Client for interacting with DShield threat intelligence API.

This class provides methods to query DShield for IP reputation, details,
attack summaries, and batch enrichment. It manages authentication, rate
limiting, caching, and session lifecycle for efficient API usage.

**Attributes**:

- `api_key` - API key for DShield authentication
- `base_url` - Base URL for DShield API
- `session` - aiohttp.ClientSession for HTTP requests
- `rate_limit_requests` - Max requests per minute
- `rate_limit_window` - Time window for rate limiting (seconds)
- `request_times` - List of request timestamps for rate limiting
- `cache` - In-memory cache for API responses
- `cache_ttl` - Time-to-live for cache entries (seconds)
- `enable_caching` - Whether caching is enabled
- `max_cache_size` - Maximum cache size
- `request_timeout` - Timeout for API requests (seconds)
- `enable_performance_logging` - Whether to log performance metrics
- `headers` - HTTP headers for API requests
- `batch_size` - Maximum batch size for IP enrichment
  

**Example**:

  >>> async with DShieldClient() as client:
  ...     rep = await client.get_ip_reputation("8.8.8.8")
  ...     print(rep)

<a id="dshield_client.DShieldClient.__init__"></a>

#### \_\_init\_\_

```python
def __init__() -> None
```

Initialize the DShield client.

Loads configuration, resolves secrets, sets up rate limiting,
caching, and prepares HTTP headers for API requests.

**Raises**:

- `RuntimeError` - If configuration or secret resolution fails

<a id="dshield_client.DShieldClient.__aenter__"></a>

#### \_\_aenter\_\_

```python
async def __aenter__() -> "DShieldClient"
```

Async context manager entry.

**Returns**:

- `DShieldClient` - The initialized client instance

<a id="dshield_client.DShieldClient.__aexit__"></a>

#### \_\_aexit\_\_

```python
async def __aexit__(exc_type, exc_val, exc_tb) -> None
```

Async context manager exit.

Closes the HTTP session on exit.

<a id="dshield_client.DShieldClient.connect"></a>

#### connect

```python
async def connect() -> None
```

Initialize HTTP session.

Creates an aiohttp.ClientSession for making API requests.
Logs session initialization.

<a id="dshield_client.DShieldClient.close"></a>

#### close

```python
async def close() -> None
```

Close HTTP session.

Closes the aiohttp.ClientSession and releases resources.
Logs session closure.

<a id="dshield_client.DShieldClient.get_ip_reputation"></a>

#### get\_ip\_reputation

```python
async def get_ip_reputation(ip_address: str) -> Dict[str, Any]
```

Get IP reputation from DShield.

Looks up the reputation of a given IP address using the DShield API.
Utilizes caching and rate limiting for efficiency.

**Arguments**:

- `ip_address` - The IP address to look up
  

**Returns**:

  Dictionary containing reputation data for the IP

<a id="dshield_client.DShieldClient.get_ip_details"></a>

#### get\_ip\_details

```python
async def get_ip_details(ip_address: str) -> Dict[str, Any]
```

Get detailed IP information from DShield.

Retrieves detailed information for a given IP address from the DShield API.
Utilizes caching and rate limiting for efficiency.

**Arguments**:

- `ip_address` - The IP address to look up
  

**Returns**:

  Dictionary containing detailed data for the IP

<a id="dshield_client.DShieldClient.get_top_attackers"></a>

#### get\_top\_attackers

```python
async def get_top_attackers(hours: int = 24) -> List[Dict[str, Any]]
```

Get top attackers from DShield.

<a id="dshield_client.DShieldClient.get_attack_summary"></a>

#### get\_attack\_summary

```python
async def get_attack_summary(hours: int = 24) -> Dict[str, Any]
```

Get attack summary from DShield.

<a id="dshield_client.DShieldClient.enrich_ips_batch"></a>

#### enrich\_ips\_batch

```python
async def enrich_ips_batch(
        ip_addresses: List[str]) -> Dict[str, Dict[str, Any]]
```

Enrich multiple IP addresses with threat intelligence.

<a id="elasticsearch_client"></a>

# elasticsearch\_client

Elasticsearch client for querying DShield SIEM events and logs.

Optimized for DShield SIEM integration patterns.

<a id="elasticsearch_client.ElasticsearchClient"></a>

## ElasticsearchClient Objects

```python
class ElasticsearchClient()
```

Client for interacting with DShield SIEM Elasticsearch.

<a id="elasticsearch_client.ElasticsearchClient.__init__"></a>

#### \_\_init\_\_

```python
def __init__()
```

Initialize the Elasticsearch client.

Sets up the client connection, field mappings, and configuration
for DShield SIEM integration.

<a id="elasticsearch_client.ElasticsearchClient.connect"></a>

#### connect

```python
async def connect()
```

Connect to Elasticsearch cluster.

<a id="elasticsearch_client.ElasticsearchClient.close"></a>

#### close

```python
async def close()
```

Close Elasticsearch connection.

<a id="elasticsearch_client.ElasticsearchClient.get_available_indices"></a>

#### get\_available\_indices

```python
async def get_available_indices() -> List[str]
```

Get available DShield indices.

<a id="elasticsearch_client.ElasticsearchClient.query_dshield_events"></a>

#### query\_dshield\_events

```python
async def query_dshield_events(
    time_range_hours: int = 24,
    indices: Optional[List[str]] = None,
    filters: Optional[Dict[str, Any]] = None,
    fields: Optional[List[str]] = None,
    page: int = 1,
    page_size: int = 100,
    sort_by: str = "@timestamp",
    sort_order: str = "desc",
    cursor: Optional[str] = None,
    include_summary: bool = True,
    optimization: str = "auto",
    fallback_strategy: str = "aggregate",
    max_result_size_mb: float = 10.0,
    query_timeout_seconds: int = 30
) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]
```

Query DShield events from Elasticsearch with enhanced pagination support.

Supports both traditional page-based pagination and cursor-based pagination
for better performance with massive datasets.

<a id="elasticsearch_client.ElasticsearchClient.execute_aggregation_query"></a>

#### execute\_aggregation\_query

```python
async def execute_aggregation_query(
        index: List[str], query: Dict[str, Any],
        aggregation_query: Dict[str, Any]) -> Dict[str, Any]
```

Execute an aggregation query on Elasticsearch.

Performs aggregation queries for statistical analysis and
data summarization. This is useful for generating reports
and understanding data patterns without retrieving full records.

**Arguments**:

- `index` - List of indices to query
- `query` - Base query to filter documents
- `aggregation_query` - Aggregation definition to apply
  

**Returns**:

  Dictionary containing aggregation results
  

**Raises**:

- `ConnectionError` - If not connected to Elasticsearch
- `RequestError` - If the aggregation query fails

<a id="elasticsearch_client.ElasticsearchClient.stream_dshield_events"></a>

#### stream\_dshield\_events

```python
async def stream_dshield_events(
    time_range_hours: int = 24,
    indices: Optional[List[str]] = None,
    filters: Optional[Dict[str, Any]] = None,
    fields: Optional[List[str]] = None,
    chunk_size: int = 500,
    stream_id: Optional[str] = None
) -> tuple[List[Dict[str, Any]], int, Optional[str]]
```

Stream DShield events in chunks for large datasets.

Retrieves DShield events in configurable chunks to handle
very large datasets efficiently. This method is designed
for processing large amounts of data without memory issues.

**Arguments**:

- `time_range_hours` - Time range in hours to query (default: 24)
- `indices` - Specific indices to query (default: all DShield indices)
- `filters` - Additional query filters to apply
- `fields` - Specific fields to return (reduces payload size)
- `chunk_size` - Number of events per chunk (default: 500, max: 1000)
- `stream_id` - Optional stream ID for resuming interrupted streams
  

**Returns**:

  Tuple containing:
  - List of event dictionaries for the current chunk
  - Total count of available events
  - Next stream ID for continuing the stream (None if complete)
  

**Raises**:

- `ConnectionError` - If not connected to Elasticsearch
- `RequestError` - If the streaming query fails
- `ValueError` - If parameters are invalid

<a id="elasticsearch_client.ElasticsearchClient.query_dshield_attacks"></a>

#### query\_dshield\_attacks

```python
async def query_dshield_attacks(
        time_range_hours: int = 24,
        page: int = 1,
        page_size: int = 100,
        include_summary: bool = True) -> tuple[List[Dict[str, Any]], int]
```

Query DShield attack data specifically.

Retrieves attack-specific data from DShield indices, focusing
on security events that represent actual attacks rather than
general network traffic or logs.

**Arguments**:

- `time_range_hours` - Time range in hours to query (default: 24)
- `page` - Page number for pagination (default: 1)
- `page_size` - Number of results per page (default: 100, max: 1000)
- `include_summary` - Whether to include summary statistics
  

**Returns**:

  Tuple containing:
  - List of attack event dictionaries
  - Total count of available attacks
  

**Raises**:

- `ConnectionError` - If not connected to Elasticsearch
- `RequestError` - If the query fails

<a id="elasticsearch_client.ElasticsearchClient.query_dshield_reputation"></a>

#### query\_dshield\_reputation

```python
async def query_dshield_reputation(ip_addresses: Optional[List[str]] = None,
                                   size: int = 1000) -> List[Dict[str, Any]]
```

Query DShield reputation data for IP addresses.

Retrieves reputation and threat intelligence data for specific
IP addresses or all IPs in the DShield reputation database.

**Arguments**:

- `ip_addresses` - List of IP addresses to query (default: all IPs)
- `size` - Maximum number of results to return (default: 1000)
  

**Returns**:

  List of reputation data dictionaries
  

**Raises**:

- `ConnectionError` - If not connected to Elasticsearch
- `RequestError` - If the query fails

<a id="elasticsearch_client.ElasticsearchClient.query_dshield_top_attackers"></a>

#### query\_dshield\_top\_attackers

```python
async def query_dshield_top_attackers(hours: int = 24,
                                      limit: int = 100
                                      ) -> List[Dict[str, Any]]
```

Query DShield top attackers data.

Retrieves the most active attacker IP addresses based on
attack frequency and severity within the specified time period.

**Arguments**:

- `hours` - Time range in hours to analyze (default: 24)
- `limit` - Maximum number of attackers to return (default: 100)
  

**Returns**:

  List of top attacker data dictionaries
  

**Raises**:

- `ConnectionError` - If not connected to Elasticsearch
- `RequestError` - If the query fails

<a id="elasticsearch_client.ElasticsearchClient.query_dshield_geographic_data"></a>

#### query\_dshield\_geographic\_data

```python
async def query_dshield_geographic_data(
        countries: Optional[List[str]] = None,
        size: int = 1000) -> List[Dict[str, Any]]
```

Query DShield geographic attack data.

Retrieves attack data grouped by geographic location,
including country-level statistics and attack patterns.

**Arguments**:

- `countries` - List of countries to filter by (default: all countries)
- `size` - Maximum number of results to return (default: 1000)
  

**Returns**:

  List of geographic attack data dictionaries
  

**Raises**:

- `ConnectionError` - If not connected to Elasticsearch
- `RequestError` - If the query fails

<a id="elasticsearch_client.ElasticsearchClient.query_dshield_port_data"></a>

#### query\_dshield\_port\_data

```python
async def query_dshield_port_data(ports: Optional[List[int]] = None,
                                  size: int = 1000) -> List[Dict[str, Any]]
```

Query DShield port attack data.

Retrieves attack data grouped by destination ports,
including port-specific attack patterns and statistics.

**Arguments**:

- `ports` - List of ports to filter by (default: all ports)
- `size` - Maximum number of results to return (default: 1000)
  

**Returns**:

  List of port attack data dictionaries
  

**Raises**:

- `ConnectionError` - If not connected to Elasticsearch
- `RequestError` - If the query fails

<a id="elasticsearch_client.ElasticsearchClient.query_events_by_ip"></a>

#### query\_events\_by\_ip

```python
async def query_events_by_ip(
        ip_addresses: List[str],
        time_range_hours: int = 24,
        indices: Optional[List[str]] = None) -> List[Dict[str, Any]]
```

Query DShield events for specific IP addresses.

Retrieves all events associated with the specified IP addresses,
including both source and destination IP matches. This is useful
for investigating specific IP addresses involved in attacks.

**Arguments**:

- `ip_addresses` - List of IP addresses to search for
- `time_range_hours` - Time range in hours to query (default: 24)
- `indices` - Specific indices to query (default: all DShield indices)
  

**Returns**:

  List of event dictionaries for the specified IPs
  

**Raises**:

- `RuntimeError` - If Elasticsearch client is not connected
- `RequestError` - If the query fails

<a id="elasticsearch_client.ElasticsearchClient.get_dshield_statistics"></a>

#### get\_dshield\_statistics

```python
async def get_dshield_statistics(time_range_hours: int = 24) -> Dict[str, Any]
```

Get comprehensive DShield statistics and summary.

Retrieves aggregated statistics from multiple DShield data sources,
including event counts, top attackers, geographic distribution,
and other summary metrics.

**Arguments**:

- `time_range_hours` - Time range in hours for statistics (default: 24)
  

**Returns**:

  Dictionary containing comprehensive statistics including:
  - total_events: Total number of events
  - top_attackers: List of most active attackers
  - geographic_distribution: Attack distribution by country
  - time_range_hours: Time range used for analysis
  - timestamp: When the statistics were generated
  

**Raises**:

- `Exception` - If statistics collection fails

<a id="elasticsearch_client.ElasticsearchClient.log_unmapped_fields"></a>

#### log\_unmapped\_fields

```python
def log_unmapped_fields(source: Dict[str, Any])
```

Log any fields in the source document that are not mapped to any known field type.

**Arguments**:

- `source` - Source dictionary from Elasticsearch document
  

**Returns**:

  None

<a id="elasticsearch_client.ElasticsearchClient.query_security_events"></a>

#### query\_security\_events

```python
async def query_security_events(
        time_range_hours: int = 24,
        indices: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        size: Optional[int] = None,
        timeout: Optional[int] = None) -> List[Dict[str, Any]]
```

Backward compatibility method - redirects to query_dshield_events.

**Arguments**:

- `time_range_hours` - Time range in hours to query (default: 24)
- `indices` - List of indices to query (optional)
- `filters` - Query filters to apply (optional)
- `size` - Number of results to return (optional)
- `timeout` - Query timeout in seconds (optional)
  

**Returns**:

  List of event dictionaries

<a id="elasticsearch_client.ElasticsearchClient.get_index_mapping"></a>

#### get\_index\_mapping

```python
async def get_index_mapping(index_pattern: str) -> Dict[str, Any]
```

Get mapping for an index pattern.

Retrieves the field mapping information for the specified
index pattern from Elasticsearch.

**Arguments**:

- `index_pattern` - Index pattern to get mapping for
  

**Returns**:

  Dictionary containing the index mapping information
  

**Raises**:

- `RuntimeError` - If Elasticsearch client is not connected
- `Exception` - If the mapping request fails

<a id="elasticsearch_client.ElasticsearchClient.get_cluster_stats"></a>

#### get\_cluster\_stats

```python
async def get_cluster_stats() -> Dict[str, Any]
```

Get Elasticsearch cluster statistics.

Retrieves comprehensive statistics about the Elasticsearch
cluster including node information, indices, and performance metrics.

**Returns**:

  Dictionary containing cluster statistics
  

**Raises**:

- `RuntimeError` - If Elasticsearch client is not connected
- `Exception` - If the cluster stats request fails

<a id="elasticsearch_client.ElasticsearchClient.stream_dshield_events_with_session_context"></a>

#### stream\_dshield\_events\_with\_session\_context

```python
async def stream_dshield_events_with_session_context(
    time_range_hours: int = 24,
    indices: Optional[List[str]] = None,
    filters: Optional[Dict[str, Any]] = None,
    fields: Optional[List[str]] = None,
    chunk_size: int = 500,
    session_fields: Optional[List[str]] = None,
    max_session_gap_minutes: int = 30,
    include_session_summary: bool = True,
    stream_id: Optional[str] = None
) -> tuple[List[Dict[str, Any]], int, Optional[str], Dict[str, Any]]
```

Stream DShield events with smart session-based chunking.

Groups events by session context (e.g., source IP, user session, connection ID)
and ensures related events stay together in the same chunk. This is useful
for event correlation and analysis.

**Arguments**:

- `time_range_hours` - Time range in hours to query (default: 24)
- `indices` - Specific indices to query (default: all DShield indices)
- `filters` - Additional query filters to apply
- `fields` - Specific fields to return (reduces payload size)
- `chunk_size` - Number of events per chunk (default: 500, max: 1000)
- `session_fields` - Fields to use for session grouping (default: ['source.ip', 'destination.ip', 'user.name', 'session.id'])
- `max_session_gap_minutes` - Maximum time gap within a session before starting new session (default: 30)
- `include_session_summary` - Include session metadata in response (default: True)
- `stream_id` - Resume streaming from specific point
  

**Returns**:

  Tuple containing:
  - List of event dictionaries for the current chunk
  - Total count of available events
  - Next stream ID for continuing the stream (None if complete)
  - Session context information
  

**Raises**:

- `ConnectionError` - If not connected to Elasticsearch
- `RequestError` - If the streaming query fails
- `ValueError` - If parameters are invalid

<a id="models"></a>

# models

Data models for DShield MCP Elastic SIEM integration.

This module provides comprehensive data models for the DShield MCP server,
optimized for DShield SIEM data structures and patterns. It includes models
for security events, attacks, reputation data, and various DShield-specific
data types.

The models are built using Pydantic for automatic validation, serialization,
and documentation generation. They provide type safety and ensure data
consistency across the application.

This module provides:
- Security event models with validation
- DShield-specific data models
- Threat intelligence models
- Query and filter models
- Statistics and summary models

**Example**:

  >>> from src.models import SecurityEvent, EventSeverity
  >>> event = SecurityEvent(
  ...     id="event_123",
  ...     timestamp=datetime.now(),
  ...     event_type="attack",
  ...     severity=EventSeverity.HIGH,
  ...     description="Suspicious activity detected"
  ... )
  >>> print(event.severity)
  EventSeverity.HIGH

<a id="models.EventSeverity"></a>

## EventSeverity Objects

```python
class EventSeverity(str, Enum)
```

Security event severity levels.

<a id="models.EventCategory"></a>

## EventCategory Objects

```python
class EventCategory(str, Enum)
```

Security event categories.

<a id="models.DShieldEventType"></a>

## DShieldEventType Objects

```python
class DShieldEventType(str, Enum)
```

DShield specific event types.

<a id="models.SecurityEvent"></a>

## SecurityEvent Objects

```python
class SecurityEvent(BaseModel)
```

Model for security events from DShield SIEM.

<a id="models.SecurityEvent.validate_ip_address"></a>

#### validate\_ip\_address

```python
@field_validator('source_ip', 'destination_ip')
@classmethod
def validate_ip_address(cls, v: Optional[str]) -> Optional[str]
```

Validate IP address format.

**Arguments**:

- `v` - IP address string to validate
  

**Returns**:

  The validated IP address string
  

**Raises**:

- `ValueError` - If the IP address format is invalid

<a id="models.SecurityEvent.validate_port"></a>

#### validate\_port

```python
@field_validator('source_port', 'destination_port')
@classmethod
def validate_port(cls, v: Optional[int]) -> Optional[int]
```

Validate port number.

**Arguments**:

- `v` - Port number to validate
  

**Returns**:

  The validated port number
  

**Raises**:

- `ValueError` - If the port number is outside valid range (1-65535)

<a id="models.SecurityEvent.validate_reputation_score"></a>

#### validate\_reputation\_score

```python
@field_validator('reputation_score')
@classmethod
def validate_reputation_score(cls, v: Optional[float]) -> Optional[float]
```

Validate reputation score range.

**Arguments**:

- `v` - Reputation score to validate
  

**Returns**:

  The validated reputation score
  

**Raises**:

- `ValueError` - If the reputation score is outside valid range (0-100)

<a id="models.DShieldAttack"></a>

## DShieldAttack Objects

```python
class DShieldAttack(BaseModel)
```

Model for DShield attack events.

<a id="models.DShieldReputation"></a>

## DShieldReputation Objects

```python
class DShieldReputation(BaseModel)
```

Model for DShield reputation data.

<a id="models.DShieldReputation.validate_ip_address"></a>

#### validate\_ip\_address

```python
@field_validator('ip_address')
@classmethod
def validate_ip_address(cls, v)
```

Validate IP address format.

<a id="models.DShieldReputation.validate_reputation_score"></a>

#### validate\_reputation\_score

```python
@field_validator('reputation_score')
@classmethod
def validate_reputation_score(cls, v)
```

Validate reputation score range.

<a id="models.DShieldTopAttacker"></a>

## DShieldTopAttacker Objects

```python
class DShieldTopAttacker(BaseModel)
```

Model for DShield top attacker data.

<a id="models.DShieldTopAttacker.validate_ip_address"></a>

#### validate\_ip\_address

```python
@field_validator('ip_address')
@classmethod
def validate_ip_address(cls, v)
```

Validate IP address format.

<a id="models.DShieldGeographicData"></a>

## DShieldGeographicData Objects

```python
class DShieldGeographicData(BaseModel)
```

Model for DShield geographic data.

<a id="models.DShieldPortData"></a>

## DShieldPortData Objects

```python
class DShieldPortData(BaseModel)
```

Model for DShield port data.

<a id="models.DShieldPortData.validate_port"></a>

#### validate\_port

```python
@field_validator('port')
@classmethod
def validate_port(cls, v)
```

Validate port number.

<a id="models.ThreatIntelligenceSource"></a>

## ThreatIntelligenceSource Objects

```python
class ThreatIntelligenceSource(str, Enum)
```

Threat intelligence sources.

<a id="models.ThreatIntelligence"></a>

## ThreatIntelligence Objects

```python
class ThreatIntelligence(BaseModel)
```

Model for DShield threat intelligence data.

<a id="models.ThreatIntelligence.validate_ip_address"></a>

#### validate\_ip\_address

```python
@field_validator('ip_address')
@classmethod
def validate_ip_address(cls, v)
```

Validate IP address format.

<a id="models.ThreatIntelligence.validate_reputation_score"></a>

#### validate\_reputation\_score

```python
@field_validator('reputation_score')
@classmethod
def validate_reputation_score(cls, v)
```

Validate reputation score range.

<a id="models.ThreatIntelligenceResult"></a>

## ThreatIntelligenceResult Objects

```python
class ThreatIntelligenceResult(BaseModel)
```

Enhanced threat intelligence result from multiple sources.

<a id="models.ThreatIntelligenceResult.validate_ip_address"></a>

#### validate\_ip\_address

```python
@field_validator('ip_address')
@classmethod
def validate_ip_address(cls, v)
```

Validate IP address format.

<a id="models.ThreatIntelligenceResult.validate_overall_threat_score"></a>

#### validate\_overall\_threat\_score

```python
@field_validator('overall_threat_score')
@classmethod
def validate_overall_threat_score(cls, v)
```

Validate overall threat score range.

<a id="models.ThreatIntelligenceResult.validate_confidence_score"></a>

#### validate\_confidence\_score

```python
@field_validator('confidence_score')
@classmethod
def validate_confidence_score(cls, v)
```

Validate confidence score range.

<a id="models.DomainIntelligence"></a>

## DomainIntelligence Objects

```python
class DomainIntelligence(BaseModel)
```

Domain threat intelligence data.

<a id="models.DomainIntelligence.validate_domain"></a>

#### validate\_domain

```python
@field_validator('domain')
@classmethod
def validate_domain(cls, v)
```

Validate domain name format.

<a id="models.DomainIntelligence.validate_score"></a>

#### validate\_score

```python
@field_validator('threat_score', 'reputation_score')
@classmethod
def validate_score(cls, v)
```

Validate score range.

<a id="models.AttackReport"></a>

## AttackReport Objects

```python
class AttackReport(BaseModel)
```

Model for structured attack reports.

<a id="models.SecuritySummary"></a>

## SecuritySummary Objects

```python
class SecuritySummary(BaseModel)
```

Model for security summary statistics.

<a id="models.QueryFilter"></a>

## QueryFilter Objects

```python
class QueryFilter(BaseModel)
```

Model for Elasticsearch query filters.

<a id="models.QueryFilter.validate_operator"></a>

#### validate\_operator

```python
@field_validator('operator')
@classmethod
def validate_operator(cls, v)
```

Validate filter operator.

<a id="models.ElasticsearchQuery"></a>

## ElasticsearchQuery Objects

```python
class ElasticsearchQuery(BaseModel)
```

Model for Elasticsearch queries.

<a id="models.ElasticsearchQuery.validate_size"></a>

#### validate\_size

```python
@field_validator('size')
@classmethod
def validate_size(cls, v)
```

Validate result size.

<a id="models.DShieldStatistics"></a>

## DShieldStatistics Objects

```python
class DShieldStatistics(BaseModel)
```

Model for DShield statistics data.

<a id="op_secrets"></a>

# op\_secrets

1Password CLI integration for secret management in DShield MCP.

This module provides integration with the 1Password CLI for secure secret
management. It handles op:// URLs in configuration values by resolving
them using the 1Password CLI tool.

Features:
- 1Password CLI availability detection
- op:// URL resolution
- Environment variable resolution
- Complex value processing with embedded URLs
- Error handling and logging

**Example**:

  >>> from src.op_secrets import OnePasswordSecrets
  >>> op = OnePasswordSecrets()
  >>> secret = op.resolve_environment_variable("op://vault/item/field")
  >>> print(secret)

<a id="op_secrets.OnePasswordSecrets"></a>

## OnePasswordSecrets Objects

```python
class OnePasswordSecrets()
```

Handle 1Password secret resolution for config values.

This class provides methods to resolve 1Password CLI references (op:// URLs)
in configuration values. It automatically detects 1Password CLI availability
and provides fallback behavior when the CLI is not available.

**Attributes**:

- `op_available` - Whether the 1Password CLI is available and working
  

**Example**:

  >>> op = OnePasswordSecrets()
  >>> if op.op_available:
  ...     secret = op.resolve_op_url("op://vault/item/field")
  ...     print(secret)

<a id="op_secrets.OnePasswordSecrets.__init__"></a>

#### \_\_init\_\_

```python
def __init__() -> None
```

Initialize the OnePasswordSecrets manager.

Checks for 1Password CLI availability and logs a warning if it's not
available. This affects the behavior of URL resolution methods.

<a id="op_secrets.OnePasswordSecrets.resolve_op_url"></a>

#### resolve\_op\_url

```python
def resolve_op_url(op_url: str) -> Optional[str]
```

Resolve a 1Password URL (op://) to its actual value.

Uses the 1Password CLI to retrieve the secret value referenced
by the op:// URL. Handles various error conditions gracefully.

**Arguments**:

- `op_url` - The 1Password URL (e.g., "op://vault/item/field")
  

**Returns**:

  The resolved secret value or None if resolution failed
  

**Raises**:

- `subprocess.TimeoutExpired` - If the CLI command times out
- `subprocess.CalledProcessError` - If the CLI command fails

<a id="op_secrets.OnePasswordSecrets.resolve_environment_variable"></a>

#### resolve\_environment\_variable

```python
def resolve_environment_variable(value: str) -> str
```

Resolve config value, handling op:// URLs.

Processes a configuration value that may contain 1Password CLI
references. Handles both simple op:// URLs and complex values
with embedded URLs.

**Arguments**:

- `value` - The config value to resolve
  

**Returns**:

  The resolved value (original if not an op:// URL or resolution failed)

<a id="user_config"></a>

# user\_config

User Configuration Management for DShield MCP.

This module provides comprehensive user configuration management for the DShield MCP
server. It extends the base configuration system with user-customizable settings,
validation, environment variable support, and multiple configuration sources.

Features:
- User-configurable settings with validation
- Environment variable overrides
- Multiple configuration file sources
- Setting categories (query, pagination, streaming, etc.)
- Configuration export and import
- 1Password CLI integration

**Example**:

  >>> from src.user_config import get_user_config
  >>> config = get_user_config()
  >>> page_size = config.get_setting("query", "default_page_size")
  >>> print(page_size)

<a id="user_config.QuerySettings"></a>

## QuerySettings Objects

```python
@dataclass
class QuerySettings()
```

User-configurable query settings.

**Attributes**:

- `default_page_size` - Default number of results per page
- `max_page_size` - Maximum allowed page size
- `default_timeout_seconds` - Default query timeout in seconds
- `max_timeout_seconds` - Maximum allowed timeout in seconds
- `enable_smart_optimization` - Whether to enable smart query optimization
- `fallback_strategy` - Strategy for handling query failures
- `max_query_complexity` - Maximum query complexity threshold

<a id="user_config.QuerySettings.fallback_strategy"></a>

#### fallback\_strategy

aggregate, sample, error

<a id="user_config.PaginationSettings"></a>

## PaginationSettings Objects

```python
@dataclass
class PaginationSettings()
```

User-configurable pagination settings.

**Attributes**:

- `default_method` - Default pagination method (page or cursor)
- `max_pages_per_request` - Maximum pages per request
- `cursor_timeout_seconds` - Cursor timeout in seconds
- `enable_metadata` - Whether to include pagination metadata
- `include_performance_metrics` - Whether to include performance metrics

<a id="user_config.PaginationSettings.default_method"></a>

#### default\_method

page, cursor

<a id="user_config.StreamingSettings"></a>

## StreamingSettings Objects

```python
@dataclass
class StreamingSettings()
```

User-configurable streaming settings.

**Attributes**:

- `default_chunk_size` - Default chunk size for streaming
- `max_chunk_size` - Maximum allowed chunk size
- `session_context_fields` - Fields to use for session context
- `enable_session_summaries` - Whether to enable session summaries
- `session_timeout_minutes` - Session timeout in minutes

<a id="user_config.PerformanceSettings"></a>

## PerformanceSettings Objects

```python
@dataclass
class PerformanceSettings()
```

User-configurable performance settings.

**Attributes**:

- `enable_caching` - Whether to enable caching
- `cache_ttl_seconds` - Cache time-to-live in seconds
- `max_cache_size` - Maximum cache size
- `enable_connection_pooling` - Whether to enable connection pooling
- `connection_pool_size` - Connection pool size
- `request_timeout_seconds` - Request timeout in seconds
- `enable_sqlite_cache` - Whether to enable SQLite persistent caching
- `sqlite_cache_ttl_hours` - SQLite cache time-to-live in hours
- `sqlite_cache_db_name` - SQLite database filename

<a id="user_config.SecuritySettings"></a>

## SecuritySettings Objects

```python
@dataclass
class SecuritySettings()
```

User-configurable security settings.

**Attributes**:

- `rate_limit_requests_per_minute` - Rate limit for requests per minute
- `max_query_results` - Maximum query results
- `enable_field_validation` - Whether to enable field validation
- `allowed_field_patterns` - Regex patterns for allowed fields
- `block_sensitive_fields` - Whether to block sensitive fields
- `sensitive_field_patterns` - Regex patterns for sensitive fields

<a id="user_config.LoggingSettings"></a>

## LoggingSettings Objects

```python
@dataclass
class LoggingSettings()
```

User-configurable logging settings.

**Attributes**:

- `log_level` - Logging level
- `log_format` - Log format (json, text)
- `enable_query_logging` - Whether to enable query logging
- `enable_performance_logging` - Whether to enable performance logging
- `log_sensitive_data` - Whether to log sensitive data
- `max_log_size_mb` - Maximum log size in MB

<a id="user_config.CampaignSettings"></a>

## CampaignSettings Objects

```python
@dataclass
class CampaignSettings()
```

User-configurable campaign analysis settings.

**Attributes**:

- `correlation_window_minutes` - Correlation window in minutes
- `min_confidence_threshold` - Minimum confidence threshold
- `max_campaign_events` - Maximum campaign events
- `enable_geospatial_correlation` - Whether to enable geospatial correlation
- `enable_infrastructure_correlation` - Whether to enable infrastructure correlation
- `enable_behavioral_correlation` - Whether to enable behavioral correlation
- `enable_temporal_correlation` - Whether to enable temporal correlation
- `enable_ip_correlation` - Whether to enable IP correlation
- `max_expansion_depth` - Maximum expansion depth
- `expansion_timeout_seconds` - Expansion timeout in seconds

<a id="user_config.UserConfigManager"></a>

## UserConfigManager Objects

```python
class UserConfigManager()
```

Manages user-configurable settings with validation and environment variable support.

This class provides a comprehensive configuration management system that
supports multiple configuration sources with precedence ordering:
1. Environment variables (highest priority)
2. User configuration file
3. Base configuration
4. Default values (lowest priority)

**Attributes**:

- `config_path` - Path to the configuration file
- `op_secrets` - OnePassword secrets manager
- `base_config` - Base configuration dictionary
- `query_settings` - Query-related settings
- `pagination_settings` - Pagination-related settings
- `streaming_settings` - Streaming-related settings
- `performance_settings` - Performance-related settings
- `security_settings` - Security-related settings
- `logging_settings` - Logging-related settings
- `campaign_settings` - Campaign analysis settings
- `output_directory` - Directory for generated outputs (default: ~/dshield-mcp-output, configurable)
  

**Example**:

  >>> manager = UserConfigManager()
  >>> output_dir = manager.output_directory
  >>> print(output_dir)

<a id="user_config.UserConfigManager.__init__"></a>

#### \_\_init\_\_

```python
def __init__(config_path: Optional[str] = None) -> None
```

Initialize the UserConfigManager.

**Arguments**:

- `config_path` - Optional path to the configuration file

<a id="user_config.UserConfigManager.get_setting"></a>

#### get\_setting

```python
def get_setting(category: str, setting: str) -> Any
```

Get a specific setting value.

**Arguments**:

- `category` - Setting category (query, pagination, streaming, etc.)
- `setting` - Setting name within the category
  

**Returns**:

  Setting value
  

**Raises**:

- `KeyError` - If category or setting does not exist

<a id="user_config.UserConfigManager.update_setting"></a>

#### update\_setting

```python
def update_setting(category: str, setting: str, value: Any) -> None
```

Update a specific setting value.

**Arguments**:

- `category` - Setting category (query, pagination, streaming, etc.)
- `setting` - Setting name within the category
- `value` - New value for the setting
  

**Raises**:

- `KeyError` - If category or setting does not exist
- `ValueError` - If value is invalid for the setting

<a id="user_config.UserConfigManager.export_config"></a>

#### export\_config

```python
def export_config() -> Dict[str, Any]
```

Export current configuration as a dictionary.

**Returns**:

  Dictionary containing all current configuration settings

<a id="user_config.UserConfigManager.save_user_config"></a>

#### save\_user\_config

```python
def save_user_config(file_path: Optional[str] = None) -> None
```

Save current configuration to a file.

**Arguments**:

- `file_path` - Path to save the configuration file (default: auto-detected)

<a id="user_config.UserConfigManager.get_environment_variables"></a>

#### get\_environment\_variables

```python
def get_environment_variables() -> Dict[str, str]
```

Get environment variables that can be used to override settings.

**Returns**:

  Dictionary mapping setting names to environment variable names

<a id="user_config.UserConfigManager.get_database_directory"></a>

#### get\_database\_directory

```python
def get_database_directory() -> str
```

Get the database directory path.

**Returns**:

- `str` - Path to the database directory (~/dshield-mcp-output/db)

<a id="user_config.UserConfigManager.get_cache_database_path"></a>

#### get\_cache\_database\_path

```python
def get_cache_database_path() -> str
```

Get the full path to the cache database file.

**Returns**:

- `str` - Full path to the cache database file

<a id="user_config.get_user_config"></a>

#### get\_user\_config

```python
def get_user_config() -> UserConfigManager
```

Get the global user configuration manager instance.

**Returns**:

- `UserConfigManager` - The global configuration manager instance

<a id="user_config.reset_user_config"></a>

#### reset\_user\_config

```python
def reset_user_config() -> None
```

Reset the global user configuration manager instance.

This function clears the global configuration manager, forcing
a reload of configuration on the next get_user_config() call.

