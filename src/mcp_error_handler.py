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
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

import structlog
from pydantic import ValidationError

logger = structlog.get_logger(__name__)


@dataclass
class ErrorHandlingConfig:
    """Configuration for error handling behavior.
    
    Attributes:
        timeouts: Timeout settings for different operations
        retry_settings: Retry configuration for transient failures
        logging: Logging configuration for error handling
    """
    
    timeouts: Dict[str, float] = field(default_factory=lambda: {
        "elasticsearch_operations": 30.0,
        "dshield_api_calls": 10.0,
        "latex_compilation": 60.0,
        "tool_execution": 120.0
    })
    
    retry_settings: Dict[str, Any] = field(default_factory=lambda: {
        "max_retries": 3,
        "base_delay": 1.0,
        "max_delay": 30.0,
        "exponential_base": 2.0
    })
    
    logging: Dict[str, Any] = field(default_factory=lambda: {
        "include_stack_traces": True,
        "include_request_context": True,
        "include_user_parameters": True,
        "log_level": "INFO"
    })


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
    
    def __init__(self, config: Optional[ErrorHandlingConfig] = None) -> None:
        """Initialize the MCP error handler.
        
        Args:
            config: Error handling configuration. If None, uses default values.
        """
        self.config = config or ErrorHandlingConfig()
        self.logger = structlog.get_logger(__name__)
        
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
        data: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
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
        error_response = {
            "jsonrpc": "2.0",
            "error": {
                "code": code,
                "message": message
            }
        }
        
        if data:
            error_response["error"]["data"] = data
        
        if request_id:
            error_response["id"] = request_id
        
        # Log error to stderr for debugging
        self._log_error(code, message, data, request_id)
        
        return error_response
    
    def create_parse_error(self, message: str = "Parse error", data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a parse error response.
        
        Args:
            message: Error message
            data: Additional error data
        
        Returns:
            Parse error response.
        """
        return self.create_error(self.PARSE_ERROR, message, data)
    
    def create_invalid_request_error(self, message: str = "Invalid request", data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create an invalid request error response.
        
        Args:
            message: Error message
            data: Additional error data
        
        Returns:
            Invalid request error response.
        """
        return self.create_error(self.INVALID_REQUEST, message, data)
    
    def create_method_not_found_error(self, method: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
    
    def create_invalid_params_error(self, message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create an invalid parameters error response.
        
        Args:
            message: Error message
            data: Additional error data
        
        Returns:
            Invalid parameters error response.
        """
        return self.create_error(self.INVALID_PARAMS, message, data)
    
    def create_internal_error(self, message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create an internal error response.
        
        Args:
            message: Error message
            data: Additional error data
        
        Returns:
            Internal error response.
        """
        return self.create_error(self.INTERNAL_ERROR, message, data)
    
    def create_validation_error(self, tool_name: str, validation_error: ValidationError, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
                "suggestion": "Please check the tool schema and provide valid parameters"
            }
        
        return self.create_error(self.VALIDATION_ERROR, message, data)
    
    def create_timeout_error(self, tool_name: str, timeout_seconds: float, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
                "suggestion": "Try reducing the scope of your request or contact support if the issue persists"
            }
        
        return self.create_error(self.TIMEOUT_ERROR, message, data)
    
    def create_resource_error(self, resource_uri: str, error_type: str, message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
                "suggestion": "Check the resource URI and your permissions"
            }
        
        return self.create_error(code, message, data)
    
    def create_external_service_error(self, service_name: str, error_message: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
                "suggestion": "The service may be temporarily unavailable. Please try again later."
            }
        
        return self.create_error(self.EXTERNAL_SERVICE_ERROR, message, data)
    
    def create_rate_limit_error(self, service_name: str, retry_after: Optional[float] = None, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
                "suggestion": "Please wait before making additional requests"
            }
            
            if retry_after:
                data["retry_after_seconds"] = retry_after
                data["suggestion"] = f"Please wait {retry_after} seconds before retrying"
        
        return self.create_error(self.RATE_LIMIT_ERROR, message, data)
    
    def validate_tool_exists(self, tool_name: str, available_tools: List[str]) -> None:
        """Validate that a tool exists before execution.
        
        Args:
            tool_name: Name of the tool to validate
            available_tools: List of available tool names
        
        Raises:
            ValueError: If the tool does not exist.
        """
        if tool_name not in available_tools:
            raise ValueError(f"Tool '{tool_name}' not found. Available tools: {', '.join(available_tools)}")
    
    def validate_arguments(self, tool_name: str, arguments: Dict[str, Any], schema: Dict[str, Any]) -> None:
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
        timeout_seconds: Optional[float] = None
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
        
        self.logger.debug("Executing operation with timeout", 
                         operation=operation, 
                         timeout_seconds=timeout_seconds)
        
        try:
            result = await asyncio.wait_for(coro, timeout=timeout_seconds)
            return result
        except asyncio.TimeoutError:
            self.logger.warning("Operation timed out", 
                              operation=operation, 
                              timeout_seconds=timeout_seconds)
            raise
    
    async def execute_with_retry(
        self, 
        operation: str, 
        coro_factory: Any, 
        max_retries: Optional[int] = None,
        base_delay: Optional[float] = None,
        max_delay: Optional[float] = None,
        exponential_base: Optional[float] = None
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
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                if attempt > 0:
                    self.logger.info("Retrying operation", 
                                   operation=operation, 
                                   attempt=attempt, 
                                   max_retries=max_retries)
                
                # Create a new coroutine for each attempt
                if callable(coro_factory):
                    coro = coro_factory()
                else:
                    coro = coro_factory
                
                result = await coro
                if attempt > 0:
                    self.logger.info("Operation succeeded on retry", 
                                   operation=operation, 
                                   attempt=attempt)
                return result
                
            except Exception as e:
                last_exception = e
                
                if attempt == max_retries:
                    self.logger.error("Operation failed after all retries", 
                                    operation=operation, 
                                    max_retries=max_retries, 
                                    final_error=str(e))
                    raise
                
                # Calculate delay with exponential backoff
                delay = min(base_delay * (exponential_base ** attempt), max_delay)
                
                self.logger.warning("Operation failed, retrying", 
                                  operation=operation, 
                                  attempt=attempt + 1, 
                                  max_retries=max_retries, 
                                  delay_seconds=delay, 
                                  error=str(e))
                
                await asyncio.sleep(delay)
        
        # This should never be reached, but just in case
        raise last_exception
    
    def _log_error(self, code: int, message: str, data: Optional[Dict[str, Any]], request_id: Optional[str]) -> None:
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
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "request_id": request_id
        }
        
        if data:
            log_data["error_data"] = data
        
        # Log to stderr for debugging
        error_json = json.dumps(log_data, indent=2)
        print(f"[MCP ERROR] {error_json}", file=sys.stderr)
        
        # Also log to structured logger
        self.logger.error("MCP error occurred", **log_data)
    
    def get_error_summary(self) -> Dict[str, Any]:
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
                    "INTERNAL_ERROR": self.INTERNAL_ERROR
                },
                "server_defined": {
                    "RESOURCE_NOT_FOUND": self.RESOURCE_NOT_FOUND,
                    "RESOURCE_ACCESS_DENIED": self.RESOURCE_ACCESS_DENIED,
                    "RESOURCE_UNAVAILABLE": self.RESOURCE_UNAVAILABLE,
                    "TOOL_UNAVAILABLE": self.TOOL_UNAVAILABLE,
                    "TIMEOUT_ERROR": self.TIMEOUT_ERROR,
                    "VALIDATION_ERROR": self.VALIDATION_ERROR,
                    "EXTERNAL_SERVICE_ERROR": self.EXTERNAL_SERVICE_ERROR,
                    "RATE_LIMIT_ERROR": self.RATE_LIMIT_ERROR
                }
            }
        }
