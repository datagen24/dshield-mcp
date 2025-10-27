#!/usr/bin/env python3
"""Tests for metrics formatter utilities.

This module tests the metrics formatter with boundary conditions,
formatter stability, and threshold cue functionality.
"""

from datetime import datetime

import pytest

from src.tui.metrics_formatter import (
    FormattedMetric,
    MetricsFormatter,
    MetricThreshold,
    ServerMetrics,
)


class TestMetricThreshold:
    """Test cases for MetricThreshold dataclass."""

    def test_metric_threshold_creation(self) -> None:
        """Test MetricThreshold creation with valid values."""
        threshold = MetricThreshold(warning=50.0, critical=100.0, unit="connections")

        assert threshold.warning == 50.0
        assert threshold.critical == 100.0
        assert threshold.unit == "connections"

    def test_metric_threshold_immutability(self) -> None:
        """Test that MetricThreshold is immutable."""
        threshold = MetricThreshold(warning=50.0, critical=100.0, unit="connections")

        # Attempting to modify should raise AttributeError
        with pytest.raises(AttributeError):
            threshold.warning = 75.0  # type: ignore

    def test_metric_threshold_edge_cases(self) -> None:
        """Test MetricThreshold with edge case values."""
        # Zero values
        threshold = MetricThreshold(warning=0.0, critical=0.0, unit="count")
        assert threshold.warning == 0.0
        assert threshold.critical == 0.0

        # Very large values
        threshold = MetricThreshold(warning=1e6, critical=1e9, unit="bytes")
        assert threshold.warning == 1e6
        assert threshold.critical == 1e9


class TestFormattedMetric:
    """Test cases for FormattedMetric dataclass."""

    def test_formatted_metric_creation(self) -> None:
        """Test FormattedMetric creation with valid values."""
        metric = FormattedMetric(
            label="Test Metric",
            value=42.5,
            formatted_value="42.5",
            threshold_cue="●",
            status="normal",
            unit="count",
        )

        assert metric.label == "Test Metric"
        assert metric.value == 42.5
        assert metric.formatted_value == "42.5"
        assert metric.threshold_cue == "●"
        assert metric.status == "normal"
        assert metric.unit == "count"

    def test_formatted_metric_immutability(self) -> None:
        """Test that FormattedMetric is immutable."""
        metric = FormattedMetric(
            label="Test",
            value=1.0,
            formatted_value="1.0",
            threshold_cue="●",
            status="normal",
            unit="count",
        )

        # Attempting to modify should raise AttributeError
        with pytest.raises(AttributeError):
            metric.value = 2.0  # type: ignore


class TestServerMetrics:
    """Test cases for ServerMetrics dataclass."""

    def test_server_metrics_creation(self) -> None:
        """Test ServerMetrics creation with valid data."""
        timestamp = datetime.now()
        connections = {"total": FormattedMetric("Total", 10, "10", "●", "normal", "connections")}
        rps = {"average": FormattedMetric("Avg", 5.5, "5.5", "●", "normal", "rps")}
        violations = {"total": FormattedMetric("Total", 0, "0", "●", "normal", "violations")}
        server_state = {"uptime": FormattedMetric("Uptime", 1.0, "1.0h", "●", "normal", "hours")}

        metrics = ServerMetrics(
            timestamp=timestamp,
            connections=connections,
            rps=rps,
            violations=violations,
            server_state=server_state,
        )

        assert metrics.timestamp == timestamp
        assert len(metrics.connections) == 1
        assert len(metrics.rps) == 1
        assert len(metrics.violations) == 1
        assert len(metrics.server_state) == 1

    def test_server_metrics_immutability(self) -> None:
        """Test that ServerMetrics is immutable."""
        timestamp = datetime.now()
        connections = {"total": FormattedMetric("Total", 10, "10", "●", "normal", "connections")}

        metrics = ServerMetrics(
            timestamp=timestamp, connections=connections, rps={}, violations={}, server_state={}
        )

        # Attempting to modify should raise AttributeError
        with pytest.raises(AttributeError):
            metrics.timestamp = datetime.now()  # type: ignore


class TestMetricsFormatter:
    """Test cases for MetricsFormatter class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.formatter = MetricsFormatter()

    def test_format_metric_normal_status(self) -> None:
        """Test formatting metric with normal status."""
        threshold = MetricThreshold(warning=50.0, critical=100.0, unit="connections")
        metric = self.formatter.format_metric("Test", 25.0, threshold)

        assert metric.label == "Test"
        assert metric.value == 25.0
        assert metric.status == "normal"
        assert metric.threshold_cue == "●"
        assert metric.unit == "connections"

    def test_format_metric_warning_status(self) -> None:
        """Test formatting metric with warning status."""
        threshold = MetricThreshold(warning=50.0, critical=100.0, unit="connections")
        metric = self.formatter.format_metric("Test", 75.0, threshold)

        assert metric.value == 75.0
        assert metric.status == "warning"
        assert metric.threshold_cue == "▲"

    def test_format_metric_critical_status(self) -> None:
        """Test formatting metric with critical status."""
        threshold = MetricThreshold(warning=50.0, critical=100.0, unit="connections")
        metric = self.formatter.format_metric("Test", 150.0, threshold)

        assert metric.value == 150.0
        assert metric.status == "critical"
        assert metric.threshold_cue == "▼"

    def test_format_metric_boundary_values(self) -> None:
        """Test formatting metric with boundary threshold values."""
        threshold = MetricThreshold(warning=50.0, critical=100.0, unit="connections")

        # Exactly at warning threshold
        metric = self.formatter.format_metric("Test", 50.0, threshold)
        assert metric.status == "warning"

        # Exactly at critical threshold
        metric = self.formatter.format_metric("Test", 100.0, threshold)
        assert metric.status == "critical"

    def test_format_metric_precision(self) -> None:
        """Test formatting metric with different precision values."""
        threshold = MetricThreshold(warning=50.0, critical=100.0, unit="rps")

        # Test with 0 decimal places
        metric = self.formatter.format_metric("Test", 25.7, threshold, precision=0)
        assert metric.formatted_value == "26"

        # Test with 2 decimal places
        metric = self.formatter.format_metric("Test", 25.7, threshold, precision=2)
        assert metric.formatted_value == "25.70"

    def test_format_metric_percentage_unit(self) -> None:
        """Test formatting metric with percentage unit."""
        threshold = MetricThreshold(warning=80.0, critical=95.0, unit="%")
        metric = self.formatter.format_metric("CPU", 85.5, threshold)

        assert metric.formatted_value == "85.5%"
        assert metric.unit == "%"

    def test_format_connections(self) -> None:
        """Test formatting connection metrics."""
        connection_stats = {
            "total_connections": 25,
            "authenticated_connections": 20,
            "connections_with_violations": 2,
        }

        metrics = self.formatter.format_connections(connection_stats)

        assert "total" in metrics
        assert "authenticated" in metrics
        assert "violations" in metrics

        assert metrics["total"].value == 25
        assert metrics["authenticated"].value == 20
        assert metrics["violations"].value == 2

    def test_format_connections_missing_data(self) -> None:
        """Test formatting connections with missing data."""
        connection_stats = {}  # Empty stats

        metrics = self.formatter.format_connections(connection_stats)

        # Should handle missing data gracefully
        assert metrics["total"].value == 0
        assert metrics["authenticated"].value == 0
        assert metrics["violations"].value == 0

    def test_format_rps(self) -> None:
        """Test formatting RPS metrics."""
        rps_stats = {"average_rps": 15.5, "peak_rps": 45.2}

        metrics = self.formatter.format_rps(rps_stats)

        assert "average" in metrics
        assert "peak" in metrics

        assert metrics["average"].value == 15.5
        assert metrics["peak"].value == 45.2

    def test_format_violations(self) -> None:
        """Test formatting violation metrics."""
        violation_stats = {"total_violations": 5, "rate_limit_violations": 3, "abuse_violations": 2}

        metrics = self.formatter.format_violations(violation_stats)

        assert "total" in metrics
        assert "rate_limit" in metrics
        assert "abuse" in metrics

        assert metrics["total"].value == 5
        assert metrics["rate_limit"].value == 3
        assert metrics["abuse"].value == 2

    def test_format_server_state(self) -> None:
        """Test formatting server state metrics."""
        server_stats = {
            "uptime_seconds": 3600,  # 1 hour
            "error_rate": 2.5,
            "memory_usage_percent": 75.0,
        }

        metrics = self.formatter.format_server_state(server_stats)

        assert "uptime_hours" in metrics
        assert "error_rate" in metrics
        assert "memory_usage" in metrics

        assert metrics["uptime_hours"].value == 1.0  # 3600 seconds = 1 hour
        assert metrics["error_rate"].value == 2.5
        assert metrics["memory_usage"].value == 75.0

    def test_format_all_metrics(self) -> None:
        """Test formatting all metrics together."""
        raw_stats = {
            "connections": {"active": 10},
            "connection_manager": {"connections": {"active": 8}},
            "security": {"abuse_detection": {"total_violations": 2, "blocked_clients": 1}},
            "server": {"is_running": True},
        }

        metrics = self.formatter.format_all_metrics(raw_stats)

        assert isinstance(metrics, ServerMetrics)
        assert metrics.timestamp is not None
        assert len(metrics.connections) > 0
        assert len(metrics.rps) > 0
        assert len(metrics.violations) > 0
        assert len(metrics.server_state) > 0

    def test_format_metrics_display(self) -> None:
        """Test formatting metrics for display."""
        timestamp = datetime.now()
        connections = {"total": FormattedMetric("Total", 10, "10", "●", "normal", "connections")}
        rps = {"average": FormattedMetric("Avg", 5.5, "5.5", "●", "normal", "rps")}
        violations = {"total": FormattedMetric("Total", 0, "0", "●", "normal", "violations")}
        server_state = {"uptime": FormattedMetric("Uptime", 1.0, "1.0h", "●", "normal", "hours")}

        metrics = ServerMetrics(
            timestamp=timestamp,
            connections=connections,
            rps=rps,
            violations=violations,
            server_state=server_state,
        )

        display_lines = self.formatter.format_metrics_display(metrics)

        assert len(display_lines) > 0
        assert "Metrics [" in display_lines[0]
        assert "Connections:" in display_lines
        assert "RPS:" in display_lines
        assert "Violations:" in display_lines
        assert "Server State:" in display_lines

    def test_formatter_stability(self) -> None:
        """Test that formatter produces stable output."""
        threshold = MetricThreshold(warning=50.0, critical=100.0, unit="connections")

        # Format the same metric multiple times
        results = []
        for _ in range(10):
            metric = self.formatter.format_metric("Test", 25.0, threshold)
            results.append(metric)

        # All results should be identical
        first_result = results[0]
        for result in results[1:]:
            assert result.label == first_result.label
            assert result.value == first_result.value
            assert result.formatted_value == first_result.formatted_value
            assert result.threshold_cue == first_result.threshold_cue
            assert result.status == first_result.status
            assert result.unit == first_result.unit

    def test_threshold_cue_consistency(self) -> None:
        """Test that threshold cues are consistent across different metrics."""
        threshold = MetricThreshold(warning=50.0, critical=100.0, unit="test")

        # Test all status levels
        normal_metric = self.formatter.format_metric("Normal", 25.0, threshold)
        warning_metric = self.formatter.format_metric("Warning", 75.0, threshold)
        critical_metric = self.formatter.format_metric("Critical", 150.0, threshold)

        assert normal_metric.threshold_cue == "●"
        assert warning_metric.threshold_cue == "▲"
        assert critical_metric.threshold_cue == "▼"

    def test_edge_case_values(self) -> None:
        """Test formatter with edge case values."""
        threshold = MetricThreshold(warning=0.0, critical=0.0, unit="count")

        # Zero value
        metric = self.formatter.format_metric("Zero", 0.0, threshold)
        assert metric.value == 0.0
        assert metric.status == "critical"  # 0.0 >= 0.0 is True, so critical

        # Negative value
        metric = self.formatter.format_metric("Negative", -5.0, threshold)
        assert metric.value == -5.0
        assert metric.status == "normal"  # Negative values are below thresholds

        # Very large value
        threshold = MetricThreshold(warning=1e6, critical=1e9, unit="bytes")
        metric = self.formatter.format_metric("Large", 1e8, threshold)
        assert metric.value == 1e8
        assert metric.status == "warning"  # Between warning and critical
