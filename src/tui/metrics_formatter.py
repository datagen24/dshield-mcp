#!/usr/bin/env python3
"""Metrics formatter utilities for DShield MCP TUI.

This module provides immutable formatter utilities for displaying live metrics
with stable formatting and threshold cues using ASCII/Unicode characters.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, ClassVar

import structlog

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class MetricThreshold:
    """Immutable threshold configuration for metrics.

    Attributes:
        warning: Warning threshold value
        critical: Critical threshold value
        unit: Unit of measurement (e.g., 'connections', 'rps', '%')
    """

    warning: float
    critical: float
    unit: str


@dataclass(frozen=True)
class FormattedMetric:
    """Immutable formatted metric data.

    Attributes:
        label: Display label for the metric
        value: Current value
        formatted_value: Formatted string representation
        threshold_cue: ASCII/Unicode threshold indicator
        status: Status level ('normal', 'warning', 'critical')
        unit: Unit of measurement
    """

    label: str
    value: float
    formatted_value: str
    threshold_cue: str
    status: str
    unit: str


@dataclass(frozen=True)
class ServerMetrics:
    """Immutable server metrics container.

    Attributes:
        timestamp: When metrics were collected
        connections: Connection metrics
        rps: Requests per second metrics
        violations: Security violation metrics
        server_state: Server state metrics
    """

    timestamp: datetime
    connections: dict[str, FormattedMetric]
    rps: dict[str, FormattedMetric]
    violations: dict[str, FormattedMetric]
    server_state: dict[str, FormattedMetric]


class MetricsFormatter:
    """Formatter for live metrics with stable formatting and threshold cues.

    This class provides immutable formatters that return stable, consistent
    formatting for metrics display with visual threshold indicators.
    """

    # Threshold configurations
    CONNECTION_THRESHOLDS: ClassVar[dict[str, MetricThreshold]] = {
        "total": MetricThreshold(warning=50, critical=100, unit="connections"),
        "authenticated": MetricThreshold(warning=40, critical=80, unit="connections"),
        "violations": MetricThreshold(warning=5, critical=10, unit="violations"),
    }

    RPS_THRESHOLDS: ClassVar[dict[str, MetricThreshold]] = {
        "average": MetricThreshold(warning=100, critical=200, unit="rps"),
        "peak": MetricThreshold(warning=150, critical=300, unit="rps"),
    }

    VIOLATION_THRESHOLDS: ClassVar[dict[str, MetricThreshold]] = {
        "total": MetricThreshold(warning=10, critical=25, unit="violations"),
        "rate_limit": MetricThreshold(warning=5, critical=15, unit="violations"),
        "abuse": MetricThreshold(warning=3, critical=8, unit="violations"),
    }

    SERVER_STATE_THRESHOLDS: ClassVar[dict[str, MetricThreshold]] = {
        "uptime_hours": MetricThreshold(warning=24, critical=168, unit="hours"),
        "error_rate": MetricThreshold(warning=5.0, critical=10.0, unit="%"),
        "memory_usage": MetricThreshold(warning=80.0, critical=95.0, unit="%"),
    }

    # Threshold cue characters
    THRESHOLD_CUES: ClassVar[dict[str, str]] = {
        "normal": "●",  # Green circle
        "warning": "▲",  # Yellow triangle
        "critical": "▼",  # Red triangle down
        "unknown": "?",  # Question mark
    }

    def __init__(self) -> None:
        """Initialize the metrics formatter."""
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")

    def format_metric(
        self, label: str, value: float, threshold: MetricThreshold, precision: int = 1
    ) -> FormattedMetric:
        """Format a single metric with threshold cues.

        Args:
            label: Display label for the metric
            value: Current metric value
            threshold: Threshold configuration
            precision: Decimal precision for formatting

        Returns:
            Immutable FormattedMetric instance
        """
        # Determine status based on thresholds
        if value >= threshold.critical:
            status = "critical"
        elif value >= threshold.warning:
            status = "warning"
        else:
            status = "normal"

        # Get threshold cue
        threshold_cue = self.THRESHOLD_CUES.get(status, self.THRESHOLD_CUES["unknown"])

        # Format value based on type
        if threshold.unit == "%":
            formatted_value = f"{value:.{precision}f}%"
        elif threshold.unit in ["connections", "violations", "rps"]:
            formatted_value = f"{value:.{precision}f}"
        else:
            formatted_value = f"{value:.{precision}f} {threshold.unit}"

        return FormattedMetric(
            label=label,
            value=value,
            formatted_value=formatted_value,
            threshold_cue=threshold_cue,
            status=status,
            unit=threshold.unit,
        )

    def format_connections(self, connection_stats: dict[str, Any]) -> dict[str, FormattedMetric]:
        """Format connection metrics.

        Args:
            connection_stats: Raw connection statistics

        Returns:
            Dictionary of formatted connection metrics
        """
        metrics = {}

        # Total connections
        total = connection_stats.get("total_connections", 0)
        metrics["total"] = self.format_metric(
            "Total", total, self.CONNECTION_THRESHOLDS["total"], precision=0
        )

        # Authenticated connections
        authenticated = connection_stats.get("authenticated_connections", 0)
        metrics["authenticated"] = self.format_metric(
            "Auth", authenticated, self.CONNECTION_THRESHOLDS["authenticated"], precision=0
        )

        # Connections with violations
        violations = connection_stats.get("connections_with_violations", 0)
        metrics["violations"] = self.format_metric(
            "Violations", violations, self.CONNECTION_THRESHOLDS["violations"], precision=0
        )

        return metrics

    def format_rps(self, rps_stats: dict[str, Any]) -> dict[str, FormattedMetric]:
        """Format RPS (requests per second) metrics.

        Args:
            rps_stats: Raw RPS statistics

        Returns:
            Dictionary of formatted RPS metrics
        """
        metrics = {}

        # Average RPS
        average = rps_stats.get("average_rps", 0.0)
        metrics["average"] = self.format_metric(
            "Avg RPS", average, self.RPS_THRESHOLDS["average"], precision=1
        )

        # Peak RPS (if available)
        peak = rps_stats.get("peak_rps", 0.0)
        metrics["peak"] = self.format_metric(
            "Peak RPS", peak, self.RPS_THRESHOLDS["peak"], precision=1
        )

        return metrics

    def format_violations(self, violation_stats: dict[str, Any]) -> dict[str, FormattedMetric]:
        """Format security violation metrics.

        Args:
            violation_stats: Raw violation statistics

        Returns:
            Dictionary of formatted violation metrics
        """
        metrics = {}

        # Total violations
        total = violation_stats.get("total_violations", 0)
        metrics["total"] = self.format_metric(
            "Total", total, self.VIOLATION_THRESHOLDS["total"], precision=0
        )

        # Rate limit violations
        rate_limit = violation_stats.get("rate_limit_violations", 0)
        metrics["rate_limit"] = self.format_metric(
            "Rate Limit", rate_limit, self.VIOLATION_THRESHOLDS["rate_limit"], precision=0
        )

        # Abuse violations
        abuse = violation_stats.get("abuse_violations", 0)
        metrics["abuse"] = self.format_metric(
            "Abuse", abuse, self.VIOLATION_THRESHOLDS["abuse"], precision=0
        )

        return metrics

    def format_server_state(self, server_stats: dict[str, Any]) -> dict[str, FormattedMetric]:
        """Format server state metrics.

        Args:
            server_stats: Raw server statistics

        Returns:
            Dictionary of formatted server state metrics
        """
        metrics = {}

        # Server uptime (convert to hours)
        uptime_seconds = server_stats.get("uptime_seconds", 0)
        uptime_hours = uptime_seconds / 3600.0
        metrics["uptime_hours"] = self.format_metric(
            "Uptime", uptime_hours, self.SERVER_STATE_THRESHOLDS["uptime_hours"], precision=1
        )

        # Error rate
        error_rate = server_stats.get("error_rate", 0.0)
        metrics["error_rate"] = self.format_metric(
            "Error Rate", error_rate, self.SERVER_STATE_THRESHOLDS["error_rate"], precision=1
        )

        # Memory usage (if available)
        memory_usage = server_stats.get("memory_usage_percent", 0.0)
        metrics["memory_usage"] = self.format_metric(
            "Memory", memory_usage, self.SERVER_STATE_THRESHOLDS["memory_usage"], precision=1
        )

        return metrics

    def format_all_metrics(self, raw_stats: dict[str, Any]) -> ServerMetrics:
        """Format all server metrics into immutable containers.

        Args:
            raw_stats: Raw server statistics from all components

        Returns:
            Immutable ServerMetrics container
        """
        timestamp = datetime.now()

        # Extract connection statistics
        connection_stats = raw_stats.get("connections", {})
        connection_manager_stats = raw_stats.get("connection_manager", {})

        # Combine connection data
        combined_connection_stats = {
            "total_connections": connection_stats.get("active", 0),
            "authenticated_connections": connection_manager_stats.get("connections", {}).get(
                "active", 0
            ),
            "connections_with_violations": 0,  # Will be calculated from individual connections
        }

        # Extract RPS statistics
        rps_stats = {
            "average_rps": 0.0,  # Will be calculated from connections
            "peak_rps": 0.0,  # Will be calculated from connections
        }

        # Extract violation statistics
        security_stats = raw_stats.get("security", {})
        abuse_detection = security_stats.get("abuse_detection", {})
        violation_stats = {
            "total_violations": abuse_detection.get("total_violations", 0),
            "rate_limit_violations": 0,  # Will be calculated from rate limiting stats
            "abuse_violations": abuse_detection.get("blocked_clients", 0),
        }

        # Extract server state statistics
        _server_info = raw_stats.get("server", {})
        server_state_stats = {
            "uptime_seconds": 0,  # Will be calculated from server start time
            "error_rate": 0.0,  # Will be calculated from error statistics
            "memory_usage_percent": 0.0,  # System memory usage
        }

        # Format all metrics
        connections = self.format_connections(combined_connection_stats)
        rps = self.format_rps(rps_stats)
        violations = self.format_violations(violation_stats)
        server_state = self.format_server_state(server_state_stats)

        return ServerMetrics(
            timestamp=timestamp,
            connections=connections,
            rps=rps,
            violations=violations,
            server_state=server_state,
        )

    def format_metrics_display(self, metrics: ServerMetrics) -> list[str]:
        """Format metrics for display in TUI.

        Args:
            metrics: Formatted metrics container

        Returns:
            List of formatted display lines
        """
        lines = []

        # Header with timestamp
        timestamp_str = metrics.timestamp.strftime("%H:%M:%S")
        lines.append(f"Metrics [{timestamp_str}]")
        lines.append("─" * 20)

        # Connections section
        lines.append("Connections:")
        for _key, metric in metrics.connections.items():
            lines.append(f"  {metric.threshold_cue} {metric.label}: {metric.formatted_value}")

        # RPS section
        lines.append("RPS:")
        for _key, metric in metrics.rps.items():
            lines.append(f"  {metric.threshold_cue} {metric.label}: {metric.formatted_value}")

        # Violations section
        lines.append("Violations:")
        for _key, metric in metrics.violations.items():
            lines.append(f"  {metric.threshold_cue} {metric.label}: {metric.formatted_value}")

        # Server state section
        lines.append("Server State:")
        for _key, metric in metrics.server_state.items():
            lines.append(f"  {metric.threshold_cue} {metric.label}: {metric.formatted_value}")

        return lines
