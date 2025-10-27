# get_health_status

Get health status tool.

This tool provides functionality to check the health status
of the MCP server and its dependencies.

## GetHealthStatusTool

Tool for checking health status.

#### definition

```python
def definition(self)
```

Return the tool definition.

#### validate_arguments

```python
def validate_arguments(self, arguments)
```

Validate tool arguments.
        
        Args:
            arguments: Arguments to validate
            
        Raises:
            ValueError: If arguments are invalid
