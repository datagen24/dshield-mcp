import pytest

from src.dynamic_tool_registry import DynamicToolRegistry
from src.feature_manager import FeatureManager
from src.health_check_manager import HealthCheckManager


@pytest.mark.asyncio
async def test_health_check_manager():
    manager = HealthCheckManager()
    result = await manager.run_all_checks()
    assert isinstance(result, dict)
    assert "status" in result
    assert "details" in result
    assert "summary" in result

    # Check that the status contains boolean values
    health_status = result["status"]
    assert isinstance(health_status, dict)
    assert all(isinstance(v, bool) for v in health_status.values())


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
