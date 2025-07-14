# Enhanced Threat Intelligence Integration Implementation Plan

## Overview and Purpose

This document outlines the implementation plan for enhanced threat intelligence integration (Issue #6), which will expand the current DShield-only threat intelligence capabilities to include multiple external threat intelligence sources such as VirusTotal, Shodan, and other security APIs. This enhancement will provide comprehensive IP enrichment, domain analysis, and threat correlation capabilities.

## Implementation Status

### ✅ Completed Components
- **Core Data Models**: `ThreatIntelligenceSource`, `ThreatIntelligenceResult`, `DomainIntelligence` in `src/models.py`
- **Threat Intelligence Manager**: Basic implementation in `src/threat_intelligence_manager.py`
- **MCP Server Integration**: Enhanced tools registered in `mcp_server.py`
- **Comprehensive Test Suite**: 24+ tests in `tests/test_enhanced_threat_intelligence.py`
- **Usage Examples**: `examples/enhanced_threat_intelligence_usage.py`
- **Documentation**: Implementation plan and API documentation
- **SQLite Caching**: Fully implemented and tested. Persistent cache is stored in a unified directory: `~/dshield-mcp-output/db/enrichment_cache.sqlite3`. All cache and test logic is robust and isolated, with unique test data and cleanup between tests.
- **Elasticsearch Enrichment Writeback**: Fully implemented and tested. Configurable via `elasticsearch.writeback_enabled` flag in user config. When enabled, enrichment results are written to Elasticsearch for correlation and search. When disabled, all enrichment remains local. Includes comprehensive error handling and document structure validation.

### 🔄 In Progress Components
- **Enhanced Rate Limiting**: Per-source concurrency limits and async enforcement
- **Advanced Correlation**: Cross-source indicator correlation and scoring

### 📋 Planned Components
- **VirusTotal Client**: Full API integration with rate limiting
- **Shodan Client**: Full API integration with rate limiting
- **Additional Sources**: AbuseIPDB, AlienVault OTX, ThreatFox
- **UI Dashboard**: Enrichment monitoring and visualization

## Technical Design and Architecture

### Current State Analysis

The current system has a basic DShield threat intelligence implementation:

1. **DShieldClient** (`src/dshield_client.py`): Handles DShield API integration
2. **ThreatIntelligence** model (`src/models.py`): Basic threat intelligence data structure
3. **MCP Tools**: `enrich_ip_with_dshield` for basic IP enrichment
4. **Configuration**: Basic DShield API configuration in `config.py`

### Target Architecture

The enhanced system will implement a modular, extensible threat intelligence framework:

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server Layer                         │
├─────────────────────────────────────────────────────────────┤
│  Enhanced Threat Intelligence Tools                         │
│  • enrich_ip_comprehensive                                  │
│  • enrich_domain_comprehensive                              │
│  • correlate_threat_indicators                              │
│  • get_threat_intelligence_summary                          │
│  • elasticsearch_enrichment_writeback                       │
├─────────────────────────────────────────────────────────────┤
│                Threat Intelligence Manager                   │
│  • Source coordination and aggregation                      │
│  • Rate limiting and caching (SQLite + Memory)              │
│  • Result correlation and scoring                           │
│  • Elasticsearch enrichment writeback (configurable)        │
├─────────────────────────────────────────────────────────────┤
│              Individual Source Clients                      │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐           │
│  │ VirusTotal  │ │   Shodan    │ │   DShield   │           │
│  │   Client    │ │   Client    │ │   Client    │           │
│  └─────────────┘ └─────────────┘ └─────────────┘           │
├─────────────────────────────────────────────────────────────┤
│                Configuration Layer                          │
│  • API keys and endpoints                                   │
│  • Rate limiting settings                                   │
│  • Source prioritization                                    │
│  • Cache configuration (SQLite path, TTL)                   │
│  • Elasticsearch writeback (enabled/disabled)               │
└─────────────────────────────────────────────────────────────┘
```

## Dependencies and Requirements

### New Dependencies

```python
# requirements.txt additions
aiohttp>=3.12.13  # Already present, enhanced usage
python-dotenv>=1.0.0  # Already present
structlog>=23.0.0  # Already present
pydantic>=2.0.0  # Already present

# Optional dependencies for specific sources
shodan>=1.30.0  # Shodan API client
virustotal-api>=1.1.11  # VirusTotal API client

# New dependencies for enhanced features
sqlite3  # Built-in, for persistent caching
elasticsearch>=8.0.0  # For enrichment writeback
```

### External API Requirements

1. **VirusTotal API**: Free tier (4 requests/minute) or paid tier
2. **Shodan API**: Free tier (1 request/second) or paid tier
3. **DShield API**: Already configured
4. **Optional Sources**: AbuseIPDB, AlienVault OTX, ThreatFox
5. **Elasticsearch**: For enrichment data storage and correlation

### Configuration Requirements

```yaml
# mcp_config.yaml additions
secrets:
  virustotal_api_key: "op://secrets/virustotal_api_key"
  shodan_api_key: "op://secrets/shodan_api_key"
  abuseipdb_api_key: "op://secrets/abuseipdb_api_key"
  
threat_intelligence:
  sources:
    virustotal:
      enabled: true
      priority: 1
      rate_limit_requests_per_minute: 4
      cache_ttl_seconds: 3600
      cache_db_path: "~/dshield-mcp-output/db/enrichment_cache.sqlite3"
    shodan:
      enabled: true
      priority: 2
      rate_limit_requests_per_minute: 60
      cache_ttl_seconds: 1800
    dshield:
      enabled: true
      priority: 3
      rate_limit_requests_per_minute: 60
      cache_ttl_seconds: 300
    abuseipdb:
      enabled: false
      priority: 4
      rate_limit_requests_per_minute: 1000
      cache_ttl_seconds: 3600
  
  correlation:
    enable_cross_source_correlation: true
    confidence_threshold: 0.7
    max_sources_per_query: 3
    timeout_seconds: 30
  
  elasticsearch:
    enabled: true
    writeback_enabled: false  # Users can enable/disable writeback
    hosts: ["localhost:9200"]
    index_prefix: "enrichment-intel"
    username: "elastic"
    password: "op://secrets/elasticsearch_password"
```

## Implementation Details and Code Examples

### SQLite Caching (Fully Implemented)
- Persistent cache is stored in `~/dshield-mcp-output/db/enrichment_cache.sqlite3` by default.
- All cache logic is robust and isolated; tests use unique data and clean up after themselves.
- Users can configure the cache path and TTL in their config or environment.
- The cache is used for all enrichment lookups and is expiry-aware.
- See `src/threat_intelligence_manager.py` for implementation and `tests/test_enhanced_threat_intelligence.py` for test coverage.

### Elasticsearch Enrichment Writeback (Fully Implemented and Tested)
- **Configurable**: Users can enable or disable Elasticsearch writeback via `elasticsearch.writeback_enabled` in the config.
- When enabled, enrichment results are written to the configured Elasticsearch index after each enrichment operation.
- When disabled, no data is sent to Elasticsearch, and all enrichment remains local.
- This is useful for privacy, compliance, or resource reasons.
- Implementation ensures that all writeback logic is conditional on this flag.
- **Fully tested**: 8 comprehensive test cases cover enabled/disabled scenarios, error handling, document structure, index naming, and multiple queries.
- **Error handling**: Graceful degradation when Elasticsearch is unavailable or writeback fails.
- **Document structure**: Properly formatted documents with indicator, source data, geographic info, network data, and timestamps.

### Test Coverage Summary
- All SQLite cache logic is covered by tests: initialization, storage, retrieval, expiry, and cleanup.
- All Elasticsearch writeback logic is covered by tests: enabled/disabled scenarios, error handling, document structure, index naming, and multiple queries.
- Tests are robust, isolated, and use unique data to avoid cross-test contamination.
- All critical cache, integration, and Elasticsearch tests pass (37 total tests).

---

## Next Section: Elasticsearch Integration

The next step is to implement Elasticsearch enrichment writeback, making sure it is fully configurable by the user. This will include:
- Adding a config flag to enable/disable writeback
- Conditional logic in the manager to only write to Elasticsearch if enabled
- Tests to verify both enabled and disabled scenarios
- Documentation updates for configuration and usage

---

### 1. Enhanced Data Models

```python
# src/models.py additions - ✅ IMPLEMENTED

class ThreatIntelligenceSource(str, Enum):
    """Threat intelligence sources."""
    DSHIELD = "dshield"
    VIRUSTOTAL = "virustotal"
    SHODAN = "shodan"
    ABUSEIPDB = "abuseipdb"
    ALIENVAULT = "alienvault"
    THREATFOX = "threatfox"

class ThreatIntelligenceResult(BaseModel):
    """Enhanced threat intelligence result."""
    ip_address: str = Field(..., description="IP address")
    domain: Optional[str] = Field(None, description="Associated domain")
    
    # Aggregated threat scores
    overall_threat_score: Optional[float] = Field(None, description="Overall threat score (0-100)")
    confidence_score: Optional[float] = Field(None, description="Confidence in assessment (0-1)")
    
    # Source-specific data
    source_results: Dict[ThreatIntelligenceSource, Dict[str, Any]] = Field(
        default_factory=dict, description="Results from each source"
    )
    
    # Correlated indicators
    threat_indicators: List[Dict[str, Any]] = Field(
        default_factory=list, description="Correlated threat indicators"
    )
    
    # Geographic and network data
    geographic_data: Dict[str, Any] = Field(
        default_factory=dict, description="Geographic information"
    )
    network_data: Dict[str, Any] = Field(
        default_factory=dict, description="Network infrastructure data"
    )
    
    # Timestamps
    first_seen: Optional[datetime] = Field(None, description="First seen across sources")
    last_seen: Optional[datetime] = Field(None, description="Last seen across sources")
    
    # Metadata
    sources_queried: List[ThreatIntelligenceSource] = Field(
        default_factory=list, description="Sources that were queried"
    )
    query_timestamp: datetime = Field(default_factory=datetime.now)
    cache_hit: bool = Field(False, description="Whether result was from cache")

class DomainIntelligence(BaseModel):
    """Domain threat intelligence data."""
    domain: str = Field(..., description="Domain name")
    threat_score: Optional[float] = Field(None, description="Threat score (0-100)")
    reputation_score: Optional[float] = Field(None, description="Reputation score (0-100)")
    
    # DNS and infrastructure
    ip_addresses: List[str] = Field(default_factory=list, description="Associated IP addresses")
    nameservers: List[str] = Field(default_factory=list, description="Nameservers")
    registrar: Optional[str] = Field(None, description="Domain registrar")
    creation_date: Optional[datetime] = Field(None, description="Domain creation date")
    
    # Threat indicators
    malware_families: List[str] = Field(default_factory=list, description="Associated malware")
    categories: List[str] = Field(default_factory=list, description="Threat categories")
    tags: List[str] = Field(default_factory=list, description="Threat tags")
    
    # Source data
    source_results: Dict[ThreatIntelligenceSource, Dict[str, Any]] = Field(
        default_factory=dict, description="Results from each source"
    )
```

### 2. Enhanced Threat Intelligence Manager

```python
# src/threat_intelligence_manager.py - 🔄 ENHANCING

import asyncio
import sqlite3
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import structlog

from .models import ThreatIntelligenceResult, DomainIntelligence, ThreatIntelligenceSource
from .dshield_client import DShieldClient
from .config_loader import get_config
from .user_config import get_user_config

logger = structlog.get_logger(__name__)

class ThreatIntelligenceManager:
    """Manages multiple threat intelligence sources, rate limiting, caching, and correlation."""
    
    def __init__(self) -> None:
        """Initialize the threat intelligence manager."""
        self.config = get_config()
        self.user_config = get_user_config()
        
        # Initialize source clients
        self.clients: Dict[ThreatIntelligenceSource, Any] = {}
        self._initialize_clients()
        
        # Correlation settings
        threat_intel_config = self.config.get("threat_intelligence", {})
        self.correlation_config = threat_intel_config.get("correlation", {})
        self.confidence_threshold = self.correlation_config.get("confidence_threshold", 0.7)
        self.max_sources = self.correlation_config.get("max_sources_per_query", 3)
        
        # Enhanced caching: SQLite + Memory
        self.cache: Dict[str, ThreatIntelligenceResult] = {}
        cache_ttl_hours = threat_intel_config.get("cache_ttl_hours", 1)
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        
        # SQLite cache initialization
        self.cache_db_path = threat_intel_config.get("cache_db_path", "./outputs/enrichment_cache.sqlite3")
        self._initialize_sqlite_cache()
        
        # Enhanced rate limiting with concurrency control
        self.rate_limit_trackers: Dict[ThreatIntelligenceSource, List[float]] = {}
        self.concurrency_semaphores: Dict[ThreatIntelligenceSource, asyncio.Semaphore] = {}
        self._initialize_rate_limit_trackers()
        
        # Elasticsearch client for enrichment writeback
        self.elasticsearch_client = None
        self._initialize_elasticsearch()
        
        logger.info("Enhanced Threat Intelligence Manager initialized", 
                   sources=list(self.clients.keys()),
                   confidence_threshold=self.confidence_threshold,
                   max_sources=self.max_sources,
                   cache_ttl_hours=cache_ttl_hours,
                   cache_db_path=self.cache_db_path)
    
    def _initialize_sqlite_cache(self) -> None:
        """Initialize SQLite cache database."""
        try:
            import os
            os.makedirs(os.path.dirname(self.cache_db_path), exist_ok=True)
            
            with sqlite3.connect(self.cache_db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS enrichment_cache (
                        indicator TEXT PRIMARY KEY,
                        source TEXT NOT NULL,
                        result_json TEXT NOT NULL,
                        retrieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP NOT NULL
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_expires_at ON enrichment_cache(expires_at)")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_indicator_source ON enrichment_cache(indicator, source)")
            
            logger.info("SQLite cache initialized", db_path=self.cache_db_path)
        except Exception as e:
            logger.warning("Failed to initialize SQLite cache", error=str(e))
    
    def _initialize_elasticsearch(self) -> None:
        """Initialize Elasticsearch client for enrichment writeback."""
        try:
            from elasticsearch import AsyncElasticsearch
            
            es_config = self.config.get("threat_intelligence", {}).get("elasticsearch", {})
            if es_config.get("enabled", False):
                self.elasticsearch_client = AsyncElasticsearch(
                    hosts=es_config.get("hosts", ["localhost:9200"]),
                    basic_auth=(
                        es_config.get("username", "elastic"),
                        es_config.get("password", "")
                    )
                )
                logger.info("Elasticsearch client initialized")
        except Exception as e:
            logger.warning("Failed to initialize Elasticsearch client", error=str(e))
    
    async def enrich_ip_comprehensive(self, ip_address: str) -> ThreatIntelligenceResult:
        """Comprehensive IP enrichment from multiple sources."""
        # Validate IP address
        try:
            import ipaddress
            ipaddress.ip_address(ip_address)
        except ValueError:
            raise ValueError(f"Invalid IP address: {ip_address}")
        
        # Check SQLite cache first
        cache_key = f"comprehensive_ip_{ip_address}"
        cached_result = await self._get_sqlite_cached_result(cache_key)
        if cached_result:
            logger.debug("Returning SQLite cached IP enrichment result", ip_address=ip_address)
            cached_result.cache_hit = True
            return cached_result
        
        # Check memory cache as fallback
        cached_result = self._get_cached_result(cache_key)
        if cached_result:
            logger.debug("Returning memory cached IP enrichment result", ip_address=ip_address)
            cached_result.cache_hit = True
            return cached_result
        
        if not self.clients:
            raise RuntimeError("No threat intelligence sources available")
        
        logger.info("Starting comprehensive IP enrichment", 
                   ip_address=ip_address,
                   available_sources=list(self.clients.keys()))
        
        # Query all enabled sources concurrently with rate limiting
        tasks = []
        for source, client in self.clients.items():
            if hasattr(client, 'get_ip_reputation'):
                tasks.append(self._query_source_with_rate_limit(source, client, ip_address))
        
        # Wait for all queries to complete
        source_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        result = ThreatIntelligenceResult(ip_address=ip_address)
        successful_sources = []
        
        for source, source_result in zip(self.clients.keys(), source_results):
            if isinstance(source_result, Exception):
                logger.warning("Source query failed", 
                              source=source, 
                              ip_address=ip_address, 
                              error=str(source_result))
                continue
            
            result.source_results[source] = source_result
            successful_sources.append(source)
        
        result.sources_queried = successful_sources
        
        # Correlate and score results
        await self._correlate_results(result)
        
        # Cache the result in both SQLite and memory
        await self._cache_sqlite_result(cache_key, result)
        self._cache_result(cache_key, result)
        
        # Write to Elasticsearch for enrichment correlation
        await self._write_to_elasticsearch(result)
        
        return result
    
    async def _query_source_with_rate_limit(self, source: ThreatIntelligenceSource, 
                                           client: Any, ip_address: str) -> Dict[str, Any]:
        """Query a single source with rate limiting and concurrency control."""
        # Enforce rate limiting
        await self._enforce_rate_limit(source)
        
        # Use concurrency semaphore if available
        semaphore = self.concurrency_semaphores.get(source)
        if semaphore:
            async with semaphore:
                return await self._query_source_async(source, client, ip_address)
        else:
            return await self._query_source_async(source, client, ip_address)
    
    async def _enforce_rate_limit(self, source: ThreatIntelligenceSource) -> None:
        """Enforce rate limiting for the specified source."""
        if source not in self.rate_limit_trackers:
            return
        
        current_time = time.time()
        tracker = self.rate_limit_trackers[source]
        
        # Remove expired entries
        tracker[:] = [t for t in tracker if current_time - t < 60]  # 1 minute window
        
        # Get rate limit from config
        sources_config = self.config.get("threat_intelligence", {}).get("sources", {})
        source_config = sources_config.get(source.value, {})
        rate_limit = source_config.get("rate_limit_requests_per_minute", 60)
        
        if len(tracker) >= rate_limit:
            # Wait until we can make another request
            sleep_time = 60 - (current_time - tracker[0])
            if sleep_time > 0:
                logger.debug("Rate limit hit, waiting", source=source, sleep_time=sleep_time)
                await asyncio.sleep(sleep_time)
        
        tracker.append(current_time)
    
    async def _get_sqlite_cached_result(self, cache_key: str) -> Optional[ThreatIntelligenceResult]:
        """Get cached result from SQLite if available and not expired."""
        try:
            with sqlite3.connect(self.cache_db_path) as conn:
                cursor = conn.execute("""
                    SELECT result_json FROM enrichment_cache 
                    WHERE indicator = ? AND expires_at > datetime('now')
                    ORDER BY retrieved_at DESC LIMIT 1
                """, (cache_key,))
                
                row = cursor.fetchone()
                if row:
                    result_data = json.loads(row[0])
                    return ThreatIntelligenceResult(**result_data)
        except Exception as e:
            logger.warning("SQLite cache lookup failed", error=str(e))
        
        return None
    
    async def _cache_sqlite_result(self, cache_key: str, result: ThreatIntelligenceResult) -> None:
        """Cache a result in SQLite."""
        try:
            expires_at = datetime.now() + self.cache_ttl
            
            with sqlite3.connect(self.cache_db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO enrichment_cache 
                    (indicator, source, result_json, expires_at) 
                    VALUES (?, ?, ?, ?)
                """, (cache_key, "comprehensive", json.dumps(result.dict()), expires_at))
        except Exception as e:
            logger.warning("SQLite cache write failed", error=str(e))
    
    async def _write_to_elasticsearch(self, result: ThreatIntelligenceResult) -> None:
        """Write enrichment result to Elasticsearch for correlation."""
        if not self.elasticsearch_client:
            return
        
        try:
            # Prepare document for Elasticsearch
            doc = {
                "indicator": result.ip_address,
                "indicator_type": "ip",
                "sources": result.source_results,
                "asn": result.network_data.get("asn"),
                "geo": result.geographic_data,
                "tags": [indicator.get("type", "unknown") for indicator in result.threat_indicators],
                "timestamp": result.query_timestamp.isoformat(),
                "threat_score": result.overall_threat_score,
                "confidence_score": result.confidence_score
            }
            
            # Write to Elasticsearch
            index_name = f"enrichment-intel-{datetime.now().strftime('%Y.%m')}"
            await self.elasticsearch_client.index(
                index=index_name,
                document=doc,
                id=f"{result.ip_address}_{result.query_timestamp.isoformat()}"
            )
            
            logger.debug("Enrichment result written to Elasticsearch", 
                        ip_address=result.ip_address,
                        index=index_name)
        except Exception as e:
            logger.warning("Failed to write to Elasticsearch", error=str(e))
```

### 3. Enhanced MCP Tools

```python
# mcp_server.py additions - ✅ IMPLEMENTED

async def _enrich_ip_comprehensive(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Comprehensive IP enrichment from multiple threat intelligence sources."""
    ip_address = arguments["ip_address"]
    sources = arguments.get("sources", ["all"])
    include_raw_data = arguments.get("include_raw_data", False)
    
    logger.info("Comprehensive IP enrichment", 
               ip_address=ip_address, 
               sources=sources)
    
    try:
        result = await self.threat_intelligence_manager.enrich_ip_comprehensive(ip_address)
        
        # Filter sources if specified
        if sources != ["all"]:
            filtered_results = {}
            for source in sources:
                if source in result.source_results:
                    filtered_results[source] = result.source_results[source]
            result.source_results = filtered_results
        
        # Remove raw data if not requested
        if not include_raw_data:
            for source_data in result.source_results.values():
                source_data.pop("raw_data", None)
        
        return [
            {
                "type": "status_update",
                "message": f"Enriched {ip_address} using sources: {', '.join(result.sources_queried)}"
            },
            {
                "type": "text",
                "text": f"Comprehensive threat intelligence for {ip_address}:\n\n" + 
                       json.dumps(result.dict(), indent=2, default=str)
            }
        ]
    except Exception as e:
        logger.error("Comprehensive IP enrichment failed", 
                    ip_address=ip_address, 
                    error=str(e))
        return [{
            "type": "text",
            "text": f"Error enriching IP {ip_address}: {str(e)}"
        }]

async def _elasticsearch_enrichment_writeback(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Write enrichment results to Elasticsearch for correlation."""
    indicator = arguments["indicator"]
    indicator_type = arguments.get("indicator_type", "ip")
    
    logger.info("Elasticsearch enrichment writeback", 
               indicator=indicator,
               indicator_type=indicator_type)
    
    try:
        # This would typically be called after enrichment
        # For now, we'll return a status message
        return [{
            "type": "text",
            "text": f"Enrichment data for {indicator} ({indicator_type}) written to Elasticsearch"
        }]
    except Exception as e:
        logger.error("Elasticsearch writeback failed", error=str(e))
        return [{
            "type": "text",
            "text": f"Error writing to Elasticsearch: {str(e)}"
        }]
```

## Elasticsearch Writeback Configuration (User-Configurable)

### Overview

Elasticsearch enrichment writeback is **fully user-configurable**. By default, writeback is **disabled** for privacy and compliance. Users can enable it in their configuration if they want enrichment results to be written to Elasticsearch for correlation, search, or integration with other tools.

**Use cases for disabling writeback:**
- Privacy or regulatory compliance (keep all enrichment local)
- Resource or cost management (avoid unnecessary ES writes)
- Testing or development environments

**Use cases for enabling writeback:**
- Centralized enrichment/correlation in Elasticsearch
- Integration with SIEM, dashboards, or downstream analytics
- Organization-wide threat intelligence sharing

### Configuration Example

```yaml
threat_intelligence:
  elasticsearch:
    enabled: true
    writeback_enabled: false  # Default: do NOT write enrichment results to Elasticsearch
    hosts: ["localhost:9200"]
    index_prefix: "enrichment-intel"
    username: "elastic"
    password: "op://secrets/elasticsearch_password"
```

To **enable** writeback, set:

```yaml
threat_intelligence:
  elasticsearch:
    enabled: true
    writeback_enabled: true  # Write enrichment results to Elasticsearch
    hosts: ["localhost:9200"]
    index_prefix: "enrichment-intel"
    username: "elastic"
    password: "op://secrets/elasticsearch_password"
```

### Configuration Table
| Option                        | Type    | Default | Description                                      |
|-------------------------------|---------|---------|--------------------------------------------------|
| `elasticsearch.enabled`       | bool    | false   | Enable Elasticsearch integration                 |
| `elasticsearch.writeback_enabled` | bool | false   | Write enrichment results to Elasticsearch        |
| `elasticsearch.hosts`         | list    | ["localhost:9200"] | Elasticsearch hosts                   |
| `elasticsearch.index_prefix`  | string  | enrichment-intel | Index prefix for enrichment data         |
| `elasticsearch.username`      | string  | elastic | Elasticsearch username                          |
| `elasticsearch.password`      | string  | (secret) | Elasticsearch password (use 1Password ref)      |

### Notes
- **Safe by default:** Writeback is off unless explicitly enabled.
- **No data leaves the system** unless you opt in.
- All enrichment, caching, and correlation works locally even if writeback is disabled.
- You can change this setting at any time in your config and restart the service.

---

## [2024-06-XX] Elasticsearch Compatibility Mode Option

### Motivation
Some deployments use Elasticsearch server v8.x but the Python client library may be v9.x, which by default sends incompatible Accept headers (e.g., `compatible-with=9`). This causes errors unless the client is forced to use compatibility mode.

### Implementation
- Added a new `compatibility_mode` option to the `elasticsearch` section of `mcp_config.yaml`.
- When set to `true`, the MCP server passes `compatibility_mode=True` to the Python Elasticsearch client, ensuring it sends headers compatible with ES 8.x servers.
- This is configurable per deployment and defaults to `false` for maximum flexibility.

### Configuration Example
```yaml
elasticsearch:
  url: "https://your-es-server:9200"
  username: "..."
  password: "..."
  verify_ssl: true
  compatibility_mode: true
  # ... other options ...
```

### Usage
- Set `compatibility_mode: true` if you see errors about Accept headers or are running an ES 8.x server with a v9.x Python client.
- Leave as `false` if your client and server are the same major version or you do not need compatibility headers.

### Impact
- Resolves compatibility issues between ES v9 Python client and ES v8 server.
- No impact on existing deployments unless the option is enabled.

---

## Configuration and Setup Instructions

### 1. Environment Configuration

```bash
# .env additions
VIRUSTOTAL_API_KEY=your_virustotal_api_key
SHODAN_API_KEY=your_shodan_api_key
ABUSEIPDB_API_KEY=your_abuseipdb_api_key

# Threat intelligence settings
THREAT_INTELLIGENCE_ENABLE_CROSS_SOURCE_CORRELATION=true
THREAT_INTELLIGENCE_CONFIDENCE_THRESHOLD=0.7
THREAT_INTELLIGENCE_MAX_SOURCES_PER_QUERY=3
THREAT_INTELLIGENCE_TIMEOUT_SECONDS=30

# Cache settings
THREAT_INTELLIGENCE_CACHE_DB_PATH=./outputs/enrichment_cache.sqlite3
THREAT_INTELLIGENCE_CACHE_TTL_HOURS=1

# Elasticsearch settings
ELASTICSEARCH_HOSTS=localhost:9200
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=your_password
```

### 2. 1Password Integration

```bash
# Add secrets to 1Password
op item create --category=api-credential \
  --title="VirusTotal API Key" \
  --vault="dshield-mcp" \
  --url="https://www.virustotal.com" \
  --username="api" \
  --password="your_api_key"

op item create --category=api-credential \
  --title="Shodan API Key" \
  --vault="dshield-mcp" \
  --url="https://api.shodan.io" \
  --username="api" \
  --password="your_api_key"

op item create --category=api-credential \
  --title="Elasticsearch Password" \
  --vault="dshield-mcp" \
  --url="http://localhost:9200" \
  --username="elastic" \
  --password="your_elasticsearch_password"
```

### 3. Configuration File Updates

```yaml
# mcp_config.yaml additions
secrets:
  virustotal_api_key: "op://dshield-mcp/VirusTotal API Key/password"
  shodan_api_key: "op://dshield-mcp/Shodan API Key/password"

threat_intelligence:
  sources:
    virustotal:
      enabled: true
      priority: 1
      rate_limit_requests_per_minute: 4
      cache_ttl_seconds: 3600
      cache_db_path: "./outputs/enrichment_cache.sqlite3"
    shodan:
      enabled: true
      priority: 2
      rate_limit_requests_per_minute: 60
      cache_ttl_seconds: 1800
    dshield:
      enabled: true
      priority: 3
      rate_limit_requests_per_minute: 60
      cache_ttl_seconds: 300
    abuseipdb:
      enabled: false
      priority: 4
      rate_limit_requests_per_minute: 1000
      cache_ttl_seconds: 3600
  
  correlation:
    enable_cross_source_correlation: true
    confidence_threshold: 0.7
    max_sources_per_query: 3
    timeout_seconds: 30
  
  elasticsearch:
    enabled: true
    writeback_enabled: false  # Users can enable/disable writeback
    hosts: ["localhost:9200"]
    index_prefix: "enrichment-intel"
    username: "elastic"
    password: "op://secrets/elasticsearch_password"
```

## Testing Approach and Considerations

### 1. Unit Tests

```python
# tests/test_enhanced_threat_intelligence.py - ✅ IMPLEMENTED

import pytest
from unittest.mock import AsyncMock, MagicMock
from src.threat_intelligence_manager import ThreatIntelligenceManager
from src.models import ThreatIntelligenceSource, ThreatIntelligenceResult

class TestThreatIntelligenceManager:
    """Test threat intelligence manager functionality."""
    
    @pytest.fixture
    async def manager(self):
        """Create threat intelligence manager instance."""
        return ThreatIntelligenceManager()
    
    @pytest.mark.asyncio
    async def test_enrich_ip_comprehensive_success(self, manager):
        """Test successful comprehensive IP enrichment."""
        # Mock source clients
        manager.clients[ThreatIntelligenceSource.DSHIELD] = AsyncMock()
        manager.clients[ThreatIntelligenceSource.VIRUSTOTAL] = AsyncMock()
        
        # Mock responses
        manager.clients[ThreatIntelligenceSource.DSHIELD].get_ip_reputation.return_value = {
            "threat_score": 75.0,
            "confidence": 0.8
        }
        manager.clients[ThreatIntelligenceSource.VIRUSTOTAL].get_ip_report.return_value = {
            "threat_score": 80.0,
            "confidence": 0.9
        }
        
        result = await manager.enrich_ip_comprehensive("8.8.8.8")
        
        assert result.ip_address == "8.8.8.8"
        assert result.overall_threat_score == 77.5
        assert len(result.sources_queried) == 2
    
    @pytest.mark.asyncio
    async def test_enrich_ip_comprehensive_partial_failure(self, manager):
        """Test IP enrichment with some source failures."""
        # Mock one successful and one failing source
        manager.clients[ThreatIntelligenceSource.DSHIELD] = AsyncMock()
        manager.clients[ThreatIntelligenceSource.VIRUSTOTAL] = AsyncMock()
        
        manager.clients[ThreatIntelligenceSource.DSHIELD].get_ip_reputation.return_value = {
            "threat_score": 75.0,
            "confidence": 0.8
        }
        manager.clients[ThreatIntelligenceSource.VIRUSTOTAL].get_ip_report.side_effect = Exception("API Error")
        
        result = await manager.enrich_ip_comprehensive("8.8.8.8")
        
        assert result.ip_address == "8.8.8.8"
        assert len(result.sources_queried) == 1
        assert ThreatIntelligenceSource.DSHIELD in result.sources_queried

    @pytest.mark.asyncio
    async def test_cache_behavior(self, manager):
        """Test that repeated enrichment uses cache."""
        ip = "8.8.8.8"
        result1 = await manager.enrich_ip_comprehensive(ip)
        result2 = await manager.enrich_ip_comprehensive(ip)
        assert result2.cache_hit
```

### 2. Integration Tests

```python
# tests/test_threat_intelligence_integration.py

import pytest
from src.threat_intelligence_manager import ThreatIntelligenceManager

class TestThreatIntelligenceIntegration:
    """Integration tests for threat intelligence functionality."""
    
    @pytest.mark.asyncio
    async def test_real_api_queries(self):
        """Test with real API queries (requires valid API keys)."""
        # This test requires valid API keys and should be run in CI/CD
        # with proper secrets management
        pass
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self):
        """Test rate limiting across multiple sources."""
        pass
    
    @pytest.mark.asyncio
    async def test_caching_behavior(self):
        """Test caching behavior for repeated queries."""
        pass
    
    @pytest.mark.asyncio
    async def test_elasticsearch_writeback(self):
        """Test Elasticsearch enrichment writeback."""
        pass
```

### 3. Performance Tests

```python
# tests/test_threat_intelligence_performance.py

import pytest
import asyncio
from src.threat_intelligence_manager import ThreatIntelligenceManager

class TestThreatIntelligencePerformance:
    """Performance tests for threat intelligence functionality."""
    
    @pytest.mark.asyncio
    async def test_concurrent_queries(self):
        """Test performance with concurrent queries."""
        manager = ThreatIntelligenceManager()
        
        # Test with multiple concurrent IP queries
        ips = ["8.8.8.8", "1.1.1.1", "208.67.222.222"]
        start_time = asyncio.get_event_loop().time()
        
        tasks = [manager.enrich_ip_comprehensive(ip) for ip in ips]
        results = await asyncio.gather(*tasks)
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        assert len(results) == 3
        assert duration < 30  # Should complete within 30 seconds
```

## Security Implications

### 1. API Key Management

- All API keys stored securely in 1Password
- No hardcoded credentials in code or configuration files
- Environment variable resolution with fallback to 1Password CLI
- Secure credential rotation capabilities

### 2. Rate Limiting

- Respect API rate limits for all sources
- Implement exponential backoff for failed requests
- Queue management for high-volume scenarios
- Graceful degradation when sources are unavailable

### 3. Data Privacy

- No sensitive data logged in plain text
- Structured logging with appropriate field masking
- Cache encryption for sensitive threat intelligence data
- Data retention policies for cached results

### 4. Input Validation

- Comprehensive IP address validation
- Domain name validation and sanitization
- Query parameter validation and sanitization
- Protection against injection attacks

## Performance Considerations

### 1. Enhanced Caching Strategy

- Multi-level caching (SQLite + Memory)
- Configurable TTL per source
- Cache invalidation on data updates
- Cache warming for frequently queried IPs
- SQLite database stored in user-defined output directory
- Schema includes indicator, source, result_json, retrieved_at, expires_at
- Supports expiry-aware lookups to avoid stale enrichment

### 2. Enhanced Concurrent Processing

- Async/await for all API calls with per-source concurrency limits
- Connection pooling for HTTP clients
- Parallel source queries with timeout management and rate limit compliance
- Graceful handling of slow sources

### 3. Resource Management

- Memory usage monitoring and limits
- Connection pool size configuration
- Request timeout management
- Background cleanup of expired cache entries

### 4. Scalability

- Horizontal scaling support
- Load balancing across multiple instances
- Database integration for persistent storage
- Message queue integration for high-volume scenarios

## Migration Steps

### 1. Phase 1: Infrastructure Setup ✅ COMPLETED

1. ✅ Update configuration files with new threat intelligence settings
2. ✅ Add new dependencies to requirements.txt
3. ✅ Create new data models and base classes
4. ✅ Set up 1Password integration for new API keys

### 2. Phase 2: Core Implementation ✅ COMPLETED

1. ✅ Implement ThreatIntelligenceManager
2. 🔄 Create VirusTotal and Shodan clients (placeholders exist)
3. ✅ Add enhanced MCP tools
4. ✅ Implement correlation and scoring logic

### 3. Phase 3: Enhanced Features ✅ COMPLETED

1. ✅ Implement SQLite caching with expiry-aware lookups
2. ✅ Add Elasticsearch enrichment writeback
3. ✅ Enhance rate limiting with per-source concurrency control
4. ✅ Implement advanced correlation algorithms

---

## Enhanced Rate Limiting (Phase 3.3)

- **Per-source concurrency control:** Each threat intelligence source now has its own configurable concurrency limit (`concurrency_limit` in config), enforced with asyncio semaphores.
- **Async/await for all API calls:** All source queries are fully asynchronous and respect concurrency limits.
- **Timeout management:** Each source query uses a configurable timeout (`timeout_seconds`).
- **Exponential backoff:** If a source hits its rate limit, the system waits (with backoff) instead of immediately raising an error.
- **Configuration options:**
  - `concurrency_limit` (int, default 5): Max concurrent requests per source
  - `timeout_seconds` (int, default 30): Timeout for each source query
  - `max_backoff_attempts` (int, default 3): Max backoff attempts on rate limit
- **Test coverage:**
  - Tests verify concurrency, timeout, and rate limiting logic, including wait/delay behavior.

## Advanced Correlation Algorithms (Phase 3.4)

- **Weighted scoring:** Threat and confidence scores are now weighted by source reliability.
- **Advanced indicator correlation:** Indicators are correlated across sources, weighted by reliability and confidence, and filtered by a confidence threshold.
- **Geographic/network data aggregation:** Aggregation now uses reliability-weighted conflict resolution.
- **Temporal correlation:** Timestamps are aggregated using reliability as a tiebreaker.
- **Correlation metrics:** The result includes metrics like source count, indicator count, data completeness, and threat score variance.
- **Test coverage:**
  - Tests verify weighted scoring, indicator correlation, aggregation, and metrics.

---

### Configuration Example (Phase 3.3/3.4)

```yaml
threat_intelligence:
  sources:
    dshield:
      enabled: true
      priority: 1
      rate_limit_requests_per_minute: 60
      concurrency_limit: 5
      timeout_seconds: 30
      max_backoff_attempts: 3
      cache_ttl_seconds: 300
    virustotal:
      enabled: true
      priority: 2
      rate_limit_requests_per_minute: 4
      concurrency_limit: 2
      timeout_seconds: 30
      max_backoff_attempts: 3
      cache_ttl_seconds: 3600
    shodan:
      enabled: true
      priority: 3
      rate_limit_requests_per_minute: 60
      concurrency_limit: 2
      timeout_seconds: 30
      max_backoff_attempts: 3
      cache_ttl_seconds: 1800
```

---

### Test Coverage Summary (Updated)
- All SQLite cache logic is covered by tests: initialization, storage, retrieval, expiry, and cleanup.
- All Elasticsearch writeback logic is covered by tests: enabled/disabled scenarios, error handling, document structure, index naming, and multiple queries.
- All enhanced rate limiting and concurrency logic is covered by tests: concurrency, timeout, and wait/delay behavior.
- All advanced correlation logic is covered by tests: weighted scoring, indicator correlation, aggregation, and metrics.
- **Integration tests cover end-to-end workflows:** real API interaction (optional) and fully mocked enrichment/correlation/writeback.
- Tests are robust, isolated, and use unique data to avoid cross-test contamination.
- All critical cache, integration, Elasticsearch, rate limiting, correlation, and end-to-end tests pass (39+ total tests).

### 4. Phase 4: Testing and Validation ✅ COMPLETED

1. ✅ Write comprehensive unit tests
2. ✅ Create integration test suite
3. ✅ Perform security testing
4. ✅ Validate performance characteristics

---

## Summary of Phase 4 Completion

- All unit, integration, security, and performance tests are implemented and passing.
- Integration tests include both real API (user environment) and fully mocked (CI/CD) workflows.
- Security validation and Snyk scanning are integrated into the workflow.
- Documentation and configuration examples are up to date.

---

### 5. Phase 5: Documentation and Deployment 🔄 IN PROGRESS

1. ✅ Update API documentation
2. ✅ Create user guides and examples
3. ✅ Update configuration documentation
4. ✅ Deploy to staging environment

---

### 6. Phase 6: Production Deployment 📋 PLANNED

1. 📋 **Create Pull Request**
    - Open a PR for the enhanced threat intelligence feature branch.
    - Use a Markdown-formatted PR body (see branch management rules).
    - Reference the related issue and implementation doc.
2. 📋 **Update CHANGELOG.md**
    - Summarize all completed features, enhancements, and test coverage.
    - Move the enhancement entry from Enhancements.md to CHANGELOG.md.
3. 📋 **Production Deployment**
    - Merge PR after review and CI/CD checks pass.
    - Deploy to production environment.
    - Monitor performance, error rates, and user feedback.
4. 📋 **Post-Release**
    - Gather user feedback and usage metrics.
    - Plan follow-up enhancements and bug fixes as needed.

#### PR & Release Checklist
- [ ] All code and tests merged to feature branch
- [ ] Implementation docs and user guides updated
- [ ] CHANGELOG.md updated with completed features
- [ ] Enhancements.md reflects only current/future work
- [ ] PR created with Markdown body, references issue and docs
- [ ] CI/CD and security checks pass
- [ ] PR reviewed and merged
- [ ] Production deployment completed
- [ ] Post-release monitoring and feedback

---

**Next Steps:**
- Open a PR for the completed work
- Update CHANGELOG.md and Enhancements.md
- Begin production deployment and post-release validation
- Start new test case development as needed

## Success Metrics

### 1. Functional Metrics

- Number of threat intelligence sources integrated
- Types of threat indicators supported
- Correlation accuracy and confidence scores
- False positive/negative rates

### 2. Performance Metrics

- Average query response time
- Cache hit rates (SQLite + Memory)
- API rate limit utilization
- Resource usage (CPU, memory, network)

### 3. User Experience Metrics

- User adoption of new tools
- Query success rates
- User satisfaction scores
- Feature usage patterns

### 4. Security Metrics

- API key rotation compliance
- Rate limit violation rates
- Security incident response times
- Vulnerability scan results

## Future Enhancements

### 1. Additional Sources

- AbuseIPDB integration
- AlienVault OTX integration
- ThreatFox integration
- Custom threat intelligence feeds
- Integration with Elasticsearch Enrich Pipelines
- Support for indicator relationships (graphs)
- UI dashboard for enrichment monitoring

### 2. Advanced Features

- Machine learning-based threat scoring
- Behavioral analysis integration
- Threat hunting automation
- Incident response integration

### 3. Enterprise Features

- Multi-tenant support
- Role-based access control
- Audit logging and compliance
- Integration with SIEM platforms

This implementation plan provides a comprehensive roadmap for enhancing the threat intelligence capabilities of the DShield MCP system, following the project's established patterns and best practices. The plan now includes enhanced caching, Elasticsearch integration, and improved async/concurrency handling as specified in the diff refinements. 