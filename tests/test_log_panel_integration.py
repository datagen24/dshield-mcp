#!/usr/bin/env python3
"""Integration tests for the updated log panel with bounded buffer.

This module provides tests for the LogPanel class integration with the LogBuffer,
including UI interactions, filtering, and lifecycle management.
"""

import time
from unittest.mock import Mock

from src.tui.log_panel import LogPanel


class TestLogPanelIntegration:
    """Test cases for LogPanel integration with LogBuffer."""

    def test_log_panel_initialization(self) -> None:
        """Test log panel initialization with bounded buffer."""
        panel = LogPanel(max_entries=500)

        assert panel.log_buffer.max_size == 500
        assert panel.log_buffer.coalesce_interval_ms == 100
        assert panel.filter_config["levels"] == {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        assert panel.filter_config["search_text"] == ""
        assert panel.filter_config["case_sensitive"] is False

    def test_add_log_entries_integration(self) -> None:
        """Test adding log entries through the panel."""
        panel = LogPanel(max_entries=10)

        entries = [
            {"level": "INFO", "message": "Test message 1"},
            {"level": "ERROR", "message": "Test message 2"},
            {"level": "DEBUG", "message": "Test message 3"},
        ]

        panel.add_log_entries(entries)

        # Check that entries were added to buffer
        all_entries = panel.log_buffer.get_all_entries()
        assert len(all_entries) == 3
        assert all_entries[0]["message"] == "Test message 1"
        assert all_entries[1]["message"] == "Test message 2"
        assert all_entries[2]["message"] == "Test message 3"

    def test_clear_logs_integration(self) -> None:
        """Test clearing logs through the panel."""
        panel = LogPanel(max_entries=10)

        # Add some entries
        panel.add_log_entries(
            [
                {"level": "INFO", "message": "Test message 1"},
                {"level": "ERROR", "message": "Test message 2"},
            ]
        )

        assert len(panel.log_buffer.get_all_entries()) == 2

        # Mock the UI elements that would be present in a mounted panel
        from unittest.mock import Mock
        mock_text_area = Mock()
        panel.query_one = Mock(return_value=mock_text_area)

        # Clear logs
        panel.clear_logs()

        assert len(panel.log_buffer.get_all_entries()) == 0

    def test_render_callback_integration(self) -> None:
        """Test that render callback is properly connected."""
        panel = LogPanel(max_entries=10)

        # Mock the _update_display method
        panel._update_display = Mock()

        # Add an entry which should trigger render callback
        panel.add_log_entries([{"level": "INFO", "message": "Test message"}])

        # Wait a bit for the callback to be called
        time.sleep(0.2)

        # _update_display should have been called
        assert panel._update_display.called

    def test_level_filtering_integration(self) -> None:
        """Test level filtering through the panel."""
        panel = LogPanel(max_entries=10)

        # Add entries with different levels
        entries = [
            {"level": "DEBUG", "message": "Debug message"},
            {"level": "INFO", "message": "Info message"},
            {"level": "ERROR", "message": "Error message"},
        ]
        panel.add_log_entries(entries)

        # Update level filter
        panel.filter_config["levels"] = {"INFO", "ERROR"}
        panel._apply_filters()

        # Check that buffer filters were updated
        assert panel.log_buffer._enabled_levels == {"INFO", "ERROR"}

        # Get filtered entries
        filtered_entries = panel.log_buffer.get_filtered_entries()
        assert len(filtered_entries) == 2
        assert filtered_entries[0]["level"] == "INFO"
        assert filtered_entries[1]["level"] == "ERROR"

    def test_search_filtering_integration(self) -> None:
        """Test search filtering through the panel."""
        panel = LogPanel(max_entries=10)

        # Add entries
        entries = [
            {"level": "INFO", "message": "Database connection successful"},
            {"level": "ERROR", "message": "Database connection failed"},
            {"level": "INFO", "message": "User authentication successful"},
        ]
        panel.add_log_entries(entries)

        # Update search filter
        panel.filter_config["search_text"] = "database"
        panel.filter_config["case_sensitive"] = False
        panel._apply_filters()

        # Check that buffer filters were updated
        assert panel.log_buffer._search_text == "database"
        assert panel.log_buffer._case_sensitive is False

        # Get filtered entries
        filtered_entries = panel.log_buffer.get_filtered_entries()
        assert len(filtered_entries) == 2
        assert "database" in filtered_entries[0]["message"].lower()
        assert "database" in filtered_entries[1]["message"].lower()

    def test_case_sensitive_search_integration(self) -> None:
        """Test case-sensitive search filtering."""
        panel = LogPanel(max_entries=10)

        # Add entries
        entries = [
            {"level": "INFO", "message": "Database connection successful"},
            {"level": "ERROR", "message": "database connection failed"},
            {"level": "INFO", "message": "User authentication successful"},
        ]
        panel.add_log_entries(entries)

        # Update search filter with case sensitivity
        panel.filter_config["search_text"] = "Database"
        panel.filter_config["case_sensitive"] = True
        panel._apply_filters()

        # Check that buffer filters were updated
        assert panel.log_buffer._search_text == "Database"
        assert panel.log_buffer._case_sensitive is True

        # Get filtered entries
        filtered_entries = panel.log_buffer.get_filtered_entries()
        assert len(filtered_entries) == 1
        assert "Database" in filtered_entries[0]["message"]

    def test_get_log_statistics_integration(self) -> None:
        """Test getting log statistics through the panel."""
        panel = LogPanel(max_entries=10)

        # Add some entries
        entries = [
            {"level": "INFO", "message": "Message 1"},
            {"level": "ERROR", "message": "Message 2"},
            {"level": "DEBUG", "message": "Message 3"},
        ]
        panel.add_log_entries(entries)

        # Get statistics
        stats = panel.get_log_statistics()

        assert stats["total_entries"] == 3
        assert stats["max_entries"] == 10
        assert "buffer_statistics" in stats
        assert stats["level_counts"]["INFO"] == 1
        assert stats["level_counts"]["ERROR"] == 1
        assert stats["level_counts"]["DEBUG"] == 1

    def test_set_max_entries_integration(self) -> None:
        """Test setting max entries through the panel."""
        panel = LogPanel(max_entries=10)

        # Add some entries
        panel.add_log_entries(
            [{"level": "INFO", "message": "Message 1"}, {"level": "ERROR", "message": "Message 2"}]
        )

        # Change max entries
        panel.set_max_entries(5)

        # Check that buffer was updated
        assert panel.log_buffer.max_size == 5

        # Check that existing entries were preserved
        all_entries = panel.log_buffer.get_all_entries()
        assert len(all_entries) == 2

    def test_set_max_entries_with_eviction(self) -> None:
        """Test setting max entries that causes eviction."""
        panel = LogPanel(max_entries=10)

        # Add more entries than new max
        entries = []
        for i in range(8):
            entries.append({"level": "INFO", "message": f"Message {i}"})
        panel.add_log_entries(entries)

        # Set max entries to 5
        panel.set_max_entries(5)

        # Check that buffer was updated and entries were evicted
        assert panel.log_buffer.max_size == 5
        all_entries = panel.log_buffer.get_all_entries()
        assert len(all_entries) == 5  # Should be capped at new max

    def test_on_unmount_cleanup(self) -> None:
        """Test cleanup on unmount."""
        panel = LogPanel(max_entries=10)

        # Add some entries
        panel.add_log_entries(
            [{"level": "INFO", "message": "Message 1"}, {"level": "ERROR", "message": "Message 2"}]
        )

        # Mock the cleanup method
        panel.log_buffer.cleanup = Mock()

        # Call on_unmount
        panel.on_unmount()

        # Check that cleanup was called
        assert panel.log_buffer.cleanup.called

    def test_format_log_entry_with_timestamps(self) -> None:
        """Test formatting log entries with timestamps."""
        panel = LogPanel(max_entries=10)

        entry = {
            "level": "INFO",
            "message": "Test message",
            "timestamp": "2024-01-01T12:00:00",
            "source": "test",
        }

        # Test with timestamps enabled
        panel.filter_config["show_timestamps"] = True
        panel.filter_config["show_levels"] = True
        panel.filter_config["show_sources"] = True

        formatted = panel._format_log_entry(entry)

        assert "[INFO]" in formatted
        assert "[test]" in formatted
        assert "Test message" in formatted
        assert "12:00:00" in formatted  # Should format timestamp

    def test_format_log_entry_without_timestamps(self) -> None:
        """Test formatting log entries without timestamps."""
        panel = LogPanel(max_entries=10)

        entry = {"level": "ERROR", "message": "Error message", "source": "test"}

        # Test with timestamps disabled
        panel.filter_config["show_timestamps"] = False
        panel.filter_config["show_levels"] = True
        panel.filter_config["show_sources"] = True

        formatted = panel._format_log_entry(entry)

        assert "[ERROR]" in formatted
        assert "[test]" in formatted
        assert "Error message" in formatted
        assert "[" not in formatted or formatted.count("[") == 2  # Only level and source

    def test_filter_config_persistence(self) -> None:
        """Test that filter configuration persists across operations."""
        panel = LogPanel(max_entries=10)

        # Set initial filter config
        panel.filter_config["levels"] = {"ERROR", "CRITICAL"}
        panel.filter_config["search_text"] = "error"
        panel.filter_config["case_sensitive"] = True

        # Add entries
        panel.add_log_entries(
            [
                {"level": "INFO", "message": "Info message"},
                {"level": "ERROR", "message": "Error message"},
                {"level": "CRITICAL", "message": "Critical error"},
            ]
        )

        # Apply filters
        panel._apply_filters()

        # Check that filter config is preserved
        assert panel.filter_config["levels"] == {"ERROR", "CRITICAL"}
        assert panel.filter_config["search_text"] == "error"
        assert panel.filter_config["case_sensitive"] is True

        # Check that buffer filters were applied
        assert panel.log_buffer._enabled_levels == {"ERROR", "CRITICAL"}
        assert panel.log_buffer._search_text == "error"
        assert panel.log_buffer._case_sensitive is True

    def test_large_number_of_entries(self) -> None:
        """Test handling large number of entries."""
        panel = LogPanel(max_entries=1000)

        # Add many entries
        entries = []
        for i in range(2000):  # More than max_entries
            entries.append({"level": "INFO", "message": f"Message {i}", "timestamp": time.time()})

        panel.add_log_entries(entries)

        # Should be capped at max_entries
        all_entries = panel.log_buffer.get_all_entries()
        assert len(all_entries) == 1000

        # Should contain the last 1000 entries
        assert all_entries[0]["message"] == "Message 1000"
        assert all_entries[-1]["message"] == "Message 1999"

    def test_concurrent_operations(self) -> None:
        """Test concurrent operations on the panel."""
        import threading

        panel = LogPanel(max_entries=100)

        def add_entries_thread(thread_id: int) -> None:
            """Add entries from a thread."""
            for i in range(10):
                panel.add_log_entries(
                    [
                        {
                            "level": "INFO",
                            "message": f"Thread {thread_id} message {i}",
                            "timestamp": time.time(),
                        }
                    ]
                )

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=add_entries_thread, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have entries from all threads
        all_entries = panel.log_buffer.get_all_entries()
        assert len(all_entries) == 50  # 5 threads * 10 entries each

    def test_render_callback_error_handling(self) -> None:
        """Test that render callback errors are handled gracefully."""
        panel = LogPanel(max_entries=10)

        # Mock _update_display to raise an exception
        panel._update_display = Mock(side_effect=ValueError("Test error"))

        # This should not raise an exception
        panel.add_log_entries([{"level": "INFO", "message": "Test message"}])

        # Wait a bit for the callback to be called
        time.sleep(0.2)

        # _update_display should have been called despite the error
        assert panel._update_display.called
