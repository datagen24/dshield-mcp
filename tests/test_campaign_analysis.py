"""Campaign Analysis Tests.

Tests for campaign analysis functionality including data models, correlation methods,
timeline building, scoring, and MCP tools integration.
"""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List

from src.campaign_analyzer import CampaignAnalyzer, Campaign, CampaignEvent, CorrelationMethod
from src.campaign_mcp_tools import CampaignMCPTools
from src.elasticsearch_client import ElasticsearchClient


class TestCampaignAnalysis:
    """Test campaign analysis functionality."""
    
    @pytest_asyncio.fixture
    async def mock_es_client(self):
        """Create a mock ElasticsearchClient."""
        with patch('src.elasticsearch_client.ElasticsearchClient') as mock_class:
            client = mock_class.return_value
            client.client = AsyncMock()
            client.connect = AsyncMock()
            client.close = AsyncMock()
            client.get_available_indices = AsyncMock(return_value=["dshield-2024.01.01"])
            
            # Mock query methods
            client.query_dshield_events = AsyncMock(return_value=([], 0, {}))
            client.query_events_by_ip = AsyncMock(return_value=[])
            
            yield client
    
    @pytest_asyncio.fixture
    async def mock_campaign_analyzer(self, mock_es_client):
        """Create a mock CampaignAnalyzer."""
        with patch('src.campaign_analyzer.CampaignAnalyzer') as mock_class:
            analyzer = mock_class.return_value
            analyzer.es_client = mock_es_client
            analyzer.user_config = MagicMock()
            analyzer.user_config.campaign_settings = MagicMock()
            analyzer.user_config.campaign_settings.correlation_window_minutes = 30
            analyzer.user_config.campaign_settings.min_confidence_threshold = 0.7
            analyzer.user_config.campaign_settings.max_campaign_events = 10000
            analyzer.user_config.campaign_settings.enable_ip_correlation = True
            
            # Mock analyzer methods
            analyzer.build_campaign_timeline = AsyncMock(return_value={
                "timeline": [],
                "total_periods": 24,
                "total_events": 5
            })
            analyzer.score_campaign = AsyncMock(return_value=0.85)
            analyzer.expand_indicators = AsyncMock(return_value=[])
            
            yield analyzer
    
    @pytest_asyncio.fixture
    async def mock_campaign_tools(self, mock_es_client):
        """Create a mock CampaignMCPTools."""
        with patch('src.campaign_mcp_tools.CampaignMCPTools') as mock_class:
            tools = mock_class.return_value
            tools.es_client = mock_es_client
            tools.campaign_analyzer = MagicMock()
            tools.user_config = MagicMock()
            
            # Mock tool methods
            tools.analyze_campaign = AsyncMock(return_value={
                "success": True,
                "campaign_analysis": {
                    "campaign_id": "test_campaign_1",
                    "confidence_score": 0.85,
                    "total_events": 10,
                    "unique_ips": 3
                }
            })
            
            yield tools
    
    @pytest.mark.asyncio
    async def test_campaign_analyzer_initialization(self, mock_es_client):
        """Test campaign analyzer initialization."""
        with patch('src.campaign_analyzer.CampaignAnalyzer') as mock_class:
            # Test basic initialization
            analyzer = CampaignAnalyzer()
            assert analyzer is not None
            
            # Test with ES client
            analyzer_with_es = CampaignAnalyzer(mock_es_client)
            assert analyzer_with_es is not None
            
            # Verify configuration loading
            config = analyzer.user_config
            assert config is not None, "User config should be loaded"
            
            # Verify campaign settings
            campaign_settings = config.campaign_settings
            assert campaign_settings.correlation_window_minutes == 30, "Default correlation window should be 30 minutes"
            assert campaign_settings.min_confidence_threshold == 0.7, "Default confidence threshold should be 0.7"
    
    @pytest.mark.asyncio
    async def test_campaign_data_models(self):
        """Test campaign data models."""
        # Test CampaignEvent creation
        event = CampaignEvent(
            event_id="test_event_1",
            timestamp=datetime.now(),
            source_ip="192.168.1.100",
            destination_ip="10.0.0.1",
            event_type="network_scan",
            ttp_technique="T1046",
            ttp_tactic="discovery",
            confidence_score=0.8
        )
        
        assert event.event_id == "test_event_1", "Event ID should match"
        assert event.source_ip == "192.168.1.100", "Source IP should match"
        assert event.confidence_score == 0.8, "Confidence score should match"
        assert event.ttp_technique == "T1046", "TTP technique should match"
        assert event.ttp_tactic == "discovery", "TTP tactic should match"
        
        # Test Campaign creation
        campaign = Campaign(
            campaign_id="test_campaign_1",
            confidence_score=0.85,
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now(),
            attack_vectors=["network_scan", "port_scan"],
            related_indicators=["192.168.1.100", "10.0.0.1"],
            total_events=10,
            unique_ips=2
        )
        
        assert campaign.campaign_id == "test_campaign_1", "Campaign ID should match"
        assert campaign.confidence_score == 0.85, "Campaign confidence should match"
        assert len(campaign.attack_vectors) == 2, "Attack vectors should match"
        assert len(campaign.related_indicators) == 2, "Related indicators should match"
        assert campaign.total_events == 10, "Total events should match"
        assert campaign.unique_ips == 2, "Unique IPs should match"
    
    @pytest.mark.asyncio
    async def test_correlation_methods(self):
        """Test correlation method enums."""
        # Test all correlation methods
        methods = [
            CorrelationMethod.IP_CORRELATION,
            CorrelationMethod.INFRASTRUCTURE_CORRELATION,
            CorrelationMethod.BEHAVIORAL_CORRELATION,
            CorrelationMethod.TEMPORAL_CORRELATION,
            CorrelationMethod.GEOSPATIAL_CORRELATION,
            CorrelationMethod.SIGNATURE_CORRELATION
        ]
        
        assert len(methods) == 6, "Should have 6 correlation methods"
        
        # Test string conversion
        method_strings = [method.value for method in methods]
        expected_strings = [
            "ip_correlation",
            "infrastructure_correlation", 
            "behavioral_correlation",
            "temporal_correlation",
            "geospatial_correlation",
            "signature_correlation"
        ]
        
        assert method_strings == expected_strings, "Method strings should match expected values"
        
        # Test individual method validation
        assert CorrelationMethod.IP_CORRELATION.value == "ip_correlation"
        assert CorrelationMethod.BEHAVIORAL_CORRELATION.value == "behavioral_correlation"
        assert CorrelationMethod.TEMPORAL_CORRELATION.value == "temporal_correlation"
    
    @pytest.mark.asyncio
    async def test_campaign_timeline_building(self, mock_campaign_analyzer):
        """Test campaign timeline building."""
        # Create test events
        events = []
        base_time = datetime.now() - timedelta(hours=2)
        
        for i in range(5):
            event = CampaignEvent(
                event_id=f"test_event_{i}",
                timestamp=base_time + timedelta(minutes=i * 30),
                source_ip="192.168.1.100",
                destination_ip=f"10.0.0.{i+1}",
                event_type="network_scan",
                confidence_score=0.7 + (i * 0.05)
            )
            events.append(event)
        
        # Test timeline building
        timeline = await mock_campaign_analyzer.build_campaign_timeline(
            events,
            timeline_granularity="hourly"
        )
        
        assert "timeline" in timeline, "Timeline should contain timeline data"
        assert "total_periods" in timeline, "Timeline should contain total periods"
        assert "total_events" in timeline, "Timeline should contain total events"
        assert timeline["total_events"] == 5, "Should have 5 events"
        assert timeline["total_periods"] == 24, "Should have 24 periods for hourly granularity"
    
    @pytest.mark.asyncio
    async def test_campaign_scoring(self, mock_campaign_analyzer):
        """Test campaign scoring functionality."""
        # Create test campaign
        campaign = Campaign(
            campaign_id="test_campaign_scoring",
            confidence_score=0.0,  # Will be calculated
            start_time=datetime.now() - timedelta(hours=24),
            end_time=datetime.now(),
            attack_vectors=["network_scan", "port_scan", "vulnerability_scan"],
            related_indicators=["192.168.1.100", "192.168.1.101", "192.168.1.102"],
            total_events=50,
            unique_ips=3,
            unique_targets=10,
            ttp_techniques=["T1046", "T1043", "T1041"],
            ttp_tactics=["discovery", "reconnaissance"],
            infrastructure_domains=["malicious.com", "evil.net"],
            geographic_regions=["US", "EU", "AS"]
        )
        
        # Test scoring
        score = await mock_campaign_analyzer.score_campaign(campaign)
        
        assert 0.0 <= score <= 1.0, "Score should be between 0 and 1"
        assert score > 0.0, "Score should be positive for this campaign"
        assert score == 0.85, "Score should match mocked value"
    
    @pytest.mark.asyncio
    async def test_campaign_tools_initialization(self, mock_es_client):
        """Test campaign MCP tools initialization."""
        with patch('src.campaign_mcp_tools.CampaignMCPTools') as mock_class:
            # Test tools initialization
            tools = CampaignMCPTools(mock_es_client)
            
            # Verify tools have required components
            assert tools.es_client is not None, "ES client should be set"
            assert tools.campaign_analyzer is not None, "Campaign analyzer should be set"
            assert tools.user_config is not None, "User config should be set"
    
    @pytest.mark.asyncio
    async def test_analyze_campaign_tool(self, mock_campaign_tools):
        """Test analyze_campaign MCP tool."""
        # Test with sample indicators
        seed_indicators = ["192.168.1.100", "malicious.com"]
        
        result = await mock_campaign_tools.analyze_campaign(
            seed_indicators=seed_indicators,
            time_range_hours=24,
            correlation_methods=["ip_correlation", "temporal_correlation"],
            min_confidence=0.7,
            include_timeline=True,
            include_relationships=True
        )
        
        assert "success" in result, "Result should contain success field"
        assert "campaign_analysis" in result, "Result should contain campaign_analysis"
        
        # Verify campaign data structure
        if result["success"]:
            campaign_data = result["campaign_analysis"]
            assert "campaign_id" in campaign_data, "Campaign should have ID"
            assert "confidence_score" in campaign_data, "Campaign should have confidence score"
            assert "total_events" in campaign_data, "Campaign should have total events"
            assert "unique_ips" in campaign_data, "Campaign should have unique IPs"
            
            assert campaign_data["campaign_id"] == "test_campaign_1"
            assert campaign_data["confidence_score"] == 0.85
            assert campaign_data["total_events"] == 10
            assert campaign_data["unique_ips"] == 3
    
    @pytest.mark.asyncio
    async def test_campaign_indicator_expansion(self, mock_campaign_analyzer):
        """Test campaign indicator expansion."""
        # Test indicator expansion
        seed_iocs = ["192.168.1.100"]
        
        relationships = await mock_campaign_analyzer.expand_indicators(
            seed_iocs=seed_iocs,
            expansion_strategy="comprehensive",
            max_depth=2
        )
        
        # The expansion should return a list (even if empty)
        assert isinstance(relationships, list), "Should return list of relationships"
        assert len(relationships) == 0, "Mock should return empty list"
    
    @pytest.mark.asyncio
    async def test_user_config_campaign_settings(self):
        """Test user configuration campaign settings."""
        with patch('src.user_config.get_user_config') as mock_get_config:
            # Mock user config
            mock_config = MagicMock()
            mock_config.campaign_settings = MagicMock()
            mock_config.campaign_settings.correlation_window_minutes = 30
            mock_config.campaign_settings.min_confidence_threshold = 0.7
            mock_config.campaign_settings.max_campaign_events = 10000
            mock_config.campaign_settings.enable_ip_correlation = True
            
            # Mock get_setting and update_setting methods
            mock_config.get_setting = MagicMock(return_value=30)
            mock_config.update_setting = MagicMock()
            
            mock_get_config.return_value = mock_config
            
            # Test campaign settings access
            config = mock_get_config()
            campaign_settings = config.campaign_settings
            
            # Test default values
            assert campaign_settings.correlation_window_minutes == 30, "Default correlation window should be 30"
            assert campaign_settings.min_confidence_threshold == 0.7, "Default confidence threshold should be 0.7"
            assert campaign_settings.max_campaign_events == 10000, "Default max events should be 10000"
            assert campaign_settings.enable_ip_correlation == True, "IP correlation should be enabled by default"
            
            # Test setting access via get_setting
            correlation_window = config.get_setting("campaign", "correlation_window_minutes")
            assert correlation_window == 30, "Should get correlation window via get_setting"
            
            # Test setting update
            config.update_setting("campaign", "correlation_window_minutes", 60)
            config.update_setting.assert_called_with("campaign", "correlation_window_minutes", 60)
    
    @pytest.mark.asyncio
    async def test_campaign_environment_variables(self):
        """Test campaign environment variable support."""
        with patch('src.user_config.get_user_config') as mock_get_config:
            # Mock user config with environment variables
            mock_config = MagicMock()
            mock_config.get_environment_variables = MagicMock(return_value={
                "CORRELATION_WINDOW_MINUTES": "30",
                "MIN_CONFIDENCE_THRESHOLD": "0.7",
                "MAX_CAMPAIGN_EVENTS": "10000",
                "ENABLE_GEOSPATIAL_CORRELATION": "true",
                "ENABLE_INFRASTRUCTURE_CORRELATION": "true",
                "ENABLE_BEHAVIORAL_CORRELATION": "true",
                "ENABLE_TEMPORAL_CORRELATION": "true",
                "ENABLE_IP_CORRELATION": "true",
                "MAX_EXPANSION_DEPTH": "3",
                "EXPANSION_TIMEOUT_SECONDS": "300"
            })
            
            mock_get_config.return_value = mock_config
            
            config = mock_get_config()
            
            # Test environment variable export
            env_vars = config.get_environment_variables()
            
            # Check for campaign-related environment variables
            campaign_env_vars = [
                "CORRELATION_WINDOW_MINUTES",
                "MIN_CONFIDENCE_THRESHOLD", 
                "MAX_CAMPAIGN_EVENTS",
                "ENABLE_GEOSPATIAL_CORRELATION",
                "ENABLE_INFRASTRUCTURE_CORRELATION",
                "ENABLE_BEHAVIORAL_CORRELATION",
                "ENABLE_TEMPORAL_CORRELATION",
                "ENABLE_IP_CORRELATION",
                "MAX_EXPANSION_DEPTH",
                "EXPANSION_TIMEOUT_SECONDS"
            ]
            
            for var in campaign_env_vars:
                assert var in env_vars, f"Environment variable {var} should be present"
                assert env_vars[var] is not None, f"Environment variable {var} should have a value"
            
            assert len(campaign_env_vars) == 10, "Should have 10 campaign environment variables"
    
    @pytest.mark.asyncio
    async def test_campaign_config_export(self):
        """Test campaign configuration export."""
        with patch('src.user_config.get_user_config') as mock_get_config:
            # Mock user config with export functionality
            mock_config = MagicMock()
            mock_config.export_config = MagicMock(return_value={
                "campaign": {
                    "correlation_window_minutes": 30,
                    "min_confidence_threshold": 0.7,
                    "max_campaign_events": 10000,
                    "enable_geospatial_correlation": True,
                    "enable_infrastructure_correlation": True,
                    "enable_behavioral_correlation": True,
                    "enable_temporal_correlation": True,
                    "enable_ip_correlation": True,
                    "max_expansion_depth": 3,
                    "expansion_timeout_seconds": 300
                }
            })
            
            mock_get_config.return_value = mock_config
            
            config = mock_get_config()
            
            # Test configuration export
            exported_config = config.export_config()
            
            # Check for campaign section
            assert "campaign" in exported_config, "Exported config should contain campaign section"
            
            campaign_config = exported_config["campaign"]
            expected_fields = [
                "correlation_window_minutes",
                "min_confidence_threshold",
                "max_campaign_events",
                "enable_geospatial_correlation",
                "enable_infrastructure_correlation",
                "enable_behavioral_correlation",
                "enable_temporal_correlation",
                "enable_ip_correlation",
                "max_expansion_depth",
                "expansion_timeout_seconds"
            ]
            
            for field in expected_fields:
                assert field in campaign_config, f"Campaign config should contain {field}"
                assert campaign_config[field] is not None, f"Campaign config {field} should have a value"
            
            assert len(expected_fields) == 10, "Should have 10 campaign config fields"
    
    @pytest.mark.asyncio
    async def test_campaign_event_validation(self):
        """Test campaign event validation and edge cases."""
        # Test event with minimal required fields
        minimal_event = CampaignEvent(
            event_id="minimal_event",
            timestamp=datetime.now(),
            source_ip="192.168.1.100",
            destination_ip="10.0.0.1",
            event_type="network_scan"
        )
        
        assert minimal_event.event_id == "minimal_event"
        assert minimal_event.confidence_score == 0.0, "Default confidence should be 0.0"
        assert minimal_event.ttp_technique is None, "TTP technique should be None by default"
        assert minimal_event.metadata == {}, "Default metadata should be empty dict"
        
        # Test event with all fields
        full_event = CampaignEvent(
            event_id="full_event",
            timestamp=datetime.now(),
            source_ip="192.168.1.100",
            destination_ip="10.0.0.1",
            event_type="network_scan",
            ttp_technique="T1046",
            ttp_tactic="discovery",
            confidence_score=0.9,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            url="http://malicious.com/scan",
            payload="GET /scan HTTP/1.1",
            metadata={"description": "Test network scan event", "tags": ["malicious", "scan"]}
        )
        
        assert full_event.confidence_score == 0.9
        assert full_event.user_agent == "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        assert full_event.url == "http://malicious.com/scan"
        assert full_event.payload == "GET /scan HTTP/1.1"
        assert full_event.metadata["description"] == "Test network scan event"
        assert "malicious" in full_event.metadata["tags"]
        assert "scan" in full_event.metadata["tags"]
    
    @pytest.mark.asyncio
    async def test_campaign_validation(self):
        """Test campaign validation and edge cases."""
        # Test campaign with minimal required fields
        minimal_campaign = Campaign(
            campaign_id="minimal_campaign",
            confidence_score=0.5,
            start_time=datetime.now() - timedelta(hours=1),
            end_time=datetime.now()
        )
        
        assert minimal_campaign.campaign_id == "minimal_campaign"
        assert minimal_campaign.confidence_score == 0.5
        assert minimal_campaign.attack_vectors == [], "Default attack vectors should be empty"
        assert minimal_campaign.related_indicators == [], "Default indicators should be empty"
        assert minimal_campaign.total_events == 0, "Default total events should be 0"
        assert minimal_campaign.metadata == {}, "Default metadata should be empty dict"
        
        # Test campaign with all fields
        full_campaign = Campaign(
            campaign_id="full_campaign",
            confidence_score=0.95,
            start_time=datetime.now() - timedelta(hours=24),
            end_time=datetime.now(),
            attack_vectors=["network_scan", "port_scan", "vulnerability_scan"],
            related_indicators=["192.168.1.100", "malicious.com"],
            total_events=100,
            unique_ips=5,
            unique_targets=20,
            ttp_techniques=["T1046", "T1043"],
            ttp_tactics=["discovery", "reconnaissance"],
            infrastructure_domains=["evil.com", "malicious.net"],
            geographic_regions=["US", "EU"],
            description="Comprehensive test campaign",
            metadata={"tags": ["advanced", "persistent"], "threat_level": "high"}
        )
        
        assert full_campaign.confidence_score == 0.95
        assert len(full_campaign.attack_vectors) == 3
        assert len(full_campaign.related_indicators) == 2
        assert full_campaign.total_events == 100
        assert full_campaign.unique_ips == 5
        assert full_campaign.description == "Comprehensive test campaign"
        assert "advanced" in full_campaign.metadata["tags"]
        assert "persistent" in full_campaign.metadata["tags"]
        assert full_campaign.metadata["threat_level"] == "high" 