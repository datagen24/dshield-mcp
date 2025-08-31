# TCP Transport and Terminal UI Implementation Plan

## Overview
This document outlines the implementation plan for adding TCP socket-based transport mode and a terminal-based UI to the DShield MCP server. This enhancement will allow the server to operate over network connections while maintaining full MCP protocol compliance and security.

## Requirements Analysis

### 1. TCP Socket Transport Requirements
- **Configurable Port**: Must support configurable port binding (default: 3000)
- **IP Binding**: Must support binding to localhost or any IP based on configuration
- **MCP Protocol Compliance**: Must maintain full JSON-RPC 2.0 compliance
- **Security**: Must implement authentication and rate limiting for TCP connections
- **Graceful Shutdown**: Must support graceful connection termination

### 2. Terminal UI Requirements
- **Connection Management**: Visual display of active connections
- **Tool Status Monitoring**: Real-time status of MCP tools and operations
- **Connection Logging**: Visible log of connection events and tool usage
- **Agent Management**: Ability to disconnect agents and force graceful shutdown
- **Interactive Controls**: User-friendly interface for server management

### 3. Security and Compliance Requirements
- **MCP Protocol Compliance**: Full adherence to MCP specification
- **Authentication**: Secure connection authentication mechanism
- **Rate Limiting**: Protection against abuse and DoS attacks
- **Input Validation**: Comprehensive validation of all TCP inputs
- **Audit Logging**: Complete audit trail of all operations

## Technical Architecture

### 1. Transport Layer Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    DShield MCP Server                      │
├─────────────────────────────────────────────────────────────┤
│  Transport Layer (Abstract)                                │
│  ├── STDIO Transport (Existing)                            │
│  └── TCP Transport (New)                                   │
│      ├── Connection Manager                                │
│      ├── Authentication Handler                            │
│      ├── Rate Limiter                                      │
│      └── JSON-RPC Message Router                           │
├─────────────────────────────────────────────────────────────┤
│  MCP Protocol Layer (Existing)                             │
│  ├── Tool Registry                                         │
│  ├── Resource Manager                                      │
│  └── Error Handler                                         │
├─────────────────────────────────────────────────────────────┤
│  Business Logic Layer (Existing)                           │
│  ├── Campaign Analyzer                                     │
│  ├── DShield Client                                        │
│  └── Elasticsearch Client                                  │
└─────────────────────────────────────────────────────────────┘
```

### 2. Terminal UI Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Terminal UI (TUI)                       │
├─────────────────────────────────────────────────────────────┤
│  UI Components                                             │
│  ├── Connection Status Panel                               │
│  ├── Tool Status Panel                                     │
│  ├── Activity Log Panel                                    │
│  └── Control Panel                                         │
├─────────────────────────────────────────────────────────────┤
│  Data Sources                                              │
│  ├── Connection Manager Events                             │
│  ├── Tool Registry Status                                  │
│  ├── Server Metrics                                        │
│  └── Audit Logs                                            │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: Configuration and Infrastructure Setup
**Duration**: 2-3 days

#### 1.1 TCP Configuration System
- **File**: `src/tcp_config.py`
- **Purpose**: TCP-specific configuration management
- **Features**:
  - Port configuration (default: 3000)
  - IP binding options (localhost, any)
  - Connection limits and timeouts
  - Authentication settings
  - Rate limiting configuration

#### 1.2 Transport Abstraction Layer
- **File**: `src/transport/`
- **Purpose**: Abstract transport layer for multiple transport types
- **Components**:
  - `base_transport.py`: Abstract base class
  - `stdio_transport.py`: Existing STDIO transport (refactored)
  - `tcp_transport.py`: New TCP transport implementation

#### 1.3 Connection Management
- **File**: `src/connection_manager.py`
- **Purpose**: Manage TCP connections and sessions
- **Features**:
  - Connection lifecycle management
  - Session tracking and cleanup
  - Connection health monitoring
  - Graceful disconnection handling

### Phase 2: TCP Transport Implementation
**Duration**: 4-5 days

#### 2.1 TCP Server Implementation
- **File**: `src/tcp_server.py`
- **Purpose**: Core TCP server with MCP protocol support
- **Features**:
  - Async TCP server using asyncio
  - JSON-RPC 2.0 message handling
  - Connection authentication
  - Message routing and validation

#### 2.2 Authentication System
- **File**: `src/tcp_auth.py`
- **Purpose**: TCP connection authentication
- **Features**:
  - API key authentication
  - Session token management
  - Connection authorization
  - Security event logging

#### 2.3 Rate Limiting and Security
- **File**: `src/tcp_security.py`
- **Purpose**: TCP-specific security measures
- **Features**:
  - Per-connection rate limiting
  - Request size limits
  - Connection timeout management
  - Abuse detection and prevention

### Phase 3: Terminal UI Implementation
**Duration**: 3-4 days

#### 3.1 TUI Framework Setup
- **File**: `src/tui/`
- **Purpose**: Terminal UI framework and components
- **Components**:
  - `tui_app.py`: Main TUI application
  - `panels/`: UI panel components
  - `widgets/`: Reusable UI widgets
  - `events.py`: Event handling system

#### 3.2 Connection Management UI
- **File**: `src/tui/panels/connection_panel.py`
- **Purpose**: Visual connection management interface
- **Features**:
  - Active connections display
  - Connection details (IP, port, status)
  - Connection controls (disconnect, force close)
  - Real-time connection updates

#### 3.3 Tool Status and Monitoring UI
- **File**: `src/tui/panels/tool_panel.py`
- **Purpose**: Tool status and performance monitoring
- **Features**:
  - Tool availability status
  - Performance metrics display
  - Error rate monitoring
  - Tool usage statistics

#### 3.4 Activity Logging UI
- **File**: `src/tui/panels/log_panel.py`
- **Purpose**: Real-time activity logging interface
- **Features**:
  - Scrollable log display
  - Log filtering and search
  - Log level indicators
  - Export functionality

### Phase 4: Integration and Testing
**Duration**: 3-4 days

#### 4.1 Server Integration
- **File**: `mcp_server.py` (modifications)
- **Purpose**: Integrate TCP transport with existing server
- **Changes**:
  - Transport selection logic
  - Dual-mode operation support
  - Configuration integration
  - Graceful shutdown handling

#### 4.2 Comprehensive Testing
- **Files**: `tests/test_tcp_*.py`
- **Purpose**: Comprehensive test coverage for TCP transport
- **Test Categories**:
  - Unit tests for TCP components
  - Integration tests for MCP protocol
  - Security tests for authentication
  - Performance tests for rate limiting
  - End-to-end tests for TUI functionality

#### 4.3 Documentation and Examples
- **Files**: `docs/`, `examples/`
- **Purpose**: Complete documentation and usage examples
- **Content**:
  - TCP configuration guide
  - TUI usage documentation
  - Security best practices
  - Troubleshooting guide
  - Example configurations

## Configuration Schema

### TCP Transport Configuration
```yaml
# user_config.yaml additions
tcp_transport:
  enabled: false  # Default to STDIO mode
  port: 3000
  bind_address: "127.0.0.1"  # localhost by default
  max_connections: 10
  connection_timeout_seconds: 300
  authentication:
    enabled: true
    method: "api_key"  # api_key, token, none
    api_key_source: "op://vault/item/field"  # 1Password reference
  rate_limiting:
    enabled: true
    requests_per_minute: 60
    burst_limit: 10
  security:
    max_request_size_bytes: 1048576  # 1MB
    enable_compression: true
    tls:
      enabled: false  # Future enhancement
      cert_file: ""
      key_file: ""

# TUI Configuration
tui:
  enabled: false  # Default to headless mode
  refresh_interval_ms: 1000
  log_history_size: 1000
  panels:
    connections:
      enabled: true
      show_details: true
    tools:
      enabled: true
      show_metrics: true
    logs:
      enabled: true
      log_levels: ["INFO", "WARN", "ERROR"]
```

## Security Considerations

### 1. Authentication Mechanisms
- **API Key Authentication**: Primary method using 1Password-stored keys
- **Session Management**: Secure session token generation and validation
- **Connection Authorization**: Per-connection permission checking

### 2. Network Security
- **Rate Limiting**: Per-connection and global rate limiting
- **Input Validation**: Comprehensive validation of all TCP inputs
- **Connection Limits**: Maximum concurrent connection limits
- **Timeout Management**: Automatic connection cleanup

### 3. Audit and Monitoring
- **Connection Logging**: Complete audit trail of all connections
- **Security Events**: Logging of authentication and authorization events
- **Performance Monitoring**: Real-time monitoring of connection health
- **Abuse Detection**: Detection and prevention of abuse patterns

## Testing Strategy

### 1. Unit Testing
- TCP transport components
- Authentication system
- Rate limiting mechanisms
- TUI components and widgets

### 2. Integration Testing
- MCP protocol compliance over TCP
- End-to-end tool execution
- Connection lifecycle management
- TUI integration with server

### 3. Security Testing
- Authentication bypass attempts
- Rate limiting effectiveness
- Input validation robustness
- Connection abuse scenarios

### 4. Performance Testing
- Concurrent connection handling
- Message throughput testing
- Memory usage under load
- TUI responsiveness testing

## Migration and Deployment

### 1. Backward Compatibility
- Existing STDIO mode remains unchanged
- Configuration defaults maintain current behavior
- No breaking changes to existing functionality

### 2. Deployment Options
- **STDIO Mode**: Current behavior (default)
- **TCP Mode**: New network-based operation
- **TUI Mode**: Terminal-based management interface
- **Hybrid Mode**: TCP with TUI management

### 3. Configuration Migration
- Automatic configuration validation
- Migration scripts for existing configurations
- Clear documentation for new configuration options

## Risk Assessment and Mitigation

### 1. Security Risks
- **Risk**: Unauthorized access via TCP
- **Mitigation**: Strong authentication and rate limiting

- **Risk**: Network-based attacks
- **Mitigation**: Input validation and connection limits

### 2. Performance Risks
- **Risk**: TCP overhead affecting performance
- **Mitigation**: Efficient message handling and connection pooling

- **Risk**: TUI impacting server performance
- **Mitigation**: Asynchronous UI updates and configurable refresh rates

### 3. Compatibility Risks
- **Risk**: Breaking existing STDIO functionality
- **Mitigation**: Comprehensive testing and backward compatibility

## Success Criteria

### 1. Functional Requirements
- ✅ TCP transport operates on configurable port (default 3000)
- ✅ Supports binding to localhost or any IP
- ✅ Full MCP protocol compliance maintained
- ✅ Terminal UI provides connection management
- ✅ Tool status monitoring and logging
- ✅ Graceful connection termination

### 2. Performance Requirements
- ✅ Handles multiple concurrent connections
- ✅ Maintains sub-60-second response times
- ✅ TUI updates in real-time without blocking
- ✅ Memory usage remains stable under load

### 3. Security Requirements
- ✅ Secure authentication mechanism
- ✅ Effective rate limiting
- ✅ Comprehensive audit logging
- ✅ Input validation and sanitization

## Timeline Summary

- **Phase 1**: Configuration and Infrastructure (2-3 days)
- **Phase 2**: TCP Transport Implementation (4-5 days)
- **Phase 3**: Terminal UI Implementation (3-4 days)
- **Phase 4**: Integration and Testing (3-4 days)

**Total Estimated Duration**: 12-16 days

## Updated Implementation Plan Based on User Feedback

### Key Changes Based on User Responses:

1. **Authentication Method**: API key generated from TUI after server startup, persistent and tagged between runs
2. **TUI Library**: Textual (async-first, modern)
3. **TLS Support**: Deferred for future enhancement, but architecture designed to support it
4. **Connection Model**: Follow MCP protocol specification for stateful connections
5. **TUI Deployment**: TUI is the manager of the server - only runs TCP mode when TUI is active, STDIO mode when called directly
6. **Configuration**: Use existing project configurations only

### Refined Architecture

#### TUI-Managed Server Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    TUI Manager Process                     │
│  ├── Server Lifecycle Management                           │
│  ├── API Key Generation & Management                       │
│  ├── Connection Monitoring & Control                       │
│  └── Server Configuration Management                       │
├─────────────────────────────────────────────────────────────┤
│                    DShield MCP Server                      │
│  ├── Transport Selection Logic                             │
│  │   ├── STDIO Mode (Direct Execution)                    │
│  │   └── TCP Mode (TUI-Managed)                           │
│  ├── TCP Transport Layer                                   │
│  │   ├── Connection Manager                               │
│  │   ├── API Key Authentication                           │
│  │   ├── Rate Limiter                                     │
│  │   └── JSON-RPC Message Router                          │
│  └── MCP Protocol Layer (Existing)                        │
└─────────────────────────────────────────────────────────────┘
```

#### API Key Management System
- **Generation**: TUI generates unique API keys for each connection using cryptographically secure random generation
- **Storage**: Keys stored in 1Password secrets manager with user-configurable vault
- **Validation**: Keys validated on each connection with proper error handling
- **Multi-Agent Support**: Each connection gets unique API key with individual rate limits
- **Permission Grants**: API keys can have grants for Elastic write-back mode
- **Rate Limiting**: Per-API-key rate limits for untested agents with limited access

#### MCP Protocol Compliance
- **Stateful Connections**: Implement proper session management per MCP specification
- **Capability Negotiation**: Full initialize/initialized handshake
- **JSON-RPC 2.0**: Complete protocol compliance with proper error handling
- **Tool Registration**: Dynamic tool registration with capability declaration

#### Multi-Agent Architecture
- **Concurrent Connections**: Support multiple simultaneous agent connections
- **Individual Rate Limits**: Per-API-key rate limiting for untested agents
- **Permission System**: API key grants for Elastic write-back mode
- **Connection Management**: TUI provides connection monitoring and control
- **Graceful Shutdown**: Server shutdowns gracefully when TUI exits

#### Process Management
- **TUI Subprocess Control**: TUI spawns server as subprocess with restart capabilities
- **Transport Detection**: Process parent detection with command-line fallback
- **Server Lifecycle**: TUI manages server lifecycle and transport mode selection
- **Terminal Integration**: Works in any terminal environment (tmux, screen, etc.)

## Final Implementation Architecture

### Core Components
1. **TUI Manager**: Terminal UI for server management and connection monitoring
2. **TCP Transport**: Async TCP server with MCP protocol compliance
3. **API Key System**: 1Password-integrated key management with permissions
4. **Multi-Agent Support**: Concurrent connection handling with individual rate limits
5. **Process Management**: TUI-controlled server lifecycle with subprocess management

### Security Model
- **Authentication**: 1Password-stored API keys with user-configurable vault
- **Authorization**: Permission-based access control with Elastic write-back grants
- **Rate Limiting**: Per-API-key rate limits for untested agents
- **Input Validation**: Comprehensive validation following MCP security guidelines
- **Audit Logging**: Complete audit trail of all operations and connections

### Configuration Schema (Updated)
```yaml
# user_config.yaml additions
tcp_transport:
  enabled: false  # Default to STDIO mode
  port: 3000
  bind_address: "127.0.0.1"
  max_connections: 10
  connection_timeout_seconds: 300
  api_key_management:
    vault: "op://vault/item/field"  # User-configurable 1Password vault
    rate_limit_per_key: 60  # Requests per minute per API key
    untested_agent_limit: 10  # Lower limit for untested agents
  permissions:
    elastic_write_back: false  # Default permission for new keys
    max_query_results: 1000
    timeout_seconds: 30

# TUI Configuration
tui:
  enabled: false  # Default to headless mode
  refresh_interval_ms: 1000
  log_history_size: 1000
  server_management:
    restart_on_update: true
    graceful_shutdown_timeout: 30
  panels:
    connections:
      enabled: true
      show_details: true
      show_rate_limits: true
    tools:
      enabled: true
      show_metrics: true
    logs:
      enabled: true
      log_levels: ["INFO", "WARN", "ERROR"]
```

## Implementation Ready

The implementation plan is now complete with all user requirements incorporated. The architecture supports:

✅ **Multi-Agent TCP Transport** with 1Password API key management  
✅ **TUI Server Management** with subprocess control and restart capabilities  
✅ **Permission-Based Access Control** with Elastic write-back grants  
✅ **Per-API-Key Rate Limiting** for untested agents  
✅ **Full MCP Protocol Compliance** with stateful connections  
✅ **Graceful Shutdown** and process management  
✅ **Terminal Integration** for any environment (tmux, screen, etc.)  

**Ready to proceed with implementation on TUI-andTCP branch.**

## Enhanced TUI Detection Implementation

### Overview
The transport manager now includes enhanced TUI detection capabilities that automatically determine whether the MCP server should run in STDIO or TCP mode based on the execution context.

### Detection Strategies
The `_is_tui_parent()` method in `src/transport/transport_manager.py` implements a multi-layered detection approach:

#### 1. Environment Variable Detection (Primary)
- **Variable**: `DSHIELD_TUI_MODE`
- **Values**: `true`, `TRUE`, `True`, `1`, `yes`, `YES`, `Yes`
- **Priority**: Highest - most reliable detection method
- **Usage**: Set by TUI launcher when spawning server subprocess

#### 2. Parent Process Analysis
- **Method**: Analyzes parent process name and command line
- **Indicators**: `tui`, `textual`, `rich`, `curses`, `dshield-mcp-tui`, `mcp-tui`, `tui_launcher.py`
- **Terminal Multiplexers**: `tmux`, `screen`, `byobu`
- **Error Handling**: Graceful handling of `psutil.NoSuchProcess` and `psutil.AccessDenied`

#### 3. Current Process Command Line Analysis
- **Method**: Checks current process command line for TUI indicators
- **Indicators**: `tui_launcher.py`, `src.tui_launcher`, `-m src.tui_launcher`
- **Fallback**: Used when parent process detection fails

#### 4. Default Behavior
- **Fallback**: Returns `False` (STDIO mode) if no TUI indicators found
- **Safety**: Conservative approach ensures compatibility

### Debug Logging
Comprehensive debug logging tracks the detection process:
- Parent process information (PID, name, command line)
- Detection strategy results
- Error conditions and fallbacks
- Final detection decision

### Usage Examples

#### TUI Launcher Integration
```python
# TUI launcher sets environment variable
env = os.environ.copy()
env["DSHIELD_TUI_MODE"] = "true"

# Spawn server subprocess
server_process = subprocess.Popen(
    [sys.executable, "-m", "src.server_launcher"],
    env=env
)
```

#### Direct Server Execution
```bash
# STDIO mode (default)
python -m src.server_launcher

# TCP mode via environment variable
DSHIELD_TUI_MODE=true python -m src.server_launcher

# TCP mode via command line flag
python -m src.server_launcher --tcp
```

### Testing
Comprehensive test suite in `tests/test_enhanced_tui_detection.py` covers:
- Environment variable detection (true/false values)
- Parent process indicator detection
- Terminal multiplexer detection
- Current process command line detection
- Exception handling (NoSuchProcess, AccessDenied)
- Transport mode detection integration
- Debug logging verification
- Integration testing with actual TUI launcher

### Benefits
1. **Automatic Mode Selection**: No manual configuration required
2. **Robust Detection**: Multiple fallback strategies ensure reliability
3. **Error Resilience**: Graceful handling of process access issues
4. **Debug Visibility**: Comprehensive logging for troubleshooting
5. **Backward Compatibility**: Maintains existing STDIO behavior as default
