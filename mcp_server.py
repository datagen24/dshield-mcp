#!/usr/bin/env python3
"""
DShield MCP Server - Elastic SIEM Integration
Main server for handling MCP protocol communication and coordinating
between DShield Elasticsearch queries and DShield threat intelligence.
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import structlog
from mcp.server import Server
from mcp.server import NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server

from src.elasticsearch_client import ElasticsearchClient
from src.dshield_client import DShieldClient
from src.data_processor import DataProcessor
from src.context_injector import ContextInjector
from src.models import SecurityEvent, ThreatIntelligence, AttackReport, DShieldStatistics
from src.data_dictionary import DataDictionary

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class DShieldMCPServer:
    """Main MCP server for DShield Elastic SIEM integration."""
    
    def __init__(self):
        self.server = Server("dshield-elastic-mcp")
        self.elastic_client = None
        self.dshield_client = None
        self.data_processor = None
        self.context_injector = None
        
        # Register tools
        self._register_tools()
        
    def _register_tools(self):
        """Register all available MCP tools."""
        
        @self.server.list_tools()
        async def handle_list_tools() -> List[Dict[str, Any]]:
            """List all available tools."""
            return [
                {
                    "name": "query_dshield_events",
                    "description": "Query DShield events from Elasticsearch SIEM with enhanced pagination support",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "time_range_hours": {
                                "type": "integer",
                                "description": "Time range in hours to query (default: 24)"
                            },
                            "time_range": {
                                "type": "object",
                                "description": "Exact time range with start and end timestamps",
                                "properties": {
                                    "start": {"type": "string", "format": "date-time"},
                                    "end": {"type": "string", "format": "date-time"}
                                }
                            },
                            "relative_time": {
                                "type": "string",
                                "description": "Relative time range (e.g., 'last_6_hours', 'last_24_hours', 'last_7_days')"
                            },
                            "time_window": {
                                "type": "object",
                                "description": "Time window around a specific timestamp",
                                "properties": {
                                    "around": {"type": "string", "format": "date-time"},
                                    "window_minutes": {"type": "integer"}
                                }
                            },
                            "indices": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "DShield Elasticsearch indices to query"
                            },
                            "filters": {
                                "type": "object",
                                "description": "Additional query filters"
                            },
                            "fields": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific fields to return (reduces payload size)"
                            },
                            "page": {
                                "type": "integer",
                                "description": "Page number for pagination (default: 1)"
                            },
                            "page_size": {
                                "type": "integer",
                                "description": "Number of results per page (default: 100, max: 1000)"
                            },
                            "sort_by": {
                                "type": "string",
                                "description": "Field to sort by (default: '@timestamp')"
                            },
                            "sort_order": {
                                "type": "string",
                                "enum": ["asc", "desc"],
                                "description": "Sort order (default: 'desc')"
                            },
                            "cursor": {
                                "type": "string",
                                "description": "Cursor token for cursor-based pagination (better for large datasets)"
                            },
                            "optimization": {
                                "type": "string",
                                "enum": ["auto", "none"],
                                "description": "Smart query optimization mode (default: 'auto')"
                            },
                            "fallback_strategy": {
                                "type": "string",
                                "enum": ["aggregate", "sample", "error"],
                                "description": "Fallback strategy when optimization fails (default: 'aggregate')"
                            },
                            "max_result_size_mb": {
                                "type": "number",
                                "description": "Maximum result size in MB before optimization (default: 10.0)"
                            },
                            "query_timeout_seconds": {
                                "type": "integer",
                                "description": "Query timeout in seconds (default: 30)"
                            },
                            "include_summary": {
                                "type": "boolean",
                                "description": "Include summary statistics with results (default: true)"
                            }
                        }
                    }
                },
                {
                    "name": "stream_dshield_events_with_session_context",
                    "description": "Stream DShield events with smart session-based chunking for event correlation",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "time_range_hours": {
                                "type": "integer",
                                "description": "Time range in hours to query (default: 24)"
                            },
                            "indices": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific indices to query (optional)"
                            },
                            "filters": {
                                "type": "object",
                                "description": "Filter criteria (supports user-friendly field names)"
                            },
                            "fields": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific fields to return (optional)"
                            },
                            "chunk_size": {
                                "type": "integer",
                                "description": "Target chunk size (default: 500)"
                            },
                            "session_fields": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Fields to use for session grouping (default: ['source.ip', 'destination.ip', 'user.name', 'session.id'])"
                            },
                            "max_session_gap_minutes": {
                                "type": "integer",
                                "description": "Maximum time gap within a session (default: 30)"
                            },
                            "include_session_summary": {
                                "type": "boolean",
                                "description": "Include session metadata in response (default: true)"
                            },
                            "stream_id": {
                                "type": "string",
                                "description": "Resume streaming from specific point"
                            }
                        }
                    }
                },
                {
                    "name": "query_dshield_aggregations",
                    "description": "Get aggregated summary data without full records",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "time_range_hours": {
                                "type": "integer",
                                "description": "Time range in hours to query (default: 24)"
                            },
                            "time_range": {
                                "type": "object",
                                "description": "Exact time range with start and end timestamps",
                                "properties": {
                                    "start": {"type": "string", "format": "date-time"},
                                    "end": {"type": "string", "format": "date-time"}
                                }
                            },
                            "relative_time": {
                                "type": "string",
                                "description": "Relative time range (e.g., 'last_6_hours', 'last_24_hours', 'last_7_days')"
                            },
                            "group_by": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Fields to group by (e.g., ['source_ip', 'destination_port'])"
                            },
                            "metrics": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Metrics to calculate (e.g., ['count', 'unique_sessions', 'avg_duration'])"
                            },
                            "filters": {
                                "type": "object",
                                "description": "Additional query filters"
                            },
                            "top_n": {
                                "type": "integer",
                                "description": "Number of top results to return (default: 50)"
                            },
                            "sort_by": {
                                "type": "string",
                                "description": "Field to sort by (default: 'count')"
                            },
                            "sort_order": {
                                "type": "string",
                                "enum": ["asc", "desc"],
                                "description": "Sort order (default: 'desc')"
                            }
                        }
                    }
                },
                {
                    "name": "stream_dshield_events",
                    "description": "Stream DShield events for very large datasets with chunked processing",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "time_range_hours": {
                                "type": "integer",
                                "description": "Time range in hours to query (default: 24)"
                            },
                            "time_range": {
                                "type": "object",
                                "description": "Exact time range with start and end timestamps",
                                "properties": {
                                    "start": {"type": "string", "format": "date-time"},
                                    "end": {"type": "string", "format": "date-time"}
                                }
                            },
                            "relative_time": {
                                "type": "string",
                                "description": "Relative time range (e.g., 'last_6_hours', 'last_24_hours', 'last_7_days')"
                            },
                            "indices": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "DShield Elasticsearch indices to query"
                            },
                            "filters": {
                                "type": "object",
                                "description": "Additional query filters"
                            },
                            "fields": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific fields to return (reduces payload size)"
                            },
                            "chunk_size": {
                                "type": "integer",
                                "description": "Number of events per chunk (default: 500, max: 1000)"
                            },
                            "max_chunks": {
                                "type": "integer",
                                "description": "Maximum number of chunks to return (default: 20)"
                            },
                            "include_summary": {
                                "type": "boolean",
                                "description": "Include summary statistics with results (default: true)"
                            },
                            "stream_id": {
                                "type": "string",
                                "description": "Optional stream ID for resuming interrupted streams"
                            }
                        }
                    }
                },
                {
                    "name": "query_dshield_attacks",
                    "description": "Query DShield attack data specifically with pagination",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "time_range_hours": {
                                "type": "integer",
                                "description": "Time range in hours to query (default: 24)"
                            },
                            "page": {
                                "type": "integer",
                                "description": "Page number for pagination (default: 1)"
                            },
                            "page_size": {
                                "type": "integer",
                                "description": "Number of results per page (default: 100, max: 1000)"
                            },
                            "include_summary": {
                                "type": "boolean",
                                "description": "Include summary statistics with results (default: true)"
                            }
                        }
                    }
                },
                {
                    "name": "query_dshield_reputation",
                    "description": "Query DShield reputation data for IP addresses",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "ip_addresses": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "IP addresses to query reputation for"
                            },
                            "size": {
                                "type": "integer",
                                "description": "Maximum number of results (default: 1000)"
                            }
                        }
                    }
                },
                {
                    "name": "query_dshield_top_attackers",
                    "description": "Query DShield top attackers data",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "hours": {
                                "type": "integer",
                                "description": "Time range in hours (default: 24)"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "Maximum number of attackers to return (default: 100)"
                            }
                        }
                    }
                },
                {
                    "name": "query_dshield_geographic_data",
                    "description": "Query DShield geographic attack data",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "countries": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific countries to filter by"
                            },
                            "size": {
                                "type": "integer",
                                "description": "Maximum number of results (default: 1000)"
                            }
                        }
                    }
                },
                {
                    "name": "query_dshield_port_data",
                    "description": "Query DShield port attack data",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "ports": {
                                "type": "array",
                                "items": {"type": "integer"},
                                "description": "Specific ports to filter by"
                            },
                            "size": {
                                "type": "integer",
                                "description": "Maximum number of results (default: 1000)"
                            }
                        }
                    }
                },
                {
                    "name": "get_dshield_statistics",
                    "description": "Get comprehensive DShield statistics and summary",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "time_range_hours": {
                                "type": "integer",
                                "description": "Time range in hours (default: 24)"
                            }
                        }
                    }
                },
                {
                    "name": "enrich_ip_with_dshield",
                    "description": "Enrich IP address with DShield threat intelligence",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "ip_address": {
                                "type": "string",
                                "description": "IP address to enrich"
                            }
                        },
                        "required": ["ip_address"]
                    }
                },
                {
                    "name": "generate_attack_report",
                    "description": "Generate structured attack report with DShield data",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "events": {
                                "type": "array",
                                "description": "Security events to analyze"
                            },
                            "threat_intelligence": {
                                "type": "object",
                                "description": "Threat intelligence data"
                            }
                        }
                    }
                },
                {
                    "name": "query_events_by_ip",
                    "description": "Query DShield events for specific IP addresses",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "ip_addresses": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "IP addresses to query events for"
                            },
                            "time_range_hours": {
                                "type": "integer",
                                "description": "Time range in hours (default: 24)"
                            }
                        },
                        "required": ["ip_addresses"]
                    }
                },
                {
                    "name": "get_security_summary",
                    "description": "Get security summary with DShield enrichment",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "include_threat_intelligence": {
                                "type": "boolean",
                                "description": "Include threat intelligence enrichment (default: true)"
                            }
                        }
                    }
                },
                {
                    "name": "test_elasticsearch_connection",
                    "description": "Test connection to Elasticsearch and show available indices",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "get_data_dictionary",
                    "description": "Get comprehensive data dictionary for DShield SIEM fields and analysis guidelines",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "format": {
                                "type": "string",
                                "description": "Output format: 'prompt' for model prompt, 'json' for structured data (default: 'prompt')"
                            },
                            "sections": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Specific sections to include: 'fields', 'examples', 'patterns', 'guidelines' (default: all)"
                            }
                        }
                    }
                }
            ]
        
        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
            """Handle tool calls."""
            try:
                if name == "query_dshield_events":
                    return await self._query_dshield_events(arguments)
                elif name == "query_dshield_aggregations":
                    return await self._query_dshield_aggregations(arguments)
                elif name == "stream_dshield_events":
                    return await self._stream_dshield_events(arguments)
                elif name == "stream_dshield_events_with_session_context":
                    return await self._stream_dshield_events_with_session_context(arguments)
                elif name == "query_dshield_attacks":
                    return await self._query_dshield_attacks(arguments)
                elif name == "query_dshield_reputation":
                    return await self._query_dshield_reputation(arguments)
                elif name == "query_dshield_top_attackers":
                    return await self._query_dshield_top_attackers(arguments)
                elif name == "query_dshield_geographic_data":
                    return await self._query_dshield_geographic_data(arguments)
                elif name == "query_dshield_port_data":
                    return await self._query_dshield_port_data(arguments)
                elif name == "get_dshield_statistics":
                    return await self._get_dshield_statistics(arguments)
                elif name == "enrich_ip_with_dshield":
                    return await self._enrich_ip_with_dshield(arguments)
                elif name == "generate_attack_report":
                    return await self._generate_attack_report(arguments)
                elif name == "query_events_by_ip":
                    return await self._query_events_by_ip(arguments)
                elif name == "get_security_summary":
                    return await self._get_security_summary(arguments)
                elif name == "test_elasticsearch_connection":
                    return await self._test_elasticsearch_connection(arguments)
                elif name == "get_data_dictionary":
                    return await self._get_data_dictionary(arguments)
                else:
                    raise ValueError(f"Unknown tool: {name}")
            except Exception as e:
                logger.error("Tool call failed", tool=name, error=str(e))
                raise
        
        @self.server.list_resources()
        async def handle_list_resources() -> List[Dict[str, Any]]:
            """List available resources."""
            return [
                {
                    "uri": "dshield://events",
                    "name": "DShield Events",
                    "description": "Recent DShield events from Elasticsearch",
                    "mimeType": "application/json"
                },
                {
                    "uri": "dshield://attacks",
                    "name": "DShield Attacks",
                    "description": "Recent DShield attack data",
                    "mimeType": "application/json"
                },
                {
                    "uri": "dshield://top-attackers",
                    "name": "DShield Top Attackers",
                    "description": "DShield top attackers data",
                    "mimeType": "application/json"
                },
                {
                    "uri": "dshield://statistics",
                    "name": "DShield Statistics",
                    "description": "DShield statistics and summary data",
                    "mimeType": "application/json"
                },
                {
                    "uri": "dshield://threat-intelligence",
                    "name": "DShield Threat Intelligence",
                    "description": "DShield threat intelligence data",
                    "mimeType": "application/json"
                },
                {
                    "uri": "dshield://data-dictionary",
                    "name": "DShield Data Dictionary",
                    "description": "Comprehensive data dictionary for DShield SIEM fields and analysis guidelines",
                    "mimeType": "text/markdown"
                }
            ]
        
        @self.server.read_resource()
        async def handle_read_resource(uri: str) -> str:
            """Read resource content."""
            if uri == "dshield://events":
                events = await self._get_recent_dshield_events()
                return json.dumps(events, default=str)
            elif uri == "dshield://attacks":
                attacks = await self._get_recent_dshield_attacks()
                return json.dumps(attacks, default=str)
            elif uri == "dshield://top-attackers":
                attackers = await self._get_dshield_top_attackers()
                return json.dumps(attackers, default=str)
            elif uri == "dshield://statistics":
                stats = await self._get_dshield_stats()
                return json.dumps(stats, default=str)
            elif uri == "dshield://threat-intelligence":
                # Return cached threat intelligence
                return json.dumps({"message": "Use enrich_ip_with_dshield tool for specific IPs"})
            elif uri == "dshield://data-dictionary":
                # Return the data dictionary
                return DataDictionary.get_initial_prompt()
            else:
                raise ValueError(f"Unknown resource: {uri}")
    
    async def initialize(self):
        """Initialize the MCP server and clients."""
        logger.info("Initializing DShield MCP Server")
        
        # Initialize Elasticsearch client (but don't connect yet)
        self.elastic_client = ElasticsearchClient()
        
        # Initialize DShield client
        self.dshield_client = DShieldClient()
        
        # Initialize data processor
        self.data_processor = DataProcessor()
        
        # Initialize context injector
        self.context_injector = ContextInjector()
        
        logger.info("DShield MCP Server initialized successfully")
    
    async def _query_dshield_events(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query DShield events from Elasticsearch."""
        time_range_hours = arguments.get("time_range_hours", 24)
        time_range = arguments.get("time_range")
        relative_time = arguments.get("relative_time")
        time_window = arguments.get("time_window")
        indices = arguments.get("indices")
        filters = arguments.get("filters", {})
        fields = arguments.get("fields")
        page = arguments.get("page", 1)
        page_size = arguments.get("page_size", 100)
        sort_by = arguments.get("sort_by", "@timestamp")
        sort_order = arguments.get("sort_order", "desc")
        cursor = arguments.get("cursor")
        include_summary = arguments.get("include_summary", True)
        optimization = arguments.get("optimization", "auto")
        fallback_strategy = arguments.get("fallback_strategy", "aggregate")
        max_result_size_mb = arguments.get("max_result_size_mb", 10.0)
        query_timeout_seconds = arguments.get("query_timeout_seconds", 30)
        
        logger.info("Querying DShield events", 
                   time_range_hours=time_range_hours, 
                   indices=indices, 
                   fields=fields,
                   page=page, 
                   page_size=page_size, 
                   include_summary=include_summary,
                   optimization=optimization,
                   fallback_strategy=fallback_strategy,
                   max_result_size_mb=max_result_size_mb,
                   query_timeout_seconds=query_timeout_seconds)
        
        try:
            # Determine time range based on arguments
            if time_range:
                start_time = datetime.fromisoformat(time_range["start"])
                end_time = datetime.fromisoformat(time_range["end"])
            elif relative_time:
                time_delta = {"last_6_hours": timedelta(hours=6),
                              "last_24_hours": timedelta(hours=24),
                              "last_7_days": timedelta(days=7)}
                if relative_time in time_delta:
                    start_time = datetime.now() - time_delta[relative_time]
                    end_time = datetime.now()
                else:
                    raise ValueError(f"Unsupported relative_time: {relative_time}")
            elif time_window:
                center_time = datetime.fromisoformat(time_window["around"])
                window_minutes = time_window.get("window_minutes", 30)
                half_window = timedelta(minutes=window_minutes // 2)
                start_time = center_time - half_window
                end_time = center_time + half_window
            else:
                start_time = datetime.now() - timedelta(hours=time_range_hours)
                end_time = datetime.now()
            
            # Add time range to filters
            time_filters = {
                "@timestamp": {
                    "gte": start_time.isoformat(),
                    "lte": end_time.isoformat()
                }
            }
            
            # Merge time filters with existing filters
            if filters:
                filters.update(time_filters)
            else:
                filters = time_filters
            
            # Query events with pagination and field selection
            events, total_count, pagination_info = await self.elastic_client.query_dshield_events(
                time_range_hours=time_range_hours,
                indices=indices,
                filters=filters,
                fields=fields,
                page=page,
                page_size=page_size,
                sort_by=sort_by,
                sort_order=sort_order,
                cursor=cursor,
                include_summary=include_summary,
                optimization=optimization,
                fallback_strategy=fallback_strategy,
                max_result_size_mb=max_result_size_mb,
                query_timeout_seconds=query_timeout_seconds
            )
            
            if not events:
                return [{
                    "type": "text",
                    "text": f"No DShield events found for the specified criteria.\n\nQuery Parameters:\n- Time Range: {start_time.isoformat()} to {end_time.isoformat()}\n- Page: {page}\n- Page Size: {page_size}\n- Sort: {sort_by} {sort_order}\n- Fields: {fields or 'All'}\n- Filters: {filters}"
                }]
            
            # Format response with enhanced pagination info
            response_text = f"DShield Events (Page {pagination_info['page_number']} of {pagination_info['total_pages']}):\n\n"
            response_text += f"Total Events: {pagination_info['total_available']:,}\n"
            response_text += f"Events on this page: {len(events)}\n"
            response_text += f"Page Size: {pagination_info['page_size']}\n"
            response_text += f"Sort: {pagination_info['sort_by']} {pagination_info['sort_order']}\n\n"
            
            # Enhanced navigation information
            if pagination_info['has_previous'] or pagination_info['has_next']:
                response_text += "Navigation:\n"
                if pagination_info['has_previous']:
                    if 'previous_page' in pagination_info:
                        response_text += f"- Previous: page {pagination_info['previous_page']}\n"
                    if 'cursor' in pagination_info and not cursor:
                        response_text += f"- Previous cursor: {pagination_info['cursor']}\n"
                if pagination_info['has_next']:
                    if 'next_page' in pagination_info:
                        response_text += f"- Next: page {pagination_info['next_page']}\n"
                    if 'next_page_token' in pagination_info:
                        response_text += f"- Next cursor: {pagination_info['next_page_token']}\n"
                response_text += "\n"
            
            # Add pagination metadata for programmatic access
            response_text += f"Pagination Metadata:\n{json.dumps(pagination_info, indent=2)}\n\n"
            
            # Add events
            response_text += "Events:\n" + json.dumps(events, indent=2, default=str)
            
            return [{
                "type": "text",
                "text": response_text
            }]
        except Exception as e:
            logger.error("Failed to query DShield events", error=str(e))
            return [{
                "type": "text",
                "text": f"Error querying DShield events: {str(e)}\n\nPlease check your Elasticsearch configuration and ensure the server is running."
            }]
    
    async def _query_dshield_aggregations(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get aggregated summary data without full records."""
        time_range_hours = arguments.get("time_range_hours", 24)
        time_range = arguments.get("time_range")
        relative_time = arguments.get("relative_time")
        group_by = arguments.get("group_by", [])
        metrics = arguments.get("metrics", ["count"])
        filters = arguments.get("filters", {})
        top_n = arguments.get("top_n", 50)
        sort_by = arguments.get("sort_by", "count")
        sort_order = arguments.get("sort_order", "desc")

        logger.info("Querying DShield aggregations",
                   time_range_hours=time_range_hours,
                   group_by=group_by,
                   metrics=metrics,
                   top_n=top_n,
                   sort_by=sort_by,
                   sort_order=sort_order)

        try:
            # Determine time range based on arguments
            if time_range:
                start_time = datetime.fromisoformat(time_range["start"])
                end_time = datetime.fromisoformat(time_range["end"])
            elif relative_time:
                time_delta = {"last_6_hours": timedelta(hours=6),
                              "last_24_hours": timedelta(hours=24),
                              "last_7_days": timedelta(days=7)}
                if relative_time in time_delta:
                    start_time = datetime.now() - time_delta[relative_time]
                    end_time = datetime.now()
                else:
                    raise ValueError(f"Unsupported relative_time: {relative_time}")
            elif time_range_hours:
                start_time = datetime.now() - timedelta(hours=time_range_hours)
                end_time = datetime.now()
            else:
                raise ValueError("Time range not specified")

            # Add time range filters to the main query
            filters["@timestamp"] = {
                "gte": start_time.isoformat(),
                "lte": end_time.isoformat()
            }

            # Add filters from arguments
            for key, value in filters.items():
                if isinstance(value, dict):
                    # Handle nested filters (e.g., "source_ip": {"eq": "1.2.3.4"})
                    for sub_key, sub_value in value.items():
                        filters[f"{key}.{sub_key}"] = sub_value
                    del filters[key] # Remove original nested filter

            # Construct the aggregation query
            aggregation_query = {
                "size": 0, # We only want aggregation results, not documents
                "aggs": {
                    "group_by_agg": {
                        "terms": {
                            "field": group_by,
                            "size": top_n
                        },
                        "aggs": {
                            "metrics_agg": {
                                "sum": {"field": "bytes_sent"},
                                "avg": {"field": "duration"},
                                "count": {"value": 1}
                            }
                        }
                    }
                }
            }

            # Add sort if specified
            if sort_by:
                aggregation_query["aggs"]["group_by_agg"]["terms"]["order"] = {sort_by: {"order": sort_order}}

            # Execute the aggregation query
            aggregation_results = await self.elastic_client.execute_aggregation_query(
                index=indices,
                query=filters,
                aggregation_query=aggregation_query
            )

            # Process aggregation results
            processed_aggregations = {}
            for bucket in aggregation_results.get("aggregations", {}).get("group_by_agg", {}).get("buckets", []):
                key = bucket["key"]
                metrics_data = bucket["metrics_agg"]
                processed_aggregations[key] = {
                    "count": metrics_data.get("count", 0),
                    "sum_bytes_sent": metrics_data.get("sum_bytes_sent", 0),
                    "avg_duration": metrics_data.get("avg_duration", 0)
                }

            # Add summary information
            summary = {
                "total_count": aggregation_results.get("hits", {}).get("total", {}).get("value", 0),
                "total_bytes_sent": aggregation_results.get("aggregations", {}).get("group_by_agg", {}).get("sum_of_sum_bytes_sent", 0),
                "avg_duration": aggregation_results.get("aggregations", {}).get("group_by_agg", {}).get("avg_of_avg_duration", 0)
            }

            response_text = f"DShield Aggregated Statistics (Last {time_range_hours} hours):\n\n"
            response_text += f"- Total Events: {summary['total_count']}\n"
            response_text += f"- Total Bytes Sent: {summary['total_bytes_sent']}\n"
            response_text += f"- Average Duration: {summary['avg_duration']}\n\n"

            response_text += "Detailed Aggregations:\n" + json.dumps(processed_aggregations, indent=2, default=str)

            return [{
                "type": "text",
                "text": response_text
            }]
        except Exception as e:
            logger.error("Failed to query DShield aggregations", error=str(e))
            return [{
                "type": "text",
                "text": f"Error querying DShield aggregations: {str(e)}\n\nPlease check your Elasticsearch configuration and ensure the server is running."
            }]
    
    async def _stream_dshield_events(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Stream DShield events for very large datasets with chunked processing."""
        time_range_hours = arguments.get("time_range_hours", 24)
        time_range = arguments.get("time_range")
        relative_time = arguments.get("relative_time")
        indices = arguments.get("indices")
        filters = arguments.get("filters", {})
        fields = arguments.get("fields")
        chunk_size = arguments.get("chunk_size", 500)
        max_chunks = arguments.get("max_chunks", 20)
        include_summary = arguments.get("include_summary", True)
        stream_id = arguments.get("stream_id")

        logger.info("Streaming DShield events",
                   time_range_hours=time_range_hours,
                   indices=indices,
                   fields=fields,
                   chunk_size=chunk_size,
                   max_chunks=max_chunks,
                   include_summary=include_summary,
                   stream_id=stream_id)

        try:
            # Determine time range based on arguments
            if time_range:
                start_time = datetime.fromisoformat(time_range["start"])
                end_time = datetime.fromisoformat(time_range["end"])
            elif relative_time:
                time_delta = {"last_6_hours": timedelta(hours=6),
                              "last_24_hours": timedelta(hours=24),
                              "last_7_days": timedelta(days=7)}
                if relative_time in time_delta:
                    start_time = datetime.now() - time_delta[relative_time]
                    end_time = datetime.now()
                else:
                    raise ValueError(f"Unsupported relative_time: {relative_time}")
            else:
                start_time = datetime.now() - timedelta(hours=time_range_hours)
                end_time = datetime.now()

            # Add time range to filters
            time_filters = {
                "@timestamp": {
                    "gte": start_time.isoformat(),
                    "lte": end_time.isoformat()
                }
            }
            if filters:
                filters.update(time_filters)
            else:
                filters = time_filters

            # Initialize stream state
            stream_state = {
                "current_chunk_index": 0,
                "total_events_processed": 0,
                "last_event_id": None
            }

            # Collect all chunks into a single response
            all_chunks = []
            current_stream_id = stream_id

            # Fetch events in chunks
            for chunk_index in range(max_chunks):
                logger.info(f"Fetching chunk {chunk_index + 1}/{max_chunks}",
                           start_time=start_time.isoformat(),
                           end_time=end_time.isoformat(),
                           chunk_size=chunk_size,
                           stream_id=current_stream_id)

                events, total_count, last_event_id = await self.elastic_client.stream_dshield_events(
                    time_range_hours=time_range_hours,
                    indices=indices,
                    filters=filters,
                    fields=fields,
                    chunk_size=chunk_size,
                    stream_id=current_stream_id
                )

                if not events:
                    logger.info(f"No more events in chunk {chunk_index + 1}. Ending stream.")
                    break

                # Update stream state
                stream_state["current_chunk_index"] = chunk_index + 1
                stream_state["total_events_processed"] += len(events)
                stream_state["last_event_id"] = last_event_id

                # Create chunk summary
                chunk_summary = {
                    "chunk_index": chunk_index + 1,
                    "events_count": len(events),
                    "total_count": total_count,
                    "stream_id": last_event_id,
                    "events": events
                }

                all_chunks.append(chunk_summary)

                # Update stream_id for next chunk
                current_stream_id = last_event_id

                # If we've reached the end, break
                if not last_event_id:
                    break

            # Create comprehensive response
            response_text = f"DShield Event Streaming Results:\n\n"
            response_text += f"Time Range: {start_time.isoformat()} to {end_time.isoformat()}\n"
            response_text += f"Total Chunks Processed: {stream_state['current_chunk_index']}\n"
            response_text += f"Total Events Processed: {stream_state['total_events_processed']}\n"
            response_text += f"Chunk Size: {chunk_size}\n"
            response_text += f"Max Chunks: {max_chunks}\n"
            response_text += f"Final Stream ID: {stream_state['last_event_id']}\n\n"

            if include_summary:
                response_text += "Stream Summary:\n"
                response_text += f"- Chunks returned: {len(all_chunks)}\n"
                response_text += f"- Events per chunk: {[chunk['events_count'] for chunk in all_chunks]}\n"
                response_text += f"- Stream IDs: {[chunk['stream_id'] for chunk in all_chunks if chunk['stream_id']]}\n\n"

            response_text += "Chunk Details:\n" + json.dumps(all_chunks, indent=2, default=str)

            return [{
                "type": "text",
                "text": response_text
            }]

        except Exception as e:
            logger.error("Failed to stream DShield events", error=str(e))
            return [{
                "type": "text",
                "text": f"Error streaming DShield events: {str(e)}\n\nPlease check your Elasticsearch configuration and ensure the server is running."
            }]
    
    async def _stream_dshield_events_with_session_context(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Stream DShield events with smart session-based chunking."""
        time_range_hours = arguments.get("time_range_hours", 24)
        indices = arguments.get("indices")
        filters = arguments.get("filters", {})
        fields = arguments.get("fields")
        chunk_size = arguments.get("chunk_size", 500)
        session_fields = arguments.get("session_fields")
        max_session_gap_minutes = arguments.get("max_session_gap_minutes", 30)
        include_session_summary = arguments.get("include_session_summary", True)
        stream_id = arguments.get("stream_id")
        
        logger.info("Streaming DShield events with session context", 
                   time_range_hours=time_range_hours, 
                   indices=indices, 
                   fields=fields,
                   chunk_size=chunk_size,
                   session_fields=session_fields,
                   max_session_gap_minutes=max_session_gap_minutes,
                   include_session_summary=include_session_summary,
                   stream_id=stream_id)
        
        try:
            # Stream events with session context
            events, total_count, next_stream_id, session_context = await self.elastic_client.stream_dshield_events_with_session_context(
                time_range_hours=time_range_hours,
                indices=indices,
                filters=filters,
                fields=fields,
                chunk_size=chunk_size,
                session_fields=session_fields,
                max_session_gap_minutes=max_session_gap_minutes,
                include_session_summary=include_session_summary,
                stream_id=stream_id
            )
            
            # Format response with session context
            response = {
                "events": events,
                "total_count": total_count,
                "next_stream_id": next_stream_id,
                "session_context": session_context
            }
            
            return [{"type": "text", "text": json.dumps(response, default=str, indent=2)}]
            
        except Exception as e:
            logger.error("Session context streaming failed", error=str(e))
            raise
    
    async def _query_dshield_attacks(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query DShield attack data specifically."""
        time_range_hours = arguments.get("time_range_hours", 24)
        page = arguments.get("page", 1)
        page_size = arguments.get("page_size", 100)
        include_summary = arguments.get("include_summary", True)
        
        logger.info("Querying DShield attacks", 
                   time_range_hours=time_range_hours, 
                   page=page, 
                   page_size=page_size, 
                   include_summary=include_summary)
        
        try:
            attacks, total_count = await self.elastic_client.query_dshield_attacks(
                time_range_hours=time_range_hours,
                page=page,
                page_size=page_size,
                include_summary=include_summary
            )
            
            # Generate pagination info
            pagination_info = self.elastic_client._generate_pagination_info(page, page_size, total_count)
            
            response_text = f"Found {total_count} DShield attacks in the last {time_range_hours} hours.\n"
            response_text += f"Showing page {page} of {pagination_info['total_pages']} (results {pagination_info['start_index']}-{pagination_info['end_index']}).\n\n"
            
            if include_summary and attacks:
                # Add summary information
                summary = self.data_processor.generate_security_summary(attacks)
                response_text += f"Page Summary:\n"
                response_text += f"- Attacks on this page: {len(attacks)}\n"
                response_text += f"- High risk attacks: {summary.get('high_risk_events', 0)}\n"
                response_text += f"- Unique attacker IPs: {len(summary.get('unique_source_ips', []))}\n"
                response_text += f"- Attack patterns: {list(summary.get('attack_patterns', {}).keys())}\n\n"
            
            response_text += "Attack Details:\n" + json.dumps(attacks, indent=2, default=str)
            
            # Add pagination info to response
            if pagination_info['has_next'] or pagination_info['has_previous']:
                response_text += f"\n\nPagination Info:\n" + json.dumps(pagination_info, indent=2)
            
            return [{
                "type": "text",
                "text": response_text
            }]
        except Exception as e:
            logger.error("Failed to query DShield attacks", error=str(e))
            return [{
                "type": "text",
                "text": f"Error querying DShield attacks: {str(e)}\n\nPlease check your Elasticsearch configuration and ensure the server is running."
            }]
    
    async def _query_dshield_reputation(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query DShield reputation data."""
        ip_addresses = arguments.get("ip_addresses", [])
        size = arguments.get("size", 1000)
        
        logger.info("Querying DShield reputation data", 
                   ip_addresses=ip_addresses, 
                   size=size)
        
        reputation_data = await self.elastic_client.query_dshield_reputation(
            ip_addresses=ip_addresses if ip_addresses else None,
            size=size
        )
        
        return [{
            "type": "text",
            "text": f"Found {len(reputation_data)} DShield reputation records:\n\n" + 
                   json.dumps(reputation_data, indent=2, default=str)
        }]
    
    async def _query_dshield_top_attackers(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query DShield top attackers data."""
        hours = arguments.get("hours", 24)
        limit = arguments.get("limit", 100)
        
        logger.info("Querying DShield top attackers", 
                   hours=hours, 
                   limit=limit)
        
        attackers = await self.elastic_client.query_dshield_top_attackers(
            hours=hours,
            limit=limit
        )
        
        return [{
            "type": "text",
            "text": f"Found {len(attackers)} top DShield attackers in the last {hours} hours:\n\n" + 
                   json.dumps(attackers, indent=2, default=str)
        }]
    
    async def _query_dshield_geographic_data(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query DShield geographic data."""
        countries = arguments.get("countries")
        size = arguments.get("size", 1000)
        
        logger.info("Querying DShield geographic data", 
                   countries=countries, 
                   size=size)
        
        geo_data = await self.elastic_client.query_dshield_geographic_data(
            countries=countries,
            size=size
        )
        
        return [{
            "type": "text",
            "text": f"Found {len(geo_data)} DShield geographic records:\n\n" + 
                   json.dumps(geo_data, indent=2, default=str)
        }]
    
    async def _query_dshield_port_data(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query DShield port data."""
        ports = arguments.get("ports")
        size = arguments.get("size", 1000)
        
        logger.info("Querying DShield port data", 
                   ports=ports, 
                   size=size)
        
        port_data = await self.elastic_client.query_dshield_port_data(
            ports=ports,
            size=size
        )
        
        return [{
            "type": "text",
            "text": f"Found {len(port_data)} DShield port records:\n\n" + 
                   json.dumps(port_data, indent=2, default=str)
        }]
    
    async def _get_dshield_statistics(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get DShield statistics and summary."""
        time_range_hours = arguments.get("time_range_hours", 24)
        
        logger.info("Getting DShield statistics", time_range_hours=time_range_hours)
        
        stats = await self.elastic_client.get_dshield_statistics(
            time_range_hours=time_range_hours
        )
        
        return [{
            "type": "text",
            "text": f"DShield Statistics (Last {time_range_hours} hours):\n\n" + 
                   json.dumps(stats, indent=2, default=str)
        }]
    
    async def _enrich_ip_with_dshield(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Enrich IP address with DShield threat intelligence."""
        ip_address = arguments["ip_address"]
        
        logger.info("Enriching IP with DShield", ip_address=ip_address)
        
        threat_data = await self.dshield_client.get_ip_reputation(ip_address)
        
        return [{
            "type": "text",
            "text": f"DShield threat intelligence for {ip_address}:\n\n" + 
                   json.dumps(threat_data, indent=2, default=str)
        }]
    
    async def _generate_attack_report(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate structured attack report."""
        events = arguments.get("events", [])
        threat_intelligence = arguments.get("threat_intelligence", {})
        
        logger.info("Generating attack report", event_count=len(events))
        
        report = self.data_processor.generate_attack_report(events, threat_intelligence)
        
        return [{
            "type": "text",
            "text": "Attack Report:\n\n" + json.dumps(report, indent=2, default=str)
        }]
    
    async def _query_events_by_ip(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query events for specific IP addresses."""
        ip_addresses = arguments["ip_addresses"]
        time_range_hours = arguments.get("time_range_hours", 24)
        
        logger.info("Querying events by IP", 
                   ip_addresses=ip_addresses, 
                   time_range_hours=time_range_hours)
        
        events = await self.elastic_client.query_events_by_ip(
            ip_addresses=ip_addresses,
            time_range_hours=time_range_hours
        )
        
        processed_events = self.data_processor.process_security_events(events)
        
        return [{
            "type": "text",
            "text": f"Events for IPs {ip_addresses} in the last {time_range_hours} hours:\n\n" + 
                   json.dumps(processed_events, indent=2, default=str)
        }]
    
    async def _get_security_summary(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get security summary for the last 24 hours."""
        include_threat_intelligence = arguments.get("include_threat_intelligence", True)
        
        logger.info("Getting security summary")
        
        # Get recent events
        events = await self.elastic_client.query_dshield_events(time_range_hours=24)
        
        # Process and summarize
        summary = self.data_processor.generate_security_summary(events)
        
        if include_threat_intelligence:
            # Extract unique IPs and enrich them
            unique_ips = self.data_processor.extract_unique_ips(events)
            threat_data = {}
            
            for ip in unique_ips[:10]:  # Limit to first 10 IPs
                try:
                    threat_data[ip] = await self.dshield_client.get_ip_reputation(ip)
                except Exception as e:
                    logger.warning("Failed to enrich IP", ip=ip, error=str(e))
            
            summary["threat_intelligence"] = threat_data
        
        return [{
            "type": "text",
            "text": "Security Summary (Last 24 Hours):\n\n" + 
                   json.dumps(summary, indent=2, default=str)
        }]
    
    async def _test_elasticsearch_connection(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Test Elasticsearch connection and show available indices."""
        try:
            # Try to connect
            await self.elastic_client.connect()
            
            # Get cluster info
            info = await self.elastic_client.client.info()
            
            # Get available indices
            indices = await self.elastic_client.get_available_indices()
            
            # Get cluster health
            health = await self.elastic_client.client.cluster.health()
            
            result = {
                "connection_status": "success",
                "cluster_info": {
                    "cluster_name": info.get('cluster_name'),
                    "version": info.get('version', {}).get('number'),
                    "status": health.get('status')
                },
                "available_dshield_indices": indices,
                "total_indices": len(indices)
            }
            
            return [{
                "type": "text",
                "text": f"✅ Elasticsearch connection successful!\n\n" + 
                       json.dumps(result, indent=2, default=str)
            }]
            
        except Exception as e:
            logger.error("Elasticsearch connection test failed", error=str(e))
            return [{
                "type": "text",
                "text": f"❌ Elasticsearch connection failed: {str(e)}\n\n" +
                       "Please check:\n" +
                       "1. Elasticsearch is running\n" +
                       "2. The URL in mcp_config.yaml is correct\n" +
                       "3. Network connectivity to the Elasticsearch server\n" +
                       "4. Authentication credentials if required"
            }]
    
    async def _get_data_dictionary(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get comprehensive data dictionary for DShield SIEM fields and analysis guidelines."""
        format_type = arguments.get("format", "prompt")
        sections = arguments.get("sections", ["fields", "examples", "patterns", "guidelines"])
        
        logger.info("Getting data dictionary", format=format_type, sections=sections)
        
        if format_type == "prompt":
            # Return the formatted prompt
            prompt = DataDictionary.get_initial_prompt()
            return [{
                "type": "text",
                "text": prompt
            }]
        else:
            # Return structured JSON data
            data = {}
            
            if "fields" in sections:
                data["field_descriptions"] = DataDictionary.get_field_descriptions()
            
            if "examples" in sections:
                data["query_examples"] = DataDictionary.get_query_examples()
            
            if "patterns" in sections:
                data["data_patterns"] = DataDictionary.get_data_patterns()
            
            if "guidelines" in sections:
                data["analysis_guidelines"] = DataDictionary.get_analysis_guidelines()
            
            return [{
                "type": "text",
                "text": json.dumps(data, indent=2, default=str)
            }]
    
    async def _get_recent_dshield_events(self) -> List[Dict[str, Any]]:
        """Get recent DShield events for resource reading."""
        events = await self.elastic_client.query_dshield_events(time_range_hours=1)
        return self.data_processor.process_security_events(events)
    
    async def _get_recent_dshield_attacks(self) -> List[Dict[str, Any]]:
        """Get recent DShield attacks for resource reading."""
        return await self.elastic_client.query_dshield_attacks(time_range_hours=1)
    
    async def _get_dshield_top_attackers(self) -> List[Dict[str, Any]]:
        """Get DShield top attackers for resource reading."""
        return await self.elastic_client.query_dshield_top_attackers(hours=24)
    
    async def _get_dshield_stats(self) -> Dict[str, Any]:
        """Get DShield statistics for resource reading."""
        return await self.elastic_client.get_dshield_statistics(time_range_hours=24)
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.elastic_client:
            await self.elastic_client.close()
        logger.info("DShield MCP Server cleanup completed")


async def main():
    """Main entry point for the DShield MCP server."""
    server = DShieldMCPServer()
    
    try:
        await server.initialize()
        
        # Run the server
        async with stdio_server() as (read_stream, write_stream):
            await server.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="dshield-elastic-mcp",
                    server_version="1.0.0",
                    capabilities=server.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={
                            "dshield_data_dictionary": {
                                "description": "DShield SIEM data dictionary and analysis guidelines",
                                "prompt": DataDictionary.get_initial_prompt()
                            }
                        }
                    )
                )
            )
    
    except Exception as e:
        logger.error("Server error", error=str(e))
        raise
    finally:
        await server.cleanup()


if __name__ == "__main__":
    asyncio.run(main()) 