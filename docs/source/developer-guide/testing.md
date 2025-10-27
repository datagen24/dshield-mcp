# Testing Guide

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

## Running Tests

### All Tests

```bash
# Run all tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=src --cov-report=html

# Run specific test file
uv run pytest tests/mcp/test_mcp_server_refactored.py

# Run single test
uv run pytest tests/mcp/test_mcp_server_refactored.py::test_server_initialization -v
```

### By Marker

```bash
# Unit tests only
uv run pytest -m unit

# Integration tests only
uv run pytest -m integration

# Exclude slow tests
uv run pytest -m "not slow"
```

## Pytest Configuration

### Markers

Defined in `pyproject.toml`:

- `@pytest.mark.unit`: Unit tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.slow`: Slow-running tests

### Key Fixtures

**Location**: `conftest.py`

- Blocks 1Password CLI calls in tests
- Mocks Elasticsearch with `_FakeES` class
- Blocks subprocess/process spawning
- Provides custom event loop for async tests

### Fast Test Execution

Environment variables for fast test runs:

- `MCP_TEST_FAST`: Enable fast mode for MCP tests
- `TUI_FAST`: Enable fast mode for TUI tests
- `TUI_HEADLESS`: Run TUI tests in headless mode

**Important**: All external dependencies are mocked (1Password, Elasticsearch, subprocess)

## TUI Tests

TUI tests run in headless mode to avoid spawning terminal I/O threads:

```bash
# Run TUI tests in headless mode (default in CI)
pytest tests/tui/

# Manual validation (full TUI)
unset TUI_HEADLESS TUI_FAST && pytest tests/tui/
```

### Features

- Uses null driver and disables UI refreshes
- Some stress tests shortened in CI
- Validates functionality without visual rendering

## Writing Tests

### Unit Test Example

```python
import pytest
from src.elasticsearch_client import ElasticsearchClient

@pytest.mark.unit
async def test_query_builder():
    """Test query builder constructs correct Elasticsearch query."""
    client = ElasticsearchClient(config={})
    query = await client.build_query(
        index="test-*",
        filters={"field": "value"}
    )
    assert query["query"]["bool"]["must"][0]["match"]["field"] == "value"
```

### Integration Test Example

```python
import pytest
from src.mcp_server import DShieldMCPServer

@pytest.mark.integration
async def test_end_to_end_query(mock_elasticsearch):
    """Test complete query flow through MCP server."""
    server = DShieldMCPServer()
    await server.initialize()

    result = await server.handle_tool_call(
        "query_dshield_events",
        {"query": "test", "limit": 10}
    )

    assert result["total"] > 0
    assert len(result["events"]) <= 10
```

### Mocking External Dependencies

```python
import pytest
from unittest.mock import AsyncMock, patch

@pytest.fixture
def mock_dshield_api():
    """Mock DShield API client."""
    with patch('src.dshield_client.DShieldClient') as mock:
        mock.return_value.get_ip_info = AsyncMock(
            return_value={"reputation": "malicious"}
        )
        yield mock

async def test_with_mocked_api(mock_dshield_api):
    """Test using mocked DShield API."""
    # Test code here
    pass
```

## Coverage

### Generate Coverage Report

```bash
# Run tests with coverage
uv run pytest --cov=src --cov-report=html

# Open coverage report
open htmlcov/index.html
```

### Coverage Configuration

**Location**: `pyproject.toml`

```toml
[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/test_*",
    "*/__pycache__/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "@(abc\\.)?abstractmethod",
]
```

## Best Practices

### Test Organization

1. **One test file per module**: `test_elasticsearch_client.py` tests `elasticsearch_client.py`
2. **Group related tests in classes**: Use `TestClassName` for logical grouping
3. **Descriptive test names**: `test_query_builder_with_date_range`
4. **Use markers**: Tag tests with `@pytest.mark.unit` or `@pytest.mark.integration`

### Mocking

1. **Mock external dependencies**: Never make real API calls in tests
2. **Use fixtures**: Share common mocks across tests
3. **Verify mock calls**: Use `assert_called_with()` to verify behavior
4. **Mock at the right level**: Mock the lowest level that makes sense

### Async Testing

1. **Use pytest-asyncio**: All async tests must use `async def`
2. **Await all async calls**: Don't forget `await` keyword
3. **Mock async functions**: Use `AsyncMock` for async functions
4. **Clean up resources**: Use `try/finally` or fixtures for cleanup

### Assertions

1. **Use specific assertions**: `assert x == 5` not `assert x`
2. **Test one thing**: Each test should verify one behavior
3. **Provide clear messages**: Use `assert x == 5, f"Expected 5, got {x}"`
4. **Test edge cases**: Empty inputs, None values, boundary conditions

## Continuous Integration

Tests run automatically on:

- Every push to any branch
- Every pull request
- Scheduled nightly builds

**CI Environment Variables**:

- `MCP_TEST_FAST=1`
- `TUI_HEADLESS=1`
- `TUI_FAST=1`

All tests must pass before merging to main branch.
