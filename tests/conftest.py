"""Pytest configuration and common fixtures for DShield MCP tests."""

import pytest
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.models import SecurityEvent, ThreatIntelligence, DShieldAttack, DShieldReputation


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_elasticsearch_client():
    """Mock Elasticsearch client for testing."""
    mock_client = Mock()
    mock_client.connect = AsyncMock()
    mock_client.close = AsyncMock()
    mock_client.query_dshield_events = AsyncMock(return_value=[])
    mock_client.query_dshield_attacks = AsyncMock(return_value=[])
    mock_client.query_dshield_reputation = AsyncMock(return_value=[])
    mock_client.query_dshield_top_attackers = AsyncMock(return_value=[])
    mock_client.query_dshield_geographic_data = AsyncMock(return_value=[])
    mock_client.query_dshield_port_data = AsyncMock(return_value=[])
    mock_client.get_dshield_statistics = AsyncMock(return_value={})
    mock_client.query_events_by_ip = AsyncMock(return_value=[])
    return mock_client


@pytest.fixture
def mock_dshield_client():
    """Mock DShield client for testing."""
    mock_client = Mock()
    mock_client.connect = AsyncMock()
    mock_client.close = AsyncMock()
    mock_client.get_ip_reputation = AsyncMock(return_value={})
    mock_client.get_ip_details = AsyncMock(return_value={})
    mock_client.get_top_attackers = AsyncMock(return_value=[])
    mock_client.get_attack_summary = AsyncMock(return_value={})
    mock_client.enrich_ips_batch = AsyncMock(return_value={})
    return mock_client


@pytest.fixture
def sample_security_events():
    """Sample security events for testing."""
    return [
        {
            "timestamp": "2024-01-01T10:00:00Z",
            "source_ip": "192.168.1.100",
            "destination_ip": "10.0.0.1",
            "source_port": 12345,
            "destination_port": 80,
            "protocol": "TCP",
            "event_type": "attack",
            "severity": "high",
            "category": "brute_force",
            "description": "Brute force attack detected",
            "country": "US",
            "asn": "AS12345",
            "organization": "Test Org",
            "reputation_score": 85,
            "attack_count": 1000,
            "first_seen": "2024-01-01T09:00:00Z",
            "last_seen": "2024-01-01T10:00:00Z",
            "tags": ["brute_force", "ssh"],
            "attack_types": ["ssh_brute_force"],
            "port": 22,
            "service": "ssh"
        },
        {
            "timestamp": "2024-01-01T11:00:00Z",
            "source_ip": "203.0.113.1",
            "destination_ip": "10.0.0.2",
            "source_port": 54321,
            "destination_port": 443,
            "protocol": "TCP",
            "event_type": "scan",
            "severity": "medium",
            "category": "reconnaissance",
            "description": "Port scan detected",
            "country": "CN",
            "asn": "AS67890",
            "organization": "Another Org",
            "reputation_score": 60,
            "attack_count": 500,
            "first_seen": "2024-01-01T10:30:00Z",
            "last_seen": "2024-01-01T11:00:00Z",
            "tags": ["port_scan", "reconnaissance"],
            "attack_types": ["port_scan"],
            "port": 443,
            "service": "https"
        }
    ]


@pytest.fixture
def sample_threat_intelligence():
    """Sample threat intelligence data for testing."""
    return {
        "192.168.1.100": {
            "ip_address": "192.168.1.100",
            "reputation_score": 85,
            "threat_level": "high",
            "attack_count": 1000,
            "first_seen": "2024-01-01T09:00:00Z",
            "last_seen": "2024-01-01T10:00:00Z",
            "country": "US",
            "asn": "AS12345",
            "organization": "Test Org",
            "attack_types": ["ssh_brute_force", "port_scan"],
            "tags": ["brute_force", "ssh", "malicious"]
        },
        "203.0.113.1": {
            "ip_address": "203.0.113.1",
            "reputation_score": 60,
            "threat_level": "medium",
            "attack_count": 500,
            "first_seen": "2024-01-01T10:30:00Z",
            "last_seen": "2024-01-01T11:00:00Z",
            "country": "CN",
            "asn": "AS67890",
            "organization": "Another Org",
            "attack_types": ["port_scan"],
            "tags": ["port_scan", "reconnaissance"]
        }
    }


@pytest.fixture
def mock_op_secrets():
    """Mock 1Password secrets for testing."""
    with patch('src.op_secrets.op_secrets') as mock:
        mock.op_available = True
        mock.resolve_op_url.return_value = "resolved_secret"
        mock.resolve_environment_variable.return_value = "resolved_secret"
        yield mock


@pytest.fixture
def test_env_vars():
    """Test environment variables."""
    return {
        "ELASTICSEARCH_URL": "https://test-elasticsearch:9200",
        "ELASTICSEARCH_USERNAME": "test_user",
        "ELASTICSEARCH_PASSWORD": "test_password",
        "DSHIELD_API_KEY": "test_api_key",
        "DSHIELD_API_URL": "https://test-dshield.org/api",
        "LOG_LEVEL": "INFO",
        "RATE_LIMIT_REQUESTS_PER_MINUTE": "60",
        "MAX_QUERY_RESULTS": "1000",
        "QUERY_TIMEOUT_SECONDS": "30"
    }


@pytest.fixture
def test_op_env_vars():
    """Test environment variables with 1Password URLs."""
    return {
        "ELASTICSEARCH_URL": "https://test-elasticsearch:9200",
        "ELASTICSEARCH_USERNAME": "test_user",
        "ELASTICSEARCH_PASSWORD": "op://vault/elasticsearch/password",
        "DSHIELD_API_KEY": "op://vault/dshield/api-key",
        "DSHIELD_API_URL": "https://test-dshield.org/api",
        "LOG_LEVEL": "INFO"
    } 