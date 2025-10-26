"""Generate attack report tool.

This tool provides functionality to generate PDF attack reports
using LaTeX templates.
"""

from typing import Any, Dict, List
from .base import BaseTool, ToolDefinition, ToolCategory


class GenerateAttackReportTool(BaseTool):
    """Tool for generating PDF attack reports."""
    
    @property
    def definition(self) -> ToolDefinition:
        """Return the tool definition."""
        return ToolDefinition(
            name="generate_attack_report",
            description="Generate PDF attack reports using LaTeX templates",
            category=ToolCategory.REPORT,
            schema={
                "type": "object",
                "properties": {
                    "campaign_id": {
                        "type": "string",
                        "description": "Campaign ID to generate report for",
                    },
                    "template_name": {
                        "type": "string",
                        "description": "LaTeX template to use (default: 'Attack_Report')",
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Output path for the generated PDF",
                    },
                    "include_timeline": {
                        "type": "boolean",
                        "description": "Include attack timeline in report (default: true)",
                    },
                    "include_iocs": {
                        "type": "boolean",
                        "description": "Include IOC details in report (default: true)",
                    },
                    "include_recommendations": {
                        "type": "boolean",
                        "description": "Include security recommendations (default: true)",
                    },
                },
                "required": ["campaign_id"],
            },
            handler="_generate_attack_report",
            timeout=180.0,
            requires_features=["latex", "campaign_analyzer"]
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute the generate attack report tool.
        
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

