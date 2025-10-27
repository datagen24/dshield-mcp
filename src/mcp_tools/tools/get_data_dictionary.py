"""Get data dictionary tool.

This tool provides functionality to retrieve the data dictionary
for DShield SIEM fields and analysis guidelines.
"""

from typing import Any, Dict, List
from .base import BaseTool, ToolDefinition, ToolCategory


class GetDataDictionaryTool(BaseTool):
    """Tool for retrieving data dictionary."""
    
    @property
    def definition(self) -> ToolDefinition:
        """Return the tool definition."""
        return ToolDefinition(
            name="get_data_dictionary",
            description="Get data dictionary for DShield SIEM fields and analysis guidelines",
            category=ToolCategory.UTILITY,
            schema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Data category to retrieve (e.g., 'core_fields', 'network_fields')",
                    },
                    "format": {
                        "type": "string",
                        "enum": ["json", "markdown", "summary"],
                        "description": "Output format (default: 'json')",
                    },
                },
            },
            handler="_get_data_dictionary",
            timeout=30.0,
            requires_features=[]
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute the get data dictionary tool.
        
        Args:
            arguments: Tool arguments from MCP client
            
        Returns:
            List of result dictionaries
            
        Raises:
            ValueError: If arguments are invalid
            TimeoutError: If execution times out
            Exception: For other execution errors
        """
        # This method will be implemented by the MCP server
        raise NotImplementedError("Tool execution is handled by the MCP server")
    
    def validate_arguments(self, arguments: Dict[str, Any]) -> None:
        """Validate tool arguments.
        
        Args:
            arguments: Arguments to validate
            
        Raises:
            ValueError: If arguments are invalid
        """
        if not isinstance(arguments, dict):
            raise ValueError("Arguments must be a dictionary")
        
        # Validate format if provided
        if "format" in arguments:
            format_value = arguments["format"]
            if format_value not in ["json", "markdown", "summary"]:
                raise ValueError("format must be one of: json, markdown, summary")

