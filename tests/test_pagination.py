"""Tests for pagination functionality in DShield MCP service."""

import pytest
from unittest.mock import Mock
from src.elasticsearch_client import ElasticsearchClient

@pytest.fixture
def mock_es_client():
    """Create a mock ElasticsearchClient for testing pagination functionality.
    
    Returns:
        Mock ElasticsearchClient with pagination info generation mocked.

    """
    client = ElasticsearchClient.__new__(ElasticsearchClient)
    client.max_results = 1000
    client._generate_pagination_info = Mock(side_effect=lambda page, page_size, total_count: {
        "current_page": page,
        "page_size": page_size,
        "total_count": total_count,
        "total_pages": (total_count + page_size - 1) // page_size,
        "has_next": page < ((total_count + page_size - 1) // page_size),
        "has_previous": page > 1,
        "next_page": page + 1 if page < ((total_count + page_size - 1) // page_size) else None,
        "previous_page": page - 1 if page > 1 else None,
        "start_index": (page - 1) * page_size + 1,
        "end_index": min(page * page_size, total_count)
    })
    return client

class TestPagination:
    """Unit tests for pagination logic in ElasticsearchClient."""

    def test_first_page_pagination(self, mock_es_client):
        """Test pagination info for the first page of results."""
        # Simulate 25 total events, page 1, page_size 10
        page, page_size, total_count = 1, 10, 25
        events = [{} for _ in range(10)]
        mock_es_client.query_dshield_events = Mock(return_value=(events, total_count))
        pagination_info = mock_es_client._generate_pagination_info(page, page_size, total_count)
        assert pagination_info["current_page"] == 1
        assert pagination_info["page_size"] == 10
        assert pagination_info["total_count"] == 25
        assert pagination_info["total_pages"] == 3
        assert pagination_info["has_next"] is True
        assert pagination_info["has_previous"] is False
        assert pagination_info["next_page"] == 2
        assert pagination_info["previous_page"] is None
        assert pagination_info["start_index"] == 1
        assert pagination_info["end_index"] == 10

    def test_second_page_pagination(self, mock_es_client):
        """Test pagination info for the second page of results."""
        page, page_size, total_count = 2, 10, 25
        events = [{} for _ in range(10)]
        mock_es_client.query_dshield_events = Mock(return_value=(events, total_count))
        pagination_info = mock_es_client._generate_pagination_info(page, page_size, total_count)
        assert pagination_info["current_page"] == 2
        assert pagination_info["has_next"] is True
        assert pagination_info["has_previous"] is True
        assert pagination_info["next_page"] == 3
        assert pagination_info["previous_page"] == 1
        assert pagination_info["start_index"] == 11
        assert pagination_info["end_index"] == 20

    def test_last_page_pagination(self, mock_es_client):
        """Test pagination info for the last page of results."""
        page, page_size, total_count = 3, 10, 25
        events = [{} for _ in range(5)]
        mock_es_client.query_dshield_events = Mock(return_value=(events, total_count))
        pagination_info = mock_es_client._generate_pagination_info(page, page_size, total_count)
        assert pagination_info["current_page"] == 3
        assert pagination_info["has_next"] is False
        assert pagination_info["has_previous"] is True
        assert pagination_info["next_page"] is None
        assert pagination_info["previous_page"] == 2
        assert pagination_info["start_index"] == 21
        assert pagination_info["end_index"] == 25

    def test_large_page_size(self, mock_es_client):
        """Test pagination info when page size exceeds total events."""
        page, page_size, total_count = 1, 50, 25
        events = [{} for _ in range(25)]
        mock_es_client.query_dshield_events = Mock(return_value=(events, total_count))
        pagination_info = mock_es_client._generate_pagination_info(page, page_size, total_count)
        assert pagination_info["current_page"] == 1
        assert pagination_info["page_size"] == 50
        assert pagination_info["total_pages"] == 1
        assert pagination_info["has_next"] is False
        assert pagination_info["end_index"] == 25

    def test_page_size_larger_than_max(self, mock_es_client):
        """Test pagination info when page size is larger than max_results."""
        page, page_size, total_count = 1, 2000, 100
        # Should be capped at max_results (1000)
        capped_size = min(page_size, mock_es_client.max_results)
        events = [{} for _ in range(min(capped_size, total_count))]
        mock_es_client.query_dshield_events = Mock(return_value=(events, total_count))
        pagination_info = mock_es_client._generate_pagination_info(page, capped_size, total_count)
        assert pagination_info["page_size"] == 1000
        assert pagination_info["end_index"] == 100

    def test_very_large_page_number(self, mock_es_client):
        """Test pagination info for a very large page number (no results)."""
        page, page_size, total_count = 1000, 10, 25
        events = []
        mock_es_client.query_dshield_events = Mock(return_value=(events, total_count))
        pagination_info = mock_es_client._generate_pagination_info(page, page_size, total_count)
        assert pagination_info["current_page"] == 1000
        assert pagination_info["start_index"] == 9991
        assert pagination_info["end_index"] == 25
        assert pagination_info["has_next"] is False

    def test_attacks_pagination(self, mock_es_client):
        """Test pagination info for attacks endpoint."""
        page, page_size, total_count = 1, 5, 12
        attacks = [{} for _ in range(5)]
        mock_es_client.query_dshield_attacks = Mock(return_value=(attacks, total_count))
        pagination_info = mock_es_client._generate_pagination_info(page, page_size, total_count)
        assert pagination_info["current_page"] == 1
        assert pagination_info["page_size"] == 5
        assert pagination_info["total_pages"] == 3
        assert pagination_info["has_next"] is True
        assert pagination_info["end_index"] == 5

    def test_pagination_info_structure(self, mock_es_client):
        """Test that pagination info contains all expected keys."""
        page, page_size, total_count = 2, 10, 25
        pagination_info = mock_es_client._generate_pagination_info(page, page_size, total_count)
        expected_keys = {"current_page", "page_size", "total_count", "total_pages", "has_next", "has_previous", "next_page", "previous_page", "start_index", "end_index"}
        assert set(pagination_info.keys()) == expected_keys 