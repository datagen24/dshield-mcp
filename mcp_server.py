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
                    "description": "Query DShield events from Elasticsearch SIEM",
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
                                "description": "DShield Elasticsearch indices to query"
                            },
                            "filters": {
                                "type": "object",
                                "description": "Additional query filters"
                            }
                        }
                    }
                },
                {
                    "name": "query_dshield_attacks",
                    "description": "Query DShield attack data specifically",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "time_range_hours": {
                                "type": "integer",
                                "description": "Time range in hours to query (default: 24)"
                            },
                            "size": {
                                "type": "integer",
                                "description": "Maximum number of results (default: 1000)"
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
        indices = arguments.get("indices")
        filters = arguments.get("filters", {})
        
        logger.info("Querying DShield events", 
                   time_range_hours=time_range_hours, 
                   indices=indices)
        
        try:
            events = await self.elastic_client.query_dshield_events(
                time_range_hours=time_range_hours,
                indices=indices,
                filters=filters
            )
            
            processed_events = self.data_processor.process_security_events(events)
            
            return [{
                "type": "text",
                "text": f"Found {len(processed_events)} DShield events in the last {time_range_hours} hours:\n\n" + 
                       json.dumps(processed_events, indent=2, default=str)
            }]
        except Exception as e:
            logger.error("Failed to query DShield events", error=str(e))
            return [{
                "type": "text",
                "text": f"Error querying DShield events: {str(e)}\n\nPlease check your Elasticsearch configuration and ensure the server is running."
            }]
    
    async def _query_dshield_attacks(self, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Query DShield attack data specifically."""
        time_range_hours = arguments.get("time_range_hours", 24)
        size = arguments.get("size", 1000)
        
        logger.info("Querying DShield attacks", 
                   time_range_hours=time_range_hours, 
                   size=size)
        
        attacks = await self.elastic_client.query_dshield_attacks(
            time_range_hours=time_range_hours,
            size=size
        )
        
        return [{
            "type": "text",
            "text": f"Found {len(attacks)} DShield attacks in the last {time_range_hours} hours:\n\n" + 
                   json.dumps(attacks, indent=2, default=str)
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