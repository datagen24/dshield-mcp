#!/usr/bin/env python3
"""Tests for the bounded log buffer implementation.

This module provides comprehensive tests for the LogBuffer class including
buffer eviction, filtering, substring search, burst coalescing, and lifecycle management.
"""

import asyncio
import threading
import time
from unittest.mock import Mock

import pytest

from src.tui.log_buffer import LogBuffer


class TestLogBuffer:
    """Test cases for LogBuffer class."""

    def test_buffer_initialization(self) -> None:
        """Test buffer initialization with default parameters."""
        buffer = LogBuffer()

        assert buffer.max_size == 1000
        assert buffer.coalesce_interval_ms == 100
        assert buffer.render_callback is None
        assert len(buffer.get_all_entries()) == 0
        assert len(buffer.get_filtered_entries()) == 0

    def test_buffer_initialization_with_custom_params(self) -> None:
        """Test buffer initialization with custom parameters."""
        render_callback = Mock()
        buffer = LogBuffer(max_size=500, coalesce_interval_ms=50, render_callback=render_callback)

        assert buffer.max_size == 500
        assert buffer.coalesce_interval_ms == 50
        assert buffer.render_callback == render_callback

    def test_add_single_entry(self) -> None:
        """Test adding a single log entry."""
        buffer = LogBuffer(max_size=10)
        entry = {"level": "INFO", "message": "Test message", "timestamp": time.time()}

        buffer.add_entry(entry)

        all_entries = buffer.get_all_entries()
        assert len(all_entries) == 1
        assert all_entries[0]["level"] == "INFO"
        assert all_entries[0]["message"] == "Test message"

    def test_add_multiple_entries(self) -> None:
        """Test adding multiple log entries."""
        buffer = LogBuffer(max_size=10)
        entries = [
            {"level": "INFO", "message": "Message 1"},
            {"level": "ERROR", "message": "Message 2"},
            {"level": "DEBUG", "message": "Message 3"},
        ]

        buffer.add_entries(entries)

        all_entries = buffer.get_all_entries()
        assert len(all_entries) == 3
        assert all_entries[0]["message"] == "Message 1"
        assert all_entries[1]["message"] == "Message 2"
        assert all_entries[2]["message"] == "Message 3"

    def test_buffer_eviction_at_limits(self) -> None:
        """Test that buffer evicts old entries when at capacity."""
        buffer = LogBuffer(max_size=3)

        # Add entries beyond capacity
        for i in range(5):
            buffer.add_entry({"level": "INFO", "message": f"Message {i}", "timestamp": time.time()})

        all_entries = buffer.get_all_entries()
        assert len(all_entries) == 3  # Should be capped at max_size
        assert all_entries[0]["message"] == "Message 2"  # First two should be evicted
        assert all_entries[1]["message"] == "Message 3"
        assert all_entries[2]["message"] == "Message 4"

    def test_level_filtering(self) -> None:
        """Test level filtering functionality."""
        buffer = LogBuffer(max_size=10)

        # Add entries with different levels
        entries = [
            {"level": "DEBUG", "message": "Debug message"},
            {"level": "INFO", "message": "Info message"},
            {"level": "WARNING", "message": "Warning message"},
            {"level": "ERROR", "message": "Error message"},
            {"level": "CRITICAL", "message": "Critical message"},
        ]
        buffer.add_entries(entries)

        # Test filtering by level
        buffer.set_level_filter({"INFO", "ERROR"})
        filtered_entries = buffer.get_filtered_entries()

        assert len(filtered_entries) == 2
        assert filtered_entries[0]["level"] == "INFO"
        assert filtered_entries[1]["level"] == "ERROR"

    def test_substring_search_case_insensitive(self) -> None:
        """Test substring search with case-insensitive matching."""
        buffer = LogBuffer(max_size=10)

        entries = [
            {"level": "INFO", "message": "Hello World"},
            {"level": "ERROR", "message": "Error in database"},
            {"level": "DEBUG", "message": "Debugging database connection"},
            {"level": "INFO", "message": "Database connected successfully"},
        ]
        buffer.add_entries(entries)

        # Test case-insensitive search
        buffer.set_search_filter("database", case_sensitive=False)
        filtered_entries = buffer.get_filtered_entries()

        assert len(filtered_entries) == 3
        assert "database" in filtered_entries[0]["message"].lower()
        assert "database" in filtered_entries[1]["message"].lower()
        assert "database" in filtered_entries[2]["message"].lower()

    def test_substring_search_case_sensitive(self) -> None:
        """Test substring search with case-sensitive matching."""
        buffer = LogBuffer(max_size=10)

        entries = [
            {"level": "INFO", "message": "Hello World"},
            {"level": "ERROR", "message": "Error in Database"},
            {"level": "DEBUG", "message": "Debugging database connection"},
            {"level": "INFO", "message": "Database connected successfully"},
        ]
        buffer.add_entries(entries)

        # Test case-sensitive search
        buffer.set_search_filter("Database", case_sensitive=True)
        filtered_entries = buffer.get_filtered_entries()

        assert len(filtered_entries) == 2
        assert "Database" in filtered_entries[0]["message"]
        assert "Database" in filtered_entries[1]["message"]

    def test_combined_filters(self) -> None:
        """Test combining level and search filters."""
        buffer = LogBuffer(max_size=10)

        entries = [
            {"level": "INFO", "message": "Database connection successful"},
            {"level": "ERROR", "message": "Database connection failed"},
            {"level": "DEBUG", "message": "Database query executed"},
            {"level": "INFO", "message": "User authentication successful"},
            {"level": "ERROR", "message": "User authentication failed"},
        ]
        buffer.add_entries(entries)

        # Apply both level and search filters
        buffer.set_level_filter({"ERROR"})
        buffer.set_search_filter("database", case_sensitive=False)
        filtered_entries = buffer.get_filtered_entries()

        assert len(filtered_entries) == 1
        assert filtered_entries[0]["level"] == "ERROR"
        assert "database" in filtered_entries[0]["message"].lower()

    def test_entry_normalization(self) -> None:
        """Test that entries are properly normalized."""
        buffer = LogBuffer(max_size=10)

        # Test with non-string level
        buffer.add_entry({"level": 42, "message": "Test message"})

        # Test with missing level
        buffer.add_entry({"message": "Test message 2"})

        # Test with missing message
        buffer.add_entry({"level": "INFO"})

        all_entries = buffer.get_all_entries()
        assert len(all_entries) == 3

        # Check normalization
        assert all_entries[0]["level"] == "42"  # Converted to string
        assert all_entries[1]["level"] == "INFO"  # Default level
        assert all_entries[2]["message"] == ""  # Default message

    def test_clear_buffer(self) -> None:
        """Test clearing the buffer."""
        buffer = LogBuffer(max_size=10)

        # Add some entries
        entries = [
            {"level": "INFO", "message": "Message 1"},
            {"level": "ERROR", "message": "Message 2"},
        ]
        buffer.add_entries(entries)

        assert len(buffer.get_all_entries()) == 2

        # Clear buffer
        buffer.clear()

        assert len(buffer.get_all_entries()) == 0
        assert len(buffer.get_filtered_entries()) == 0

    def test_statistics(self) -> None:
        """Test buffer statistics."""
        buffer = LogBuffer(max_size=5)

        # Add some entries
        entries = [
            {"level": "INFO", "message": "Message 1"},
            {"level": "ERROR", "message": "Message 2"},
            {"level": "DEBUG", "message": "Message 3"},
        ]
        buffer.add_entries(entries)

        stats = buffer.get_statistics()

        assert stats["buffer_size"] == 3
        assert stats["max_size"] == 5
        assert stats["total_added"] == 3
        assert stats["enabled_levels"] == {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        assert stats["search_text"] == ""
        assert stats["case_sensitive"] is False

    @pytest.mark.asyncio
    async def test_burst_coalescing(self) -> None:
        """Test burst coalescing functionality."""
        render_callback = Mock()
        buffer = LogBuffer(max_size=10, coalesce_interval_ms=100, render_callback=render_callback)

        # Add multiple entries rapidly
        for i in range(5):
            buffer.add_entry({"level": "INFO", "message": f"Message {i}", "timestamp": time.time()})

        # Wait a bit to ensure coalescing happens
        await asyncio.sleep(0.2)

        # Render callback should have been called
        assert render_callback.called

    def test_render_callback_error_handling(self) -> None:
        """Test that render callback errors are handled gracefully."""

        def failing_callback() -> None:
            raise ValueError("Test error")

        buffer = LogBuffer(max_size=10, coalesce_interval_ms=10, render_callback=failing_callback)

        # This should not raise an exception
        buffer.add_entry({"level": "INFO", "message": "Test message"})

        # Wait a bit for the callback to be called
        time.sleep(0.1)

    def test_cleanup(self) -> None:
        """Test buffer cleanup functionality."""
        buffer = LogBuffer(max_size=10)

        # Add some entries
        buffer.add_entry({"level": "INFO", "message": "Test message"})

        # Cleanup should not raise exceptions
        buffer.cleanup()

        # Buffer should still be usable after cleanup
        buffer.add_entry({"level": "INFO", "message": "Another message"})
        assert len(buffer.get_all_entries()) == 2

    def test_thread_safety(self) -> None:
        """Test that buffer operations are thread-safe."""
        buffer = LogBuffer(max_size=100)

        def add_entries_thread(thread_id: int) -> None:
            """Add entries from a thread."""
            for i in range(10):
                buffer.add_entry(
                    {
                        "level": "INFO",
                        "message": f"Thread {thread_id} message {i}",
                        "timestamp": time.time(),
                    }
                )

        # Start multiple threads adding entries
        threads = []
        for i in range(5):
            thread = threading.Thread(target=add_entries_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have 50 entries total
        assert len(buffer.get_all_entries()) == 50

    def test_filter_updates_trigger_render(self) -> None:
        """Test that filter updates trigger render callback."""
        render_callback = Mock()
        buffer = LogBuffer(max_size=10, coalesce_interval_ms=10, render_callback=render_callback)

        # Add some entries
        buffer.add_entries(
            [{"level": "INFO", "message": "Message 1"}, {"level": "ERROR", "message": "Message 2"}]
        )

        # Update filters
        buffer.set_level_filter({"ERROR"})
        buffer.set_search_filter("Message")

        # Wait for render callback
        time.sleep(0.1)

        # Render callback should have been called
        assert render_callback.called

    def test_empty_search_filter(self) -> None:
        """Test that empty search filter shows all entries."""
        buffer = LogBuffer(max_size=10)

        entries = [
            {"level": "INFO", "message": "Message 1"},
            {"level": "ERROR", "message": "Message 2"},
        ]
        buffer.add_entries(entries)

        # Set empty search filter
        buffer.set_search_filter("")
        filtered_entries = buffer.get_filtered_entries()

        assert len(filtered_entries) == 2

    def test_nonexistent_level_filter(self) -> None:
        """Test filtering with non-existent levels."""
        buffer = LogBuffer(max_size=10)

        entries = [
            {"level": "INFO", "message": "Message 1"},
            {"level": "ERROR", "message": "Message 2"},
        ]
        buffer.add_entries(entries)

        # Filter for non-existent level
        buffer.set_level_filter({"NONEXISTENT"})
        filtered_entries = buffer.get_filtered_entries()

        assert len(filtered_entries) == 0

    def test_special_characters_in_search(self) -> None:
        """Test search with special characters."""
        buffer = LogBuffer(max_size=10)

        entries = [
            {"level": "INFO", "message": "Error: connection failed"},
            {"level": "ERROR", "message": "Exception: ValueError"},
            {"level": "DEBUG", "message": "Debug info"},
        ]
        buffer.add_entries(entries)

        # Search for special characters
        buffer.set_search_filter("Error:", case_sensitive=False)
        filtered_entries = buffer.get_filtered_entries()

        assert len(filtered_entries) == 1
        assert "Error:" in filtered_entries[0]["message"]

    def test_large_message_handling(self) -> None:
        """Test handling of large messages."""
        buffer = LogBuffer(max_size=10)

        # Create a large message
        large_message = "x" * 10000
        buffer.add_entry({"level": "INFO", "message": large_message, "timestamp": time.time()})

        all_entries = buffer.get_all_entries()
        assert len(all_entries) == 1
        assert len(all_entries[0]["message"]) == 10000

    def test_unicode_handling(self) -> None:
        """Test handling of Unicode characters."""
        buffer = LogBuffer(max_size=10)

        unicode_message = "测试消息 🚀 émojis"
        buffer.add_entry({"level": "INFO", "message": unicode_message, "timestamp": time.time()})

        # Test search with Unicode
        buffer.set_search_filter("测试", case_sensitive=False)
        filtered_entries = buffer.get_filtered_entries()

        assert len(filtered_entries) == 1
        assert "测试" in filtered_entries[0]["message"]
