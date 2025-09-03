#!/usr/bin/env python3
"""Tests for MCP Error Handler functionality.

This module provides comprehensive testing for the MCPErrorHandler class,
ensuring proper JSON-RPC error responses, timeout handling, retry logic,
and error context capture for all MCP operations.

Test coverage includes:
- Error code generation and formatting
- Configuration validation
- Timeout handling
- Retry logic with exponential backoff
- Error logging and context capture
- Input validation
- Resource error handling
- External service error handling
"""

import asyncio
import pytest
import sys
from typing import Any
from unittest.mock import Mock

from src.mcp_error_handler import MCPErrorHandler, ErrorHandlingConfig


class TestErrorHandlingConfig:
    """Test ErrorHandlingConfig dataclass functionality."""

    def test_default_configuration(self) -> None:
        """Test that default configuration values are set correctly."""
        config = ErrorHandlingConfig()

        assert config.timeouts["elasticsearch_operations"] == 30.0
        assert config.timeouts["dshield_api_calls"] == 10.0
        assert config.timeouts["latex_compilation"] == 60.0
        assert config.timeouts["tool_execution"] == 120.0

        assert config.retry_settings["max_retries"] == 3
        assert config.retry_settings["base_delay"] == 1.0
        assert config.retry_settings["max_delay"] == 30.0
        assert config.retry_settings["exponential_base"] == 2.0

        assert config.logging["include_stack_traces"] is True
        assert config.logging["include_request_context"] is True
        assert config.logging["include_user_parameters"] is True
        assert config.logging["log_level"] == "INFO"

    def test_custom_configuration(self) -> None:
        """Test that custom configuration values can be set."""
        custom_timeouts = {"elasticsearch_operations": 60.0, "dshield_api_calls": 20.0}

        custom_retry = {"max_retries": 5, "base_delay": 2.0}

        config = ErrorHandlingConfig(timeouts=custom_timeouts, retry_settings=custom_retry)

        assert config.timeouts["elasticsearch_operations"] == 60.0
        assert config.timeouts["dshield_api_calls"] == 20.0
        assert config.retry_settings["max_retries"] == 5
        assert config.retry_settings["base_delay"] == 2.0


class TestMCPErrorHandler:
    """Test MCPErrorHandler class functionality."""

    def test_initialization_with_default_config(self) -> None:
        """Test error handler initialization with default configuration."""
        error_handler = MCPErrorHandler()

        assert error_handler.config is not None
        assert error_handler.logger is not None
        assert error_handler.PARSE_ERROR == -32700
        assert error_handler.INVALID_REQUEST == -32600
        assert error_handler.METHOD_NOT_FOUND == -32601
        assert error_handler.INVALID_PARAMS == -32602
        assert error_handler.INTERNAL_ERROR == -32603

    def test_initialization_with_custom_config(self) -> None:
        """Test error handler initialization with custom configuration."""
        custom_config = ErrorHandlingConfig()
        custom_config.timeouts["tool_execution"] = 300.0

        error_handler = MCPErrorHandler(custom_config)

        assert error_handler.config.timeouts["tool_execution"] == 300.0

    def test_config_validation_invalid_retries(self) -> None:
        """Test that invalid retry configuration raises ValueError."""
        config = ErrorHandlingConfig()
        config.retry_settings["max_retries"] = -1

        with pytest.raises(ValueError, match="max_retries must be non-negative"):
            MCPErrorHandler(config)

    def test_config_validation_invalid_delay(self) -> None:
        """Test that invalid delay configuration raises ValueError."""
        config = ErrorHandlingConfig()
        config.retry_settings["base_delay"] = 0

        with pytest.raises(ValueError, match="base_delay must be positive"):
            MCPErrorHandler(config)

    def test_config_validation_invalid_exponential_base(self) -> None:
        """Test that invalid exponential base raises ValueError."""
        config = ErrorHandlingConfig()
        config.retry_settings["exponential_base"] = 1.0

        with pytest.raises(ValueError, match="exponential_base must be greater than 1"):
            MCPErrorHandler(config)

    def test_config_validation_invalid_timeout(self) -> None:
        """Test that invalid timeout configuration raises ValueError."""
        config = ErrorHandlingConfig()
        config.timeouts["tool_execution"] = 0

        with pytest.raises(ValueError, match="timeout for tool_execution must be positive"):
            MCPErrorHandler(config)

    def test_create_error_basic(self) -> None:
        """Test basic error creation without optional parameters."""
        error_handler = MCPErrorHandler()

        error = error_handler.create_error(MCPErrorHandler.INVALID_PARAMS, "Invalid parameters")

        assert error["jsonrpc"] == "2.0"
        assert error["error"]["code"] == -32602
        assert error["error"]["message"] == "Invalid parameters"
        assert "data" not in error["error"]
        assert "id" not in error

    def test_create_error_with_data(self) -> None:
        """Test error creation with additional data."""
        error_handler = MCPErrorHandler()

        data = {"field": "time_range", "issue": "must be positive"}
        error = error_handler.create_error(
            MCPErrorHandler.INVALID_PARAMS, "Invalid parameters", data=data
        )

        assert error["error"]["data"] == data

    def test_create_error_with_request_id(self) -> None:
        """Test error creation with request ID."""
        error_handler = MCPErrorHandler()

        request_id = "req_123"
        error = error_handler.create_error(
            MCPErrorHandler.INVALID_PARAMS, "Invalid parameters", request_id=request_id
        )

        assert error["id"] == request_id

    def test_create_parse_error(self) -> None:
        """Test parse error creation."""
        error_handler = MCPErrorHandler()

        error = error_handler.create_parse_error("Invalid JSON")

        assert error["error"]["code"] == MCPErrorHandler.PARSE_ERROR
        assert error["error"]["message"] == "Invalid JSON"

    def test_create_invalid_request_error(self) -> None:
        """Test invalid request error creation."""
        error_handler = MCPErrorHandler()

        error = error_handler.create_invalid_request_error("Missing method")

        assert error["error"]["code"] == MCPErrorHandler.INVALID_REQUEST
        assert error["error"]["message"] == "Missing method"

    def test_create_method_not_found_error(self) -> None:
        """Test method not found error creation."""
        error_handler = MCPErrorHandler()

        error = error_handler.create_method_not_found_error("unknown_tool")

        assert error["error"]["code"] == MCPErrorHandler.METHOD_NOT_FOUND
        assert "unknown_tool" in error["error"]["message"]
        assert error["error"]["data"]["method"] == "unknown_tool"

    def test_create_invalid_params_error(self) -> None:
        """Test invalid parameters error creation."""
        error_handler = MCPErrorHandler()

        error = error_handler.create_invalid_params_error("Missing required field")

        assert error["error"]["code"] == MCPErrorHandler.INVALID_PARAMS
        assert error["error"]["message"] == "Missing required field"

    def test_create_internal_error(self) -> None:
        """Test internal error creation."""
        error_handler = MCPErrorHandler()

        error = error_handler.create_internal_error("Database connection failed")

        assert error["error"]["code"] == MCPErrorHandler.INTERNAL_ERROR
        assert error["error"]["message"] == "Database connection failed"

    def test_create_validation_error(self) -> None:
        """Test validation error creation."""
        error_handler = MCPErrorHandler()

        # Mock ValidationError
        mock_validation_error = Mock()
        mock_validation_error.errors.return_value = [
            {"loc": ("time_range",), "msg": "field required", "type": "value_error.missing"}
        ]

        error = error_handler.create_validation_error("test_tool", mock_validation_error)

        assert error["error"]["code"] == MCPErrorHandler.VALIDATION_ERROR
        assert "test_tool" in error["error"]["message"]
        assert error["error"]["data"]["tool"] == "test_tool"
        assert "suggestion" in error["error"]["data"]

    def test_create_timeout_error(self) -> None:
        """Test timeout error creation."""
        error_handler = MCPErrorHandler()

        error = error_handler.create_timeout_error("test_tool", 30.0)

        assert error["error"]["code"] == MCPErrorHandler.TIMEOUT_ERROR
        assert "test_tool" in error["error"]["message"]
        assert "30" in error["error"]["message"]
        assert error["error"]["data"]["timeout_seconds"] == 30.0
        assert "suggestion" in error["error"]["data"]

    def test_create_resource_error_not_found(self) -> None:
        """Test resource not found error creation."""
        error_handler = MCPErrorHandler()

        error = error_handler.create_resource_error(
            "dshield://events", "not_found", "Resource not found"
        )

        assert error["error"]["code"] == MCPErrorHandler.RESOURCE_NOT_FOUND
        assert error["error"]["data"]["resource_uri"] == "dshield://events"
        assert error["error"]["data"]["error_type"] == "not_found"

    def test_create_resource_error_access_denied(self) -> None:
        """Test resource access denied error creation."""
        error_handler = MCPErrorHandler()

        error = error_handler.create_resource_error(
            "dshield://events", "access_denied", "Permission denied"
        )

        assert error["error"]["code"] == MCPErrorHandler.RESOURCE_ACCESS_DENIED

    def test_create_external_service_error(self) -> None:
        """Test external service error creation."""
        error_handler = MCPErrorHandler()

        error = error_handler.create_external_service_error("Elasticsearch", "Connection refused")

        assert error["error"]["code"] == MCPErrorHandler.EXTERNAL_SERVICE_ERROR
        assert "Elasticsearch" in error["error"]["message"]
        assert "Connection refused" in error["error"]["message"]

    def test_create_rate_limit_error(self) -> None:
        """Test rate limit error creation."""
        error_handler = MCPErrorHandler()

        error = error_handler.create_rate_limit_error("DShield API", 60.0)

        assert error["error"]["code"] == MCPErrorHandler.RATE_LIMIT_ERROR
        assert "DShield API" in error["error"]["message"]
        assert error["error"]["data"]["retry_after_seconds"] == 60.0

    def test_validate_tool_exists_success(self) -> None:
        """Test successful tool validation."""
        error_handler = MCPErrorHandler()
        available_tools = ["tool1", "tool2", "tool3"]

        # Should not raise an exception
        error_handler.validate_tool_exists("tool2", available_tools)

    def test_validate_tool_exists_failure(self) -> None:
        """Test tool validation failure."""
        error_handler = MCPErrorHandler()
        available_tools = ["tool1", "tool2", "tool3"]

        with pytest.raises(ValueError, match="Tool 'unknown_tool' not found"):
            error_handler.validate_tool_exists("unknown_tool", available_tools)

    def test_validate_arguments_success(self) -> None:
        """Test successful argument validation."""
        error_handler = MCPErrorHandler()

        # Should not raise an exception
        error_handler.validate_arguments("test_tool", {"param1": "value1"}, {})

    def test_validate_arguments_failure(self) -> None:
        """Test argument validation failure."""
        error_handler = MCPErrorHandler()

        with pytest.raises(Exception):  # ValidationError or similar
            error_handler.validate_arguments("test_tool", "not_a_dict", {})

    @pytest.mark.asyncio
    async def test_execute_with_timeout_success(self) -> None:
        """Test successful timeout execution."""
        error_handler = MCPErrorHandler()

        async def successful_operation() -> str:
            await asyncio.sleep(0.1)
            return "success"

        result = await error_handler.execute_with_timeout(
            "test_operation", successful_operation(), timeout_seconds=1.0
        )

        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_with_timeout_failure(self) -> None:
        """Test timeout execution failure."""
        error_handler = MCPErrorHandler()

        async def slow_operation() -> str:
            await asyncio.sleep(2.0)
            return "success"

        with pytest.raises(asyncio.TimeoutError):
            await error_handler.execute_with_timeout(
                "test_operation", slow_operation(), timeout_seconds=0.1
            )

    @pytest.mark.asyncio
    async def test_execute_with_timeout_default(self) -> None:
        """Test timeout execution with default timeout."""
        error_handler = MCPErrorHandler()

        async def successful_operation() -> str:
            await asyncio.sleep(0.1)
            return "success"

        result = await error_handler.execute_with_timeout("test_operation", successful_operation())

        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_with_retry_success_first_attempt(self) -> None:
        """Test successful retry execution on first attempt."""
        error_handler = MCPErrorHandler()

        async def successful_operation() -> str:
            return "success"

        result = await error_handler.execute_with_retry("test_operation", successful_operation())

        assert result == "success"

    @pytest.mark.asyncio
    async def test_execute_with_retry_success_after_failure(self) -> None:
        """Test successful retry execution after initial failure."""
        error_handler = MCPErrorHandler()

        attempt_count = 0

        def operation_factory() -> Any:
            async def operation_with_failure() -> str:
                nonlocal attempt_count
                attempt_count += 1
                if attempt_count == 1:
                    raise Exception("Temporary failure")
                return "success"

            return operation_with_failure()

        result = await error_handler.execute_with_retry(
            "test_operation", operation_factory, max_retries=2, base_delay=0.1
        )

        assert result == "success"
        assert attempt_count == 2

    @pytest.mark.asyncio
    async def test_execute_with_retry_all_failures(self) -> None:
        """Test retry execution with all attempts failing."""
        error_handler = MCPErrorHandler()

        def always_failing_factory() -> Any:
            async def always_failing_operation() -> str:
                raise Exception("Persistent failure")

            return always_failing_operation()

        with pytest.raises(Exception, match="Persistent failure"):
            await error_handler.execute_with_retry(
                "test_operation", always_failing_factory, max_retries=2, base_delay=0.1
            )

    @pytest.mark.asyncio
    async def test_execute_with_retry_custom_settings(self) -> None:
        """Test retry execution with custom settings."""
        error_handler = MCPErrorHandler()

        attempt_count = 0

        def operation_factory() -> Any:
            async def operation_with_failure() -> str:
                nonlocal attempt_count
                attempt_count += 1
                if attempt_count < 3:
                    raise Exception(f"Failure {attempt_count}")
                return "success"

            return operation_with_failure()

        result = await error_handler.execute_with_retry(
            "test_operation",
            operation_factory,
            max_retries=3,
            base_delay=0.1,
            max_delay=0.5,
            exponential_base=1.5,
        )

        assert result == "success"
        assert attempt_count == 3

    def test_get_error_summary(self) -> None:
        """Test error summary generation."""
        error_handler = MCPErrorHandler()

        summary = error_handler.get_error_summary()

        assert "timeouts" in summary
        assert "retry_settings" in summary
        assert "logging" in summary
        assert "error_codes" in summary

        # Check standard error codes
        assert summary["error_codes"]["standard"]["PARSE_ERROR"] == -32700
        assert summary["error_codes"]["standard"]["INVALID_REQUEST"] == -32600

        # Check server-defined codes
        assert summary["error_codes"]["server_defined"]["RESOURCE_NOT_FOUND"] == -32001
        assert summary["error_codes"]["server_defined"]["TIMEOUT_ERROR"] == -32005

    def test_error_logging_to_stderr(self) -> None:
        """Test that errors are logged to stderr."""
        error_handler = MCPErrorHandler()

        # Capture stderr output
        import io

        stderr_capture = io.StringIO()

        # Temporarily redirect stderr
        old_stderr = sys.stderr
        sys.stderr = stderr_capture

        try:
            error = error_handler.create_error(MCPErrorHandler.INVALID_PARAMS, "Test error message")

            # Check that error was logged to stderr
            stderr_output = stderr_capture.getvalue()
            assert "[MCP ERROR]" in stderr_output
            assert "Test error message" in stderr_output
        finally:
            # Restore stderr
            sys.stderr = old_stderr

    def test_error_logging_with_data(self) -> None:
        """Test error logging with additional data."""
        error_handler = MCPErrorHandler()

        data = {"field": "test", "value": 123}
        error = error_handler.create_error(MCPErrorHandler.INVALID_PARAMS, "Test error", data=data)

        # Verify data is included in the error response
        assert error["error"]["data"] == data


class TestMCPErrorHandlerIntegration:
    """Integration tests for MCPErrorHandler with real scenarios."""

    @pytest.mark.asyncio
    async def test_complete_error_handling_flow(self) -> None:
        """Test complete error handling flow from creation to logging."""
        config = ErrorHandlingConfig()
        config.timeouts["tool_execution"] = 0.1
        config.retry_settings["max_retries"] = 1
        config.retry_settings["base_delay"] = 0.1

        error_handler = MCPErrorHandler(config)

        # Test timeout error
        async def timeout_operation() -> str:
            await asyncio.sleep(0.2)
            return "success"

        with pytest.raises(asyncio.TimeoutError):
            await error_handler.execute_with_timeout("timeout_test", timeout_operation())

        # Test retry logic
        attempt_count = 0

        def retry_operation_factory() -> Any:
            async def retry_operation() -> str:
                nonlocal attempt_count
                attempt_count += 1
                if attempt_count == 1:
                    raise Exception("First attempt failure")
                return "success"

            return retry_operation()

        result = await error_handler.execute_with_retry("retry_test", retry_operation_factory)

        assert result == "success"
        assert attempt_count == 2

    def test_error_code_consistency(self) -> None:
        """Test that all error codes are unique and properly defined."""
        error_handler = MCPErrorHandler()

        # Get all error codes
        all_codes = []

        # Standard JSON-RPC codes
        all_codes.extend(
            [
                error_handler.PARSE_ERROR,
                error_handler.INVALID_REQUEST,
                error_handler.METHOD_NOT_FOUND,
                error_handler.INVALID_PARAMS,
                error_handler.INTERNAL_ERROR,
            ]
        )

        # Server-defined codes
        all_codes.extend(
            [
                error_handler.RESOURCE_NOT_FOUND,
                error_handler.RESOURCE_ACCESS_DENIED,
                error_handler.RESOURCE_UNAVAILABLE,
                error_handler.TOOL_UNAVAILABLE,
                error_handler.TIMEOUT_ERROR,
                error_handler.VALIDATION_ERROR,
                error_handler.EXTERNAL_SERVICE_ERROR,
                error_handler.RATE_LIMIT_ERROR,
            ]
        )

        # Check uniqueness
        assert len(all_codes) == len(set(all_codes))

        # Check server-defined codes are in correct range
        for code in all_codes[5:]:  # Server-defined codes
            assert -32008 <= code <= -32001

    def test_configuration_immutability(self) -> None:
        """Test that configuration changes don't affect other instances."""
        config1 = ErrorHandlingConfig()
        config2 = ErrorHandlingConfig()

        # Modify config1
        config1.timeouts["tool_execution"] = 999.0

        # config2 should remain unchanged
        assert config2.timeouts["tool_execution"] == 120.0

        # Create handlers with different configs
        handler1 = MCPErrorHandler(config1)
        handler2 = MCPErrorHandler(config2)

        assert handler1.config.timeouts["tool_execution"] == 999.0
        assert handler2.config.timeouts["tool_execution"] == 120.0
