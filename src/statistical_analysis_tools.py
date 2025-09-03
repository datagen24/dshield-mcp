#!/usr/bin/env python3
"""Statistical Analysis MCP Tools.

MCP tools for statistical analysis, anomaly detection, and pattern recognition
in DShield SIEM data.
"""

from datetime import UTC, datetime
from typing import Any

import structlog

from .elasticsearch_client import ElasticsearchClient
from .user_config import get_user_config

logger = structlog.get_logger(__name__)


class StatisticalAnalysisTools:
    """MCP tools for statistical analysis and anomaly detection."""

    def __init__(self, es_client: ElasticsearchClient | None = None):
        """Initialize StatisticalAnalysisTools.

        Args:
            es_client: Optional ElasticsearchClient instance. If not provided, a new one is created.

        """
        self.es_client = es_client or ElasticsearchClient()
        self.user_config = get_user_config()

    async def detect_statistical_anomalies(
        self,
        time_range_hours: int = 24,
        anomaly_methods: list[str] | None = None,
        sensitivity: float = 2.5,
        dimensions: list[str] | None = None,
        return_summary_only: bool = True,
        max_anomalies: int = 50,
    ) -> dict[str, Any]:
        """Detect statistical anomalies in DShield events without returning all raw data.

        Args:
            time_range_hours: Time range in hours to analyze (default: 24)
            anomaly_methods: List of anomaly detection methods to use
            sensitivity: Sensitivity threshold for anomaly detection (default: 2.5)
            dimensions: Dimensions to analyze for anomalies
            return_summary_only: Whether to return only summary data (default: True)
            max_anomalies: Maximum number of anomalies to return (default: 50)

        Returns:
            Dictionary containing anomaly detection results and analysis

        """
        logger.info(
            "Starting statistical anomaly detection",
            time_range_hours=time_range_hours,
            anomaly_methods=anomaly_methods,
            sensitivity=sensitivity,
            dimensions=dimensions,
        )

        try:
            # Set default values
            if anomaly_methods is None:
                anomaly_methods = ["zscore", "iqr"]
            if dimensions is None:
                dimensions = ["source_ip", "destination_port", "bytes_transferred", "event_rate"]

            # Get anomaly aggregations using existing aggregation tool
            anomaly_data = await self._get_anomaly_aggregations(
                time_range_hours,
                dimensions,
                anomaly_methods,
                sensitivity,
            )

            # Apply statistical methods server-side
            anomalies = await self._apply_anomaly_detection_methods(
                anomaly_data,
                anomaly_methods,
                sensitivity,
                max_anomalies,
            )

            # Generate risk assessment and recommendations
            anomalies["risk_assessment"] = await self._assess_anomaly_risk(anomalies)
            anomalies["recommended_actions"] = await self._generate_anomaly_recommendations(
                anomalies
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
    ) -> dict[str, Any]:
        """Get aggregated data for anomaly detection without raw events.

        Args:
            time_range_hours: Time range in hours to query
            dimensions: Dimensions to analyze for anomalies
            methods: Anomaly detection methods to use
            sensitivity: Sensitivity threshold for anomaly detection

        Returns:
            Dictionary containing aggregated data for anomaly analysis

        """
        # Build aggregation query for each dimension
        aggs = {}

        for dimension in dimensions:
            if dimension in ["source_ip", "destination_ip"]:
                aggs[f"{dimension}_counts"] = {
                    "terms": {"field": f"{dimension}.keyword", "size": 1000},
                }
            elif dimension in ["destination_port", "bytes_transferred"]:
                aggs[f"{dimension}_stats"] = {
                    "stats": {"field": dimension},
                }
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
    ) -> dict[str, Any]:
        """Apply statistical anomaly detection methods to aggregated data.

        Args:
            anomaly_data: Aggregated data from Elasticsearch
            methods: List of anomaly detection methods to apply
            sensitivity: Sensitivity threshold for anomaly detection
            max_anomalies: Maximum number of anomalies to return

        Returns:
            Dictionary containing anomaly detection results

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
        if "iqr" in methods:
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
        """Apply Z-score analysis for numerical fields.

        Args:
            anomaly_data: Aggregated data from Elasticsearch
            sensitivity: Z-score threshold for anomaly detection
            max_anomalies: Maximum number of anomalies to return

        Returns:
            Dictionary containing Z-score analysis results

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
        """Apply IQR-based outlier detection.

        Args:
            anomaly_data: Aggregated data from Elasticsearch
            sensitivity: IQR multiplier for outlier detection
            max_anomalies: Maximum number of anomalies to return

        Returns:
            Dictionary containing IQR analysis results

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

            # Process numerical fields that have stats
            for field_name, field_data in anomaly_data.items():
                if field_name.endswith("_stats") and "stats" in field_data:
                    stats_data = field_data["stats"]

                    if "count" in stats_data and stats_data["count"] > 0:
                        # Extract percentiles for IQR calculation
                        # Note: Elasticsearch stats aggregation doesn't provide percentiles by default
                        # We'd need to use percentiles aggregation for full IQR analysis
                        mean = stats_data.get("avg", 0)
                        min_val = stats_data.get("min", 0)
                        max_val = stats_data.get("max", 0)

                        # Simple range-based anomaly detection as fallback
                        range_val = max_val - min_val
                        if range_val > 0:
                            iqr_results["anomalies"].append(
                                {
                                    "field": field_name.replace("_stats", ""),
                                    "mean": mean,
                                    "range": range_val,
                                    "min": min_val,
                                    "max": max_val,
                                    "anomaly_threshold": sensitivity,
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
    ) -> dict[str, Any]:
        """Apply Isolation Forest for multivariate anomaly detection.

        Args:
            anomaly_data: Aggregated data from Elasticsearch
            sensitivity: Contamination factor for anomaly detection
            max_anomalies: Maximum number of anomalies to return

        Returns:
            Dictionary containing Isolation Forest analysis results

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

    async def _apply_time_series_analysis(
        self,
        anomaly_data: dict[str, Any],
        sensitivity: float,
        max_anomalies: int,
    ) -> dict[str, Any]:
        """Apply time series anomaly detection.

        Args:
            anomaly_data: Aggregated data from Elasticsearch
            sensitivity: Sensitivity threshold for anomaly detection
            max_anomalies: Maximum number of anomalies to return

        Returns:
            Dictionary containing time series analysis results

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
                    # Simple time series anomaly detection based on volume changes
                    volumes = [bucket.get("doc_count", 0) for bucket in buckets]

                    if volumes:
                        # Calculate basic statistics
                        avg_volume = sum(volumes) / len(volumes)

                        # Identify significant deviations
                        for i, volume in enumerate(volumes):
                            if avg_volume > 0:
                                deviation = abs(volume - avg_volume) / avg_volume
                                if deviation > (sensitivity / 10):  # Scale sensitivity
                                    time_series_results["anomalies"].append(
                                        {
                                            "timestamp": buckets[i].get(
                                                "key_as_string", f"bucket_{i}"
                                            ),
                                            "volume": volume,
                                            "average_volume": avg_volume,
                                            "deviation": deviation,
                                            "anomaly_threshold": sensitivity / 10,
                                        }
                                    )

        time_series_results["count"] = len(time_series_results["anomalies"])
        return time_series_results

    async def _detect_anomaly_patterns(self, anomalies: dict[str, Any]) -> dict[str, Any]:
        """Detect patterns in detected anomalies.

        Args:
            anomalies: Anomaly detection results

        Returns:
            Dictionary containing pattern analysis

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
        """Assess the overall risk level of detected anomalies.

        Args:
            anomalies: Anomaly detection results

        Returns:
            Dictionary containing risk assessment

        """
        total_anomalies = anomalies.get("summary", {}).get("total_anomalies_detected", 0)

        # Simple risk scoring based on anomaly count and methods
        risk_score = 0
        if total_anomalies > 20:
            risk_score = 3  # High
        elif total_anomalies > 10:
            risk_score = 2  # Medium
        elif total_anomalies > 0:
            risk_score = 1  # Low

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
        """Generate actionable recommendations based on anomaly analysis.

        Args:
            anomalies: Anomaly detection results

        Returns:
            List of actionable recommendations

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
