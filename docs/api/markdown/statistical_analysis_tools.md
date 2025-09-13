# statistical_analysis_tools

Statistical analysis and anomaly detection tools for DShield MCP.

This module provides data-driven anomaly detection utilities backed by
Elasticsearch aggregations. It supports multiple detection methods (Z-score,
IQR, Isolation Forest, and time-series analysis) and exposes flexible,
schema-based aggregation building with optional percentiles. It can generate
context pivots (drill-down query templates), calculate calibrated risk scores,
and optionally fetch small raw samples for analyst validation.

The module is optimized to avoid heavy queries by default ("fast" modes) while
allowing more robust methods (true IQR, MAD, rolling z-score, seasonality) via
config and function arguments.

Example:
    >>> tools = StatisticalAnalysisTools()
    >>> results = await tools.detect_statistical_anomalies(
    ...     time_range_hours=24,
    ...     anomaly_methods=["iqr", "time_series"],
    ...     time_series_mode="robust",
    ...     enable_iqr=True,
    ...     enable_percentiles=True,
    ... )
    >>> results["success"]
    True

## StatisticalAnalysisTools

Statistical analysis and anomaly detection utilities.

    This class encapsulates anomaly detection methods that operate over
    Elasticsearch aggregation results, with optional configuration loaded from
    the main MCP YAML config under the ``statistical_analysis`` section.

    Attributes:
        es_client (ElasticsearchClient): Client used to execute aggregations.
        user_config: User configuration manager reference.
        analysis_cfg (dict[str, Any]): Optional analysis configuration loaded
            from MCP YAML (e.g., percentiles, schema, tunables).

#### __init__

```python
def __init__(self, es_client)
```

Initialize the analysis utilities.

        Args:
            es_client (ElasticsearchClient | None): Optional Elasticsearch client.
                If omitted, a new client is created.

#### _time_series_anomalies_fast

```python
def _time_series_anomalies_fast(self, volumes, timestamps, sensitivity)
```

Compute simple mean-based deviations for a time series.

        Args:
            volumes: Sequence of counts per bucket.
            timestamps: ISO-like timestamps per bucket (or None).
            sensitivity: Threshold scaling factor (mapped to mean-deviation).

        Returns:
            List of anomaly entries with deviation metrics.

#### _time_series_anomalies_robust

```python
def _time_series_anomalies_robust(self, volumes, timestamps, sensitivity, seasonality_hour_of_day)
```

Compute robust time-series anomalies using median/MAD and rolling z-score.

        Falls back to fast mode if NumPy is unavailable.

        Args:
            volumes: Sequence of counts per bucket.
            timestamps: ISO-like timestamps per bucket (or None).
            sensitivity: Threshold for robust_z / rolling_z.
            seasonality_hour_of_day: Whether to adjust baseline by hour-of-day.

        Returns:
            List of anomaly entries with robust metrics.

#### _build_context_pivots

```python
def _build_context_pivots(self, anomalies)
```

Build ES query templates to drill down on flagged anomalies.

        Args:
            anomalies (dict[str, Any]): Combined per-method anomaly outputs.

        Returns:
            dict[str, Any]: Mapping of field name → list of ES query templates
            with placeholders (e.g., ``${start}``, ``${end}``, ``${port}``, ``${ip}``).
