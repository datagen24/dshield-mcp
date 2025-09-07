# Test Coverage Implementation Plan

## Phase 1: Critical Path Coverage (Target: +15% coverage)

### 1. Campaign Analyzer Error Handling Tests
**File**: `src/campaign_analyzer.py` (324 missed lines)
**Priority**: CRITICAL

#### Test Cases to Implement:
1. **Empty/Invalid Input Handling**
   - `test_correlate_events_empty_seed_events`
   - `test_correlate_events_malformed_events`
   - `test_expand_indicators_empty_seed_iocs`
   - `test_expand_indicators_invalid_ioc_formats`

2. **Exception Path Testing**
   - `test_correlate_events_elasticsearch_failure`
   - `test_expand_indicators_network_timeout`
   - `test_build_campaign_timeline_data_corruption`
   - `test_score_campaign_invalid_confidence_values`

3. **Edge Case Scenarios**
   - `test_correlate_events_single_event_campaign`
   - `test_expand_indicators_max_depth_reached`
   - `test_build_campaign_timeline_timezone_edge_cases`
   - `test_score_campaign_boundary_values`

### 2. Campaign MCP Tools Parameter Validation
**File**: `src/campaign_mcp_tools.py` (206 missed lines)
**Priority**: HIGH

#### Test Cases to Implement:
1. **Input Validation**
   - `test_analyze_campaign_invalid_seed_indicators`
   - `test_analyze_campaign_invalid_time_range`
   - `test_analyze_campaign_invalid_confidence_threshold`
   - `test_get_campaign_timeline_invalid_campaign_id`

2. **Error Response Handling**
   - `test_analyze_campaign_elasticsearch_unavailable`
   - `test_get_campaign_timeline_campaign_not_found`
   - `test_expand_campaign_indicators_invalid_parameters`
   - `test_search_campaigns_invalid_filters`

### 3. Elasticsearch Client Error Scenarios
**File**: `src/elasticsearch_client.py` (438 missed lines)
**Priority**: HIGH

#### Test Cases to Implement:
1. **Connection Failures**
   - `test_elasticsearch_connection_timeout`
   - `test_elasticsearch_authentication_failure`
   - `test_elasticsearch_cluster_unavailable`
   - `test_elasticsearch_index_not_found`

2. **Query Error Handling**
   - `test_elasticsearch_query_syntax_error`
   - `test_elasticsearch_query_timeout`
   - `test_elasticsearch_pagination_errors`
   - `test_elasticsearch_aggregation_failures`

## Phase 2: Data Processing Coverage (Target: +8% coverage)

### 4. Data Processor Edge Cases
**File**: `src/data_processor.py` (234 missed lines)
**Priority**: MEDIUM

#### Test Cases to Implement:
1. **Data Validation**
   - `test_process_events_malformed_json`
   - `test_process_events_missing_required_fields`
   - `test_process_events_invalid_timestamps`
   - `test_process_events_oversized_payloads`

2. **Processing Pipeline Errors**
   - `test_process_events_memory_exhaustion`
   - `test_process_events_concurrent_modification`
   - `test_process_events_partial_failure_recovery`
   - `test_process_events_corrupted_data_handling`

## Implementation Strategy

### 1. Use Parametrized Tests
```python
@pytest.mark.parametrize("invalid_input,expected_error", [
    ([], ValueError),
    (None, TypeError),
    ([""], ValueError),
    (["invalid@format"], ValueError),
])
def test_analyze_campaign_invalid_inputs(invalid_input, expected_error):
    # Test implementation
```

### 2. Mock Only I/O Boundaries
- Mock Elasticsearch client calls
- Mock network requests
- Mock file system operations
- Test real logic with actual data structures

### 3. Focus on Error Paths
- Exception handling blocks
- Early return conditions
- Timeout scenarios
- Resource exhaustion cases

### 4. Test Real Behavior
- Use actual Pydantic models
- Test with realistic data
- Verify actual return values
- Test side effects and state changes

## Expected Coverage Impact
- **Phase 1**: +15% coverage (from 56.77% to ~72%)
- **Phase 2**: +8% coverage (from 72% to ~80%)
- **Total**: +23.23% coverage to reach 80% target

## Next Steps
1. Start with campaign_analyzer.py error handling tests
2. Implement parametrized test cases for edge scenarios
3. Focus on exception paths and boundary conditions
4. Verify coverage improvements after each batch of tests

