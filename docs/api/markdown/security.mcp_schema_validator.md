# mcp_schema_validator

JSON schema validation for MCP messages.

This module provides comprehensive JSON schema validation for all MCP protocol
messages to prevent malformed input attacks and ensure protocol compliance.

## MCPSchemaValidator

Validates MCP protocol messages against JSON schemas.

#### __init__

```python
def __init__(self)
```

Initialize the MCP schema validator.

#### _compile_schemas

```python
def _compile_schemas(self)
```

Compile JSON schemas for better performance.

#### validate_message_size

```python
def validate_message_size(self, message)
```

Validate message size is within limits.

        Args:
            message: The JSON message string

        Returns:
            True if message size is valid, False otherwise

#### validate_json_structure

```python
def validate_json_structure(self, message)
```

Validate JSON structure, nesting depth, and array sizes.

        Args:
            message: The JSON message string

        Returns:
            Parsed JSON object if valid, None otherwise

#### _get_nesting_depth

```python
def _get_nesting_depth(self, obj, current_depth)
```

Calculate the maximum nesting depth of a JSON object.

        Args:
            obj: The JSON object to analyze
            current_depth: Current nesting depth

        Returns:
            Maximum nesting depth

#### _validate_object_bounds

```python
def _validate_object_bounds(self, obj)
```

Validate object bounds including array sizes and key counts.

        Args:
            obj: The JSON object to validate

        Returns:
            True if bounds are valid, False otherwise

#### validate_request

```python
def validate_request(self, message)
```

Validate an MCP request message.

        Args:
            message: The parsed JSON message

        Returns:
            True if valid, False otherwise

#### validate_response

```python
def validate_response(self, message)
```

Validate an MCP response message.

        Args:
            message: The parsed JSON message

        Returns:
            True if valid, False otherwise

#### validate_notification

```python
def validate_notification(self, message)
```

Validate an MCP notification message.

        Args:
            message: The parsed JSON message

        Returns:
            True if valid, False otherwise

#### validate_tool_parameters

```python
def validate_tool_parameters(self, tool_name, params)
```

Validate tool-specific parameters.

        Args:
            tool_name: Name of the tool
            params: Tool parameters to validate

        Returns:
            True if valid, False otherwise

#### sanitize_string_input

```python
def sanitize_string_input(self, value, max_length)
```

Sanitize string input to prevent injection attacks.

        Args:
            value: Input string to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized string

#### validate_message

```python
def validate_message(self, message)
```

Validate a complete MCP message with all security checks.

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

#### validate_complete_message

```python
def validate_complete_message(self, message)
```

Perform complete message validation.

        Args:
            message: The raw JSON message string

        Returns:
            Validated and parsed message if valid, None otherwise
