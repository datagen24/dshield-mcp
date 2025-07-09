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

### **Phase 1: Foundation & Simple Tests** (Week 1)
**Goal**: Establish patterns and migrate the simplest tests first.

#### **1.1 Data Dictionary Tests** (Priority: High, Complexity: Low) ✅ COMPLETED
- **Source**: `dev_tools/test_data_dictionary.py`
- **Target**: `tests/test_data_dictionary.py`
- **Why first**: Simple unit tests, no external dependencies, pure function testing
- **Pattern**: Use existing `tests/test_op_secrets.py` as template

**Tests created**:
```python
def test_get_field_descriptions()
def test_get_query_examples()
def test_get_data_patterns()
def test_get_analysis_guidelines()
def test_get_initial_prompt()
def test_json_format()
def test_field_descriptions_content()
def test_query_examples_content()
def test_data_patterns_content()
def test_analysis_guidelines_content()
def test_initial_prompt_content()
def test_data_consistency()
```

**Implementation Notes**:
- Created comprehensive test suite with 12 test methods
- Fixed data structure assumptions to match actual DataDictionary implementation
- Added content validation tests for each method
- Implemented data consistency checks between different methods
- All tests pass successfully (12/12)

#### **1.2 1Password Integration Tests** (Priority: High, Complexity: Low) ✅ COMPLETED
- **Source**: `dev_tools/test_op_secrets.py`
- **Target**: Enhanced existing `tests/test_op_secrets.py`
- **Why second**: Already had good pytest pattern, just needed to add dev_tools coverage

**Tests created/enhanced**:
```python
def test_config_loading_with_secrets_resolution()
def test_config_loading_with_nested_structures()
def test_config_loading_with_op_cli_unavailable()
def test_config_loading_with_op_cli_errors()
def test_resolve_secrets_function()
def test_config_loading_with_no_secrets()
def test_config_file_not_found()
def test_config_file_invalid_yaml()
def test_config_file_not_dict()
# Plus all OnePasswordSecrets unit tests
```

**Implementation Notes**:
- Added comprehensive integration tests for config loading and op:// URL resolution
- Covered error handling for CLI unavailable and CLI errors
- Removed database connection string test (no DB integration in project)
- All tests pass successfully (22/22)

### **Phase 2: Core Functionality Tests** (Week 2)
**Goal**: Migrate tests that validate core system functionality.

#### **2.1 Server Startup & Installation Tests** (Priority: High, Complexity: Medium)
- **Source**: `dev_tools/test_server_startup.py`, `dev_tools/test_installation.py`
- **Target**: `tests/test_server_integration.py`

**Tests to create**:
```python
def test_server_startup()
def test_tool_registration()
def test_dependency_verification()
def test_configuration_loading()
```

#### **2.2 MCP Server Tests** (Priority: High, Complexity: Medium)
- **Source**: `dev_tools/test_mcp_server.py`
- **Target**: `tests/test_mcp_server.py`

**Tests to create**:
```python
def test_mcp_server_initialization()
def test_tool_registration()
def test_basic_queries()
def test_error_handling()
```

### **Phase 3: Feature Tests** (Week 3)
**Goal**: Migrate tests for specific features and capabilities.

#### **3.1 Data Parsing & Field Mapping Tests** (Priority: Medium, Complexity: Medium)
- **Source**: `dev_tools/test_data_parsing.py`
- **Target**: `tests/test_data_parsing.py`

**Tests to create**:
```python
def test_field_mapping()
def test_data_parsing()
def test_ecs_field_support()
```

#### **3.2 Pagination Tests** (Priority: Medium, Complexity: High)
- **Source**: `dev_tools/test_pagination.py`, `dev_tools/test_enhanced_pagination*.py`
- **Target**: `tests/test_pagination.py`

**Tests to create**:
```python
def test_basic_pagination()
def test_cursor_pagination()
def test_field_selection_with_pagination()
def test_pagination_metadata()
```

### **Phase 4: Advanced Feature Tests** (Week 4)
**Goal**: Migrate complex feature tests that require more setup.

#### **4.1 Smart Query Optimization Tests** (Priority: Medium, Complexity: High)
- **Source**: `dev_tools/test_smart_query_optimization.py`
- **Target**: `tests/test_query_optimization.py`

**Tests to create**:
```python
def test_size_estimation()
def test_field_optimization()
def test_fallback_strategies()
```

#### **4.2 Performance Metrics Tests** (Priority: Low, Complexity: Medium)
- **Source**: `dev_tools/test_performance_metrics.py`
- **Target**: `tests/test_performance_metrics.py`

**Tests to create**:
```python
def test_query_performance_tracking()
def test_metrics_inclusion()
```

### **Phase 5: Complex Integration Tests** (Week 5)
**Goal**: Migrate tests that require real data or complex scenarios.

#### **5.1 Campaign Analysis Tests** (Priority: High, Complexity: Very High)
- **Source**: `dev_tools/test_campaign_analysis*.py`
- **Target**: `tests/test_campaign_analysis.py`

**Tests to create**:
```python
def test_campaign_detection()
def test_correlation_pipeline()
def test_ioc_expansion()
```

**Note**: May require significant refactoring and mock data

#### **5.2 Streaming & Smart Chunking Tests** (Priority: Low, Complexity: High)
- **Source**: `dev_tools/test_streaming*.py`, `dev_tools/test_smart_chunking.py`
- **Target**: `tests/test_streaming.py`

**Tests to create**:
```python
def test_event_streaming()
def test_session_context_chunking()
```

### **Phase 6: Debug & Utility Tests** (Week 6)
**Goal**: Migrate or deprecate debug tools.

#### **6.1 Debug Tools Assessment** (Priority: Low, Complexity: Variable)
- **Source**: `debug_elasticsearch.py`, `diagnose_elasticsearch_data.py`
- **Decision**: Keep as standalone debug tools (don't migrate to pytest)
- **Reason**: These are development utilities, not unit tests

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