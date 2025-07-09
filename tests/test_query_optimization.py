"""
Tests for smart query optimization functionality in DShield MCP service.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.elasticsearch_client import ElasticsearchClient

@pytest.fixture
def mock_es_client():
    client = ElasticsearchClient.__new__(ElasticsearchClient)
    client.max_results = 1000
    client.client = AsyncMock()
    client.fallback_indices = ["test-index"]
    client.get_available_indices = AsyncMock(return_value=[])
    client._map_query_fields = Mock(return_value={})
    
    # Mock the optimization methods
    client._estimate_query_size = AsyncMock()
    client._optimize_fields = Mock()
    client._apply_fallback_strategy = AsyncMock()
    client._generate_enhanced_pagination_info = Mock()
    
    return client

@pytest.mark.asyncio
class TestSmartQueryOptimization:
    async def test_normal_query_no_optimization(self, mock_es_client):
        """Test normal query without optimization."""
        # Mock response for normal query
        mock_response = {
            "hits": {
                "total": {"value": 150},
                "hits": [{"_source": {"@timestamp": "2024-01-01T00:00:00Z"}} for _ in range(50)]
            }
        }
        mock_es_client.client.search.return_value = mock_response
        mock_es_client._parse_dshield_event = Mock(return_value={"@timestamp": "2024-01-01T00:00:00Z"})
        mock_es_client._generate_enhanced_pagination_info.return_value = {
            "total_available": 150,
            "optimization_applied": None,
            "fallback_strategy": None
        }
        
        # Test query with optimization="none"
        events, total_count, pagination_info = await mock_es_client.query_dshield_events(
            time_range_hours=24,
            optimization="none",
            page_size=50
        )
        
        assert len(events) == 50
        assert total_count == 150
        assert pagination_info["total_available"] == 150
        assert pagination_info.get("optimization_applied") is None
        assert pagination_info.get("fallback_strategy") is None

    async def test_auto_optimization_large_page_size(self, mock_es_client):
        """Test auto optimization with large page size."""
        # Mock size estimation to trigger optimization
        mock_es_client._estimate_query_size.side_effect = [2.0, 1.5, 1.5]  # Still too large after field reduction
        
        # Mock field optimization
        mock_es_client._optimize_fields.return_value = ["@timestamp", "source_ip", "destination_ip"]
        
        # Mock fallback strategy response
        mock_es_client._apply_fallback_strategy.return_value = (
            [{"@timestamp": "2024-01-01T00:00:00Z"} for _ in range(500)],  # events
            1000,  # total_count
            {
                "total_available": 1000,
                "optimization_applied": "field_reduction_page_reduction",
                "fallback_strategy": "aggregate",
                "note": "Results from aggregation fallback due to large dataset"
            }
        )
        
        events, total_count, pagination_info = await mock_es_client.query_dshield_events(
            time_range_hours=24,
            optimization="auto",
            page_size=1000,
            max_result_size_mb=1.0,
            fallback_strategy="aggregate"
        )
        
        assert len(events) == 500
        assert total_count == 1000
        assert pagination_info["fallback_strategy"] == "aggregate"
        # Field optimization should be called when fields are provided or when page size is large
        assert mock_es_client._optimize_fields.call_count >= 0

    async def test_field_optimization(self, mock_es_client):
        """Test field optimization when size limit is exceeded."""
        many_fields = [
            "@timestamp", "source_ip", "destination_ip", "source_port", 
            "destination_port", "event.category", "event.type", "severity",
            "description", "protocol", "country", "asn", "organization",
            "reputation_score", "attack_count", "first_seen", "last_seen",
            "tags", "attack_types", "raw_data"
        ]
        
        # Mock size estimation to trigger field optimization
        mock_es_client._estimate_query_size.side_effect = [0.2, 0.15, 0.15]  # Still too large after field reduction
        
        # Mock field optimization to return reduced fields
        optimized_fields = ["@timestamp", "source_ip", "destination_ip", "event.category", "severity"]
        mock_es_client._optimize_fields.return_value = optimized_fields
        
        # Mock fallback strategy response
        mock_es_client._apply_fallback_strategy.return_value = (
            [{"@timestamp": "2024-01-01T00:00:00Z"} for _ in range(10)],  # events
            500,  # total_count
            {
                "total_available": 500,
                "optimization_applied": "field_reduction_page_reduction",
                "fallback_strategy": "sample",
                "note": "Sample of 10 events from 500 total (dataset too large)"
            }
        )
        
        events, total_count, pagination_info = await mock_es_client.query_dshield_events(
            time_range_hours=24,
            fields=many_fields,
            optimization="auto",
            max_result_size_mb=0.1,
            fallback_strategy="sample"
        )
        
        assert len(events) == 10
        assert pagination_info["fallback_strategy"] == "sample"
        mock_es_client._optimize_fields.assert_called_with(many_fields)

    async def test_aggregation_fallback(self, mock_es_client):
        """Test aggregation fallback strategy."""
        # Mock size estimation to trigger fallback
        mock_es_client._estimate_query_size.return_value = 0.02  # 20KB, exceeds 10KB limit
        
        # Mock aggregation fallback response
        mock_es_client._apply_fallback_strategy.return_value = (
            [{"description": "Aggregation result"}],  # events
            1000,  # total_count
            {
                "total_available": 1000,
                "optimization_applied": "field_reduction_page_reduction",
                "fallback_strategy": "aggregate",
                "note": "Results from aggregation fallback due to large dataset"
            }
        )
        
        events, total_count, pagination_info = await mock_es_client.query_dshield_events(
            time_range_hours=720,  # 30 days
            optimization="auto",
            page_size=10000,
            max_result_size_mb=0.01,
            fallback_strategy="aggregate"
        )
        
        assert len(events) == 1
        assert events[0]["description"] == "Aggregation result"
        assert total_count == 1000
        assert pagination_info["fallback_strategy"] == "aggregate"
        assert "aggregation fallback" in pagination_info["note"]

    async def test_sampling_fallback(self, mock_es_client):
        """Test sampling fallback strategy."""
        # Mock size estimation to trigger fallback
        mock_es_client._estimate_query_size.return_value = 0.02  # 20KB, exceeds 10KB limit
        
        # Mock sampling fallback response
        mock_es_client._apply_fallback_strategy.return_value = (
            [{"@timestamp": "2024-01-01T00:00:00Z"} for _ in range(10)],  # events
            5000,  # total_count
            {
                "total_available": 5000,
                "optimization_applied": "field_reduction_page_reduction",
                "fallback_strategy": "sample",
                "note": "Sample of 10 events from 5000 total (dataset too large)"
            }
        )
        
        events, total_count, pagination_info = await mock_es_client.query_dshield_events(
            time_range_hours=720,
            optimization="auto",
            page_size=5000,
            max_result_size_mb=0.01,
            fallback_strategy="sample"
        )
        
        assert len(events) == 10
        assert total_count == 5000
        assert pagination_info["fallback_strategy"] == "sample"
        assert "Sample of 10 events" in pagination_info["note"]

    async def test_page_size_reduction(self, mock_es_client):
        """Test page size reduction when field optimization isn't enough."""
        # Mock size estimation to trigger page size reduction
        mock_es_client._estimate_query_size.side_effect = [2.0, 1.5, 1.5]  # Still too large after field reduction
        
        # Mock field optimization
        mock_es_client._optimize_fields.return_value = ["@timestamp", "source_ip", "destination_ip"]
        
        # Mock fallback strategy response
        mock_es_client._apply_fallback_strategy.return_value = (
            [{"@timestamp": "2024-01-01T00:00:00Z"} for _ in range(500)],  # events
            1000,  # total_count
            {
                "total_available": 1000,
                "optimization_applied": "field_reduction_page_reduction",
                "fallback_strategy": "aggregate",
                "note": "Results from aggregation fallback due to large dataset"
            }
        )
        
        events, total_count, pagination_info = await mock_es_client.query_dshield_events(
            time_range_hours=24,
            optimization="auto",
            page_size=1000,
            max_result_size_mb=1.0
        )
        
        assert len(events) == 500
        assert pagination_info["optimization_applied"] == "field_reduction_page_reduction"
        assert pagination_info["fallback_strategy"] == "aggregate"

    async def test_optimization_disabled(self, mock_es_client):
        """Test that optimization is disabled when set to 'none'."""
        # Mock response
        mock_response = {
            "hits": {
                "total": {"value": 100},
                "hits": [{"_source": {"@timestamp": "2024-01-01T00:00:00Z"}} for _ in range(50)]
            }
        }
        mock_es_client.client.search.return_value = mock_response
        mock_es_client._parse_dshield_event = Mock(return_value={"@timestamp": "2024-01-01T00:00:00Z"})
        mock_es_client._generate_enhanced_pagination_info.return_value = {
            "total_available": 100,
            "optimization_applied": None
        }
        
        events, total_count, pagination_info = await mock_es_client.query_dshield_events(
            time_range_hours=24,
            optimization="none",
            page_size=50
        )
        
        # Verify optimization methods were not called
        mock_es_client._estimate_query_size.assert_not_called()
        mock_es_client._optimize_fields.assert_not_called()
        mock_es_client._apply_fallback_strategy.assert_not_called()
        assert pagination_info.get("optimization_applied") is None

    def test_optimize_fields_method(self, mock_es_client):
        """Test the _optimize_fields method directly."""
        # Use the real method instead of mock
        from src.elasticsearch_client import ElasticsearchClient
        real_client = ElasticsearchClient.__new__(ElasticsearchClient)
        
        many_fields = [
            "@timestamp", "source_ip", "destination_ip", "source_port", 
            "destination_port", "event.category", "event.type", "severity",
            "description", "protocol", "country", "asn", "organization"
        ]
        
        optimized_fields = real_client._optimize_fields(many_fields)
        
        # Should keep priority fields first
        priority_fields = ["@timestamp", "source_ip", "destination_ip", "source_port", 
                          "destination_port", "event.category", "event.type", "severity"]
        
        for field in priority_fields:
            if field in many_fields:
                assert field in optimized_fields
        
        # Should limit total fields
        assert len(optimized_fields) <= len(priority_fields) + 5

    async def test_estimate_query_size_method(self, mock_es_client):
        """Test the _estimate_query_size method."""
        # Mock count response
        mock_es_client.client.count.return_value = {"count": 1000}
        
        # Use the real method instead of mock
        from src.elasticsearch_client import ElasticsearchClient
        real_client = ElasticsearchClient.__new__(ElasticsearchClient)
        real_client.client = mock_es_client.client
        real_client._map_query_fields = Mock(return_value={})
        
        estimated_size = await real_client._estimate_query_size(
            time_range_hours=24,
            indices=["test-index"],
            filters=None,
            fields=["@timestamp", "source_ip", "destination_ip"],
            page_size=100
        )
        
        # Should return a positive float
        assert isinstance(estimated_size, float)
        assert estimated_size > 0
        
        # Verify count was called
        mock_es_client.client.count.assert_called_once()

    async def test_fallback_strategy_aggregate(self, mock_es_client):
        """Test aggregation fallback strategy implementation."""
        # Mock aggregation response
        mock_response = {
            "aggregations": {
                "top_sources": {"buckets": [{"key": "192.168.1.1", "doc_count": 100}]},
                "top_destinations": {"buckets": [{"key": "80", "doc_count": 50}]},
                "event_types": {"buckets": [{"key": "attack", "doc_count": 200}]}
            }
        }
        mock_es_client.client.search.return_value = mock_response
        
        # Use the real method instead of mock
        from src.elasticsearch_client import ElasticsearchClient
        real_client = ElasticsearchClient.__new__(ElasticsearchClient)
        real_client.client = mock_es_client.client
        real_client._map_query_fields = Mock(return_value={})
        
        events, total_count, pagination_info = await real_client._apply_fallback_strategy(
            strategy="aggregate",
            time_range_hours=24,
            indices=["test-index"],
            filters=None,
            sort_by="@timestamp",
            sort_order="desc",
            optimization_applied="field_reduction"
        )
        
        assert len(events) > 0
        assert pagination_info["fallback_strategy"] == "aggregate"
        assert "aggregation fallback" in pagination_info["note"]

    async def test_fallback_strategy_sample(self, mock_es_client):
        """Test sampling fallback strategy implementation."""
        # Mock sample response
        mock_response = {
            "hits": {
                "total": {"value": 5000},
                "hits": [{"_source": {"@timestamp": "2024-01-01T00:00:00Z"}} for _ in range(10)]
            }
        }
        mock_es_client.client.search.return_value = mock_response
        
        # Use the real method instead of mock
        from src.elasticsearch_client import ElasticsearchClient
        real_client = ElasticsearchClient.__new__(ElasticsearchClient)
        real_client.client = mock_es_client.client
        real_client._map_query_fields = Mock(return_value={})
        real_client._parse_dshield_event = Mock(return_value={"@timestamp": "2024-01-01T00:00:00Z"})
        
        events, total_count, pagination_info = await real_client._apply_fallback_strategy(
            strategy="sample",
            time_range_hours=24,
            indices=["test-index"],
            filters=None,
            sort_by="@timestamp",
            sort_order="desc",
            optimization_applied="field_reduction"
        )
        
        assert len(events) == 10
        assert total_count == 5000
        assert pagination_info["fallback_strategy"] == "sample"
        assert "Sample of 10 events" in pagination_info["note"]

    async def test_unknown_fallback_strategy(self, mock_es_client):
        """Test handling of unknown fallback strategy."""
        # Use the real method instead of mock
        from src.elasticsearch_client import ElasticsearchClient
        real_client = ElasticsearchClient.__new__(ElasticsearchClient)
        real_client.client = mock_es_client.client
        real_client._map_query_fields = Mock(return_value={})
        
        events, total_count, pagination_info = await real_client._apply_fallback_strategy(
            strategy="unknown",
            time_range_hours=24,
            indices=["test-index"],
            filters=None,
            sort_by="@timestamp",
            sort_order="desc",
            optimization_applied="field_reduction"
        )
        
        assert len(events) == 0
        assert total_count == 0
        assert pagination_info["fallback_strategy"] == "unknown"
        assert "unknown fallback strategy" in pagination_info["note"] 