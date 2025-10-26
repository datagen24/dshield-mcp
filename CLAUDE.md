# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

DShield MCP is a Model Context Protocol (MCP) server that integrates DShield threat intelligence and Elasticsearch SIEM capabilities. It bridges AI assistants with DShield's threat data, enabling intelligent analysis of security threats and attack campaigns.

**Current Focus**: Refactoring project (issue #113) aimed at reducing MCP server complexity through improved separation of concerns and modular design patterns.

---

## Common Development Commands

### Environment Setup
```bash
# Install UV package manager first (if not installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Install development dependencies
uv sync --group dev

# Copy environment template
cp .env.example .env
```

### Running the Application
```bash
# Run MCP server (STDIO mode - default)
uv run python mcp_server.py

# Run TUI interface
uv run python -m src.tui_launcher

# Run TCP server
uv run python -m src.server_launcher --transport tcp

# Run examples
uv run python examples/basic_usage.py
```

### Testing
```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/mcp/test_mcp_server_refactored.py

# Run tests by marker
uv run pytest -m unit          # Unit tests only
uv run pytest -m integration   # Integration tests only
uv run pytest -m "not slow"    # Exclude slow tests

# Run single test
uv run pytest tests/mcp/test_mcp_server_refactored.py::test_server_initialization -v
```

### Code Quality
```bash
# Linting with Ruff
uv run ruff check .
uv run ruff check --fix .

# Formatting with Ruff
uv run ruff format .

# Type checking with mypy
uv run mypy src/

# Security scanning
snyk test
snyk code test
```

### Documentation
```bash
# Generate API documentation
./scripts/build_api_docs.sh

# Or manually with pdoc
uv run pdoc --html --output-dir docs/api src/
```

### Debugging
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
uv run python mcp_server.py

# Test Elasticsearch connection
cd dev_tools && python debug_elasticsearch.py

# Test 1Password integration
cd dev_tools && python test_op_integration.py
```

---

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
│  │     MCP Tools (src/mcp/tools/)                      │  │
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

### Core Components

**DShieldMCPServer** (`mcp_server.py`, 500+ lines):
- Central orchestration point for the entire system
- Initializes all components (Elasticsearch client, DShield client, analyzers)
- Registers MCP protocol handlers (tools, resources, prompts)
- Manages tool loading via dispatcher
- Uses **Facade pattern** to hide complexity

**Tool System** (`src/mcp/tools/`):
- `base.py`: Tool categories, definitions, and base classes
- `dispatcher.py`: Routes tool calls to handlers with timeout management
- Individual tool files: Each tool has its own definition file
- Uses **Strategy pattern** for tool execution

**ElasticsearchClient** (`elasticsearch_client.py`, 1200+ lines):
- Unified interface for all SIEM queries
- Supports multiple index patterns: Cowrie honeypot, Zeek network data, DShield-specific indices
- Query optimization for large result sets
- Pagination (offset and cursor-based)
- Circuit breaker integration

**Campaign Analysis System**:
- `campaign_analyzer.py` (1000+ lines): Core correlation engine with 7 correlation methods
- `campaign_mcp_tools.py`: High-level campaign tools wrapping the analyzer
- Campaign confidence scoring (Low, Medium, High, Critical)
- Event grouping and indicator relationship tracking

**Threat Intelligence**:
- `dshield_client.py` (350+ lines): DShield API client for IP reputation and attack data
- `threat_intelligence_manager.py` (1600+ lines): Multi-source threat intelligence aggregation
- `statistical_analysis_tools.py`: Zscore-based anomaly detection

**Error Handling & Resilience**:
- `mcp_error_handler.py` (900+ lines): JSON-RPC 2.0 compliant error handling
- Circuit breaker implementation (CLOSED, OPEN, HALF_OPEN states)
- Timeout handling and retry logic with exponential backoff
- Error aggregation and rate limiting

**Feature Management** (`feature_manager.py`, 300+ lines):
- Graceful degradation when dependencies fail
- Maps tools to required dependencies
- Health checks determine feature availability
- Tools listed only if dependencies are healthy

---

## Configuration & Secrets Management

### Configuration Hierarchy

1. **YAML Configuration** (`mcp_config.yaml`):
   - Elasticsearch connection settings and index patterns
   - DShield API credentials (resolved from 1Password)
   - Error handling settings (timeouts, retries, circuit breaker)

2. **User Configuration** (`user_config.yaml`):
   - Query settings (page size, timeout, optimization)
   - Pagination preferences
   - Streaming settings
   - Performance tuning

3. **Environment Variables** (`.env`):
   - `ELASTICSEARCH_URL`: Elasticsearch cluster URL
   - `ELASTICSEARCH_USERNAME`: Username (or `op://` reference)
   - `ELASTICSEARCH_PASSWORD`: Password (or `op://` reference)
   - `DSHIELD_API_KEY`: DShield API key (or `op://` reference)
   - `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
   - `LOG_FILE_PATH`: Optional log file path

### 1Password CLI Integration

**All secrets resolved at runtime** via `op_secrets.py` (350+ lines):
- Format: `op://vault-name/item-name/field-name`
- Example: `ELASTICSEARCH_PASSWORD=op://DevSecOps/es-data01-elastic/password`
- **No plain text secrets in configuration files**
- Async secret resolution with fallback behavior

**Setup 1Password CLI**:
```bash
# macOS
brew install 1password-cli

# Authenticate
op signin
```

**Testing Integration**:
```bash
cd dev_tools && python test_op_integration.py
```

---

## MCP Protocol Implementation

### Tools (8+ tools)
Registered via `@server.list_tools()` and `@server.call_tool()`:
- **Query Tools**: `query_dshield_events`, `stream_dshield_events_with_session_context`
- **Campaign Tools**: `analyze_campaign`, `expand_campaign_indicators`, `get_campaign_timeline`
- **Report Tools**: `generate_attack_report`
- **Utility Tools**: `get_data_dictionary`, `get_health_status`
- **Analysis Tools**: `detect_statistical_anomalies`

Each tool has:
- JSON schema for input validation
- Feature dependency tracking
- Timeout configuration
- Category classification

### Resources (6 resources)
Registered via `@server.list_resources()` and `@server.read_resource()`:
- `dshield://events`: Recent DShield events
- `dshield://attacks`: Recent attack data
- `dshield://top-attackers`: Top attacker statistics
- `dshield://statistics`: Summary statistics
- `dshield://threat-intelligence`: Threat intelligence info
- `dshield://data-dictionary`: Field definitions

### JSON-RPC 2.0 Compliance
- Proper error codes (-32600, -32601, -32602, etc.)
- Request ID tracking for request-response correlation
- Batch request support via MCP server library

---

## Testing Architecture

### Test Structure
```
tests/
├── conftest.py                 # Shared fixtures and pytest configuration
├── mcp/                        # MCP-specific tests
│   ├── __init__.py
│   ├── tools/                  # Tool-specific tests
│   └── test_mcp_server_refactored.py
├── <component>/                # Unit tests (one directory per component)
│   ├── test_elasticsearch_client/
│   ├── test_campaign_analyzer/
│   ├── test_mcp_error_handler/
│   └── ...
└── integration/                # Multi-component integration tests
```

### Pytest Configuration
**Markers** (defined in `pyproject.toml`):
- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.slow`: Slow-running tests

**Key Fixtures** (`conftest.py`):
- Blocks 1Password CLI calls in tests
- Mocks Elasticsearch with `_FakeES` class
- Blocks subprocess/process spawning
- Provides custom event loop for async tests

**Fast Test Execution**:
- Environment variables: `MCP_TEST_FAST`, `TUI_FAST`, `TUI_HEADLESS`
- Mock all external dependencies (1Password, Elasticsearch, subprocess)
- Fast paths ensure tests run quickly in CI

### TUI Tests (Headless Mode)
TUI tests run in headless mode to avoid spawning terminal I/O threads:
- Uses null driver and disables UI refreshes
- Some stress tests shortened in CI
- Manual validation: `unset TUI_HEADLESS TUI_FAST && pytest tests/tui/`

---

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

---

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

---

## Refactoring Goals (Issue #113)

**Current Branch**: `refactor/issue-113-reduce-mcp-server-complexity`

**Objectives**:
1. Extract tool loading into `ToolLoader` class
2. Clearer mapping of tool names to handler methods
3. Use `ToolDispatcher` for clean tool routing
4. Dynamic feature availability based on dependencies
5. Centralize error responses through `MCPErrorHandler`

**Benefits**:
- Easier to add new tools without modifying core server
- Better error handling and timeout management
- Graceful degradation when dependencies fail
- Improved testability and maintainability

---

## Extension Points

### Adding New Tools
1. Create tool definition file in `src/mcp/tools/your_tool.py`
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

---

## Important Considerations

### Elasticsearch Index Patterns
The system supports multiple SIEM data sources:
- **Cowrie Honeypot**: `cowrie-*`, `cowrie.dshield-*`, `cowrie.vt_data-*`, `cowrie.webhoneypot-*`
- **Zeek Network Data**: `filebeat-zeek-*`, `zeek.connection*`, `zeek.dns*`, `zeek.http*`, `zeek.ssl*`
- Index patterns configured in `mcp_config.yaml`

### LaTeX Report Generation
- Requires LaTeX distribution installed (MacTeX, MiKTeX, or TeX Live)
- Templates stored in `templates/` directory
- PDF compilation handled by `latex_template_tools.py`
- Output directory configurable via `DMC_OUTPUT_DIRECTORY` env var

### Security Considerations
- **API Key Management**: Store keys securely in 1Password
- **Rate Limiting**: Respect DShield API rate limits
- **Data Privacy**: Ensure compliance with data protection regulations
- **Network Security**: Use secure connections (HTTPS/TLS)
- **Access Control**: Implement proper access controls for the MCP server

### Performance Optimization
- **Smart Query Optimization**: Auto-detects large result sets, uses aggregation
- **Pagination**: Supports offset and cursor-based pagination
- **Streaming**: Large datasets streamed with session context
- **Caching**: DShield API responses cached with TTL
- **Concurrency**: All operations async using `asyncio`

---

## Documentation

### Implementation Docs
- `docs/README.md`: Documentation index
- `docs/USAGE.md`: Detailed usage examples
- `docs/CHANGELOG.md`: Version history
- `docs/Enhancements.md`: Planned features and roadmap
- `docs/API_DOCUMENTATION.md`: API reference

### Generated API Docs
- HTML: `docs/api/index.html` (generated by pdoc)
- Build script: `./scripts/build_api_docs.sh`

---

## Cursor Rules (.cursorrules)

Key development guidelines from `.cursorrules`:
- **1Password for Secrets**: Never hardcode secrets; use `op://` references
- **Type Annotations**: All functions and classes must have typing annotations
- **Docstrings**: Use PEP257 convention (Google style)
- **Testing**: Use pytest only (no unittest module)
- **Documentation**: Create implementation docs in `docs/` for all new features
- **Branch Management**: Always create feature/bugfix branches (never work on main)
- **GitHub PRs**: Use `gh pr create --body-file` for formatted PR descriptions

---

## Summary

DShield MCP is a sophisticated SIEM analysis platform that leverages MCP protocol to provide AI assistants with security intelligence capabilities. The architecture emphasizes modularity, resilience, security, observability, testability, and extensibility. The current refactoring (Issue #113) focuses on reducing server complexity through better tool management, clearer handler registration, and improved feature-aware tool availability.
