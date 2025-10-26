"""Query DShield events tool.

This tool provides functionality to query DShield events from Elasticsearch
with various filtering, pagination, and optimization options.
"""

from typing import Any, Dict, List
from .base import BaseTool, ToolDefinition, ToolCategory


class QueryDShieldEventsTool(BaseTool):
    """Tool for querying DShield events from Elasticsearch."""
    
    @property
    def definition(self) -> ToolDefinition:
        """Return the tool definition."""
        return ToolDefinition(
            name="query_dshield_events",
            description="Query DShield events from Elasticsearch with filtering and pagination",
            category=ToolCategory.QUERY,
            schema={
                "type": "object",
                "properties": {
                    "time_range_hours": {
                        "type": "integer",
                        "description": "Time range in hours to query (default: 24)",
                    },
                    "time_range": {
                        "type": "object",
                        "description": "Exact time range with start and end timestamps",
                        "properties": {
                            "start": {"type": "string", "format": "date-time"},
                            "end": {"type": "string", "format": "date-time"},
                        },
                    },
                    "relative_time": {
                        "type": "string",
                        "description": "Relative time range (e.g., 'last_6_hours', "
                        "'last_24_hours', 'last_7_days')",
                    },
                    "time_window": {
                        "type": "object",
                        "description": "Time window around a specific timestamp",
                        "properties": {
                            "around": {"type": "string", "format": "date-time"},
                            "window_minutes": {"type": "integer"},
                        },
                    },
                    "indices": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "DShield Elasticsearch indices to query",
                    },
                    "filters": {
                        "type": "object",
                        "description": "Additional query filters",
                    },
                    "fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Specific fields to return (reduces payload size)",
                    },
                    "page": {
                        "type": "integer",
                        "description": "Page number for pagination (default: 1)",
                    },
                    "page_size": {
                        "type": "integer",
                        "description": "Number of results per page (default: 100, max: 1000)",
                    },
                    "sort_by": {
                        "type": "string",
                        "description": "Field to sort by (default: '@timestamp')",
                    },
                    "sort_order": {
                        "type": "string",
                        "enum": ["asc", "desc"],
                        "description": "Sort order (default: 'desc')",
                    },
                    "cursor": {
                        "type": "string",
                        "description": "Cursor token for cursor-based pagination (better for large datasets)",
                    },
                    "optimization": {
                        "type": "string",
                        "enum": ["auto", "none"],
                        "description": "Smart query optimization mode (default: 'auto')",
                    },
                    "fallback_strategy": {
                        "type": "string",
                        "enum": ["aggregate", "sample", "error"],
                        "description": "Fallback strategy when optimization fails (default: 'aggregate')",
                    },
                    "max_result_size_mb": {
                        "type": "number",
                        "description": "Maximum result size in MB before optimization (default: 10.0)",
                    },
                    "query_timeout_seconds": {
                        "type": "integer",
                        "description": "Query timeout in seconds (default: 30)",
                    },
                    "include_summary": {
                        "type": "boolean",
                        "description": "Include summary statistics with results (default: true)",
                    },
                },
            },
            handler="_query_dshield_events",
            timeout=120.0,
            requires_features=["elasticsearch"]
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute the query DShield events tool.
        
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
        # The actual implementation will be in the server's _query_dshield_events method
        raise NotImplementedError("Tool execution is handled by the MCP server")
    
    def validate_arguments(self, arguments: Dict[str, Any]) -> None:
        """Validate tool arguments.
        
        Args:
            arguments: Arguments to validate
            
        Raises:
            ValueError: If arguments are invalid
        """
        # Basic validation
        if not isinstance(arguments, dict):
            raise ValueError("Arguments must be a dictionary")
        
        # Validate time range if provided
        if "time_range" in arguments:
            time_range = arguments["time_range"]
            if not isinstance(time_range, dict):
                raise ValueError("time_range must be a dictionary")
            
            if "start" in time_range and "end" in time_range:
                # Additional validation could be added here
                pass

