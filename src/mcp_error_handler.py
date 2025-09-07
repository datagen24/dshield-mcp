#!/usr/bin/env python3
"""MCP Error Handler for DShield MCP Server.

This module provides centralized error handling for all MCP operations,
ensuring proper JSON-RPC error responses with correct error codes,
timeout handling, retry logic, and comprehensive error context capture.

The error handler follows the JSON-RPC 2.0 specification and provides
user-friendly error messages while maintaining detailed logging for
debugging and troubleshooting.

Example:
    >>> error_handler = MCPErrorHandler(config)
    >>> error_response = error_handler.create_validation_error("tool_name", validation_error)
    >>> timeout_response = error_handler.create_timeout_error("tool_name", 30)

"""

import asyncio
import json
import sys
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any

import structlog
from pydantic import ValidationError

from .security.mcp_schema_validator import MCPSchemaValidator
from .security.rate_limiter import (
    APIKeyRateLimiter,
    ConnectionRateLimiter,
    GlobalRateLimiter,
)

logger = structlog.get_logger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior.

    Attributes:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Time to wait before attempting recovery
        expected_exception: Exception types that count as failures
        success_threshold: Number of successes needed to close circuit

    """

    failure_threshold: int = 5
    recovery_timeout: float = 60.0  # seconds
    expected_exception: tuple[type[Exception], ...] = (Exception,)
    success_threshold: int = 2


@dataclass
class ErrorHandlingConfig:
    """Configuration for error handling behavior.

    Attributes:
        timeouts: Timeout settings for different operations
        retry_settings: Retry configuration for transient failures
        logging: Logging configuration for error handling
        circuit_breaker: Circuit breaker configuration
        error_aggregation: Error aggregation settings

    """

    timeouts: dict[str, float] = field(
        default_factory=lambda: {
            "elasticsearch_operations": 30.0,
            "dshield_api_calls": 10.0,
            "latex_compilation": 60.0,
            "tool_execution": 120.0,
        }
    )

    retry_settings: dict[str, Any] = field(
        default_factory=lambda: {
            "max_retries": 3,
            "base_delay": 1.0,
            "max_delay": 30.0,
            "exponential_base": 2.0,
        }
    )

    logging: dict[str, Any] = field(
        default_factory=lambda: {
            "include_stack_traces": True,
            "include_request_context": True,
            "include_user_parameters": True,
            "log_level": "INFO",
        }
    )

    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)

    error_aggregation: dict[str, Any] = field(
        default_factory=lambda: {
            "enabled": True,
            "window_size": 300,  # 5 minutes
            "max_errors_per_window": 100,
            "history_size": 1000,
        }
    )


class MCPErrorHandler:
    """Handles JSON-RPC error responses for MCP server.

    This class provides comprehensive error handling for all MCP operations,
    including proper error code generation, timeout handling, retry logic,
    and detailed error logging for debugging and troubleshooting.

    The error handler follows the JSON-RPC 2.0 specification and ensures
    that all error responses are properly formatted and contain actionable
    information for users while maintaining detailed logging for developers.

    Attributes:
        config: Error handling configuration
        logger: Structured logger instance

    """

    # Standard JSON-RPC 2.0 error codes
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # Server-defined error codes (starting at -32000)
    RESOURCE_NOT_FOUND = -32001
    RESOURCE_ACCESS_DENIED = -32002
    RESOURCE_UNAVAILABLE = -32003
    TOOL_UNAVAILABLE = -32004
    TIMEOUT_ERROR = -32005
    VALIDATION_ERROR = -32006
    EXTERNAL_SERVICE_ERROR = -32007
    RATE_LIMIT_ERROR = -32008
    SECURITY_ERROR = -32009
    SCHEMA_VALIDATION_ERROR = -32010

    def __init__(self, config: ErrorHandlingConfig | None = None) -> None:
        """Initialize the MCP error handler.

        Args:
            config: Error handling configuration. If None, uses default values.

        """
        self.config = config or ErrorHandlingConfig()
        self.logger = structlog.get_logger(__name__)

        # Initialize error aggregator for Phase 3 features
        self.error_aggregator = ErrorAggregator(self.config.error_aggregation)

        # Initialize security components
        self.schema_validator = MCPSchemaValidator()
        self.api_key_rate_limiter = APIKeyRateLimiter()
        self.connection_rate_limiter = ConnectionRateLimiter()
        self.global_rate_limiter = GlobalRateLimiter()

        # Validate configuration
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate the error handling configuration.

        Raises:
            ValueError: If configuration values are invalid.

        """
        if self.config.retry_settings["max_retries"] < 0:
            raise ValueError("max_retries must be non-negative")

        if self.config.retry_settings["base_delay"] <= 0:
            raise ValueError("base_delay must be positive")

        if self.config.retry_settings["max_delay"] <= 0:
            raise ValueError("max_delay must be positive")

        if self.config.retry_settings["exponential_base"] <= 1:
            raise ValueError("exponential_base must be greater than 1")

        for operation, timeout in self.config.timeouts.items():
            if timeout <= 0:
                raise ValueError(f"timeout for {operation} must be positive")

    def create_error(
        self,
        code: int,
        message: str,
        data: dict[str, Any] | None = None,
        request_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a properly formatted JSON-RPC error response.

        Args:
            code: JSON-RPC error code
            message: Human-readable error message
            data: Additional error data (optional)
            request_id: Request ID for correlation (optional)

        Returns:
            Dictionary containing the JSON-RPC error response.

        Example:
            >>> error = error_handler.create_error(
            ...     MCPErrorHandler.INVALID_PARAMS,
            ...     "Invalid parameters provided",
            ...     {"field": "time_range", "issue": "must be positive"}
            ... )

        """
        error_response: dict[str, Any] = {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message,
            },
        }

        if data:
            error_response["error"]["data"] = data

        if request_id:
            error_response["id"] = request_id

        # Log error to stderr for debugging
        self._log_error(code, message, data, request_id)

        # Record error with aggregator for Phase 3 analytics
        if self.config.error_aggregation["enabled"]:
            error_type = self._get_error_type(code)
            context: dict[str, Any] = {
                "message": message,
                "request_id": request_id,
                "timestamp": datetime.now(UTC).isoformat(),
            }
            if data:
                context["error_data"] = data
            self.error_aggregator.record_error(code, error_type, context)

        return error_response

    def _get_error_type(self, code: int) -> str:
        """Get a human-readable error type from error code.

        Args:
            code: JSON-RPC error code

        Returns:
            String representation of error type.

        """
        error_type_map = {
            self.PARSE_ERROR: "parse_error",
            self.INVALID_REQUEST: "invalid_request",
            self.METHOD_NOT_FOUND: "method_not_found",
            self.INVALID_PARAMS: "invalid_params",
            self.INTERNAL_ERROR: "internal_error",
            self.RESOURCE_NOT_FOUND: "resource_not_found",
            self.RESOURCE_ACCESS_DENIED: "resource_access_denied",
            self.RESOURCE_UNAVAILABLE: "resource_unavailable",
            self.TOOL_UNAVAILABLE: "tool_unavailable",
            self.TIMEOUT_ERROR: "timeout_error",
            self.VALIDATION_ERROR: "validation_error",
            self.EXTERNAL_SERVICE_ERROR: "external_service_error",
            self.RATE_LIMIT_ERROR: "rate_limit_error",
        }

        return error_type_map.get(code, "unknown_error")

    def create_parse_error(
        self, message: str = "Parse error", data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create a parse error response.

        Args:
            message: Error message
            data: Additional error data

        Returns:
            Parse error response.

        """
        return self.create_error(self.PARSE_ERROR, message, data)

    def create_invalid_request_error(
        self, message: str = "Invalid request", data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create an invalid request error response.

        Args:
            message: Error message
            data: Additional error data

        Returns:
            Invalid request error response.

        """
        return self.create_error(self.INVALID_REQUEST, message, data)

    def create_method_not_found_error(
        self, method: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create a method not found error response.

        Args:
            method: Method name that was not found
            data: Additional error data

        Returns:
            Method not found error response.

        """
        message = f"Method '{method}' not found"
        if not data:
            data = {"method": method}
        return self.create_error(self.METHOD_NOT_FOUND, message, data)

    def create_invalid_params_error(
        self, message: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create an invalid parameters error response.

        Args:
            message: Error message
            data: Additional error data

        Returns:
            Invalid parameters error response.

        """
        return self.create_error(self.INVALID_PARAMS, message, data)

    def create_internal_error(
        self, message: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create an internal error response.

        Args:
            message: Error message
            data: Additional error data

        Returns:
            Internal error response.

        """
        return self.create_error(self.INTERNAL_ERROR, message, data)

    def create_validation_error(
        self, tool_name: str, validation_error: ValidationError, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create a validation error response.

        Args:
            tool_name: Name of the tool that failed validation
            validation_error: Pydantic validation error
            data: Additional error data

        Returns:
            Validation error response.

        """
        message = f"Invalid parameters for tool '{tool_name}'"

        if not data:
            data = {
                "tool": tool_name,
                "validation_errors": validation_error.errors(),
                "suggestion": "Please check the tool schema and provide valid parameters",
            }

        return self.create_error(self.VALIDATION_ERROR, message, data)

    def create_timeout_error(
        self, tool_name: str, timeout_seconds: float, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create a timeout error response.

        Args:
            tool_name: Name of the tool that timed out
            timeout_seconds: Timeout value in seconds
            data: Additional error data

        Returns:
            Timeout error response.

        """
        message = f"Tool '{tool_name}' execution timed out after {timeout_seconds} seconds"

        if not data:
            data = {
                "tool": tool_name,
                "timeout_seconds": timeout_seconds,
                "suggestion": "Try reducing the scope of your request or contact support if "
                "the issue persists",
            }

        return self.create_error(self.TIMEOUT_ERROR, message, data)

    def create_resource_error(
        self, resource_uri: str, error_type: str, message: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create a resource-related error response.

        Args:
            resource_uri: URI of the resource that caused the error
            error_type: Type of resource error
            message: Error message
            data: Additional error data

        Returns:
            Resource error response.

        """
        if error_type == "not_found":
            code = self.RESOURCE_NOT_FOUND
        elif error_type == "access_denied":
            code = self.RESOURCE_ACCESS_DENIED
        elif error_type == "unavailable":
            code = self.RESOURCE_UNAVAILABLE
        else:
            code = self.INTERNAL_ERROR

        if not data:
            data = {
                "resource_uri": resource_uri,
                "error_type": error_type,
                "suggestion": "Check the resource URI and your permissions",
            }

        return self.create_error(code, message, data)

    def create_external_service_error(
        self, service_name: str, error_message: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create an external service error response.

        Args:
            service_name: Name of the external service
            error_message: Error message from the service
            data: Additional error data

        Returns:
            External service error response.

        """
        message = f"External service '{service_name}' error: {error_message}"

        if not data:
            data = {
                "service": service_name,
                "suggestion": "The service may be temporarily unavailable. Please try again later.",
            }

        return self.create_error(self.EXTERNAL_SERVICE_ERROR, message, data)

    def create_rate_limit_error(
        self,
        service_name: str,
        retry_after: float | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a rate limit error response.

        Args:
            service_name: Name of the service that rate limited the request
            retry_after: Suggested retry delay in seconds
            data: Additional error data

        Returns:
            Rate limit error response.

        """
        message = f"Rate limit exceeded for service '{service_name}'"

        if not data:
            data = {
                "service": service_name,
                "suggestion": "Please wait before making additional requests",
            }

            if retry_after:
                data["retry_after_seconds"] = retry_after
                data["suggestion"] = f"Please wait {retry_after} seconds before retrying"

        return self.create_error(self.RATE_LIMIT_ERROR, message, data)

    def create_security_error(
        self, message: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create a security error response.

        Args:
            message: Security error message
            data: Additional error data

        Returns:
            Security error response.

        """
        if not data:
            data = {
                "error_type": "security_violation",
                "timestamp": datetime.now(UTC).isoformat(),
            }

        return self.create_error(self.SECURITY_ERROR, message, data)

    def create_schema_validation_error(
        self, message: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create a schema validation error response.

        Args:
            message: Schema validation error message
            data: Additional error data

        Returns:
            Schema validation error response.

        """
        if not data:
            data = {
                "error_type": "schema_validation_failed",
                "timestamp": datetime.now(UTC).isoformat(),
            }

        return self.create_error(self.SCHEMA_VALIDATION_ERROR, message, data)

    async def validate_message_security(
        self, message: str, connection_id: str | None = None, api_key_id: str | None = None
    ) -> dict[str, Any] | None:
        """Validate message security including schema validation and rate limiting.

        Args:
            message: Raw JSON message string
            connection_id: Connection ID for rate limiting
            api_key_id: API key ID for rate limiting

        Returns:
            Error response if validation fails, None if valid

        """
        # Global rate limiting
        if not await self.global_rate_limiter.is_allowed():
            wait_time = await self.global_rate_limiter.get_wait_time()
            return self.create_rate_limit_error("global", retry_after=wait_time)

        # Connection rate limiting
        if connection_id and not await self.connection_rate_limiter.is_allowed(connection_id):
            wait_time = await self.connection_rate_limiter.get_wait_time(connection_id)
            return self.create_rate_limit_error("connection", retry_after=wait_time)

        # API key rate limiting
        if api_key_id and not await self.api_key_rate_limiter.is_allowed(api_key_id):
            wait_time = await self.api_key_rate_limiter.get_wait_time(api_key_id)
            return self.create_rate_limit_error("api_key", retry_after=wait_time)

        # Schema validation
        parsed_message = self.schema_validator.validate_complete_message(message)
        if parsed_message is None:
            return self.create_schema_validation_error("Invalid message format or content")

        return None

    def validate_tool_exists(self, tool_name: str, available_tools: list[str]) -> None:
        """Validate that a tool exists before execution.

        Args:
            tool_name: Name of the tool to validate
            available_tools: List of available tool names

        Raises:
            ValueError: If the tool does not exist.

        """
        if tool_name not in available_tools:
            raise ValueError(
                f"Tool '{tool_name}' not found. Available tools: {', '.join(available_tools)}"
            )

    def validate_arguments(
        self, tool_name: str, arguments: dict[str, Any], schema: dict[str, Any]
    ) -> None:
        """Validate arguments against a tool schema.

        Args:
            tool_name: Name of the tool
            arguments: Arguments to validate
            schema: Tool schema for validation

        Raises:
            ValidationError: If arguments are invalid.

        """
        # This is a placeholder for schema validation
        # In a full implementation, you would use a JSON schema validator
        # For now, we'll do basic validation
        if not isinstance(arguments, dict):
            raise ValidationError(f"Arguments must be a dictionary, got {type(arguments)}")

        # Log validation attempt
        self.logger.debug("Validating arguments", tool=tool_name, arguments=arguments)

    async def execute_with_timeout(
        self,
        operation: str,
        coro: Any,
        timeout_seconds: float | None = None,
    ) -> Any:
        """Execute a coroutine with timeout protection.

        Args:
            operation: Name of the operation for logging
            coro: Coroutine to execute
            timeout_seconds: Timeout in seconds (uses default if None)

        Returns:
            Result of the coroutine execution.

        Raises:
            asyncio.TimeoutError: If the operation times out.

        """
        if timeout_seconds is None:
            timeout_seconds = self.config.timeouts.get("tool_execution", 120.0)

        self.logger.debug(
            "Executing operation with timeout", operation=operation, timeout_seconds=timeout_seconds
        )

        try:
            result = await asyncio.wait_for(coro, timeout=timeout_seconds)
            return result
        except TimeoutError:
            self.logger.warning(
                "Operation timed out", operation=operation, timeout_seconds=timeout_seconds
            )
            raise

    async def execute_with_retry(
        self,
        operation: str,
        coro_factory: Any,
        max_retries: int | None = None,
        base_delay: float | None = None,
        max_delay: float | None = None,
        exponential_base: float | None = None,
    ) -> Any:
        """Execute a coroutine with retry logic and exponential backoff.

        Args:
            operation: Name of the operation for logging
            coro_factory: Coroutine factory function or callable that returns a coroutine
            max_retries: Maximum number of retries (uses config default if None)
            base_delay: Base delay between retries (uses config default if None)
            max_delay: Maximum delay between retries (uses config default if None)
            exponential_base: Exponential backoff multiplier (uses config default if None)

        Returns:
            Result of the coroutine execution.

        Raises:
            Exception: If all retries are exhausted.

        """
        if max_retries is None:
            max_retries = self.config.retry_settings["max_retries"]
        if base_delay is None:
            base_delay = self.config.retry_settings["base_delay"]
        if max_delay is None:
            max_delay = self.config.retry_settings["max_delay"]
        if exponential_base is None:
            exponential_base = self.config.retry_settings["exponential_base"]

        last_exception: Exception | None = None

        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    self.logger.info(
                        "Retrying operation",
                        operation=operation,
                        attempt=attempt,
                        max_retries=max_retries,
                    )

                # Create a new coroutine for each attempt
                if callable(coro_factory):
                    coro = coro_factory()
                else:
                    coro = coro_factory

                result = await coro
                if attempt > 0:
                    self.logger.info(
                        "Operation succeeded on retry", operation=operation, attempt=attempt
                    )
                return result

            except Exception as e:
                last_exception = e

                if attempt == max_retries:
                    self.logger.error(
                        "Operation failed after all retries",
                        operation=operation,
                        max_retries=max_retries,
                        final_error=str(e),
                    )
                    raise

                # Calculate delay with exponential backoff
                delay = min(base_delay * (exponential_base**attempt), max_delay)

                self.logger.warning(
                    "Operation failed, retrying",
                    operation=operation,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    delay_seconds=delay,
                    error=str(e),
                )

                await asyncio.sleep(delay)

        # This should never be reached, but just in case
        if last_exception is not None:
            raise last_exception
        else:
            raise RuntimeError("Retry operation failed without exception")

    def _log_error(
        self, code: int, message: str, data: dict[str, Any] | None, request_id: str | None
    ) -> None:
        """Log error information to stderr for debugging.

        Args:
            code: Error code
            message: Error message
            data: Additional error data
            request_id: Request ID for correlation

        """
        log_data = {
            "error_code": code,
            "error_message": message,
            "timestamp": datetime.now(UTC).isoformat(),
            "request_id": request_id,
        }

        if data:
            log_data["error_data"] = data

        # Log to stderr for debugging
        error_json = json.dumps(log_data, indent=2)
        print(f"[MCP ERROR] {error_json}", file=sys.stderr)

        # Also log to structured logger
        self.logger.error("MCP error occurred", **log_data)

    def get_error_summary(self) -> dict[str, Any]:
        """Get a summary of error handling configuration.

        Returns:
            Dictionary containing error handling configuration summary.

        """
        return {
            "timeouts": self.config.timeouts,
            "retry_settings": self.config.retry_settings,
            "logging": self.config.logging,
            "error_codes": {
                "standard": {
                    "PARSE_ERROR": self.PARSE_ERROR,
                    "INVALID_REQUEST": self.INVALID_REQUEST,
                    "METHOD_NOT_FOUND": self.METHOD_NOT_FOUND,
                    "INVALID_PARAMS": self.INVALID_PARAMS,
                    "INTERNAL_ERROR": self.INTERNAL_ERROR,
                },
                "server_defined": {
                    "RESOURCE_NOT_FOUND": self.RESOURCE_NOT_FOUND,
                    "RESOURCE_ACCESS_DENIED": self.RESOURCE_ACCESS_DENIED,
                    "RESOURCE_UNAVAILABLE": self.RESOURCE_UNAVAILABLE,
                    "TOOL_UNAVAILABLE": self.TOOL_UNAVAILABLE,
                    "TIMEOUT_ERROR": self.TIMEOUT_ERROR,
                    "VALIDATION_ERROR": self.VALIDATION_ERROR,
                    "EXTERNAL_SERVICE_ERROR": self.EXTERNAL_SERVICE_ERROR,
                    "RATE_LIMIT_ERROR": self.RATE_LIMIT_ERROR,
                },
            },
        }

    # Phase 3: Advanced Error Handling Features

    def create_resource_not_found_error(
        self, resource_uri: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create a resource not found error response.

        Args:
            resource_uri: URI of the resource that was not found
            data: Additional error data

        Returns:
            Resource not found error response.

        """
        if not data:
            data = {
                "resource_uri": resource_uri,
                "suggestion": "Check the resource URI and ensure it exists",
            }

        return self.create_error(
            self.RESOURCE_NOT_FOUND, f"Resource '{resource_uri}' not found", data
        )

    def create_resource_access_denied_error(
        self,
        resource_uri: str,
        reason: str = "Permission denied",
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a resource access denied error response.

        Args:
            resource_uri: URI of the resource that access was denied to
            reason: Reason for access denial
            data: Additional error data

        Returns:
            Resource access denied error response.

        """
        if not data:
            data = {
                "resource_uri": resource_uri,
                "reason": reason,
                "suggestion": "Check your permissions and authentication",
            }

        return self.create_error(
            self.RESOURCE_ACCESS_DENIED,
            f"Access denied to resource '{resource_uri}': {reason}",
            data,
        )

    def create_resource_unavailable_error(
        self,
        resource_uri: str,
        reason: str = "Resource temporarily unavailable",
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a resource unavailable error response.

        Args:
            resource_uri: URI of the resource that is unavailable
            reason: Reason for unavailability
            data: Additional error data

        Returns:
            Resource unavailable error response.

        """
        if not data:
            data = {
                "resource_uri": resource_uri,
                "reason": reason,
                "suggestion": "Try again later or contact support if the issue persists",
            }

        return self.create_error(
            self.RESOURCE_UNAVAILABLE, f"Resource '{resource_uri}' unavailable: {reason}", data
        )

    def create_circuit_breaker_open_error(
        self, service_name: str, data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Create a circuit breaker open error response.

        Args:
            service_name: Name of the service with open circuit breaker
            data: Additional error data

        Returns:
            Circuit breaker open error response.

        """
        if not data:
            data = {
                "service": service_name,
                "suggestion": "Service is temporarily unavailable due to repeated failures. "
                "Please try again later.",
            }

        return self.create_error(
            self.EXTERNAL_SERVICE_ERROR, f"Service '{service_name}' circuit breaker is open", data
        )

    def create_validation_error_with_context(
        self,
        tool_name: str,
        validation_error: ValidationError,
        context: dict[str, Any],
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a validation error response with additional context.

        Args:
            tool_name: Name of the tool that failed validation
            validation_error: Pydantic validation error
            context: Additional context about the validation failure
            data: Additional error data

        Returns:
            Enhanced validation error response.

        """
        if not data:
            data = {
                "tool_name": tool_name,
                "validation_errors": [str(e) for e in validation_error.errors()],
                "context": context,
                "suggestion": "Check the input parameters and ensure they match the "
                "expected schema",
            }

        return self.create_error(
            self.VALIDATION_ERROR, f"Validation failed for tool '{tool_name}'", data
        )

    def create_timeout_error_with_context(
        self,
        tool_name: str,
        timeout_seconds: float,
        operation_context: dict[str, Any],
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a timeout error response with operation context.

        Args:
            tool_name: Name of the tool that timed out
            timeout_seconds: Timeout value that was exceeded
            operation_context: Context about the operation that timed out
            data: Additional error data

        Returns:
            Enhanced timeout error response.

        """
        if not data:
            data = {
                "tool_name": tool_name,
                "timeout_seconds": timeout_seconds,
                "operation_context": operation_context,
                "suggestion": "The operation may be taking longer than expected. Try reducing "
                "the scope or increasing the timeout.",
            }

        return self.create_error(
            self.TIMEOUT_ERROR,
            f"Tool '{tool_name}' timed out after {timeout_seconds} seconds",
            data,
        )

    def get_enhanced_error_summary(self) -> dict[str, Any]:
        """Get an enhanced summary including Phase 3 features.

        Returns:
            Dictionary containing comprehensive error handling configuration and capabilities.

        """
        base_summary = self.get_error_summary()
        base_summary.update(
            {
                "phase_3_features": {
                    "circuit_breaker": {
                        "enabled": True,
                        "config": {
                            "failure_threshold": self.config.circuit_breaker.failure_threshold,
                            "recovery_timeout": self.config.circuit_breaker.recovery_timeout,
                            "success_threshold": self.config.circuit_breaker.success_threshold,
                        },
                    },
                    "error_aggregation": {
                        "enabled": self.config.error_aggregation["enabled"],
                        "window_size": self.config.error_aggregation["window_size"],
                        "max_errors_per_window": self.config.error_aggregation[
                            "max_errors_per_window"
                        ],
                    },
                    "enhanced_resource_handling": True,
                    "context_aware_errors": True,
                },
            }
        )
        return base_summary

    def get_error_analytics(self, window_seconds: int | None = None) -> dict[str, Any]:
        """Get error analytics and patterns from the aggregator.

        Args:
            window_seconds: Time window in seconds (uses config default if None)

        Returns:
            Dictionary containing error analytics and patterns.

        """
        if not self.config.error_aggregation["enabled"]:
            return {"error_aggregation": "disabled"}

        return {
            "error_summary": self.error_aggregator.get_error_summary(window_seconds),
            "error_trends": self.error_aggregator.get_error_trends(),
            "aggregation_config": self.config.error_aggregation,
        }

    def get_circuit_breaker_status(self, service_name: str) -> dict[str, Any] | None:
        """Get circuit breaker status for a specific service.

        Args:
            service_name: Name of the service to check

        Returns:
            Circuit breaker status or None if not found.

        """
        # This would be implemented when circuit breakers are added to specific services
        # For now, return None to indicate no circuit breaker exists
        return None


class CircuitBreaker:
    """Circuit breaker implementation for external service calls.

    This class implements the circuit breaker pattern to prevent cascading failures
    when external services are experiencing issues. It tracks failures and
    automatically opens the circuit when the failure threshold is reached.

    Attributes:
        config: Circuit breaker configuration
        state: Current circuit breaker state
        failure_count: Number of consecutive failures
        success_count: Number of consecutive successes
        last_failure_time: Timestamp of last failure
        logger: Structured logger instance

    """

    def __init__(self, service_name: str, config: CircuitBreakerConfig | None = None) -> None:
        """Initialize the circuit breaker.

        Args:
            service_name: Name of the service being protected
            config: Circuit breaker configuration

        """
        self.service_name = service_name
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: datetime | None = None
        self.logger = structlog.get_logger(__name__)

    def can_execute(self) -> bool:
        """Check if the circuit breaker allows execution.

        Returns:
            True if execution is allowed, False otherwise.

        """
        if self.state == CircuitBreakerState.CLOSED:
            return True

        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self._set_half_open()
                return True
            return False

        # HALF_OPEN state - allow limited execution
        return True

    def on_success(self) -> None:
        """Record a successful operation."""
        if self.state == CircuitBreakerState.HALF_OPEN:
            self.success_count += 1
            if self.success_count >= self.config.success_threshold:
                self._set_closed()
                self.logger.info("Circuit breaker closed", service=self.service_name)
        else:
            # Reset failure count on success
            self.failure_count = 0

    def on_failure(self, exception: Exception) -> None:
        """Record a failed operation.

        Args:
            exception: The exception that occurred

        """
        if isinstance(exception, self.config.expected_exception):
            self.failure_count += 1
            self.last_failure_time = datetime.now(UTC)

            if self.failure_count >= self.config.failure_threshold:
                self._set_open()
                self.logger.warning(
                    "Circuit breaker opened",
                    service=self.service_name,
                    failure_count=self.failure_count,
                )

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset.

        Returns:
            True if reset should be attempted.

        """
        if self.last_failure_time is None:
            return False

        time_since_failure = (datetime.now(UTC) - self.last_failure_time).total_seconds()
        return time_since_failure >= self.config.recovery_timeout

    def _set_half_open(self) -> None:
        """Set circuit breaker to half-open state."""
        self.state = CircuitBreakerState.HALF_OPEN
        self.success_count = 0
        self.logger.info("Circuit breaker set to half-open", service=self.service_name)

    def _set_open(self) -> None:
        """Set circuit breaker to open state."""
        self.state = CircuitBreakerState.OPEN
        self.logger.warning("Circuit breaker opened", service=self.service_name)

    def _set_closed(self) -> None:
        """Set circuit breaker to closed state."""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.success_count = 0

    def get_status(self) -> dict[str, Any]:
        """Get the current status of the circuit breaker.

        Returns:
            Dictionary containing circuit breaker status.

        """
        return {
            "service_name": self.service_name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "last_failure_time": self.last_failure_time.isoformat()
            if self.last_failure_time
            else None,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout": self.config.recovery_timeout,
                "success_threshold": self.config.success_threshold,
            },
        }

    async def execute(self, coro_factory: Any, error_handler: "MCPErrorHandler") -> Any:
        """Execute a coroutine with circuit breaker protection.

        Args:
            coro_factory: Coroutine factory function or callable
            error_handler: MCPErrorHandler instance for error responses

        Returns:
            Result of the coroutine execution.

        Raises:
            Exception: If the circuit breaker is open or execution fails.

        """
        if not self.can_execute():
            raise Exception(f"Circuit breaker is open for service '{self.service_name}'")

        try:
            if callable(coro_factory):
                coro = coro_factory()
            else:
                coro = coro_factory

            result = await coro
            self.on_success()
            return result

        except Exception as e:
            self.on_failure(e)
            raise


class ErrorAggregator:
    """Error aggregation and analytics for monitoring and debugging.

    This class tracks error patterns, frequencies, and trends to help
    identify systemic issues and provide insights for debugging.

    Attributes:
        config: Error aggregation configuration
        error_counts: Count of errors by type and time window
        error_history: Recent error history for analysis
        logger: Structured logger instance

    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the error aggregator.

        Args:
            config: Error aggregation configuration

        """
        self.config = config or {
            "enabled": True,
            "window_size": 300,  # 5 minutes
            "max_errors_per_window": 100,
            "history_size": 1000,
        }

        self.error_counts: defaultdict[str, int] = defaultdict(int)
        self.error_history: deque[dict[str, Any]] = deque(maxlen=self.config["history_size"])
        self.logger = structlog.get_logger(__name__)

    def record_error(self, error_code: int, error_type: str, context: dict[str, Any]) -> None:
        """Record an error occurrence.

        Args:
            error_code: JSON-RPC error code
            error_type: Type of error (e.g., 'timeout', 'validation', 'external_service')
            context: Additional context about the error

        """
        if not self.config["enabled"]:
            return

        timestamp = datetime.now(UTC)

        # Record error count
        key = f"{error_code}_{error_type}"
        self.error_counts[key] += 1

        # Record error history
        error_record = {
            "timestamp": timestamp,
            "error_code": error_code,
            "error_type": error_type,
            "context": context,
        }
        self.error_history.append(error_record)

        # Check if we're exceeding error thresholds
        self._check_error_thresholds(error_type)

    def _check_error_thresholds(self, error_type: str) -> None:
        """Check if error thresholds are exceeded and log warnings.

        Args:
            error_type: Type of error to check

        """
        recent_errors = self._get_recent_errors(self.config["window_size"])
        error_count = len([e for e in recent_errors if e["error_type"] == error_type])

        if error_count > self.config["max_errors_per_window"]:
            self.logger.warning(
                "Error threshold exceeded",
                error_type=error_type,
                count=error_count,
                threshold=self.config["max_errors_per_window"],
            )

    def _get_recent_errors(self, window_seconds: int) -> list[dict[str, Any]]:
        """Get errors from the recent time window.

        Args:
            window_seconds: Time window in seconds

        Returns:
            List of recent errors

        """
        cutoff_time = datetime.now(UTC) - timedelta(seconds=window_seconds)
        return [e for e in self.error_history if e["timestamp"] >= cutoff_time]

    def get_error_summary(self, window_seconds: int | None = None) -> dict[str, Any]:
        """Get a summary of error patterns.

        Args:
            window_seconds: Time window in seconds (uses config default if None)

        Returns:
            Dictionary containing error summary and patterns.

        """
        if window_seconds is None:
            window_seconds = self.config["window_size"]

        recent_errors = self._get_recent_errors(window_seconds)

        # Group errors by type and code
        error_summary: defaultdict[str, dict[str, Any]] = defaultdict(
            lambda: {"count": 0, "examples": []}
        )

        for error in recent_errors:
            key = f"{error['error_code']}_{error['error_type']}"
            error_summary[key]["count"] += 1
            if len(error_summary[key]["examples"]) < 5:  # Keep only first 5 examples
                error_summary[key]["examples"].append(
                    {
                        "timestamp": error["timestamp"].isoformat(),
                        "context": error["context"],
                    }
                )

        return {
            "window_seconds": window_seconds,
            "total_errors": len(recent_errors),
            "error_patterns": dict(error_summary),
            "most_common_errors": sorted(
                error_summary.items(),
                key=lambda x: x[1]["count"],
                reverse=True,
            )[:10],  # Top 10 most common errors
        }

    def get_error_trends(self, hours: int = 24) -> dict[str, Any]:
        """Get error trends over a longer time period.

        Args:
            hours: Number of hours to analyze

        Returns:
            Dictionary containing error trends and patterns.

        """
        window_seconds = hours * 3600
        recent_errors = self._get_recent_errors(window_seconds)

        # Group errors by hour
        hourly_errors: defaultdict[str, int] = defaultdict(int)
        for error in recent_errors:
            hour_key = error["timestamp"].replace(minute=0, second=0, microsecond=0)
            hourly_errors[hour_key] += 1

        # Calculate trend
        if len(hourly_errors) >= 2:
            hours_list = sorted(hourly_errors.keys())
            first_hour_count = hourly_errors[hours_list[0]]
            last_hour_count = hourly_errors[hours_list[-1]]

            if first_hour_count > 0:
                trend_percentage = ((last_hour_count - first_hour_count) / first_hour_count) * 100
            else:
                trend_percentage = 0
        else:
            trend_percentage = 0

        return {
            "analysis_period_hours": hours,
            "total_errors": len(recent_errors),
            "hourly_breakdown": {str(h): c for h, c in hourly_errors.items()},
            "trend_percentage": trend_percentage,
            "trend_description": self._describe_trend(trend_percentage),
        }

    def _describe_trend(self, trend_percentage: float) -> str:
        """Describe the error trend in human-readable terms.

        Args:
            trend_percentage: Percentage change in error rate

        Returns:
            Human-readable trend description.

        """
        if trend_percentage > 20:
            return "Significantly increasing"
        if trend_percentage > 5:
            return "Moderately increasing"
        if trend_percentage > -5:
            return "Stable"
        if trend_percentage > -20:
            return "Moderately decreasing"
        return "Significantly decreasing"

    def reset(self) -> None:
        """Reset all error tracking data."""
        self.error_counts.clear()
        self.error_history.clear()
        self.logger.info("Error aggregator reset")
