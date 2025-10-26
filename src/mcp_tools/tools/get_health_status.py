"""Get health status tool.

This tool provides functionality to check the health status
of the MCP server and its dependencies.
"""

from typing import Any, Dict, List
from .base import BaseTool, ToolDefinition, ToolCategory


class GetHealthStatusTool(BaseTool):
    """Tool for checking health status."""
    
    @property
    def definition(self) -> ToolDefinition:
        """Return the tool definition."""
        return ToolDefinition(
            name="get_health_status",
            description="Get health status of the MCP server and dependencies",
            category=ToolCategory.MONITORING,
            schema={
                "type": "object",
                "properties": {
                    "detailed": {
                        "type": "boolean",
                        "description": "Include detailed health information (default: false)",
                    }
                },
            },
            handler="_get_health_status",
            timeout=30.0,
            requires_features=[]
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute the get health status tool.
        
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
        
        # No required arguments, all are optional

