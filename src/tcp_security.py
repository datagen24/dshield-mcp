#!/usr/bin/env python3
"""TCP security module for DShield MCP Server.

This module provides security measures for TCP transport, including
rate limiting, input validation, and abuse detection.
"""

import json
import re
from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class SecurityViolation(Exception):
    """Exception raised for security violations.

    Attributes:
        violation_type: Type of security violation
        message: Violation message
        details: Additional violation details

    """

    def __init__(
        self, violation_type: str, message: str, details: dict[str, Any] | None = None
    ) -> None:
        """Initialize security violation.

        Args:
            violation_type: Type of security violation
            message: Violation message
            details: Additional violation details

        """
        super().__init__(message)
        self.violation_type = violation_type
        self.message = message
        self.details = details or {}


class RateLimiter:
    """Advanced rate limiter with multiple strategies.

    Implements token bucket, sliding window, and adaptive rate limiting
    for different types of operations and clients.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_limit: int = 10,
        window_size: int = 60,
        adaptive: bool = True,
    ) -> None:
        """Initialize the rate limiter.

        Args:
            requests_per_minute: Maximum requests per minute
            burst_limit: Maximum burst requests
            window_size: Time window size in seconds
            adaptive: Whether to use adaptive rate limiting

        """
        self.requests_per_minute = requests_per_minute
        self.burst_limit = burst_limit
        self.window_size = window_size
        self.adaptive = adaptive

        # Token bucket parameters
        self.tokens = burst_limit
        self.last_refill = datetime.now(UTC)

        # Sliding window parameters
        self.request_times: deque[datetime] = deque()

        # Adaptive parameters
        self.current_limit = requests_per_minute
        self.violation_count = 0
        self.last_violation: datetime | None = None

    def is_allowed(self, client_id: str = "default") -> bool:
        """Check if a request is allowed.

        Args:
            client_id: Client identifier for tracking

        Returns:
            True if request is allowed, False if rate limited

        """
        now = datetime.utcnow()

        # Token bucket check
        if not self._check_token_bucket(now):
            return False

        # Sliding window check
        if not self._check_sliding_window(now):
            return False

        # Adaptive rate limiting
        if self.adaptive:
            self._update_adaptive_limits(now)

        return True

    def _check_token_bucket(self, now: datetime) -> bool:
        """Check token bucket rate limiting.

        Args:
            now: Current timestamp

        Returns:
            True if tokens available, False otherwise

        """
        time_passed = (now - self.last_refill).total_seconds()

        # Refill tokens based on time passed
        tokens_to_add = (time_passed / 60.0) * self.requests_per_minute
        self.tokens = min(self.burst_limit, int(self.tokens + tokens_to_add))
        self.last_refill = now

        # Check if we have tokens available
        if self.tokens >= 1:
            self.tokens -= 1
            return True
        return False

    def _check_sliding_window(self, now: datetime) -> bool:
        """Check sliding window rate limiting.

        Args:
            now: Current timestamp

        Returns:
            True if within window limits, False otherwise

        """
        # Remove old requests outside the window
        cutoff_time = now - timedelta(seconds=self.window_size)
        while self.request_times and self.request_times[0] < cutoff_time:
            self.request_times.popleft()

        # Check if we're within the limit
        if len(self.request_times) >= self.current_limit:
            return False

        # Add current request
        self.request_times.append(now)
        return True

    def _update_adaptive_limits(self, now: datetime) -> None:
        """Update adaptive rate limits based on recent violations.

        Args:
            now: Current timestamp

        """
        # If we had a recent violation, reduce the limit
        if self.last_violation and (now - self.last_violation).total_seconds() < 300:  # 5 minutes
            self.current_limit = max(10, int(self.current_limit * 0.8))  # Reduce by 20%, minimum 10
        else:
            # Gradually increase the limit back to normal
            self.current_limit = min(self.requests_per_minute, int(self.current_limit * 1.05))

    def record_violation(self) -> None:
        """Record a rate limit violation."""
        self.violation_count += 1
        self.last_violation = datetime.utcnow()
        logger.warning(
            "Rate limit violation recorded",
            violation_count=self.violation_count,
            current_limit=self.current_limit,
        )


class InputValidator:
    """Validates and sanitizes input for TCP connections.

    Provides comprehensive input validation for MCP messages,
    preventing injection attacks and malformed requests.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the input validator.

        Args:
            config: Validation configuration

        """
        self.config = config or {}
        self.max_message_size = self.config.get("max_message_size", 1048576)  # 1MB
        self.max_field_length = self.config.get("max_field_length", 10000)
        self.allowed_methods = self.config.get(
            "allowed_methods",
            [
                "initialize",
                "initialized",
                "tools/list",
                "tools/call",
                "resources/list",
                "resources/read",
                "prompts/list",
                "prompts/get",
            ],
        )

        # Compile regex patterns for validation
        self.safe_string_pattern = re.compile(r"^[a-zA-Z0-9_\-\.\s]+$")
        self.json_rpc_id_pattern = re.compile(r"^[a-zA-Z0-9_\-]+$")

    def validate_message(self, message: dict[str, Any]) -> dict[str, Any]:
        """Validate an MCP message.

        Args:
            message: Message to validate

        Returns:
            Validated and sanitized message

        Raises:
            SecurityViolation: If message validation fails

        """
        try:
            # Check message size
            message_str = json.dumps(message)
            if len(message_str) > self.max_message_size:
                raise SecurityViolation(
                    "MESSAGE_SIZE_EXCEEDED",
                    f"Message size exceeds maximum allowed size of {self.max_message_size} bytes",
                    {"message_size": len(message_str), "max_size": self.max_message_size},
                )

            # Validate JSON-RPC structure
            self._validate_json_rpc_structure(message)

            # Validate method if present
            if "method" in message:
                self._validate_method(message["method"])

            # Validate parameters if present
            if "params" in message:
                self._validate_params(message["params"])

            # Validate ID if present
            if "id" in message:
                self._validate_id(message["id"])

            return message

        except SecurityViolation:
            raise
        except Exception as e:
            raise SecurityViolation(
                "VALIDATION_ERROR",
                f"Message validation failed: {e}",
                {"error": str(e)},
            ) from e

    def _validate_json_rpc_structure(self, message: dict[str, Any]) -> None:
        """Validate JSON-RPC 2.0 structure.

        Args:
            message: Message to validate

        Raises:
            SecurityViolation: If structure is invalid

        """
        # Check required fields
        if "jsonrpc" not in message:
            raise SecurityViolation(
                "MISSING_JSONRPC_VERSION",
                "Missing required 'jsonrpc' field",
                {"required_field": "jsonrpc"},
            )

        if message["jsonrpc"] != "2.0":
            raise SecurityViolation(
                "INVALID_JSONRPC_VERSION",
                "Invalid JSON-RPC version, must be '2.0'",
                {"version": message["jsonrpc"]},
            )

        # Check for required fields based on message type
        if "method" in message:
            # Request or notification
            if "id" not in message:
                # Notification (no response expected)
                pass
            else:
                # Request (response expected)
                pass
        elif "result" in message or "error" in message:
            # Response
            if "id" not in message:
                raise SecurityViolation(
                    "MISSING_RESPONSE_ID",
                    "Response messages must include 'id' field",
                    {"message_type": "response"},
                )
        else:
            raise SecurityViolation(
                "INVALID_MESSAGE_TYPE",
                "Message must be request, notification, or response",
                {"message": message},
            )

    def _validate_method(self, method: str) -> None:
        """Validate method name.

        Args:
            method: Method name to validate

        Raises:
            SecurityViolation: If method is invalid

        """
        if not isinstance(method, str):
            raise SecurityViolation(
                "INVALID_METHOD_TYPE",
                "Method must be a string",
                {"method_type": type(method).__name__},
            )

        if len(method) > self.max_field_length:
            raise SecurityViolation(
                "METHOD_TOO_LONG",
                f"Method name exceeds maximum length of {self.max_field_length}",
                {"method_length": len(method), "max_length": self.max_field_length},
            )

        if method not in self.allowed_methods:
            raise SecurityViolation(
                "METHOD_NOT_ALLOWED",
                f"Method '{method}' is not allowed",
                {"method": method, "allowed_methods": self.allowed_methods},
            )

    def _validate_params(self, params: Any) -> None:
        """Validate parameters.

        Args:
            params: Parameters to validate

        Raises:
            SecurityViolation: If parameters are invalid

        """
        if params is None:
            return

        if not isinstance(params, dict | list):
            raise SecurityViolation(
                "INVALID_PARAMS_TYPE",
                "Parameters must be an object or array",
                {"params_type": type(params).__name__},
            )

        # Validate parameter structure
        if isinstance(params, dict):
            self._validate_object_params(params)
        elif isinstance(params, list):
            self._validate_array_params(params)

    def _validate_object_params(self, params: dict[str, Any]) -> None:
        """Validate object parameters.

        Args:
            params: Object parameters to validate

        Raises:
            SecurityViolation: If parameters are invalid

        """
        for key, value in params.items():
            # Validate key
            if not isinstance(key, str):
                raise SecurityViolation(
                    "INVALID_PARAM_KEY_TYPE",
                    "Parameter keys must be strings",
                    {"key": key, "key_type": type(key).__name__},
                )

            if len(key) > self.max_field_length:
                raise SecurityViolation(
                    "PARAM_KEY_TOO_LONG",
                    f"Parameter key exceeds maximum length of {self.max_field_length}",
                    {"key": key, "key_length": len(key)},
                )

            # Validate value
            self._validate_param_value(value)

    def _validate_array_params(self, params: list[Any]) -> None:
        """Validate array parameters.

        Args:
            params: Array parameters to validate

        Raises:
            SecurityViolation: If parameters are invalid

        """
        if len(params) > 100:  # Reasonable limit for array size
            raise SecurityViolation(
                "PARAMS_ARRAY_TOO_LARGE",
                "Parameters array exceeds maximum size of 100",
                {"array_size": len(params)},
            )

        for i, value in enumerate(params):
            self._validate_param_value(value, f"params[{i}]")

    def _validate_param_value(self, value: Any, path: str = "params") -> None:
        """Validate a parameter value.

        Args:
            value: Value to validate
            path: Path to the value for error reporting

        Raises:
            SecurityViolation: If value is invalid

        """
        if isinstance(value, str):
            if len(value) > self.max_field_length:
                raise SecurityViolation(
                    "PARAM_VALUE_TOO_LONG",
                    f"Parameter value at '{path}' exceeds maximum length of "
                    f"{self.max_field_length}",
                    {"path": path, "value_length": len(value)},
                )
        elif isinstance(value, dict | list):
            # Recursively validate nested structures
            if isinstance(value, dict):
                self._validate_object_params(value)
            else:
                self._validate_array_params(value)
        elif not isinstance(value, int | float | bool | type(None)):
            raise SecurityViolation(
                "INVALID_PARAM_VALUE_TYPE",
                f"Parameter value at '{path}' has invalid type",
                {"path": path, "value_type": type(value).__name__},
            )

    def _validate_id(self, id_value: Any) -> None:
        """Validate JSON-RPC ID.

        Args:
            id_value: ID value to validate

        Raises:
            SecurityViolation: If ID is invalid

        """
        if id_value is None:
            return  # Null ID is allowed for notifications

        if not isinstance(id_value, str | int | float):
            raise SecurityViolation(
                "INVALID_ID_TYPE",
                "ID must be a string, number, or null",
                {"id_type": type(id_value).__name__},
            )

        if isinstance(id_value, str):
            if len(id_value) > self.max_field_length:
                raise SecurityViolation(
                    "ID_TOO_LONG",
                    f"ID exceeds maximum length of {self.max_field_length}",
                    {"id_length": len(id_value)},
                )


class TCPSecurityManager:
    """Manages security for TCP connections.

    Provides comprehensive security measures including rate limiting,
    input validation, abuse detection, and connection monitoring.
    """

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        """Initialize the TCP security manager.

        Args:
            config: Security configuration

        """
        self.config = config or {}
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")

        # Initialize components
        self.input_validator = InputValidator(self.config.get("input_validation", {}))
        self.global_rate_limiter = RateLimiter(
            requests_per_minute=self.config.get("global_rate_limit", 1000),
            burst_limit=self.config.get("global_burst_limit", 100),
        )

        # Per-client rate limiters
        self.client_rate_limiters: dict[str, RateLimiter] = {}

        # Abuse detection
        self.violation_counts: dict[str, int] = defaultdict(int)
        self.blocked_clients: set[str] = set()
        self.abuse_threshold = self.config.get("abuse_threshold", 10)
        self.block_duration = self.config.get("block_duration_seconds", 3600)  # 1 hour
        self.client_block_times: dict[str, datetime] = {}

        # Connection monitoring
        self.connection_attempts: dict[str, list[datetime]] = defaultdict(list)
        self.max_connection_attempts = self.config.get("max_connection_attempts", 5)
        self.connection_window = self.config.get("connection_window_seconds", 300)  # 5 minutes

    def validate_message(self, message: dict[str, Any], client_id: str) -> dict[str, Any]:
        """Validate a message from a client.

        Args:
            message: Message to validate
            client_id: Client identifier

        Returns:
            Validated message

        Raises:
            SecurityViolation: If validation fails

        """
        # Check if client is blocked
        if self._is_client_blocked(client_id):
            raise SecurityViolation(
                "CLIENT_BLOCKED",
                "Client is temporarily blocked due to security violations",
                {"client_id": client_id, "blocked_until": self.client_block_times.get(client_id)},
            )

        # Validate input
        validated_message = self.input_validator.validate_message(message)

        # Check rate limits
        if not self._check_rate_limits(client_id):
            self._record_violation(client_id, "RATE_LIMIT_EXCEEDED")
            raise SecurityViolation(
                "RATE_LIMIT_EXCEEDED",
                "Rate limit exceeded for client",
                {"client_id": client_id},
            )

        return validated_message

    def _is_client_blocked(self, client_id: str) -> bool:
        """Check if a client is currently blocked.

        Args:
            client_id: Client identifier

        Returns:
            True if client is blocked, False otherwise

        """
        if client_id not in self.blocked_clients:
            return False

        block_time = self.client_block_times.get(client_id)
        if not block_time:
            return False

        # Check if block has expired
        if datetime.utcnow() > block_time + timedelta(seconds=self.block_duration):
            self._unblock_client(client_id)
            return False

        return True

    def _check_rate_limits(self, client_id: str) -> bool:
        """Check rate limits for a client.

        Args:
            client_id: Client identifier

        Returns:
            True if within rate limits, False otherwise

        """
        # Check global rate limit
        if not self.global_rate_limiter.is_allowed():
            return False

        # Check per-client rate limit
        if client_id not in self.client_rate_limiters:
            # Create rate limiter for new client
            self.client_rate_limiters[client_id] = RateLimiter(
                requests_per_minute=self.config.get("client_rate_limit", 60),
                burst_limit=self.config.get("client_burst_limit", 10),
            )

        return self.client_rate_limiters[client_id].is_allowed(client_id)

    def _record_violation(self, client_id: str, violation_type: str) -> None:
        """Record a security violation for a client.

        Args:
            client_id: Client identifier
            violation_type: Type of violation

        """
        self.violation_counts[client_id] += 1

        self.logger.warning(
            "Security violation recorded",
            client_id=client_id,
            violation_type=violation_type,
            violation_count=self.violation_counts[client_id],
        )

        # Check if client should be blocked
        if self.violation_counts[client_id] >= self.abuse_threshold:
            self._block_client(client_id, violation_type)

    def _block_client(self, client_id: str, violation_type: str) -> None:
        """Block a client due to security violations.

        Args:
            client_id: Client identifier
            violation_type: Type of violation that triggered the block

        """
        self.blocked_clients.add(client_id)
        self.client_block_times[client_id] = datetime.utcnow()

        self.logger.warning(
            "Client blocked due to security violations",
            client_id=client_id,
            violation_type=violation_type,
            violation_count=self.violation_counts[client_id],
            block_duration=self.block_duration,
        )

    def _unblock_client(self, client_id: str) -> None:
        """Unblock a client after block period expires.

        Args:
            client_id: Client identifier

        """
        self.blocked_clients.discard(client_id)
        self.client_block_times.pop(client_id, None)
        self.violation_counts[client_id] = 0

        self.logger.info("Client unblocked", client_id=client_id)

    def record_connection_attempt(self, client_id: str) -> bool:
        """Record a connection attempt and check if it should be allowed.

        Args:
            client_id: Client identifier

        Returns:
            True if connection should be allowed, False otherwise

        """
        now = datetime.utcnow()

        # Clean old attempts
        cutoff_time = now - timedelta(seconds=self.connection_window)
        self.connection_attempts[client_id] = [
            attempt for attempt in self.connection_attempts[client_id] if attempt > cutoff_time
        ]

        # Check if too many attempts
        if len(self.connection_attempts[client_id]) >= self.max_connection_attempts:
            self._record_violation(client_id, "TOO_MANY_CONNECTION_ATTEMPTS")
            return False

        # Record this attempt
        self.connection_attempts[client_id].append(now)
        return True

    def get_security_statistics(self) -> dict[str, Any]:
        """Get security statistics.

        Returns:
            Dictionary of security statistics

        """
        return {
            "rate_limiting": {
                "global_requests_per_minute": self.global_rate_limiter.requests_per_minute,
                "global_burst_limit": self.global_rate_limiter.burst_limit,
                "active_client_limiters": len(self.client_rate_limiters),
            },
            "abuse_detection": {
                "blocked_clients": len(self.blocked_clients),
                "total_violations": sum(self.violation_counts.values()),
                "abuse_threshold": self.abuse_threshold,
                "block_duration": self.block_duration,
            },
            "connection_monitoring": {
                "tracked_clients": len(self.connection_attempts),
                "max_connection_attempts": self.max_connection_attempts,
                "connection_window": self.connection_window,
            },
            "input_validation": {
                "max_message_size": self.input_validator.max_message_size,
                "max_field_length": self.input_validator.max_field_length,
                "allowed_methods": self.input_validator.allowed_methods,
            },
        }

    def cleanup_expired_data(self) -> int:
        """Clean up expired security data.

        Returns:
            Number of items cleaned up

        """
        cleaned_count = 0
        now = datetime.utcnow()

        # Clean up expired blocks
        expired_blocks = [
            client_id
            for client_id, block_time in self.client_block_times.items()
            if now > block_time + timedelta(seconds=self.block_duration)
        ]

        for client_id in expired_blocks:
            self._unblock_client(client_id)
            cleaned_count += 1

        # Clean up old connection attempts
        cutoff_time = now - timedelta(seconds=self.connection_window)
        for client_id in list(self.connection_attempts.keys()):
            old_count = len(self.connection_attempts[client_id])
            self.connection_attempts[client_id] = [
                attempt for attempt in self.connection_attempts[client_id] if attempt > cutoff_time
            ]
            new_count = len(self.connection_attempts[client_id])
            if new_count == 0:
                del self.connection_attempts[client_id]
            cleaned_count += old_count - new_count

        if cleaned_count > 0:
            self.logger.info("Cleaned up expired security data", count=cleaned_count)

        return cleaned_count
