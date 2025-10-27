# DShield MCP - Codebase Index

**Last Updated:** 2024-10-26
**Total Python Files:** 189
**Total Lines of Code:** ~82,414
**Source Code:** 67 files (~32,785 lines)
**Test Code:** 114 files (~26,506 lines)

---

## Quick Navigation

- [Core Server & MCP](#1-core-server--mcp-components)
- [Data & Intelligence Clients](#2-data--intelligence-clients)
- [Analysis & Processing](#3-analysis--intelligence)
- [Error Handling & Security](#4-error-handling--security)
- [MCP Tools](#5-mcp-tools-modular-system)
- [TUI Components](#6-tui-terminal-user-interface)
- [Configuration](#7-configuration--secrets)
- [Tests](#8-test-files)
- [Documentation](#9-documentation)
- [Templates](#10-templates)

---

## Source Files (`src/`)

### 1. Core Server & MCP Components

#### `mcp_server.py` (2,466 lines)
Main MCP server implementation
- Central orchestration point for entire system
- Handles JSON-RPC 2.0 protocol communication
- Registers and dispatches all MCP tools
- Integrates ES client, DShield client, campaign analyzer
- **Key Class:** `DShieldMCPServer`

#### `src/__init__.py` (58 lines)
Package initialization with comprehensive documentation

---

### 2. Data & Intelligence Clients

#### `src/elasticsearch_client.py` (3,073 lines)
Elasticsearch client for querying DShield SIEM
- Supports Cowrie honeypot and Zeek network data
- Query optimization and field mapping
- Pagination (offset and cursor-based)
- Aggregations and health checks
- Circuit breaker integration
- **Key Class:** `ElasticsearchClient`

#### `src/dshield_client.py` (780 lines)
DShield API client for threat intelligence
- IP reputation lookups and attack summaries
- Batch enrichment with rate limiting
- Caching and circuit breaker support
- Async context manager
- **Key Class:** `DShieldClient`

---

### 3. Analysis & Intelligence

#### `src/threat_intelligence_manager.py` (1,675 lines)
Multi-source threat intelligence aggregation
- Coordinates DShield, VirusTotal, Shodan APIs
- Intelligent correlation and scoring
- Advanced caching with configurable TTL
- **Key Class:** `ThreatIntelligenceManager`

#### `src/campaign_analyzer.py` (1,437 lines)
Campaign correlation and analysis engine
- Identifies coordinated attack campaigns
- 7 correlation methods: IP, infrastructure, behavioral, temporal, geospatial, signature, network
- Confidence scoring (Low, Medium, High, Critical)
- **Key Classes:** `CampaignAnalyzer`, `CampaignEvent`, `Campaign`
- **Enums:** `CorrelationMethod`, `CampaignConfidence`

#### `src/statistical_analysis_tools.py` (1,184 lines)
Statistical anomaly detection
- Z-score, IQR, Isolation Forest, time-series analysis
- Elasticsearch aggregation-based detection
- Context pivots and calibrated risk scores
- **Key Class:** `StatisticalAnalysisTools`

#### `src/campaign_mcp_tools.py` (976 lines)
MCP tools for campaign analysis
- Wraps campaign analyzer for MCP protocol
- **Key Class:** `CampaignMCPTools`
- **Tools:** `analyze_campaign`, `expand_campaign_indicators`, `get_campaign_timeline`

---

### 4. Error Handling & Security

#### `src/mcp_error_handler.py` (1,414 lines)
Centralized error handling
- JSON-RPC error responses with proper codes
- Timeout handling and retry logic
- Circuit breaker pattern (CLOSED, OPEN, HALF_OPEN)
- **Key Classes:** `MCPErrorHandler`, `CircuitBreaker`, `ErrorHandlingConfig`

#### `src/security/mcp_schema_validator.py` (805 lines)
MCP protocol schema validation
- Input/output validation for tool calls
- Security-focused validation rules
- **Key Class:** `MCPSchemaValidator`

#### `src/security_validator.py` (573 lines)
Tool security validation
- Parameter schema validation
- Input sanitization checks
- **Key Classes:** `SecurityValidator`, `SecurityIssue`
- **Enum:** `SecurityRiskLevel`

#### `src/security/rate_limiter.py` (397 lines)
Rate limiting implementation
- Token bucket and sliding window algorithms
- **Key Classes:** `APIKeyRateLimiter`, `ConnectionRateLimiter`, `GlobalRateLimiter`

#### `src/tcp_security.py` (753 lines)
TCP transport security
- Rate limiting and input validation
- Abuse detection
- **Key Classes:** `RateLimiter`, `TCPSecurityManager`, `SecurityViolation`

#### `src/tcp_auth.py` (432 lines)
TCP authentication system
- API key validation and permission checking
- Session management
- **Key Classes:** `TCPAuthenticator`, `AuthenticationError`

---

### 5. MCP Tools (Modular System)

**Location:** `src/mcp/tools/`

#### `base.py` (92 lines)
Base tool classes and interfaces
- **Key Classes:** `BaseTool`, `ToolDefinition`
- **Enum:** `ToolCategory` (CAMPAIGN, QUERY, REPORT, UTILITY, MONITORING)

#### `dispatcher.py` (146 lines)
Tool call dispatcher
- Routes tool calls to handlers
- Error handling and timeout management
- **Key Class:** `ToolDispatcher`

#### Individual Tool Files:
- `query_dshield_events.py` (153 lines) - Query SIEM events
- `stream_dshield_events_with_session_context.py` (90 lines) - Streaming with context
- `analyze_campaign.py` (95 lines) - Campaign analysis
- `expand_campaign_indicators.py` (94 lines) - Campaign indicator expansion
- `get_campaign_timeline.py` (90 lines) - Timeline analysis
- `generate_attack_report.py` (91 lines) - Report generation
- `get_data_dictionary.py` (74 lines) - Data dictionary access
- `get_health_status.py` (65 lines) - Health status check
- `detect_statistical_anomalies.py` (106 lines) - Anomaly detection

---

### 6. TUI (Terminal User Interface)

**Location:** `src/tui/`

#### `tui_app.py` (1,007 lines)
Main TUI application using Textual
- Layout management and event handling
- TCP server integration
- **Key Classes:** `DShieldTUIApp`, `ServerStatusUpdate`

#### `connection_panel.py` (615 lines)
Connection management panel
- Active connections display
- **Key Class:** `ConnectionPanel`

#### `server_panel.py` (422 lines)
Server control and status panel
- **Key Classes:** `ServerPanel`, `ServerStart`, `ServerStop`, `ServerRestart`

#### `log_panel.py` (404 lines)
Log display with filtering
- **Key Class:** `LogPanel`

#### `api_key_panel.py` (403 lines)
API key management panel
- **Key Class:** `APIKeyPanel`

#### `status_bar.py` (266 lines)
Status bar widget
- **Key Class:** `StatusBar`

#### `log_buffer.py` (274 lines)
Thread-safe log buffering
- **Key Class:** `LogBuffer`

#### `live_metrics_panel.py` (285 lines)
Real-time metrics display
- **Key Class:** `LiveMetricsPanel`

#### `metrics_subscriber.py` (347 lines)
Metrics subscription and updates
- **Key Class:** `MetricsSubscriber`

#### `metrics_formatter.py` (373 lines)
Metrics formatting for display
- **Key Class:** `MetricsFormatter`

#### `server_process_manager.py` (292 lines)
Server process lifecycle
- **Key Class:** `ServerProcessManager`

#### `screens/api_key_screen.py` (316 lines)
API key management screen
- **Key Class:** `APIKeyScreen`

#### `src/tui_launcher.py` (469 lines)
TUI entry point
- **Key Classes:** `TUIProcessManager`, `DShieldTUILauncher`

---

### 7. Configuration & Secrets

#### `src/config_loader.py` (299 lines)
YAML configuration loading
- 1Password CLI secret resolution
- **Functions:** `get_config()`, `get_error_handling_config()`
- **Exception:** `ConfigError`

#### `src/user_config.py` (1,385 lines)
User configuration management
- Environment variable overrides
- **Key Classes:** `UserConfigManager`, `QuerySettings`, `PaginationSettings`, `StreamingSettings`, `TCPTransportSettings`
- **Function:** `get_user_config()` (singleton)

#### `src/op_secrets.py` (395 lines)
1Password CLI integration
- op:// URL resolution
- **Key Classes:** `OnePasswordSecrets`, `OnePasswordAPIKeyManager`

#### `src/secrets_manager/base_secrets_manager.py` (527 lines)
Base secrets manager
- Abstract interface
- **Key Classes:** `BaseSecretsManager`, `APIKey`

#### `src/secrets_manager/onepassword_cli_manager.py` (965 lines)
1Password CLI manager implementation
- **Key Class:** `OnePasswordCLIManager`

---

### 8. Data Processing & Models

#### `src/data_processor.py` (1,335 lines)
Data formatting for AI consumption
- Event normalization and enrichment
- Attack pattern detection
- **Key Class:** `DataProcessor`

#### `src/models.py` (685 lines)
Pydantic data models
- **Key Classes:** `SecurityEvent`, `DShieldAttack`, `DShieldReputation`, `ThreatIntelligenceResult`
- **Enums:** `EventSeverity`, `EventCategory`

#### `src/context_injector.py` (869 lines)
Context preparation for AI
- Multiple output formats
- ChatGPT-optimized formatting
- **Key Class:** `ContextInjector`

#### `src/data_dictionary.py` (737 lines)
Field descriptions and query examples
- **Key Class:** `DataDictionary`
- Static methods for field info and analysis guidelines

---

### 9. Transport Layer

**Location:** `src/transport/`

#### `base_transport.py` (155 lines)
Abstract base for transports
- **Key Classes:** `BaseTransport`, `TransportError`

#### `stdio_transport.py` (149 lines)
STDIO transport implementation
- **Key Class:** `STDIOTransport`

#### `tcp_transport.py` (474 lines)
TCP transport implementation
- **Key Classes:** `TCPTransport`, `TCPConnection`

#### `transport_manager.py` (420 lines)
Transport selection and lifecycle
- Automatic transport detection
- **Key Class:** `TransportManager`

---

### 10. TCP Server & Networking

#### `src/tcp_server.py` (821 lines)
TCP server with full MCP support
- Authentication, security, integration
- **Key Classes:** `MCPServerAdapter`, `EnhancedTCPServer`

#### `src/connection_manager.py` (505 lines)
TCP connection lifecycle
- API key management
- **Key Classes:** `ConnectionManager`, `APIKey`

---

### 11. Server Management & Utilities

#### `src/server_launcher.py` (283 lines)
Main entry point for MCP server
- Transport selection (STDIO/TCP)
- **Key Class:** `DShieldServerLauncher`

#### `src/api_key_generator.py` (437 lines)
Cryptographically secure API key generation
- SHA-256 hashing, metadata handling
- **Key Class:** `APIKeyGenerator`

#### `src/health_check_manager.py` (377 lines)
Health checks for dependencies
- **Key Class:** `HealthCheckManager`

#### `src/feature_manager.py` (323 lines)
Feature availability management
- Graceful degradation
- **Key Class:** `FeatureManager`

#### `src/dynamic_tool_registry.py` (337 lines)
Dynamic tool registration
- Tool-to-feature mapping
- **Key Class:** `DynamicToolRegistry`

#### `src/latex_template_tools.py` (932 lines)
LaTeX template automation
- Variable substitution and PDF generation
- **Key Class:** `LaTeXTemplateTools`

#### `src/operation_tracker.py` (54 lines)
Operation tracking
- **Key Class:** `OperationTracker`

#### `src/signal_handler.py` (48 lines)
Signal handling for graceful shutdown
- **Key Class:** `SignalHandler`

#### `src/resource_manager.py` (46 lines)
Resource lifecycle management
- **Key Class:** `ResourceManager`

---

## Test Files (`tests/`)

### Test Structure
- **Total Test Files:** 114
- **Total Test Lines:** ~26,506
- **Coverage:** Comprehensive (unit, integration, TUI, security, performance)

### Integration Tests
- `test_enhanced_threat_intelligence.py` (1,455 lines)
- `test_data_parsing.py` (1,224 lines)
- `test_elasticsearch_client.py` (842 lines)
- `test_latex_template_tools.py` (747 lines)
- `test_streaming.py` (595 lines)
- `test_error_handling.py` (573 lines)
- `test_campaign_analysis.py` (563 lines)
- `test_server_integration.py`
- `test_remaining_integration.py` (472 lines)

### TUI Tests
- `tui/test_tui_app.py` (570 lines)
- `tui/test_connection_panel.py` (753 lines)
- `tui/test_log_panel.py` (541 lines)
- `tui/test_server_panel.py` (491 lines)
- `tui/test_status_bar.py` (467 lines)
- `tui/test_api_key_panel.py`
- `tui/test_server_process_manager.py`
- `tui/screens/test_api_key_screen.py`
- `test_connection_panel_integration.py` (413 lines)

### Security & Authentication Tests
- `test_security.py` (484 lines)
- `test_mcp_schema_validator.py` (449 lines)
- `test_api_key_generator.py` (385 lines)
- `tcp_auth/test_tcp_auth.py`
- `security/` - Security component tests

### Error Handling Tests
- `test_phase3_error_handling.py` (395 lines)
- `test_phase4_elasticsearch_circuit_breaker.py` (484 lines)
- `test_phase4_dshield_circuit_breaker.py` (469 lines)
- `mcp_error_handler/test_mcp_error_handler.py`

### Performance Tests
- `test_performance_metrics.py` (446 lines)
- `test_query_optimization.py` (466 lines)
- `test_metrics_subscriber.py` (471 lines)
- `test_live_metrics_panel.py` (480 lines)

### Component Tests
- `secrets_manager/test_base_secrets_manager.py` (662 lines)
- `test_log_buffer.py` (396 lines)
- `test_pagination.py`
- `test_signal_handling.py`
- `test_data_dictionary.py`
- `test_models.py`
- `test_op_secrets.py`
- `context_injector/test_context_injector.py`
- `dshield_client/test_dshield_client.py`
- Plus many more...

### Refactored Tests
- `test_mcp_server_refactored.py` - Main refactored server tests (active)
- `test_mcp_server_refactored_simple.py` (512 lines)
- `test_simple_critical_components.py`

---

## Configuration Files (Root)

### YAML Configuration
- **`mcp_config.yaml`** - Main MCP server configuration
- **`mcp_config.example.yaml`** - Example configuration template
- **`user_config.yaml`** - User-specific settings
- **`user_config.example.yaml`** - Example user config
- **`test_config.yaml`** - Test environment config

### Python Configuration
- **`pyproject.toml`** (6,256 bytes) - Project metadata, dependencies, tool configs
- **`config.py`** (336 lines) - Interactive configuration setup
- **`setup.py`** (68 lines) - Package setup

### Dependencies
- **`requirements.txt`** - Production dependencies
- **`requirements-dev.txt`** - Development dependencies
- **`package.json`** - NPM config for MCP Inspector
- **`uv.lock`** - UV package manager lock file

### Documentation Config
- **`pdoc.yaml`** - pdoc HTML documentation config
- **`pydoc-markdown.yml`** - pydoc-markdown config

---

## Documentation (`docs/` and root)

### Main Documentation
- **`README.md`** (24,744 bytes, ~700+ lines) - Comprehensive project overview
- **`CLAUDE.md`** (20,039 bytes) - Claude AI integration guide
- **`CHANGELOG.md`** (2,926 bytes) - Version history
- **`AGENTS.md`** (7,768 bytes) - Agent architecture
- **`LICENSE`** - BSD 4-Clause License

### User Guides
- **`docs/README.md`** - Documentation index
- **`docs/USAGE.md`** - Detailed usage and API reference
- **`docs/ERROR_HANDLING_USER_GUIDE.md`**
- **`docs/ERROR_HANDLING_TROUBLESHOOTING_GUIDE.md`**
- **`docs/ERROR_HANDLING_CONFIGURATION_GUIDE.md`**
- **`docs/OUTPUT_DIRECTORY_CONFIGURATION.md`**

### Implementation Documentation
**`docs/Implementation_Docs/`:**
- TCP_TUI_IMPLEMENTATION_SUMMARY.md
- ISSUE_58_JSON_RPC_ERROR_HANDLING_IMPLEMENTATION.md
- ISSUE_99_DATA_AVAILABILITY_DIAGNOSTICS_IMPLEMENTATION.md
- SECURITY_HARDENING_IMPLEMENTATION.md
- API_KEY_MANAGEMENT_IMPLEMENTATION.md
- PAGINATION_IMPLEMENTATION.md
- STREAMING_IMPLEMENTATION.md
- CAMPAIGN_ANALYSIS_IMPLEMENTATION.md
- ENHANCED_THREAT_INTELLIGENCE_IMPLEMENTATION.md
- STATISTICAL_ANOMALY_DETECTION_IMPLEMENTATION.md
- LATEX_TEMPLATE_AUTOMATION_IMPLEMENTATION.md
- Plus many more...

### Progress Reports
**`docs/`:**
- TEST_COVERAGE_PROGRESS_REPORT.md
- CODE_QUALITY_CLEANUP_REPORT.md
- SECURITY_TEST_AUDIT.md
- test_coverage_plan.md
- coverage_worklist.md

### API Documentation (Auto-Generated)
**`docs/api/markdown/`:** Complete API docs for all modules in Markdown format

---

## Scripts

### Python Scripts
- **`scripts/security_scan.py`** - Security vulnerability scanning
- **`scripts/build_api_docs.py`** - Build API documentation (Python)

### Shell Scripts
- **`scripts/build_api_docs.sh`** - Build API documentation (Shell)
- **`setup_venv.sh`** - Virtual environment setup
- **`activate_venv.sh`** - Virtual environment activation
- **`commit_changes.sh`** - Git commit automation
- **`test_tcp_tui_validation.sh`** - TCP TUI validation

---

## Examples (`examples/`)

- **`basic_usage.py`** (320 lines) - Core functionality examples
- **`data_dictionary_usage.py`** - Data dictionary examples
- **`enhanced_threat_intelligence_usage.py`** - Threat intelligence examples
- **`latex_template_usage.py`** - LaTeX template examples
- **`statistical_anomaly_detection_usage.py`** - Anomaly detection examples

---

## Templates (`templates/`)

### Attack_Report Template
Professional security report template with LaTeX

**Structure:**
```
templates/Attack_Report/
├── main_report.tex
├── preamble.tex
├── document_body.tex
├── template_info.json
├── compile_report.sh
├── sections/
│   ├── title_page.tex
│   ├── executive_summary.tex
│   ├── campaign_overview.tex
│   ├── attack_analysis.tex
│   ├── threat_assessment.tex
│   ├── c2_infrastructure.tex
│   ├── payload_analysis.tex
│   ├── iocs.tex
│   ├── recommendations.tex
│   └── ...
└── assets/
```

**Features:**
- Modular section-based architecture
- Variable substitution system
- Professional formatting
- Automatic PDF compilation
- MCP-integrated data population

---

## Key Architecture Highlights

### Design Patterns
1. **Facade:** `DShieldMCPServer` as single entry point
2. **Strategy:** Tool dispatcher and correlation methods
3. **Factory:** Dynamic tool creation
4. **Circuit Breaker:** Fault tolerance in `MCPErrorHandler`
5. **Dependency Injection:** Loose coupling throughout
6. **Observer:** `FeatureManager` monitors health
7. **Async/Await:** All I/O operations

### Technologies
- **Framework:** MCP (Model Context Protocol)
- **Language:** Python 3.10+
- **Data:** Elasticsearch 7.x/8.x
- **TUI:** Textual framework
- **Testing:** pytest ecosystem
- **Security:** 1Password CLI, cryptography
- **Validation:** Pydantic
- **Logging:** structlog

### Project Statistics
- **189 Python files** (~82,414 total lines)
- **67 source files** (~32,785 lines)
- **114 test files** (~26,506 lines)
- **Comprehensive test coverage** (unit, integration, TUI, security, performance)

---

## Navigation Tips

**For Development:**
1. Start with `mcp_server.py` to understand orchestration
2. Check `src/mcp/tools/` for tool implementations
3. Review `src/elasticsearch_client.py` for data access
4. See `src/mcp_error_handler.py` for error handling

**For Testing:**
1. `tests/conftest.py` - Shared fixtures
2. `tests/mcp/test_mcp_server_refactored.py` - Current server tests
3. Component-specific test directories match source structure

**For Documentation:**
1. `README.md` - Start here for overview
2. `CLAUDE.md` - Development guide for AI assistants
3. `docs/USAGE.md` - Usage examples
4. `docs/api/markdown/` - API reference

**For Configuration:**
1. `.env` - Environment variables
2. `mcp_config.yaml` - Server configuration
3. `user_config.yaml` - User settings
4. `pyproject.toml` - Project metadata and tools
