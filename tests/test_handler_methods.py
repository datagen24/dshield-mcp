"""Tests for new MCP server handler methods.

This module tests the handler methods added for Issue #113 refactoring:
- _get_health_status
- _detect_statistical_anomalies
"""

import json
import pytest
from datetime import datetime, UTC
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Note: Due to MCP namespace collision (Issue #124), we cannot import mcp_server directly
# These tests will need to be updated once that issue is resolved


@pytest.mark.skip(reason="Blocked by MCP namespace collision - Issue #124")
class TestHealthStatusHandler:
    """Tests for _get_health_status handler method."""

    @pytest.fixture
    def mock_server(self):
        """Create a mock MCP server instance."""
        server = Mock()
        server.health_manager = AsyncMock()
        server.feature_manager = Mock()
        server.tool_loader = Mock()
        return server

    @pytest.mark.asyncio
    async def test_health_status_detailed_mode(self, mock_server):
        """Test health status handler in detailed mode."""
        # Mock health check results
        health_results = {
            "summary": {"healthy": 2, "unhealthy": 1},
            "checks": {
                "elasticsearch": {"status": "healthy", "latency_ms": 15},
                "dshield_api": {"status": "healthy", "latency_ms": 120},
                "latex": {"status": "unhealthy", "error": "Not installed"}
            }
        }
        mock_server.health_manager.run_all_checks.return_value = health_results

        # Mock feature summary
        feature_summary = {
            "available": ["elasticsearch", "dshield_api"],
            "unavailable": ["latex"]
        }
        mock_server.feature_manager.get_feature_summary.return_value = feature_summary

        # Mock tool loader info
        mock_server.tool_loader.get_all_tool_definitions.return_value = [Mock()] * 10
        mock_server.tool_loader.get_available_tools.return_value = [Mock()] * 8

        # Test the handler
        from mcp_server import DShieldMCPServer
        result = await DShieldMCPServer._get_health_status(
            mock_server,
            {"detailed": True}
        )

        # Verify result structure
        assert len(result) == 1
        assert result[0]["type"] == "text"

        response_data = json.loads(result[0]["text"])
        assert response_data["status"] in ["healthy", "degraded"]
        assert "timestamp" in response_data
        assert response_data["health_checks"] == health_results
        assert response_data["features"] == feature_summary
        assert response_data["server_info"]["tools_loaded"] == 10
        assert response_data["server_info"]["tools_available"] == 8

    @pytest.mark.asyncio
    async def test_health_status_summary_mode(self, mock_server):
        """Test health status handler in summary mode (default)."""
        # Mock health check results
        health_results = {
            "summary": {"healthy": 3, "unhealthy": 0}
        }
        mock_server.health_manager.run_all_checks.return_value = health_results

        # Mock feature summary
        mock_server.feature_manager.get_available_features.return_value = [
            "elasticsearch", "dshield_api", "latex"
        ]

        # Mock tool loader info
        mock_server.tool_loader.get_all_tool_definitions.return_value = [Mock()] * 10

        # Test the handler
        from mcp_server import DShieldMCPServer
        result = await DShieldMCPServer._get_health_status(
            mock_server,
            {"detailed": False}
        )

        # Verify result structure
        assert len(result) == 1
        response_data = json.loads(result[0]["text"])

        assert response_data["status"] == "healthy"
        assert response_data["healthy_services"] == 3
        assert response_data["unhealthy_services"] == 0
        assert response_data["available_features"] == 3
        assert response_data["total_tools"] == 10
        assert "health_checks" not in response_data  # Not included in summary mode

    @pytest.mark.asyncio
    async def test_health_status_degraded_state(self, mock_server):
        """Test health status when system is degraded."""
        # Mock health check results with failures
        health_results = {
            "summary": {"healthy": 1, "unhealthy": 2}
        }
        mock_server.health_manager.run_all_checks.return_value = health_results
        mock_server.feature_manager.get_available_features.return_value = ["elasticsearch"]
        mock_server.tool_loader.get_all_tool_definitions.return_value = [Mock()] * 10

        # Test the handler
        from mcp_server import DShieldMCPServer
        result = await DShieldMCPServer._get_health_status(
            mock_server,
            {}  # Default arguments
        )

        response_data = json.loads(result[0]["text"])
        assert response_data["status"] == "degraded"
        assert response_data["healthy_services"] == 1
        assert response_data["unhealthy_services"] == 2


@pytest.mark.skip(reason="Blocked by MCP namespace collision - Issue #124")
class TestStatisticalAnomaliesHandler:
    """Tests for _detect_statistical_anomalies handler method."""

    @pytest.fixture
    def mock_server(self):
        """Create a mock MCP server instance."""
        server = Mock()
        server.elastic_client = AsyncMock()
        server.error_handler = Mock()
        return server

    @pytest.fixture
    def mock_stat_tools(self):
        """Create mock statistical analysis tools."""
        with patch('mcp_server.StatisticalAnalysisTools') as mock:
            tools = Mock()
            tools.detect_zscore_anomalies = AsyncMock()
            tools.detect_iqr_anomalies = AsyncMock()
            tools.detect_isolation_forest_anomalies = AsyncMock()
            tools.detect_time_series_anomalies = AsyncMock()
            mock.return_value = tools
            yield mock

    @pytest.mark.asyncio
    async def test_detect_anomalies_zscore_method(self, mock_server, mock_stat_tools):
        """Test anomaly detection with z-score method."""
        # Mock anomaly results
        anomalies = [
            {"timestamp": "2024-01-01T00:00:00Z", "value": 100, "zscore": 4.5},
            {"timestamp": "2024-01-01T01:00:00Z", "value": 95, "zscore": 4.2}
        ]
        mock_stat_tools.return_value.detect_zscore_anomalies.return_value = anomalies

        # Test the handler
        from mcp_server import DShieldMCPServer
        result = await DShieldMCPServer._detect_statistical_anomalies(
            mock_server,
            {
                "time_range_hours": 24,
                "anomaly_methods": ["zscore"],
                "sensitivity": 3.0,
                "return_summary_only": False
            }
        )

        # Verify result
        assert len(result) == 1
        response_data = json.loads(result[0]["text"])
        assert "zscore" in response_data
        assert len(response_data["zscore"]) == 2

    @pytest.mark.asyncio
    async def test_detect_anomalies_multiple_methods(self, mock_server, mock_stat_tools):
        """Test anomaly detection with multiple methods."""
        # Mock anomaly results for different methods
        zscore_anomalies = [{"value": 100, "zscore": 4.5}]
        iqr_anomalies = [{"value": 95, "iqr_score": 2.5}]

        mock_stat_tools.return_value.detect_zscore_anomalies.return_value = zscore_anomalies
        mock_stat_tools.return_value.detect_iqr_anomalies.return_value = iqr_anomalies

        # Test the handler
        from mcp_server import DShieldMCPServer
        result = await DShieldMCPServer._detect_statistical_anomalies(
            mock_server,
            {
                "anomaly_methods": ["zscore", "iqr"],
                "return_summary_only": False
            }
        )

        # Verify both methods are included
        response_data = json.loads(result[0]["text"])
        assert "zscore" in response_data
        assert "iqr" in response_data
        assert len(response_data["zscore"]) == 1
        assert len(response_data["iqr"]) == 1

    @pytest.mark.asyncio
    async def test_detect_anomalies_with_max_limit(self, mock_server, mock_stat_tools):
        """Test anomaly detection with max anomalies limit."""
        # Mock many anomalies
        anomalies = [{"value": i, "zscore": 4.0 + i * 0.1} for i in range(200)]
        mock_stat_tools.return_value.detect_zscore_anomalies.return_value = anomalies

        # Test the handler with max limit
        from mcp_server import DShieldMCPServer
        result = await DShieldMCPServer._detect_statistical_anomalies(
            mock_server,
            {
                "anomaly_methods": ["zscore"],
                "max_anomalies": 50
            }
        )

        # Verify limit is applied
        response_data = json.loads(result[0]["text"])
        assert len(response_data["zscore"]) == 50

    @pytest.mark.asyncio
    async def test_detect_anomalies_default_parameters(self, mock_server, mock_stat_tools):
        """Test anomaly detection with default parameters."""
        anomalies = [{"value": 100, "zscore": 4.5}]
        mock_stat_tools.return_value.detect_zscore_anomalies.return_value = anomalies

        # Test with minimal arguments (should use defaults)
        from mcp_server import DShieldMCPServer
        result = await DShieldMCPServer._detect_statistical_anomalies(
            mock_server,
            {}  # Empty arguments - use all defaults
        )

        # Verify it uses defaults
        mock_stat_tools.return_value.detect_zscore_anomalies.assert_called_once()
        call_args = mock_stat_tools.return_value.detect_zscore_anomalies.call_args
        assert call_args.kwargs["time_range_hours"] == 24
        assert call_args.kwargs["z_threshold"] == 3.0

    @pytest.mark.asyncio
    async def test_detect_anomalies_with_dimension_schema(self, mock_server, mock_stat_tools):
        """Test anomaly detection with custom dimension schema."""
        anomalies = [{"value": 100, "dimension": "source_ip"}]
        mock_stat_tools.return_value.detect_zscore_anomalies.return_value = anomalies

        dimension_schema = {
            "field": "source_ip",
            "aggregation": "cardinality"
        }

        # Test with dimension schema
        from mcp_server import DShieldMCPServer
        result = await DShieldMCPServer._detect_statistical_anomalies(
            mock_server,
            {
                "anomaly_methods": ["zscore"],
                "dimension_schema": dimension_schema
            }
        )

        # Verify dimension schema is passed
        call_args = mock_stat_tools.return_value.detect_zscore_anomalies.call_args
        assert call_args.kwargs["dimension_schema"] == dimension_schema


@pytest.mark.skip(reason="Blocked by MCP namespace collision - Issue #124")
class TestHandlerIntegration:
    """Integration tests for handler methods."""

    @pytest.mark.asyncio
    async def test_handlers_registered_with_dispatcher(self):
        """Test that new handlers are properly registered with the dispatcher."""
        # This test would verify that the handlers are registered
        # Will be implemented once namespace collision is fixed
        pass

    @pytest.mark.asyncio
    async def test_handler_error_handling(self):
        """Test that handlers properly handle errors."""
        # This test would verify error handling in handlers
        # Will be implemented once namespace collision is fixed
        pass
