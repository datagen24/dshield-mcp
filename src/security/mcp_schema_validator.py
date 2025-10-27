"""JSON schema validation for MCP messages.

This module provides comprehensive JSON schema validation for all MCP protocol
messages to prevent malformed input attacks and ensure protocol compliance.
"""

import json
from typing import Any

import jsonschema
import structlog

logger = structlog.get_logger(__name__)

# Resource bounds for security
MAX_MESSAGE_BYTES = 10 * 1024 * 1024  # 10MB
MAX_NESTING_DEPTH = 50  # Reduced for security
MAX_ARRAY_LEN = 1000  # Maximum array length per level
MAX_STRING_LENGTH = 10000  # Maximum string length
MAX_OBJECT_KEYS = 100  # Maximum keys per object

# MCP Protocol JSON Schemas with bounds checking
MCP_REQUEST_SCHEMA = {
    "type": "object",
    "required": ["jsonrpc", "id", "method"],
    "maxProperties": MAX_OBJECT_KEYS,
    "properties": {
        "jsonrpc": {
            "type": "string",
            "const": "2.0",
            "maxLength": MAX_STRING_LENGTH,
        },
        "id": {
            "oneOf": [
                {"type": "string", "maxLength": MAX_STRING_LENGTH},
                {"type": "number"},
                {"type": "null"},
            ],
        },
        "method": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100,
            "pattern": "^[a-zA-Z_][a-zA-Z0-9_./-]*$",
        },
        "params": {
            "type": "object",
            "maxProperties": MAX_OBJECT_KEYS,
            "additionalProperties": True,
        },
    },
    "additionalProperties": False,
}

MCP_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["jsonrpc", "id"],
    "maxProperties": MAX_OBJECT_KEYS,
    "properties": {
        "jsonrpc": {
            "type": "string",
            "const": "2.0",
            "maxLength": MAX_STRING_LENGTH,
        },
        "id": {
            "oneOf": [
                {"type": "string", "maxLength": MAX_STRING_LENGTH},
                {"type": "number"},
                {"type": "null"},
            ],
        },
        "result": {
            "type": "object",
            "maxProperties": MAX_OBJECT_KEYS,
            "additionalProperties": True,
        },
        "error": {
            "type": "object",
            "required": ["code", "message"],
            "maxProperties": MAX_OBJECT_KEYS,
            "properties": {
                "code": {
                    "type": "integer",
                },
                "message": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": MAX_STRING_LENGTH,
                },
                "data": {
                    "type": "object",
                    "maxProperties": MAX_OBJECT_KEYS,
                    "additionalProperties": True,
                },
            },
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
    "oneOf": [
        {"required": ["result"]},
        {"required": ["error"]},
    ],
}

MCP_NOTIFICATION_SCHEMA = {
    "type": "object",
    "required": ["jsonrpc", "method"],
    "maxProperties": MAX_OBJECT_KEYS,
    "properties": {
        "jsonrpc": {
            "type": "string",
            "const": "2.0",
            "maxLength": MAX_STRING_LENGTH,
        },
        "method": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100,
            "pattern": "^[a-zA-Z_][a-zA-Z0-9_./-]*$",
        },
        "params": {
            "type": "object",
            "maxProperties": MAX_OBJECT_KEYS,
            "additionalProperties": True,
        },
    },
    "additionalProperties": False,
}

# Tool-specific parameter schemas with bounds checking
TOOL_PARAMETER_SCHEMAS = {
    # Core MCP methods
    "initialize": {
        "type": "object",
        "maxProperties": MAX_OBJECT_KEYS,
        "properties": {
            "protocolVersion": {
                "type": "string",
                "maxLength": MAX_STRING_LENGTH,
            },
            "capabilities": {
                "type": "object",
                "maxProperties": MAX_OBJECT_KEYS,
                "additionalProperties": True,
            },
            "clientInfo": {
                "type": "object",
                "maxProperties": MAX_OBJECT_KEYS,
                "properties": {
                    "name": {"type": "string", "maxLength": MAX_STRING_LENGTH},
                    "version": {"type": "string", "maxLength": MAX_STRING_LENGTH},
                },
                "additionalProperties": False,
            },
        },
        "additionalProperties": False,
    },
    "tools/list": {
        "type": "object",
        "maxProperties": MAX_OBJECT_KEYS,
        "properties": {},
        "additionalProperties": False,
    },
    "tools/call": {
        "type": "object",
        "required": ["name", "arguments"],
        "maxProperties": MAX_OBJECT_KEYS,
        "properties": {
            "name": {
                "type": "string",
                "minLength": 1,
                "maxLength": 100,
                "pattern": "^[a-zA-Z_][a-zA-Z0-9_]*$",
            },
            "arguments": {
                "type": "object",
                "maxProperties": MAX_OBJECT_KEYS,
                "additionalProperties": True,
            },
        },
        "additionalProperties": False,
    },
    "resources/list": {
        "type": "object",
        "maxProperties": MAX_OBJECT_KEYS,
        "properties": {},
        "additionalProperties": False,
    },
    "resources/read": {
        "type": "object",
        "required": ["uri"],
        "maxProperties": MAX_OBJECT_KEYS,
        "properties": {
            "uri": {
                "type": "string",
                "minLength": 1,
                "maxLength": MAX_STRING_LENGTH,
                "pattern": "^[a-zA-Z0-9_/.-]+$",
            },
        },
        "additionalProperties": False,
    },
    "prompts/list": {
        "type": "object",
        "maxProperties": MAX_OBJECT_KEYS,
        "properties": {},
        "additionalProperties": False,
    },
    "prompts/get": {
        "type": "object",
        "required": ["name"],
        "maxProperties": MAX_OBJECT_KEYS,
        "properties": {
            "name": {
                "type": "string",
                "minLength": 1,
                "maxLength": 100,
                "pattern": "^[a-zA-Z_][a-zA-Z0-9_]*$",
            },
            "arguments": {
                "type": "object",
                "maxProperties": MAX_OBJECT_KEYS,
                "additionalProperties": True,
            },
        },
        "additionalProperties": False,
    },
    # DShield-specific tools
    "query_dshield_events": {
        "type": "object",
        "maxProperties": MAX_OBJECT_KEYS,
        "properties": {
            "time_range_hours": {
                "type": "integer",
                "minimum": 1,
                "maximum": 168,  # 1 week max
            },
            "time_range": {
                "type": "object",
                "maxProperties": MAX_OBJECT_KEYS,
                "properties": {
                    "start": {
                        "type": "string",
                        "maxLength": MAX_STRING_LENGTH,
                        "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z?$",
                    },
                    "end": {
                        "type": "string",
                        "maxLength": MAX_STRING_LENGTH,
                        "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z?$",
                    },
                },
                "additionalProperties": False,
            },
            "relative_time": {
                "type": "string",
                "maxLength": MAX_STRING_LENGTH,
                "enum": ["last_1_hour", "last_6_hours", "last_24_hours", "last_7_days"],
            },
            "indices": {
                "type": "array",
                "items": {
                    "type": "string",
                    "maxLength": MAX_STRING_LENGTH,
                },
                "maxItems": MAX_ARRAY_LEN,
            },
            "filters": {
                "type": "object",
                "maxProperties": MAX_OBJECT_KEYS,
                "additionalProperties": True,
            },
            "fields": {
                "type": "array",
                "items": {
                    "type": "string",
                    "maxLength": MAX_STRING_LENGTH,
                },
                "maxItems": MAX_ARRAY_LEN,
            },
            "page": {
                "type": "integer",
                "minimum": 1,
                "maximum": 10000,
            },
            "page_size": {
                "type": "integer",
                "minimum": 1,
                "maximum": 1000,
            },
            "sort_by": {
                "type": "string",
                "maxLength": MAX_STRING_LENGTH,
            },
            "sort_order": {
                "type": "string",
                "enum": ["asc", "desc"],
            },
            "cursor": {
                "type": "string",
                "maxLength": MAX_STRING_LENGTH,
            },
            "optimization": {
                "type": "string",
                "enum": ["auto", "none"],
            },
            "fallback_strategy": {
                "type": "string",
                "enum": ["aggregate", "sample", "error"],
            },
            "max_result_size_mb": {
                "type": "number",
                "minimum": 0.1,
                "maximum": 100.0,
            },
            "query_timeout_seconds": {
                "type": "integer",
                "minimum": 1,
                "maximum": 300,
            },
            "include_summary": {
                "type": "boolean",
            },
        },
        "additionalProperties": False,
    },
    "analyze_campaign": {
        "type": "object",
        "required": ["seed_iocs"],
        "maxProperties": MAX_OBJECT_KEYS,
        "properties": {
            "seed_iocs": {
                "type": "array",
                "items": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": MAX_STRING_LENGTH,
                },
                "minItems": 1,
                "maxItems": MAX_ARRAY_LEN,
            },
            "time_range": {
                "type": "object",
                "maxProperties": MAX_OBJECT_KEYS,
                "properties": {
                    "start_time": {
                        "type": "string",
                        "maxLength": MAX_STRING_LENGTH,
                        "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z?$",
                    },
                    "end_time": {
                        "type": "string",
                        "maxLength": MAX_STRING_LENGTH,
                        "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z?$",
                    },
                },
                "additionalProperties": False,
            },
            "correlation_window": {
                "type": "integer",
                "minimum": 1,
                "maximum": 1440,  # 24 hours in minutes
            },
        },
        "additionalProperties": False,
    },
    "get_campaign_timeline": {
        "type": "object",
        "required": ["campaign_id"],
        "maxProperties": MAX_OBJECT_KEYS,
        "properties": {
            "campaign_id": {
                "type": "string",
                "minLength": 1,
                "maxLength": 100,
                "pattern": "^[a-zA-Z0-9_-]+$",
            },
            "granularity": {
                "type": "string",
                "enum": ["hourly", "daily", "weekly"],
            },
        },
        "additionalProperties": False,
    },
    "generate_report": {
        "type": "object",
        "required": ["campaign_id"],
        "maxProperties": MAX_OBJECT_KEYS,
        "properties": {
            "campaign_id": {
                "type": "string",
                "minLength": 1,
                "maxLength": 100,
                "pattern": "^[a-zA-Z0-9_-]+$",
            },
            "template_name": {
                "type": "string",
                "minLength": 1,
                "maxLength": 100,
                "pattern": "^[a-zA-Z0-9_-]+$",
            },
            "output_path": {
                "type": "string",
                "minLength": 1,
                "maxLength": 500,
                "pattern": "^[a-zA-Z0-9_/.-]+$",
            },
        },
        "additionalProperties": False,
    },
}


class MCPSchemaValidator:
    """Validates MCP protocol messages against JSON schemas."""

    def __init__(self) -> None:
        """Initialize the MCP schema validator."""
        self.logger = structlog.get_logger(__name__)
        self._compile_schemas()

    def _compile_schemas(self) -> None:
        """Compile JSON schemas for better performance."""
        try:
            self.request_validator = jsonschema.Draft7Validator(MCP_REQUEST_SCHEMA)
            self.response_validator = jsonschema.Draft7Validator(MCP_RESPONSE_SCHEMA)
            self.notification_validator = jsonschema.Draft7Validator(MCP_NOTIFICATION_SCHEMA)

            # Compile tool parameter validators
            self.tool_validators = {}
            for tool_name, schema in TOOL_PARAMETER_SCHEMAS.items():
                self.tool_validators[tool_name] = jsonschema.Draft7Validator(schema)

            self.logger.info("MCP schemas compiled successfully")

        except Exception as e:
            self.logger.error("Failed to compile MCP schemas", error=str(e))
            raise

    def validate_message_size(self, message: str) -> bool:
        """Validate message size is within limits.

        Args:
            message: The JSON message string

        Returns:
            True if message size is valid, False otherwise

        """
        message_bytes = len(message.encode("utf-8"))
        if message_bytes > MAX_MESSAGE_BYTES:
            self.logger.warning(
                "Message size exceeds limit",
                size=message_bytes,
                limit=MAX_MESSAGE_BYTES,
            )
            return False
        return True

    def validate_json_structure(self, message: str) -> dict[str, Any] | None:
        """Validate JSON structure, nesting depth, and array sizes.

        Args:
            message: The JSON message string

        Returns:
            Parsed JSON object if valid, None otherwise

        """
        try:
            # Check for valid UTF-8 encoding
            message.encode("utf-8").decode("utf-8")
        except UnicodeDecodeError as e:
            self.logger.warning("Invalid UTF-8 sequence in message", error=str(e))
            return None

        try:
            parsed = json.loads(message)
        except json.JSONDecodeError as e:
            self.logger.warning("Invalid JSON structure", error=str(e))
            return None

        # Check nesting depth
        depth = self._get_nesting_depth(parsed)
        if depth > MAX_NESTING_DEPTH:
            self.logger.warning(
                "JSON nesting depth exceeds limit",
                depth=depth,
                limit=MAX_NESTING_DEPTH,
            )
            return None

        # Check array sizes and object key counts
        if not self._validate_object_bounds(parsed):
            return None

        return parsed  # type: ignore[no-any-return]

    def _get_nesting_depth(self, obj: Any, current_depth: int = 0) -> int:
        """Calculate the maximum nesting depth of a JSON object.

        Args:
            obj: The JSON object to analyze
            current_depth: Current nesting depth

        Returns:
            Maximum nesting depth

        """
        if current_depth > MAX_NESTING_DEPTH:
            return current_depth

        if isinstance(obj, dict):
            if not obj:
                return current_depth
            return max(self._get_nesting_depth(value, current_depth + 1) for value in obj.values())
        if isinstance(obj, list):
            if not obj:
                return current_depth
            return max(self._get_nesting_depth(item, current_depth + 1) for item in obj)
        return current_depth  # Leaf nodes return current depth

    def _validate_object_bounds(self, obj: Any) -> bool:
        """Validate object bounds including array sizes and key counts.

        Args:
            obj: The JSON object to validate

        Returns:
            True if bounds are valid, False otherwise

        """
        if isinstance(obj, dict):
            # Check object key count
            if len(obj) > MAX_OBJECT_KEYS:
                self.logger.warning(
                    "Object has too many keys",
                    key_count=len(obj),
                    limit=MAX_OBJECT_KEYS,
                )
                return False

            # Check string lengths in keys and values
            for key, value in obj.items():
                if isinstance(key, str) and len(key) > MAX_STRING_LENGTH:
                    self.logger.warning(
                        "Object key too long",
                        key_length=len(key),
                        limit=MAX_STRING_LENGTH,
                    )
                    return False

                if isinstance(value, str) and len(value) > MAX_STRING_LENGTH:
                    self.logger.warning(
                        "String value too long",
                        value_length=len(value),
                        limit=MAX_STRING_LENGTH,
                    )
                    return False

                # Recursively check nested objects
                if not self._validate_object_bounds(value):
                    return False

        elif isinstance(obj, list):
            # Check array length
            if len(obj) > MAX_ARRAY_LEN:
                self.logger.warning(
                    "Array too long",
                    array_length=len(obj),
                    limit=MAX_ARRAY_LEN,
                )
                return False

            # Check string lengths in array items
            for item in obj:
                if isinstance(item, str) and len(item) > MAX_STRING_LENGTH:
                    self.logger.warning(
                        "Array item string too long",
                        item_length=len(item),
                        limit=MAX_STRING_LENGTH,
                    )
                    return False

                # Recursively check nested objects
                if not self._validate_object_bounds(item):
                    return False

        return True

    def validate_request(self, message: dict[str, Any]) -> bool:
        """Validate an MCP request message.

        Args:
            message: The parsed JSON message

        Returns:
            True if valid, False otherwise

        """
        try:
            self.request_validator.validate(message)
            return True
        except jsonschema.ValidationError as e:
            self.logger.warning("MCP request validation failed", error=str(e), message=message)
            return False
        except Exception as e:
            self.logger.error("Unexpected error during request validation", error=str(e))
            return False

    def validate_response(self, message: dict[str, Any]) -> bool:
        """Validate an MCP response message.

        Args:
            message: The parsed JSON message

        Returns:
            True if valid, False otherwise

        """
        try:
            self.response_validator.validate(message)
            return True
        except jsonschema.ValidationError as e:
            self.logger.warning("MCP response validation failed", error=str(e), message=message)
            return False
        except Exception as e:
            self.logger.error("Unexpected error during response validation", error=str(e))
            return False

    def validate_notification(self, message: dict[str, Any]) -> bool:
        """Validate an MCP notification message.

        Args:
            message: The parsed JSON message

        Returns:
            True if valid, False otherwise

        """
        try:
            self.notification_validator.validate(message)
            return True
        except jsonschema.ValidationError as e:
            self.logger.warning("MCP notification validation failed", error=str(e), message=message)
            return False
        except Exception as e:
            self.logger.error("Unexpected error during notification validation", error=str(e))
            return False

    def validate_tool_parameters(self, tool_name: str, params: dict[str, Any]) -> bool:
        """Validate tool-specific parameters.

        Args:
            tool_name: Name of the tool
            params: Tool parameters to validate

        Returns:
            True if valid, False otherwise

        """
        if tool_name not in self.tool_validators:
            self.logger.warning("Unknown tool for parameter validation", tool_name=tool_name)
            return False

        try:
            self.tool_validators[tool_name].validate(params)
            return True
        except jsonschema.ValidationError as e:
            self.logger.warning(
                "Tool parameter validation failed", tool_name=tool_name, error=str(e), params=params
            )
            return False
        except Exception as e:
            self.logger.error(
                "Unexpected error during tool parameter validation",
                tool_name=tool_name,
                error=str(e),
            )
            return False

    def sanitize_string_input(self, value: str, max_length: int = 1000) -> str:
        """Sanitize string input to prevent injection attacks.

        Args:
            value: Input string to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized string

        """
        if not isinstance(value, str):
            return str(value)

        # Truncate if too long
        if len(value) > max_length:
            value = value[:max_length]

        # Remove null bytes and control characters
        value = "".join(char for char in value if ord(char) >= 32 or char in "\t\n\r")

        # Remove potential SQL injection patterns
        sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(--|#|/\*|\*/)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\b(OR|AND)\s+'.*'\s*=\s*'.*')",
            r"(\b(OR|AND)\s+\".*\"\s*=\s*\".*\")",
        ]

        # Remove XSS patterns
        xss_patterns = [
            r"<script[^>]*>.*?</script>",
            r"javascript:",
            r"on\w+\s*=",
            r"<iframe[^>]*>.*?</iframe>",
            r"<object[^>]*>.*?</object>",
            r"<embed[^>]*>.*?</embed>",
        ]

        # Remove path traversal patterns
        path_patterns = [
            r"\.\./",
            r"\.\.\\",
            r"/etc/passwd",
            r"/windows/system32",
            r"/proc/self/environ",
        ]

        import re

        all_patterns = sql_patterns + xss_patterns + path_patterns
        for pattern in all_patterns:
            value = re.sub(pattern, "", value, flags=re.IGNORECASE)

        return value.strip()

    def validate_message(self, message: str) -> dict[str, Any] | None:
        """Validate a complete MCP message with all security checks.

        This is the main entry point for message validation that performs:
        - Size bounds checking
        - JSON structure validation
        - Nesting depth validation
        - Array size validation
        - Object key count validation
        - String length validation
        - JSON-RPC 2.0 compliance
        - Method-specific parameter validation

        Args:
            message: The raw JSON message string

        Returns:
            Validated and parsed message if valid, None otherwise

        """
        # Check message size
        if not self.validate_message_size(message):
            return None

        # Parse and validate JSON structure with bounds checking
        parsed = self.validate_json_structure(message)
        if parsed is None:
            return None

        # Determine message type and validate accordingly
        if "id" in parsed and "method" in parsed:
            if not self.validate_request(parsed):
                return None
        elif "id" in parsed and ("result" in parsed or "error" in parsed):
            if not self.validate_response(parsed):
                return None
        elif "method" in parsed and "id" not in parsed:
            if not self.validate_notification(parsed):
                return None
        else:
            self.logger.warning("Unknown MCP message type", message=parsed)
            return None

        # Validate tool parameters if this is a tool call
        if (
            parsed.get("method", "").startswith("tools/")
            and "params" in parsed
            and parsed["params"]
        ):
            tool_name = parsed["method"].replace("tools/", "")
            if not self.validate_tool_parameters(tool_name, parsed["params"]):
                return None

        return parsed

    def validate_complete_message(self, message: str) -> dict[str, Any] | None:
        """Perform complete message validation.

        Args:
            message: The raw JSON message string

        Returns:
            Validated and parsed message if valid, None otherwise

        """
        return self.validate_message(message)
