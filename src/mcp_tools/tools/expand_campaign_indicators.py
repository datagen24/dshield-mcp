"""Expand campaign indicators tool.

This tool provides functionality to expand IOCs (Indicators of Compromise)
for a campaign using various expansion strategies.
"""

from typing import Any, Dict, List
from .base import BaseTool, ToolDefinition, ToolCategory


class ExpandCampaignIndicatorsTool(BaseTool):
    """Tool for expanding campaign indicators."""
    
    @property
    def definition(self) -> ToolDefinition:
        """Return the tool definition."""
        return ToolDefinition(
            name="expand_campaign_indicators",
            description="Expand IOCs for a campaign using various expansion strategies",
            category=ToolCategory.CAMPAIGN,
            schema={
                "type": "object",
                "properties": {
                    "campaign_id": {
                        "type": "string",
                        "description": "Campaign ID to expand indicators for",
                    },
                    "expansion_strategies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Expansion strategies to use (default: all available)",
                    },
                    "max_new_iocs": {
                        "type": "integer",
                        "description": "Maximum number of new IOCs to discover (default: 1000)",
                    },
                    "confidence_threshold": {
                        "type": "number",
                        "description": "Minimum confidence threshold for new IOCs (default: 0.5)",
                    },
                    "include_context": {
                        "type": "boolean",
                        "description": "Include context information for new IOCs (default: true)",
                    },
                },
                "required": ["campaign_id"],
            },
            handler="_expand_campaign_indicators",
            timeout=180.0,
            requires_features=["elasticsearch", "campaign_analyzer"]
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute the expand campaign indicators tool.
        
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
        
        # Validate confidence_threshold if provided
        if "confidence_threshold" in arguments:
            threshold = arguments["confidence_threshold"]
            if not isinstance(threshold, (int, float)) or not 0 <= threshold <= 1:
                raise ValueError("confidence_threshold must be a number between 0 and 1")

