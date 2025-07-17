import pytest
from src.health_check_manager import HealthCheckManager
from src.feature_manager import FeatureManager
from src.dynamic_tool_registry import DynamicToolRegistry

@pytest.mark.asyncio
async def test_health_check_manager():
    manager = HealthCheckManager()
    status = await manager.run_all_checks()
    assert isinstance(status, dict)
    assert all(isinstance(v, bool) for v in status.values())

@pytest.mark.asyncio
async def test_feature_manager():
    health_manager = HealthCheckManager()
    await health_manager.run_all_checks()
    feature_manager = FeatureManager(health_manager)
    await feature_manager.initialize_features()
    features = feature_manager.get_available_features()
    assert isinstance(features, list)

@pytest.mark.asyncio
async def test_dynamic_tool_registry():
    health_manager = HealthCheckManager()
    await health_manager.run_all_checks()
    feature_manager = FeatureManager(health_manager)
    await feature_manager.initialize_features()
    registry = DynamicToolRegistry(feature_manager)
    all_tools = [
        'elasticsearch_queries',
        'dshield_enrichment',
        'latex_reports',
        'threat_intelligence',
        'campaign_analysis',
        'data_dictionary',
    ]
    available = registry.register_tools(all_tools)
    assert isinstance(available, list)
    assert set(available).issubset(set(all_tools)) 