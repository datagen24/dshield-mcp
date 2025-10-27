# metrics_formatter

Metrics formatter utilities for DShield MCP TUI.

This module provides immutable formatter utilities for displaying live metrics
with stable formatting and threshold cues using ASCII/Unicode characters.

## MetricThreshold

Immutable threshold configuration for metrics.

    Attributes:
        warning: Warning threshold value
        critical: Critical threshold value
        unit: Unit of measurement (e.g., 'connections', 'rps', '%')

## FormattedMetric

Immutable formatted metric data.

    Attributes:
        label: Display label for the metric
        value: Current value
        formatted_value: Formatted string representation
        threshold_cue: ASCII/Unicode threshold indicator
        status: Status level ('normal', 'warning', 'critical')
        unit: Unit of measurement

## ServerMetrics

Immutable server metrics container.

    Attributes:
        timestamp: When metrics were collected
        connections: Connection metrics
        rps: Requests per second metrics
        violations: Security violation metrics
        server_state: Server state metrics

## MetricsFormatter

Formatter for live metrics with stable formatting and threshold cues.

    This class provides immutable formatters that return stable, consistent
    formatting for metrics display with visual threshold indicators.

#### __init__

```python
def __init__(self)
```

Initialize the metrics formatter.

#### format_metric

```python
def format_metric(self, label, value, threshold, precision)
```

Format a single metric with threshold cues.

        Args:
            label: Display label for the metric
            value: Current metric value
            threshold: Threshold configuration
            precision: Decimal precision for formatting

        Returns:
            Immutable FormattedMetric instance

#### format_connections

```python
def format_connections(self, connection_stats)
```

Format connection metrics.

        Args:
            connection_stats: Raw connection statistics

        Returns:
            Dictionary of formatted connection metrics

#### format_rps

```python
def format_rps(self, rps_stats)
```

Format RPS (requests per second) metrics.

        Args:
            rps_stats: Raw RPS statistics

        Returns:
            Dictionary of formatted RPS metrics

#### format_violations

```python
def format_violations(self, violation_stats)
```

Format security violation metrics.

        Args:
            violation_stats: Raw violation statistics

        Returns:
            Dictionary of formatted violation metrics

#### format_server_state

```python
def format_server_state(self, server_stats)
```

Format server state metrics.

        Args:
            server_stats: Raw server statistics

        Returns:
            Dictionary of formatted server state metrics

#### format_all_metrics

```python
def format_all_metrics(self, raw_stats)
```

Format all server metrics into immutable containers.

        Args:
            raw_stats: Raw server statistics from all components

        Returns:
            Immutable ServerMetrics container

#### format_metrics_display

```python
def format_metrics_display(self, metrics)
```

Format metrics for display in TUI.

        Args:
            metrics: Formatted metrics container

        Returns:
            List of formatted display lines
