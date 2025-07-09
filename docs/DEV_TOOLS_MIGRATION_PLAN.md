# Dev Tools Migration Plan

This document outlines the iterative plan to migrate development tools tests from the `dev_tools/` directory into the formal pytest test suite in `tests/`.

## Overview

The `dev_tools/` directory contains 25+ test scripts that were created during development for debugging and feature validation. These scripts need to be migrated to the formal pytest suite to:

- Ensure consistent test patterns and mocking
- Enable CI/CD integration
- Provide better test isolation and reliability
- Standardize test reporting and coverage

## Current State Analysis

### Dev Tools Test Files (25 total)

#### **Simple Unit Tests** (Phase 1)
- `test_data_dictionary.py` - Data dictionary functionality (73 lines)
- `test_op_secrets.py` - 1Password integration (59 lines)

#### **Core Functionality Tests** (Phase 2)
- `test_server_startup.py` - Server startup validation (67 lines)
- `test_installation.py` - Installation verification (246 lines)
- `test_mcp_server.py` - MCP server functionality (235 lines)
- `test_mcp_queries.py` - MCP query testing (99 lines)

#### **Feature Tests** (Phase 3)
- `test_data_parsing.py` - Data parsing and field mapping (153 lines)
- `test_pagination.py` - Basic pagination (146 lines)
- `test_enhanced_pagination.py` - Enhanced pagination (194 lines)
- `test_enhanced_pagination_fixed.py` - Fixed pagination (217 lines)
- `test_enhanced_pagination_broad.py` - Broad pagination (185 lines)
- `test_enhanced_features.py` - Field selection, time ranges, aggregations (215 lines)

#### **Advanced Feature Tests** (Phase 4)
- `test_smart_query_optimization.py` - Query optimization (190 lines)
- `test_performance_metrics.py` - Performance tracking (192 lines)
- `test_streaming.py` - Event streaming (193 lines)
- `test_streaming_broad.py` - Broad streaming (106 lines)
- `test_smart_chunking.py` - Smart chunking (170 lines)

#### **Complex Integration Tests** (Phase 5)
- `test_campaign_analysis.py` - Campaign analysis (510 lines)
- `test_campaign_analysis_debug.py` - Campaign analysis debugging (459 lines)
- `test_attack_report_fix.py` - Attack report fixes (177 lines)
- `test_field_mapping.py` - Field mapping (221 lines)
- `test_user_configuration.py` - User configuration (438 lines)

#### **Debug Tools** (Phase 6 - Keep as-is)
- `debug_elasticsearch.py` - Elasticsearch debugging (220 lines)
- `diagnose_elasticsearch_data.py` - Data diagnosis (53 lines)
- `find_available_ips.py` - IP discovery (153 lines)
- `find_related_ip_debug.py` - Related IP debugging (29 lines)

## Migration Phases

### Phase 1: Data Dictionary and 1Password Integration
- **1.1 Data Dictionary tests**: ✅ Completed
- **1.2 1Password integration tests**: ✅ Completed

### Phase 2: Core Functionality
- **2.1 Import validation, DataProcessor, ContextInjector, and integration startup tests**: ✅ Completed
    - Created `tests/test_server_integration.py` covering:
        - Import validation for all core modules and clients
        - DataProcessor: initialization, event processing, summary generation, unique IP extraction, empty/invalid event handling
        - ContextInjector: initialization, context preparation, ChatGPT formatting, empty data handling
        - Integration startup: all components can be imported and initialized together
    - All tests pass and confirm robust integration of core server logic and context preparation.
- **2.2 MCP Server and Query Tests**: ✅ Completed
    - Created `tests/test_mcp_server.py` covering:
        - Server initialization and structure validation
        - Tool registration and MCP protocol handling
        - Core MCP tools: query_dshield_events, get_dshield_statistics, enrich_ip_with_dshield, get_data_dictionary
        - Server cleanup and error handling
        - Tool error handling with graceful failure recovery
    - All 11 tests pass with comprehensive async mocking and proper error handling
    - Fixed server config loading error handling to prevent crashes when user config fails to load

### Phase 3: ...

(Continue updating as migration progresses)

## Migration Guidelines

### **For Each Phase:**

1. **Create new test file** in `tests/` directory
2. **Use existing pytest patterns** from current test suite
3. **Apply proper mocking** (1Password, config loader, etc.)
4. **Add comprehensive test coverage** with multiple scenarios
5. **Update conftest.py** with shared fixtures if needed
6. **Run existing tests** to ensure no regressions
7. **Document any new fixtures** or test utilities

### **Test Structure Pattern:**
```python
@pytest.mark.asyncio
@patch('src.user_config.get_user_config')
@patch('src.config_loader._resolve_secrets')
@patch('src.config_loader.get_config')
async def test_feature_name(self, mock_get_config, mock_resolve_secrets, mock_user_config):
    """Test description."""
    # Setup
    mock_get_config.return_value = TEST_CONFIG
    mock_resolve_secrets.return_value = TEST_CONFIG
    
    # Test logic
    # Assertions
```

### **Success Criteria for Each Phase:**
- ✅ All new tests pass
- ✅ Existing tests still pass
- ✅ No real external dependencies called
- ✅ Proper mocking in place
- ✅ Good test coverage
- ✅ Clear test documentation

## Progress Tracking

### **Phase 1: Foundation & Simple Tests**
- [ ] 1.1 Data Dictionary Tests
- [ ] 1.2 1Password Integration Tests

### **Phase 2: Core Functionality Tests**
- [ ] 2.1 Server Startup & Installation Tests
- [ ] 2.2 MCP Server Tests

### **Phase 3: Feature Tests**
- [ ] 3.1 Data Parsing & Field Mapping Tests
- [ ] 3.2 Pagination Tests

### **Phase 4: Advanced Feature Tests**
- [ ] 4.1 Smart Query Optimization Tests
- [ ] 4.2 Performance Metrics Tests

### **Phase 5: Complex Integration Tests**
- [ ] 5.1 Campaign Analysis Tests
- [ ] 5.2 Streaming & Smart Chunking Tests

### **Phase 6: Debug & Utility Tests**
- [ ] 6.1 Debug Tools Assessment

## File Organization

### **New Test Files to Create:**
```
tests/
├── test_data_dictionary.py          # Phase 1.1
├── test_server_integration.py       # Phase 2.1
├── test_mcp_server.py               # Phase 2.2
├── test_data_parsing.py             # Phase 3.1
├── test_pagination.py               # Phase 3.2
├── test_query_optimization.py       # Phase 4.1
├── test_performance_metrics.py      # Phase 4.2
├── test_campaign_analysis.py        # Phase 5.1
└── test_streaming.py                # Phase 5.2
```

### **Files to Keep in dev_tools/ (Debug Tools):**
```
dev_tools/
├── debug_elasticsearch.py           # Keep as debug tool
├── diagnose_elasticsearch_data.py   # Keep as debug tool
├── find_available_ips.py           # Keep as debug tool
└── find_related_ip_debug.py        # Keep as debug tool
```

## Risk Mitigation

### **High-Risk Areas:**
1. **Campaign Analysis Tests** - Complex integration, may need significant refactoring
2. **Pagination Tests** - Multiple variations, need careful consolidation
3. **Real Data Dependencies** - Some tests may rely on specific data that needs mocking

### **Mitigation Strategies:**
1. **Start with simple tests** to establish patterns
2. **Use comprehensive mocking** to avoid external dependencies
3. **Create mock data fixtures** for complex scenarios
4. **Test incrementally** - one phase at a time
5. **Maintain existing dev_tools** until migration is complete

## Completion Criteria

The migration is complete when:
- [ ] All appropriate dev_tools tests are migrated to pytest
- [ ] All new tests pass consistently
- [ ] Existing test suite continues to pass
- [ ] Debug tools remain available for development
- [ ] Documentation is updated
- [ ] CI/CD pipeline includes all new tests

## Next Steps

1. **Start with Phase 1.1**: Migrate data dictionary tests
2. **Establish patterns**: Use as template for subsequent phases
3. **Iterate through phases**: One phase per week
4. **Validate progress**: Ensure no regressions at each phase
5. **Update documentation**: Keep this plan current with progress 