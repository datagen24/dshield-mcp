"""JSON schema validation for MCP messages.

This module provides comprehensive JSON schema validation for all MCP protocol
messages to prevent malformed input attacks and ensure protocol compliance.
"""

import json
import jsonschema
from typing import Any, Dict, List, Optional, Union
import structlog

logger = structlog.get_logger(__name__)

# Maximum allowed message size (10MB)
MAX_MESSAGE_SIZE = 10 * 1024 * 1024

# Maximum allowed nesting depth
MAX_NESTING_DEPTH = 100

# MCP Protocol JSON Schemas
MCP_REQUEST_SCHEMA = {
    "type": "object",
    "required": ["jsonrpc", "id", "method"],
    "properties": {
        "jsonrpc": {
            "type": "string",
            "const": "2.0"
        },
        "id": {
            "oneOf": [
                {"type": "string"},
                {"type": "number"},
                {"type": "null"}
            ]
        },
        "method": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100,
            "pattern": "^[a-zA-Z_][a-zA-Z0-9_.]*$"
        },
        "params": {
            "type": "object",
            "additionalProperties": True
        }
    },
    "additionalProperties": False
}

MCP_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["jsonrpc", "id"],
    "properties": {
        "jsonrpc": {
            "type": "string",
            "const": "2.0"
        },
        "id": {
            "oneOf": [
                {"type": "string"},
                {"type": "number"},
                {"type": "null"}
            ]
        },
        "result": {
            "type": "object",
            "additionalProperties": True
        },
        "error": {
            "type": "object",
            "required": ["code", "message"],
            "properties": {
                "code": {
                    "type": "integer"
                },
                "message": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 1000
                },
                "data": {
                    "type": "object",
                    "additionalProperties": True
                }
            },
            "additionalProperties": False
        }
    },
    "additionalProperties": False,
    "oneOf": [
        {"required": ["result"]},
        {"required": ["error"]}
    ]
}

MCP_NOTIFICATION_SCHEMA = {
    "type": "object",
    "required": ["jsonrpc", "method"],
    "properties": {
        "jsonrpc": {
            "type": "string",
            "const": "2.0"
        },
        "method": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100,
            "pattern": "^[a-zA-Z_][a-zA-Z0-9_.]*$"
        },
        "params": {
            "type": "object",
            "additionalProperties": True
        }
    },
    "additionalProperties": False
}

# Tool-specific parameter schemas
TOOL_PARAMETER_SCHEMAS = {
    "analyze_campaign": {
        "type": "object",
        "required": ["seed_iocs"],
        "properties": {
            "seed_iocs": {
                "type": "array",
                "items": {
                    "type": "string",
                    "minLength": 1,
                    "maxLength": 1000
                },
                "minItems": 1,
                "maxItems": 100
            },
            "time_range": {
                "type": "object",
                "properties": {
                    "start_time": {"type": "string", "format": "date-time"},
                    "end_time": {"type": "string", "format": "date-time"}
                },
                "additionalProperties": False
            },
            "correlation_window": {
                "type": "integer",
                "minimum": 1,
                "maximum": 1440  # 24 hours in minutes
            }
        },
        "additionalProperties": False
    },
    "get_campaign_timeline": {
        "type": "object",
        "required": ["campaign_id"],
        "properties": {
            "campaign_id": {
                "type": "string",
                "minLength": 1,
                "maxLength": 100,
                "pattern": "^[a-zA-Z0-9_-]+$"
            },
            "granularity": {
                "type": "string",
                "enum": ["hourly", "daily", "weekly"]
            }
        },
        "additionalProperties": False
    },
    "generate_report": {
        "type": "object",
        "required": ["campaign_id"],
        "properties": {
            "campaign_id": {
                "type": "string",
                "minLength": 1,
                "maxLength": 100,
                "pattern": "^[a-zA-Z0-9_-]+$"
            },
            "template_name": {
                "type": "string",
                "minLength": 1,
                "maxLength": 100,
                "pattern": "^[a-zA-Z0-9_-]+$"
            },
            "output_path": {
                "type": "string",
                "minLength": 1,
                "maxLength": 500,
                "pattern": "^[a-zA-Z0-9_/.-]+$"
            }
        },
        "additionalProperties": False
    }
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
        if len(message.encode('utf-8')) > MAX_MESSAGE_SIZE:
            self.logger.warning("Message size exceeds limit", 
                              size=len(message.encode('utf-8')), 
                              limit=MAX_MESSAGE_SIZE)
            return False
        return True
    
    def validate_json_structure(self, message: str) -> Optional[Dict[str, Any]]:
        """Validate JSON structure and nesting depth.
        
        Args:
            message: The JSON message string
            
        Returns:
            Parsed JSON object if valid, None otherwise
        """
        try:
            # Check for valid UTF-8 encoding
            message.encode('utf-8').decode('utf-8')
        except UnicodeDecodeError as e:
            self.logger.warning("Invalid UTF-8 sequence in message", error=str(e))
            return None
        
        try:
            parsed = json.loads(message)
        except json.JSONDecodeError as e:
            self.logger.warning("Invalid JSON structure", error=str(e))
            return None
        
        # Check nesting depth
        if self._get_nesting_depth(parsed) > MAX_NESTING_DEPTH:
            self.logger.warning("JSON nesting depth exceeds limit", 
                              depth=self._get_nesting_depth(parsed),
                              limit=MAX_NESTING_DEPTH)
            return None
        
        return parsed
    
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
            return max(self._get_nesting_depth(value, current_depth + 1) 
                      for value in obj.values())
        elif isinstance(obj, list):
            if not obj:
                return current_depth
            return max(self._get_nesting_depth(item, current_depth + 1) 
                      for item in obj)
        else:
            return current_depth
    
    def validate_request(self, message: Dict[str, Any]) -> bool:
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
            self.logger.warning("MCP request validation failed", 
                              error=str(e), 
                              message=message)
            return False
        except Exception as e:
            self.logger.error("Unexpected error during request validation", error=str(e))
            return False
    
    def validate_response(self, message: Dict[str, Any]) -> bool:
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
            self.logger.warning("MCP response validation failed", 
                              error=str(e), 
                              message=message)
            return False
        except Exception as e:
            self.logger.error("Unexpected error during response validation", error=str(e))
            return False
    
    def validate_notification(self, message: Dict[str, Any]) -> bool:
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
            self.logger.warning("MCP notification validation failed", 
                              error=str(e), 
                              message=message)
            return False
        except Exception as e:
            self.logger.error("Unexpected error during notification validation", error=str(e))
            return False
    
    def validate_tool_parameters(self, tool_name: str, params: Dict[str, Any]) -> bool:
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
            self.logger.warning("Tool parameter validation failed", 
                              tool_name=tool_name,
                              error=str(e), 
                              params=params)
            return False
        except Exception as e:
            self.logger.error("Unexpected error during tool parameter validation", 
                            tool_name=tool_name, error=str(e))
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
        value = ''.join(char for char in value if ord(char) >= 32 or char in '\t\n\r')
        
        # Remove potential SQL injection patterns
        sql_patterns = [
            r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)",
            r"(--|#|/\*|\*/)",
            r"(\b(OR|AND)\s+\d+\s*=\s*\d+)",
            r"(\b(OR|AND)\s+'.*'\s*=\s*'.*')",
            r"(\b(OR|AND)\s+\".*\"\s*=\s*\".*\")"
        ]
        
        import re
        for pattern in sql_patterns:
            value = re.sub(pattern, '', value, flags=re.IGNORECASE)
        
        return value.strip()
    
    def validate_complete_message(self, message: str) -> Optional[Dict[str, Any]]:
        """Perform complete message validation.
        
        Args:
            message: The raw JSON message string
            
        Returns:
            Validated and parsed message if valid, None otherwise
        """
        # Check message size
        if not self.validate_message_size(message):
            return None
        
        # Parse and validate JSON structure
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
        if (parsed.get("method", "").startswith("tools/") and 
            "params" in parsed and parsed["params"]):
            tool_name = parsed["method"].replace("tools/", "")
            if not self.validate_tool_parameters(tool_name, parsed["params"]):
                return None
        
        return parsed
