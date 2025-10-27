# base

Base tool class and interfaces for MCP tools.

This module provides the foundation for all MCP tools, including
base classes, interfaces, and common functionality.

## ToolCategory

Categories for organizing MCP tools.

## ToolDefinition

Definition of an MCP tool.
    
    Attributes:
        name: The tool name
        description: Human-readable description
        category: Tool category for organization
        schema: JSON schema for tool parameters
        handler: Async function that handles tool execution
        timeout: Optional timeout in seconds
        requires_features: List of required features for tool availability

## BaseTool

Abstract base class for MCP tools.
    
    All MCP tools should inherit from this class to ensure
    consistent interface and behavior.

#### definition

```python
def definition(self)
```

Return the tool definition.
        
        Returns:
            ToolDefinition: The complete tool definition

#### validate_arguments

```python
def validate_arguments(self, arguments)
```

Validate tool arguments.
        
        Args:
            arguments: Arguments to validate
            
        Raises:
            ValueError: If arguments are invalid
