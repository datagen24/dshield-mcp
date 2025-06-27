"""
Elasticsearch client for querying DShield SIEM events and logs.
Optimized for DShield SIEM integration patterns.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

import structlog
from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import RequestError, TransportError
from dotenv import load_dotenv

from .models import SecurityEvent, ElasticsearchQuery, QueryFilter
from .op_secrets import get_env_with_op_resolution

# Load environment variables
load_dotenv()

logger = structlog.get_logger(__name__)


class ElasticsearchClient:
    """Client for interacting with DShield SIEM Elasticsearch."""
    
    def __init__(self):
        self.client: Optional[AsyncElasticsearch] = None
        self.url = get_env_with_op_resolution("ELASTICSEARCH_URL", "http://localhost:9200")
        self.username = get_env_with_op_resolution("ELASTICSEARCH_USERNAME", "elastic")
        self.password = get_env_with_op_resolution("ELASTICSEARCH_PASSWORD", "")
        self.verify_ssl = get_env_with_op_resolution("ELASTICSEARCH_VERIFY_SSL", "true").lower() == "true"
        self.ca_certs = get_env_with_op_resolution("ELASTICSEARCH_CA_CERTS")
        self.timeout = int(get_env_with_op_resolution("QUERY_TIMEOUT_SECONDS", "30"))
        self.max_results = int(get_env_with_op_resolution("MAX_QUERY_RESULTS", "1000"))
        
        # DShield SIEM specific indices
        self.dshield_indices = [
            "dshield-*",           # DShield specific data
            "dshield-attacks-*",   # DShield attack data
            "dshield-blocks-*",    # DShield block data
            "dshield-reputation-*", # DShield reputation data
            "dshield-summary-*",   # DShield summary data
            "dshield-top-*",       # DShield top attackers/ports
            "dshield-geo-*",       # DShield geographic data
            "dshield-asn-*",       # DShield ASN data
            "dshield-org-*",       # DShield organization data
            "dshield-tags-*",      # DShield tag data
            "dshield-ports-*",     # DShield port data
            "dshield-countries-*", # DShield country data
            "dshield-protocols-*", # DShield protocol data
            "dshield-sources-*",   # DShield source data
            "dshield-targets-*",   # DShield target data
            "dshield-events-*",    # DShield event data
            "dshield-alerts-*",    # DShield alert data
            "dshield-logs-*",      # DShield log data
            "dshield-reports-*",   # DShield report data
            "dshield-statistics-*" # DShield statistics data
        ]
        
        # Fallback to general SIEM indices if DShield specific ones don't exist
        self.fallback_indices = ["logs-*", "security-*", "alerts-*", "zeek-*", "suricata-*"]
        
        # DShield specific field mappings
        self.dshield_field_mappings = {
            'timestamp': ['@timestamp', 'timestamp', 'time', 'date'],
            'source_ip': ['source.ip', 'src_ip', 'srcip', 'sourceip', 'attacker_ip', 'attackerip'],
            'destination_ip': ['destination.ip', 'dst_ip', 'dstip', 'destinationip', 'target_ip', 'targetip'],
            'source_port': ['source.port', 'src_port', 'srcport', 'sourceport', 'attacker_port'],
            'destination_port': ['destination.port', 'dst_port', 'dstport', 'destinationport', 'target_port'],
            'protocol': ['network.protocol', 'protocol', 'proto', 'transport_protocol'],
            'event_type': ['event.type', 'event_type', 'type', 'attack_type', 'dshield_type'],
            'severity': ['event.severity', 'severity', 'level', 'risk_level', 'threat_level'],
            'category': ['event.category', 'event_category', 'category', 'attack_category'],
            'description': ['event.description', 'message', 'description', 'summary', 'attack_description'],
            'country': ['geoip.country_name', 'country', 'country_name', 'attacker_country'],
            'asn': ['asn', 'as_number', 'autonomous_system', 'attacker_asn'],
            'organization': ['org', 'organization', 'org_name', 'attacker_org'],
            'reputation_score': ['reputation', 'reputation_score', 'dshield_score', 'threat_score'],
            'attack_count': ['count', 'attack_count', 'hits', 'attempts'],
            'first_seen': ['firstseen', 'first_seen', 'first_seen_date'],
            'last_seen': ['lastseen', 'last_seen', 'last_seen_date'],
            'tags': ['tags', 'attack_tags', 'threat_tags', 'dshield_tags'],
            'attack_types': ['attacks', 'attack_types', 'attack_methods'],
            'port': ['port', 'target_port', 'service_port'],
            'service': ['service', 'service_name', 'target_service']
        }
        
    async def connect(self):
        """Connect to Elasticsearch cluster."""
        try:
            # Parse URL to extract host and port
            parsed_url = urlparse(self.url)
            hosts = [{
                'host': parsed_url.hostname,
                'port': parsed_url.port or 9200,
                'scheme': parsed_url.scheme or 'http'
            }]
            
            # Configure SSL/TLS
            ssl_options = {}
            if self.verify_ssl and self.ca_certs:
                ssl_options['ca_certs'] = self.ca_certs
            elif not self.verify_ssl:
                ssl_options['verify_certs'] = False
                ssl_options['ssl_show_warn'] = False
            
            # Create client
            self.client = AsyncElasticsearch(
                hosts=hosts,
                http_auth=(self.username, self.password) if self.password else None,
                request_timeout=self.timeout,
                max_retries=3,
                retry_on_timeout=True,
                **ssl_options
            )
            
            # Test connection
            info = await self.client.info()
            logger.info("Connected to Elasticsearch", 
                       cluster_name=info['cluster_name'],
                       version=info['version']['number'])
            
        except Exception as e:
            logger.error("Failed to connect to Elasticsearch", error=str(e))
            raise
    
    async def close(self):
        """Close Elasticsearch connection."""
        if self.client:
            await self.client.close()
            logger.info("Elasticsearch connection closed")
    
    async def get_available_indices(self) -> List[str]:
        """Get available DShield indices."""
        if not self.client:
            raise RuntimeError("Elasticsearch client not connected")
        
        try:
            # Get all indices
            indices = await self.client.cat.indices(format='json')
            
            # Filter for DShield indices
            dshield_indices = []
            for index in indices:
                index_name = index['index']
                if any(pattern.replace('*', '') in index_name for pattern in self.dshield_indices):
                    dshield_indices.append(index_name)
            
            logger.info("Found DShield indices", count=len(dshield_indices), indices=dshield_indices)
            return dshield_indices
            
        except Exception as e:
            logger.error("Failed to get available indices", error=str(e))
            return []
    
    async def query_dshield_events(
        self,
        time_range_hours: int = 24,
        indices: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        size: int = 1000
    ) -> List[Dict[str, Any]]:
        """Query DShield events from Elasticsearch."""
        
        if not self.client:
            raise RuntimeError("Elasticsearch client not connected")
        
        # Use DShield indices if available, otherwise fallback
        if indices is None:
            available_indices = await self.get_available_indices()
            if available_indices:
                indices = available_indices
            else:
                indices = self.fallback_indices
        
        filters = filters or {}
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_range_hours)
        
        # Build DShield-specific query
        query = self._build_dshield_query(start_time, end_time, filters)
        
        logger.info("Querying DShield events",
                   indices=indices,
                   time_range_hours=time_range_hours,
                   size=size)
        
        try:
            response = await self.client.search(
                index=indices,
                body=query,
                size=min(size, self.max_results),
                timeout=f"{self.timeout}s"
            )
            
            events = []
            for hit in response['hits']['hits']:
                event = self._parse_dshield_event(hit, indices)
                if event:
                    events.append(event)
            
            logger.info("DShield events query completed",
                       total_hits=response['hits']['total']['value'],
                       returned_events=len(events))
            
            return events
            
        except RequestError as e:
            logger.error("Elasticsearch query error", error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error during query", error=str(e))
            raise
    
    async def query_dshield_attacks(
        self,
        time_range_hours: int = 24,
        size: int = 1000
    ) -> List[Dict[str, Any]]:
        """Query DShield attack data specifically."""
        
        return await self.query_dshield_events(
            time_range_hours=time_range_hours,
            indices=["dshield-attacks-*", "dshield-*"],
            filters={"event.category": "attack"},
            size=size
        )
    
    async def query_dshield_reputation(
        self,
        ip_addresses: Optional[List[str]] = None,
        size: int = 1000
    ) -> List[Dict[str, Any]]:
        """Query DShield reputation data."""
        
        filters = {}
        if ip_addresses:
            filters["source.ip"] = ip_addresses
        
        return await self.query_dshield_events(
            time_range_hours=24,
            indices=["dshield-reputation-*", "dshield-*"],
            filters=filters,
            size=size
        )
    
    async def query_dshield_top_attackers(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query DShield top attackers data."""
        
        return await self.query_dshield_events(
            time_range_hours=hours,
            indices=["dshield-top-*", "dshield-summary-*"],
            filters={"event.type": "top_attacker"},
            size=limit
        )
    
    async def query_dshield_geographic_data(
        self,
        countries: Optional[List[str]] = None,
        size: int = 1000
    ) -> List[Dict[str, Any]]:
        """Query DShield geographic data."""
        
        filters = {}
        if countries:
            filters["geoip.country_name"] = countries
        
        return await self.query_dshield_events(
            time_range_hours=24,
            indices=["dshield-geo-*", "dshield-*"],
            filters=filters,
            size=size
        )
    
    async def query_dshield_port_data(
        self,
        ports: Optional[List[int]] = None,
        size: int = 1000
    ) -> List[Dict[str, Any]]:
        """Query DShield port data."""
        
        filters = {}
        if ports:
            filters["destination.port"] = ports
        
        return await self.query_dshield_events(
            time_range_hours=24,
            indices=["dshield-ports-*", "dshield-*"],
            filters=filters,
            size=size
        )
    
    async def query_events_by_ip(
        self,
        ip_addresses: List[str],
        time_range_hours: int = 24,
        indices: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Query events for specific IP addresses."""
        
        if not self.client:
            raise RuntimeError("Elasticsearch client not connected")
        
        # Use DShield indices if available, otherwise fallback
        if indices is None:
            available_indices = await self.get_available_indices()
            if available_indices:
                indices = available_indices
            else:
                indices = self.fallback_indices
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_range_hours)
        
        # Build IP-specific query
        query = self._build_ip_query(ip_addresses, start_time, end_time)
        
        logger.info("Querying events by IP",
                   ip_addresses=ip_addresses,
                   time_range_hours=time_range_hours)
        
        try:
            response = await self.client.search(
                index=indices,
                body=query,
                size=self.max_results,
                timeout=f"{self.timeout}s"
            )
            
            events = []
            for hit in response['hits']['hits']:
                event = self._parse_dshield_event(hit, indices)
                if event:
                    events.append(event)
            
            logger.info("IP events query completed",
                       total_hits=response['hits']['total']['value'],
                       returned_events=len(events))
            
            return events
            
        except RequestError as e:
            logger.error("Elasticsearch IP query error", error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error during IP query", error=str(e))
            raise
    
    async def get_dshield_statistics(
        self,
        time_range_hours: int = 24
    ) -> Dict[str, Any]:
        """Get DShield statistics and summary data."""
        
        try:
            # Query summary data
            summary_events = await self.query_dshield_events(
                time_range_hours=time_range_hours,
                indices=["dshield-summary-*", "dshield-statistics-*"],
                size=100
            )
            
            # Query top attackers
            top_attackers = await self.query_dshield_top_attackers(time_range_hours)
            
            # Query geographic data
            geo_data = await self.query_dshield_geographic_data()
            
            # Compile statistics
            stats = {
                'total_events': len(summary_events),
                'top_attackers': top_attackers[:10],
                'geographic_distribution': self._compile_geo_stats(geo_data),
                'time_range_hours': time_range_hours,
                'timestamp': datetime.utcnow().isoformat()
            }
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get DShield statistics", error=str(e))
            return {}
    
    def _build_dshield_query(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build Elasticsearch query for DShield events."""
        
        # Base query with time range
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": start_time.isoformat(),
                                    "lte": end_time.isoformat()
                                }
                            }
                        }
                    ],
                    "filter": [],
                    "should": [],
                    "must_not": []
                }
            },
            "sort": [
                {"@timestamp": {"order": "desc"}}
            ]
        }
        
        # Add filters
        for field, value in filters.items():
            if isinstance(value, (list, tuple)):
                query["query"]["bool"]["filter"].append({
                    "terms": {field: value}
                })
            else:
                query["query"]["bool"]["filter"].append({
                    "term": {field: value}
                })
        
        # Add DShield-specific filters
        dshield_filters = [
            {"exists": {"field": "source.ip"}},
            {"exists": {"field": "destination.ip"}}
        ]
        
        query["query"]["bool"]["filter"].extend(dshield_filters)
        
        return query
    
    def _build_ip_query(
        self,
        ip_addresses: List[str],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, Any]:
        """Build Elasticsearch query for IP-specific events."""
        
        query = {
            "query": {
                "bool": {
                    "must": [
                        {
                            "range": {
                                "@timestamp": {
                                    "gte": start_time.isoformat(),
                                    "lte": end_time.isoformat()
                                }
                            }
                        },
                        {
                            "terms": {
                                "source.ip": ip_addresses
                            }
                        }
                    ],
                    "should": [
                        {
                            "terms": {
                                "destination.ip": ip_addresses
                            }
                        }
                    ],
                    "minimum_should_match": 0
                }
            },
            "sort": [
                {"@timestamp": {"order": "desc"}}
            ]
        }
        
        return query
    
    def _parse_dshield_event(self, hit: Dict[str, Any], indices: List[str]) -> Optional[Dict[str, Any]]:
        """Parse Elasticsearch hit into DShield event."""
        try:
            source = hit['_source']
            
            # Extract timestamp using DShield field mappings
            timestamp = self._extract_field_mapped(source, 'timestamp')
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif not isinstance(timestamp, datetime):
                timestamp = datetime.utcnow()
            
            # Extract IP addresses using DShield field mappings
            source_ip = self._extract_field_mapped(source, 'source_ip')
            destination_ip = self._extract_field_mapped(source, 'destination_ip')
            
            # Extract ports using DShield field mappings
            source_port = self._extract_field_mapped(source, 'source_port')
            destination_port = self._extract_field_mapped(source, 'destination_port')
            
            # Extract event information using DShield field mappings
            event_type = self._extract_field_mapped(source, 'event_type', 'unknown')
            event_category = self._extract_field_mapped(source, 'category', 'other')
            severity = self._extract_field_mapped(source, 'severity', 'medium')
            
            # Extract description using DShield field mappings
            description = self._extract_field_mapped(
                source, 
                'description',
                f"{event_type} event from {source_ip or 'unknown'} to {destination_ip or 'unknown'}"
            )
            
            # Extract protocol using DShield field mappings
            protocol = self._extract_field_mapped(source, 'protocol')
            
            # Extract DShield-specific fields
            country = self._extract_field_mapped(source, 'country')
            asn = self._extract_field_mapped(source, 'asn')
            organization = self._extract_field_mapped(source, 'organization')
            reputation_score = self._extract_field_mapped(source, 'reputation_score')
            attack_count = self._extract_field_mapped(source, 'attack_count')
            first_seen = self._extract_field_mapped(source, 'first_seen')
            last_seen = self._extract_field_mapped(source, 'last_seen')
            tags = self._extract_field_mapped(source, 'tags', [])
            attack_types = self._extract_field_mapped(source, 'attack_types', [])
            
            event = {
                'id': hit['_id'],
                'timestamp': timestamp.isoformat(),
                'source_ip': source_ip,
                'destination_ip': destination_ip,
                'source_port': source_port,
                'destination_port': destination_port,
                'protocol': protocol,
                'event_type': event_type,
                'severity': severity,
                'category': event_category,
                'description': description,
                'country': country,
                'asn': asn,
                'organization': organization,
                'reputation_score': reputation_score,
                'attack_count': attack_count,
                'first_seen': first_seen,
                'last_seen': last_seen,
                'tags': tags,
                'attack_types': attack_types,
                'raw_data': source,
                'indices': indices
            }
            
            return event
            
        except Exception as e:
            logger.warning("Failed to parse DShield event", hit_id=hit.get('_id'), error=str(e))
            return None
    
    def _extract_field_mapped(self, source: Dict[str, Any], field_type: str, default: Any = None) -> Any:
        """Extract field value using DShield field mappings."""
        if field_type in self.dshield_field_mappings:
            field_names = self.dshield_field_mappings[field_type]
            for field in field_names:
                value = source.get(field)
                if value is not None:
                    return value
        return default
    
    def _compile_geo_stats(self, geo_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Compile geographic statistics from geo data."""
        country_counts = {}
        for event in geo_data:
            country = event.get('country')
            if country:
                country_counts[country] = country_counts.get(country, 0) + 1
        return country_counts
    
    # Backward compatibility methods
    async def query_security_events(
        self,
        time_range_hours: int = 24,
        indices: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        size: int = 1000
    ) -> List[Dict[str, Any]]:
        """Backward compatibility method - redirects to query_dshield_events."""
        return await self.query_dshield_events(
            time_range_hours=time_range_hours,
            indices=indices,
            filters=filters,
            size=size
        )
    
    async def get_index_mapping(self, index_pattern: str) -> Dict[str, Any]:
        """Get mapping for an index pattern."""
        if not self.client:
            raise RuntimeError("Elasticsearch client not connected")
        
        try:
            response = await self.client.indices.get_mapping(index=index_pattern)
            return response
        except Exception as e:
            logger.error("Failed to get index mapping", index=index_pattern, error=str(e))
            raise
    
    async def get_cluster_stats(self) -> Dict[str, Any]:
        """Get Elasticsearch cluster statistics."""
        if not self.client:
            raise RuntimeError("Elasticsearch client not connected")
        
        try:
            stats = await self.client.cluster.stats()
            return stats
        except Exception as e:
            logger.error("Failed to get cluster stats", error=str(e))
            raise 