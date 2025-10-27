# get_feature_status

Get feature status tool.

This tool provides functionality to check the status of specific
features or all features in the MCP server.

## GetFeatureStatusTool

Tool for checking feature status.

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
