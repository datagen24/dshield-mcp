"""
Elasticsearch client for querying DShield SIEM events and logs.
Optimized for DShield SIEM integration patterns.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union, Tuple
from urllib.parse import urlparse

import structlog
from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import RequestError, TransportError
from models import SecurityEvent, ElasticsearchQuery, QueryFilter
from config_loader import get_config, ConfigError
from user_config import get_user_config

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
        
        # Load user configuration
        user_config = get_user_config()
        self.default_page_size = user_config.get_setting("query", "default_page_size")
        self.max_page_size = user_config.get_setting("query", "max_page_size")
        self.default_timeout = user_config.get_setting("query", "default_timeout_seconds")
        self.max_timeout = user_config.get_setting("query", "max_timeout_seconds")
        self.enable_smart_optimization = user_config.get_setting("query", "enable_smart_optimization")
        self.fallback_strategy = user_config.get_setting("query", "fallback_strategy")
        self.max_query_complexity = user_config.get_setting("query", "max_query_complexity")
        self.enable_performance_logging = user_config.get_setting("logging", "enable_performance_logging")

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
        sort_by: str = "@timestamp",
        sort_order: str = "desc",
        cursor: Optional[str] = None,
        include_summary: bool = True,
        optimization: str = "auto",
        fallback_strategy: str = "aggregate",
        max_result_size_mb: float = 10.0,
        query_timeout_seconds: int = 30
    ) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]:
        """Query DShield events from Elasticsearch with enhanced pagination support.
        
        Supports both traditional page-based pagination and cursor-based pagination
        for better performance with massive datasets.
        """
        
        if not self.client:
            await self.connect()
        
        # Use DShield indices if available, otherwise fallback
        if indices is None:
            available_indices = await self.get_available_indices()
            if available_indices:
                indices = available_indices
            else:
                indices = self.fallback_indices
        
        # Smart Query Optimization
        optimization_applied = None
        original_page_size = page_size
        original_fields = fields
        
        if optimization == "auto":
            # Step 1: Estimate result size
            estimated_size_mb = await self._estimate_query_size(
                time_range_hours, indices, filters, fields, page_size
            )
            
            logger.info(f"Estimated query size: {estimated_size_mb:.2f} MB")
            
            # Step 2: Apply optimizations if needed
            if estimated_size_mb > max_result_size_mb:
                logger.warning(f"Estimated size ({estimated_size_mb:.2f} MB) exceeds limit ({max_result_size_mb} MB)")
                
                # Try field reduction first
                if fields and len(fields) > 3:
                    reduced_fields = self._optimize_fields(fields)
                    fields = reduced_fields
                    optimization_applied = "field_reduction"
                    logger.info(f"Applied field reduction: {reduced_fields}")
                    
                    # Re-estimate with reduced fields
                    estimated_size_mb = await self._estimate_query_size(
                        time_range_hours, indices, filters, fields, page_size
                    )
                
                # Try page size reduction if still too large
                if estimated_size_mb > max_result_size_mb and page_size > 10:
                    original_page_size = page_size
                    page_size = max(10, int(page_size * 0.5))
                    optimization_applied = f"{optimization_applied}_page_reduction" if optimization_applied else "page_reduction"
                    logger.info(f"Applied page size reduction: {page_size}")
                    
                    # Re-estimate with reduced page size
                    estimated_size_mb = await self._estimate_query_size(
                        time_range_hours, indices, filters, fields, page_size
                    )
                
                # If still too large, apply fallback strategy
                if estimated_size_mb > max_result_size_mb:
                    logger.warning(f"Query still too large after optimizations, applying fallback: {fallback_strategy}")
                    return await self._apply_fallback_strategy(
                        fallback_strategy, time_range_hours, indices, filters, 
                        sort_by, sort_order, optimization_applied
                    )
        
        # Build search query with timeout
        search_body = {
            "timeout": f"{query_timeout_seconds}s",
            "query": {
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
            },
            "size": page_size
        }
        
        # Apply intelligent field mapping for user-friendly field names
        mapped_filters = self._map_query_fields(filters) if filters else None
        
        # Add additional filters
        if mapped_filters:
            for key, value in mapped_filters.items():
                if key == "@timestamp":
                    # Handle custom timestamp filtering
                    search_body["query"]["bool"]["must"].append({"range": {"@timestamp": value}})
                elif isinstance(value, dict):
                    # Handle nested filters (e.g., "source_ip": {"eq": "1.2.3.4"})
                    for sub_key, sub_value in value.items():
                        if sub_key == "eq":
                            search_body["query"]["bool"]["must"].append({"term": {key: sub_value}})
                        elif sub_key == "in":
                            search_body["query"]["bool"]["must"].append({"terms": {key: sub_value}})
                        elif sub_key == "gte":
                            search_body["query"]["bool"]["must"].append({"range": {key: {"gte": sub_value}}})
                        elif sub_key == "lte":
                            search_body["query"]["bool"]["must"].append({"range": {key: {"lte": sub_value}}})
                else:
                    # Handle arrays with terms, single values with term
                    if isinstance(value, (list, tuple)):
                        search_body["query"]["bool"]["must"].append({"terms": {key: value}})
                    else:
                        search_body["query"]["bool"]["must"].append({"term": {key: value}})
        
        # Build search body with enhanced pagination
        search_body["sort"] = [{sort_by: {"order": sort_order}}]
        
        # Handle pagination method
        if cursor:
            # Cursor-based pagination (search_after) - better for large datasets
            try:
                # Parse cursor: single field value (timestamp)
                search_body["search_after"] = [cursor]
            except (ValueError, AttributeError):
                # Fallback to page-based if cursor format is invalid
                search_body["from_"] = (page - 1) * page_size
        else:
            # Traditional page-based pagination
            search_body["from_"] = (page - 1) * page_size
        
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
            next_cursor = None
            
            for doc in documents:
                event = self._parse_dshield_event(doc, indices)
                if event:
                    events.append(event)
            
            # Generate next cursor for cursor-based pagination
            if documents and cursor:
                last_hit = documents[-1]
                sort_values = last_hit.get("sort", [])
                if len(sort_values) >= 1:
                    # Create cursor from sort values (single field now)
                    next_cursor = f"{sort_values[0]}"
                else:
                    # Fallback: use timestamp from the last document
                    last_source = last_hit.get("_source", {})
                    timestamp = last_source.get("@timestamp")
                    if timestamp:
                        next_cursor = f"{timestamp}"
            
            # Generate enhanced pagination info
            pagination_info = self._generate_enhanced_pagination_info(
                page=page,
                page_size=page_size,
                total_count=total_count,
                cursor=cursor,
                next_cursor=next_cursor,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            logger.info(f"Retrieved {len(events)} events from {len(indices)} indices", 
                       total_count=total_count, page=page, page_size=page_size,
                       pagination_method="cursor" if cursor else "page")
            
            return events, total_count, pagination_info
            
        except Exception as e:
            logger.error(f"Error querying DShield events: {str(e)}")
            raise

    async def _estimate_query_size(
        self, 
        time_range_hours: int, 
        indices: List[str], 
        filters: Optional[Dict[str, Any]], 
        fields: Optional[List[str]], 
        page_size: int
    ) -> float:
        """Estimate the size of query results in MB."""
        try:
            # Build a count query to get total documents
            count_body = {
                "query": {
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
            }
            
            # Apply intelligent field mapping for user-friendly field names
            mapped_filters = self._map_query_fields(filters) if filters else None
            
            # Add filters if provided
            if mapped_filters:
                for key, value in mapped_filters.items():
                    if key == "@timestamp":
                        count_body["query"]["bool"]["must"].append({"range": {"@timestamp": value}})
                    elif isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            if sub_key == "eq":
                                count_body["query"]["bool"]["must"].append({"term": {key: sub_value}})
                            elif sub_key == "in":
                                count_body["query"]["bool"]["must"].append({"terms": {key: sub_value}})
                            elif sub_key == "gte":
                                count_body["query"]["bool"]["must"].append({"range": {key: {"gte": sub_value}}})
                            elif sub_key == "lte":
                                count_body["query"]["bool"]["must"].append({"range": {key: {"lte": sub_value}}})
                    else:
                        count_body["query"]["bool"]["must"].append({"term": {key: value}})
            
            # Get total count
            count_response = await self.client.count(
                index=",".join(indices),
                body=count_body
            )
            
            total_docs = count_response["count"]
            
            # Estimate size per document based on fields
            if fields:
                # Conservative estimate: 1KB per field per document
                bytes_per_doc = len(fields) * 1024
            else:
                # Conservative estimate: 5KB per document for all fields
                bytes_per_doc = 5 * 1024
            
            # Calculate total size for requested page
            total_bytes = min(total_docs, page_size) * bytes_per_doc
            total_mb = total_bytes / (1024 * 1024)
            
            return total_mb
            
        except Exception as e:
            logger.warning(f"Could not estimate query size: {e}")
            # Return conservative estimate
            return page_size * 0.005  # 5KB per document estimate

    def _optimize_fields(self, fields: List[str]) -> List[str]:
        """Optimize field selection by keeping only essential fields."""
        # Priority fields that are most important for analysis
        priority_fields = [
            "@timestamp", "source_ip", "destination_ip", "source_port", 
            "destination_port", "event.category", "event.type", "severity"
        ]
        
        # Keep priority fields first, then add others up to a reasonable limit
        optimized = []
        
        # Add priority fields that are in the original list
        for field in priority_fields:
            if field in fields and field not in optimized:
                optimized.append(field)
        
        # Add remaining fields up to a limit
        remaining_fields = [f for f in fields if f not in optimized]
        optimized.extend(remaining_fields[:5])  # Keep max 5 additional fields
        
        return optimized

    async def _apply_fallback_strategy(
        self,
        strategy: str,
        time_range_hours: int,
        indices: List[str],
        filters: Optional[Dict[str, Any]],
        sort_by: str,
        sort_order: str,
        optimization_applied: Optional[str]
    ) -> Tuple[List[Dict[str, Any]], int, Dict[str, Any]]:
        """Apply fallback strategy when query optimization fails."""
        
        if strategy == "aggregate":
            # Return aggregation results instead of individual events
            logger.info("Applying aggregation fallback strategy")
            
            # Create aggregation query
            agg_body = {
                "query": {
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
                },
                "size": 0,  # No individual documents
                "aggs": {
                    "top_sources": {
                        "terms": {
                            "field": "source_ip",
                            "size": 50
                        }
                    },
                    "top_destinations": {
                        "terms": {
                            "field": "destination_port",
                            "size": 50
                        }
                    },
                    "event_types": {
                        "terms": {
                            "field": "event.category",
                            "size": 20
                        }
                    },
                    "timeline": {
                        "date_histogram": {
                            "field": "@timestamp",
                            "calendar_interval": "1h"
                        }
                    }
                }
            }
            
            # Add filters if provided
            if filters:
                for key, value in filters.items():
                    if key == "@timestamp":
                        agg_body["query"]["bool"]["must"].append({"range": {"@timestamp": value}})
                    elif isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            if sub_key == "eq":
                                agg_body["query"]["bool"]["must"].append({"term": {key: sub_value}})
                            elif sub_key == "in":
                                agg_body["query"]["bool"]["must"].append({"terms": {key: sub_value}})
                            elif sub_key == "gte":
                                agg_body["query"]["bool"]["must"].append({"range": {key: {"gte": sub_value}}})
                            elif sub_key == "lte":
                                agg_body["query"]["bool"]["must"].append({"range": {key: {"lte": sub_value}}})
                    else:
                        agg_body["query"]["bool"]["must"].append({"term": {key: value}})
            
            response = await self.client.search(
                index=",".join(indices),
                body=agg_body
            )
            
            # Convert aggregation results to event-like format
            events = []
            aggs = response.get("aggregations", {})
            
            # Add summary events for each aggregation
            if "top_sources" in aggs:
                for bucket in aggs["top_sources"]["buckets"]:
                    events.append({
                        "id": f"agg_source_{bucket['key']}",
                        "timestamp": datetime.now().isoformat(),
                        "source_ip": bucket["key"],
                        "event_type": "aggregation",
                        "category": ["summary", "source_analysis"],
                        "description": f"Top source IP: {bucket['key']} with {bucket['doc_count']} events",
                        "raw_data": {
                            "aggregation_type": "top_sources",
                            "doc_count": bucket["doc_count"]
                        }
                    })
            
            if "top_destinations" in aggs:
                for bucket in aggs["top_destinations"]["buckets"]:
                    events.append({
                        "id": f"agg_dest_{bucket['key']}",
                        "timestamp": datetime.now().isoformat(),
                        "destination_port": bucket["key"],
                        "event_type": "aggregation",
                        "category": ["summary", "destination_analysis"],
                        "description": f"Top destination port: {bucket['key']} with {bucket['doc_count']} events",
                        "raw_data": {
                            "aggregation_type": "top_destinations",
                            "doc_count": bucket["doc_count"]
                        }
                    })
            
            # Create pagination info for aggregation results
            pagination_info = {
                "page_size": len(events),
                "page_number": 1,
                "total_results": len(events),
                "total_available": len(events),
                "has_more": False,
                "total_pages": 1,
                "has_previous": False,
                "has_next": False,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "optimization_applied": optimization_applied,
                "fallback_strategy": strategy,
                "note": "Results from aggregation fallback due to large dataset"
            }
            
            return events, len(events), pagination_info
            
        elif strategy == "sample":
            # Return a small sample of events
            logger.info("Applying sampling fallback strategy")
            
            sample_body = {
                "query": {
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
                },
                "size": 10,  # Small sample
                "sort": [{sort_by: {"order": sort_order}}]
            }
            
            # Add filters if provided
            if filters:
                for key, value in filters.items():
                    if key == "@timestamp":
                        sample_body["query"]["bool"]["must"].append({"range": {"@timestamp": value}})
                    elif isinstance(value, dict):
                        for sub_key, sub_value in value.items():
                            if sub_key == "eq":
                                sample_body["query"]["bool"]["must"].append({"term": {key: sub_value}})
                            elif sub_key == "in":
                                sample_body["query"]["bool"]["must"].append({"terms": {key: sub_value}})
                            elif sub_key == "gte":
                                sample_body["query"]["bool"]["must"].append({"range": {key: {"gte": sub_value}}})
                            elif sub_key == "lte":
                                sample_body["query"]["bool"]["must"].append({"range": {key: {"lte": sub_value}}})
                    else:
                        sample_body["query"]["bool"]["must"].append({"term": {key: value}})
            
            response = await self.client.search(
                index=",".join(indices),
                body=sample_body
            )
            
            # Extract and process results the same way as main query
            hits = response.get("hits", {})
            total_count = hits.get("total", {}).get("value", 0)
            documents = hits.get("hits", [])
            
            events = []
            for doc in documents:
                event = self._parse_dshield_event(doc, indices)
                if event:
                    events.append(event)
            
            pagination_info = {
                "page_size": 10,
                "page_number": 1,
                "total_results": len(events),
                "total_available": total_count,
                "has_more": total_count > 10,
                "total_pages": 1,
                "has_previous": False,
                "has_next": total_count > 10,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "optimization_applied": optimization_applied,
                "fallback_strategy": strategy,
                "note": f"Sample of {len(events)} events from {total_count} total (dataset too large)"
            }
            
            return events, total_count, pagination_info
        
        else:
            # Default: return empty result with warning
            logger.warning(f"Unknown fallback strategy: {strategy}")
            return [], 0, {
                "page_size": 0,
                "page_number": 1,
                "total_results": 0,
                "total_available": 0,
                "has_more": False,
                "total_pages": 1,
                "has_previous": False,
                "has_next": False,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "optimization_applied": optimization_applied,
                "fallback_strategy": strategy,
                "note": f"Query failed - unknown fallback strategy: {strategy}"
            }

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
        
        events, _, _ = await self.query_dshield_events(
            time_range_hours=24,
            indices=["dshield-reputation-*", "dshield-*"],
            filters=filters,
            page_size=size
        )
        return events
    
    async def query_dshield_top_attackers(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Query DShield top attackers data."""
        
        events, _, _ = await self.query_dshield_events(
            time_range_hours=hours,
            indices=["dshield-top-*", "dshield-summary-*"],
            filters={"event.type": "top_attacker"},
            page_size=limit
        )
        return events
    
    async def query_dshield_geographic_data(
        self,
        countries: Optional[List[str]] = None,
        size: int = 1000
    ) -> List[Dict[str, Any]]:
        """Query DShield geographic data."""
        
        filters = {}
        if countries:
            filters["geoip.country_name"] = countries
        
        events, _, _ = await self.query_dshield_events(
            time_range_hours=24,
            indices=["dshield-geo-*", "dshield-*"],
            filters=filters,
            page_size=size
        )
        return events
    
    async def query_dshield_port_data(
        self,
        ports: Optional[List[int]] = None,
        size: int = 1000
    ) -> List[Dict[str, Any]]:
        """Query DShield port data."""
        
        filters = {}
        if ports:
            filters["destination.port"] = ports
        
        events, _, _ = await self.query_dshield_events(
            time_range_hours=24,
            indices=["dshield-ports-*", "dshield-*"],
            filters=filters,
            page_size=size
        )
        return events
    
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
            summary_events, _, _ = await self.query_dshield_events(
                time_range_hours=time_range_hours,
                indices=["dshield-summary-*", "dshield-statistics-*"],
                page_size=100
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
        size: Optional[int] = None,
        timeout: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Backward compatibility method - redirects to query_dshield_events."""
        # Use user configuration defaults
        if size is None:
            size = self.default_page_size
        if timeout is None:
            timeout = self.default_timeout
        
        # Validate against user configuration limits
        size = min(size, self.max_page_size)
        timeout = min(timeout, self.max_timeout)
        
        events, _ = await self.query_dshield_events(
            time_range_hours=time_range_hours,
            indices=indices,
            filters=filters,
            page_size=size,
            query_timeout_seconds=timeout
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
    
    def _generate_enhanced_pagination_info(
        self, 
        page: int, 
        page_size: int, 
        total_count: int,
        cursor: Optional[str] = None,
        next_cursor: Optional[str] = None,
        sort_by: str = "@timestamp",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """Generate enhanced pagination information for response.
        
        Provides comprehensive pagination details including cursor tokens,
        total available count, and sorting information for massive datasets.
        """
        total_pages = (total_count + page_size - 1) // page_size
        has_next = page < total_pages or next_cursor is not None
        has_previous = page > 1 or cursor is not None
        
        pagination_info = {
            "page_size": page_size,
            "page_number": page,
            "total_results": total_count,
            "total_available": total_count,  # For consistency with critical needs
            "has_more": has_next,
            "total_pages": total_pages,
            "has_previous": has_previous,
            "has_next": has_next,
            "start_index": (page - 1) * page_size + 1,
            "end_index": min(page * page_size, total_count),
            "sort_by": sort_by,
            "sort_order": sort_order
        }
        
        # Add cursor information for cursor-based pagination
        if cursor:
            pagination_info["cursor"] = cursor
        if next_cursor:
            pagination_info["next_page_token"] = next_cursor
            pagination_info["cursor"] = next_cursor
        
        # Add page navigation for traditional pagination
        if not cursor:
            if has_next:
                pagination_info["next_page"] = page + 1
            if has_previous:
                pagination_info["previous_page"] = page - 1
        
        return pagination_info
    
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

    def _map_query_fields(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map user-friendly field names to ECS dot notation for querying.
        
        This handles the mismatch between display fields (source_ip) and 
        query fields (source.ip) as described in GitHub issue #17.
        """
        if not filters:
            return filters
            
        field_mappings = {
            # IP address fields
            "source_ip": "source.ip",
            "src_ip": "source.ip",
            "sourceip": "source.ip",
            "destination_ip": "destination.ip",
            "dest_ip": "destination.ip",
            "destinationip": "destination.ip",
            "target_ip": "destination.ip",
            
            # Port fields
            "source_port": "source.port",
            "src_port": "source.port",
            "destination_port": "destination.port",
            "dest_port": "destination.port",
            "target_port": "destination.port",
            
            # Event fields
            "event_type": "event.type",
            "eventtype": "event.type",
            "event_category": "event.category",
            "eventcategory": "event.category",
            "event_kind": "event.kind",
            "eventkind": "event.kind",
            "event_outcome": "event.outcome",
            "eventoutcome": "event.outcome",
            
            # Network fields
            "protocol": "network.protocol",
            "network_protocol": "network.protocol",
            "network_type": "network.type",
            "networktype": "network.type",
            "network_direction": "network.direction",
            "networkdirection": "network.direction",
            
            # HTTP fields
            "http_method": "http.request.method",
            "httpmethod": "http.request.method",
            "http_status": "http.response.status_code",
            "httpstatus": "http.response.status_code",
            "http_version": "http.version",
            "httpversion": "http.version",
            
            # URL fields
            "url": "url.original",
            "url_original": "url.original",
            "url_path": "url.path",
            "urlpath": "url.path",
            "url_query": "url.query",
            "urlquery": "url.query",
            
            # User agent fields
            "user_agent": "user_agent.original",
            "useragent": "user_agent.original",
            "ua": "user_agent.original",
            
            # Geographic fields
            "source_country": "source.geo.country_name",
            "sourcecountry": "source.geo.country_name",
            "dest_country": "destination.geo.country_name",
            "destcountry": "destination.geo.country_name",
            "country": "source.geo.country_name",  # Default to source
            
            # Timestamp fields
            "timestamp": "@timestamp",
            "time": "@timestamp",
            "date": "@timestamp",
            
            # Severity and description (common user expectations)
            "severity": "event.severity",
            "description": "event.description",
            "message": "log.message",
            "log_message": "log.message"
        }
        
        mapped_filters = {}
        unmapped_fields = []
        
        for key, value in filters.items():
            mapped_key = field_mappings.get(key, key)
            if mapped_key != key:
                logger.info(f"Field mapping: '{key}' -> '{mapped_key}'")
            mapped_filters[mapped_key] = value
            
            # Track unmapped fields for potential suggestions
            if key not in field_mappings and "." not in key:
                unmapped_fields.append(key)
        
        # Log suggestions for unmapped fields
        if unmapped_fields:
            logger.info(f"Unmapped fields detected: {unmapped_fields}")
            logger.info("Consider using ECS dot notation (e.g., 'source.ip' instead of 'source_ip')")
        
        return mapped_filters

    def _get_field_suggestions(self, field_name: str) -> List[str]:
        """Get suggestions for field name alternatives."""
        suggestions = []
        
        # Common patterns
        if field_name.endswith("_ip"):
            base = field_name[:-3]
            suggestions.extend([
                f"{base}.ip",
                f"source.ip" if "source" in base else f"destination.ip"
            ])
        elif field_name.endswith("_port"):
            base = field_name[:-5]
            suggestions.extend([
                f"{base}.port",
                f"source.port" if "source" in base else f"destination.port"
            ])
        elif field_name.endswith("_type"):
            base = field_name[:-5]
            suggestions.extend([
                f"{base}.type",
                "event.type"
            ])
        elif field_name.endswith("_category"):
            base = field_name[:-9]
            suggestions.extend([
                f"{base}.category",
                "event.category"
            ])
        
        return suggestions 

    def _generate_session_key(self, event: Dict[str, Any], session_fields: List[str]) -> Optional[str]:
        """
        Generate a session key from event data using specified session fields.
        
        Args:
            event: The event data
            session_fields: List of fields to use for session grouping
            
        Returns:
            Session key string or None if no session fields are available
        """
        session_values = []
        
        for field in session_fields:
            value = event.get(field)
            if value:
                # Convert to string and clean up
                if isinstance(value, (list, dict)):
                    value = str(value)
                session_values.append(f"{field}:{value}")
        
        if session_values:
            return "|".join(session_values)
        else:
            return None
    
    def _calculate_session_duration(self, first_timestamp: Optional[str], last_timestamp: Optional[str]) -> Optional[float]:
        """
        Calculate session duration in minutes.
        
        Args:
            first_timestamp: First event timestamp
            last_timestamp: Last event timestamp
            
        Returns:
            Duration in minutes or None if timestamps are invalid
        """
        if not first_timestamp or not last_timestamp:
            return None
        
        try:
            # Parse timestamps (assuming ISO format)
            first_dt = datetime.fromisoformat(first_timestamp.replace('Z', '+00:00'))
            last_dt = datetime.fromisoformat(last_timestamp.replace('Z', '+00:00'))
            
            # Calculate duration in minutes
            duration = (last_dt - first_dt).total_seconds() / 60
            return round(duration, 2)
        except (ValueError, TypeError):
            return None

    async def stream_dshield_events_with_session_context(
        self,
        time_range_hours: int = 24,
        indices: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        fields: Optional[List[str]] = None,
        chunk_size: int = 500,
        session_fields: Optional[List[str]] = None,
        max_session_gap_minutes: int = 30,
        include_session_summary: bool = True,
        stream_id: Optional[str] = None
    ) -> tuple[List[Dict[str, Any]], int, Optional[str], Dict[str, Any]]:
        """
        Stream DShield events with smart session-based chunking.
        
        Groups events by session context (e.g., source IP, user session, connection ID)
        and ensures related events stay together in the same chunk.
        
        Args:
            session_fields: Fields to use for session grouping (e.g., ['source.ip', 'user.name'])
            max_session_gap_minutes: Maximum time gap within a session before starting new session
            include_session_summary: Include session metadata in response
            stream_id: Resume streaming from specific point
            
        Returns:
            Tuple of (events, total_count, next_stream_id, session_context)
        """
        if not self.client:
            await self.connect()
        
        # Initialize performance tracking
        performance_metrics = {
            "query_time_ms": 0,
            "optimization_applied": ["session_chunking"],
            "indices_scanned": 0,
            "total_documents_examined": 0,
            "query_complexity": "session_aware",
            "cache_hit": False,
            "shards_scanned": 0,
            "aggregations_used": False,
            "sessions_processed": 0,
            "session_chunks_created": 0
        }
        
        try:
            # Determine indices to query
            if indices is None:
                available_indices = await self.get_available_indices()
                if available_indices:
                    indices = available_indices
                else:
                    indices = self.fallback_indices
            elif not indices:
                indices = self.fallback_indices
                
            performance_metrics["indices_scanned"] = len(indices)
            
            # Default session fields if not specified
            if session_fields is None:
                session_fields = ["source.ip", "destination.ip", "user.name", "session.id"]
            
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
            
            # Add filters if provided
            if filters:
                mapped_filters = self._map_query_fields(filters)
                for key, value in mapped_filters.items():
                    if key == "@timestamp":
                        query["bool"]["must"].append({"range": {"@timestamp": value}})
                    elif isinstance(value, dict):
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
                        query["bool"]["must"].append({"term": {key: value}})
            
            # Build search body with session-aware sorting
            search_body = {
                "query": query,
                "size": min(chunk_size * 2, 2000),  # Get more events to group by session
                "sort": [
                    {"@timestamp": {"order": "desc"}},
                    {"_id": {"order": "desc"}}
                ]
            }
            
            # Add field selection if specified
            if fields:
                search_body["_source"] = fields
            
            # Add search_after for cursor-based pagination
            if stream_id:
                try:
                    timestamp_val, id_val = stream_id.split("|")
                    search_body["search_after"] = [timestamp_val, id_val]
                except (ValueError, AttributeError):
                    logger.warning(f"Invalid stream_id format: {stream_id}. Starting from beginning.")
            
            # Execute search with timing
            query_start = datetime.now()
            response = await self.client.search(
                index=",".join(indices),
                body=search_body
            )
            query_end = datetime.now()
            
            # Calculate query time
            performance_metrics["query_time_ms"] = int((query_end - query_start).total_seconds() * 1000)
            
            # Extract shard information
            if "_shards" in response:
                performance_metrics["shards_scanned"] = response["_shards"].get("total", 0)
            
            # Extract results
            hits = response.get("hits", {})
            total_count = hits.get("total", {}).get("value", 0)
            documents = hits.get("hits", [])
            
            # Track documents examined
            performance_metrics["total_documents_examined"] = total_count
            
            # Parse events and group by session
            events = []
            session_groups = {}
            session_context = {
                "session_fields": session_fields,
                "max_session_gap_minutes": max_session_gap_minutes,
                "sessions_in_chunk": 0,
                "session_summaries": []
            }
            
            for doc in documents:
                event = self._parse_dshield_event(doc, indices)
                if event:
                    # Generate session key
                    session_key = self._generate_session_key(event, session_fields)
                    
                    if session_key:
                        if session_key not in session_groups:
                            session_groups[session_key] = {
                                "events": [],
                                "first_timestamp": None,
                                "last_timestamp": None,
                                "session_metadata": {}
                            }
                        
                        session_groups[session_key]["events"].append(event)
                        
                        # Track session timestamps
                        timestamp = event.get("@timestamp")
                        if timestamp:
                            if not session_groups[session_key]["first_timestamp"]:
                                session_groups[session_key]["first_timestamp"] = timestamp
                            session_groups[session_key]["last_timestamp"] = timestamp
                        
                        # Extract session metadata
                        for field in session_fields:
                            if field in event:
                                session_groups[session_key]["session_metadata"][field] = event[field]
                    else:
                        # Events without session context go to a default group
                        if "no_session" not in session_groups:
                            session_groups["no_session"] = {
                                "events": [],
                                "first_timestamp": None,
                                "last_timestamp": None,
                                "session_metadata": {"type": "no_session"}
                            }
                        session_groups["no_session"]["events"].append(event)
            
            # Sort sessions by timestamp and create smart chunks
            sorted_sessions = sorted(
                session_groups.items(),
                key=lambda x: x[1]["last_timestamp"] or "1970-01-01",
                reverse=True
            )
            
            # Build final event list with session-aware chunking
            current_chunk_size = 0
            sessions_in_chunk = 0
            
            for session_key, session_data in sorted_sessions:
                session_events = session_data["events"]
                
                # Check if adding this session would exceed chunk size
                if current_chunk_size + len(session_events) > chunk_size and current_chunk_size > 0:
                    # Start new chunk
                    break
                
                # Add session events to current chunk
                events.extend(session_events)
                current_chunk_size += len(session_events)
                sessions_in_chunk += 1
                
                # Add session summary if requested
                if include_session_summary:
                    session_summary = {
                        "session_key": session_key,
                        "event_count": len(session_events),
                        "first_timestamp": session_data["first_timestamp"],
                        "last_timestamp": session_data["last_timestamp"],
                        "duration_minutes": self._calculate_session_duration(
                            session_data["first_timestamp"],
                            session_data["last_timestamp"]
                        ),
                        "metadata": session_data["session_metadata"]
                    }
                    session_context["session_summaries"].append(session_summary)
            
            session_context["sessions_in_chunk"] = sessions_in_chunk
            performance_metrics["sessions_processed"] = len(session_groups)
            performance_metrics["session_chunks_created"] = 1
            
            # Generate next stream_id for cursor-based pagination
            next_stream_id = None
            if documents:
                last_hit = documents[-1]
                sort_values = last_hit.get("sort", [])
                if len(sort_values) >= 2:
                    next_stream_id = f"{sort_values[0]}|{sort_values[1]}"
            
            # Add performance metrics to session context
            session_context["performance_metrics"] = performance_metrics
            
            logger.info(f"Streamed {len(events)} events in {sessions_in_chunk} sessions from {len(indices)} indices", 
                       total_count=total_count, chunk_size=chunk_size, stream_id=stream_id,
                       sessions_processed=len(session_groups), query_time_ms=performance_metrics["query_time_ms"])
            
            return events, total_count, next_stream_id, session_context
            
        except Exception as e:
            logger.error(f"Error streaming DShield events with session context: {str(e)}")
            raise 