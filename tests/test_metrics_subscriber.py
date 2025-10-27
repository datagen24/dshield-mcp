#!/usr/bin/env python3
"""Tests for metrics subscription system.

This module tests the metrics subscriber with boundary conditions,
subscription/unsubscription lifecycle, and performance characteristics.
"""

import asyncio
from datetime import datetime
from typing import Any

import pytest

from src.tui.metrics_formatter import ServerMetrics
from src.tui.metrics_subscriber import MetricsSubscriber, MetricsUpdate


class TestMetricsSubscriber:
    """Test cases for MetricsSubscriber class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.subscriber = MetricsSubscriber(update_interval=0.1, max_subscribers=5)
        self.metrics_collector_calls: list[dict[str, Any]] = []

    def _mock_metrics_collector(self, return_value: dict[str, Any] | None = None) -> None:
        """Create a mock metrics collector that tracks calls."""

        def collector() -> dict[str, Any]:
            self.metrics_collector_calls.append({"timestamp": datetime.now()})
            return return_value or {
                "connections": {"active": 5},
                "security": {"abuse_detection": {"total_violations": 0}},
                "server": {"is_running": True},
            }

        self.subscriber.set_metrics_collector(collector)

    def test_subscriber_initialization(self) -> None:
        """Test MetricsSubscriber initialization."""
        assert self.subscriber.update_interval == 0.1
        assert self.subscriber.max_subscribers == 5
        assert not self.subscriber.is_running
        assert len(self.subscriber.subscribers) == 0
        assert self.subscriber.metrics_collector is None

    def test_set_metrics_collector(self) -> None:
        """Test setting the metrics collector function."""

        def test_collector() -> dict[str, Any]:
            return {"test": "data"}

        self.subscriber.set_metrics_collector(test_collector)
        assert self.subscriber.metrics_collector == test_collector

    def test_subscribe_success(self) -> None:
        """Test successful subscription."""

        def test_callback(update: MetricsUpdate) -> None:
            pass

        result = self.subscriber.subscribe(test_callback)

        assert result is True
        assert test_callback in self.subscriber.subscribers
        assert len(self.subscriber.subscribers) == 1

    def test_subscribe_at_capacity(self) -> None:
        """Test subscription when at maximum capacity."""
        # Fill up to capacity
        for _i in range(self.subscriber.max_subscribers):

            def callback(update: MetricsUpdate) -> None:
                pass

            self.subscriber.subscribe(callback)

        # Try to subscribe one more
        def extra_callback(update: MetricsUpdate) -> None:
            pass

        result = self.subscriber.subscribe(extra_callback)

        assert result is False
        assert extra_callback not in self.subscriber.subscribers
        assert len(self.subscriber.subscribers) == self.subscriber.max_subscribers

    def test_unsubscribe_success(self) -> None:
        """Test successful unsubscription."""

        def test_callback(update: MetricsUpdate) -> None:
            pass

        # Subscribe first
        self.subscriber.subscribe(test_callback)
        assert len(self.subscriber.subscribers) == 1

        # Unsubscribe
        result = self.subscriber.unsubscribe(test_callback)

        assert result is True
        assert test_callback not in self.subscriber.subscribers
        assert len(self.subscriber.subscribers) == 0

    def test_unsubscribe_not_found(self) -> None:
        """Test unsubscription of unknown callback."""

        def test_callback(update: MetricsUpdate) -> None:
            pass

        result = self.subscriber.unsubscribe(test_callback)

        assert result is False
        assert len(self.subscriber.subscribers) == 0

    @pytest.mark.asyncio
    async def test_start_without_collector(self) -> None:
        """Test starting subscriber without metrics collector."""
        await self.subscriber.start()

        # Should not be running because no collector was set
        assert not self.subscriber.is_running

    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(self) -> None:
        """Test start and stop lifecycle."""
        self._mock_metrics_collector()

        # Start subscriber
        await self.subscriber.start()
        assert self.subscriber.is_running

        # Let it run briefly
        await asyncio.sleep(0.2)

        # Stop subscriber
        await self.subscriber.stop()
        assert not self.subscriber.is_running

    @pytest.mark.asyncio
    async def test_metrics_collection_and_distribution(self) -> None:
        """Test metrics collection and distribution to subscribers."""
        received_updates: list[MetricsUpdate] = []

        def test_callback(update: MetricsUpdate) -> None:
            received_updates.append(update)

        # Set up subscriber
        self.subscriber.subscribe(test_callback)
        self._mock_metrics_collector()

        # Start subscriber
        await self.subscriber.start()

        # Let it collect metrics
        await asyncio.sleep(0.3)

        # Stop subscriber
        await self.subscriber.stop()

        # Verify metrics were collected and distributed
        assert len(self.metrics_collector_calls) > 0
        assert len(received_updates) > 0

        # Verify update structure
        for update in received_updates:
            assert isinstance(update, MetricsUpdate)
            assert isinstance(update.metrics, ServerMetrics)
            assert isinstance(update.timestamp, datetime)

    @pytest.mark.asyncio
    async def test_subscriber_error_handling(self) -> None:
        """Test error handling in metrics collection."""

        def failing_collector() -> dict[str, Any]:
            raise ValueError("Test error")

        received_updates: list[MetricsUpdate] = []

        def test_callback(update: MetricsUpdate) -> None:
            received_updates.append(update)

        # Set up subscriber with failing collector
        self.subscriber.subscribe(test_callback)
        self.subscriber.set_metrics_collector(failing_collector)

        # Start subscriber
        await self.subscriber.start()

        # Let it try to collect metrics
        await asyncio.sleep(0.3)

        # Stop subscriber
        await self.subscriber.stop()

        # Should not have received any updates due to errors
        assert len(received_updates) == 0

    @pytest.mark.asyncio
    async def test_subscriber_callback_error_handling(self) -> None:
        """Test error handling when subscriber callback fails."""

        def test_callback(update: MetricsUpdate) -> None:
            raise RuntimeError("Callback error")

        # Set up subscriber
        self.subscriber.subscribe(test_callback)
        self._mock_metrics_collector()

        # Start subscriber
        await self.subscriber.start()

        # Let it collect metrics
        await asyncio.sleep(0.3)

        # Stop subscriber
        await self.subscriber.stop()

        # Should have collected metrics despite callback errors
        assert len(self.metrics_collector_calls) > 0

    def test_should_update_subscribers_no_previous_metrics(self) -> None:
        """Test should_update_subscribers with no previous metrics."""
        # Create test metrics
        from src.tui.metrics_formatter import FormattedMetric

        connections = {"total": FormattedMetric("Total", 10, "10", "●", "normal", "connections")}
        rps = {"average": FormattedMetric("Avg", 5.0, "5.0", "●", "normal", "rps")}
        violations = {"total": FormattedMetric("Total", 0, "0", "●", "normal", "violations")}
        server_state = {
            "uptime_hours": FormattedMetric("Uptime", 1.0, "1.0h", "●", "normal", "hours")
        }

        new_metrics = ServerMetrics(
            timestamp=datetime.now(),
            connections=connections,
            rps=rps,
            violations=violations,
            server_state=server_state,
        )

        # With no previous metrics, should update
        assert self.subscriber._should_update_subscribers(new_metrics) is True

    def test_should_update_subscribers_significant_changes(self) -> None:
        """Test should_update_subscribers with significant changes."""
        from src.tui.metrics_formatter import FormattedMetric

        # Create initial metrics
        initial_connections = {
            "total": FormattedMetric("Total", 10, "10", "●", "normal", "connections")
        }
        initial_rps = {"average": FormattedMetric("Avg", 5.0, "5.0", "●", "normal", "rps")}
        initial_violations = {
            "total": FormattedMetric("Total", 0, "0", "●", "normal", "violations")
        }
        initial_server_state = {
            "uptime_hours": FormattedMetric("Uptime", 1.0, "1.0h", "●", "normal", "hours")
        }

        initial_metrics = ServerMetrics(
            timestamp=datetime.now(),
            connections=initial_connections,
            rps=initial_rps,
            violations=initial_violations,
            server_state=initial_server_state,
        )

        self.subscriber.last_metrics = initial_metrics

        # Create new metrics with significant changes
        new_connections = {
            "total": FormattedMetric("Total", 15, "15", "●", "normal", "connections")  # +5
        }
        new_rps = {
            "average": FormattedMetric("Avg", 5.2, "5.2", "●", "normal", "rps")  # +0.2
        }
        new_violations = {
            "total": FormattedMetric("Total", 1, "1", "●", "normal", "violations")  # +1
        }
        new_server_state = {
            "uptime_hours": FormattedMetric("Uptime", 1.1, "1.1h", "●", "normal", "hours")  # +0.1
        }

        new_metrics = ServerMetrics(
            timestamp=datetime.now(),
            connections=new_connections,
            rps=new_rps,
            violations=new_violations,
            server_state=new_server_state,
        )

        # Should update due to significant changes
        assert self.subscriber._should_update_subscribers(new_metrics) is True

    def test_should_update_subscribers_insignificant_changes(self) -> None:
        """Test should_update_subscribers with insignificant changes."""
        from src.tui.metrics_formatter import FormattedMetric

        # Create initial metrics
        initial_connections = {
            "total": FormattedMetric("Total", 10, "10", "●", "normal", "connections")
        }
        initial_rps = {"average": FormattedMetric("Avg", 5.0, "5.0", "●", "normal", "rps")}
        initial_violations = {
            "total": FormattedMetric("Total", 0, "0", "●", "normal", "violations")
        }
        initial_server_state = {
            "uptime_hours": FormattedMetric("Uptime", 1.0, "1.0h", "●", "normal", "hours")
        }

        initial_metrics = ServerMetrics(
            timestamp=datetime.now(),
            connections=initial_connections,
            rps=initial_rps,
            violations=initial_violations,
            server_state=initial_server_state,
        )

        self.subscriber.last_metrics = initial_metrics

        # Create new metrics with insignificant changes
        new_connections = {
            "total": FormattedMetric("Total", 10, "10", "●", "normal", "connections")  # No change
        }
        new_rps = {
            "average": FormattedMetric(
                "Avg", 5.05, "5.05", "●", "normal", "rps"
            )  # +0.05 (below threshold)
        }
        new_violations = {
            "total": FormattedMetric("Total", 0, "0", "●", "normal", "violations")  # No change
        }
        new_server_state = {
            "uptime_hours": FormattedMetric(
                "Uptime", 1.05, "1.05h", "●", "normal", "hours"
            )  # +0.05 (below threshold)
        }

        new_metrics = ServerMetrics(
            timestamp=datetime.now(),
            connections=new_connections,
            rps=new_rps,
            violations=new_violations,
            server_state=new_server_state,
        )

        # Should not update due to insignificant changes
        assert self.subscriber._should_update_subscribers(new_metrics) is False

    def test_performance_stats_tracking(self) -> None:
        """Test performance statistics tracking."""
        # Simulate some updates
        self.subscriber.update_count = 5
        self.subscriber.last_update_time = datetime.now()
        self.subscriber.average_update_duration = 0.05

        stats = self.subscriber.get_performance_stats()

        assert stats["is_running"] == self.subscriber.is_running
        assert stats["subscriber_count"] == len(self.subscriber.subscribers)
        assert stats["update_count"] == 5
        assert stats["average_update_duration"] == 0.05
        assert stats["update_interval"] == 0.1

    def test_get_current_metrics(self) -> None:
        """Test getting current metrics."""
        # Initially no metrics
        assert self.subscriber.get_current_metrics() is None

        # Set some metrics
        from src.tui.metrics_formatter import FormattedMetric, ServerMetrics

        connections = {"total": FormattedMetric("Total", 10, "10", "●", "normal", "connections")}

        metrics = ServerMetrics(
            timestamp=datetime.now(),
            connections=connections,
            rps={},
            violations={},
            server_state={},
        )

        self.subscriber.last_metrics = metrics

        # Should return the metrics
        current = self.subscriber.get_current_metrics()
        assert current == metrics

    @pytest.mark.asyncio
    async def test_force_update(self) -> None:
        """Test forcing an immediate update."""
        received_updates: list[MetricsUpdate] = []

        def test_callback(update: MetricsUpdate) -> None:
            received_updates.append(update)

        # Set up subscriber
        self.subscriber.subscribe(test_callback)
        self._mock_metrics_collector()

        # Start subscriber first (force_update only works when running)
        await self.subscriber.start()

        # Force update
        self.subscriber.force_update()

        # Wait for the update to complete
        await asyncio.sleep(0.2)

        # Stop subscriber
        await self.subscriber.stop()

        # Should have received an update
        assert len(received_updates) > 0
        assert len(self.metrics_collector_calls) > 0

    @pytest.mark.asyncio
    async def test_concurrent_subscribers(self) -> None:
        """Test handling multiple concurrent subscribers."""
        received_updates: list[list[MetricsUpdate]] = []

        # Create multiple subscribers
        for _i in range(3):
            updates: list[MetricsUpdate] = []
            received_updates.append(updates)

            def make_callback(updates_list: list[MetricsUpdate]) -> None:
                def callback(update: MetricsUpdate) -> None:
                    updates_list.append(update)

                return callback

            self.subscriber.subscribe(make_callback(updates))

        # Set up subscriber
        self._mock_metrics_collector()

        # Start subscriber
        await self.subscriber.start()

        # Let it collect metrics
        await asyncio.sleep(0.3)

        # Stop subscriber
        await self.subscriber.stop()

        # All subscribers should have received updates
        for updates in received_updates:
            assert len(updates) > 0

    def test_boundary_conditions(self) -> None:
        """Test boundary conditions and edge cases."""
        # Test with zero update interval
        subscriber = MetricsSubscriber(update_interval=0.0, max_subscribers=1)
        assert subscriber.update_interval == 0.0

        # Test with very large update interval
        subscriber = MetricsSubscriber(update_interval=3600.0, max_subscribers=1)
        assert subscriber.update_interval == 3600.0

        # Test with zero max subscribers
        subscriber = MetricsSubscriber(update_interval=1.0, max_subscribers=0)
        assert subscriber.max_subscribers == 0

        # Should not be able to subscribe with zero max subscribers
        def test_callback(update: MetricsUpdate) -> None:
            pass

        result = subscriber.subscribe(test_callback)
        assert result is False
