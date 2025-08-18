"""Elasticsearch client for querying DShield SIEM events and logs.

Optimized for DShield SIEM integration patterns.
"""

import asyncio
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Union, Tuple, AsyncGenerator
from urllib.parse import urlparse
import inspect

import structlog
from elasticsearch import AsyncElasticsearch
from elasticsearch.exceptions import RequestError, TransportError
from .models import SecurityEvent, ElasticsearchQuery, QueryFilter
from .config_loader import get_config, ConfigError
from .user_config import get_user_config
from .mcp_error_handler import MCPErrorHandler
from packaging import version
import elasticsearch as es_module

logger = structlog.get_logger(__name__)


class ElasticsearchClient:
    """Client for interacting with DShield SIEM Elasticsearch."""
    
    def __init__(self, error_handler: Optional[MCPErrorHandler] = None):
        """Initialize the Elasticsearch client.
        
        Sets up the client connection, field mappings, and configuration
        for DShield SIEM integration.
        
        Args:
            error_handler: Optional MCPErrorHandler instance for proper error handling
        
        New config option:
            - 'compatibility_mode' (bool, default: false):
                If true, sets compatibility_mode=True on the Elasticsearch Python client (for ES 8.x servers).
        """
        self.client: Optional[AsyncElasticsearch] = None
        self.error_handler = error_handler
        try:
            config = get_config()
            es_config = config["elasticsearch"]
            
            # Debug: Log raw config values
            logger.debug("Raw Elasticsearch config", 
                        url=es_config.get("url"),
                        username_type=type(es_config.get("username")).__name__,
                        password_type=type(es_config.get("password")).__name__,
                        username_length=len(str(es_config.get("username", ""))) if es_config.get("username") else 0,
                        password_length=len(str(es_config.get("password", ""))) if es_config.get("password") else 0)
            
        except Exception as e:
            raise RuntimeError(f"Failed to load Elasticsearch config: {e}")

        self.url = es_config["url"]
        self.username = es_config.get("username", "")
        self.password = es_config.get("password", "")
        
        # Debug: Log processed values
        logger.debug("Processed Elasticsearch credentials",
                    url=self.url,
                    username_type=type(self.username).__name__,
                    password_type=type(self.password).__name__,
                    username_length=len(str(self.username)) if self.username else 0,
                    password_length=len(str(self.password)) if self.password else 0)
        
        self.verify_ssl = es_config.get("verify_ssl", True)
        self.ca_certs = es_config.get("ca_certs", None)
        self.timeout = int(es_config.get("timeout", 30))
        self.max_results = int(es_config.get("max_results", 1000))
        self.compatibility_mode = es_config.get("compatibility_mode", False)
        
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

        # DShield specific field mappings - updated to match actual available fields from Elasticsearch
        self.dshield_field_mappings = {
            'timestamp': ['@timestamp', 'timestamp', 'time', 'date', 'event.ingested'],
            'source_ip': [
                'source.ip', 'src_ip', 'srcip', 'sourceip', 'attacker_ip', 'attackerip', 'src', 'client_ip', 'ip.src', 'ip_source', 'source.address', 'related.ip'
            ],
            'destination_ip': [
                'destination.ip', 'dst_ip', 'dstip', 'destinationip', 'target_ip', 'targetip', 'dst', 'server_ip', 'ip.dst', 'ip_destination', 'destination.address', 'related.ip'
            ],
            'source_port': [
                'source.port', 'src_port', 'srcport', 'sourceport', 'attacker_port', 'sport', 'client_port', 'port.src', 'port_source'
            ],
            'destination_port': [
                'destination.port', 'dst_port', 'dstport', 'destinationport', 'target_port', 'dport', 'server_port', 'port.dst', 'port_destination'
            ],
            'event_type': ['event.type', 'type', 'eventtype', 'event_type', 'event.category'],
            'category': ['event.category', 'category', 'eventcategory', 'event_category'],
            'severity': ['event.severity', 'severity', 'level', 'risk_level', 'threat_level', 'event.level'],
            'description': ['event.description', 'message', 'description', 'summary', 'attack_description', 'event.original'],
            'protocol': ['network.protocol', 'protocol', 'proto', 'transport_protocol', 'event.protocol', 'ip.proto'],
            'country': ['source.geo.country_name', 'country', 'country_name', 'geo.country', 'source.country'],
            'asn': ['asn', 'as_number', 'autonomous_system', 'attacker_asn', 'source.geo.asn'],
            'organization': ['org', 'organization', 'org_name', 'attacker_org', 'source.geo.organization_name'],
            'reputation_score': ['reputation', 'reputation_score', 'dshield_score', 'threat_score'],
            'attack_count': ['count', 'attack_count', 'hits', 'attempts'],
            'first_seen': ['firstseen', 'first_seen', 'first_seen_date'],
            'last_seen': ['lastseen', 'last_seen', 'last_seen_date'],
            'tags': ['tags', 'event.tags', 'labels', 'categories'],
            'attack_types': ['attacks', 'attack_types', 'attack_methods'],
            # Add ECS and observed fields from debug logs
            'event_kind': ['event.kind'],
            'event_dataset': ['event.dataset'],
            'host': ['host'],
            'region': ['region'],
            'network_ttl': ['network.ttl'],
            'event_outcome': ['event.outcome'],
            'source_geo': ['source.geo'],
            'interface_alias': ['interface.alias'],
            'related_host': ['related.host', 'related.hosts'],
            'source_mac': ['source.mac'],
            'network_bytes': ['network.bytes'],
            'event_id': ['event.id'],
            'input': ['input'],
            'log': ['log'],
            'process_id': ['process.id'],
            'destination_mac': ['destination.mac'],
            'network_direction': ['network.direction'],
            'ecs': ['ecs'],
            'network_type': ['network.type'],
            'source': ['source'],
            'interface_name': ['interface.name'],
            'related_ip': ['related.ip'],
            'destination': ['destination'],
            'file_directory': ['file.directory'],
            'event_code': ['event.code'],
            'event_duration': ['event.duration'],
            'event_original': ['event.original'],
            'destination_geo': ['destination.geo'],
            'agent': ['agent'],
            'user_agent': ['user_agent.original', 'user_agent', 'useragent', 'agent'],
            'url_original': ['url.original'],
            'url_query': ['url.query'],
            'http_method': ['http.request.method', 'http_method', 'method', 'request_method'],
            'http_status': ['http.response.status_code', 'http_status', 'status_code', 'response_status'],
            'http_version': ['http.version', 'http_version', 'version'],
        }
        
    async def connect(self):
        """Connect to Elasticsearch cluster."""
        try:
            logger.info("Starting Elasticsearch connection", url=self.url, username=self.username[:3] + "***" if self.username else None)
            
            # Parse URL to extract host and port
            try:
                parsed_url = urlparse(self.url)
                logger.debug("URL parsed successfully", hostname=parsed_url.hostname, port=parsed_url.port, scheme=parsed_url.scheme)
            except Exception as e:
                logger.error("Failed to parse URL", url=self.url, error=str(e))
                raise
            
            hosts = [{
                'host': parsed_url.hostname,
                'port': parsed_url.port or 9200,
                'scheme': parsed_url.scheme or 'http'
            }]
            logger.debug("Hosts configuration", hosts=hosts)
            
            # Configure SSL/TLS
            ssl_options = {}
            if self.verify_ssl and self.ca_certs:
                ssl_options['ca_certs'] = self.ca_certs
            elif not self.verify_ssl:
                ssl_options['verify_certs'] = False
                ssl_options['ssl_show_warn'] = False
            
            logger.debug("SSL options", ssl_options=ssl_options)
            
            # Handle authentication
            auth_config = None
            if self.password:
                try:
                    # Ensure password is string and not None
                    if self.password is None:
                        logger.error("Password is None - 1Password secret resolution may have failed")
                        raise ValueError("Password is None - check 1Password CLI configuration")
                    
                    password_str = str(self.password)
                    username_str = str(self.username) if self.username is not None else ""
                    
                    # Validate credentials
                    if not username_str or not password_str:
                        logger.error("Invalid credentials - username or password is empty", 
                                   username_length=len(username_str), 
                                   password_length=len(password_str))
                        raise ValueError("Invalid credentials - username or password is empty")
                    
                    auth_config = (username_str, password_str)
                    logger.debug("Authentication configured", username=username_str[:3] + "***")
                except Exception as e:
                    logger.error("Failed to configure authentication", error=str(e))
                    raise
            
            # Create client
            es_kwargs = dict(
                hosts=hosts,
                http_auth=auth_config,
                request_timeout=self.timeout,
                max_retries=3,
                retry_on_timeout=True,
                **ssl_options
            )
            
            # Only add compatibility_mode if the client supports it (>=8.7.0) and the argument exists
            try:
                es_version_raw = getattr(es_module, '__version__', '0.0.0')
                if isinstance(es_version_raw, tuple):
                    es_version_str = '.'.join(str(x) for x in es_version_raw)
                else:
                    es_version_str = str(es_version_raw)
                logger.debug("Raw elasticsearch module version", es_version_raw=es_version_raw, es_version_str=es_version_str)
                es_version = version.parse(es_version_str)

                # Check if compatibility_mode is a valid argument
                compat_mode_supported = 'compatibility_mode' in inspect.signature(AsyncElasticsearch.__init__).parameters
                logger.debug("compatibility_mode supported", compat_mode_supported=compat_mode_supported)

                if self.compatibility_mode and es_version >= version.parse('8.7.0') and compat_mode_supported:
                    es_kwargs['compatibility_mode'] = True
                    logger.debug("Added compatibility_mode to client kwargs")
                elif self.compatibility_mode and not compat_mode_supported:
                    logger.warning("compatibility_mode requested but not supported by this elasticsearch client version or class signature")
            except Exception as e:
                logger.error("Failed to check elasticsearch client version or compatibility_mode support", error=str(e))
            
            logger.debug("Creating AsyncElasticsearch client", kwargs_keys=list(es_kwargs.keys()))
            
            try:
                self.client = AsyncElasticsearch(**es_kwargs)
                logger.debug("AsyncElasticsearch client created successfully")
            except Exception as e:
                logger.error("Failed to create AsyncElasticsearch client", error=str(e), kwargs_keys=list(es_kwargs.keys()))
                raise
            
            # Test connection
            try:
                info = await self.client.info()
                logger.info("Connected to Elasticsearch", 
                           cluster_name=info['cluster_name'],
                           version=info['version']['number'])
            except Exception as e:
                logger.error("Failed to get Elasticsearch info", error=str(e))
                raise
            
        except Exception as e:
            logger.error("Failed to connect to Elasticsearch", error=str(e), error_type=type(e).__name__)
            if self.error_handler:
                # Create appropriate error response based on exception type
                if isinstance(e, TransportError):
                    raise RuntimeError(f"Elasticsearch connection failed: {str(e)}")
                else:
                    raise RuntimeError(f"Elasticsearch setup failed: {str(e)}")
            else:
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
            if self.error_handler:
                # Log error but return empty list to allow fallback
                logger.warning("Using fallback indices due to index discovery failure")
                return []
            else:
                # Fallback to raising exception if no error handler
                raise
    
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
            if self.error_handler:
                # Create appropriate error response based on exception type
                if isinstance(e, RequestError):
                    return [], 0, {"error": self.error_handler.create_external_service_error("Elasticsearch", str(e))}
                elif isinstance(e, TransportError):
                    return [], 0, {"error": self.error_handler.create_external_service_error("Elasticsearch", f"Connection error: {str(e)}")}
                elif isinstance(e, ValueError):
                    return [], 0, {"error": self.error_handler.create_invalid_params_error(str(e))}
                else:
                    return [], 0, {"error": self.error_handler.create_internal_error(f"Query execution failed: {str(e)}")}
            else:
                # Fallback to raising exception if no error handler
                raise

    async def _estimate_query_size(
        self, 
        time_range_hours: int, 
        indices: List[str], 
        filters: Optional[Dict[str, Any]], 
        fields: Optional[List[str]], 
        page_size: int
    ) -> float:
        """Estimate the size of a query result in MB.
        
        Performs a lightweight query to estimate the size of the full
        result set. This is used for smart query optimization to
        determine if optimization is needed.
        
        Args:
            time_range_hours: Time range in hours to query
            indices: List of indices to query
            filters: Query filters to apply
            fields: Fields to include in the result
            page_size: Number of results per page
        
        Returns:
            Estimated result size in megabytes
            
        Raises:
            RequestError: If the estimation query fails

        """
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
        """Optimize field selection for better performance.
        
        Analyzes the requested fields and optimizes the selection
        to improve query performance while maintaining data quality.
        This includes removing redundant fields and adding essential
        fields that are needed for proper event parsing.
        
        Args:
            fields: List of requested fields
        
        Returns:
            Optimized list of fields for the query

        """
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
        """Apply fallback strategy when query optimization fails.
        
        Implements various fallback strategies when the primary query
        optimization fails or is insufficient. Strategies include
        aggregation, sampling, or error reporting.
        
        Args:
            strategy: Fallback strategy to apply ('aggregate', 'sample', 'error')
            time_range_hours: Time range in hours to query
            indices: List of indices to query
            filters: Query filters to apply
            sort_by: Field to sort by
            sort_order: Sort order ('asc' or 'desc')
            optimization_applied: Description of optimization that was applied
        
        Returns:
            Tuple containing:
                - List of event dictionaries (or aggregated results)
                - Total count or aggregated count
                - Pagination/aggregation information
        
        Raises:
            ValueError: If the fallback strategy is invalid
            RequestError: If the fallback query fails

        """
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
                        "timestamp": datetime.now(timezone.utc).isoformat(),
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
                        "timestamp": datetime.now(timezone.utc).isoformat(),
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
        """Execute an aggregation query on Elasticsearch.
        
        Performs aggregation queries for statistical analysis and
        data summarization. This is useful for generating reports
        and understanding data patterns without retrieving full records.
        
        Args:
            index: List of indices to query
            query: Base query to filter documents
            aggregation_query: Aggregation definition to apply
        
        Returns:
            Dictionary containing aggregation results
            
        Raises:
            ConnectionError: If not connected to Elasticsearch
            RequestError: If the aggregation query fails

        """
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
            if self.error_handler:
                # Create appropriate error response based on exception type
                if isinstance(e, RequestError):
                    return {"error": self.error_handler.create_external_service_error("Elasticsearch", str(e))}
                elif isinstance(e, TransportError):
                    return {"error": self.error_handler.create_external_service_error("Elasticsearch", f"Connection error: {str(e)}")}
                else:
                    return {"error": self.error_handler.create_internal_error(f"Aggregation query failed: {str(e)}")}
            else:
                # Fallback to raising exception if no error handler
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
        """Stream DShield events in chunks for large datasets.
        
        Retrieves DShield events in configurable chunks to handle
        very large datasets efficiently. This method is designed
        for processing large amounts of data without memory issues.
        
        Args:
            time_range_hours: Time range in hours to query (default: 24)
            indices: Specific indices to query (default: all DShield indices)
            filters: Additional query filters to apply
            fields: Specific fields to return (reduces payload size)
            chunk_size: Number of events per chunk (default: 500, max: 1000)
            stream_id: Optional stream ID for resuming interrupted streams
        
        Returns:
            Tuple containing:
                - List of event dictionaries for the current chunk
                - Total count of available events
                - Next stream ID for continuing the stream (None if complete)
        
        Raises:
            ConnectionError: If not connected to Elasticsearch
            RequestError: If the streaming query fails
            ValueError: If parameters are invalid

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
            if self.error_handler:
                # Create appropriate error response based on exception type
                if isinstance(e, RequestError):
                    return [], 0, {"error": self.error_handler.create_external_service_error("Elasticsearch", str(e))}
                elif isinstance(e, TransportError):
                    return [], 0, {"error": self.error_handler.create_external_service_error("Elasticsearch", f"Connection error: {str(e)}")}
                elif isinstance(e, ValueError):
                    return [], 0, {"error": self.error_handler.create_invalid_params_error(str(e))}
                else:
                    return [], 0, {"error": self.error_handler.create_internal_error(f"Streaming failed: {str(e)}")}
            else:
                # Fallback to raising exception if no error handler
                raise
    
    async def query_dshield_attacks(
        self,
        time_range_hours: int = 24,
        page: int = 1,
        page_size: int = 100,
        include_summary: bool = True
    ) -> tuple[List[Dict[str, Any]], int]:
        """Query DShield attack data specifically.
        
        Retrieves attack-specific data from DShield indices, focusing
        on security events that represent actual attacks rather than
        general network traffic or logs.
        
        Args:
            time_range_hours: Time range in hours to query (default: 24)
            page: Page number for pagination (default: 1)
            page_size: Number of results per page (default: 100, max: 1000)
            include_summary: Whether to include summary statistics
        
        Returns:
            Tuple containing:
                - List of attack event dictionaries
                - Total count of available attacks
        
        Raises:
            ConnectionError: If not connected to Elasticsearch
            RequestError: If the query fails

        """
        if not self.client:
            await self.connect()
        
        # Calculate time range
        end_time = datetime.now(timezone.utc)
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
            if self.error_handler:
                return [], 0
            else:
                raise
        except Exception as e:
            logger.error("Unexpected error during attack query", error=str(e))
            if self.error_handler:
                return [], 0
            else:
                raise
    
    async def query_dshield_reputation(
        self,
        ip_addresses: Optional[List[str]] = None,
        size: int = 1000
    ) -> List[Dict[str, Any]]:
        """Query DShield reputation data for IP addresses.
        
        Retrieves reputation and threat intelligence data for specific
        IP addresses or all IPs in the DShield reputation database.
        
        Args:
            ip_addresses: List of IP addresses to query (default: all IPs)
            size: Maximum number of results to return (default: 1000)
        
        Returns:
            List of reputation data dictionaries
        
        Raises:
            ConnectionError: If not connected to Elasticsearch
            RequestError: If the query fails

        """
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
        """Query DShield top attackers data.
        
        Retrieves the most active attacker IP addresses based on
        attack frequency and severity within the specified time period.
        
        Args:
            hours: Time range in hours to analyze (default: 24)
            limit: Maximum number of attackers to return (default: 100)
        
        Returns:
            List of top attacker data dictionaries
        
        Raises:
            ConnectionError: If not connected to Elasticsearch
            RequestError: If the query fails

        """
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
        """Query DShield geographic attack data.
        
        Retrieves attack data grouped by geographic location,
        including country-level statistics and attack patterns.
        
        Args:
            countries: List of countries to filter by (default: all countries)
            size: Maximum number of results to return (default: 1000)
        
        Returns:
            List of geographic attack data dictionaries
        
        Raises:
            ConnectionError: If not connected to Elasticsearch
            RequestError: If the query fails

        """
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
        """Query DShield port attack data.
        
        Retrieves attack data grouped by destination ports,
        including port-specific attack patterns and statistics.
        
        Args:
            ports: List of ports to filter by (default: all ports)
            size: Maximum number of results to return (default: 1000)
        
        Returns:
            List of port attack data dictionaries
        
        Raises:
            ConnectionError: If not connected to Elasticsearch
            RequestError: If the query fails

        """
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
        """Query DShield events for specific IP addresses.
        
        Retrieves all events associated with the specified IP addresses,
        including both source and destination IP matches. This is useful
        for investigating specific IP addresses involved in attacks.
        
        Args:
            ip_addresses: List of IP addresses to search for
            time_range_hours: Time range in hours to query (default: 24)
            indices: Specific indices to query (default: all DShield indices)
        
        Returns:
            List of event dictionaries for the specified IPs
        
        Raises:
            RuntimeError: If Elasticsearch client is not connected
            RequestError: If the query fails

        """
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
        end_time = datetime.now(timezone.utc)
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
        """Get comprehensive DShield statistics and summary.
        
        Retrieves aggregated statistics from multiple DShield data sources,
        including event counts, top attackers, geographic distribution,
        and other summary metrics.
        
        Args:
            time_range_hours: Time range in hours for statistics (default: 24)
        
        Returns:
            Dictionary containing comprehensive statistics including:
                - total_events: Total number of events
                - top_attackers: List of most active attackers
                - geographic_distribution: Attack distribution by country
                - time_range_hours: Time range used for analysis
                - timestamp: When the statistics were generated
                - indices_queried: List of indices that were actually queried
                - diagnostic_info: Additional diagnostic information if issues occur
        
        Raises:
            Exception: If statistics collection fails

        """
        try:
            # Get available indices first
            available_indices = await self.get_available_indices()
            
            if not available_indices:
                logger.warning("No DShield indices available for statistics query")
                return {
                    'total_events': 0,
                    'top_attackers': [],
                    'geographic_distribution': {},
                    'time_range_hours': time_range_hours,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'indices_queried': [],
                    'diagnostic_info': {
                        'warning': 'No DShield indices found',
                        'configured_patterns': self.dshield_indices,
                        'fallback_patterns': self.fallback_indices,
                        'suggestion': 'Check index_patterns configuration and ensure indices exist'
                    }
                }
            
            logger.info("Querying DShield statistics", 
                       available_indices=available_indices, 
                       time_range_hours=time_range_hours)
            
            # Query events using available indices
            summary_events, total_count, _ = await self.query_dshield_events(
                time_range_hours=time_range_hours,
                indices=available_indices,
                page_size=100
            )
            
            # Query top attackers
            top_attackers = await self.query_dshield_top_attackers(time_range_hours)
            
            # Query geographic data
            geo_data = await self.query_dshield_geographic_data()
            
            # Compile statistics
            stats = {
                'total_events': total_count if total_count > 0 else len(summary_events),
                'top_attackers': top_attackers[:10] if top_attackers else [],
                'geographic_distribution': self._compile_geo_stats(geo_data) if geo_data else {},
                'time_range_hours': time_range_hours,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'indices_queried': available_indices,
                'diagnostic_info': {
                    'status': 'success',
                    'indices_found': len(available_indices),
                    'events_retrieved': len(summary_events),
                    'total_count': total_count
                }
            }
            
            logger.info("Successfully retrieved DShield statistics", 
                       total_events=stats['total_events'],
                       indices_queried=len(available_indices))
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get DShield statistics", 
                        error=str(e), 
                        time_range_hours=time_range_hours)
            
            # Return diagnostic information instead of empty dict
            return {
                'total_events': 0,
                'top_attackers': [],
                'geographic_distribution': {},
                'time_range_hours': time_range_hours,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'indices_queried': [],
                'diagnostic_info': {
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'configured_patterns': getattr(self, 'dshield_indices', []),
                    'fallback_patterns': getattr(self, 'fallback_indices', []),
                    'suggestion': 'Use diagnose_data_availability tool to troubleshoot'
                }
            }
    
    def _build_dshield_query(
        self,
        start_time: datetime,
        end_time: datetime,
        filters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build Elasticsearch query for DShield events.
        
        Constructs a standardized Elasticsearch query for DShield
        security events with proper time range filtering and
        additional filter criteria.
        
        Args:
            start_time: Start time for the query range
            end_time: End time for the query range
            filters: Additional filter criteria to apply
        
        Returns:
            Dictionary containing the complete Elasticsearch query
        
        Raises:
            ValueError: If time range is invalid

        """
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
        """Build Elasticsearch query for IP-specific events.
        
        Constructs a query that matches events where the specified
        IP addresses appear as either source or destination IPs.
        
        Args:
            ip_addresses: List of IP addresses to search for
            start_time: Start time for the query range
            end_time: End time for the query range
        
        Returns:
            Dictionary containing the complete Elasticsearch query
        
        Raises:
            ValueError: If time range is invalid or IP list is empty

        """
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
        """Parse Elasticsearch hit into standardized DShield event.
        
        Converts raw Elasticsearch document into a standardized
        DShield event format with proper field mapping and
        data normalization.
        
        Args:
            hit: Raw Elasticsearch hit document
            indices: List of indices the hit came from (for context)
        
        Returns:
            Standardized DShield event dictionary or None if parsing fails
        
        Raises:
            KeyError: If required fields are missing
            ValueError: If timestamp parsing fails

        """
        try:
            source = hit['_source']
            self.log_unmapped_fields(source)
            
            # Defensive: ensure source is a dict
            if not isinstance(source, dict):
                logger.error("Elasticsearch hit _source is not a dict", hit=hit)
                return None
            
            # Extract timestamp using DShield field mappings
            timestamp = self._extract_field_mapped(source, 'timestamp')
            if isinstance(timestamp, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                except Exception as e:
                    logger.warning("Failed to parse timestamp string", value=timestamp, error=str(e))
                    timestamp = datetime.now(timezone.utc)
            elif not isinstance(timestamp, datetime):
                timestamp = datetime.now(timezone.utc)
            
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
            
            # Extract HTTP fields for description derivation
            http_method = self._extract_field_mapped(source, 'http_method')
            http_status = self._extract_field_mapped(source, 'http_status')
            user_agent = self._extract_field_mapped(source, 'user_agent')
            
            # Extract description using DShield field mappings with better fallback
            description = self._extract_field_mapped(source, 'description')
            
            # Derive description from HTTP fields if not directly available
            if not description:
                if http_method and http_status:
                    description = f"HTTP {http_method} request with status {http_status}"
                elif http_method:
                    description = f"HTTP {http_method} request"
                elif user_agent:
                    description = f"Request with user agent: {str(user_agent)[:50]}..."
                else:
                    description = f"{event_type} event from {source_ip or 'unknown'} to {destination_ip or 'unknown'}"
            
            # Extract protocol using DShield field mappings
            protocol = self._extract_field_mapped(source, 'protocol')
            
            # Derive protocol from HTTP fields if not directly available
            if not protocol:
                http_version = self._extract_field_mapped(source, 'http_version')
                if http_version:
                    protocol = 'http'
                elif source_port == 443 or destination_port == 443:
                    protocol = 'https'
                elif source_port == 80 or destination_port == 80:
                    protocol = 'http'
                else:
                    protocol = 'unknown'
            
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
            
            # Ensure tags and attack_types are lists
            if not isinstance(tags, list):
                tags = [tags] if tags else []
            if not isinstance(attack_types, list):
                attack_types = [attack_types] if attack_types else []
            
            # Provide fallback values for critical fields
            if not severity:
                severity = 'medium'
            if not event_category:
                event_category = 'other'
            if not event_type:
                event_type = 'unknown'
            
            event = {
                'id': hit.get('_id'),
                'timestamp': timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp),
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
        except TypeError as e:
            logger.error("TypeError while parsing Elasticsearch hit", hit=hit, error=str(e))
            return None
        except Exception as e:
            logger.warning("Failed to parse DShield event", hit_id=hit.get('_id'), error=str(e))
            return None
    
    def _extract_field_mapped(self, source: Dict[str, Any], field_type: str, default: Any = None) -> Any:
        """Extract field value using DShield field mappings.
        
        Supports dot notation for both top-level and nested fields. Attempts to map the requested field type
        to the correct field in the source document using the DShield field mapping configuration.
        
        Args:
            source: Source dictionary from Elasticsearch document
            field_type: Logical DShield field type to extract (e.g., 'source_ip', 'event_type')
            default: Default value to return if field is not found
        
        Returns:
            The extracted value if found, otherwise the default value

        """
        mapped = False
        tried_fields = []
        if field_type in self.dshield_field_mappings:
            field_names = self.dshield_field_mappings[field_type]
            for field in field_names:
                tried_fields.append(field)
                # First, check if the field exists as a top-level key (including dot notation)
                if field in source:
                    value = source[field]
                    if value is not None:
                        mapped = True
                        return value
                # Next, support dot notation for nested fields
                if "." in field:
                    value = source
                    for part in field.split("."):
                        if isinstance(value, dict) and part in value:
                            value = value[part]
                        else:
                            value = None
                            break
                    if value is not None:
                        mapped = True
                        return value
        # Try to match nested fields at one level deep if not found above
        if not mapped:
            for key in source.keys():
                if isinstance(source[key], dict):
                    for field in self.dshield_field_mappings.get(field_type, []):
                        if field in source[key]:
                            value = source[key][field]
                            if value is not None:
                                mapped = True
                                return value
        if not mapped:
            logger.debug(f"Field type '{field_type}' not mapped in document.", tried_fields=tried_fields, available_fields=list(source.keys()))
        return default

    def log_unmapped_fields(self, source: Dict[str, Any]):
        """Log any fields in the source document that are not mapped to any known field type.
        
        Args:
            source: Source dictionary from Elasticsearch document
        
        Returns:
            None

        """
        mapped_fields = set()
        for field_list in self.dshield_field_mappings.values():
            mapped_fields.update(field_list)
        unmapped = [f for f in source.keys() if f not in mapped_fields]
        if unmapped:
            logger.info("Unmapped fields detected in document", unmapped_fields=unmapped)
    
    def _compile_geo_stats(self, geo_data: List[Dict[str, Any]]) -> Dict[str, int]:
        """Compile geographic statistics from geo data.
        
        Aggregates event counts by country from a list of geo-tagged events.
        
        Args:
            geo_data: List of event dictionaries containing 'country' keys
        
        Returns:
            Dictionary mapping country names to event counts

        """
        country_counts = {}
        for event in geo_data:
            country = event.get('country')
            if country:
                country_counts[country] = country_counts.get(country, 0) + 1
        return country_counts
    
    async def query_security_events(
        self,
        time_range_hours: int = 24,
        indices: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        size: Optional[int] = None,
        timeout: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Backward compatibility method - redirects to query_dshield_events.
        
        Args:
            time_range_hours: Time range in hours to query (default: 24)
            indices: List of indices to query (optional)
            filters: Query filters to apply (optional)
            size: Number of results to return (optional)
            timeout: Query timeout in seconds (optional)
        
        Returns:
            List of event dictionaries

        """
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
        """Generate pagination information for response.
        
        Args:
            page: Current page number
            page_size: Number of results per page
            total_count: Total number of results available
        
        Returns:
            Dictionary containing pagination metadata, including current page, total pages, and navigation info

        """
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
        Supports both traditional page-based and cursor-based pagination.
        
        Args:
            page: Current page number
            page_size: Number of results per page
            total_count: Total number of results available
            cursor: Current cursor token for cursor-based pagination
            next_cursor: Next cursor token for continuing pagination
            sort_by: Field used for sorting
            sort_order: Sort order ('asc' or 'desc')
        
        Returns:
            Dictionary containing comprehensive pagination metadata

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
        """Get mapping for an index pattern.
        
        Retrieves the field mapping information for the specified
        index pattern from Elasticsearch.
        
        Args:
            index_pattern: Index pattern to get mapping for
        
        Returns:
            Dictionary containing the index mapping information
        
        Raises:
            RuntimeError: If Elasticsearch client is not connected
            Exception: If the mapping request fails

        """
        if not self.client:
            raise RuntimeError("Elasticsearch client not connected")
        
        try:
            response = await self.client.indices.get_mapping(index=index_pattern)
            return response
        except Exception as e:
            logger.error("Failed to get index mapping", index=index_pattern, error=str(e))
            raise
    
    async def get_cluster_stats(self) -> Dict[str, Any]:
        """Get Elasticsearch cluster statistics.
        
        Retrieves comprehensive statistics about the Elasticsearch
        cluster including node information, indices, and performance metrics.
        
        Returns:
            Dictionary containing cluster statistics
        
        Raises:
            RuntimeError: If Elasticsearch client is not connected
            Exception: If the cluster stats request fails

        """
        if not self.client:
            raise RuntimeError("Elasticsearch client not connected")
        
        try:
            stats = await self.client.cluster.stats()
            return stats
        except Exception as e:
            logger.error("Failed to get cluster stats", error=str(e))
            raise 

    def _map_query_fields(self, filters: Dict[str, Any]) -> Dict[str, Any]:
        """Map user-friendly field names to ECS dot notation for querying.
        
        This handles the mismatch between display fields (source_ip) and 
        query fields (source.ip) as described in GitHub issue #17.
        Converts user-friendly field names to the proper Elasticsearch
        Common Schema (ECS) field names for querying.
        
        Args:
            filters: Dictionary containing user-friendly field names and values
        
        Returns:
            Dictionary with field names mapped to ECS notation
        
        Raises:
            ValueError: If field mapping is invalid

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
        """Get suggestions for field name alternatives.
        
        Provides alternative field names when a user-friendly field name
        is not found in the mapping. This helps users understand the
        correct ECS field names to use.
        
        Args:
            field_name: The field name that needs alternatives
        
        Returns:
            List of suggested field name alternatives

        """
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
        """Generate a session key from event data using specified session fields.
        
        Creates a unique session identifier by combining values from
        specified session fields. This is used for grouping related
        events together in session-based streaming.
        
        Args:
            event: The event data dictionary
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
        """Calculate session duration in minutes.
        
        Computes the duration between the first and last events in a session.
        This is used for session analysis and reporting.
        
        Args:
            first_timestamp: First event timestamp in ISO format
            last_timestamp: Last event timestamp in ISO format
        
        Returns:
            Duration in minutes or None if timestamps are invalid
        
        Raises:
            ValueError: If timestamp format is invalid

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
        """Stream DShield events with smart session-based chunking.
        
        Groups events by session context (e.g., source IP, user session, connection ID)
        and ensures related events stay together in the same chunk. This is useful
        for event correlation and analysis.
        
        Args:
            time_range_hours: Time range in hours to query (default: 24)
            indices: Specific indices to query (default: all DShield indices)
            filters: Additional query filters to apply
            fields: Specific fields to return (reduces payload size)
            chunk_size: Number of events per chunk (default: 500, max: 1000)
            session_fields: Fields to use for session grouping (default: ['source.ip', 'destination.ip', 'user.name', 'session.id'])
            max_session_gap_minutes: Maximum time gap within a session before starting new session (default: 30)
            include_session_summary: Include session metadata in response (default: True)
            stream_id: Resume streaming from specific point
        
        Returns:
            Tuple containing:
                - List of event dictionaries for the current chunk
                - Total count of available events
                - Next stream ID for continuing the stream (None if complete)
                - Session context information
        
        Raises:
            ConnectionError: If not connected to Elasticsearch
            RequestError: If the streaming query fails
            ValueError: If parameters are invalid

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

    async def check_health(self) -> bool:
        """Check Elasticsearch connectivity and health.
        
        Returns:
            bool: True if Elasticsearch is healthy and accessible, False otherwise
        """
        try:
            # Check if we have valid configuration
            if not self.url:
                logger.error("Elasticsearch URL not configured")
                return False
            
            # Try to create a connection and check cluster health
            if not self.client:
                await self.connect()
            
            if self.client:
                # Check cluster health
                try:
                    health_response = await self.client.cluster.health(timeout="5s")
                    cluster_status = health_response.get("status", "unknown")
                    
                    # Consider cluster healthy if status is green, yellow, or red (but accessible)
                    is_healthy = cluster_status in ["green", "yellow", "red"]
                    
                    if is_healthy:
                        logger.debug("Elasticsearch cluster health check passed", 
                                   status=cluster_status, 
                                   cluster_name=health_response.get("cluster_name"),
                                   number_of_nodes=health_response.get("number_of_nodes"))
                    else:
                        logger.warning("Elasticsearch cluster health check failed", 
                                     status=cluster_status)
                    
                    return is_healthy
                    
                except Exception as e:
                    logger.error("Elasticsearch cluster health check failed", error=str(e))
                    return False
            else:
                logger.error("Failed to create Elasticsearch client connection")
                return False
                
        except Exception as e:
            logger.error("Elasticsearch health check failed", error=str(e))
            return False

    async def health_check(self) -> bool:
        """Check Elasticsearch connectivity and health (deprecated, use check_health)."""
        return await self.check_health()

    def _get_current_time(self) -> datetime:
        """Get current UTC time.
        
        Returns:
            Current UTC datetime
        """
        return datetime.now(timezone.utc)

    def _get_timestamp_for_query(self) -> str:
        """Get current timestamp in ISO format for queries.
        
        Returns:
            Current timestamp in ISO format
        """
        return datetime.now(timezone.utc).isoformat()

    def _get_timestamp_for_logging(self) -> str:
        """Get current timestamp in ISO format for logging.
        
        Returns:
            Current timestamp in ISO format
        """
        return datetime.now(timezone.utc).isoformat()

    def _get_timestamp_for_metrics(self) -> str:
        """Get current timestamp in ISO format for metrics.
        
        Returns:
            Current timestamp in ISO format
        """
        return datetime.now(timezone.utc).isoformat()

    def _get_timestamp_for_cache(self) -> datetime:
        """Get current UTC time for cache operations.
        
        Returns:
            Current UTC datetime
        """
        timestamp = datetime.now(timezone.utc)
        return timestamp

    def _get_timestamp_for_session(self) -> datetime:
        """Get current UTC time for session operations.
        
        Returns:
            Current UTC datetime
        """
        timestamp = datetime.now(timezone.utc)
        return timestamp