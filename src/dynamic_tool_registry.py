"""Dynamic tool registry for DShield MCP server."""
from typing import List, Dict
from src.feature_manager import FeatureManager

class DynamicToolRegistry:
    """Registers tools based on feature availability."""
    def __init__(self, feature_manager: FeatureManager) -> None:
        self.feature_manager = feature_manager
        self.available_tools: List[str] = []

    def register_tools(self, all_tools: List[str]) -> List[str]:
        """Register tools based on available features."""
        self.available_tools = [tool for tool in all_tools if self.feature_manager.is_feature_available(tool)]
        return self.available_tools

    def get_tool_availability(self) -> Dict[str, bool]:
        """Get availability status for all tools."""
        return {tool: (tool in self.available_tools) for tool in self.available_tools}

    def get_disabled_tools_info(self, all_tools: List[str]) -> List[Dict[str, str]]:
        """Get information about disabled tools and reasons."""
        return [
            {"tool": tool, "reason": "Dependency unavailable"}
            for tool in all_tools if tool not in self.available_tools
        ] 