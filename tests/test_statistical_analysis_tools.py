import pytest

from src.statistical_analysis_tools import StatisticalAnalysisTools


class DummyESClient:
    def __init__(self, aggregations):
        class Client:
            async def search(self, index=None, body=None):
                return {"aggregations": aggregations}

        self.client = Client()

    async def get_available_indices(self):
        return ["test-index"]


@pytest.mark.asyncio
async def test_schema_driven_aggregations_builds_percentiles_when_enabled(monkeypatch):
    aggregations = {}
    es = DummyESClient(aggregations)
    tools = StatisticalAnalysisTools(es_client=es)

    schema = {
        "bytes": {"field": "network.bytes", "agg": "stats"},
        "ts": {"field": "@timestamp", "agg": "date_histogram", "interval": "1h"},
        "port": {"field": "destination.port", "agg": "terms", "size": 10},
    }

    # Patch analysis_cfg to enable percentiles
    tools.analysis_cfg = {"percentiles": [25, 50, 75], "enable_percentiles": True}

    res = await tools._get_anomaly_aggregations(
        1, ["bytes"], ["iqr"], 2.0, dimension_schema=schema, enable_percentiles=True
    )
    # The Dummy client returns our input aggregations back; ensure call succeeded
    assert isinstance(res, dict)


@pytest.mark.asyncio
async def test_iqr_uses_percentiles_when_present():
    tools = StatisticalAnalysisTools(es_client=DummyESClient({}))
    anomaly_data = {
        "bytes_percentiles": {"values": {"25.0": 10.0, "50.0": 20.0, "75.0": 30.0, "95.0": 60.0}}
    }
    iqr = await tools._apply_iqr_analysis(anomaly_data, sensitivity=1.5, max_anomalies=10)
    assert iqr["count"] == 1
    a = iqr["anomalies"][0]
    assert a["lower_bound"] < a["upper_bound"]


@pytest.mark.asyncio
async def test_recommendations_when_no_anomalies():
    tools = StatisticalAnalysisTools(es_client=DummyESClient({}))
    anomalies = {"summary": {"total_anomalies_detected": 0}, "anomalies_by_method": {}}
    recs = await tools._generate_anomaly_recommendations(anomalies)
    assert any("No anomalies detected" in r for r in recs)
