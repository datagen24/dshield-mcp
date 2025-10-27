"""Dynamic tool registry for DShield MCP server."""

from typing import Any

import structlog

from src.feature_manager import FeatureManager

logger = structlog.get_logger(__name__)

# Tool to feature mapping for better dependency tracking
TOOL_FEATURE_MAPPING = {
    # Elasticsearch-based tools
    "query_dshield_events": "elasticsearch_queries",
    "query_dshield_aggregations": "aggregation_queries",
    "stream_dshield_events": "streaming_queries",
    "stream_dshield_events_with_session_context": "streaming_queries",
    "query_dshield_attacks": "elasticsearch_queries",
    "query_dshield_top_attackers": "elasticsearch_queries",
    "query_dshield_geographic_data": "elasticsearch_queries",
    "query_dshield_port_data": "elasticsearch_queries",
    "get_dshield_statistics": "elasticsearch_queries",
    "diagnose_data_availability": "elasticsearch_queries",
    "query_events_by_ip": "elasticsearch_queries",
    "get_security_summary": "elasticsearch_queries",
    "test_elasticsearch_connection": "elasticsearch_queries",
    # DShield API-based tools
    "query_dshield_reputation": "dshield_enrichment",
    "enrich_ip_with_dshield": "dshield_enrichment",
    # LaTeX-based tools
    "generate_attack_report": "latex_reports",
    "generate_latex_document": "latex_reports",
    "list_latex_templates": "latex_reports",
    "get_latex_template_schema": "latex_reports",
    "validate_latex_document_data": "latex_reports",
    # Threat intelligence tools
    "enrich_ip_comprehensive": "threat_intelligence",
    "enrich_domain_comprehensive": "threat_intelligence",
    "correlate_threat_indicators": "threat_intelligence",
    "get_threat_intelligence_summary": "threat_intelligence",
    # Campaign analysis tools
    "analyze_campaign": "campaign_analysis",
    "expand_campaign_indicators": "campaign_analysis",
    "get_campaign_timeline": "campaign_analysis",
    "compare_campaigns": "campaign_analysis",
    "detect_ongoing_campaigns": "campaign_analysis",
    "search_campaigns": "campaign_analysis",
    "get_campaign_details": "campaign_analysis",
    # Statistical analysis tools
    "detect_statistical_anomalies": "statistical_analysis",
    # Data dictionary tools (no dependencies)
    "get_data_dictionary": "data_dictionary",
    # Health monitoring tools (no dependencies)
    "get_health_status": "health_monitoring",
    "get_feature_status": "health_monitoring",
    # Configuration tools (no dependencies)
    "get_configuration": "configuration_management",
    "update_configuration": "configuration_management",
}

# Tool descriptions for better user understanding
TOOL_DESCRIPTIONS = {
    "query_dshield_events": "Query DShield events from Elasticsearch SIEM with pagination",
    "query_dshield_aggregations": "Run aggregation queries on DShield data",
    "stream_dshield_events": "Stream DShield events with smart chunking",
    "stream_dshield_events_with_session_context": "Stream events with session-based grouping",
    "query_dshield_attacks": "Query attack data from DShield",
    "query_dshield_reputation": "Query IP reputation from DShield API",
    "query_dshield_top_attackers": "Get top attacker information",
    "query_dshield_geographic_data": "Query geographic attack data",
    "query_dshield_port_data": "Query port-based attack data",
    "get_dshield_statistics": "Get statistical overview of DShield data",
    "diagnose_data_availability": "Diagnose data availability issues",
    "enrich_ip_with_dshield": "Enrich IP addresses with DShield data",
    "generate_attack_report": "Generate attack reports in PDF format",
    "query_events_by_ip": "Query events for specific IP addresses",
    "get_security_summary": "Get security summary and overview",
    "test_elasticsearch_connection": "Test Elasticsearch connectivity",
    "get_data_dictionary": "Access DShield data structure definitions",
    "analyze_campaign": "Analyze attack campaigns and correlations",
    "expand_campaign_indicators": "Expand campaign indicators",
    "get_campaign_timeline": "Get timeline for specific campaigns",
    "compare_campaigns": "Compare multiple campaigns",
    "detect_ongoing_campaigns": "Detect ongoing attack campaigns",
    "search_campaigns": "Search for campaigns by criteria",
    "get_campaign_details": "Get detailed campaign information",
    "generate_latex_document": "Generate LaTeX documents",
    "list_latex_templates": "List available LaTeX templates",
    "get_latex_template_schema": "Get LaTeX template schemas",
    "validate_latex_document_data": "Validate LaTeX document data",
    "enrich_ip_comprehensive": "Comprehensive IP enrichment",
    "enrich_domain_comprehensive": "Comprehensive domain enrichment",
    "correlate_threat_indicators": "Correlate threat indicators",
    "get_threat_intelligence_summary": "Get threat intelligence summary",
    "detect_statistical_anomalies": "Detect statistical anomalies in data",
    "get_health_status": "Get system health status",
    "get_feature_status": "Get feature availability status",
    "get_configuration": "Get current configuration",
    "update_configuration": "Update configuration settings",
}


class DynamicToolRegistry:
    """Registers tools based on feature availability."""

    def __init__(self, feature_manager: FeatureManager) -> None:
        """Initialize the dynamic tool registry.

        Args:
            feature_manager: Feature manager instance

        """
        self.feature_manager = feature_manager
        self.available_tools: list[str] = []
        self.tool_details: dict[str, dict[str, Any]] = {}
        self._initialized = False

    def register_tools(self, all_tools: list[str]) -> list[str]:
        """Register tools based on available features.

        Args:
            all_tools: List of all available tool names

        Returns:
            List[str]: List of available tool names

        """
        try:
            logger.info("Registering tools based on feature availability")

            self.available_tools = []
            self.tool_details = {}

            for tool_name in all_tools:
                # Get the feature this tool depends on
                feature = TOOL_FEATURE_MAPPING.get(tool_name, "unknown")

                # Check if the feature is available
                if feature == "unknown":
                    # Tool not mapped - assume available
                    is_available = True
                    reason = "No dependency mapping found - assuming available"
                    feature_status = "unknown"
                else:
                    is_available = self.feature_manager.is_feature_available(feature)
                    if is_available:
                        reason = f"Feature '{feature}' is available"
                        feature_status = "healthy"
                    else:
                        reason = f"Feature '{feature}' is unavailable"
                        feature_status = "unhealthy"

                # Store tool details
                self.tool_details[tool_name] = {
                    "available": is_available,
                    "feature": feature,
                    "feature_status": feature_status,
                    "reason": reason,
                    "description": TOOL_DESCRIPTIONS.get(tool_name, "No description available"),
                    "dependencies": self.feature_manager.get_feature_dependencies(feature)
                    if feature != "unknown"
                    else [],
                }

                if is_available:
                    self.available_tools.append(tool_name)

            self._initialized = True

            # Log tool registration summary
            available_count = len(self.available_tools)
            total_count = len(all_tools)

            logger.info(
                "Tool registration completed",
                available_tools=available_count,
                total_tools=total_count,
                availability_percentage=round(available_count / total_count * 100, 1),
            )

            return self.available_tools

        except Exception as e:
            logger.error("Tool registration failed", error=str(e))
            # Return empty list if registration fails
            return []

    def get_tool_availability(self) -> dict[str, bool]:
        """Get availability status for all tools.

        Returns:
            Dict[str, bool]: Dictionary mapping tool names to availability status

        """
        if not self._initialized:
            return {}

        return {tool: (tool in self.available_tools) for tool in self.tool_details.keys()}

    def get_disabled_tools_info(self, all_tools: list[str]) -> list[dict[str, str]]:
        """Get information about disabled tools and reasons.

        Args:
            all_tools: List of all tool names

        Returns:
            List[Dict[str, str]]: List of disabled tool information

        """
        if not self._initialized:
            return []

        disabled_tools = []

        for tool_name in all_tools:
            if tool_name not in self.available_tools:
                tool_detail = self.tool_details.get(tool_name, {})
                disabled_tools.append(
                    {
                        "tool": tool_name,
                        "reason": tool_detail.get("reason", "Unknown reason"),
                        "feature": tool_detail.get("feature", "unknown"),
                        "description": tool_detail.get("description", "No description available"),
                    }
                )

        return disabled_tools

    def get_tool_details(self, tool_name: str) -> dict[str, Any] | None:
        """Get detailed information about a specific tool.

        Args:
            tool_name: Name of the tool

        Returns:
            Optional[Dict[str, Any]]: Tool details or None if not found

        """
        return self.tool_details.get(tool_name)

    def get_all_tool_details(self) -> dict[str, dict[str, Any]]:
        """Get details for all tools.

        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of all tool details

        """
        return self.tool_details.copy()

    def get_tool_summary(self) -> dict[str, Any]:
        """Get a summary of tool availability.

        Returns:
            Dict[str, Any]: Tool availability summary

        """
        if not self._initialized:
            return {
                "initialized": False,
                "available_count": 0,
                "total_count": 0,
                "availability_percentage": 0.0,
                "status": "not_initialized",
            }

        available_count = len(self.available_tools)
        total_count = len(self.tool_details)
        availability_percentage = round(available_count / total_count * 100, 1)

        # Determine overall status
        if availability_percentage == 100:
            status = "fully_available"
        elif availability_percentage >= 80:
            status = "mostly_available"
        elif availability_percentage >= 50:
            status = "partially_available"
        else:
            status = "mostly_unavailable"

        return {
            "initialized": True,
            "available_count": available_count,
            "total_count": total_count,
            "availability_percentage": availability_percentage,
            "status": status,
            "available_tools": self.available_tools.copy(),
            "unavailable_tools": [
                tool for tool in self.tool_details.keys() if tool not in self.available_tools
            ],
        }

    def is_tool_available(self, tool_name: str) -> bool:
        """Check if a specific tool is available.

        Args:
            tool_name: Name of the tool to check

        Returns:
            bool: True if tool is available, False otherwise

        """
        if not self._initialized:
            return False

        return tool_name in self.available_tools

    def refresh_tool_status(self) -> None:
        """Refresh tool status based on current feature availability.

        This method can be called to update tool availability
        without re-registering all tools.
        """
        if self._initialized and self.tool_details:
            # Re-evaluate tool availability based on current feature status
            for tool_name, tool_detail in self.tool_details.items():
                feature = tool_detail.get("feature")
                if feature and feature != "unknown":
                    is_available = self.feature_manager.is_feature_available(feature)
                    tool_detail["available"] = is_available
                    tool_detail["feature_status"] = "healthy" if is_available else "unhealthy"
                    tool_detail["reason"] = (
                        f"Feature '{feature}' is {'available' if is_available else 'unavailable'}"
                    )

                    if is_available and tool_name not in self.available_tools:
                        self.available_tools.append(tool_name)
                    elif not is_available and tool_name in self.available_tools:
                        self.available_tools.remove(tool_name)

    def is_initialized(self) -> bool:
        """Check if the tool registry has been initialized.

        Returns:
            bool: True if initialized, False otherwise

        """
        return self._initialized
