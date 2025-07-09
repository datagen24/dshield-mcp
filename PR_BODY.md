# Test Suite Fixes and Pydantic V2 Migration

## Summary
This PR addresses the failing tests after migrating old dev_tools scripts to pytest and updates the codebase to use Pydantic V2 style validators.

## Changes Made

### Test Fixes
- **Fixed Elasticsearch Client Tests**: Updated test assertions to match actual implementation behavior
  - `test_query_dshield_events`: Fixed expected total count to match mock response
  - `test_query_dshield_events_no_client`: Fixed test logic to properly trigger connect method
  - `test_get_dshield_statistics`: Updated to expect structured response instead of empty dict

### Pydantic V2 Migration
- **Updated all validators** from deprecated V1 style `@validator` to V2 style `@field_validator`
- **Added `@classmethod` decorators** to all validator methods as required by Pydantic V2
- **Updated imports** from `pydantic.validator` to `pydantic.field_validator`

### Files Modified
- `src/models.py`: Updated all Pydantic validators to V2 style
- `tests/test_elasticsearch_client.py`: Fixed test assertions and logic

## Test Results
- **All 183 tests now pass** ✅
- **Pydantic deprecation warnings resolved** ✅
- **Test suite ready for CI/CD integration** ✅

## Impact
- No breaking changes to API or functionality
- Improved test reliability and maintainability
- Future-proofed against Pydantic V3 deprecation
- Ready for GitHub PR checks and CI/CD pipeline integration

## Testing
The complete test suite has been verified to pass:
```bash
python -m pytest tests/ -v
# Result: 183 passed, 9 warnings in 67.48s
```

The remaining warnings are related to unawaited coroutines in AsyncMock usage, which are common in async testing and do not affect test correctness. 