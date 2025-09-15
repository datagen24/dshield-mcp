#!/usr/bin/env python3
"""Statistical analysis and anomaly detection tools for DShield MCP.

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
"""

import time
from datetime import UTC, datetime
from typing import Any

import structlog

from .config_loader import get_config
from .elasticsearch_client import ElasticsearchClient
from .user_config import get_user_config

logger = structlog.get_logger(__name__)


class StatisticalAnalysisTools:
    """Statistical analysis and anomaly detection utilities.

    This class encapsulates anomaly detection methods that operate over
    Elasticsearch aggregation results, with optional configuration loaded from
    the main MCP YAML config under the ``statistical_analysis`` section.

    Attributes:
        es_client (ElasticsearchClient): Client used to execute aggregations.
        user_config: User configuration manager reference.
        analysis_cfg (dict[str, Any]): Optional analysis configuration loaded
            from MCP YAML (e.g., percentiles, schema, tunables).
    """

    def __init__(self, es_client: ElasticsearchClient | None = None):
        """Initialize the analysis utilities.

        Args:
            es_client (ElasticsearchClient | None): Optional Elasticsearch client.
                If omitted, a new client is created.
        """
        self.es_client = es_client or ElasticsearchClient()
        self.user_config = get_user_config()
        # Optional analysis configuration (schema, toggles) from main YAML
        try:
            cfg = get_config()
            self.analysis_cfg = cfg.get("statistical_analysis", {})
        except Exception:
            self.analysis_cfg = {}

    async def detect_statistical_anomalies(
        self,
        time_range_hours: int = 24,
        anomaly_methods: list[str] | None = None,
        sensitivity: float = 2.5,
        dimensions: list[str] | None = None,
        return_summary_only: bool = True,
        max_anomalies: int = 50,
        dimension_schema: dict[str, Any] | None = None,
        enable_iqr: bool | None = None,
        enable_percentiles: bool | None = None,
        time_series_mode: str = "fast",
        seasonality_hour_of_day: bool | None = None,
        raw_sample_mode: bool = False,
        raw_sample_size: int = 50,
        min_iforest_samples: int | None = None,
        scale_iforest_features: bool | None = None,
    ) -> dict[str, Any]:
        """Detect anomalies across dimensions using configurable methods.

        This function builds aggregations (schema-driven if provided), executes
        them against Elasticsearch, applies selected anomaly detection methods,
        and returns a concise analysis (optionally with drill-down templates and
        raw sample snippets).

        Args:
            time_range_hours (int): Time window in hours to analyze.
            anomaly_methods (list[str] | None): Methods to apply. Supported:
                ``zscore``, ``iqr``, ``isolation_forest``, ``time_series``. If None,
                defaults to ["zscore", "iqr"].
            sensitivity (float): Sensitivity parameter used by methods (e.g., z-score
                multiplier, IQR multiplier, thresholds). Default is 2.5.
            dimensions (list[str] | None): Legacy dimension list for quick setup
                (e.g., ["source_ip", "destination_port", ...]). Ignored when
                ``dimension_schema`` is provided. Default includes common fields.
            return_summary_only (bool): Reserved for future use; currently no effect.
            max_anomalies (int): Max anomalies to include per method.
            dimension_schema (dict[str, Any] | None): Data-driven schema mapping dimension
                names to aggregation specs with keys: ``field``, ``agg`` (terms, stats,
                percentiles, histogram, date_histogram), and optional ``size``, ``interval``,
                ``percents``.
            enable_iqr (bool | None): Whether to enable true IQR analysis. Defaults from
                config (statistical_analysis.enable_iqr) if None; false by default.
            enable_percentiles (bool | None): Whether to request percentiles in ES aggregations.
                Defaults from config or falls back to ``enable_iqr`` when None.
            time_series_mode (str): "fast" (mean deviation) or "robust" (median/MAD, rolling z).
            seasonality_hour_of_day (bool | None): If True, adjust robust baseline per hour-of-day.
            raw_sample_mode (bool): If True, fetch a small bounded raw sample from ES for the
                first detected anomaly.
            raw_sample_size (int): Size of the optional raw sample pull (default 50).
            min_iforest_samples (int | None): Minimum sample rows required for Isolation Forest.
            scale_iforest_features (bool | None): If True, scale features before Isolation Forest.

        Returns:
            dict[str, Any]: Result object containing:
                - success (bool)
                - anomaly_analysis (dict): Per-method results, patterns, risk_assessment,
                  context_pivots, etc.
                - metadata (dict): Method list, sensitivity, dimensions, telemetry, and
                  optional raw_samples.

        Raises:
            RuntimeError: If aggregation query fails.
        """
        logger.info(
            "Starting statistical anomaly detection",
            time_range_hours=time_range_hours,
            anomaly_methods=anomaly_methods,
            sensitivity=sensitivity,
            dimensions=dimensions,
        )

        try:
            t0 = time.perf_counter()
            # Set default values
            if anomaly_methods is None:
                anomaly_methods = ["zscore", "iqr"]
            if dimensions is None:
                dimensions = ["source_ip", "destination_port", "bytes_transferred", "event_rate"]

            # Merge with config-driven options
            cfg_dims = self.analysis_cfg.get("dimensions")
            if dimension_schema is None and isinstance(cfg_dims, dict):
                dimension_schema = cfg_dims

            if enable_iqr is None:
                enable_iqr = bool(self.analysis_cfg.get("enable_iqr", False))
            if enable_percentiles is None:
                # Use percentiles if iqr enabled or explicitly requested
                enable_percentiles = bool(self.analysis_cfg.get("enable_percentiles", enable_iqr))
            if seasonality_hour_of_day is None:
                seasonality_hour_of_day = bool(
                    self.analysis_cfg.get("seasonality_hour_of_day", False)
                )
            if min_iforest_samples is None:
                min_iforest_samples = int(self.analysis_cfg.get("min_iforest_samples", 20))
            if scale_iforest_features is None:
                scale_iforest_features = bool(self.analysis_cfg.get("scale_iforest_features", True))

            # Get anomaly aggregations using existing aggregation tool
            anomaly_data = await self._get_anomaly_aggregations(
                time_range_hours,
                dimensions,
                anomaly_methods,
                sensitivity,
                dimension_schema=dimension_schema,
                enable_percentiles=enable_percentiles,
            )

            # Apply statistical methods server-side
            anomalies = await self._apply_anomaly_detection_methods(
                anomaly_data,
                anomaly_methods,
                sensitivity,
                max_anomalies,
                time_series_mode=time_series_mode,
                seasonality_hour_of_day=seasonality_hour_of_day,
                enable_iqr=enable_iqr,
                min_iforest_samples=min_iforest_samples,
                scale_iforest_features=scale_iforest_features,
            )

            # Generate risk assessment and recommendations
            anomalies["risk_assessment"] = await self._assess_anomaly_risk(anomalies)
            anomalies["recommended_actions"] = await self._generate_anomaly_recommendations(
                anomalies
            )

            # Optional context pivots and raw samples
            anomalies["context_pivots"] = self._build_context_pivots(anomalies)

            raw_samples: dict[str, Any] | None = None
            if raw_sample_mode:
                raw_samples = await self._fetch_raw_samples(
                    anomaly_data, anomalies, sample_size=max(1, int(raw_sample_size))
                )

            return {
                "success": True,
                "anomaly_analysis": anomalies,
                "metadata": {
                    "time_range_hours": time_range_hours,
                    "methods_used": anomaly_methods,
                    "sensitivity": sensitivity,
                    "dimensions_analyzed": dimensions,
                    "timestamp": datetime.now(UTC).isoformat(),
                    "telemetry": {
                        "total_latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                        "anomalies_per_hour": (
                            round(
                                (
                                    anomalies.get("summary", {}).get("total_anomalies_detected", 0)
                                    / max(1, time_range_hours)
                                ),
                                3,
                            )
                        ),
                    },
                    "raw_samples": raw_samples if raw_sample_mode else None,
                },
            }

        except Exception as e:
            logger.error("Anomaly detection failed", error=str(e))
            return {
                "success": False,
                "error": f"Anomaly detection failed: {e!s}",
                "anomaly_analysis": None,
            }

    async def _get_anomaly_aggregations(
        self,
        time_range_hours: int,
        dimensions: list[str],
        methods: list[str],
        sensitivity: float,
        *,
        dimension_schema: dict[str, Any] | None = None,
        enable_percentiles: bool | None = False,
    ) -> dict[str, Any]:
        """Build and execute ES aggregations required for detection.

        Args:
            time_range_hours (int): Time window to query (hours).
            dimensions (list[str]): Legacy dimension list (ignored if
                ``dimension_schema`` is provided).
            methods (list[str]): Requested methods (may influence which aggs to build).
            sensitivity (float): Sensitivity parameter (for potential future tuning).
            dimension_schema (dict[str, Any] | None): Schema mapping custom dimension names to
                aggregation specifications. See ``detect_statistical_anomalies`` for details.
            enable_percentiles (bool | None): Whether to add ES ``percentiles`` aggregations
                for numeric fields.

        Returns:
            dict[str, Any]: The ES ``aggregations`` section from the search response.

        Raises:
            RuntimeError: If the ES search fails.
        """
        # Build aggregation query (schema-driven if provided)
        aggs: dict[str, Any] = {}

        def add_percentiles(target_aggs: dict[str, Any], key_name: str, field: str) -> None:
            if enable_percentiles:
                percs = self.analysis_cfg.get("percentiles", [25, 50, 75, 95, 99])
                target_aggs[f"{key_name}_percentiles"] = {
                    "percentiles": {
                        "field": field,
                        "percents": percs,
                    }
                }

        if dimension_schema:
            for name, spec in dimension_schema.items():
                agg_type = str(spec.get("agg", "terms"))
                field = str(spec.get("field", name))
                size = int(spec.get("size", 100))
                interval = spec.get("interval", "1h")
                if agg_type == "terms":
                    aggs[f"{name}_counts"] = {"terms": {"field": field, "size": size}}
                elif agg_type == "stats":
                    aggs[f"{name}_stats"] = {"stats": {"field": field}}
                    add_percentiles(aggs, name, field)
                elif agg_type == "percentiles":
                    aggs[f"{name}_percentiles"] = {
                        "percentiles": {
                            "field": field,
                            "percents": spec.get(
                                "percents",
                                self.analysis_cfg.get("percentiles", [25, 50, 75, 95, 99]),
                            ),
                        }
                    }
                elif agg_type == "histogram":
                    aggs[f"{name}_histogram"] = {
                        "histogram": {"field": field, "interval": spec.get("bucket", 10)}
                    }
                elif agg_type == "date_histogram":
                    aggs[f"{name}_time_series"] = {
                        "date_histogram": {"field": field, "calendar_interval": interval}
                    }
                else:
                    aggs[f"{name}_stats"] = {"stats": {"field": field}}
                    add_percentiles(aggs, name, field)
        else:
            for dimension in dimensions:
                if dimension in ["source_ip", "destination_ip"]:
                    aggs[f"{dimension}_counts"] = {
                        "terms": {"field": f"{dimension}.keyword", "size": 1000},
                    }
                elif dimension in ["destination_port", "bytes_transferred"]:
                    aggs[f"{dimension}_stats"] = {
                        "stats": {"field": dimension},
                    }
                    add_percentiles(aggs, dimension, dimension)
                elif dimension == "event_rate":
                    aggs[f"{dimension}_time_series"] = {
                        "date_histogram": {
                            "field": "@timestamp",
                            "calendar_interval": "1h",
                        },
                    }

        # Execute aggregation query using existing client method
        query_body = {
            "size": 0,
            "query": {
                "range": {
                    "@timestamp": {
                        "gte": f"now-{time_range_hours}h",
                        "lte": "now",
                    },
                },
            },
            "aggs": aggs,
        }

        try:
            result = await self.es_client.client.search(
                index=await self.es_client.get_available_indices(),
                body=query_body,
            )

            return result["aggregations"]

        except Exception as e:
            logger.error("Failed to get anomaly aggregations", error=str(e))
            raise RuntimeError(f"Failed to retrieve aggregation data: {e!s}") from e

    async def _apply_anomaly_detection_methods(
        self,
        anomaly_data: dict[str, Any],
        methods: list[str],
        sensitivity: float,
        max_anomalies: int,
        *,
        time_series_mode: str = "fast",
        seasonality_hour_of_day: bool = False,
        enable_iqr: bool = False,
        min_iforest_samples: int = 20,
        scale_iforest_features: bool = True,
    ) -> dict[str, Any]:
        """Apply the requested anomaly detection methods to aggregated data.

        Args:
            anomaly_data (dict[str, Any]): Aggregated results from ES.
            methods (list[str]): Methods to apply (zscore, iqr, isolation_forest, time_series).
            sensitivity (float): Sensitivity parameter for thresholds.
            max_anomalies (int): Max anomalies per method.
            time_series_mode (str): "fast" or "robust".
            seasonality_hour_of_day (bool): Enable hour-of-day seasonal baseline in robust mode.
            enable_iqr (bool): Enable IQR method (requires percentiles for best results).
            min_iforest_samples (int): Minimum rows to fit Isolation Forest.
            scale_iforest_features (bool): Whether to scale features for Isolation Forest.

        Returns:
            dict[str, Any]: Aggregated detection results including per-method details.
        """
        anomalies = {
            "summary": {
                "total_anomalies_detected": 0,
                "methods_applied": methods,
                "sensitivity_threshold": sensitivity,
            },
            "anomalies_by_method": {},
            "top_anomalies": [],
            "patterns": {},
        }

        # Apply Z-score analysis for numerical fields
        if "zscore" in methods:
            zscore_anomalies = await self._apply_zscore_analysis(
                anomaly_data,
                sensitivity,
                max_anomalies,
            )
            anomalies["anomalies_by_method"]["zscore"] = zscore_anomalies
            anomalies["summary"]["total_anomalies_detected"] += zscore_anomalies.get("count", 0)

        # Apply IQR-based outlier detection
        if "iqr" in methods and enable_iqr:
            iqr_anomalies = await self._apply_iqr_analysis(
                anomaly_data,
                sensitivity,
                max_anomalies,
            )
            anomalies["anomalies_by_method"]["iqr"] = iqr_anomalies
            anomalies["summary"]["total_anomalies_detected"] += iqr_anomalies.get("count", 0)

        # Apply Isolation Forest for multivariate anomalies
        if "isolation_forest" in methods:
            isolation_forest_anomalies = await self._apply_isolation_forest_analysis(
                anomaly_data,
                sensitivity,
                max_anomalies,
                min_samples=min_iforest_samples,
                scale_features=scale_iforest_features,
            )
            anomalies["anomalies_by_method"]["isolation_forest"] = isolation_forest_anomalies
            anomalies["summary"]["total_anomalies_detected"] += isolation_forest_anomalies.get(
                "count", 0
            )

        # Apply time series anomaly detection
        if "time_series" in methods:
            time_series_anomalies = await self._apply_time_series_analysis(
                anomaly_data,
                sensitivity,
                max_anomalies,
                mode=time_series_mode,
                seasonality_hour_of_day=seasonality_hour_of_day,
            )
            anomalies["anomalies_by_method"]["time_series"] = time_series_anomalies
            anomalies["summary"]["total_anomalies_detected"] += time_series_anomalies.get(
                "count", 0
            )

        # Generate pattern analysis
        anomalies["patterns"] = await self._detect_anomaly_patterns(anomalies)

        return anomalies

    async def _apply_zscore_analysis(
        self,
        anomaly_data: dict[str, Any],
        sensitivity: float,
        max_anomalies: int,
    ) -> dict[str, Any]:
        """Apply Z-score bounds on numeric field aggregates.

        Args:
            anomaly_data (dict[str, Any]): Aggregated ES data containing ``*_stats`` blocks.
            sensitivity (float): Z multiplier (e.g., 2.5 yields mean ± 2.5*std bounds).
            max_anomalies (int): Maximum anomalies to include (not heavily used here).

        Returns:
            dict[str, Any]: Z-score analysis summary with per-field bounds.
        """
        try:
            # Import scientific libraries for analysis
            import numpy as np  # noqa: F401
            from scipy import stats  # noqa: F401

            zscore_results = {
                "count": 0,
                "anomalies": [],
                "method": "zscore",
                "sensitivity": sensitivity,
            }

            # Process numerical fields that have stats
            for field_name, field_data in anomaly_data.items():
                if field_name.endswith("_stats") and "stats" in field_data:
                    stats_data = field_data["stats"]

                    # Extract numerical values for analysis
                    if "count" in stats_data and stats_data["count"] > 0:
                        # For now, we'll use the stats data to identify potential anomalies
                        # In a full implementation, we'd need to get the actual values
                        mean = stats_data.get("avg", 0)
                        std = stats_data.get("std_deviation", 1)

                        if std > 0:
                            # Calculate z-score bounds
                            lower_bound = mean - (sensitivity * std)
                            upper_bound = mean + (sensitivity * std)

                            zscore_results["anomalies"].append(
                                {
                                    "field": field_name.replace("_stats", ""),
                                    "mean": mean,
                                    "std_deviation": std,
                                    "lower_bound": lower_bound,
                                    "upper_bound": upper_bound,
                                    "anomaly_threshold": sensitivity,
                                }
                            )

            zscore_results["count"] = len(zscore_results["anomalies"])
            return zscore_results

        except ImportError as e:
            logger.warning("Required libraries not available for Z-score analysis", error=str(e))
            return {
                "count": 0,
                "anomalies": [],
                "method": "zscore",
                "error": "Required libraries (numpy, scipy) not available",
            }
        except Exception as e:
            logger.error("Z-score analysis failed", error=str(e))
            return {
                "count": 0,
                "anomalies": [],
                "method": "zscore",
                "error": f"Analysis failed: {e!s}",
            }

    async def _apply_iqr_analysis(
        self,
        anomaly_data: dict[str, Any],
        sensitivity: float,
        max_anomalies: int,
    ) -> dict[str, Any]:
        """Apply IQR-based outlier detection using percentiles when available.

        Args:
            anomaly_data (dict[str, Any]): Aggregated ES data containing ``*_percentiles``
                and/or ``*_stats`` blocks.
            sensitivity (float): Multiplier for IQR whiskers (e.g., 1.5 => Tukey fences).
            max_anomalies (int): Maximum anomalies to include (not heavily used here).

        Returns:
            dict[str, Any]: IQR analysis summary with per-field bounds or fallback ranges.
        """
        try:
            # Import scientific libraries for analysis
            import numpy as np  # noqa: F401

            iqr_results = {
                "count": 0,
                "anomalies": [],
                "method": "iqr",
                "sensitivity": sensitivity,
            }

            # Prefer percentiles (true IQR) if present; fallback to range
            for field_name, field_data in anomaly_data.items():
                base_field = field_name.replace("_percentiles", "").replace("_stats", "")
                if field_name.endswith("_percentiles") and "values" in field_data:
                    values = field_data["values"]
                    q1 = float(values.get("25.0", values.get("25", 0)))
                    q3 = float(values.get("75.0", values.get("75", 0)))
                    med = float(values.get("50.0", values.get("50", 0)))
                    iqr = max(0.0, q3 - q1)
                    if iqr > 0:
                        lower = q1 - sensitivity * iqr
                        upper = q3 + sensitivity * iqr
                        iqr_results["anomalies"].append(
                            {
                                "field": base_field,
                                "q1": q1,
                                "q3": q3,
                                "median": med,
                                "iqr": iqr,
                                "lower_bound": lower,
                                "upper_bound": upper,
                            }
                        )
                elif field_name.endswith("_stats") and "stats" in field_data:
                    stats_data = field_data["stats"]
                    if "count" in stats_data and stats_data["count"] > 0:
                        mean = float(stats_data.get("avg", 0))
                        min_val = float(stats_data.get("min", 0))
                        max_val = float(stats_data.get("max", 0))
                        range_val = max_val - min_val
                        if range_val > 0:
                            iqr_results["anomalies"].append(
                                {
                                    "field": base_field,
                                    "mean": mean,
                                    "range": range_val,
                                    "min": min_val,
                                    "max": max_val,
                                }
                            )

            iqr_results["count"] = len(iqr_results["anomalies"])
            return iqr_results

        except ImportError as e:
            logger.warning("Required libraries not available for IQR analysis", error=str(e))
            return {
                "count": 0,
                "anomalies": [],
                "method": "iqr",
                "error": "Required libraries (numpy) not available",
            }
        except Exception as e:
            logger.error("IQR analysis failed", error=str(e))
            return {
                "count": 0,
                "anomalies": [],
                "method": "iqr",
                "error": f"Analysis failed: {e!s}",
            }

    async def _apply_isolation_forest_analysis(
        self,
        anomaly_data: dict[str, Any],
        sensitivity: float,
        max_anomalies: int,
        *,
        min_samples: int = 20,
        scale_features: bool = True,
    ) -> dict[str, Any]:
        """Apply Isolation Forest to multivariate feature summaries.

        Args:
            anomaly_data (dict[str, Any]): Aggregated ES data with ``*_stats`` for fields.
            sensitivity (float): Scales the contamination parameter (sensitivity/10 capped at 0.1).
            max_anomalies (int): Max anomalies to include.
            min_samples (int): Minimum rows required to fit a model; returns a warning otherwise.
            scale_features (bool): Whether to mean/standardize features for stability.

        Returns:
            dict[str, Any]: Isolation Forest analysis including anomaly scores and features.
        """
        try:
            import numpy as np
            from sklearn.ensemble import IsolationForest

            isolation_results = {
                "count": 0,
                "anomalies": [],
                "method": "isolation_forest",
                "sensitivity": sensitivity,
            }

            # For Isolation Forest, we need to prepare features from the aggregated data
            # This is a simplified implementation - in practice, we'd need more data
            features = []
            feature_names = []

            for field_name, field_data in anomaly_data.items():
                if field_name.endswith("_stats") and "stats" in field_data:
                    stats_data = field_data["stats"]
                    if "count" in stats_data and stats_data["count"] > 0:
                        features.append(
                            [
                                stats_data.get("avg", 0),
                                stats_data.get("min", 0),
                                stats_data.get("max", 0),
                                stats_data.get("std_deviation", 0),
                            ]
                        )
                        feature_names.append(field_name.replace("_stats", ""))

            if features:
                # Convert to numpy array
                X = np.array(features)

                # Guardrail: minimum sample rows to avoid unstable models
                if X.shape[0] < max(1, int(min_samples)):
                    return {
                        "count": 0,
                        "anomalies": [],
                        "method": "isolation_forest",
                        "warning": f"insufficient samples: {X.shape[0]} < {min_samples}",
                    }

                # Optional feature scaling for stability
                if scale_features:
                    means = X.mean(axis=0)
                    stds = X.std(axis=0)
                    stds[stds == 0] = 1.0
                    X = (X - means) / stds

                # Apply Isolation Forest
                iso_forest = IsolationForest(
                    contamination=min(0.1, sensitivity / 10),  # Scale sensitivity to contamination
                    random_state=42,
                )

                # Fit and predict
                predictions = iso_forest.fit_predict(X)
                anomaly_indices = np.where(predictions == -1)[0]

                isolation_results["count"] = len(anomaly_indices)
                isolation_results["anomalies"] = [
                    {
                        "field": feature_names[i],
                        "anomaly_score": float(iso_forest.score_samples([X[i]])[0]),
                        "features": features[i].tolist(),
                    }
                    for i in anomaly_indices[:max_anomalies]
                ]

            return isolation_results

        except ImportError as e:
            logger.warning(
                "Required libraries not available for Isolation Forest analysis", error=str(e)
            )
            return {
                "count": 0,
                "anomalies": [],
                "method": "isolation_forest",
                "error": "Required libraries (scikit-learn, numpy) not available",
            }
        except Exception as e:
            logger.error("Isolation Forest analysis failed", error=str(e))
            return {
                "count": 0,
                "anomalies": [],
                "method": "isolation_forest",
                "error": f"Analysis failed: {e!s}",
            }

    def _time_series_anomalies_fast(
        self,
        volumes: list[int | float],
        timestamps: list[str | None],
        sensitivity: float,
    ) -> list[dict[str, Any]]:
        """Compute simple mean-based deviations for a time series.

        Args:
            volumes: Sequence of counts per bucket.
            timestamps: ISO-like timestamps per bucket (or None).
            sensitivity: Threshold scaling factor (mapped to mean-deviation).

        Returns:
            List of anomaly entries with deviation metrics.
        """
        anomalies: list[dict[str, Any]] = []
        if not volumes:
            return anomalies
        avg_volume = sum(volumes) / len(volumes)
        if avg_volume <= 0:
            return anomalies
        for i, volume in enumerate(volumes):
            deviation = abs(volume - avg_volume) / avg_volume
            if deviation > (sensitivity / 10):
                anomalies.append(
                    {
                        "timestamp": timestamps[i] or f"bucket_{i}",
                        "volume": volume,
                        "average_volume": avg_volume,
                        "deviation": deviation,
                        "anomaly_threshold": sensitivity / 10,
                    }
                )
        return anomalies

    def _time_series_anomalies_robust(
        self,
        volumes: list[int | float],
        timestamps: list[str | None],
        sensitivity: float,
        seasonality_hour_of_day: bool,
    ) -> list[dict[str, Any]]:
        """Compute robust time-series anomalies using median/MAD and rolling z-score.

        Falls back to fast mode if NumPy is unavailable.

        Args:
            volumes: Sequence of counts per bucket.
            timestamps: ISO-like timestamps per bucket (or None).
            sensitivity: Threshold for robust_z / rolling_z.
            seasonality_hour_of_day: Whether to adjust baseline by hour-of-day.

        Returns:
            List of anomaly entries with robust metrics.
        """
        try:
            import numpy as np  # type: ignore
        except Exception:
            # Fallback to fast mode
            return self._time_series_anomalies_fast(volumes, timestamps, sensitivity)

        anomalies: list[dict[str, Any]] = []
        if not volumes:
            return anomalies
        arr = np.array(volumes, dtype=float)
        med = float(np.median(arr))
        mad = float(np.median(np.abs(arr - med))) or 1.0
        window = min(7, max(3, len(arr) // 6))

        for i, v in enumerate(arr):
            baseline = med
            if seasonality_hour_of_day and timestamps[i]:
                ts = timestamps[i]
                hour = None
                if isinstance(ts, str) and len(ts) >= 13:
                    try:
                        hour = int(ts[11:13])
                    except Exception:
                        hour = None
                if hour is not None:
                    hour_vals = []
                    for j, t in enumerate(timestamps):
                        if isinstance(t, str) and len(t) >= 13:
                            try:
                                if int(t[11:13]) == hour:
                                    hour_vals.append(arr[j])
                            except Exception:
                                pass
                    if hour_vals:
                        baseline = float(np.median(np.array(hour_vals)))

            robust_z = 0.6745 * (v - baseline) / mad if mad != 0 else 0.0
            if i >= window:
                recent = arr[i - window : i]
                mu = float(np.mean(recent))
                sd = float(np.std(recent)) or 1.0
                rolling_z = (v - mu) / sd
            else:
                rolling_z = robust_z

            if abs(robust_z) > sensitivity or abs(rolling_z) > sensitivity:
                anomalies.append(
                    {
                        "timestamp": timestamps[i] or f"bucket_{i}",
                        "volume": float(v),
                        "median": med,
                        "mad": mad,
                        "robust_z": robust_z,
                        "rolling_z": rolling_z,
                        "anomaly_threshold": sensitivity,
                    }
                )
        return anomalies

    async def _apply_time_series_analysis(
        self,
        anomaly_data: dict[str, Any],
        sensitivity: float,
        max_anomalies: int,
        *,
        mode: str = "fast",
        seasonality_hour_of_day: bool = False,
    ) -> dict[str, Any]:
        """Detect time-series anomalies over date_histogram buckets.

        Args:
            anomaly_data (dict[str, Any]): Aggregated ES data containing ``*_time_series`` buckets.
            sensitivity (float): Threshold for deviation (fast) or for robust_z/rolling_z (robust).
            max_anomalies (int): Maximum anomalies to include.
            mode (str): "fast" for mean-based deviation; "robust" for MAD + rolling z.
            seasonality_hour_of_day (bool): If True, use hour-of-day baseline when possible.

        Returns:
            dict[str, Any]: Time-series anomalies with deviation metrics and thresholds.
        """
        time_series_results = {
            "count": 0,
            "anomalies": [],
            "method": "time_series",
            "sensitivity": sensitivity,
        }

        # Look for time series data in aggregations
        for field_name, field_data in anomaly_data.items():
            if field_name.endswith("_time_series") and "buckets" in field_data:
                buckets = field_data["buckets"]

                if len(buckets) > 1:
                    volumes = [bucket.get("doc_count", 0) for bucket in buckets]
                    timestamps = [bucket.get("key_as_string") for bucket in buckets]

                    if volumes:
                        if mode == "fast":
                            anomalies = self._time_series_anomalies_fast(
                                volumes, timestamps, sensitivity
                            )
                            time_series_results["anomalies"].extend(anomalies)
                        else:
                            anomalies = self._time_series_anomalies_robust(
                                volumes, timestamps, sensitivity, seasonality_hour_of_day
                            )
                            time_series_results["anomalies"].extend(anomalies)

        time_series_results["count"] = len(time_series_results["anomalies"])
        return time_series_results

    async def _detect_anomaly_patterns(self, anomalies: dict[str, Any]) -> dict[str, Any]:
        """Infer basic patterns from per-method anomaly outputs.

        Args:
            anomalies (dict[str, Any]): Combined anomaly analysis from all methods.

        Returns:
            dict[str, Any]: Pattern summaries (method agreement, field concentration).
        """
        patterns: dict[str, Any] = {
            "temporal_clustering": {},
            "field_concentration": {},
            "method_agreement": {},
        }

        # Analyze method agreement (how many methods detected the same anomalies)
        method_results = anomalies.get("anomalies_by_method", {})
        if len(method_results) > 1:
            # Simple pattern: check if multiple methods agree on anomalies
            total_anomalies = sum(result.get("count", 0) for result in method_results.values())
            if total_anomalies > 0:
                patterns["method_agreement"] = {
                    "total_methods": len(method_results),
                    "total_anomalies": total_anomalies,
                    "agreement_level": "high"
                    if total_anomalies > 10
                    else "medium"
                    if total_anomalies > 5
                    else "low",
                }

        # Analyze field concentration (which fields have most anomalies)
        field_counts: dict[str, int] = {}
        for _method_name, method_data in method_results.items():
            for anomaly in method_data.get("anomalies", []):
                field = anomaly.get("field", "unknown")
                field_counts[field] = field_counts.get(field, 0) + 1

        if field_counts:
            patterns["field_concentration"] = {
                "most_anomalous_fields": sorted(
                    field_counts.items(), key=lambda x: x[1], reverse=True
                )[:5],
                "total_fields_with_anomalies": len(field_counts),
            }

        return patterns

    async def _assess_anomaly_risk(self, anomalies: dict[str, Any]) -> dict[str, Any]:
        """Assign an overall risk level using configurable tiers and agreement.

        Args:
            anomalies (dict[str, Any]): Combined anomaly results including per-method counts.

        Returns:
            dict[str, Any]: Risk level, score, and contributing factors.
        """
        total_anomalies = anomalies.get("summary", {}).get("total_anomalies_detected", 0)

        # Calibrated risk scoring based on tunables + method agreement
        try:
            tunables = self.analysis_cfg.get("risk", {})  # type: ignore[attr-defined]
        except Exception:
            tunables = {}
        tiers = tunables.get("tiers", {"low": 1, "medium": 10, "high": 20})
        agree_weight = float(tunables.get("method_agreement_weight", 0.5))

        methods_used = anomalies.get("summary", {}).get("methods_applied", [])
        method_results = anomalies.get("anomalies_by_method", {})
        agreement = sum(result.get("count", 0) > 0 for result in method_results.values())
        agreement_norm = (agreement / max(1, len(methods_used))) if methods_used else 0.0

        base_score = 0
        if total_anomalies > int(tiers.get("high", 20)):
            base_score = 3
        elif total_anomalies > int(tiers.get("medium", 10)):
            base_score = 2
        elif total_anomalies > int(tiers.get("low", 0)):
            base_score = 1

        blended = base_score + agree_weight * agreement_norm
        if blended >= 2.5:
            risk_score = 3
        elif blended >= 1.5:
            risk_score = 2
        elif blended > 0.0:
            risk_score = 1
        else:
            risk_score = 0

        risk_levels = {0: "none", 1: "low", 2: "medium", 3: "high"}

        return {
            "overall_risk_level": risk_levels.get(risk_score, "unknown"),
            "risk_score": risk_score,
            "total_anomalies": total_anomalies,
            "risk_factors": [
                "high_anomaly_count" if total_anomalies > 20 else None,
                "multiple_methods_agree"
                if len(anomalies.get("anomalies_by_method", {})) > 1
                else None,
                "time_series_anomalies"
                if "time_series" in anomalies.get("anomalies_by_method", {})
                else None,
            ],
        }

    async def _generate_anomaly_recommendations(self, anomalies: dict[str, Any]) -> list[str]:
        """Produce human-readable next steps from anomaly context.

        Args:
            anomalies (dict[str, Any]): Combined anomaly and pattern results.

        Returns:
            list[str]: Recommendation strings prioritized by impact.
        """
        recommendations = []

        total_anomalies = anomalies.get("summary", {}).get("total_anomalies_detected", 0)

        if total_anomalies == 0:
            recommendations.append("No anomalies detected - current data appears normal")
            return recommendations

        if total_anomalies > 20:
            recommendations.append(
                "High number of anomalies detected - consider immediate investigation"
            )
            recommendations.append("Review security controls and monitoring thresholds")

        if total_anomalies > 10:
            recommendations.append(
                "Moderate anomalies detected - schedule investigation within 24 hours"
            )
            recommendations.append("Check for correlation with recent security events")

        # Method-specific recommendations
        method_results = anomalies.get("anomalies_by_method", {})

        if "time_series" in method_results:
            recommendations.append("Time series anomalies detected - investigate temporal patterns")

        if "isolation_forest" in method_results:
            recommendations.append(
                "Multivariate anomalies detected - investigate complex attack patterns"
            )

        if len(method_results) > 1:
            recommendations.append(
                "Multiple detection methods agree - high confidence in anomaly detection"
            )

        # Field-specific recommendations
        field_concentration = anomalies.get("patterns", {}).get("field_concentration", {})
        if field_concentration:
            most_anomalous = field_concentration.get("most_anomalous_fields", [])
            if most_anomalous:
                top_field = most_anomalous[0][0]
                recommendations.append(f"Focus investigation on {top_field} field anomalies")

        return recommendations

    def _build_context_pivots(self, anomalies: dict[str, Any]) -> dict[str, Any]:
        """Build ES query templates to drill down on flagged anomalies.

        Args:
            anomalies (dict[str, Any]): Combined per-method anomaly outputs.

        Returns:
            dict[str, Any]: Mapping of field name → list of ES query templates
            with placeholders (e.g., ``${start}``, ``${end}``, ``${port}``, ``${ip}``).
        """
        pivots: dict[str, Any] = {}

        def add(field: str, template: dict[str, Any]) -> None:
            pivots.setdefault(field, []).append(template)

        for method_data in anomalies.get("anomalies_by_method", {}).values():
            for a in method_data.get("anomalies", []):
                field = a.get("field")
                if not field:
                    continue
                if field in ("destination_port", "destination.port"):
                    add(
                        field,
                        {
                            "description": (
                                "Top 10 source.ip contributing to destination port spike"
                            ),
                            "size": 0,
                            "aggs": {"top_sources": {"terms": {"field": "source.ip", "size": 10}}},
                            "query": {
                                "bool": {
                                    "filter": [
                                        {"term": {"destination.port": "${port}"}},
                                        {
                                            "range": {
                                                "@timestamp": {
                                                    "gte": "${start}",
                                                    "lte": "${end}",
                                                }
                                            }
                                        },
                                    ]
                                }
                            },
                        },
                    )
                if field in ("source_ip", "source.ip"):
                    add(
                        field,
                        {
                            "description": "Top 10 destination.port for anomalous source.ip",
                            "size": 0,
                            "aggs": {
                                "top_ports": {"terms": {"field": "destination.port", "size": 10}}
                            },
                            "query": {
                                "bool": {
                                    "filter": [
                                        {"term": {"source.ip": "${ip}"}},
                                        {
                                            "range": {
                                                "@timestamp": {
                                                    "gte": "${start}",
                                                    "lte": "${end}",
                                                }
                                            }
                                        },
                                    ]
                                }
                            },
                        },
                    )
        return pivots

    async def _fetch_raw_samples(
        self,
        anomaly_data: dict[str, Any],
        anomalies: dict[str, Any],
        *,
        sample_size: int = 50,
    ) -> dict[str, Any]:
        """Fetch a small, bounded raw sample for the first anomaly (optional).

        Args:
            anomaly_data (dict[str, Any]): Raw aggregations (unused, reserved for future filtering).
            anomalies (dict[str, Any]): Per-method anomalies used to pick a target field/time.
            sample_size (int): Maximum number of documents to fetch.

        Returns:
            dict[str, Any]: Mapping of field → list of sampled documents (``_id`` and ``_source``).
        """
        samples: dict[str, Any] = {}
        try:
            indices = await self.es_client.get_available_indices()
            if not indices:
                return samples

            # Fetch at most one sample set for the first anomaly we find
            for _m, method_data in anomalies.get("anomalies_by_method", {}).items():
                for a in method_data.get("anomalies", [])[:1]:
                    # For now, use a recent 2h window for sampling
                    time_filter = {
                        "range": {
                            "@timestamp": {
                                "gte": "now-2h",
                                "lte": "now",
                            }
                        }
                    }
                    body = {
                        "size": max(1, int(sample_size)),
                        "query": {"bool": {"filter": [time_filter]}},
                    }
                    try:
                        res = await self.es_client.client.search(index=indices, body=body)
                        hits = res.get("hits", {}).get("hits", [])
                        field = a.get("field", "sample")
                        samples[field] = [
                            {"_id": h.get("_id"), "_source": h.get("_source")} for h in hits
                        ]
                    except Exception:
                        pass
                    return samples
        except Exception:
            return samples
        return samples
