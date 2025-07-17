"""Feature manager for DShield MCP server."""
from typing import Dict, List
from src.health_check_manager import HealthCheckManager

FEATURE_DEPENDENCIES = {
    'elasticsearch_queries': ['elasticsearch'],
    'dshield_enrichment': ['dshield_api'],
    'latex_reports': ['latex'],
    'threat_intelligence': ['threat_intel_sources'],
    'campaign_analysis': ['elasticsearch'],
    'data_dictionary': [],
}

class FeatureManager:
    """Manages feature availability based on dependency health."""
    def __init__(self, health_manager: HealthCheckManager) -> None:
        self.health_manager = health_manager
        self.features: Dict[str, bool] = {}

    async def initialize_features(self) -> None:
        health = self.health_manager.health_status
        for feature, deps in FEATURE_DEPENDENCIES.items():
            self.features[feature] = all(health.get(dep, False) for dep in deps)

    def is_feature_available(self, feature: str) -> bool:
        return self.features.get(feature, False)

    def get_available_features(self) -> List[str]:
        return [f for f, available in self.features.items() if available]

    def get_feature_dependencies(self, feature: str) -> List[str]:
        return FEATURE_DEPENDENCIES.get(feature, []) 