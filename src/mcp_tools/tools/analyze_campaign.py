"""Analyze campaign tool.

This tool provides functionality to analyze attack campaigns by correlating
events, expanding IOCs, and building attack timelines.
"""

from typing import Any, Dict, List
from .base import BaseTool, ToolDefinition, ToolCategory


class AnalyzeCampaignTool(BaseTool):
    """Tool for analyzing attack campaigns."""
    
    @property
    def definition(self) -> ToolDefinition:
        """Return the tool definition."""
        return ToolDefinition(
            name="analyze_campaign",
            description="Analyze attack campaigns by correlating events and expanding IOCs",
            category=ToolCategory.CAMPAIGN,
            schema={
                "type": "object",
                "properties": {
                    "seed_iocs": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Initial indicators of compromise (IPs, domains, hashes)",
                    },
                    "time_range_hours": {
                        "type": "integer",
                        "description": "Time range in hours to analyze (default: 24)",
                    },
                    "correlation_threshold": {
                        "type": "number",
                        "description": "Threshold for event correlation (default: 0.7)",
                    },
                    "max_events": {
                        "type": "integer",
                        "description": "Maximum number of events to analyze (default: 10000)",
                    },
                    "include_timeline": {
                        "type": "boolean",
                        "description": "Include attack timeline in results (default: true)",
                    },
                    "include_ioc_expansion": {
                        "type": "boolean",
                        "description": "Include IOC expansion results (default: true)",
                    },
                },
                "required": ["seed_iocs"],
            },
            handler="_analyze_campaign",
            timeout=300.0,
            requires_features=["elasticsearch", "campaign_analyzer"]
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute the analyze campaign tool.
        
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
        
        if "seed_iocs" not in arguments:
            raise ValueError("seed_iocs is required")
        
        seed_iocs = arguments["seed_iocs"]
        if not isinstance(seed_iocs, list) or not seed_iocs:
            raise ValueError("seed_iocs must be a non-empty list")
        
        if not all(isinstance(ioc, str) for ioc in seed_iocs):
            raise ValueError("All seed_iocs must be strings")

