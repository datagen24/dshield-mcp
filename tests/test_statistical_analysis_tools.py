#!/usr/bin/env python3
"""Tests for Statistical Analysis MCP Tools.

Tests the statistical anomaly detection functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.statistical_analysis_tools import StatisticalAnalysisTools


class TestStatisticalAnalysisTools:
    """Test cases for StatisticalAnalysisTools class."""

    @pytest.fixture
    def mock_es_client(self) -> MagicMock:
        """Create a mock Elasticsearch client."""
        mock_client = MagicMock()
        mock_client.client = AsyncMock()
        mock_client.get_available_indices = AsyncMock(return_value=["test-index"])
        return mock_client

    @pytest.fixture
    def stats_tools(self, mock_es_client: MagicMock) -> StatisticalAnalysisTools:
        """Create StatisticalAnalysisTools instance with mock ES client."""
        return StatisticalAnalysisTools(mock_es_client)

    @pytest.mark.asyncio
    async def test_init_with_es_client(self, mock_es_client: MagicMock) -> None:
        """Test initialization with provided Elasticsearch client."""
        stats_tools = StatisticalAnalysisTools(mock_es_client)
        assert stats_tools.es_client == mock_es_client

    @pytest.mark.asyncio
    async def test_init_without_es_client(self) -> None:
        """Test initialization without Elasticsearch client."""
        with patch('src.statistical_analysis_tools.ElasticsearchClient') as mock_es_class:
            mock_es_instance = MagicMock()
            mock_es_class.return_value = mock_es_instance

            stats_tools = StatisticalAnalysisTools()
            assert stats_tools.es_client == mock_es_instance

    @pytest.mark.asyncio
    async def test_detect_statistical_anomalies_success(
        self, stats_tools: StatisticalAnalysisTools
    ) -> None:
        """Test successful anomaly detection."""
        # Mock the aggregation data
        mock_aggregations = {
            "source_ip_counts": {
                "buckets": [
                    {"key": "192.168.1.1", "doc_count": 100},
                    {"key": "192.168.1.2", "doc_count": 50},
                ]
            },
            "destination_port_stats": {
                "stats": {"count": 150, "min": 80, "max": 443, "avg": 261.5, "std_deviation": 181.5}
            },
        }

        # Mock the _get_anomaly_aggregations method
        with patch.object(stats_tools, '_get_anomaly_aggregations', return_value=mock_aggregations):
            with patch.object(stats_tools, '_apply_anomaly_detection_methods') as mock_apply:
                mock_apply.return_value = {
                    "summary": {"total_anomalies_detected": 5},
                    "anomalies_by_method": {},
                    "top_anomalies": [],
                    "patterns": {},
                }

                result = await stats_tools.detect_statistical_anomalies(
                    time_range_hours=24, anomaly_methods=["zscore", "iqr"]
                )

                assert result["success"] is True
                assert "anomaly_analysis" in result
                assert "metadata" in result
                assert result["metadata"]["time_range_hours"] == 24
                assert result["metadata"]["methods_used"] == ["zscore", "iqr"]

    @pytest.mark.asyncio
    async def test_detect_statistical_anomalies_failure(
        self, stats_tools: StatisticalAnalysisTools
    ) -> None:
        """Test anomaly detection failure handling."""
        with patch.object(
            stats_tools, '_get_anomaly_aggregations', side_effect=Exception("Test error")
        ):
            result = await stats_tools.detect_statistical_anomalies()

            assert result["success"] is False
            assert "error" in result
            assert "Test error" in result["error"]

    @pytest.mark.asyncio
    async def test_get_anomaly_aggregations(self, stats_tools: StatisticalAnalysisTools) -> None:
        """Test aggregation data retrieval."""
        mock_es_response = {
            "aggregations": {
                "source_ip_counts": {"buckets": []},
                "destination_port_stats": {"stats": {}},
            }
        }

        stats_tools.es_client.client.search = AsyncMock(return_value=mock_es_response)

        result = await stats_tools._get_anomaly_aggregations(
            time_range_hours=24,
            dimensions=["source_ip", "destination_port"],
            methods=["zscore"],
            sensitivity=2.5,
        )

        assert "source_ip_counts" in result
        assert "destination_port_stats" in result

    @pytest.mark.asyncio
    async def test_get_anomaly_aggregations_error(
        self, stats_tools: StatisticalAnalysisTools
    ) -> None:
        """Test aggregation data retrieval error handling."""
        stats_tools.es_client.client.search = AsyncMock(side_effect=Exception("ES error"))

        with pytest.raises(RuntimeError, match="Failed to retrieve aggregation data"):
            await stats_tools._get_anomaly_aggregations(
                time_range_hours=24, dimensions=["source_ip"], methods=["zscore"], sensitivity=2.5
            )

    @pytest.mark.asyncio
    async def test_apply_anomaly_detection_methods(
        self, stats_tools: StatisticalAnalysisTools
    ) -> None:
        """Test application of anomaly detection methods."""
        mock_aggregations = {
            "destination_port_stats": {
                "stats": {"count": 100, "min": 80, "max": 443, "avg": 261.5, "std_deviation": 181.5}
            }
        }

        with patch.object(stats_tools, '_apply_zscore_analysis') as mock_zscore:
            mock_zscore.return_value = {"count": 2, "anomalies": []}

            result = await stats_tools._apply_anomaly_detection_methods(
                mock_aggregations, ["zscore"], 2.5, 50
            )

            assert result["summary"]["total_anomalies_detected"] == 2
            assert "zscore" in result["anomalies_by_method"]

    @pytest.mark.asyncio
    async def test_apply_zscore_analysis_success(
        self, stats_tools: StatisticalAnalysisTools
    ) -> None:
        """Test successful Z-score analysis."""
        mock_aggregations = {
            "destination_port_stats": {
                "stats": {"count": 100, "min": 80, "max": 443, "avg": 261.5, "std_deviation": 181.5}
            }
        }

        with patch('builtins.__import__') as mock_import:
            # Mock numpy and scipy imports
            mock_np = MagicMock()
            mock_stats = MagicMock()
            mock_import.side_effect = lambda name, *args, **kwargs: {
                'numpy': mock_np,
                'scipy.stats': mock_stats,
                'scipy': MagicMock(stats=mock_stats),
            }.get(name, MagicMock())

            result = await stats_tools._apply_zscore_analysis(mock_aggregations, 2.5, 50)

            assert result["method"] == "zscore"
            assert result["sensitivity"] == 2.5
            assert len(result["anomalies"]) > 0

    @pytest.mark.asyncio
    async def test_apply_zscore_analysis_import_error(
        self, stats_tools: StatisticalAnalysisTools
    ) -> None:
        """Test Z-score analysis with missing dependencies."""

        # Mock the import to fail only for numpy
        def mock_import(name, *args, **kwargs):
            if name == 'numpy':
                raise ImportError("numpy not available")
            return MagicMock()

        with patch('builtins.__import__', side_effect=mock_import):
            result = await stats_tools._apply_zscore_analysis({}, 2.5, 50)

            assert result["count"] == 0
            assert "error" in result
            assert "numpy" in result["error"]

    @pytest.mark.asyncio
    async def test_apply_iqr_analysis_success(self, stats_tools: StatisticalAnalysisTools) -> None:
        """Test successful IQR analysis."""
        mock_aggregations = {
            "destination_port_stats": {
                "stats": {"count": 100, "min": 80, "max": 443, "avg": 261.5, "std_deviation": 181.5}
            }
        }

        with patch('builtins.__import__') as mock_import:
            # Mock numpy import
            mock_np = MagicMock()
            mock_import.side_effect = lambda name, *args, **kwargs: {'numpy': mock_np}.get(
                name, MagicMock()
            )

            result = await stats_tools._apply_iqr_analysis(mock_aggregations, 2.5, 50)

            assert result["method"] == "iqr"
            assert result["sensitivity"] == 2.5
            assert len(result["anomalies"]) > 0

    @pytest.mark.asyncio
    async def test_apply_isolation_forest_analysis_success(
        self, stats_tools: StatisticalAnalysisTools
    ) -> None:
        """Test successful Isolation Forest analysis."""
        mock_aggregations = {
            "destination_port_stats": {
                "stats": {"count": 100, "min": 80, "max": 443, "avg": 261.5, "std_deviation": 181.5}
            }
        }

        with patch('builtins.__import__') as mock_import:
            # Mock sklearn and numpy imports
            mock_forest = MagicMock()
            mock_forest.fit_predict.return_value = [1, -1, 1]  # -1 indicates anomaly
            mock_forest.score_samples.return_value = [0.1, -0.5, 0.2]

            mock_import.side_effect = lambda name, *args, **kwargs: {
                'sklearn.ensemble': MagicMock(IsolationForest=MagicMock(return_value=mock_forest)),
                'sklearn': MagicMock(
                    ensemble=MagicMock(IsolationForest=MagicMock(return_value=mock_forest))
                ),
                'numpy': MagicMock(),
            }.get(name, MagicMock())

            result = await stats_tools._apply_isolation_forest_analysis(mock_aggregations, 2.5, 50)

            assert result["method"] == "isolation_forest"
            assert result["sensitivity"] == 2.5

    @pytest.mark.asyncio
    async def test_apply_time_series_analysis(self, stats_tools: StatisticalAnalysisTools) -> None:
        """Test time series anomaly detection."""
        mock_aggregations = {
            "event_rate_time_series": {
                "buckets": [
                    {"key_as_string": "2024-01-01T00:00:00", "doc_count": 100},
                    {"key_as_string": "2024-01-01T01:00:00", "doc_count": 150},
                    {"key_as_string": "2024-01-01T02:00:00", "doc_count": 50},
                ]
            }
        }

        result = await stats_tools._apply_time_series_analysis(mock_aggregations, 2.5, 50)

        assert result["method"] == "time_series"
        assert result["sensitivity"] == 2.5
        assert result["count"] > 0

    @pytest.mark.asyncio
    async def test_detect_anomaly_patterns(self, stats_tools: StatisticalAnalysisTools) -> None:
        """Test anomaly pattern detection."""
        mock_anomalies = {
            "anomalies_by_method": {
                "zscore": {"count": 5, "anomalies": [{"field": "source_ip"}]},
                "iqr": {"count": 3, "anomalies": [{"field": "destination_port"}]},
            }
        }

        result = await stats_tools._detect_anomaly_patterns(mock_anomalies)

        assert "method_agreement" in result
        assert "field_concentration" in result
        assert result["method_agreement"]["total_methods"] == 2

    @pytest.mark.asyncio
    async def test_assess_anomaly_risk(self, stats_tools: StatisticalAnalysisTools) -> None:
        """Test anomaly risk assessment."""
        mock_anomalies = {
            "summary": {"total_anomalies_detected": 25},
            "anomalies_by_method": {"zscore": {"count": 15}, "iqr": {"count": 10}},
        }

        result = await stats_tools._assess_anomaly_risk(mock_anomalies)

        assert result["overall_risk_level"] == "high"
        assert result["risk_score"] == 3
        assert "high_anomaly_count" in result["risk_factors"]

    @pytest.mark.asyncio
    async def test_generate_anomaly_recommendations(
        self, stats_tools: StatisticalAnalysisTools
    ) -> None:
        """Test anomaly recommendation generation."""
        mock_anomalies = {
            "summary": {"total_anomalies_detected": 15},
            "anomalies_by_method": {"zscore": {"count": 10}, "time_series": {"count": 5}},
        }

        result = await stats_tools._generate_anomaly_recommendations(mock_anomalies)

        assert len(result) > 0
        assert any("Moderate anomalies" in rec for rec in result)
        assert any("Time series anomalies" in rec for rec in result)

    @pytest.mark.asyncio
    async def test_generate_anomaly_recommendations_no_anomalies(
        self, stats_tools: StatisticalAnalysisTools
    ) -> None:
        """Test recommendation generation when no anomalies are detected."""
        mock_anomalies = {"summary": {"total_anomalies_detected": 0}}

        result = await stats_tools._generate_anomaly_recommendations(mock_anomalies)

        assert len(result) == 1
        assert "No anomalies detected" in result[0]

    @pytest.mark.asyncio
    async def test_default_parameters(self, stats_tools: StatisticalAnalysisTools) -> None:
        """Test that default parameters are properly set."""
        with patch.object(stats_tools, '_get_anomaly_aggregations') as mock_get:
            with patch.object(stats_tools, '_apply_anomaly_detection_methods') as mock_apply:
                mock_get.return_value = {}
                mock_apply.return_value = {
                    "summary": {"total_anomalies_detected": 0},
                    "anomalies_by_method": {},
                    "top_anomalies": [],
                    "patterns": {},
                }

                await stats_tools.detect_statistical_anomalies()

                # Check that default values were used
                mock_get.assert_called_once()
                call_args = mock_get.call_args[0]
                assert call_args[0] == 24  # time_range_hours
                assert call_args[1] == [
                    "source_ip",
                    "destination_port",
                    "bytes_transferred",
                    "event_rate",
                ]  # dimensions
                assert call_args[2] == ["zscore", "iqr"]  # anomaly_methods
                assert call_args[3] == 2.5  # sensitivity

    @pytest.mark.asyncio
    async def test_custom_parameters(self, stats_tools: StatisticalAnalysisTools) -> None:
        """Test that custom parameters are properly passed through."""
        custom_params = {
            "time_range_hours": 48,
            "anomaly_methods": ["isolation_forest", "time_series"],
            "sensitivity": 3.0,
            "dimensions": ["custom_field"],
            "return_summary_only": False,
            "max_anomalies": 100,
        }

        with patch.object(stats_tools, '_get_anomaly_aggregations') as mock_get:
            with patch.object(stats_tools, '_apply_anomaly_detection_methods') as mock_apply:
                mock_get.return_value = {}
                mock_apply.return_value = {
                    "summary": {"total_anomalies_detected": 0},
                    "anomalies_by_method": {},
                    "top_anomalies": [],
                    "patterns": {},
                }

                await stats_tools.detect_statistical_anomalies(**custom_params)

                # Check that custom values were used
                mock_get.assert_called_once()
                call_args = mock_get.call_args[0]
                assert call_args[0] == 48  # time_range_hours
                assert call_args[1] == ["custom_field"]  # dimensions
                assert call_args[2] == ["isolation_forest", "time_series"]  # anomaly_methods
                assert call_args[3] == 3.0  # sensitivity
