<a id="campaign_analyzer"></a>

# campaign\_analyzer

Campaign Analysis Engine for DShield MCP
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

<a id="campaign_analyzer.CampaignAnalyzer.correlate_events"></a>

#### correlate\_events

```python
async def correlate_events(seed_events: List[Dict[str, Any]],
                           correlation_criteria: List[CorrelationMethod],
                           time_window_hours: int = 48,
                           min_confidence: float = 0.7) -> Campaign
```

Correlate events based on specified criteria to identify campaigns.

<a id="campaign_analyzer.CampaignAnalyzer.expand_indicators"></a>

#### expand\_indicators

```python
async def expand_indicators(seed_iocs: List[str],
                            expansion_strategy: str = "comprehensive",
                            max_depth: int = 3) -> List[IndicatorRelationship]
```

Expand IOCs to find related indicators.

<a id="campaign_analyzer.CampaignAnalyzer.build_campaign_timeline"></a>

#### build\_campaign\_timeline

```python
async def build_campaign_timeline(
        correlated_events: List[CampaignEvent],
        timeline_granularity: str = "hourly") -> Dict[str, Any]
```

Build chronological timeline of campaign events.

<a id="campaign_analyzer.CampaignAnalyzer.score_campaign"></a>

#### score\_campaign

```python
async def score_campaign(campaign_data: Campaign) -> float
```

Score campaign based on sophistication and impact.

<a id="campaign_mcp_tools"></a>

# campaign\_mcp\_tools

Campaign Analysis MCP Tools
MCP tools for campaign analysis and correlation.

<a id="campaign_mcp_tools.CampaignMCPTools"></a>

## CampaignMCPTools Objects

```python
class CampaignMCPTools()
```

MCP tools for campaign analysis and correlation.

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

<a id="config_loader.get_config"></a>

#### get\_config

```python
def get_config(config_path: str = None) -> dict
```

Load the MCP YAML config file. Raise ConfigError if missing or invalid.
By default, looks for 'mcp_config.yaml' in the project root.

<a id="context_injector"></a>

# context\_injector

Context injector for preparing data for ChatGPT context injection.

<a id="context_injector.ContextInjector"></a>

## ContextInjector Objects

```python
class ContextInjector()
```

Prepare and inject security context for ChatGPT analysis.

<a id="context_injector.ContextInjector.prepare_security_context"></a>

#### prepare\_security\_context

```python
def prepare_security_context(
        events: List[Dict[str, Any]],
        threat_intelligence: Optional[Dict[str, Any]] = None,
        summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]
```

Prepare security context for injection.

<a id="context_injector.ContextInjector.prepare_attack_report_context"></a>

#### prepare\_attack\_report\_context

```python
def prepare_attack_report_context(report: Dict[str, Any]) -> Dict[str, Any]
```

Prepare attack report context for injection.

<a id="context_injector.ContextInjector.prepare_query_context"></a>

#### prepare\_query\_context

```python
def prepare_query_context(query_type: str, parameters: Dict[str, Any],
                          results: List[Dict[str, Any]]) -> Dict[str, Any]
```

Prepare query context for injection.

<a id="context_injector.ContextInjector.inject_context_for_chatgpt"></a>

#### inject\_context\_for\_chatgpt

```python
def inject_context_for_chatgpt(context: Dict[str, Any]) -> str
```

Format context for ChatGPT consumption.

<a id="context_injector.ContextInjector.create_mcp_context_injection"></a>

#### create\_mcp\_context\_injection

```python
def create_mcp_context_injection(context: Dict[str, Any]) -> Dict[str, Any]
```

Create MCP-compatible context injection.

<a id="data_dictionary"></a>

# data\_dictionary

Data Dictionary for DShield MCP Elastic SIEM Integration
Provides comprehensive field descriptions and examples to help models understand
the available data structures and their meanings.

<a id="data_dictionary.DataDictionary"></a>

## DataDictionary Objects

```python
class DataDictionary()
```

Comprehensive data dictionary for DShield SIEM data.

<a id="data_dictionary.DataDictionary.get_field_descriptions"></a>

#### get\_field\_descriptions

```python
@staticmethod
def get_field_descriptions() -> Dict[str, Any]
```

Get comprehensive field descriptions for DShield data.

<a id="data_dictionary.DataDictionary.get_query_examples"></a>

#### get\_query\_examples

```python
@staticmethod
def get_query_examples() -> Dict[str, Any]
```

Get example queries for common use cases.

<a id="data_dictionary.DataDictionary.get_data_patterns"></a>

#### get\_data\_patterns

```python
@staticmethod
def get_data_patterns() -> Dict[str, Any]
```

Get common data patterns and their meanings.

<a id="data_dictionary.DataDictionary.get_analysis_guidelines"></a>

#### get\_analysis\_guidelines

```python
@staticmethod
def get_analysis_guidelines() -> Dict[str, Any]
```

Get guidelines for analyzing DShield data.

<a id="data_dictionary.DataDictionary.get_initial_prompt"></a>

#### get\_initial\_prompt

```python
@staticmethod
def get_initial_prompt() -> str
```

Get the initial prompt to provide to models for understanding DShield data.

<a id="data_processor"></a>

# data\_processor

Data processor for formatting and structuring DShield SIEM data for AI consumption.
Optimized for DShield SIEM data structures and patterns.

<a id="data_processor.DataProcessor"></a>

## DataProcessor Objects

```python
class DataProcessor()
```

Process and structure DShield SIEM data for AI analysis.

<a id="data_processor.DataProcessor.process_security_events"></a>

#### process\_security\_events

```python
def process_security_events(
        events: List[Dict[str, Any]]) -> List[Dict[str, Any]]
```

Process and normalize security events from DShield SIEM.

<a id="data_processor.DataProcessor.process_dshield_attacks"></a>

#### process\_dshield\_attacks

```python
def process_dshield_attacks(
        attacks: List[Dict[str, Any]]) -> List[DShieldAttack]
```

Process DShield attack events into structured format.

<a id="data_processor.DataProcessor.process_dshield_reputation"></a>

#### process\_dshield\_reputation

```python
def process_dshield_reputation(
        reputation_data: List[Dict[str, Any]]) -> Dict[str, DShieldReputation]
```

Process DShield reputation data into structured format.

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

<a id="dshield_client.DShieldClient"></a>

## DShieldClient Objects

```python
class DShieldClient()
```

Client for interacting with DShield threat intelligence API.

<a id="dshield_client.DShieldClient.__aenter__"></a>

#### \_\_aenter\_\_

```python
async def __aenter__()
```

Async context manager entry.

<a id="dshield_client.DShieldClient.__aexit__"></a>

#### \_\_aexit\_\_

```python
async def __aexit__(exc_type, exc_val, exc_tb)
```

Async context manager exit.

<a id="dshield_client.DShieldClient.connect"></a>

#### connect

```python
async def connect()
```

Initialize HTTP session.

<a id="dshield_client.DShieldClient.close"></a>

#### close

```python
async def close()
```

Close HTTP session.

<a id="dshield_client.DShieldClient.get_ip_reputation"></a>

#### get\_ip\_reputation

```python
async def get_ip_reputation(ip_address: str) -> Dict[str, Any]
```

Get IP reputation from DShield.

<a id="dshield_client.DShieldClient.get_ip_details"></a>

#### get\_ip\_details

```python
async def get_ip_details(ip_address: str) -> Dict[str, Any]
```

Get detailed IP information from DShield.

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

Execute an aggregation query against Elasticsearch.

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

Stream DShield events with cursor-based pagination for large datasets.

<a id="elasticsearch_client.ElasticsearchClient.query_dshield_attacks"></a>

#### query\_dshield\_attacks

```python
async def query_dshield_attacks(
        time_range_hours: int = 24,
        page: int = 1,
        page_size: int = 100,
        include_summary: bool = True) -> tuple[List[Dict[str, Any]], int]
```

Query DShield attack events with pagination support.

<a id="elasticsearch_client.ElasticsearchClient.query_dshield_reputation"></a>

#### query\_dshield\_reputation

```python
async def query_dshield_reputation(ip_addresses: Optional[List[str]] = None,
                                   size: int = 1000) -> List[Dict[str, Any]]
```

Query DShield reputation data.

<a id="elasticsearch_client.ElasticsearchClient.query_dshield_top_attackers"></a>

#### query\_dshield\_top\_attackers

```python
async def query_dshield_top_attackers(hours: int = 24,
                                      limit: int = 100
                                      ) -> List[Dict[str, Any]]
```

Query DShield top attackers data.

<a id="elasticsearch_client.ElasticsearchClient.query_dshield_geographic_data"></a>

#### query\_dshield\_geographic\_data

```python
async def query_dshield_geographic_data(
        countries: Optional[List[str]] = None,
        size: int = 1000) -> List[Dict[str, Any]]
```

Query DShield geographic data.

<a id="elasticsearch_client.ElasticsearchClient.query_dshield_port_data"></a>

#### query\_dshield\_port\_data

```python
async def query_dshield_port_data(ports: Optional[List[int]] = None,
                                  size: int = 1000) -> List[Dict[str, Any]]
```

Query DShield port data.

<a id="elasticsearch_client.ElasticsearchClient.query_events_by_ip"></a>

#### query\_events\_by\_ip

```python
async def query_events_by_ip(
        ip_addresses: List[str],
        time_range_hours: int = 24,
        indices: Optional[List[str]] = None) -> List[Dict[str, Any]]
```

Query events for specific IP addresses.

<a id="elasticsearch_client.ElasticsearchClient.get_dshield_statistics"></a>

#### get\_dshield\_statistics

```python
async def get_dshield_statistics(time_range_hours: int = 24) -> Dict[str, Any]
```

Get DShield statistics and summary data.

<a id="elasticsearch_client.ElasticsearchClient.log_unmapped_fields"></a>

#### log\_unmapped\_fields

```python
def log_unmapped_fields(source: Dict[str, Any])
```

Log any fields in the source document that are not mapped to any known field type.

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

<a id="elasticsearch_client.ElasticsearchClient.get_index_mapping"></a>

#### get\_index\_mapping

```python
async def get_index_mapping(index_pattern: str) -> Dict[str, Any]
```

Get mapping for an index pattern.

<a id="elasticsearch_client.ElasticsearchClient.get_cluster_stats"></a>

#### get\_cluster\_stats

```python
async def get_cluster_stats() -> Dict[str, Any]
```

Get Elasticsearch cluster statistics.

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
and ensures related events stay together in the same chunk.

**Arguments**:

- `session_fields` - Fields to use for session grouping (e.g., ['source.ip', 'user.name'])
- `max_session_gap_minutes` - Maximum time gap within a session before starting new session
- `include_session_summary` - Include session metadata in response
- `stream_id` - Resume streaming from specific point
  

**Returns**:

  Tuple of (events, total_count, next_stream_id, session_context)

<a id="models"></a>

# models

Data models for DShield MCP Elastic SIEM integration.
Optimized for DShield SIEM data structures and patterns.

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
def validate_ip_address(cls, v)
```

Validate IP address format.

<a id="models.SecurityEvent.validate_port"></a>

#### validate\_port

```python
@field_validator('source_port', 'destination_port')
@classmethod
def validate_port(cls, v)
```

Validate port number.

<a id="models.SecurityEvent.validate_reputation_score"></a>

#### validate\_reputation\_score

```python
@field_validator('reputation_score')
@classmethod
def validate_reputation_score(cls, v)
```

Validate reputation score range.

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
Handles op:// URLs in config values by resolving them using the 1Password CLI.

<a id="op_secrets.OnePasswordSecrets"></a>

## OnePasswordSecrets Objects

```python
class OnePasswordSecrets()
```

Handle 1Password secret resolution for config values.

<a id="op_secrets.OnePasswordSecrets.resolve_op_url"></a>

#### resolve\_op\_url

```python
def resolve_op_url(op_url: str) -> Optional[str]
```

Resolve a 1Password URL (op://) to its actual value.

**Arguments**:

- `op_url` - The 1Password URL (e.g., "op://vault/item/field")

**Returns**:

  The resolved secret value or None if resolution failed

<a id="op_secrets.OnePasswordSecrets.resolve_environment_variable"></a>

#### resolve\_environment\_variable

```python
def resolve_environment_variable(value: str) -> str
```

Resolve config value, handling op:// URLs.

**Arguments**:

- `value` - The config value

**Returns**:

  The resolved value (original if not an op:// URL)

<a id="user_config"></a>

# user\_config

User Configuration Management for DShield MCP
Extends the existing configuration system with user-customizable settings,
validation, and environment variable support.

<a id="user_config.QuerySettings"></a>

## QuerySettings Objects

```python
@dataclass
class QuerySettings()
```

User-configurable query settings.

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

<a id="user_config.PerformanceSettings"></a>

## PerformanceSettings Objects

```python
@dataclass
class PerformanceSettings()
```

User-configurable performance settings.

<a id="user_config.SecuritySettings"></a>

## SecuritySettings Objects

```python
@dataclass
class SecuritySettings()
```

User-configurable security settings.

<a id="user_config.LoggingSettings"></a>

## LoggingSettings Objects

```python
@dataclass
class LoggingSettings()
```

User-configurable logging settings.

<a id="user_config.CampaignSettings"></a>

## CampaignSettings Objects

```python
@dataclass
class CampaignSettings()
```

User-configurable campaign analysis settings.

<a id="user_config.UserConfigManager"></a>

## UserConfigManager Objects

```python
class UserConfigManager()
```

Manages user-configurable settings with validation and environment variable support.

<a id="user_config.UserConfigManager.get_setting"></a>

#### get\_setting

```python
def get_setting(category: str, setting: str) -> Any
```

Get a specific setting value.

<a id="user_config.UserConfigManager.update_setting"></a>

#### update\_setting

```python
def update_setting(category: str, setting: str, value: Any)
```

Update a specific setting value.

<a id="user_config.UserConfigManager.export_config"></a>

#### export\_config

```python
def export_config() -> Dict[str, Any]
```

Export current configuration as a dictionary.

<a id="user_config.UserConfigManager.save_user_config"></a>

#### save\_user\_config

```python
def save_user_config(file_path: Optional[str] = None)
```

Save current configuration to a user config file.

<a id="user_config.UserConfigManager.get_environment_variables"></a>

#### get\_environment\_variables

```python
def get_environment_variables() -> Dict[str, str]
```

Get environment variable names and their current values.

<a id="user_config.get_user_config"></a>

#### get\_user\_config

```python
def get_user_config() -> UserConfigManager
```

Get the global user configuration manager instance.

<a id="user_config.reset_user_config"></a>

#### reset\_user\_config

```python
def reset_user_config()
```

Reset the global user configuration manager instance.

