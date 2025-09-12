#!/usr/bin/env python3
"""Tests for live metrics panel.

This module tests the live metrics panel with boundary conditions,
display stability, and integration with the metrics subscriber.
"""

from datetime import datetime
from unittest.mock import MagicMock

from src.tui.live_metrics_panel import LiveMetricsPanel
from src.tui.metrics_formatter import FormattedMetric, ServerMetrics
from src.tui.metrics_subscriber import MetricsSubscriber, MetricsUpdate


class TestLiveMetricsPanel:
    """Test cases for LiveMetricsPanel class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.panel = LiveMetricsPanel()
        self.mock_subscriber = MagicMock(spec=MetricsSubscriber)

    def test_panel_initialization(self) -> None:
        """Test LiveMetricsPanel initialization."""
        assert self.panel.metrics_subscriber is None
        assert self.panel.current_metrics is None
        assert self.panel.update_count == 0
        assert self.panel.display_updates == 0

    def test_panel_with_subscriber_initialization(self) -> None:
        """Test LiveMetricsPanel initialization with subscriber."""
        panel = LiveMetricsPanel(metrics_subscriber=self.mock_subscriber)

        assert panel.metrics_subscriber == self.mock_subscriber
        assert panel.current_metrics is None

    def test_set_metrics_subscriber(self) -> None:
        """Test setting metrics subscriber."""
        # Initially no subscriber
        assert self.panel.metrics_subscriber is None

        # Set subscriber
        self.panel.set_metrics_subscriber(self.mock_subscriber)

        # Verify subscriber was set and subscribe was called
        assert self.panel.metrics_subscriber == self.mock_subscriber
        self.mock_subscriber.subscribe.assert_called_once_with(self.panel._on_metrics_update)

    def test_set_metrics_subscriber_replacement(self) -> None:
        """Test replacing existing metrics subscriber."""
        # Set initial subscriber
        initial_subscriber = MagicMock(spec=MetricsSubscriber)
        self.panel.set_metrics_subscriber(initial_subscriber)

        # Replace with new subscriber
        new_subscriber = MagicMock(spec=MetricsSubscriber)
        self.panel.set_metrics_subscriber(new_subscriber)

        # Verify old subscriber was unsubscribed and new one was subscribed
        initial_subscriber.unsubscribe.assert_called_once_with(self.panel._on_metrics_update)
        new_subscriber.subscribe.assert_called_once_with(self.panel._on_metrics_update)
        assert self.panel.metrics_subscriber == new_subscriber

    def test_on_metrics_update_success(self) -> None:
        """Test successful metrics update handling."""
        # Create test metrics
        connections = {"total": FormattedMetric("Total", 10, "10", "●", "normal", "connections")}
        rps = {"average": FormattedMetric("Avg", 5.0, "5.0", "●", "normal", "rps")}
        violations = {"total": FormattedMetric("Total", 0, "0", "●", "normal", "violations")}
        server_state = {
            "uptime_hours": FormattedMetric("Uptime", 1.0, "1.0h", "●", "normal", "hours")
        }

        metrics = ServerMetrics(
            timestamp=datetime.now(),
            connections=connections,
            rps=rps,
            violations=violations,
            server_state=server_state,
        )

        update = MetricsUpdate(metrics, datetime.now())

        # Handle update
        self.panel._on_metrics_update(update)

        # Verify metrics were stored
        assert self.panel.current_metrics == metrics
        assert self.panel.update_count == 1
        assert self.panel.display_updates == 1

    def test_on_metrics_update_error(self) -> None:
        """Test metrics update handling with error."""
        # Create invalid update (missing required attributes)
        update = MagicMock()
        update.metrics = None  # Invalid metrics
        update.timestamp = datetime.now()

        # Handle update (should not raise exception)
        self.panel._on_metrics_update(update)

        # Should not have updated metrics
        assert self.panel.current_metrics is None
        # Update count is incremented even on error (it's incremented before the try block)
        assert self.panel.update_count == 1

    def test_display_loading_state(self) -> None:
        """Test display loading state."""
        # Mock the widget components
        self.panel.connections_widget = MagicMock()
        self.panel.rps_widget = MagicMock()
        self.panel.violations_widget = MagicMock()
        self.panel.server_state_widget = MagicMock()

        # Set no current metrics
        self.panel.current_metrics = None

        # Update display
        self.panel._update_display()

        # Verify loading state was displayed
        self.panel.connections_widget.update.assert_called_with("Connections: Loading...")
        self.panel.rps_widget.update.assert_called_with("RPS: Loading...")
        self.panel.violations_widget.update.assert_called_with("Violations: Loading...")
        self.panel.server_state_widget.update.assert_called_with("Server State: Loading...")

    def test_display_error_state(self) -> None:
        """Test display error state."""
        # Mock the widget components
        self.panel.connections_widget = MagicMock()
        self.panel.rps_widget = MagicMock()
        self.panel.violations_widget = MagicMock()
        self.panel.server_state_widget = MagicMock()

        # Display error state
        error_message = "Test error message that is longer than 50 characters"
        self.panel._display_error_state(error_message)

        # Verify error state was displayed
        expected_error = f"Error: {error_message[:50]}..."
        self.panel.connections_widget.update.assert_called_with(f"Connections: {expected_error}")
        self.panel.rps_widget.update.assert_called_with(f"RPS: {expected_error}")
        self.panel.violations_widget.update.assert_called_with(f"Violations: {expected_error}")
        self.panel.server_state_widget.update.assert_called_with(f"Server State: {expected_error}")

    def test_update_connections_display(self) -> None:
        """Test updating connections display."""
        # Mock the connections widget
        self.panel.connections_widget = MagicMock()

        # Create test metrics with connections
        connections = {
            "total": FormattedMetric("Total", 10, "10", "●", "normal", "connections"),
            "authenticated": FormattedMetric("Auth", 8, "8", "●", "normal", "connections"),
            "violations": FormattedMetric("Violations", 2, "2", "▲", "warning", "violations"),
        }

        metrics = ServerMetrics(
            timestamp=datetime.now(),
            connections=connections,
            rps={},
            violations={},
            server_state={},
        )

        self.panel.current_metrics = metrics

        # Update connections display
        self.panel._update_connections_display()

        # Verify display was updated
        expected_lines = ["Connections:", "  ● Total: 10", "  ● Auth: 8", "  ▲ Violations: 2"]
        self.panel.connections_widget.update.assert_called_with("\n".join(expected_lines))

    def test_update_rps_display(self) -> None:
        """Test updating RPS display."""
        # Mock the RPS widget
        self.panel.rps_widget = MagicMock()

        # Create test metrics with RPS
        rps = {
            "average": FormattedMetric("Avg RPS", 15.5, "15.5", "●", "normal", "rps"),
            "peak": FormattedMetric("Peak RPS", 45.2, "45.2", "▲", "warning", "rps"),
        }

        metrics = ServerMetrics(
            timestamp=datetime.now(), connections={}, rps=rps, violations={}, server_state={}
        )

        self.panel.current_metrics = metrics

        # Update RPS display
        self.panel._update_rps_display()

        # Verify display was updated
        expected_lines = ["RPS:", "  ● Avg RPS: 15.5", "  ▲ Peak RPS: 45.2"]
        self.panel.rps_widget.update.assert_called_with("\n".join(expected_lines))

    def test_update_violations_display(self) -> None:
        """Test updating violations display."""
        # Mock the violations widget
        self.panel.violations_widget = MagicMock()

        # Create test metrics with violations
        violations = {
            "total": FormattedMetric("Total", 5, "5", "▲", "warning", "violations"),
            "rate_limit": FormattedMetric("Rate Limit", 3, "3", "●", "normal", "violations"),
            "abuse": FormattedMetric("Abuse", 2, "2", "▼", "critical", "violations"),
        }

        metrics = ServerMetrics(
            timestamp=datetime.now(), connections={}, rps={}, violations=violations, server_state={}
        )

        self.panel.current_metrics = metrics

        # Update violations display
        self.panel._update_violations_display()

        # Verify display was updated
        expected_lines = ["Violations:", "  ▲ Total: 5", "  ● Rate Limit: 3", "  ▼ Abuse: 2"]
        self.panel.violations_widget.update.assert_called_with("\n".join(expected_lines))

    def test_update_server_state_display(self) -> None:
        """Test updating server state display."""
        # Mock the server state widget
        self.panel.server_state_widget = MagicMock()

        # Create test metrics with server state
        server_state = {
            "uptime_hours": FormattedMetric("Uptime", 24.5, "24.5", "●", "normal", "hours"),
            "error_rate": FormattedMetric("Error Rate", 2.5, "2.5%", "●", "normal", "%"),
            "memory_usage": FormattedMetric("Memory", 85.0, "85.0%", "▲", "warning", "%"),
        }

        metrics = ServerMetrics(
            timestamp=datetime.now(),
            connections={},
            rps={},
            violations={},
            server_state=server_state,
        )

        self.panel.current_metrics = metrics

        # Update server state display
        self.panel._update_server_state_display()

        # Verify display was updated
        expected_lines = [
            "Server State:",
            "  ● Uptime: 24.5",
            "  ● Error Rate: 2.5%",
            "  ▲ Memory: 85.0%",
        ]
        self.panel.server_state_widget.update.assert_called_with("\n".join(expected_lines))

    def test_update_display_with_metrics(self) -> None:
        """Test updating display with valid metrics."""
        # Mock all widget components
        self.panel.header_widget = MagicMock()
        self.panel.connections_widget = MagicMock()
        self.panel.rps_widget = MagicMock()
        self.panel.violations_widget = MagicMock()
        self.panel.server_state_widget = MagicMock()

        # Create test metrics
        connections = {"total": FormattedMetric("Total", 10, "10", "●", "normal", "connections")}
        rps = {"average": FormattedMetric("Avg", 5.0, "5.0", "●", "normal", "rps")}
        violations = {"total": FormattedMetric("Total", 0, "0", "●", "normal", "violations")}
        server_state = {
            "uptime_hours": FormattedMetric("Uptime", 1.0, "1.0h", "●", "normal", "hours")
        }

        metrics = ServerMetrics(
            timestamp=datetime.now(),
            connections=connections,
            rps=rps,
            violations=violations,
            server_state=server_state,
        )

        self.panel.current_metrics = metrics

        # Update display
        self.panel._update_display()

        # Verify all widgets were updated
        self.panel.header_widget.update.assert_called_once()
        self.panel.connections_widget.update.assert_called_once()
        self.panel.rps_widget.update.assert_called_once()
        self.panel.violations_widget.update.assert_called_once()
        self.panel.server_state_widget.update.assert_called_once()

        # Verify display updates counter was incremented
        assert self.panel.display_updates == 1

    def test_update_display_error_handling(self) -> None:
        """Test error handling in display update."""
        # Mock widgets to raise exceptions
        self.panel.connections_widget = MagicMock()
        self.panel.rps_widget = MagicMock()
        self.panel.violations_widget = MagicMock()
        self.panel.server_state_widget = MagicMock()

        # Make connections widget raise exception, but others work normally
        self.panel.connections_widget.update.side_effect = Exception("Display error")

        # Create test metrics
        connections = {"total": FormattedMetric("Total", 10, "10", "●", "normal", "connections")}

        metrics = ServerMetrics(
            timestamp=datetime.now(),
            connections=connections,
            rps={},
            violations={},
            server_state={},
        )

        self.panel.current_metrics = metrics

        # Update display (should not raise exception)
        self.panel._update_display()

        # Should have attempted to update connections widget (which failed)
        # The error handling will try to update all widgets with error messages
        assert self.panel.connections_widget.update.call_count >= 1
        # Other widgets should have been updated successfully
        self.panel.rps_widget.update.assert_called_once()
        self.panel.violations_widget.update.assert_called_once()
        self.panel.server_state_widget.update.assert_called_once()

    def test_get_display_statistics(self) -> None:
        """Test getting display statistics."""
        # Set up some state
        self.panel.update_count = 5
        self.panel.display_updates = 3
        self.panel.last_update_time = datetime.now()
        self.panel.current_metrics = MagicMock()
        self.panel.metrics_subscriber = self.mock_subscriber

        stats = self.panel.get_display_statistics()

        assert stats["update_count"] == 5
        assert stats["display_updates"] == 3
        assert "last_update_time" in stats
        assert stats["has_metrics"] is True
        assert stats["subscriber_connected"] is True

    def test_force_refresh(self) -> None:
        """Test forcing a metrics refresh."""
        # Set up subscriber
        self.panel.metrics_subscriber = self.mock_subscriber

        # Force refresh
        self.panel.force_refresh()

        # Verify force_update was called
        self.mock_subscriber.force_update.assert_called_once()

    def test_force_refresh_no_subscriber(self) -> None:
        """Test forcing refresh with no subscriber."""
        # No subscriber set
        self.panel.metrics_subscriber = None

        # Force refresh (should not raise exception)
        self.panel.force_refresh()

    def test_cleanup(self) -> None:
        """Test cleanup when panel is destroyed."""
        # Set up subscriber
        self.panel.metrics_subscriber = self.mock_subscriber

        # Cleanup
        self.panel.cleanup()

        # Verify unsubscribe was called
        self.mock_subscriber.unsubscribe.assert_called_once_with(self.panel._on_metrics_update)

    def test_cleanup_no_subscriber(self) -> None:
        """Test cleanup with no subscriber."""
        # No subscriber set
        self.panel.metrics_subscriber = None

        # Cleanup (should not raise exception)
        self.panel.cleanup()

    def test_display_stability(self) -> None:
        """Test that display updates are stable and consistent."""
        # Mock all widget components
        self.panel.header_widget = MagicMock()
        self.panel.connections_widget = MagicMock()
        self.panel.rps_widget = MagicMock()
        self.panel.violations_widget = MagicMock()
        self.panel.server_state_widget = MagicMock()

        # Create test metrics
        connections = {"total": FormattedMetric("Total", 10, "10", "●", "normal", "connections")}
        rps = {"average": FormattedMetric("Avg", 5.0, "5.0", "●", "normal", "rps")}
        violations = {"total": FormattedMetric("Total", 0, "0", "●", "normal", "violations")}
        server_state = {
            "uptime_hours": FormattedMetric("Uptime", 1.0, "1.0h", "●", "normal", "hours")
        }

        metrics = ServerMetrics(
            timestamp=datetime.now(),
            connections=connections,
            rps=rps,
            violations=violations,
            server_state=server_state,
        )

        self.panel.current_metrics = metrics

        # Update display multiple times
        for _ in range(5):
            self.panel._update_display()

        # Verify all widgets were called the same number of times
        assert self.panel.header_widget.update.call_count == 5
        assert self.panel.connections_widget.update.call_count == 5
        assert self.panel.rps_widget.update.call_count == 5
        assert self.panel.violations_widget.update.call_count == 5
        assert self.panel.server_state_widget.update.call_count == 5

        # Verify display updates counter
        assert self.panel.display_updates == 5

    def test_boundary_conditions(self) -> None:
        """Test boundary conditions and edge cases."""
        # Test with empty metrics
        empty_metrics = ServerMetrics(
            timestamp=datetime.now(), connections={}, rps={}, violations={}, server_state={}
        )

        self.panel.current_metrics = empty_metrics

        # Mock widgets
        self.panel.connections_widget = MagicMock()
        self.panel.rps_widget = MagicMock()
        self.panel.violations_widget = MagicMock()
        self.panel.server_state_widget = MagicMock()

        # Update display
        self.panel._update_display()

        # Should handle empty metrics gracefully
        self.panel.connections_widget.update.assert_called_with("Connections:")
        self.panel.rps_widget.update.assert_called_with("RPS:")
        self.panel.violations_widget.update.assert_called_with("Violations:")
        self.panel.server_state_widget.update.assert_called_with("Server State:")

    def test_metrics_with_special_characters(self) -> None:
        """Test metrics with special characters in values."""
        # Mock the connections widget
        self.panel.connections_widget = MagicMock()

        # Create metrics with special characters
        connections = {
            "total": FormattedMetric("Total", 10, "10", "●", "normal", "connections"),
            "special": FormattedMetric("Special", 5, "5", "▲", "warning", "connections"),
        }

        metrics = ServerMetrics(
            timestamp=datetime.now(),
            connections=connections,
            rps={},
            violations={},
            server_state={},
        )

        self.panel.current_metrics = metrics

        # Update connections display
        self.panel._update_connections_display()

        # Verify special characters are handled correctly
        expected_lines = ["Connections:", "  ● Total: 10", "  ▲ Special: 5"]
        self.panel.connections_widget.update.assert_called_with("\n".join(expected_lines))
