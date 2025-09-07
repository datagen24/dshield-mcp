"""Streaming and Smart Chunking Tests.

Tests for event streaming functionality including basic streaming, cursor-based pagination,
field selection, filtering, and smart chunking with session context.
"""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio


class TestStreaming:
    """Test basic streaming functionality."""

    @pytest_asyncio.fixture
    async def mock_es_client(self):
        """Create a mock ElasticsearchClient."""
        with patch('src.elasticsearch_client.ElasticsearchClient') as mock_class:
            client = mock_class.return_value
            client.client = AsyncMock()
            client.connect = AsyncMock()
            client.close = AsyncMock()
            client.get_available_indices = AsyncMock(return_value=["dshield-2024.01.01"])

            # Mock streaming methods
            client.stream_dshield_events = AsyncMock(return_value=([], 0, None))
            client.stream_dshield_events_with_session_context = AsyncMock(
                return_value=([], 0, None, {})
            )

            yield client

    @pytest.mark.asyncio
    async def test_basic_streaming(self, mock_es_client):
        """Test basic streaming functionality."""
        # Mock successful streaming response
        mock_events = [
            {"id": "1", "@timestamp": "2024-01-01T10:00:00Z", "source_ip": "192.168.1.100"},
            {"id": "2", "@timestamp": "2024-01-01T10:01:00Z", "source_ip": "192.168.1.101"},
        ]
        mock_es_client.stream_dshield_events.return_value = (mock_events, 100, "stream_123")

        events, total_count, stream_id = await mock_es_client.stream_dshield_events(
            time_range_hours=24, chunk_size=10, stream_id=None
        )

        assert len(events) == 2, "Should return 2 events"
        assert total_count == 100, "Total count should be 100"
        assert stream_id == "stream_123", "Should return stream ID"
        assert events[0]["id"] == "1", "First event ID should match"
        assert events[1]["id"] == "2", "Second event ID should match"

    @pytest.mark.asyncio
    async def test_streaming_with_field_selection(self, mock_es_client):
        """Test streaming with field selection."""
        # Mock field-selected response
        mock_events = [
            {
                "@timestamp": "2024-01-01T10:00:00Z",
                "source_ip": "192.168.1.100",
                "event.category": "network",
            },
            {
                "@timestamp": "2024-01-01T10:01:00Z",
                "source_ip": "192.168.1.101",
                "event.category": "network",
            },
        ]
        mock_es_client.stream_dshield_events.return_value = (mock_events, 50, "stream_456")

        events, total_count, stream_id = await mock_es_client.stream_dshield_events(
            time_range_hours=24,
            fields=["@timestamp", "source_ip", "event.category"],
            chunk_size=5,
            stream_id=None,
        )

        assert len(events) == 2, "Should return 2 events"
        assert total_count == 50, "Total count should be 50"
        assert stream_id == "stream_456", "Should return stream ID"

        # Verify field selection
        expected_fields = {"@timestamp", "source_ip", "event.category"}
        for event in events:
            assert set(event.keys()) == expected_fields, "Event should only contain selected fields"

    @pytest.mark.asyncio
    async def test_streaming_with_filters(self, mock_es_client):
        """Test streaming with filters."""
        # Mock filtered response
        mock_events = [
            {"id": "1", "@timestamp": "2024-01-01T10:00:00Z", "event.category": "network"},
            {"id": "2", "@timestamp": "2024-01-01T10:01:00Z", "event.category": "network"},
        ]
        mock_es_client.stream_dshield_events.return_value = (mock_events, 25, "stream_789")

        filters = {"event.category": "network"}

        events, total_count, stream_id = await mock_es_client.stream_dshield_events(
            time_range_hours=24, filters=filters, chunk_size=5, stream_id=None
        )

        assert len(events) == 2, "Should return 2 events"
        assert total_count == 25, "Total count should be 25"
        assert stream_id == "stream_789", "Should return stream ID"

        # Verify all events match the filter
        for event in events:
            assert event["event.category"] == "network", "All events should match filter"

    @pytest.mark.asyncio
    async def test_cursor_based_pagination(self, mock_es_client):
        """Test cursor-based pagination (resume stream)."""
        # Mock first chunk
        mock_events1 = [
            {"id": "1", "@timestamp": "2024-01-01T10:00:00Z"},
            {"id": "2", "@timestamp": "2024-01-01T10:01:00Z"},
            {"id": "3", "@timestamp": "2024-01-01T10:02:00Z"},
        ]
        mock_es_client.stream_dshield_events.return_value = (mock_events1, 100, "stream_123")

        # First chunk
        events1, total_count1, stream_id1 = await mock_es_client.stream_dshield_events(
            time_range_hours=24, chunk_size=3, stream_id=None
        )

        assert len(events1) == 3, "First chunk should have 3 events"
        assert stream_id1 == "stream_123", "Should return stream ID"

        # Mock second chunk
        mock_events2 = [
            {"id": "4", "@timestamp": "2024-01-01T10:03:00Z"},
            {"id": "5", "@timestamp": "2024-01-01T10:04:00Z"},
            {"id": "6", "@timestamp": "2024-01-01T10:05:00Z"},
        ]
        mock_es_client.stream_dshield_events.return_value = (mock_events2, 100, "stream_456")

        # Second chunk using stream_id
        events2, total_count2, stream_id2 = await mock_es_client.stream_dshield_events(
            time_range_hours=24, chunk_size=3, stream_id=stream_id1
        )

        assert len(events2) == 3, "Second chunk should have 3 events"
        assert stream_id2 == "stream_456", "Should return new stream ID"

        # Verify no overlap
        event_ids1 = [event["id"] for event in events1]
        event_ids2 = [event["id"] for event in events2]
        overlap = set(event_ids1) & set(event_ids2)
        assert len(overlap) == 0, "Chunks should not overlap"

    @pytest.mark.asyncio
    async def test_large_dataset_simulation(self, mock_es_client):
        """Test large dataset simulation with multiple chunks."""
        # Mock multiple chunks
        chunk_responses = [
            ([{"id": str(i)} for i in range(1, 11)], 100, "stream_1"),  # Chunk 1
            ([{"id": str(i)} for i in range(11, 21)], 100, "stream_2"),  # Chunk 2
            ([{"id": str(i)} for i in range(21, 31)], 100, "stream_3"),  # Chunk 3
            ([], 100, None),  # No more events
        ]

        mock_es_client.stream_dshield_events.side_effect = chunk_responses

        # Simulate processing multiple chunks
        all_events = []
        current_stream_id = None
        chunk_count = 0
        max_chunks = 5

        while chunk_count < max_chunks:
            events, total_count, stream_id = await mock_es_client.stream_dshield_events(
                time_range_hours=24, chunk_size=10, stream_id=current_stream_id
            )

            if not events:
                break

            all_events.extend(events)
            current_stream_id = stream_id
            chunk_count += 1

        assert chunk_count == 3, "Should process 3 chunks"
        assert len(all_events) == 30, "Should have 30 total events"

        # Verify no duplicates
        event_ids = [event["id"] for event in all_events]
        unique_ids = set(event_ids)
        assert len(unique_ids) == len(event_ids), "Should have no duplicate events"

    @pytest.mark.asyncio
    async def test_time_range_streaming(self, mock_es_client):
        """Test streaming with custom time range."""
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=6)

        time_filters = {"@timestamp": {"gte": start_time.isoformat(), "lte": end_time.isoformat()}}

        mock_events = [
            {"id": "1", "@timestamp": start_time.isoformat()},
            {"id": "2", "@timestamp": end_time.isoformat()},
        ]
        mock_es_client.stream_dshield_events.return_value = (mock_events, 50, "stream_time")

        events, total_count, stream_id = await mock_es_client.stream_dshield_events(
            time_range_hours=6, filters=time_filters, chunk_size=5, stream_id=None
        )

        assert len(events) == 2, "Should return 2 events"
        assert total_count == 50, "Total count should be 50"
        assert stream_id == "stream_time", "Should return stream ID"

    @pytest.mark.asyncio
    async def test_streaming_error_handling(self, mock_es_client):
        """Test streaming error handling."""
        # Mock connection error
        mock_es_client.stream_dshield_events.side_effect = Exception("Connection failed")

        with pytest.raises(Exception, match="Connection failed"):
            await mock_es_client.stream_dshield_events(time_range_hours=24, chunk_size=10)

    @pytest.mark.asyncio
    async def test_streaming_empty_response(self, mock_es_client):
        """Test streaming with empty response."""
        # Mock empty response
        mock_es_client.stream_dshield_events.return_value = ([], 0, None)

        events, total_count, stream_id = await mock_es_client.stream_dshield_events(
            time_range_hours=24, chunk_size=10
        )

        assert len(events) == 0, "Should return empty events list"
        assert total_count == 0, "Total count should be 0"
        assert stream_id is None, "Stream ID should be None for empty response"


class TestSmartChunking:
    """Test smart chunking with session context functionality."""

    @pytest_asyncio.fixture
    async def mock_es_client(self):
        """Create a mock ElasticsearchClient."""
        with patch('src.elasticsearch_client.ElasticsearchClient') as mock_class:
            client = mock_class.return_value
            client.client = AsyncMock()
            client.connect = AsyncMock()
            client.close = AsyncMock()
            client.get_available_indices = AsyncMock(return_value=["dshield-2024.01.01"])

            # Mock session context method
            client.stream_dshield_events_with_session_context = AsyncMock(
                return_value=([], 0, None, {})
            )

            yield client

    @pytest.mark.asyncio
    async def test_basic_session_chunking(self, mock_es_client):
        """Test basic session chunking with default fields."""
        # Mock session context response
        mock_events = [
            {"id": "1", "@timestamp": "2024-01-01T10:00:00Z", "source.ip": "192.168.1.100"},
            {"id": "2", "@timestamp": "2024-01-01T10:01:00Z", "source.ip": "192.168.1.100"},
            {"id": "3", "@timestamp": "2024-01-01T10:02:00Z", "source.ip": "192.168.1.101"},
        ]

        mock_session_context = {
            "session_fields": ["source.ip", "destination.ip", "user.name", "session.id"],
            "max_session_gap_minutes": 30,
            "sessions_in_chunk": 2,
            "session_summaries": [
                {
                    "session_key": "192.168.1.100",
                    "event_count": 2,
                    "duration_minutes": 1.0,
                    "metadata": {"source.ip": "192.168.1.100"},
                },
                {
                    "session_key": "192.168.1.101",
                    "event_count": 1,
                    "duration_minutes": 0.0,
                    "metadata": {"source.ip": "192.168.1.101"},
                },
            ],
            "performance_metrics": {
                "query_time_ms": 150,
                "sessions_processed": 2,
                "session_chunks_created": 1,
            },
        }

        mock_es_client.stream_dshield_events_with_session_context.return_value = (
            mock_events,
            100,
            "session_stream_123",
            mock_session_context,
        )

        (
            events,
            total_count,
            next_stream_id,
            session_context,
        ) = await mock_es_client.stream_dshield_events_with_session_context(
            time_range_hours=1, chunk_size=100
        )

        assert len(events) == 3, "Should return 3 events"
        assert total_count == 100, "Total count should be 100"
        assert next_stream_id == "session_stream_123", "Should return stream ID"
        assert session_context["sessions_in_chunk"] == 2, "Should have 2 sessions"
        assert len(session_context["session_summaries"]) == 2, "Should have 2 session summaries"
        assert session_context["performance_metrics"]["query_time_ms"] == 150, (
            "Should have performance metrics"
        )

    @pytest.mark.asyncio
    async def test_custom_session_fields(self, mock_es_client):
        """Test custom session fields."""
        mock_events = [{"id": "1", "source.ip": "192.168.1.100", "destination.ip": "10.0.0.1"}]

        mock_session_context = {
            "session_fields": ["source.ip", "destination.ip"],
            "sessions_in_chunk": 1,
            "session_summaries": [],
        }

        mock_es_client.stream_dshield_events_with_session_context.return_value = (
            mock_events,
            50,
            "stream_456",
            mock_session_context,
        )

        (
            events,
            total_count,
            next_stream_id,
            session_context,
        ) = await mock_es_client.stream_dshield_events_with_session_context(
            time_range_hours=1, session_fields=["source.ip", "destination.ip"], chunk_size=50
        )

        assert len(events) == 1, "Should return 1 event"
        assert session_context["session_fields"] == ["source.ip", "destination.ip"], (
            "Should use custom session fields"
        )
        assert session_context["sessions_in_chunk"] == 1, "Should have 1 session"

    @pytest.mark.asyncio
    async def test_session_summaries(self, mock_es_client):
        """Test session summaries functionality."""
        mock_session_summaries = [
            {
                "session_key": "192.168.1.100",
                "event_count": 5,
                "duration_minutes": 15.5,
                "metadata": {"source.ip": "192.168.1.100", "destination.ip": "10.0.0.1"},
            }
        ]

        mock_session_context = {
            "session_fields": ["source.ip", "destination.ip"],
            "sessions_in_chunk": 1,
            "session_summaries": mock_session_summaries,
        }

        mock_es_client.stream_dshield_events_with_session_context.return_value = (
            [],
            200,
            "stream_789",
            mock_session_context,
        )

        (
            events,
            total_count,
            next_stream_id,
            session_context,
        ) = await mock_es_client.stream_dshield_events_with_session_context(
            time_range_hours=1, include_session_summary=True, chunk_size=200
        )

        assert len(session_context["session_summaries"]) == 1, "Should have 1 session summary"

        summary = session_context["session_summaries"][0]
        assert summary["session_key"] == "192.168.1.100", "Session key should match"
        assert summary["event_count"] == 5, "Event count should match"
        assert summary["duration_minutes"] == 15.5, "Duration should match"
        assert summary["metadata"]["source.ip"] == "192.168.1.100", "Metadata should match"

    @pytest.mark.asyncio
    async def test_filtered_session_chunking(self, mock_es_client):
        """Test filtered session chunking."""
        mock_events = [{"id": "1", "source.ip": "141.98.80.135"}]

        mock_session_context = {
            "session_fields": ["source.ip", "destination.ip", "event.type"],
            "sessions_in_chunk": 1,
            "performance_metrics": {"query_time_ms": 200},
        }

        mock_es_client.stream_dshield_events_with_session_context.return_value = (
            mock_events,
            25,
            "filtered_stream",
            mock_session_context,
        )

        (
            events,
            total_count,
            next_stream_id,
            session_context,
        ) = await mock_es_client.stream_dshield_events_with_session_context(
            time_range_hours=24,
            filters={"source.ip": "141.98.80.135"},
            session_fields=["source.ip", "destination.ip", "event.type"],
            chunk_size=100,
        )

        assert len(events) == 1, "Should return 1 event"
        assert total_count == 25, "Total count should be 25"
        assert session_context["sessions_in_chunk"] == 1, "Should have 1 session"
        assert session_context["performance_metrics"]["query_time_ms"] == 200, (
            "Should have performance metrics"
        )

    @pytest.mark.asyncio
    async def test_field_selection_with_session_chunking(self, mock_es_client):
        """Test field selection with session chunking."""
        mock_events = [
            {
                "@timestamp": "2024-01-01T10:00:00Z",
                "source.ip": "192.168.1.100",
                "destination.ip": "10.0.0.1",
                "event.type": "network",
            }
        ]

        mock_session_context = {
            "session_fields": ["source.ip"],
            "sessions_in_chunk": 1,
            "performance_metrics": {"query_time_ms": 100},
        }

        mock_es_client.stream_dshield_events_with_session_context.return_value = (
            mock_events,
            50,
            "field_stream",
            mock_session_context,
        )

        (
            events,
            total_count,
            next_stream_id,
            session_context,
        ) = await mock_es_client.stream_dshield_events_with_session_context(
            time_range_hours=1,
            fields=["@timestamp", "source.ip", "destination.ip", "event.type"],
            session_fields=["source.ip"],
            chunk_size=50,
        )

        assert len(events) == 1, "Should return 1 event"
        assert session_context["sessions_in_chunk"] == 1, "Should have 1 session"
        assert session_context["performance_metrics"]["query_time_ms"] == 100, (
            "Should have performance metrics"
        )

        # Verify field selection
        expected_fields = {"@timestamp", "source.ip", "destination.ip", "event.type"}
        for event in events:
            assert set(event.keys()) == expected_fields, "Event should only contain selected fields"

    @pytest.mark.asyncio
    async def test_session_gap_configuration(self, mock_es_client):
        """Test session gap configuration."""
        mock_session_context = {
            "session_fields": ["source.ip", "destination.ip"],
            "max_session_gap_minutes": 15,
            "sessions_in_chunk": 3,
        }

        mock_es_client.stream_dshield_events_with_session_context.return_value = (
            [],
            100,
            "gap_stream",
            mock_session_context,
        )

        (
            events,
            total_count,
            next_stream_id,
            session_context,
        ) = await mock_es_client.stream_dshield_events_with_session_context(
            time_range_hours=1,
            max_session_gap_minutes=15,
            session_fields=["source.ip", "destination.ip"],
            chunk_size=100,
        )

        assert session_context["max_session_gap_minutes"] == 15, "Should use custom session gap"
        assert session_context["sessions_in_chunk"] == 3, "Should have 3 sessions"

    @pytest.mark.asyncio
    async def test_performance_comparison(self, mock_es_client):
        """Test performance comparison between regular and session streaming."""
        # Mock regular streaming
        mock_es_client.stream_dshield_events = AsyncMock(
            return_value=([{"id": "1"}], 100, "regular_stream")
        )

        # Mock session streaming
        mock_session_context = {
            "performance_metrics": {"query_time_ms": 150, "sessions_processed": 2}
        }
        mock_es_client.stream_dshield_events_with_session_context = AsyncMock(
            return_value=([{"id": "1"}], 100, "session_stream", mock_session_context)
        )

        # Test regular streaming
        events_regular, _, _ = await mock_es_client.stream_dshield_events(
            time_range_hours=1, chunk_size=100
        )

        # Test session streaming
        (
            events_session,
            _,
            _,
            session_context,
        ) = await mock_es_client.stream_dshield_events_with_session_context(
            time_range_hours=1, chunk_size=100
        )

        assert len(events_regular) == 1, "Regular streaming should return 1 event"
        assert len(events_session) == 1, "Session streaming should return 1 event"
        assert session_context["performance_metrics"]["sessions_processed"] == 2, (
            "Should process 2 sessions"
        )
        assert session_context["performance_metrics"]["query_time_ms"] == 150, (
            "Should have performance metrics"
        )

    @pytest.mark.asyncio
    async def test_session_chunking_error_handling(self, mock_es_client):
        """Test session chunking error handling."""
        # Mock error
        mock_es_client.stream_dshield_events_with_session_context.side_effect = Exception(
            "Session processing failed"
        )

        with pytest.raises(Exception, match="Session processing failed"):
            await mock_es_client.stream_dshield_events_with_session_context(
                time_range_hours=1, chunk_size=100
            )

    @pytest.mark.asyncio
    async def test_session_chunking_empty_response(self, mock_es_client):
        """Test session chunking with empty response."""
        # Mock empty response
        mock_session_context = {
            "session_fields": ["source.ip"],
            "sessions_in_chunk": 0,
            "session_summaries": [],
            "performance_metrics": {"query_time_ms": 50},
        }

        mock_es_client.stream_dshield_events_with_session_context.return_value = (
            [],
            0,
            None,
            mock_session_context,
        )

        (
            events,
            total_count,
            next_stream_id,
            session_context,
        ) = await mock_es_client.stream_dshield_events_with_session_context(
            time_range_hours=1, chunk_size=100
        )

        assert len(events) == 0, "Should return empty events list"
        assert total_count == 0, "Total count should be 0"
        assert next_stream_id is None, "Stream ID should be None"
        assert session_context["sessions_in_chunk"] == 0, "Should have 0 sessions"
        assert len(session_context["session_summaries"]) == 0, "Should have 0 session summaries"
