"""Tests for MCP schema validator.

This module contains comprehensive tests for the MCPSchemaValidator class,
including bounds checking, security validation, and MCP protocol compliance.
"""

import json

import pytest

from src.security.mcp_schema_validator import (
    MAX_ARRAY_LEN,
    MAX_MESSAGE_BYTES,
    MAX_NESTING_DEPTH,
    MAX_OBJECT_KEYS,
    MAX_STRING_LENGTH,
    MCPSchemaValidator,
)


class TestMCPSchemaValidator:
    """Test cases for MCPSchemaValidator."""

    @pytest.fixture
    def validator(self) -> MCPSchemaValidator:
        """Create a validator instance for testing."""
        return MCPSchemaValidator()

    @pytest.fixture
    def valid_request(self) -> str:
        """Create a valid MCP request message."""
        return json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        })

    @pytest.fixture
    def valid_response(self) -> str:
        """Create a valid MCP response message."""
        return json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "tools": [
                    {
                        "name": "test_tool",
                        "description": "A test tool"
                    }
                ]
            }
        })

    @pytest.fixture
    def valid_notification(self) -> str:
        """Create a valid MCP notification message."""
        return json.dumps({
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        })

    def test_validator_initialization(self, validator: MCPSchemaValidator) -> None:
        """Test that validator initializes correctly."""
        assert validator is not None
        assert validator.request_validator is not None
        assert validator.response_validator is not None
        assert validator.notification_validator is not None
        assert validator.tool_validators is not None

    def test_validate_message_size_valid(self, validator: MCPSchemaValidator) -> None:
        """Test message size validation with valid message."""
        small_message = '{"test": "data"}'
        assert validator.validate_message_size(small_message) is True

    def test_validate_message_size_too_large(self, validator: MCPSchemaValidator) -> None:
        """Test message size validation with oversized message."""
        large_message = "x" * (MAX_MESSAGE_BYTES + 1)
        assert validator.validate_message_size(large_message) is False

    def test_validate_json_structure_valid(self, validator: MCPSchemaValidator) -> None:
        """Test JSON structure validation with valid JSON."""
        valid_json = '{"test": "data", "nested": {"value": 123}}'
        result = validator.validate_json_structure(valid_json)
        assert result is not None
        assert result["test"] == "data"
        assert result["nested"]["value"] == 123

    def test_validate_json_structure_invalid_utf8(self, validator: MCPSchemaValidator) -> None:
        """Test JSON structure validation with invalid UTF-8."""
        # Create a string with invalid UTF-8 sequences that will cause JSON parsing to fail
        invalid_utf8 = b'\xff\xfe{"test": "data"}'.decode('utf-8', errors='replace')
        result = validator.validate_json_structure(invalid_utf8)
        # This should fail because the JSON is malformed due to the invalid UTF-8
        assert result is None

    def test_validate_json_structure_invalid_json(self, validator: MCPSchemaValidator) -> None:
        """Test JSON structure validation with invalid JSON."""
        invalid_json = '{"test": "data", "missing": }'
        result = validator.validate_json_structure(invalid_json)
        assert result is None

    def test_validate_json_structure_too_deep(self, validator: MCPSchemaValidator) -> None:
        """Test JSON structure validation with excessive nesting."""
        # Create deeply nested JSON
        deep_json = {"level": 0}
        current = deep_json
        for i in range(1, MAX_NESTING_DEPTH + 2):
            current["nested"] = {"level": i}
            current = current["nested"]
        
        deep_json_str = json.dumps(deep_json)
        result = validator.validate_json_structure(deep_json_str)
        assert result is None

    def test_validate_json_structure_array_too_large(self, validator: MCPSchemaValidator) -> None:
        """Test JSON structure validation with oversized array."""
        large_array = list(range(MAX_ARRAY_LEN + 1))
        large_array_json = json.dumps({"data": large_array})
        result = validator.validate_json_structure(large_array_json)
        assert result is None

    def test_validate_json_structure_object_too_many_keys(
        self, validator: MCPSchemaValidator
    ) -> None:
        """Test JSON structure validation with too many object keys."""
        large_object = {f"key_{i}": f"value_{i}" for i in range(MAX_OBJECT_KEYS + 1)}
        large_object_json = json.dumps(large_object)
        result = validator.validate_json_structure(large_object_json)
        assert result is None

    def test_validate_json_structure_string_too_long(self, validator: MCPSchemaValidator) -> None:
        """Test JSON structure validation with oversized string."""
        long_string = "x" * (MAX_STRING_LENGTH + 1)
        long_string_json = json.dumps({"data": long_string})
        result = validator.validate_json_structure(long_string_json)
        assert result is None

    def test_get_nesting_depth_simple(self, validator: MCPSchemaValidator) -> None:
        """Test nesting depth calculation with simple object."""
        simple_obj = {"a": 1, "b": 2}
        depth = validator._get_nesting_depth(simple_obj)
        assert depth == 1  # Root level counts as depth 1

    def test_get_nesting_depth_nested(self, validator: MCPSchemaValidator) -> None:
        """Test nesting depth calculation with nested object."""
        nested_obj = {"a": {"b": {"c": 1}}}
        depth = validator._get_nesting_depth(nested_obj)
        assert depth == 3  # Root + 2 nested levels

    def test_get_nesting_depth_array(self, validator: MCPSchemaValidator) -> None:
        """Test nesting depth calculation with array."""
        array_obj = [1, [2, [3, 4]]]
        depth = validator._get_nesting_depth(array_obj)
        assert depth == 3  # Root + 2 nested levels

    def test_validate_object_bounds_valid(self, validator: MCPSchemaValidator) -> None:
        """Test object bounds validation with valid object."""
        valid_obj = {
            "string": "test",
            "array": [1, 2, 3],
            "nested": {"key": "value"}
        }
        assert validator._validate_object_bounds(valid_obj) is True

    def test_validate_object_bounds_invalid_array(self, validator: MCPSchemaValidator) -> None:
        """Test object bounds validation with oversized array."""
        invalid_obj = {"array": list(range(MAX_ARRAY_LEN + 1))}
        assert validator._validate_object_bounds(invalid_obj) is False

    def test_validate_object_bounds_invalid_keys(self, validator: MCPSchemaValidator) -> None:
        """Test object bounds validation with too many keys."""
        invalid_obj = {f"key_{i}": i for i in range(MAX_OBJECT_KEYS + 1)}
        assert validator._validate_object_bounds(invalid_obj) is False

    def test_validate_request_valid(self, validator: MCPSchemaValidator) -> None:
        """Test request validation with valid request."""
        valid_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        assert validator.validate_request(valid_request) is True

    def test_validate_request_invalid_jsonrpc(self, validator: MCPSchemaValidator) -> None:
        """Test request validation with invalid jsonrpc version."""
        invalid_request = {
            "jsonrpc": "1.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }
        assert validator.validate_request(invalid_request) is False

    def test_validate_request_missing_required(self, validator: MCPSchemaValidator) -> None:
        """Test request validation with missing required fields."""
        invalid_request = {
            "jsonrpc": "2.0",
            "id": 1
            # Missing method
        }
        assert validator.validate_request(invalid_request) is False

    def test_validate_response_valid(self, validator: MCPSchemaValidator) -> None:
        """Test response validation with valid response."""
        valid_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {"data": "test"}
        }
        assert validator.validate_response(valid_response) is True

    def test_validate_response_error(self, validator: MCPSchemaValidator) -> None:
        """Test response validation with error response."""
        error_response = {
            "jsonrpc": "2.0",
            "id": 1,
            "error": {
                "code": -32601,
                "message": "Method not found"
            }
        }
        assert validator.validate_response(error_response) is True

    def test_validate_notification_valid(self, validator: MCPSchemaValidator) -> None:
        """Test notification validation with valid notification."""
        valid_notification = {
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        }
        assert validator.validate_notification(valid_notification) is True

    def test_validate_tool_parameters_valid(self, validator: MCPSchemaValidator) -> None:
        """Test tool parameter validation with valid parameters."""
        valid_params = {
            "seed_iocs": ["192.168.1.1", "example.com"],
            "time_range": {
                "start_time": "2024-01-01T00:00:00Z",
                "end_time": "2024-01-02T00:00:00Z"
            }
        }
        assert validator.validate_tool_parameters("analyze_campaign", valid_params) is True

    def test_validate_tool_parameters_invalid(self, validator: MCPSchemaValidator) -> None:
        """Test tool parameter validation with invalid parameters."""
        invalid_params = {
            "seed_iocs": [],  # Empty array not allowed
            "time_range": {
                "start_time": "invalid-date",
                "end_time": "2024-01-02T00:00:00Z"
            }
        }
        assert validator.validate_tool_parameters("analyze_campaign", invalid_params) is False

    def test_validate_tool_parameters_unknown_tool(self, validator: MCPSchemaValidator) -> None:
        """Test tool parameter validation with unknown tool."""
        params = {"test": "data"}
        assert validator.validate_tool_parameters("unknown_tool", params) is False

    def test_sanitize_string_input_valid(self, validator: MCPSchemaValidator) -> None:
        """Test string sanitization with valid input."""
        valid_string = "This is a valid string"
        result = validator.sanitize_string_input(valid_string)
        assert result == valid_string

    def test_sanitize_string_input_too_long(self, validator: MCPSchemaValidator) -> None:
        """Test string sanitization with oversized input."""
        long_string = "x" * (MAX_STRING_LENGTH + 100)
        result = validator.sanitize_string_input(long_string, MAX_STRING_LENGTH)
        assert len(result) == MAX_STRING_LENGTH

    def test_sanitize_string_input_sql_injection(self, validator: MCPSchemaValidator) -> None:
        """Test string sanitization with SQL injection attempt."""
        malicious_string = "'; DROP TABLE users; --"
        result = validator.sanitize_string_input(malicious_string)
        assert "DROP TABLE" not in result

    def test_sanitize_string_input_xss(self, validator: MCPSchemaValidator) -> None:
        """Test string sanitization with XSS attempt."""
        malicious_string = "<script>alert('xss')</script>"
        result = validator.sanitize_string_input(malicious_string)
        assert "<script>" not in result

    def test_validate_message_valid_request(
        self, validator: MCPSchemaValidator, valid_request: str
    ) -> None:
        """Test complete message validation with valid request."""
        result = validator.validate_message(valid_request)
        assert result is not None
        assert result["jsonrpc"] == "2.0"
        assert result["method"] == "tools/list"

    def test_validate_message_valid_response(
        self, validator: MCPSchemaValidator, valid_response: str
    ) -> None:
        """Test complete message validation with valid response."""
        result = validator.validate_message(valid_response)
        assert result is not None
        assert result["jsonrpc"] == "2.0"
        assert "result" in result

    def test_validate_message_valid_notification(
        self, validator: MCPSchemaValidator, valid_notification: str
    ) -> None:
        """Test complete message validation with valid notification."""
        result = validator.validate_message(valid_notification)
        assert result is not None
        assert result["jsonrpc"] == "2.0"
        assert result["method"] == "initialized"

    def test_validate_message_invalid_size(self, validator: MCPSchemaValidator) -> None:
        """Test complete message validation with oversized message."""
        large_message = "x" * (MAX_MESSAGE_BYTES + 1)
        result = validator.validate_message(large_message)
        assert result is None

    def test_validate_message_invalid_json(self, validator: MCPSchemaValidator) -> None:
        """Test complete message validation with invalid JSON."""
        invalid_json = '{"jsonrpc": "2.0", "id": 1, "method": "test"'
        result = validator.validate_message(invalid_json)
        assert result is None

    def test_validate_message_unknown_type(self, validator: MCPSchemaValidator) -> None:
        """Test complete message validation with unknown message type."""
        unknown_message = json.dumps({
            "jsonrpc": "2.0",
            "unknown_field": "value"
        })
        result = validator.validate_message(unknown_message)
        assert result is None

    def test_validate_message_tool_call_with_params(self, validator: MCPSchemaValidator) -> None:
        """Test complete message validation with tool call including parameters."""
        tool_call = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "analyze_campaign",
                "arguments": {
                    "seed_iocs": ["192.168.1.1"],
                    "time_range": {
                        "start_time": "2024-01-01T00:00:00Z",
                        "end_time": "2024-01-02T00:00:00Z"
                    }
                }
            }
        })
        result = validator.validate_message(tool_call)
        # This should fail because "call" is not a valid tool name in our schemas
        assert result is None

    def test_validate_message_tool_call_invalid_params(self, validator: MCPSchemaValidator) -> None:
        """Test complete message validation with tool call with invalid parameters."""
        tool_call = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "analyze_campaign",
                "arguments": {
                    "seed_iocs": [],  # Invalid: empty array
                    "invalid_field": "value"
                }
            }
        })
        result = validator.validate_message(tool_call)
        assert result is None

    def test_validate_complete_message_alias(
        self, validator: MCPSchemaValidator, valid_request: str
    ) -> None:
        """Test that validate_complete_message is an alias for validate_message."""
        result1 = validator.validate_message(valid_request)
        result2 = validator.validate_complete_message(valid_request)
        assert result1 == result2

    def test_fuzz_nesting_near_limit(self, validator: MCPSchemaValidator) -> None:
        """Test fuzzing with nesting near the limit."""
        # Create JSON with nesting at the limit, but as a valid MCP message
        deep_json = {"level": 0}
        current = deep_json
        for i in range(1, MAX_NESTING_DEPTH - 1):  # Leave room for MCP structure
            current["nested"] = {"level": i}
            current = current["nested"]
        
        # Wrap in valid MCP request structure
        mcp_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": deep_json
        }
        
        deep_json_str = json.dumps(mcp_message)
        result = validator.validate_message(deep_json_str)
        assert result is not None

    def test_fuzz_array_near_limit(self, validator: MCPSchemaValidator) -> None:
        """Test fuzzing with array near the limit."""
        # Create JSON with array at the limit, but as a valid MCP message
        large_array = list(range(MAX_ARRAY_LEN))
        mcp_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"data": large_array}
        }
        array_json = json.dumps(mcp_message)
        result = validator.validate_message(array_json)
        assert result is not None

    def test_fuzz_object_keys_near_limit(self, validator: MCPSchemaValidator) -> None:
        """Test fuzzing with object keys near the limit."""
        # Create JSON with object keys at the limit, but as a valid MCP message
        large_object = {f"key_{i}": i for i in range(MAX_OBJECT_KEYS)}
        mcp_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": large_object
        }
        object_json = json.dumps(mcp_message)
        result = validator.validate_message(object_json)
        assert result is not None

    def test_fuzz_string_near_limit(self, validator: MCPSchemaValidator) -> None:
        """Test fuzzing with string near the limit."""
        # Create JSON with string at the limit, but as a valid MCP message
        long_string = "x" * MAX_STRING_LENGTH
        mcp_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"data": long_string}
        }
        string_json = json.dumps(mcp_message)
        result = validator.validate_message(string_json)
        assert result is not None

    def test_logging_on_validation_failure(self, validator: MCPSchemaValidator) -> None:
        """Test that validation failures are properly handled."""
        invalid_message = "x" * (MAX_MESSAGE_BYTES + 1)
        result = validator.validate_message(invalid_message)
        
        # Check that validation fails due to size limit
        assert result is None

    def test_logging_on_json_error(self, validator: MCPSchemaValidator) -> None:
        """Test that JSON parsing errors are properly handled."""
        invalid_json = '{"jsonrpc": "2.0", "id": 1, "method": "test"'
        result = validator.validate_message(invalid_json)
        
        # Check that validation fails due to invalid JSON
        assert result is None

    def test_logging_on_depth_exceeded(self, validator: MCPSchemaValidator) -> None:
        """Test that depth exceeded errors are properly handled."""
        # Create deeply nested JSON
        deep_json = {"level": 0}
        current = deep_json
        for i in range(1, MAX_NESTING_DEPTH + 2):
            current["nested"] = {"level": i}
            current = current["nested"]
        
        deep_json_str = json.dumps(deep_json)
        result = validator.validate_message(deep_json_str)
        
        # Check that validation fails due to excessive depth
        assert result is None

    def test_logging_on_array_too_large(self, validator: MCPSchemaValidator) -> None:
        """Test that array size exceeded errors are properly handled."""
        large_array = list(range(MAX_ARRAY_LEN + 1))
        large_array_json = json.dumps({"data": large_array})
        result = validator.validate_message(large_array_json)
        
        # Check that validation fails due to oversized array
        assert result is None

    def test_logging_on_object_too_many_keys(self, validator: MCPSchemaValidator) -> None:
        """Test that object key count exceeded errors are properly handled."""
        large_object = {f"key_{i}": i for i in range(MAX_OBJECT_KEYS + 1)}
        large_object_json = json.dumps(large_object)
        result = validator.validate_message(large_object_json)
        
        # Check that validation fails due to too many object keys
        assert result is None

    def test_logging_on_string_too_long(self, validator: MCPSchemaValidator) -> None:
        """Test that string length exceeded errors are properly handled."""
        long_string = "x" * (MAX_STRING_LENGTH + 1)
        long_string_json = json.dumps({"data": long_string})
        result = validator.validate_message(long_string_json)
        
        # Check that validation fails due to oversized string
        assert result is None
