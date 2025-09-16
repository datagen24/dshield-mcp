# query_dshield_events

Query DShield events tool.

This tool provides functionality to query DShield events from Elasticsearch
with various filtering, pagination, and optimization options.

## QueryDShieldEventsTool

Tool for querying DShield events from Elasticsearch.

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
