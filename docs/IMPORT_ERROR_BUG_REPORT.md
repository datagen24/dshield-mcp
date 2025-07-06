# Bug Report: Module Import Error Preventing MCP Server Startup

## Issue Summary
The DShield MCP server fails to start due to incorrect import statements in multiple source files. The error occurs when trying to import modules from the `models` package.

## Error Details
```
Traceback (most recent call last):
  File "/Users/speterson/src/dshield-mcp/mcp_server.py", line 21, in <module>
    from src.elasticsearch_client import ElasticsearchClient
  File "/Users/speterson/src/dshield-mcp/src/elasticsearch_client.py", line 16, in <module>
    from models import SecurityEvent, ElasticsearchQuery, QueryFilter
ModuleNotFoundError: No module named 'models'
```

## Root Cause
Multiple files in the `src` directory are using incorrect import statements:
- `src/elasticsearch_client.py` line 16: `from models import SecurityEvent, ElasticsearchQuery, QueryFilter`
- `src/campaign_analyzer.py` line 15: `from models import SecurityEvent`
- `src/data_processor.py` line 14: `from models import (`
- `src/context_injector.py` line 12: `from models import SecurityEvent, ThreatIntelligence, AttackReport, SecuritySummary`
- `src/dshield_client.py` line 16: `from models import ThreatIntelligence`

The imports should be relative to the `src` package, not absolute imports.

## Affected Files
1. `src/elasticsearch_client.py`
2. `src/campaign_analyzer.py`
3. `src/data_processor.py`
4. `src/context_injector.py`
5. `src/dshield_client.py`

## Impact
- MCP server cannot start
- All DShield MCP functionality is unavailable
- Users cannot connect to the MCP server

## Proposed Solution
Fix all import statements to use the correct relative imports:
- Change `from models import` to `from .models import` or `from src.models import`
- Ensure all imports are consistent across the codebase

## Priority
**High** - This is a blocking issue that prevents the entire system from functioning.

## Steps to Reproduce
1. Try to start the MCP server: `python mcp_server.py`
2. Observe the ModuleNotFoundError

## Expected Behavior
MCP server should start successfully without import errors.

## Environment
- Python 3.x
- macOS (darwin 24.5.0)
- DShield MCP project

## Related Issues
None identified yet.

---
**Issue ID**: IMPORT_ERROR_001
**Status**: Open
**Assigned**: TBD
**Created**: 2025-07-06 