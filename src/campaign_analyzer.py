#!/usr/bin/env python3
"""Campaign Analysis Engine for DShield MCP.

Core campaign correlation and analysis engine for identifying coordinated attack campaigns.
"""

import asyncio
import json
import re
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from enum import Enum
import structlog

from .models import SecurityEvent
from .elasticsearch_client import ElasticsearchClient
from .user_config import get_user_config

logger = structlog.get_logger(__name__)


class CorrelationMethod(Enum):
    """Correlation methods for campaign analysis."""

    IP_CORRELATION = "ip_correlation"
    INFRASTRUCTURE_CORRELATION = "infrastructure_correlation"
    BEHAVIORAL_CORRELATION = "behavioral_correlation"
    TEMPORAL_CORRELATION = "temporal_correlation"
    GEOSPATIAL_CORRELATION = "geospatial_correlation"
    SIGNATURE_CORRELATION = "signature_correlation"
    NETWORK_CORRELATION = "network_correlation"


class CampaignConfidence(Enum):
    """Campaign confidence levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class CampaignEvent:
    """Individual event within a campaign."""

    event_id: str
    timestamp: datetime
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    event_type: Optional[str] = None
    event_category: Optional[str] = None
    ttp_technique: Optional[str] = None
    ttp_tactic: Optional[str] = None
    user_agent: Optional[str] = None
    url: Optional[str] = None
    payload: Optional[str] = None
    confidence_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class IndicatorRelationship:
    """Relationship between indicators in a campaign."""

    source_indicator: str
    target_indicator: str
    relationship_type: str
    confidence_score: float
    evidence: List[str] = field(default_factory=list)
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None


@dataclass
class Campaign:
    """Campaign data model."""

    campaign_id: str
    confidence_score: float
    start_time: datetime
    end_time: datetime
    attack_vectors: List[str] = field(default_factory=list)
    related_indicators: List[str] = field(default_factory=list)
    suspected_actor: Optional[str] = None
    campaign_name: Optional[str] = None
    description: Optional[str] = None
    total_events: int = 0
    unique_ips: int = 0
    unique_targets: int = 0
    ttp_techniques: List[str] = field(default_factory=list)
    ttp_tactics: List[str] = field(default_factory=list)
    infrastructure_domains: List[str] = field(default_factory=list)
    geographic_regions: List[str] = field(default_factory=list)
    events: List[CampaignEvent] = field(default_factory=list)
    relationships: List[IndicatorRelationship] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CampaignAnalyzer:
    """Core campaign analysis and correlation engine.
    
    Provides methods for correlating security events, expanding indicators,
    and building campaign timelines for coordinated attack detection.
    """
    
    def __init__(self, es_client: Optional[ElasticsearchClient] = None) -> None:
        """Initialize the CampaignAnalyzer.
        
        Args:
            es_client: Optional ElasticsearchClient instance. If not provided, a new one is created.

        """
        self.es_client = es_client or ElasticsearchClient()
        self.user_config = get_user_config()
        
        # Campaign analysis configuration
        self.correlation_window_minutes = self.user_config.get_setting("campaign", "correlation_window_minutes")
        self.min_confidence_threshold = self.user_config.get_setting("campaign", "min_confidence_threshold")
        self.max_campaign_events = self.user_config.get_setting("campaign", "max_campaign_events")
        self.enable_geospatial_correlation = self.user_config.get_setting("campaign", "enable_geospatial_correlation")
        
        # Performance tracking
        self.enable_performance_logging = self.user_config.get_setting("logging", "enable_performance_logging")
        
        # Enhanced correlation settings
        self.network_correlation_enabled = True
        self.behavioral_pattern_threshold = 0.6
        self.temporal_clustering_threshold = 0.7
    
    async def correlate_events(
        self,
        seed_events: List[Dict[str, Any]],
        correlation_criteria: List[CorrelationMethod],
        time_window_hours: int = 48,
        min_confidence: float = 0.7
    ) -> Campaign:
        """Correlate events based on specified criteria to identify campaigns.
        
        Args:
            seed_events: List of seed event dictionaries to start correlation from.
            correlation_criteria: List of CorrelationMethod enums to use for correlation.
            time_window_hours: Time window in hours to consider for correlation (default: 48).
            min_confidence: Minimum confidence threshold for campaign inclusion (default: 0.7).
        
        Returns:
            Campaign: The resulting Campaign object with correlated events and metadata.
        
        Raises:
            Exception: If campaign correlation fails.

        """
        start_time = datetime.now()
        logger.info("Starting campaign correlation", 
                   seed_events_count=len(seed_events),
                   correlation_criteria=[c.value for c in correlation_criteria],
                   time_window_hours=time_window_hours,
                   min_confidence=min_confidence)
        
        try:
            # Stage 1: Direct IOC matches
            correlated_events = await self._stage1_direct_ioc_matches(seed_events, time_window_hours)
            
            # Stage 2: Infrastructure correlation
            if CorrelationMethod.INFRASTRUCTURE_CORRELATION in correlation_criteria:
                correlated_events = await self._stage2_infrastructure_correlation(correlated_events, time_window_hours)
            
            # Stage 3: Behavioral correlation
            if CorrelationMethod.BEHAVIORAL_CORRELATION in correlation_criteria:
                correlated_events = await self._stage3_behavioral_correlation(correlated_events, time_window_hours)
            
            # Stage 4: Temporal correlation
            if CorrelationMethod.TEMPORAL_CORRELATION in correlation_criteria:
                correlated_events = await self._stage4_temporal_correlation(correlated_events, time_window_hours)
            
            # Stage 5: IP correlation
            if CorrelationMethod.IP_CORRELATION in correlation_criteria:
                correlated_events = await self._stage5_ip_correlation(correlated_events, time_window_hours)
            
            # Stage 6: Network correlation (NEW)
            if CorrelationMethod.NETWORK_CORRELATION in correlation_criteria:
                correlated_events = await self._stage6_network_correlation(correlated_events, time_window_hours)
            
            # Stage 7: Confidence scoring and filtering
            campaign = await self._stage7_confidence_scoring(correlated_events, min_confidence)
            
            # Calculate performance metrics
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            
            if self.enable_performance_logging:
                logger.info("Campaign correlation completed",
                           campaign_id=campaign.campaign_id,
                           total_events=campaign.total_events,
                           processing_time_seconds=processing_time,
                           confidence_score=campaign.confidence_score)
            
            return campaign
            
        except Exception as e:
            logger.error("Campaign correlation failed", error=str(e))
            raise
    
    async def expand_indicators(
        self,
        seed_iocs: List[str],
        expansion_strategy: str = "comprehensive",
        max_depth: int = 3
    ) -> List[IndicatorRelationship]:
        """Expand IOCs to find related indicators.
        
        Args:
            seed_iocs: List of seed indicators (IOCs) to expand.
            expansion_strategy: Strategy for expansion ('comprehensive', 'infrastructure', etc.).
            max_depth: Maximum expansion depth (default: 3).
        
        Returns:
            List of IndicatorRelationship objects representing discovered relationships.

        """
        logger.info("Expanding indicators", 
                   seed_iocs=seed_iocs,
                   expansion_strategy=expansion_strategy,
                   max_depth=max_depth)
        
        relationships: List[IndicatorRelationship] = []
        
        for depth in range(max_depth):
            current_iocs = seed_iocs if depth == 0 else [r.target_indicator for r in relationships]
            
            for ioc in current_iocs:
                # Find related indicators based on expansion strategy
                if expansion_strategy == "comprehensive":
                    related = await self._expand_ioc_comprehensive(ioc, depth)
                elif expansion_strategy == "infrastructure":
                    related = await self._expand_ioc_infrastructure(ioc, depth)
                elif expansion_strategy == "temporal":
                    related = await self._expand_ioc_temporal(ioc, depth)
                else:
                    related = await self._expand_ioc_comprehensive(ioc, depth)
                
                relationships.extend(related)
        
        # Remove duplicates and sort by confidence
        unique_relationships = self._deduplicate_relationships(relationships)
        unique_relationships.sort(key=lambda x: x.confidence_score, reverse=True)
        
        logger.info("Indicator expansion completed", 
                   seed_iocs_count=len(seed_iocs),
                   relationships_found=len(unique_relationships))
        
        return unique_relationships
    
    async def build_campaign_timeline(
        self, 
        correlated_events: List[CampaignEvent],
        timeline_granularity: str = "hourly"
    ) -> Dict[str, Any]:
        """Build chronological timeline of campaign events.
        
        Args:
            correlated_events: List of CampaignEvent objects to build timeline from.
            timeline_granularity: Granularity of timeline ('hourly', 'daily', 'minute').
        
        Returns:
            Dictionary containing timeline data with events grouped by time periods.

        """
        logger.info("Building campaign timeline",
                   events_count=len(correlated_events),
                   granularity=timeline_granularity)
        
        # Sort events by timestamp
        sorted_events = sorted(correlated_events, key=lambda x: x.timestamp)
        
        # Group events by time granularity
        timeline = {}
        
        for event in sorted_events:
            if timeline_granularity == "hourly":
                time_key = event.timestamp.strftime("%Y-%m-%d %H:00")
            elif timeline_granularity == "daily":
                time_key = event.timestamp.strftime("%Y-%m-%d")
            elif timeline_granularity == "minute":
                time_key = event.timestamp.strftime("%Y-%m-%d %H:%M")
            else:
                time_key = event.timestamp.strftime("%Y-%m-%d %H:00")
            
            if time_key not in timeline:
                timeline[time_key] = {
                    "events": [],
                    "event_count": 0,
                    "unique_ips": set(),
                    "attack_types": set(),
                    "ttp_techniques": set()
                }
            
            timeline[time_key]["events"].append({
                "event_id": event.event_id,
                "timestamp": event.timestamp.isoformat(),
                "source_ip": event.source_ip,
                "destination_ip": event.destination_ip,
                "event_type": event.event_type,
                "ttp_technique": event.ttp_technique,
                "confidence_score": event.confidence_score
            })
            
            timeline[time_key]["event_count"] += 1
            if event.source_ip:
                timeline[time_key]["unique_ips"].add(event.source_ip)
            if event.event_type:
                timeline[time_key]["attack_types"].add(event.event_type)
            if event.ttp_technique:
                timeline[time_key]["ttp_techniques"].add(event.ttp_technique)
        
        # Convert sets to lists for JSON serialization
        for time_key in timeline:
            timeline[time_key]["unique_ips"] = list(timeline[time_key]["unique_ips"])
            timeline[time_key]["attack_types"] = list(timeline[time_key]["attack_types"])
            timeline[time_key]["ttp_techniques"] = list(timeline[time_key]["ttp_techniques"])
        
        logger.info("Campaign timeline built",
                   timeline_periods=len(timeline),
                   total_events=len(correlated_events))
        
        return {
            "timeline": timeline,
            "granularity": timeline_granularity,
            "total_periods": len(timeline),
            "total_events": len(correlated_events)
        }
    
    async def score_campaign(self, campaign_data: Campaign) -> float:
        """Score campaign based on sophistication and impact.
        
        Args:
            campaign_data: Campaign object to score.
        
        Returns:
            Float score between 0.0 and 1.0 representing campaign sophistication.

        """
        score = 0.0
        
        # Factor 1: Event volume (0-25 points)
        event_volume_score = min(campaign_data.total_events / 100, 25)
        score += event_volume_score
        
        # Factor 2: Time span (0-20 points)
        time_span = (campaign_data.end_time - campaign_data.start_time).total_seconds() / 3600  # hours
        time_span_score = min(time_span / 24, 20)  # Max score for 24+ hours
        score += time_span_score
        
        # Factor 3: TTP sophistication (0-25 points)
        ttp_score = min(len(campaign_data.ttp_techniques) * 2, 25)
        score += ttp_score
        
        # Factor 4: Infrastructure complexity (0-15 points)
        infra_score = min(len(campaign_data.infrastructure_domains) * 3, 15)
        score += infra_score
        
        # Factor 5: Geographic spread (0-15 points)
        geo_score = min(len(campaign_data.geographic_regions) * 3, 15)
        score += geo_score
        
        # Normalize to 0-100 scale
        final_score = min(score, 100) / 100
        
        logger.info("Campaign scored",
                   campaign_id=campaign_data.campaign_id,
                   final_score=final_score,
                   factors={
                       "event_volume": event_volume_score,
                       "time_span": time_span_score,
                       "ttp_sophistication": ttp_score,
                       "infrastructure": infra_score,
                       "geographic": geo_score
                   })
        
        return final_score
    
    async def _stage1_direct_ioc_matches(
        self, 
        seed_events: List[Dict[str, Any]], 
        time_window_hours: int
    ) -> List[Dict[str, Any]]:
        """Stage 1: Direct IOC matches from seed events.
        
        Args:
            seed_events: List of seed event dictionaries.
            time_window_hours: Time window for correlation.
        
        Returns:
            List of correlated event dictionaries.

        """
        correlated_events = []
        
        for seed_event in seed_events:
            # Extract IOCs from seed event
            iocs = self._extract_iocs_from_event(seed_event)
            
            for ioc in iocs:
                # Query for events containing this IOC
                events = await self._query_events_by_ioc(ioc, time_window_hours)
                correlated_events.extend(events)
        
        # Remove duplicates
        unique_events = self._deduplicate_events(correlated_events)
        
        logger.info("Stage 1 completed", 
                   seed_events=len(seed_events),
                   correlated_events=len(unique_events))
        
        return unique_events
    
    async def _stage2_infrastructure_correlation(
        self, 
        events: List[Dict[str, Any]], 
        time_window_hours: int
    ) -> List[Dict[str, Any]]:
        """Stage 2: Infrastructure correlation (domains, certificates, hosting).
        
        Args:
            events: List of event dictionaries to correlate.
            time_window_hours: Time window for correlation.
        
        Returns:
            List of correlated event dictionaries.

        """
        correlated_events = events.copy()
        
        # Extract infrastructure indicators
        infrastructure_indicators = self._extract_infrastructure_indicators(events)
        
        for indicator in infrastructure_indicators:
            # Query for events with similar infrastructure
            related_events = await self._query_events_by_infrastructure(indicator, time_window_hours)
            correlated_events.extend(related_events)
        
        # Remove duplicates
        unique_events = self._deduplicate_events(correlated_events)
        
        logger.info("Stage 2 completed",
                   input_events=len(events),
                   infrastructure_indicators=len(infrastructure_indicators),
                   correlated_events=len(unique_events))
        
        return unique_events
    
    async def _stage3_behavioral_correlation(
        self, 
        events: List[Dict[str, Any]], 
        time_window_hours: int
    ) -> List[Dict[str, Any]]:
        """Stage 3: Behavioral correlation (similar attack patterns, timing, TTPs).
        
        Args:
            events: List of event dictionaries to correlate.
            time_window_hours: Time window for correlation.
        
        Returns:
            List of correlated event dictionaries.

        """
        logger.info("Starting behavioral correlation", events_count=len(events))
        
        try:
            correlated_events = events.copy()
            
            # Extract behavioral patterns
            behavioral_patterns = self._extract_behavioral_patterns(events)
            
            for pattern in behavioral_patterns:
                if pattern.get("confidence", 0) >= self.behavioral_pattern_threshold:
                    # Query for events with similar behavioral patterns
                    related_events = await self._query_events_by_behavioral_pattern(pattern, time_window_hours)
                    correlated_events.extend(related_events)
            
            # Enhanced: Analyze attack sequences and TTP patterns
            attack_sequences = self._analyze_attack_sequences(events)
            for sequence in attack_sequences:
                if sequence.get("sophistication_score", 0) >= 0.7:
                    # Find events that follow similar attack sequences
                    sequence_events = await self._query_events_by_sequence(sequence, time_window_hours)
                    correlated_events.extend(sequence_events)
            
            # Enhanced: User agent and payload analysis
            ua_patterns = self._extract_user_agent_patterns(events)
            payload_patterns = self._extract_payload_patterns(events)
            
            for pattern in ua_patterns + payload_patterns:
                if pattern.get("confidence", 0) >= 0.6:
                    pattern_events = await self._query_events_by_signature(pattern, time_window_hours)
                    correlated_events.extend(pattern_events)
            
            # Remove duplicates
            unique_events = self._deduplicate_events(correlated_events)
            
            logger.info("Behavioral correlation completed", 
                       original_events=len(events),
                       correlated_events=len(unique_events),
                       patterns_found=len(behavioral_patterns),
                       sequences_found=len(attack_sequences))
            
            return unique_events
            
        except Exception as e:
            logger.error("Behavioral correlation failed", error=str(e))
            return events
    
    async def _stage4_temporal_correlation(
        self, 
        events: List[Dict[str, Any]], 
        time_window_hours: int
    ) -> List[Dict[str, Any]]:
        """Stage 4: Temporal correlation (time-based clustering and proximity).
        
        Args:
            events: List of event dictionaries to correlate.
            time_window_hours: Time window for correlation.
        
        Returns:
            List of correlated event dictionaries.

        """
        correlated_events = events.copy()
        
        # Group events by time windows
        time_windows = self._create_time_windows(events, self.correlation_window_minutes)
        
        for window_start, window_end in time_windows:
            # Query for events in this time window
            window_events = await self._query_events_by_time_window(window_start, window_end)
            correlated_events.extend(window_events)
        
        # Remove duplicates
        unique_events = self._deduplicate_events(correlated_events)
        
        logger.info("Stage 4 completed",
                   input_events=len(events),
                   time_windows=len(time_windows),
                   correlated_events=len(unique_events))
        
        return unique_events
    
    async def _stage5_ip_correlation(
        self, 
        events: List[Dict[str, Any]], 
        time_window_hours: int
    ) -> List[Dict[str, Any]]:
        """Stage 5: IP correlation (same source IPs, IP ranges, ASNs).
        
        Args:
            events: List of event dictionaries to correlate.
            time_window_hours: Time window for correlation.
        
        Returns:
            List of correlated event dictionaries.

        """
        correlated_events = events.copy()
        
        # Extract IP addresses
        ip_addresses = self._extract_ip_addresses(events)
        
        for ip in ip_addresses:
            # Query for events from the same IP
            related_events = await self._query_events_by_ip(ip, time_window_hours)
            correlated_events.extend(related_events)
        
        # Remove duplicates
        unique_events = self._deduplicate_events(correlated_events)
        
        logger.info("Stage 5 completed",
                   input_events=len(events),
                   ip_addresses=len(ip_addresses),
                   correlated_events=len(unique_events))
        
        return unique_events
    
    async def _stage6_network_correlation(
        self, 
        events: List[Dict[str, Any]], 
        time_window_hours: int
    ) -> List[Dict[str, Any]]:
        """Stage 6: Network-based correlation using subnet analysis and routing patterns.
        
        Args:
            events: List of event dictionaries to correlate.
            time_window_hours: Time window for correlation.
        
        Returns:
            List of correlated event dictionaries.

        """
        logger.info("Starting network correlation", events_count=len(events))
        
        if not self.network_correlation_enabled:
            return events
        
        try:
            # Extract IP addresses
            source_ips = self._extract_ip_addresses(events)
            
            # Group IPs by subnet
            subnet_groups = self._group_ips_by_subnet(source_ips)
            
            # Find related events from same subnets
            correlated_events = events.copy()
            
            for subnet, ips in subnet_groups.items():
                if len(ips) >= 2:  # Only process subnets with multiple IPs
                    # Query events from related IPs in the same subnet
                    for ip in ips:
                        related_events = await self._query_events_by_ip(ip, time_window_hours)
                        correlated_events.extend(related_events)
            
            # Remove duplicates
            correlated_events = self._deduplicate_events(correlated_events)
            
            logger.info("Network correlation completed", 
                       original_events=len(events),
                       correlated_events=len(correlated_events))
            
            return correlated_events
            
        except Exception as e:
            logger.error("Network correlation failed", error=str(e))
            return events
    
    async def _stage7_confidence_scoring(
        self, 
        events: List[Dict[str, Any]], 
        min_confidence: float
    ) -> Campaign:
        """Stage 7: Confidence scoring and filtering.
        
        Args:
            events: List of event dictionaries to score.
            min_confidence: Minimum confidence threshold.
        
        Returns:
            Campaign object with scored and filtered events.

        """
        # Convert events to CampaignEvent objects
        campaign_events = []
        for event in events:
            campaign_event = self._convert_to_campaign_event(event)
            campaign_events.append(campaign_event)
        
        # Calculate confidence scores
        for event in campaign_events:
            event.confidence_score = self._calculate_event_confidence(event, campaign_events)
        
        # Filter by minimum confidence
        filtered_events = [e for e in campaign_events if e.confidence_score >= min_confidence]
        
        # Create campaign object
        campaign = self._create_campaign_from_events(filtered_events)
        
        # Score the campaign
        campaign.confidence_score = await self.score_campaign(campaign)
        
        logger.info("Stage 6 completed",
                   input_events=len(events),
                   filtered_events=len(filtered_events),
                   campaign_confidence=campaign.confidence_score)
        
        return campaign
    
    def _extract_iocs_from_event(self, event: Dict[str, Any]) -> List[str]:
        """Extract IOCs from an event.
        
        Args:
            event: Event dictionary to extract IOCs from.
        
        Returns:
            List of extracted IOCs (IPs, domains, user agents, etc.).

        """
        iocs = []
        
        # Extract IP addresses
        if "source.ip" in event:
            iocs.append(event["source.ip"])
        if "destination.ip" in event:
            iocs.append(event["destination.ip"])
        
        # Extract domains
        if "url" in event:
            domain = self._extract_domain_from_url(event["url"])
            if domain:
                iocs.append(domain)
        
        # Extract user agents
        if "user_agent.original" in event:
            iocs.append(event["user_agent.original"])
        
        return iocs
    
    def _extract_domain_from_url(self, url: str) -> Optional[str]:
        """Extract domain from URL.
        
        Args:
            url: URL string to extract domain from.
        
        Returns:
            Extracted domain or None if extraction fails.

        """
        try:
            import re
            domain_pattern = r'https?://([^/]+)'
            match = re.search(domain_pattern, url)
            return match.group(1) if match else None
        except:
            return None
    
    async def _query_events_by_ioc(self, ioc: str, time_window_hours: int) -> List[Dict[str, Any]]:
        """Query events containing a specific IOC.
        
        Args:
            ioc: Indicator of compromise to search for.
            time_window_hours: Time window for the query.
        
        Returns:
            List of event dictionaries containing the IOC.

        """
        try:
            # Build query filter for IOC
            filters = {
                "query": {
                    "bool": {
                        "should": [
                            {"term": {"source.ip": ioc}},
                            {"term": {"destination.ip": ioc}},
                            {"wildcard": {"url.original": f"*{ioc}*"}},
                            {"wildcard": {"user_agent.original": f"*{ioc}*"}}
                        ]
                    }
                }
            }
            
            events, _ = await self.es_client.query_dshield_events(
                time_range_hours=time_window_hours,
                filters=filters,
                page_size=100
            )
            
            return events
            
        except Exception as e:
            logger.error("Failed to query events by IOC", ioc=ioc, error=str(e))
            return []
    
    def _deduplicate_events(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate events based on event ID.
        
        Args:
            events: List of event dictionaries to deduplicate.
        
        Returns:
            List of unique event dictionaries.

        """
        seen_ids = set()
        unique_events = []
        
        for event in events:
            event_id = event.get("_id") or event.get("event_id")
            if event_id and event_id not in seen_ids:
                seen_ids.add(event_id)
                unique_events.append(event)
        
        return unique_events
    
    def _extract_infrastructure_indicators(self, events: List[Dict[str, Any]]) -> List[str]:
        """Extract infrastructure indicators from events.
        
        Args:
            events: List of event dictionaries to extract indicators from.
        
        Returns:
            List of infrastructure indicators (domains, certificates, etc.).

        """
        indicators = []
        
        for event in events:
            # Extract domains
            if "url" in event:
                domain = self._extract_domain_from_url(event["url"])
                if domain:
                    indicators.append(domain)
            
            # Extract certificates (if available)
            if "tls.certificate" in event:
                indicators.append(event["tls.certificate"])
        
        return list(set(indicators))
    
    def _extract_behavioral_patterns(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract behavioral patterns from events.
        
        Args:
            events: List of event dictionaries to analyze.
        
        Returns:
            List of behavioral pattern dictionaries.

        """
        patterns = []
        
        for event in events:
            pattern = {
                "event_type": event.get("event.type"),
                "ttp_technique": event.get("event.technique"),
                "user_agent": event.get("user_agent.original"),
                "payload_pattern": self._extract_payload_pattern(event)
            }
            patterns.append(pattern)
        
        return patterns
    
    def _extract_payload_pattern(self, event: Dict[str, Any]) -> Optional[str]:
        """Extract payload pattern from event.
        
        Args:
            event: Event dictionary to analyze.
        
        Returns:
            Extracted payload pattern or None if no pattern found.

        """
        # This is a simplified implementation
        # In a real system, you'd have more sophisticated payload analysis
        payload = event.get("payload") or event.get("request.body")
        if payload:
            # Extract common patterns (simplified)
            if "cmd.exe" in payload:
                return "command_execution"
            elif "powershell" in payload.lower():
                return "powershell_execution"
            elif "http" in payload.lower():
                return "http_communication"
        
        return None
    
    def _analyze_attack_sequences(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze attack sequences and TTP patterns.
        
        Args:
            events: List of event dictionaries to analyze.
        
        Returns:
            List of attack sequence dictionaries.

        """
        sequences = []
        
        # Sort events by timestamp
        sorted_events = sorted(events, key=lambda x: x.get("@timestamp", ""))
        
        # Look for common attack sequences
        sequence_patterns = [
            ["T1071", "T1041"],  # C2 -> Exfiltration
            ["T1021", "T1083"],  # Remote Services -> Discovery
            ["T1059", "T1071"],  # Command Execution -> C2
        ]
        
        for pattern in sequence_patterns:
            sequence_count = 0
            for i in range(len(sorted_events) - len(pattern) + 1):
                event_sequence = [e.get("event.technique") for e in sorted_events[i:i+len(pattern)]]
                if event_sequence == pattern:
                    sequence_count += 1
            
            if sequence_count > 0:
                sequence = {
                    "type": "attack_sequence",
                    "pattern": pattern,
                    "count": sequence_count,
                    "sophistication_score": min(sequence_count / 5, 1.0)
                }
                sequences.append(sequence)
        
        return sequences
    
    def _extract_user_agent_patterns(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract patterns from user agents."""
        patterns = []
        ua_counter = Counter()
        
        for event in events:
            ua = event.get("user_agent.original")
            if ua:
                ua_counter[ua] += 1
        
        # Find common user agents
        for ua, count in ua_counter.most_common(5):
            if count >= 2:
                pattern = {
                    "type": "user_agent_pattern",
                    "user_agent": ua,
                    "count": count,
                    "confidence": min(count / 10, 1.0)
                }
                patterns.append(pattern)
        
        return patterns
    
    def _extract_payload_patterns(self, events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract patterns from payloads."""
        patterns = []
        payload_counter = Counter()
        
        for event in events:
            payload = event.get("payload") or event.get("http.request.body.content")
            if payload:
                # Extract common payload signatures
                signatures = self._extract_payload_signatures(payload)
                for sig in signatures:
                    payload_counter[sig] += 1
        
        # Find common payload signatures
        for sig, count in payload_counter.most_common(5):
            if count >= 2:
                pattern = {
                    "type": "payload_pattern",
                    "signature": sig,
                    "count": count,
                    "confidence": min(count / 10, 1.0)
                }
                patterns.append(pattern)
        
        return patterns
    
    def _extract_payload_signatures(self, payload: str) -> List[str]:
        """Extract signatures from payload."""
        signatures = []
        
        # Common attack signatures
        attack_signatures = [
            "cmd.exe", "powershell", "wget", "curl", "base64",
            "eval(", "exec(", "system(", "shell_exec",
            "union select", "drop table", "insert into",
            "javascript:", "vbscript:", "onload=", "onerror="
        ]
        
        payload_lower = payload.lower()
        for sig in attack_signatures:
            if sig in payload_lower:
                signatures.append(sig)
        
        return signatures
    
    def _create_time_windows(
        self, 
        events: List[Dict[str, Any]], 
        window_minutes: int
    ) -> List[Tuple[datetime, datetime]]:
        """Create time windows for temporal correlation."""
        if not events:
            return []
        
        # Get time range from events
        timestamps = []
        for event in events:
            timestamp = event.get("@timestamp")
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                timestamps.append(timestamp)
        
        if not timestamps:
            return []
        
        min_time = min(timestamps)
        max_time = max(timestamps)
        
        # Create windows
        windows = []
        current_time = min_time
        
        while current_time <= max_time:
            window_end = current_time + timedelta(minutes=window_minutes)
            windows.append((current_time, window_end))
            current_time = window_end
        
        return windows
    
    async def _query_events_by_time_window(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Query events within a specific time window."""
        try:
            filters = {
                "@timestamp": {
                    "gte": start_time.isoformat(),
                    "lte": end_time.isoformat()
                }
            }
            
            events, _ = await self.es_client.query_dshield_events(
                time_range_hours=24,  # Use a reasonable default
                filters=filters,
                page_size=100
            )
            
            return events
            
        except Exception as e:
            logger.error("Failed to query events by time window", 
                        start_time=start_time, end_time=end_time, error=str(e))
            return []
    
    def _extract_ip_addresses(self, events: List[Dict[str, Any]]) -> List[str]:
        """Extract IP addresses from events."""
        ips = []
        
        for event in events:
            if "source.ip" in event:
                ips.append(event["source.ip"])
            if "destination.ip" in event:
                ips.append(event["destination.ip"])
        
        return list(set(ips))
    
    async def _query_events_by_ip(self, ip: str, time_window_hours: int) -> List[Dict[str, Any]]:
        """Query events from a specific IP address."""
        try:
            filters = {
                "source.ip": ip
            }
            
            events, _ = await self.es_client.query_dshield_events(
                time_range_hours=time_window_hours,
                filters=filters,
                page_size=100
            )
            
            return events
            
        except Exception as e:
            logger.error("Failed to query events by IP", ip=ip, error=str(e))
            return []
    
    async def _query_events_by_behavioral_pattern(self, pattern: Dict[str, Any], time_window_hours: int) -> List[Dict[str, Any]]:
        """Query events with similar behavioral patterns."""
        try:
            filters = {}
            
            if pattern.get("ttp_technique"):
                filters["event.technique"] = pattern["ttp_technique"]
            
            if pattern.get("user_agent"):
                filters["user_agent.original"] = pattern["user_agent"]
            
            events, _ = await self.es_client.query_dshield_events(
                time_range_hours=time_window_hours,
                filters=filters,
                page_size=100
            )
            
            return events
            
        except Exception as e:
            logger.error("Failed to query events by behavioral pattern", pattern=pattern, error=str(e))
            return []
    
    async def _query_events_by_sequence(self, sequence: Dict[str, Any], time_window_hours: int) -> List[Dict[str, Any]]:
        """Query events that follow similar attack sequences."""
        try:
            # Query for events with the first technique in the sequence
            if sequence.get("pattern") and len(sequence["pattern"]) > 0:
                filters = {
                    "event.technique": sequence["pattern"][0]
                }
                
                events, _ = await self.es_client.query_dshield_events(
                    time_range_hours=time_window_hours,
                    filters=filters,
                    page_size=100
                )
                
                return events
            
            return []
            
        except Exception as e:
            logger.error("Failed to query events by sequence", sequence=sequence, error=str(e))
            return []
    
    async def _query_events_by_signature(self, pattern: Dict[str, Any], time_window_hours: int) -> List[Dict[str, Any]]:
        """Query events with similar signatures."""
        try:
            # This is a simplified implementation
            # In a real system, you'd have more sophisticated signature matching
            
            events, _ = await self.es_client.query_dshield_events(
                time_range_hours=time_window_hours,
                filters={},
                page_size=50  # Limit results for signature queries
            )
            
            return events
            
        except Exception as e:
            logger.error("Failed to query events by signature", pattern=pattern, error=str(e))
            return []
    
    def _convert_to_campaign_event(self, event: Dict[str, Any]) -> CampaignEvent:
        """Convert raw event to CampaignEvent."""
        timestamp = event.get("@timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        
        return CampaignEvent(
            event_id=event.get("_id", ""),
            timestamp=timestamp or datetime.now(),
            source_ip=event.get("source.ip"),
            destination_ip=event.get("destination.ip"),
            event_type=event.get("event.type"),
            event_category=event.get("event.category"),
            ttp_technique=event.get("event.technique"),
            ttp_tactic=event.get("event.tactic"),
            user_agent=event.get("user_agent.original"),
            url=event.get("url.original"),
            payload=event.get("payload"),
            metadata=event
        )
    
    def _calculate_event_confidence(self, event: CampaignEvent, all_events: List[CampaignEvent]) -> float:
        """Calculate confidence score for an event."""
        confidence = 0.0
        
        # Factor 1: Event completeness (0-30 points)
        completeness_score = 0
        if event.source_ip:
            completeness_score += 5
        if event.destination_ip:
            completeness_score += 5
        if event.event_type:
            completeness_score += 5
        if event.ttp_technique:
            completeness_score += 10
        if event.user_agent:
            completeness_score += 5
        
        confidence += min(completeness_score, 30)
        
        # Factor 2: TTP sophistication (0-40 points)
        if event.ttp_technique:
            # More sophisticated TTPs get higher scores
            ttp_scores = {
                "T1059": 40,  # Command and Scripting Interpreter
                "T1071": 35,  # Application Layer Protocol
                "T1041": 30,  # Exfiltration Over C2 Channel
                "T1021": 25,  # Remote Services
                "T1083": 20,  # File and Directory Discovery
            }
            confidence += ttp_scores.get(event.ttp_technique, 10)
        
        # Factor 3: Temporal proximity to other events (0-30 points)
        if len(all_events) > 1:
            time_proximity_score = self._calculate_time_proximity_score(event, all_events)
            confidence += time_proximity_score
        
        # Normalize to 0-1 scale
        return min(confidence / 100, 1.0)
    
    def _calculate_time_proximity_score(self, event: CampaignEvent, all_events: List[CampaignEvent]) -> float:
        """Calculate time proximity score for an event."""
        if len(all_events) <= 1:
            return 0.0
        
        # Find events within 1 hour
        one_hour = timedelta(hours=1)
        nearby_events = 0
        
        for other_event in all_events:
            if other_event.event_id != event.event_id:
                time_diff = abs((event.timestamp - other_event.timestamp).total_seconds())
                if time_diff <= 3600:  # 1 hour in seconds
                    nearby_events += 1
        
        # Score based on number of nearby events
        return min(nearby_events * 5, 30)
    
    def _create_campaign_from_events(self, events: List[CampaignEvent]) -> Campaign:
        """Create a campaign from a list of events."""
        if not events:
            return Campaign(
                campaign_id="empty_campaign",
                confidence_score=0.0,
                start_time=datetime.now(),
                end_time=datetime.now()
            )
        
        # Calculate campaign metrics
        timestamps = [e.timestamp for e in events]
        start_time = min(timestamps)
        end_time = max(timestamps)
        
        source_ips = set()
        destination_ips = set()
        ttp_techniques = set()
        ttp_tactics = set()
        infrastructure_domains = set()
        
        for event in events:
            if event.source_ip:
                source_ips.add(event.source_ip)
            if event.destination_ip:
                destination_ips.add(event.destination_ip)
            if event.ttp_technique:
                ttp_techniques.add(event.ttp_technique)
            if event.ttp_tactic:
                ttp_tactics.add(event.ttp_tactic)
            if event.url:
                domain = self._extract_domain_from_url(event.url)
                if domain:
                    infrastructure_domains.add(domain)
        
        # Generate campaign ID
        campaign_id = f"campaign_{start_time.strftime('%Y%m%d_%H%M%S')}_{len(events)}"
        
        return Campaign(
            campaign_id=campaign_id,
            confidence_score=0.0,  # Will be calculated later
            start_time=start_time,
            end_time=end_time,
            attack_vectors=list(ttp_tactics),
            related_indicators=list(source_ips) + list(destination_ips),
            total_events=len(events),
            unique_ips=len(source_ips),
            unique_targets=len(destination_ips),
            ttp_techniques=list(ttp_techniques),
            ttp_tactics=list(ttp_tactics),
            infrastructure_domains=list(infrastructure_domains),
            events=events
        )
    
    async def _expand_ioc_comprehensive(self, ioc: str, depth: int) -> List[IndicatorRelationship]:
        """Comprehensive IOC expansion."""
        relationships = []
        
        # This is a simplified implementation
        # In a real system, you'd integrate with threat intelligence feeds
        
        # Simulate finding related indicators
        if depth < 2:  # Limit expansion depth
            # Simulate related indicators
            related_indicators = [
                f"related_{ioc}_1",
                f"related_{ioc}_2"
            ]
            
            for related in related_indicators:
                relationship = IndicatorRelationship(
                    source_indicator=ioc,
                    target_indicator=related,
                    relationship_type="infrastructure",
                    confidence_score=0.7 - (depth * 0.1),
                    first_seen=datetime.now(),
                    last_seen=datetime.now()
                )
                relationships.append(relationship)
        
        return relationships
    
    async def _expand_ioc_infrastructure(self, ioc: str, depth: int) -> List[IndicatorRelationship]:
        """Infrastructure-based IOC expansion."""
        # Similar to comprehensive but focused on infrastructure
        return await self._expand_ioc_comprehensive(ioc, depth)
    
    async def _expand_ioc_temporal(self, ioc: str, depth: int) -> List[IndicatorRelationship]:
        """Temporal-based IOC expansion."""
        # Similar to comprehensive but focused on temporal patterns
        return await self._expand_ioc_comprehensive(ioc, depth)
    
    def _deduplicate_relationships(self, relationships: List[IndicatorRelationship]) -> List[IndicatorRelationship]:
        """Remove duplicate relationships."""
        seen = set()
        unique_relationships = []
        
        for rel in relationships:
            key = (rel.source_indicator, rel.target_indicator, rel.relationship_type)
            if key not in seen:
                seen.add(key)
                unique_relationships.append(rel)
        
        return unique_relationships
    
    def _group_ips_by_subnet(self, ips: List[str], subnet_mask: int = 24) -> Dict[str, List[str]]:
        """Group IP addresses by subnet."""
        subnet_groups = defaultdict(list)
        
        for ip in ips:
            try:
                # Parse IP and get network
                ip_obj = ipaddress.IPv4Address(ip)
                network = ipaddress.IPv4Network(f"{ip_obj}/{subnet_mask}", strict=False)
                subnet_key = str(network.network_address)
                subnet_groups[subnet_key].append(ip)
            except Exception as e:
                logger.debug(f"Failed to parse IP {ip}: {e}")
                continue
        
        return dict(subnet_groups)
    
    async def _expand_ioc_network(self, ioc: str, depth: int) -> List[IndicatorRelationship]:
        """Network-based IOC expansion using subnet analysis."""
        relationships = []
        
        try:
            # Check if IOC is an IP address
            ip_obj = ipaddress.IPv4Address(ioc)
            
            # Find related IPs in the same subnet
            network = ipaddress.IPv4Network(f"{ip_obj}/24", strict=False)
            
            # Simulate finding related IPs in the same subnet
            if depth < 2:
                related_ips = [
                    str(ipaddress.IPv4Address(int(ip_obj) + 1)),
                    str(ipaddress.IPv4Address(int(ip_obj) + 2))
                ]
                
                for related_ip in related_ips:
                    relationship = IndicatorRelationship(
                        source_indicator=ioc,
                        target_indicator=related_ip,
                        relationship_type="network_subnet",
                        confidence_score=0.8 - (depth * 0.1),
                        first_seen=datetime.now(),
                        last_seen=datetime.now()
                    )
                    relationships.append(relationship)
        
        except Exception as e:
            logger.debug(f"Failed to expand network IOC {ioc}: {e}")
        
        return relationships 