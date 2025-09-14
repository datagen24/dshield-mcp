"""Fast smoke tests for StatisticalAnalysisTools using internal aggregation patch.

Avoid Elasticsearch by patching _get_anomaly_aggregations; exercise zscore path.
"""

from unittest.mock import Mock
import pytest

from src.statistical_analysis_tools import StatisticalAnalysisTools


@pytest.mark.asyncio
async def test_detect_anomalies_zscore_only(monkeypatch) -> None:
    # Provide a fake ES client to avoid constructor side-effects
    tools = StatisticalAnalysisTools(es_client=Mock())

    # Patch aggregations to return a minimal stats block
    async def fake_aggs(*args, **kwargs):  # type: ignore[no-redef]
        return {
            "bytes_transferred_stats": {
                "stats": {
                    "count": 10,
                    "avg": 100.0,
                    "std_deviation": 5.0,
                }
            }
        }

    monkeypatch.setattr(tools, "_get_anomaly_aggregations", fake_aggs)

    result = await tools.detect_statistical_anomalies(
        time_range_hours=1,
        anomaly_methods=["zscore"],
        sensitivity=2.0,
        dimensions=["bytes_transferred"],
        enable_iqr=False,
        return_summary_only=True,
    )

    assert result["success"] is True
    analysis = result["anomaly_analysis"]
    assert "zscore" in analysis["anomalies_by_method"]
    zs = analysis["anomalies_by_method"]["zscore"]
    assert isinstance(zs.get("count", 0), int)
    assert any(a.get("field") == "bytes_transferred" for a in zs.get("anomalies", []))

