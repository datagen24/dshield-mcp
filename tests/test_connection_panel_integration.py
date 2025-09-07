#!/usr/bin/env python3
"""Integration tests for Connection Panel using Textual Pilot.

This module provides comprehensive integration tests for the connection panel,
including table rendering, pagination, filtering, and message emission.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Any, TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from textual.app import App
from textual.pilot import Pilot

from src.tui.connection_panel import (
    APIKeyGenerate,
    APIKeyRevoke,
    ConnectionDisconnect,
    ConnectionFilter,
    ConnectionPanel,
    ConnectionRefresh,
)

if TYPE_CHECKING:
    from _pytest.capture import CaptureFixture
    from _pytest.fixtures import FixtureRequest
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture


class TestConnectionPanelIntegration:
    """Integration tests for ConnectionPanel using Textual Pilot."""

    @pytest.fixture
    def sample_connections(self) -> list[dict[str, Any]]:
        """Generate a realistic sample of 60+ connections for testing."""
        connections = []
        base_time = datetime.now() - timedelta(hours=24)
        
        # Generate diverse connection data
        for i in range(65):  # 65 connections to test pagination
            # Vary connection types and states
            is_authenticated = i % 3 != 0  # 2/3 authenticated
            has_violations = i % 7 == 0  # Some have violations
            is_initialized = i % 5 != 0  # Most are initialized
            
            # Generate realistic IP addresses
            ip_octet = 100 + (i % 155)  # 100.0.0.0 to 254.0.0.0 range
            client_address = f"192.168.1.{ip_octet % 255}"
            
            # Generate API key IDs
            key_id = f"key_{i:03d}" if is_authenticated else None
            
            # Generate permissions
            permissions = {}
            if is_authenticated:
                if i % 2 == 0:
                    permissions = {"read": True, "write": False}
                else:
                    permissions = {"read": True, "write": True, "admin": i % 3 == 0}
            
            # Generate RPS and violations
            rps = (i % 20) + 1  # 1-20 RPS
            violations = (i % 3) if has_violations else 0
            
            # Generate connection time
            connected_at = base_time + timedelta(minutes=i * 15)
            
            connection = {
                "client_address": client_address,
                "api_key_id": key_id,
                "key_id": key_id,  # Alternative field name
                "permissions": permissions,
                "rps": rps,
                "requests_per_second": rps,  # Alternative field name
                "violations": violations,
                "connected_at": connected_at.isoformat() + "Z",
                "is_authenticated": is_authenticated,
                "is_initialized": is_initialized,
                "status": "Active" if is_authenticated and not has_violations else "Unknown",
            }
            connections.append(connection)
        
        return connections

    @pytest.fixture
    def sample_api_keys(self) -> list[dict[str, Any]]:
        """Generate sample API keys for testing."""
        keys = []
        base_time = datetime.now() - timedelta(days=30)
        
        for i in range(10):
            created_at = base_time + timedelta(days=i * 3)
            expires_at = created_at + timedelta(days=90)
            
            key = {
                "key_id": f"api_key_{i:03d}",
                "created_at": created_at.isoformat() + "Z",
                "expires_at": expires_at.isoformat() + "Z",
                "permissions": {
                    "read": True,
                    "write": i % 2 == 0,
                    "admin": i % 3 == 0,
                },
                "active_sessions": i % 5,
            }
            keys.append(key)
        
        return keys

    @pytest.fixture
    def mock_app(self) -> App:
        """Create a mock Textual app for testing."""
        app = App()
        app.logger = MagicMock()
        return app

    @pytest.fixture
    async def connection_panel(self, mock_app: App) -> ConnectionPanel:
        """Create a ConnectionPanel instance for testing."""
        panel = ConnectionPanel(refresh_interval=0.1)  # Fast refresh for testing
        await mock_app.mount(panel)
        return panel

    @pytest.mark.asyncio
    async def test_connection_panel_rendering_with_large_dataset(
        self, 
        connection_panel: ConnectionPanel, 
        sample_connections: list[dict[str, Any]]
    ) -> None:
        """Test that the connection panel renders correctly with a large dataset."""
        # Update connections with large dataset
        connection_panel.update_connections(sample_connections)
        
        # Verify table has correct number of columns
        connections_table = connection_panel.query_one("#connections-table")
        assert len(connections_table.columns) == 7  # Expected columns
        
        # Verify pagination is working (should show 20 rows per page)
        total_pages = (len(sample_connections) + 19) // 20  # 65 connections = 4 pages
        assert connection_panel.current_page == 0  # Should start at page 0
        
        # Verify page info is updated
        page_info = connection_panel.query_one("#page-info")
        assert "Page 1 of 4" in page_info.renderable
        
        # Verify pagination buttons are in correct state
        prev_btn = connection_panel.query_one("#prev-page-btn")
        next_btn = connection_panel.query_one("#next-page-btn")
        
        assert prev_btn.disabled  # First page, prev should be disabled
        assert not next_btn.disabled  # Not last page, next should be enabled

    @pytest.mark.asyncio
    async def test_pagination_navigation(
        self, 
        connection_panel: ConnectionPanel, 
        sample_connections: list[dict[str, Any]]
    ) -> None:
        """Test pagination navigation through multiple pages."""
        connection_panel.update_connections(sample_connections)
        
        # Test next page navigation
        next_btn = connection_panel.query_one("#next-page-btn")
        await connection_panel.press("Tab")  # Focus on next button
        await connection_panel.press("Enter")  # Click next
        
        assert connection_panel.current_page == 1
        
        # Test previous page navigation
        prev_btn = connection_panel.query_one("#prev-page-btn")
        await connection_panel.press("Tab")  # Focus on prev button
        await connection_panel.press("Enter")  # Click prev
        
        assert connection_panel.current_page == 0

    @pytest.mark.asyncio
    async def test_filter_functionality_with_page_reset(
        self, 
        connection_panel: ConnectionPanel, 
        sample_connections: list[dict[str, Any]]
    ) -> None:
        """Test filtering functionality and page reset behavior."""
        connection_panel.update_connections(sample_connections)
        
        # Navigate to page 2
        connection_panel.current_page = 1
        connection_panel._update_connections_display()
        
        # Apply filter by address
        filter_input = connection_panel.query_one("#connection-filter-input")
        await connection_panel.press("Tab")  # Focus on filter input
        await connection_panel.press("1")  # Type "1" to filter by IPs containing "1"
        
        # Verify page resets to 0
        assert connection_panel.current_page == 0
        
        # Verify filtered results
        assert len(connection_panel.filtered_connections) < len(sample_connections)
        assert all("1" in str(conn.get("client_address", "")) for conn in connection_panel.filtered_connections)
        
        # Test filter by key ID
        await connection_panel.press("Ctrl+a")  # Select all
        await connection_panel.press("key_001")  # Filter by specific key ID
        
        # Should find connections with that key ID
        assert len(connection_panel.filtered_connections) > 0
        assert all("key_001" in str(conn.get("api_key_id", "")) for conn in connection_panel.filtered_connections)

    @pytest.mark.asyncio
    async def test_disconnect_selected_connection_message_emission(
        self, 
        connection_panel: ConnectionPanel, 
        sample_connections: list[dict[str, Any]]
    ) -> None:
        """Test that selecting and disconnecting a connection emits the correct message."""
        connection_panel.update_connections(sample_connections)
        
        # Select first connection
        connections_table = connection_panel.query_one("#connections-table")
        await connection_panel.press("Tab")  # Focus on table
        await connection_panel.press("Enter")  # Select first row
        
        # Verify selection
        assert connection_panel.selected_connection is not None
        
        # Mock the message handler to capture emitted messages
        emitted_messages = []
        
        def capture_message(message: Any) -> None:
            emitted_messages.append(message)
        
        # Patch the post_message method to capture messages
        original_post_message = connection_panel.post_message
        connection_panel.post_message = capture_message
        
        try:
            # Click disconnect button
            disconnect_btn = connection_panel.query_one("#disconnect-btn")
            await connection_panel.press("Tab")  # Focus on disconnect button
            await connection_panel.press("Enter")  # Click disconnect
            
            # Verify ConnectionDisconnect message was emitted
            assert len(emitted_messages) == 1
            assert isinstance(emitted_messages[0], ConnectionDisconnect)
            assert emitted_messages[0].client_address == connection_panel.selected_connection
            
        finally:
            # Restore original method
            connection_panel.post_message = original_post_message

    @pytest.mark.asyncio
    async def test_rps_violation_columns_use_same_transform(
        self, 
        connection_panel: ConnectionPanel, 
        sample_connections: list[dict[str, Any]]
    ) -> None:
        """Test that RPS and violation columns use the same transform as render logic."""
        connection_panel.update_connections(sample_connections)
        
        # Get the first page of connections
        page_connections = connection_panel.filtered_connections[:20]
        
        # Verify that the data in the table matches the transform logic
        connections_table = connection_panel.query_one("#connections-table")
        
        for i, conn in enumerate(page_connections):
            # Get the row data from the table
            row_data = connections_table.get_row_at(i)
            
            # Verify RPS column uses the same logic as _update_connections_display
            expected_rps = str(conn.get("rps", conn.get("requests_per_second", 0)))
            assert row_data[3] == expected_rps  # RPS is column 3 (0-indexed)
            
            # Verify violations column uses the same logic
            expected_violations = str(conn.get("violations", 0))
            assert row_data[4] == expected_violations  # Violations is column 4 (0-indexed)

    @pytest.mark.asyncio
    async def test_refresh_timer_cleanup_on_unmount(
        self, 
        connection_panel: ConnectionPanel
    ) -> None:
        """Test that refresh timer is properly cleaned up on unmount."""
        # Start auto-refresh
        connection_panel._start_auto_refresh()
        
        # Verify refresh task is running
        assert connection_panel.refresh_task is not None
        assert not connection_panel.refresh_task.done()
        
        # Unmount the panel
        connection_panel.on_unmount()
        
        # Verify refresh task is cancelled
        assert connection_panel.refresh_task is None or connection_panel.refresh_task.done()

    @pytest.mark.asyncio
    async def test_api_key_display_update(
        self, 
        connection_panel: ConnectionPanel, 
        sample_api_keys: list[dict[str, Any]]
    ) -> None:
        """Test API key display update functionality."""
        connection_panel.update_api_keys(sample_api_keys)
        
        # Verify API keys table has correct number of columns
        api_keys_table = connection_panel.query_one("#api-keys-table")
        assert len(api_keys_table.columns) == 5  # Expected columns
        
        # Verify all API keys are displayed
        assert len(api_keys_table.rows) == len(sample_api_keys)
        
        # Verify first API key data is correct
        first_key = sample_api_keys[0]
        first_row = api_keys_table.get_row_at(0)
        
        assert first_row[0] == first_key["key_id"]
        assert first_row[1] == first_key["created_at"]
        assert first_row[2] == first_key["expires_at"]
        assert first_row[4] == str(first_key["active_sessions"])

    @pytest.mark.asyncio
    async def test_connection_statistics_calculation(
        self, 
        connection_panel: ConnectionPanel, 
        sample_connections: list[dict[str, Any]]
    ) -> None:
        """Test connection statistics calculation."""
        connection_panel.update_connections(sample_connections)
        
        stats = connection_panel.get_connection_statistics()
        
        # Verify basic counts
        assert stats["total_connections"] == len(sample_connections)
        assert stats["filtered_connections"] == len(sample_connections)  # No filter applied
        
        # Verify authenticated connections count
        expected_authenticated = len([c for c in sample_connections if c.get("is_authenticated", False)])
        assert stats["authenticated_connections"] == expected_authenticated
        
        # Verify violations count
        expected_violations = len([c for c in sample_connections if c.get("violations", 0) > 0])
        assert stats["connections_with_violations"] == expected_violations
        
        # Verify average RPS calculation
        total_rps = sum(c.get("rps", c.get("requests_per_second", 0)) for c in sample_connections)
        expected_avg_rps = total_rps / len(sample_connections)
        assert abs(stats["average_rps"] - expected_avg_rps) < 0.01

    @pytest.mark.asyncio
    async def test_message_handling_integration(
        self, 
        connection_panel: ConnectionPanel, 
        sample_connections: list[dict[str, Any]]
    ) -> None:
        """Test integration of message handling with real panel logic."""
        # Test ConnectionRefresh message
        connection_panel.update_connections(sample_connections)
        initial_count = len(connection_panel.connections)
        
        # Simulate refresh message
        refresh_message = ConnectionRefresh()
        connection_panel.post_message(refresh_message)
        
        # Verify connections are still there (refresh doesn't clear them)
        assert len(connection_panel.connections) == initial_count
        
        # Test ConnectionFilter message
        filter_message = ConnectionFilter("192.168.1.1")
        connection_panel.post_message(filter_message)
        
        # Verify filter was applied
        assert connection_panel.filter_text == "192.168.1.1"
        assert len(connection_panel.filtered_connections) < len(sample_connections)

    @pytest.mark.asyncio
    async def test_button_states_and_interactions(
        self, 
        connection_panel: ConnectionPanel, 
        sample_connections: list[dict[str, Any]]
    ) -> None:
        """Test button states and interactions."""
        connection_panel.update_connections(sample_connections)
        
        # Initially, disconnect button should be disabled
        disconnect_btn = connection_panel.query_one("#disconnect-btn")
        assert disconnect_btn.disabled
        
        # Select a connection
        connections_table = connection_panel.query_one("#connections-table")
        await connection_panel.press("Tab")  # Focus on table
        await connection_panel.press("Enter")  # Select first row
        
        # Disconnect button should now be enabled
        assert not disconnect_btn.disabled
        
        # Test auto-refresh toggle
        auto_refresh_btn = connection_panel.query_one("#auto-refresh-btn")
        assert auto_refresh_btn.label == "Auto Refresh"
        
        # Click auto-refresh to start it
        await connection_panel.press("Tab")  # Focus on auto-refresh button
        await connection_panel.press("Enter")  # Click auto-refresh
        
        # Button label should change
        assert auto_refresh_btn.label == "Stop Auto"
        
        # Click again to stop
        await connection_panel.press("Enter")  # Click stop auto-refresh
        assert auto_refresh_btn.label == "Auto Refresh"

    @pytest.mark.asyncio
    async def test_error_handling_in_table_update(
        self, 
        connection_panel: ConnectionPanel
    ) -> None:
        """Test error handling in table update operations."""
        # Test with malformed connection data
        malformed_connections = [
            {"client_address": "192.168.1.1"},  # Missing required fields
            {"invalid_field": "value"},  # Completely invalid
            None,  # None connection
        ]
        
        # Should not crash the panel
        connection_panel.update_connections(malformed_connections)
        
        # Panel should still be functional
        assert connection_panel.connections == malformed_connections
        assert len(connection_panel.filtered_connections) == 3  # All should be included

    @pytest.mark.asyncio
    async def test_performance_with_large_dataset(
        self, 
        connection_panel: ConnectionPanel
    ) -> None:
        """Test performance with a very large dataset."""
        # Generate a large dataset (1000+ connections)
        large_connections = []
        for i in range(1000):
            connection = {
                "client_address": f"192.168.1.{i % 255}",
                "api_key_id": f"key_{i:04d}",
                "permissions": {"read": True, "write": i % 2 == 0},
                "rps": i % 50,
                "violations": i % 10,
                "connected_at": (datetime.now() - timedelta(hours=i)).isoformat() + "Z",
                "is_authenticated": i % 3 != 0,
                "is_initialized": i % 5 != 0,
            }
            large_connections.append(connection)
        
        # Update with large dataset
        import time
        start_time = time.time()
        connection_panel.update_connections(large_connections)
        end_time = time.time()
        
        # Should complete within reasonable time (less than 1 second)
        assert (end_time - start_time) < 1.0
        
        # Verify pagination works correctly
        total_pages = (len(large_connections) + 19) // 20  # 50 pages
        assert connection_panel.current_page == 0
        assert len(connection_panel.filtered_connections) == len(large_connections)
