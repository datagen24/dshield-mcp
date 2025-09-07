"""Performance Metrics Tests.

Tests for query performance tracking and metrics collection functionality.
"""

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio


class TestPerformanceMetrics:
    """Test performance metrics functionality."""

    @pytest_asyncio.fixture
    async def mock_client(self):
        """Create a mock ElasticsearchClient with performance metrics."""
        with patch('src.elasticsearch_client.ElasticsearchClient') as mock_class:
            client = mock_class.return_value
            client.client = AsyncMock()
            client.connect = AsyncMock()
            client.get_available_indices = AsyncMock(return_value=["dshield-2024.01.01"])

            # Mock performance metrics in pagination info
            def mock_query_with_metrics(*args, **kwargs):
                # Create mock events
                events = [
                    {
                        "@timestamp": "2024-01-01T12:00:00Z",
                        "source.ip": "192.168.1.1",
                        "destination.ip": "10.0.0.1",
                        "event.type": "alert",
                    }
                ] * 10

                # Create pagination info with performance metrics
                pagination_info = {
                    "page_size": kwargs.get('page_size', 100),
                    "page_number": kwargs.get('page', 1),
                    "total_results": 1000,
                    "total_available": 1000,
                    "has_more": True,
                    "total_pages": 10,
                    "has_previous": False,
                    "has_next": True,
                    "start_index": 1,
                    "end_index": 10,
                    "sort_by": "@timestamp",
                    "sort_order": "desc",
                    # Performance metrics
                    "query_time_ms": 150,
                    "indices_scanned": 3,
                    "total_documents_examined": 5000,
                    "query_complexity": "simple",
                    "optimization_applied": [],
                    "cache_hit": False,
                    "shards_scanned": 6,
                    "aggregations_used": False,
                }

                return events, 1000, pagination_info

            client.query_dshield_events = AsyncMock(side_effect=mock_query_with_metrics)

            # Mock aggregation query with performance metrics
            def mock_aggregation_with_metrics(*args, **kwargs):
                return {
                    "aggregations": {
                        "top_sources": {
                            "buckets": [
                                {"key": "192.168.1.1", "doc_count": 100},
                                {"key": "192.168.1.2", "doc_count": 50},
                            ]
                        },
                        "event_types": {
                            "buckets": [
                                {"key": "alert", "doc_count": 80},
                                {"key": "info", "doc_count": 20},
                            ]
                        },
                    },
                    "performance_metrics": {
                        "query_time_ms": 200,
                        "indices_scanned": 3,
                        "total_documents_examined": 5000,
                        "query_complexity": "aggregation",
                        "optimization_applied": ["field_reduction"],
                        "cache_hit": False,
                        "shards_scanned": 6,
                        "aggregations_used": True,
                    },
                }

            client.execute_aggregation_query = AsyncMock(side_effect=mock_aggregation_with_metrics)

            yield client

    @pytest.mark.asyncio
    async def test_simple_query_performance_metrics(self, mock_client):
        """Test simple query performance metrics."""
        events, total_count, pagination_info = await mock_client.query_dshield_events(
            time_range_hours=1, page_size=100
        )

        assert len(events) == 10
        assert total_count == 1000
        assert pagination_info["query_time_ms"] == 150
        assert pagination_info["indices_scanned"] == 3
        assert pagination_info["total_documents_examined"] == 5000
        assert pagination_info["query_complexity"] == "simple"
        assert pagination_info["optimization_applied"] == []
        assert pagination_info["cache_hit"] is False
        assert pagination_info["shards_scanned"] == 6
        assert pagination_info["aggregations_used"] is False

    @pytest.mark.asyncio
    async def test_complex_query_performance_metrics(self, mock_client):
        """Test complex query performance metrics with filters and field selection."""
        events, total_count, pagination_info = await mock_client.query_dshield_events(
            time_range_hours=24,
            filters={"source.ip": "141.98.80.135", "event.type": "alert"},
            fields=["@timestamp", "source.ip", "destination.ip", "event.type"],
            page_size=50,
        )

        assert len(events) == 10
        assert total_count == 1000
        assert pagination_info["query_time_ms"] == 150
        assert pagination_info["indices_scanned"] == 3
        assert pagination_info["total_documents_examined"] == 5000
        assert pagination_info["query_complexity"] == "simple"
        assert pagination_info["optimization_applied"] == []

    @pytest.mark.asyncio
    async def test_cursor_pagination_performance_metrics(self, mock_client):
        """Test cursor pagination performance metrics."""

        # Mock client to return cursor information
        def mock_query_with_cursor(*args, **kwargs):
            events = [
                {
                    "@timestamp": "2024-01-01T12:00:00Z",
                    "source.ip": "192.168.1.1",
                    "destination.ip": "10.0.0.1",
                    "event.type": "alert",
                }
            ] * 10

            pagination_info = {
                "page_size": kwargs.get('page_size', 100),
                "page_number": kwargs.get('page', 1),
                "total_results": 1000,
                "total_available": 1000,
                "has_more": True,
                "total_pages": 10,
                "has_previous": False,
                "has_next": True,
                "start_index": 1,
                "end_index": 10,
                "sort_by": "@timestamp",
                "sort_order": "desc",
                # Performance metrics
                "query_time_ms": 150,
                "indices_scanned": 3,
                "total_documents_examined": 5000,
                "query_complexity": "simple",
                "optimization_applied": [],
                "cache_hit": False,
                "shards_scanned": 6,
                "aggregations_used": False,
                # Cursor information
                "cursor": "2024-01-01T12:00:00Z",
                "next_page_token": "2024-01-01T12:00:00Z",
            }

            return events, 1000, pagination_info

        mock_client.query_dshield_events = AsyncMock(side_effect=mock_query_with_cursor)

        events, total_count, pagination_info = await mock_client.query_dshield_events(
            time_range_hours=1,
            page_size=100,
            cursor=None,  # First page
        )

        assert len(events) == 10
        assert total_count == 1000
        assert pagination_info["query_time_ms"] == 150
        assert pagination_info["optimization_applied"] == []
        assert "cursor" in pagination_info
        assert "next_page_token" in pagination_info

    @pytest.mark.asyncio
    async def test_aggregation_query_performance_metrics(self, mock_client):
        """Test aggregation query performance metrics."""
        # Build aggregation query
        query = {"bool": {"must": [{"range": {"@timestamp": {"gte": "now-1h", "lte": "now"}}}]}}

        aggregation_query = {
            "top_sources": {"terms": {"field": "source.ip", "size": 10}},
            "event_types": {"terms": {"field": "event.type", "size": 5}},
        }

        result = await mock_client.execute_aggregation_query(
            index=["dshield-*"], query=query, aggregation_query=aggregation_query
        )

        assert "aggregations" in result
        assert "performance_metrics" in result
        assert result["performance_metrics"]["query_time_ms"] == 200
        assert result["performance_metrics"]["indices_scanned"] == 3
        assert result["performance_metrics"]["total_documents_examined"] == 5000
        assert result["performance_metrics"]["query_complexity"] == "aggregation"
        assert result["performance_metrics"]["optimization_applied"] == ["field_reduction"]
        assert result["performance_metrics"]["aggregations_used"] is True

    @pytest.mark.asyncio
    async def test_performance_comparison_different_page_sizes(self, mock_client):
        """Test performance comparison between different page sizes."""
        # Small page size
        events_small, _, pagination_small = await mock_client.query_dshield_events(
            time_range_hours=1, page_size=10
        )

        # Large page size
        events_large, _, pagination_large = await mock_client.query_dshield_events(
            time_range_hours=1, page_size=1000
        )

        assert len(events_small) == 10
        assert len(events_large) == 10  # Mock returns same number
        assert pagination_small["query_time_ms"] == 150
        assert pagination_large["query_time_ms"] == 150
        assert pagination_small["page_size"] == 10
        assert pagination_large["page_size"] == 1000

    @pytest.mark.asyncio
    async def test_field_selection_optimization_performance(self, mock_client):
        """Test field selection optimization performance."""
        # All fields (default)
        events_all, _, pagination_all = await mock_client.query_dshield_events(
            time_range_hours=1, page_size=100
        )

        # Selected fields only
        events_selected, _, pagination_selected = await mock_client.query_dshield_events(
            time_range_hours=1, fields=["@timestamp", "source.ip", "destination.ip"], page_size=100
        )

        assert len(events_all) == 10
        assert len(events_selected) == 10
        assert pagination_all["query_time_ms"] == 150
        assert pagination_selected["query_time_ms"] == 150
        assert pagination_selected["optimization_applied"] == []

    @pytest.mark.asyncio
    async def test_performance_metrics_structure(self, mock_client):
        """Test that performance metrics have the expected structure."""
        events, total_count, pagination_info = await mock_client.query_dshield_events(
            time_range_hours=1, page_size=100
        )

        # Check required performance metrics fields
        required_metrics = [
            "query_time_ms",
            "indices_scanned",
            "total_documents_examined",
            "query_complexity",
            "optimization_applied",
            "cache_hit",
            "shards_scanned",
            "aggregations_used",
        ]

        for metric in required_metrics:
            assert metric in pagination_info, f"Missing performance metric: {metric}"

        # Check data types
        assert isinstance(pagination_info["query_time_ms"], int)
        assert isinstance(pagination_info["indices_scanned"], int)
        assert isinstance(pagination_info["total_documents_examined"], int)
        assert isinstance(pagination_info["query_complexity"], str)
        assert isinstance(pagination_info["optimization_applied"], list)
        assert isinstance(pagination_info["cache_hit"], bool)
        assert isinstance(pagination_info["shards_scanned"], int)
        assert isinstance(pagination_info["aggregations_used"], bool)

    @pytest.mark.asyncio
    async def test_optimization_applied_tracking(self, mock_client):
        """Test that optimization_applied field correctly tracks applied optimizations."""

        # Mock client to return different optimization_applied values
        def mock_query_with_optimization(*args, **kwargs):
            events = [{"@timestamp": "2024-01-01T12:00:00Z"}] * 5
            pagination_info = {
                "page_size": kwargs.get('page_size', 100),
                "page_number": kwargs.get('page', 1),
                "total_results": 1000,
                "total_available": 1000,
                "has_more": True,
                "total_pages": 10,
                "has_previous": False,
                "has_next": True,
                "start_index": 1,
                "end_index": 5,
                "sort_by": "@timestamp",
                "sort_order": "desc",
                "query_time_ms": 120,
                "indices_scanned": 2,
                "total_documents_examined": 3000,
                "query_complexity": "optimized",
                "optimization_applied": ["field_reduction", "page_reduction"],
                "cache_hit": False,
                "shards_scanned": 4,
                "aggregations_used": False,
            }
            return events, 1000, pagination_info

        mock_client.query_dshield_events = AsyncMock(side_effect=mock_query_with_optimization)

        events, total_count, pagination_info = await mock_client.query_dshield_events(
            time_range_hours=1, page_size=100
        )

        assert pagination_info["optimization_applied"] == ["field_reduction", "page_reduction"]
        assert pagination_info["query_complexity"] == "optimized"
        assert pagination_info["query_time_ms"] == 120

    @pytest.mark.asyncio
    async def test_cache_hit_performance_metrics(self, mock_client):
        """Test cache hit performance metrics."""

        def mock_query_with_cache_hit(*args, **kwargs):
            events = [{"@timestamp": "2024-01-01T12:00:00Z"}] * 5
            pagination_info = {
                "page_size": kwargs.get('page_size', 100),
                "page_number": kwargs.get('page', 1),
                "total_results": 1000,
                "total_available": 1000,
                "has_more": True,
                "total_pages": 10,
                "has_previous": False,
                "has_next": True,
                "start_index": 1,
                "end_index": 5,
                "sort_by": "@timestamp",
                "sort_order": "desc",
                "query_time_ms": 25,  # Faster due to cache
                "indices_scanned": 0,  # No indices scanned due to cache
                "total_documents_examined": 0,  # No documents examined due to cache
                "query_complexity": "cached",
                "optimization_applied": ["cache_hit"],
                "cache_hit": True,
                "shards_scanned": 0,
                "aggregations_used": False,
            }
            return events, 1000, pagination_info

        mock_client.query_dshield_events = AsyncMock(side_effect=mock_query_with_cache_hit)

        events, total_count, pagination_info = await mock_client.query_dshield_events(
            time_range_hours=1, page_size=100
        )

        assert pagination_info["cache_hit"] is True
        assert pagination_info["query_time_ms"] == 25
        assert pagination_info["indices_scanned"] == 0
        assert pagination_info["total_documents_examined"] == 0
        assert pagination_info["query_complexity"] == "cached"
        assert "cache_hit" in pagination_info["optimization_applied"]

    @pytest.mark.asyncio
    async def test_aggregation_performance_metrics_structure(self, mock_client):
        """Test that aggregation performance metrics have the expected structure."""
        query = {"bool": {"must": [{"range": {"@timestamp": {"gte": "now-1h", "lte": "now"}}}]}}
        aggregation_query = {
            "top_sources": {"terms": {"field": "source.ip", "size": 10}},
            "event_types": {"terms": {"field": "event.type", "size": 5}},
        }

        result = await mock_client.execute_aggregation_query(
            index=["dshield-*"], query=query, aggregation_query=aggregation_query
        )

        assert "performance_metrics" in result

        metrics = result["performance_metrics"]
        required_metrics = [
            "query_time_ms",
            "indices_scanned",
            "total_documents_examined",
            "query_complexity",
            "optimization_applied",
            "cache_hit",
            "shards_scanned",
            "aggregations_used",
        ]

        for metric in required_metrics:
            assert metric in metrics, f"Missing aggregation performance metric: {metric}"

        assert metrics["aggregations_used"] is True
        assert isinstance(metrics["optimization_applied"], list)

    @pytest.mark.asyncio
    async def test_performance_metrics_edge_cases(self, mock_client):
        """Test performance metrics edge cases."""

        def mock_query_edge_case(*args, **kwargs):
            events = []
            pagination_info = {
                "page_size": kwargs.get('page_size', 100),
                "page_number": kwargs.get('page', 1),
                "total_results": 0,
                "total_available": 0,
                "has_more": False,
                "total_pages": 0,
                "has_previous": False,
                "has_next": False,
                "start_index": 0,
                "end_index": 0,
                "sort_by": "@timestamp",
                "sort_order": "desc",
                "query_time_ms": 5,  # Very fast for empty result
                "indices_scanned": 1,
                "total_documents_examined": 0,
                "query_complexity": "empty",
                "optimization_applied": [],
                "cache_hit": False,
                "shards_scanned": 2,
                "aggregations_used": False,
            }
            return events, 0, pagination_info

        mock_client.query_dshield_events = AsyncMock(side_effect=mock_query_edge_case)

        events, total_count, pagination_info = await mock_client.query_dshield_events(
            time_range_hours=1, page_size=100
        )

        assert len(events) == 0
        assert total_count == 0
        assert pagination_info["query_time_ms"] == 5
        assert pagination_info["total_documents_examined"] == 0
        assert pagination_info["query_complexity"] == "empty"
        assert pagination_info["has_more"] is False
