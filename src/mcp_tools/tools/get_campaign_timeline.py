"""Get campaign timeline tool.

This tool provides functionality to retrieve the attack timeline
for a specific campaign.
"""

from typing import Any, Dict, List
from .base import BaseTool, ToolDefinition, ToolCategory


class GetCampaignTimelineTool(BaseTool):
    """Tool for getting campaign timeline."""
    
    @property
    def definition(self) -> ToolDefinition:
        """Return the tool definition."""
        return ToolDefinition(
            name="get_campaign_timeline",
            description="Get attack timeline for a specific campaign",
            category=ToolCategory.CAMPAIGN,
            schema={
                "type": "object",
                "properties": {
                    "campaign_id": {
                        "type": "string",
                        "description": "Campaign ID to get timeline for",
                    },
                    "granularity": {
                        "type": "string",
                        "enum": ["hourly", "daily", "weekly"],
                        "description": "Timeline granularity (default: 'daily')",
                    },
                    "include_events": {
                        "type": "boolean",
                        "description": "Include individual events in timeline (default: true)",
                    },
                    "max_events_per_bucket": {
                        "type": "integer",
                        "description": "Maximum events per time bucket (default: 100)",
                    },
                },
                "required": ["campaign_id"],
            },
            handler="_get_campaign_timeline",
            timeout=120.0,
            requires_features=["elasticsearch", "campaign_analyzer"]
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute the get campaign timeline tool.
        
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
        
        if "campaign_id" not in arguments:
            raise ValueError("campaign_id is required")
        
        campaign_id = arguments["campaign_id"]
        if not isinstance(campaign_id, str) or not campaign_id.strip():
            raise ValueError("campaign_id must be a non-empty string")
        
        # Validate granularity if provided
        if "granularity" in arguments:
            granularity = arguments["granularity"]
            if granularity not in ["hourly", "daily", "weekly"]:
                raise ValueError("granularity must be one of: hourly, daily, weekly")

