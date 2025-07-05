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
from .models import SecurityEvent, ElasticsearchQuery, QueryFilter
from .config_loader import get_config, ConfigError

logger = structlog.get_logger(__name__)


class ElasticsearchClient:
    """Client for interacting with DShield SIEM Elasticsearch."""
    
    def __init__(self):
        self.client: Optional[AsyncElasticsearch] = None
        try:
            config = get_config()
            es_config = config["elasticsearch"]
        except Exception as e:
            raise RuntimeError(f"Failed to load Elasticsearch config: {e}")

        self.url = es_config["url"]
        self.username = es_config.get("username", "")
        self.password = es_config.get("password", "")
        self.verify_ssl = es_config.get("verify_ssl", True)
        self.ca_certs = es_config.get("ca_certs", None)
        self.timeout = int(es_config.get("timeout", 30))
        self.max_results = int(es_config.get("max_results", 1000))

        # Index patterns
        patterns = es_config.get("index_patterns", {})
        self.dshield_indices = []
        for group in ("cowrie", "zeek", "dshield"):
            self.dshield_indices.extend(patterns.get(group, []))
        self.fallback_indices = patterns.get("fallback", [])

        # DShield specific field mappings
        self.dshield_field_mappings = {
            'timestamp': ['@timestamp', 'timestamp', 'time', 'date', 'event.ingested'],
            'source_ip': ['source.ip', 'src_ip', 'srcip', 'sourceip', 'attacker_ip', 'attackerip', 'src', 'client_ip', 'ip.src', 'ip_source'],
            'destination_ip': ['destination.ip', 'dst_ip', 'dstip', 'destinationip', 'target_ip', 'targetip', 'dst', 'server_ip', 'ip.dst', 'ip_destination'],
            'source_port': ['source.port', 'src_port', 'srcport', 'sourceport', 'attacker_port', 'sport', 'client_port', 'port.src', 'port_source'],
            'destination_port': ['destination.port', 'dst_port', 'dstport', 'destinationport', 'target_port', 'dport', 'server_port', 'port.dst', 'port_destination'],
            'protocol': ['network.protocol', 'protocol', 'proto', 'transport_protocol', 'event.protocol', 'ip.proto'],
            'event_type': ['event.type', 'event_type', 'type', 'attack_type', 'dshield_type', 'event.kind', 'event.outcome'],
            'severity': ['event.severity', 'severity', 'level', 'risk_level', 'threat_level', 'event.level'],
            'category': ['event.category', 'event_category', 'category', 'attack_category'],
            'description': ['event.description', 'message', 'description', 'summary', 'attack_description', 'event.original'],
            'country': ['geoip.country_name', 'country', 'country_name', 'attacker_country', 'source.geo.country_name'],
            'asn': ['asn', 'as_number', 'autonomous_system', 'attacker_asn', 'source.geo.asn'],
            'organization': ['org', 'organization', 'org_name', 'attacker_org', 'source.geo.organization_name'],
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
            await self.connect()
        
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
        fields: Optional[List[str]] = None,
        page: int = 1,
        page_size: int = 100,
        include_summary: bool = True
    ) -> tuple[List[Dict[str, Any]], int]:
        """Query DShield events from Elasticsearch with pagination support and field selection."""
        
        if not self.client:
            await self.connect()
        
        # Use DShield indices if available, otherwise fallback
        if indices is None:
            available_indices = await self.get_available_indices()
            if available_indices:
                indices = available_indices
            else:
                indices = self.fallback_indices
        
        # Build query with time range
        query = {
            "bool": {
                "must": [
                    {
                        "range": {
                            "@timestamp": {
                                "gte": f"now-{time_range_hours}h",
                                "lte": "now"
                            }
                        }
                    }
                ]
            }
        }
        
        # Add additional filters
        if filters:
            for key, value in filters.items():
                if key == "@timestamp":
                    # Handle custom timestamp filtering
                    query["bool"]["must"].append({"range": {"@timestamp": value}})
                elif isinstance(value, dict):
                    # Handle nested filters (e.g., "source_ip": {"eq": "1.2.3.4"})
                    for sub_key, sub_value in value.items():
                        if sub_key == "eq":
                            query["bool"]["must"].append({"term": {key: sub_value}})
                        elif sub_key == "in":
                            query["bool"]["must"].append({"terms": {key: sub_value}})
                        elif sub_key == "gte":
                            query["bool"]["must"].append({"range": {key: {"gte": sub_value}}})
                        elif sub_key == "lte":
                            query["bool"]["must"].append({"range": {key: {"lte": sub_value}}})
                else:
                    # Simple term match
                    query["bool"]["must"].append({"term": {key: value}})
        
        # Build search body
        search_body = {
            "query": query,
            "from_": (page - 1) * page_size,
            "size": min(page_size, 1000)  # Limit max page size
        }
        
        # Add field selection if specified
        if fields:
            search_body["_source"] = fields
        
        # Add sorting by timestamp
        search_body["sort"] = [{"@timestamp": {"order": "desc"}}]
        
        try:
            # Execute search
            response = await self.client.search(
                index=",".join(indices),
                body=search_body
            )
            
            # Extract results
            hits = response.get("hits", {})
            total_count = hits.get("total", {}).get("value", 0)
            documents = hits.get("hits", [])
            
            # Parse events
            events = []
            for doc in documents:
                event = self._parse_dshield_event(doc, indices)
                if event:
                    events.append(event)
            
            logger.info(f"Retrieved {len(events)} events from {len(indices)} indices", 
                       total_count=total_count, page=page, page_size=page_size)
            
            return events, total_count
            
        except Exception as e:
            logger.error(f"Error querying DShield events: {str(e)}")
            raise

    async def execute_aggregation_query(
        self,
        index: List[str],
        query: Dict[str, Any],
        aggregation_query: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute an aggregation query against Elasticsearch."""
        
        if not self.client:
            await self.connect()
        
        try:
            # Build the complete search body
            search_body = {
                "query": query,
                **aggregation_query
            }
            
            # Execute search with aggregations
            response = await self.client.search(
                index=",".join(index),
                body=search_body
            )
            
            logger.info(f"Executed aggregation query on {len(index)} indices")
            
            return response
            
        except Exception as e:
            logger.error(f"Error executing aggregation query: {str(e)}")
            raise

    async def stream_dshield_events(
        self,
        time_range_hours: int = 24,
        indices: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        fields: Optional[List[str]] = None,
        chunk_size: int = 500,
        stream_id: Optional[str] = None
    ) -> tuple[List[Dict[str, Any]], int, Optional[str]]:
        """Stream DShield events with cursor-based pagination for large datasets."""
        
        if not self.client:
            await self.connect()
        
        # Use DShield indices if available, otherwise fallback
        if indices is None:
            available_indices = await self.get_available_indices()
            if available_indices:
                indices = available_indices
            else:
                indices = self.fallback_indices
        
        # Build query with time range
        query = {
            "bool": {
                "must": [
                    {
                        "range": {
                            "@timestamp": {
                                "gte": f"now-{time_range_hours}h",
                                "lte": "now"
                            }
                        }
                    }
                ]
            }
        }
        
        # Add additional filters
        if filters:
            for key, value in filters.items():
                if key == "@timestamp":
                    # Handle custom timestamp filtering
                    query["bool"]["must"].append({"range": {"@timestamp": value}})
                elif isinstance(value, dict):
                    # Handle nested filters
                    for sub_key, sub_value in value.items():
                        if sub_key == "eq":
                            query["bool"]["must"].append({"term": {key: sub_value}})
                        elif sub_key == "in":
                            query["bool"]["must"].append({"terms": {key: sub_value}})
                        elif sub_key == "gte":
                            query["bool"]["must"].append({"range": {key: {"gte": sub_value}}})
                        elif sub_key == "lte":
                            query["bool"]["must"].append({"range": {key: {"lte": sub_value}}})
                else:
                    # Simple term match
                    query["bool"]["must"].append({"term": {key: value}})
        
        # Build search body with cursor-based pagination
        search_body = {
            "query": query,
            "size": min(chunk_size, 1000),  # Limit max chunk size
            "sort": [
                {"@timestamp": {"order": "desc"}},
                {"_id": {"order": "desc"}}  # Secondary sort for consistent pagination
            ]
        }
        
        # Add field selection if specified
        if fields:
            search_body["_source"] = fields
        
        # Add search_after for cursor-based pagination
        if stream_id:
            # Parse the stream_id to get the search_after values
            try:
                # stream_id format: "timestamp_sort_value|_id_sort_value"
                timestamp_val, id_val = stream_id.split("|")
                search_body["search_after"] = [timestamp_val, id_val]
            except (ValueError, AttributeError):
                logger.warning(f"Invalid stream_id format: {stream_id}. Starting from beginning.")
        
        try:
            # Execute search
            response = await self.client.search(
                index=",".join(indices),
                body=search_body
            )
            
            # Extract results
            hits = response.get("hits", {})
            total_count = hits.get("total", {}).get("value", 0)
            documents = hits.get("hits", [])
            
            # Parse events
            events = []
            last_event_id = None
            
            for doc in documents:
                event = self._parse_dshield_event(doc, indices)
                if event:
                    events.append(event)
            
            # Generate next stream_id for cursor-based pagination
            if documents:
                last_hit = documents[-1]
                sort_values = last_hit.get("sort", [])
                if len(sort_values) >= 2:
                    # Create stream_id from sort values
                    last_event_id = f"{sort_values[0]}|{sort_values[1]}"
            
            logger.info(f"Streamed {len(events)} events from {len(indices)} indices", 
                       total_count=total_count, chunk_size=chunk_size, stream_id=stream_id)
            
            return events, total_count, last_event_id
            
        except Exception as e:
            logger.error(f"Error streaming DShield events: {str(e)}")
            raise
    
    async def query_dshield_attacks(
        self,
        time_range_hours: int = 24,
        page: int = 1,
        page_size: int = 100,
        include_summary: bool = True
    ) -> tuple[List[Dict[str, Any]], int]:
        """Query DShield attack events with pagination support."""
        
        if not self.client:
            await self.connect()
        
        # Calculate time range
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(hours=time_range_hours)
        
        # Build attack-specific query
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
                    "filter": [
                        {"exists": {"field": "source.ip"}},
                        {"exists": {"field": "destination.ip"}}
                    ]
                }
            },
            "sort": [
                {"@timestamp": {"order": "desc"}}
            ]
        }
        
        # Calculate pagination
        from_index = (page - 1) * page_size
        actual_size = min(page_size, self.max_results)
        
        logger.info("Querying DShield attacks",
                   time_range_hours=time_range_hours,
                   page=page,
                   page_size=actual_size,
                   from_index=from_index)
        
        try:
            response = await self.client.search(
                index=["dshield-attacks-*", "dshield-*"],
                body=query,
                size=actual_size,
                from_=from_index,
                timeout=f"{self.timeout}s"
            )
            
            attacks = []
            for hit in response['hits']['hits']:
                attack = self._parse_dshield_event(hit, ["dshield-attacks-*", "dshield-*"])
                if attack:
                    attacks.append(attack)
            
            total_count = response['hits']['total']['value']
            
            logger.info("DShield attacks query completed",
                       total_hits=total_count,
                       returned_attacks=len(attacks),
                       page=page,
                       page_size=actual_size)
            
            return attacks, total_count
            
        except RequestError as e:
            logger.error("Elasticsearch attack query error", error=str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error during attack query", error=str(e))
            raise
    
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
            self.log_unmapped_fields(source)
            
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
        """Extract field value using DShield field mappings. Logs unmapped fields for review."""
        mapped = False
        if field_type in self.dshield_field_mappings:
            field_names = self.dshield_field_mappings[field_type]
            for field in field_names:
                value = source.get(field)
                if value is not None:
                    mapped = True
                    return value
        if not mapped:
            logger.debug(f"Field type '{field_type}' not mapped in document.", available_fields=list(source.keys()))
        return default

    def log_unmapped_fields(self, source: Dict[str, Any]):
        """Log any fields in the source document that are not mapped to any known field type."""
        mapped_fields = set()
        for field_list in self.dshield_field_mappings.values():
            mapped_fields.update(field_list)
        unmapped = [f for f in source.keys() if f not in mapped_fields]
        if unmapped:
            logger.info("Unmapped fields detected in document", unmapped_fields=unmapped)
    
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
        events, _ = await self.query_dshield_events(
            time_range_hours=time_range_hours,
            indices=indices,
            filters=filters,
            page_size=size
        )
        return events

    def _generate_pagination_info(self, page: int, page_size: int, total_count: int) -> Dict[str, Any]:
        """Generate pagination information for response."""
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages
        has_previous = page > 1
        
        return {
            "current_page": page,
            "page_size": page_size,
            "total_count": total_count,
            "total_pages": total_pages,
            "has_next": has_next,
            "has_previous": has_previous,
            "next_page": page + 1 if has_next else None,
            "previous_page": page - 1 if has_previous else None,
            "start_index": (page - 1) * page_size + 1,
            "end_index": min(page * page_size, total_count)
        }
    
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