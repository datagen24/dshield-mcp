# Architecture Guide

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      MCP Clients                             │
│          (Claude, Other MCP-Compatible Tools)               │
└────────────────────────┬────────────────────────────────────┘
                         │ JSON-RPC 2.0 Protocol
┌────────────────────────▼────────────────────────────────────┐
│                   DShieldMCPServer                           │
│  (mcp_server.py - Main orchestration & request routing)     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────┐      ┌────────────────────────┐  │
│  │   Tool Dispatcher    │      │  Feature Manager       │  │
│  │  (dispatcher.py)     │      │  (feature_manager.py)  │  │
│  │  - Route tool calls  │      │  - Track features      │  │
│  │  - Execute handlers  │      │  - Check dependencies  │  │
│  │  - Timeout handling  │      │  - Status monitoring   │  │
│  └──────┬───────────────┘      └────────────┬───────────┘  │
│         │                                    │              │
│  ┌──────▼──────────────────────────────────▼───────────┐  │
│  │     MCP Tools (src/mcp_tools/tools/)                │  │
│  │  - query_dshield_events                             │  │
│  │  - stream_dshield_events_with_session_context       │  │
│  │  - analyze_campaign                                 │  │
│  │  - expand_campaign_indicators                       │  │
│  │  - get_campaign_timeline                            │  │
│  │  - generate_attack_report                           │  │
│  │  - get_data_dictionary                              │  │
│  │  - detect_statistical_anomalies                     │  │
│  │  - get_health_status                                │  │
│  └──────┬──────────────────────────────────────────────┘  │
│         │                                                  │
├────────┼──────────────────────────────────────────────────┤
│         │                                                  │
│  ┌──────▼─────────────┐  ┌────────────────────────────┐  │
│  │ Data Layer         │  │ Intelligence Layer         │  │
│  │ ───────────────────┤  │ ──────────────────────────│  │
│  │ • ElasticsearchC.  │  │ • CampaignAnalyzer        │  │
│  │ • DataProcessor    │  │ • ThreatIntelligenceM.    │  │
│  │ • DataDictionary   │  │ • StatisticalAnalysis     │  │
│  │ • DShieldClient    │  │ • CampaignMCPTools        │  │
│  └────────────────────┘  └────────────────────────────┘  │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │         Error & Security Layer                       │  │
│  │  • MCPErrorHandler (error responses & circuit break) │  │
│  │  • Security validators & rate limiters               │  │
│  │  • Configuration management                         │  │
│  └──────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼────────┐  ┌───▼──────────┐  ┌─▼───────────────┐
│  Elasticsearch │  │ DShield API  │  │ Configuration   │
│  (SIEM Data)   │  │ (Threat TI)  │  │ (YAML + 1Pass)  │
└────────────────┘  └──────────────┘  └─────────────────┘
```

## Core Components

### DShieldMCPServer

Central orchestration point for the entire system:
- Initializes all components (Elasticsearch client, DShield client, analyzers)
- Registers MCP protocol handlers (tools, resources, prompts)
- Manages tool loading via dispatcher
- Uses **Facade pattern** to hide complexity

**Location**: `mcp_server.py` (500+ lines)

### Tool System

- `base.py`: Tool categories, definitions, and base classes
- `dispatcher.py`: Routes tool calls to handlers with timeout management
- Individual tool files: Each tool has its own definition file
- Uses **Strategy pattern** for tool execution

**Location**: `src/mcp_tools/tools/`

### ElasticsearchClient

Unified interface for all SIEM queries:
- Supports multiple index patterns: Cowrie honeypot, Zeek network data, DShield-specific indices
- Query optimization for large result sets
- Pagination (offset and cursor-based)
- Circuit breaker integration

**Location**: `src/elasticsearch_client.py` (1200+ lines)

### Campaign Analysis System

- `campaign_analyzer.py` (1000+ lines): Core correlation engine with 7 correlation methods
- `campaign_mcp_tools.py`: High-level campaign tools wrapping the analyzer
- Campaign confidence scoring (Low, Medium, High, Critical)
- Event grouping and indicator relationship tracking

### Threat Intelligence

- `dshield_client.py` (350+ lines): DShield API client for IP reputation and attack data
- `threat_intelligence_manager.py` (1600+ lines): Multi-source threat intelligence aggregation
- `statistical_analysis_tools.py`: Zscore-based anomaly detection

### Error Handling & Resilience

- `mcp_error_handler.py` (900+ lines): JSON-RPC 2.0 compliant error handling
- Circuit breaker implementation (CLOSED, OPEN, HALF_OPEN states)
- Timeout handling and retry logic with exponential backoff
- Error aggregation and rate limiting

### Feature Management

**Location**: `src/feature_manager.py` (300+ lines)

- Graceful degradation when dependencies fail
- Maps tools to required dependencies
- Health checks determine feature availability
- Tools listed only if dependencies are healthy

## Design Patterns & Principles

### Patterns Used

1. **Facade**: `DShieldMCPServer` as single entry point
2. **Strategy**: `ToolDispatcher` and multiple correlation methods
3. **Factory**: Dynamic tool creation and registration
4. **Circuit Breaker**: `MCPErrorHandler` protects against cascading failures
5. **Dependency Injection**: Services accept optional handlers for loose coupling
6. **Observer**: `FeatureManager` monitors health status
7. **Async/Await**: All I/O operations are async with proper timeout handling

### Architectural Principles

- **Separation of Concerns**: Each module has single responsibility
- **Graceful Degradation**: Features disabled when dependencies fail
- **Security First**: All secrets resolved from 1Password, never in config
- **Testability**: Heavy use of dependency injection and mocking
- **Observability**: Structured logging with `structlog`

## Key Data Flows

### Query Flow

```
Client Request
  ↓
MCP Server (validate & route)
  ↓
Tool Dispatcher (timeout & execute)
  ↓
Handler Method (e.g., _query_dshield_events)
  ↓
Elasticsearch Client (build query & execute)
  ↓
DataProcessor (normalize & enrich)
  ↓
JSON-RPC Response
```

### Campaign Analysis Flow

```
Client Request (analyze_campaign)
  ↓
MCP Server Handler
  ↓
CampaignAnalyzer (correlate via 7 methods)
  ├─ IP correlation
  ├─ Behavioral patterns
  ├─ Temporal relationships
  └─ Calculate confidence
  ↓
DShield Client (enrich IPs)
  ↓
Campaign Object (events + relationships + score)
  ↓
JSON-RPC Response
```

## Extension Points

### Adding New Tools

1. Create tool definition file in `src/mcp_tools/tools/your_tool.py`
2. Inherit from `BaseTool` class
3. Define `ToolDefinition` with JSON schema
4. Register handler in `mcp_server.py` via `_register_tool_handlers()`
5. Implement handler method with tool execution logic
6. Add tests in `tests/mcp/tools/`

### Adding New Data Sources

1. Create client class (e.g., `NewSourceClient`)
2. Implement async methods for data retrieval
3. Add index patterns to `mcp_config.yaml` if Elasticsearch-based
4. Integrate with `DataProcessor` for normalization
5. Create corresponding MCP tools to expose functionality

### Adding New Analysis Methods

1. Create analyzer class in appropriate module
2. Implement analysis methods with proper error handling
3. Create corresponding MCP tools
4. Add feature dependency tracking in `feature_manager.py`
5. Add comprehensive tests with mocked dependencies
