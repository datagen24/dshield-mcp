"""Feature manager for DShield MCP server."""
import asyncio
from typing import Any, Dict, List, Optional

import structlog

from src.health_check_manager import HealthCheckManager

logger = structlog.get_logger(__name__)

# Feature dependency mapping
FEATURE_DEPENDENCIES = {
    "elasticsearch_queries": ["elasticsearch"],
    "dshield_enrichment": ["dshield_api"],
    "latex_reports": ["latex"],
    "threat_intelligence": ["threat_intel_sources"],
    "campaign_analysis": ["elasticsearch"],
    "data_dictionary": [],  # No external dependencies
    "statistical_analysis": ["elasticsearch"],
    "streaming_queries": ["elasticsearch"],
    "aggregation_queries": ["elasticsearch"],
    "report_generation": ["elasticsearch", "latex"],
    "threat_enrichment": ["dshield_api", "threat_intel_sources"],
    "campaign_correlation": ["elasticsearch", "thshield_api"],
    "data_export": ["elasticsearch"],
    "health_monitoring": [],  # No external dependencies
    "configuration_management": [],  # No external dependencies
}

# Feature descriptions for better user understanding
FEATURE_DESCRIPTIONS = {
    "elasticsearch_queries": "Query DShield events and data from Elasticsearch SIEM",
    "dshield_enrichment": "Enrich data with DShield threat intelligence API",
    "latex_reports": "Generate PDF reports using LaTeX templates",
    "threat_intelligence": "Access threat intelligence from multiple sources",
    "campaign_analysis": "Analyze attack campaigns and correlations",
    "data_dictionary": "Access DShield data structure and field definitions",
    "statistical_analysis": "Perform statistical analysis on security data",
    "streaming_queries": "Stream large datasets with session context",
    "aggregation_queries": "Run aggregation and summary queries",
    "report_generation": "Generate comprehensive security reports",
    "threat_enrichment": "Enrich events with threat intelligence data",
    "campaign_correlation": "Correlate events into attack campaigns",
    "data_export": "Export data in various formats",
    "health_monitoring": "Monitor system and dependency health",
    "configuration_management": "Manage server configuration and settings",
}

# Feature criticality levels
FEATURE_CRITICALITY = {
    "elasticsearch_queries": "critical",      # Core functionality
    "dshield_enrichment": "important",       # Enhanced functionality
    "latex_reports": "optional",             # Nice to have
    "threat_intelligence": "important",      # Enhanced functionality
    "campaign_analysis": "important",        # Enhanced functionality
    "data_dictionary": "optional",           # Documentation
    "statistical_analysis": "important",     # Enhanced functionality
    "streaming_queries": "important",        # Performance feature
    "aggregation_queries": "important",      # Performance feature
    "report_generation": "optional",         # Nice to have
    "threat_enrichment": "important",        # Enhanced functionality
    "campaign_correlation": "important",     # Enhanced functionality
    "data_export": "optional",               # Nice to have
    "health_monitoring": "optional",         # Operational
    "configuration_management": "optional",   # Operational
}


class FeatureManager:
    """Manages feature availability based on dependency health."""

    def __init__(self, health_manager: HealthCheckManager) -> None:
        """Initialize the feature manager.
        
        Args:
            health_manager: Health check manager instance

        """
        self.health_manager = health_manager
        self.features: Dict[str, bool] = {}
        self.feature_details: Dict[str, Dict[str, Any]] = {}
        self._initialized = False

    async def initialize_features(self) -> None:
        """Initialize feature availability based on health checks.
        
        This method runs health checks and determines which features
        are available based on dependency health.
        """
        try:
            logger.info("Initializing feature availability")

            # Get current health status
            health_status = self.health_manager.health_status

            # Initialize each feature based on dependencies
            for feature, dependencies in FEATURE_DEPENDENCIES.items():
                if not dependencies:
                    # No dependencies - always available
                    self.features[feature] = True
                    self.feature_details[feature] = {
                        "available": True,
                        "reason": "No external dependencies",
                        "criticality": FEATURE_CRITICALITY.get(feature, "unknown"),
                        "description": FEATURE_DESCRIPTIONS.get(feature, "Unknown feature"),
                    }
                else:
                    # Check if all dependencies are healthy
                    dependency_status = {}
                    all_healthy = True

                    for dep in dependencies:
                        dep_healthy = health_status.get(dep, False)
                        dependency_status[dep] = dep_healthy
                        if not dep_healthy:
                            all_healthy = False

                    self.features[feature] = all_healthy

                    if all_healthy:
                        self.feature_details[feature] = {
                            "available": True,
                            "reason": "All dependencies healthy",
                            "dependencies": dependency_status,
                            "criticality": FEATURE_CRITICALITY.get(feature, "unknown"),
                            "description": FEATURE_DESCRIPTIONS.get(feature, "Unknown feature"),
                        }
                    else:
                        unhealthy_deps = [dep for dep, healthy in dependency_status.items() if not healthy]
                        self.feature_details[feature] = {
                            "available": False,
                            "reason": f"Unhealthy dependencies: {', '.join(unhealthy_deps)}",
                            "dependencies": dependency_status,
                            "criticality": FEATURE_CRITICALITY.get(feature, "unknown"),
                            "description": FEATURE_DESCRIPTIONS.get(feature, "Unknown feature"),
                            "unhealthy_dependencies": unhealthy_deps,
                        }

            self._initialized = True

            # Log feature availability summary
            available_count = sum(self.features.values())
            total_count = len(self.features)

            logger.info("Feature initialization completed",
                       available_features=available_count,
                       total_features=total_count,
                       availability_percentage=round(available_count/total_count*100, 1))

            # Log critical features that are unavailable
            critical_unavailable = [
                feature for feature, available in self.features.items()
                if not available and FEATURE_CRITICALITY.get(feature) == "critical"
            ]

            if critical_unavailable:
                logger.warning("Critical features unavailable",
                             critical_unavailable=critical_unavailable)

        except Exception as e:
            logger.error("Feature initialization failed", error=str(e))
            # Set all features as unavailable if initialization fails
            for feature in FEATURE_DEPENDENCIES:
                self.features[feature] = False
                self.feature_details[feature] = {
                    "available": False,
                    "reason": f"Initialization failed: {e!s}",
                    "criticality": FEATURE_CRITICALITY.get(feature, "unknown"),
                    "description": FEATURE_DESCRIPTIONS.get(feature, "Unknown feature"),
                }

    def is_feature_available(self, feature: str) -> bool:
        """Check if a feature is available.
        
        Args:
            feature: Name of the feature to check
            
        Returns:
            bool: True if feature is available, False otherwise

        """
        if not self._initialized:
            logger.warning("Feature manager not initialized, returning False", feature=feature)
            return False

        return self.features.get(feature, False)

    def get_available_features(self) -> List[str]:
        """Get list of available features.
        
        Returns:
            List[str]: List of available feature names

        """
        if not self._initialized:
            return []

        return [feature for feature, available in self.features.items() if available]

    def get_unavailable_features(self) -> List[str]:
        """Get list of unavailable features.
        
        Returns:
            List[str]: List of unavailable feature names

        """
        if not self._initialized:
            return list(FEATURE_DEPENDENCIES.keys())

        return [feature for feature, available in self.features.items() if not available]

    def get_feature_dependencies(self, feature: str) -> List[str]:
        """Get dependencies required for a feature.
        
        Args:
            feature: Name of the feature
            
        Returns:
            List[str]: List of dependency names

        """
        return FEATURE_DEPENDENCIES.get(feature, [])

    def get_feature_details(self, feature: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a feature.
        
        Args:
            feature: Name of the feature
            
        Returns:
            Optional[Dict[str, Any]]: Feature details or None if not found

        """
        return self.feature_details.get(feature)

    def get_all_feature_details(self) -> Dict[str, Dict[str, Any]]:
        """Get details for all features.
        
        Returns:
            Dict[str, Dict[str, Any]]: Dictionary of all feature details

        """
        return self.feature_details.copy()

    def get_feature_summary(self) -> Dict[str, Any]:
        """Get a summary of feature availability.
        
        Returns:
            Dict[str, Any]: Feature availability summary

        """
        if not self._initialized:
            return {
                "initialized": False,
                "available_count": 0,
                "total_count": len(FEATURE_DEPENDENCIES),
                "availability_percentage": 0.0,
                "critical_features_available": False,
                "status": "not_initialized",
            }

        available_count = sum(self.features.values())
        total_count = len(self.features)
        availability_percentage = round(available_count/total_count*100, 1)

        # Check if critical features are available
        critical_features = [
            feature for feature, criticality in FEATURE_CRITICALITY.items()
            if criticality == "critical"
        ]

        critical_available = all(
            self.features.get(feature, False) for feature in critical_features
        )

        # Determine overall status
        if availability_percentage == 100:
            status = "fully_available"
        elif availability_percentage >= 80:
            status = "mostly_available"
        elif availability_percentage >= 50:
            status = "partially_available"
        elif critical_available:
            status = "critical_only"
        else:
            status = "unavailable"

        return {
            "initialized": True,
            "available_count": available_count,
            "total_count": total_count,
            "availability_percentage": availability_percentage,
            "critical_features_available": critical_available,
            "status": status,
            "available_features": self.get_available_features(),
            "unavailable_features": self.get_unavailable_features(),
            "critical_features": critical_features,
        }

    def refresh_feature_status(self) -> None:
        """Refresh feature status based on current health checks.
        
        This method can be called to update feature availability
        without re-initializing the entire manager.
        """
        if self._initialized:
            # Re-run health checks and update features
            asyncio.create_task(self.initialize_features())

    def is_initialized(self) -> bool:
        """Check if the feature manager has been initialized.
        
        Returns:
            bool: True if initialized, False otherwise

        """
        return self._initialized
