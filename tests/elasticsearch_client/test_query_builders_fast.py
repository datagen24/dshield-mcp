"""Fast tests for ElasticsearchClient query builders.

Exercises _build_dshield_query and _build_ip_query with simple inputs.
"""

from datetime import UTC, datetime, timedelta

from src.elasticsearch_client import ElasticsearchClient


def test_build_dshield_query_basic() -> None:
    client = ElasticsearchClient()
    now = datetime.now(UTC)
    start = now - timedelta(hours=1)
    q = client._build_dshield_query(start, now, {"event.kind": "alert", "tags": ["cowrie"]})

    must = q["query"]["bool"]["must"]
    should = q["query"]["bool"].get("should", [])
    filt = q["query"]["bool"]["filter"]
    assert any("range" in part and "@timestamp" in part["range"] for part in must)
    # term and terms must appear
    assert any("term" in f and "event.kind" in f["term"] for f in filt)
    assert any("terms" in f and "tags" in f["terms"] for f in filt)
    # dshield exists filters are present
    assert any(f.get("exists", {}).get("field") == "source.ip" for f in filt)
    assert any(f.get("exists", {}).get("field") == "destination.ip" for f in filt)


def test_build_ip_query_includes_ips_and_range() -> None:
    client = ElasticsearchClient()
    now = datetime.now(UTC)
    start = now - timedelta(hours=2)
    ips = ["1.2.3.4", "5.6.7.8"]
    q = client._build_ip_query(ips, start, now)
    must = q["query"]["bool"]["must"]
    should = q["query"]["bool"].get("should", [])
    # Range present
    assert any("range" in part and "@timestamp" in part["range"] for part in must)
    # Source ip terms present
    assert any("terms" in part and "source.ip" in part["terms"] for part in must)
    # Destination ip terms present (in should)
    assert any("terms" in part and "destination.ip" in part["terms"] for part in should)
