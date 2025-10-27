"""Detect statistical anomalies tool.

This tool provides functionality to detect statistical anomalies
in DShield event data using various methods.
"""

from typing import Any, Dict, List
from .base import BaseTool, ToolDefinition, ToolCategory


class DetectStatisticalAnomaliesTool(BaseTool):
    """Tool for detecting statistical anomalies."""
    
    @property
    def definition(self) -> ToolDefinition:
        """Return the tool definition."""
        return ToolDefinition(
            name="detect_statistical_anomalies",
            description="Detect statistical anomalies in DShield event data",
            category=ToolCategory.QUERY,
            schema={
                "type": "object",
                "properties": {
                    "time_range_hours": {
                        "type": "integer",
                        "description": "Time window in hours to analyze (default: 24)",
                    },
                    "anomaly_methods": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Methods: zscore, iqr, isolation_forest, time_series",
                    },
                    "sensitivity": {
                        "type": "number",
                        "description": "Sensitivity multiplier (e.g., z or IQR whisker)",
                    },
                    "dimensions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Legacy dimension names (ignored if schema provided)",
                    },
                    "return_summary_only": {"type": "boolean"},
                    "max_anomalies": {"type": "integer"},
                    "dimension_schema": {
                        "type": "object",
                        "description": "Schema: {name: {field, agg, size, interval, percents}}",
                    },
                    "enable_iqr": {"type": "boolean"},
                    "enable_percentiles": {"type": "boolean"},
                    "time_series_mode": {
                        "type": "string",
                        "enum": ["fast", "robust"],
                        "description": "fast (mean dev) or robust (MAD + rolling z)",
                    },
                    "seasonality_hour_of_day": {"type": "boolean"},
                    "raw_sample_mode": {"type": "boolean"},
                    "raw_sample_size": {"type": "integer"},
                    "min_iforest_samples": {"type": "integer"},
                    "scale_iforest_features": {"type": "boolean"},
                },
            },
            handler="_detect_statistical_anomalies",
            timeout=300.0,
            requires_features=["elasticsearch", "statistical_analysis"]
        )
    
    async def execute(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Execute the detect statistical anomalies tool.
        
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
        
        # Validate anomaly_methods if provided
        if "anomaly_methods" in arguments:
            methods = arguments["anomaly_methods"]
            if not isinstance(methods, list):
                raise ValueError("anomaly_methods must be a list")
            
            valid_methods = ["zscore", "iqr", "isolation_forest", "time_series"]
            for method in methods:
                if method not in valid_methods:
                    raise ValueError(f"Invalid anomaly method: {method}. Valid methods: {valid_methods}")

