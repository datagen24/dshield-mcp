# analyze_campaign

Analyze campaign tool.

This tool provides functionality to analyze attack campaigns by correlating
events, expanding IOCs, and building attack timelines.

## AnalyzeCampaignTool

Tool for analyzing attack campaigns.

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
