# enrich_ip_with_dshield

Enrich IP with DShield tool.

This tool provides functionality to enrich IP addresses with
DShield threat intelligence data.

## EnrichIpWithDShieldTool

Tool for enriching IP addresses with DShield data.

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
