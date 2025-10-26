"""Stream DShield events with session context tool.

This tool provides functionality to stream DShield events with session
grouping and context for campaign analysis.
"""

from typing import Any, Dict, List
from .base import BaseTool, ToolDefinition, ToolCategory


class StreamDShieldEventsWithSessionContextTool(BaseTool):
    """Tool for streaming DShield events with session context."""
    
    @property
    def definition(self) -> ToolDefinition:
        """Return the tool definition."""
        return ToolDefinition(
            name="stream_dshield_events_with_session_context",
            description="Stream DShield events with session grouping for campaign analysis",
            category=ToolCategory.QUERY,
            schema={
                "type": "object",
                "properties": {
                    "time_range_hours": {
                        "type": "integer",
                        "description": "Time range in hours to query (default: 24)",
                    },
                    "chunk_size": {
                        "type": "integer",
                        "description": "Number of events per chunk (default: 500, max: 1000)",
                    },
                    "session_fields": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Fields to use for session grouping (default: ['source.ip', 'destination.ip'])",
                    },
                    "max_session_gap_minutes": {
                        "type": "integer",
                        "description": "Maximum gap in minutes to consider events part of same session (default: 30)",
                    },
                    "filters": {
                        "type": "object",
                        "description": "Additional query filters",
                    },
                    "stream_id": {
                        "type": "string",
                        "description": "Stream ID for resuming previous stream",
                    },
                },
            },
            handler="_stream_dshield_events_with_session_context",
            timeout=300.0,
            requires_features=["elasticsearch"]
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute the stream DShield events with session context tool.
        
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
        
        # Validate chunk_size if provided
        if "chunk_size" in arguments:
            chunk_size = arguments["chunk_size"]
            if not isinstance(chunk_size, int) or chunk_size <= 0 or chunk_size > 1000:
                raise ValueError("chunk_size must be an integer between 1 and 1000")

