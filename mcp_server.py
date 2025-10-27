#!/usr/bin/env python3
"""DShield MCP Server - Elastic SIEM Integration.

Main server for handling MCP protocol communication and coordinating
between DShield Elasticsearch queries and DShield threat intelligence.
"""
# type: ignore[operator,assignment,union-attr,arg-type,index]

import asyncio
import json
import sys
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog

from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import Tool  # Fixed import for Tool
from src.campaign_analyzer import CampaignAnalyzer
from src.campaign_mcp_tools import CampaignMCPTools
from src.context_injector import ContextInjector
from src.data_dictionary import DataDictionary
from src.data_processor import DataProcessor
from src.dshield_client import DShieldClient
from src.dynamic_tool_registry import DynamicToolRegistry
from src.elasticsearch_client import ElasticsearchClient
from src.feature_manager import FeatureManager
from src.health_check_manager import HealthCheckManager
from src.latex_template_tools import LaTeXTemplateTools
from src.mcp_tools.tools.dispatcher import ToolDispatcher
from src.mcp_tools.tools.loader import ToolLoader
from src.mcp_error_handler import ErrorHandlingConfig, MCPErrorHandler
from src.operation_tracker import OperationTracker
from src.resource_manager import ResourceManager
from src.signal_handler import SignalHandler
from src.statistical_analysis_tools import StatisticalAnalysisTools
from src.threat_intelligence_manager import ThreatIntelligenceManager
from src.user_config import UserConfigManager, get_user_config

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
        structlog.processors.JSONRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


class DShieldMCPServer:
    """Main MCP server for DShield Elastic SIEM integration.

    This class provides the core MCP (Model Context Protocol) server implementation
    for integrating with DShield Elasticsearch SIEM and threat intelligence data.
    It handles tool registration, request processing, and coordination between
    various DShield data sources.

    Attributes:
        server: The MCP server instance
        elastic_client: Client for Elasticsearch operations
        dshield_client: Client for DShield API operations
        data_processor: Utility for processing security data
        context_injector: Utility for injecting context into queries
        campaign_analyzer: Campaign analysis functionality
        campaign_tools: Campaign-related MCP tools
        user_config: User configuration settings

    Example:
        >>> server = DShieldMCPServer()
        >>> await server.initialize()
        >>> # Server is ready to handle MCP requests

    """

    def __init__(self) -> None:
        """Initialize the DShield MCP server.

        Sets up the server instance, initializes client references,
        loads user configuration, and registers available MCP tools.
        """
        self.server = Server("dshield-elastic-mcp")
        self.elastic_client: ElasticsearchClient | None = None
        self.dshield_client: DShieldClient | None = None
        self.data_processor: DataProcessor | None = None
        self.context_injector: ContextInjector | None = None
        self.campaign_analyzer: CampaignAnalyzer | None = None
        self.campaign_tools: CampaignMCPTools | None = None
        self.latex_tools: LaTeXTemplateTools | None = None
        self.threat_intelligence_manager: ThreatIntelligenceManager | None = None
        self.user_config: UserConfigManager | None = None
        self.health_manager = HealthCheckManager()
        self.feature_manager = FeatureManager(self.health_manager)
        self.tool_registry = DynamicToolRegistry(self.feature_manager)
        
        # Initialize tool loader and dispatcher
        from pathlib import Path
        tools_directory = Path(__file__).parent / "src" / "mcp_tools" / "tools"
        self.tool_loader = ToolLoader(tools_directory)
        self.tool_dispatcher = ToolDispatcher(self.tool_loader)

        # Load user configuration
        try:
            self.user_config = get_user_config()
        except Exception as e:
            logger.error("Failed to load user config", error=str(e))
            self.user_config = None

        # Initialize error handler with configuration
        try:
            error_config = ErrorHandlingConfig()
            if self.user_config:
                # Load error handling settings from user config if available
                try:
                    # Try to get performance settings as fallback for timeouts
                    performance_settings = self.user_config.get_setting(
                        "performance", "default_timeout_seconds"
                    )
                    error_config.timeouts.update(
                        {
                            "elasticsearch_operations": performance_settings,
                            "dshield_api_calls": performance_settings,
                            "latex_compilation": performance_settings,
                            "tool_execution": performance_settings,
                        }
                    )
                except (ValueError, KeyError):
                    # Use default values if settings are not available
                    pass
            self.error_handler = MCPErrorHandler(error_config)
        except Exception as e:
            logger.warning("Failed to initialize error handler, using defaults", error=str(e))
            self.error_handler = MCPErrorHandler()

        # Register tools
        self._register_tools()

        self.signal_handler = SignalHandler(self)
        self.resource_manager = ResourceManager()
        self.operation_tracker = OperationTracker()

    def _register_tools(self) -> None:
        """Register all available MCP tools.

        This method sets up the MCP server's tool handlers, including:
        - Tool listing functionality
        - Tool execution handlers
        - Resource listing and reading capabilities

        The tools provide access to DShield data including:
        - Event queries with pagination
        - Streaming data with session context
        - Aggregation queries
        - Campaign analysis
        - Threat intelligence enrichment
        - Data dictionary access
        """
        # Load all tools from individual files
        self.tool_loader.load_all_tools()
        
        # Register tool handlers
        self._register_tool_handlers()
        
        # Register MCP handlers
        self._register_mcp_handlers()

    def _register_mcp_handlers(self) -> None:
        """Register MCP protocol handlers."""
        @self.server.list_tools()  # type: ignore[misc,no-untyped-call]
        async def handle_list_tools() -> list[Tool]:
            """List all available tools based on feature availability."""
            return await self._handle_list_tools()

        @self.server.call_tool()  # type: ignore[misc]
        async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
            """Handle tool calls using the dispatcher."""
            return await self._handle_call_tool(name, arguments)

        @self.server.list_resources()  # type: ignore[misc,no-untyped-call]
        async def handle_list_resources() -> list[dict[str, Any]]:
            """List available resources."""
            return [
                {
                    "uri": "dshield://events",
                    "name": "DShield Events",
                    "description": "Recent DShield events from Elasticsearch",
                    "mimeType": "application/json",
                },
                {
                    "uri": "dshield://attacks",
                    "name": "DShield Attacks",
                    "description": "Recent DShield attack data",
                    "mimeType": "application/json",
                },
                {
                    "uri": "dshield://top-attackers",
                    "name": "DShield Top Attackers",
                    "description": "DShield top attackers data",
                    "mimeType": "application/json",
                },
                {
                    "uri": "dshield://statistics",
                    "name": "DShield Statistics",
                    "description": "DShield statistics and summary data",
                    "mimeType": "application/json",
                },
                {
                    "uri": "dshield://threat-intelligence",
                    "name": "DShield Threat Intelligence",
                    "description": "DShield threat intelligence data",
                    "mimeType": "application/json",
                },
                {
                    "uri": "dshield://data-dictionary",
                    "name": "DShield Data Dictionary",
                    "description": "Comprehensive data dictionary for DShield SIEM fields and "
                    "analysis guidelines",
                    "mimeType": "text/markdown",
                },
            ]

        @self.server.read_resource()  # type: ignore[misc,no-untyped-call]
        async def handle_read_resource(uri: str) -> str:
            """Read resource content."""
            try:
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
                    return json.dumps(
                        {"message": "Use enrich_ip_with_dshield tool for specific IPs"}
                    )
                elif uri == "dshield://data-dictionary":
                    # Return the data dictionary
                    return DataDictionary.get_initial_prompt()
                else:
                    logger.error("Unknown resource requested", uri=uri)
                    error_response = self.error_handler.create_resource_error(
                        uri, "not_found", f"Resource '{uri}' not found"
                    )
                    return json.dumps(error_response)
            except Exception as e:
                logger.error("Resource reading failed", uri=uri, error=str(e))
                error_response = self.error_handler.create_resource_error(
                    uri, "unavailable", f"Failed to read resource '{uri}': {e!s}"
                )
                return json.dumps(error_response)

    def _register_tool_handlers(self) -> None:
        """Register tool handlers with the dispatcher.

        This method registers all the tool handlers with the dispatcher,
        mapping tool names to their corresponding handler methods.
        """
        # Register individual tool handlers for methods that exist
        self.tool_dispatcher.register_handler("query_dshield_events", self._query_dshield_events)
        self.tool_dispatcher.register_handler(
            "stream_dshield_events_with_session_context",
            self._stream_dshield_events_with_session_context
        )
        self.tool_dispatcher.register_handler("get_data_dictionary", self._get_data_dictionary)
        self.tool_dispatcher.register_handler("get_health_status", self._get_health_status)
        self.tool_dispatcher.register_handler(
            "detect_statistical_anomalies", self._detect_statistical_anomalies
        )
        self.tool_dispatcher.register_handler("analyze_campaign", self._analyze_campaign)
        self.tool_dispatcher.register_handler(
            "expand_campaign_indicators", self._expand_campaign_indicators
        )
        self.tool_dispatcher.register_handler("get_campaign_timeline", self._get_campaign_timeline)
        self.tool_dispatcher.register_handler(
            "enrich_ip_with_dshield", self._enrich_ip_with_dshield
        )
        self.tool_dispatcher.register_handler(
            "generate_attack_report", self._generate_attack_report
        )

        logger.info("Registered tool handlers with dispatcher")

    async def _handle_list_tools(self) -> list[Tool]:
        """Handle list tools request."""
        # Get available features
        available_features = self.feature_manager.get_available_features()
        
        # Get available tools from the tool loader
        available_tool_definitions = self.tool_dispatcher.get_available_tools(
            available_features
        )
        
        # Convert to MCP Tool objects
        available_tools = []
        for tool_def in available_tool_definitions:
            available_tools.append(
                Tool(
                    name=tool_def.name,
                    description=tool_def.description,
                    inputSchema=tool_def.schema,
                )
            )

        logger.info(
            "Listed available tools",
            available_count=len(available_tools),
            total_loaded=len(self.tool_loader.get_all_tool_definitions()),
        )

        return available_tools

    async def _handle_call_tool(self, name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Handle tool call request."""
        if not self.tool_dispatcher.is_tool_available(
            name, self.feature_manager.get_available_features()
        ):
            return await self._tool_unavailable_response(name)
        
        try:
            # Use the dispatcher to handle the tool call
            result = await self.tool_dispatcher.dispatch_tool_call(
                name, 
                arguments,
                timeout=self.error_handler.config.timeouts.get("tool_execution", 120.0)
            )
            return result
        except TimeoutError:
            logger.error("Tool call timed out", tool=name)
            return [self.error_handler.create_timeout_error(name, 30.0)]
        except ValueError as e:
            logger.error("Tool call validation error", tool=name, error=str(e))
            # Convert ValueError to ValidationError for proper error handling
            from pydantic import ValidationError

            # Create a simple ValidationError for ValueError
            validation_error = ValidationError(
                [{"type": "value_error", "loc": (), "msg": str(e), "input": None}], ValueError
            )
            return [self.error_handler.create_validation_error(name, validation_error)]
        except Exception as e:
            logger.error("Tool call failed", tool=name, error=str(e))
            return [self.error_handler.create_internal_error(f"Tool call failed: {e!s}")]

    async def initialize(self) -> None:
        """Initialize the MCP server and clients with graceful degradation."""
        logger.info(
            "Initializing DShield MCP Server with comprehensive health checks and feature flags"
        )

        try:
            # Run comprehensive health checks
            health_results = await self.health_manager.run_all_checks()
            logger.info(
                "Health checks completed",
                health_summary=health_results.get("summary", {}),
                healthy_services=health_results.get("summary", {}).get("healthy_services", []),
                unhealthy_services=health_results.get("summary", {}).get("unhealthy_services", []),
            )

            # Initialize features based on health status
            await self.feature_manager.initialize_features()
            feature_summary = self.feature_manager.get_feature_summary()
            logger.info("Feature initialization completed", feature_summary=feature_summary)

            # Define all available tools
            all_tools = [
                'query_dshield_events',
                'query_dshield_aggregations',
                'stream_dshield_events',
                'stream_dshield_events_with_session_context',
                'query_dshield_attacks',
                'query_dshield_reputation',
                'query_dshield_top_attackers',
                'query_dshield_geographic_data',
                'query_dshield_port_data',
                'get_dshield_statistics',
                'diagnose_data_availability',
                'enrich_ip_with_dshield',
                'generate_attack_report',
                'query_events_by_ip',
                'get_security_summary',
                'test_elasticsearch_connection',
                'get_data_dictionary',
                'analyze_campaign',
                'expand_campaign_indicators',
                'get_campaign_timeline',
                'compare_campaigns',
                'detect_ongoing_campaigns',
                'search_campaigns',
                'get_campaign_details',
                'generate_latex_document',
                'list_latex_templates',
                'get_latex_template_schema',
                'validate_latex_document_data',
                'enrich_ip_comprehensive',
                'enrich_domain_comprehensive',
                'correlate_threat_indicators',
                'get_threat_intelligence_summary',
                'detect_statistical_anomalies',
            ]

            # Register available tools based on feature availability
            self.available_tools = self.tool_registry.register_tools(all_tools)
            tool_summary = self.tool_registry.get_tool_summary()
            logger.info("Tool registration completed", tool_summary=tool_summary)

            # Initialize clients with graceful degradation
            await self._initialize_clients_gracefully()

            # Log comprehensive initialization summary
            logger.info(
                "DShield MCP Server initialization completed successfully",
                health_status=health_results.get("summary", {}).get("overall_health", 0),
                feature_status=feature_summary.get("status", "unknown"),
                tool_availability=tool_summary.get("availability_percentage", 0),
                available_tools_count=len(self.available_tools),
                total_tools_count=len(all_tools),
            )

            # Log user configuration summary if available
            if self.user_config:
                logger.info(
                    "User configuration loaded",
                    user_config_summary={
                        "query_settings": {
                            "default_page_size": self.user_config.get_setting(
                                "query", "default_page_size"
                            ),
                            "enable_smart_optimization": self.user_config.get_setting(
                                "query", "enable_smart_optimization"
                            ),
                            "fallback_strategy": self.user_config.get_setting(
                                "query", "fallback_strategy"
                            ),
                        },
                        "performance_settings": {
                            "enable_caching": self.user_config.get_setting(
                                "performance", "enable_caching"
                            ),
                            "enable_connection_pooling": self.user_config.get_setting(
                                "performance", "enable_connection_pooling"
                            ),
                        },
                        "security_settings": {
                            "rate_limit": self.user_config.get_setting(
                                "security", "rate_limit_requests_per_minute"
                            ),
                            "max_query_results": self.user_config.get_setting(
                                "security", "max_query_results"
                            ),
                        },
                    },
                )

        except Exception as e:
            logger.error("Server initialization failed", error=str(e))
            # Continue with minimal functionality - don't crash the server
            logger.warning("Continuing with minimal functionality due to initialization failure")

            # Set all tools as unavailable
            self.available_tools = []

            # Initialize minimal clients
            await self._initialize_clients_gracefully()

    async def _initialize_clients_gracefully(self) -> None:
        """Initialize clients with graceful degradation for unavailable dependencies."""
        try:
            # Initialize Elasticsearch client only if the feature is available
            if self.feature_manager.is_feature_available('elasticsearch_queries'):
                try:
                    self.elastic_client = ElasticsearchClient()
                    logger.info("Elasticsearch client initialized successfully")
                except Exception as e:
                    logger.error("Failed to initialize Elasticsearch client", error=str(e))
                    self.elastic_client = None
            else:
                logger.warning("Elasticsearch client not initialized - feature unavailable")
                self.elastic_client = None

            # Initialize DShield client only if the feature is available
            if self.feature_manager.is_feature_available('dshield_enrichment'):
                try:
                    self.dshield_client = DShieldClient()
                    logger.info("DShield client initialized successfully")
                except Exception as e:
                    logger.error("Failed to initialize DShield client", error=str(e))
                    self.dshield_client = None
            else:
                logger.warning("DShield client not initialized - feature unavailable")
                self.dshield_client = None

            # Initialize data processor (no external dependencies)
            try:
                self.data_processor = DataProcessor()
                logger.info("Data processor initialized successfully")
            except Exception as e:
                logger.error("Failed to initialize data processor", error=str(e))
                self.data_processor = None

            # Initialize context injector (no external dependencies)
            try:
                self.context_injector = ContextInjector()
                logger.info("Context injector initialized successfully")
            except Exception as e:
                logger.error("Failed to initialize context injector", error=str(e))
                self.context_injector = None

            # Initialize campaign analyzer and tools only if Elasticsearch is available
            if self.elastic_client and self.feature_manager.is_feature_available(
                'campaign_analysis'
            ):
                try:
                    self.campaign_analyzer = CampaignAnalyzer(self.elastic_client)
                    self.campaign_tools = CampaignMCPTools(self.elastic_client)
                    logger.info("Campaign analysis tools initialized successfully")
                except Exception as e:
                    logger.error("Failed to initialize campaign analysis tools", error=str(e))
                    self.campaign_analyzer = None
                    self.campaign_tools = None
            else:
                logger.warning("Campaign analysis tools not initialized - dependencies unavailable")
                self.campaign_analyzer = None
                self.campaign_tools = None

            # Initialize LaTeX template tools only if LaTeX is available
            if self.feature_manager.is_feature_available('latex_reports'):
                try:
                    self.latex_tools = LaTeXTemplateTools()
                    logger.info("LaTeX template tools initialized successfully")
                except Exception as e:
                    logger.error("Failed to initialize LaTeX template tools", error=str(e))
                    self.latex_tools = None
            else:
                logger.warning("LaTeX template tools not initialized - feature unavailable")
                self.latex_tools = None

            # Initialize threat intelligence manager only if the feature is available
            if self.feature_manager.is_feature_available('threat_intelligence'):
                try:
                    self.threat_intelligence_manager = ThreatIntelligenceManager()
                    logger.info("Threat intelligence manager initialized successfully")
                except Exception as e:
                    logger.error("Failed to initialize threat intelligence manager", error=str(e))
                    self.threat_intelligence_manager = None
            else:
                logger.warning("Threat intelligence manager not initialized - feature unavailable")
                self.threat_intelligence_manager = None

        except Exception as e:
            logger.error("Client initialization failed", error=str(e))
            # Set all clients to None to prevent errors
            self.elastic_client = None
            self.dshield_client = None
            self.data_processor = None
            self.context_injector = None
            self.campaign_analyzer = None
            self.campaign_tools = None
            self.latex_tools = None
            self.threat_intelligence_manager = None

    async def _query_dshield_events(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Query DShield events from Elasticsearch.

        This method handles queries for DShield security events from the
        Elasticsearch SIEM with support for advanced pagination, filtering,
        and optimization features.

        Args:
            arguments: Dictionary containing query parameters including:
                - time_range_hours: Time range in hours to query (default: 24)
                - time_range: Exact time range with start/end timestamps
                - relative_time: Relative time range string
                - time_window: Time window around specific timestamp
                - indices: DShield Elasticsearch indices to query
                - filters: Additional query filters
                - fields: Specific fields to return
                - page: Page number for pagination (default: 1)
                - page_size: Number of results per page (default: 100, max: 1000)
                - sort_by: Field to sort by (default: '@timestamp')
                - sort_order: Sort order 'asc' or 'desc' (default: 'desc')
                - cursor: Cursor token for cursor-based pagination
                - optimization: Smart query optimization mode
                - fallback_strategy: Fallback strategy when optimization fails
                - max_result_size_mb: Maximum result size in MB
                - query_timeout_seconds: Query timeout in seconds
                - include_summary: Include summary statistics

        Returns:
            List containing a single dictionary with 'type' and 'text' keys.
            The text contains formatted event data with pagination information.

        Raises:
            ValueError: If invalid time range parameters are provided
            Exception: If Elasticsearch query fails

        """
        time_range_hours = arguments.get("time_range_hours", 24)
        time_range = arguments.get("time_range")
        relative_time = arguments.get("relative_time")
        time_window = arguments.get("time_window")
        indices = arguments.get("indices")
        filters = arguments.get("filters", {})
        fields = arguments.get("fields")
        page = arguments.get("page", 1)
        page_size = arguments.get(
            "page_size",
            self.user_config.get_setting("query", "default_page_size") if self.user_config else 100,
        )
        sort_by = arguments.get("sort_by", "@timestamp")
        sort_order = arguments.get("sort_order", "desc")
        cursor = arguments.get("cursor")
        include_summary = arguments.get("include_summary", True)
        optimization = arguments.get(
            "optimization",
            "auto"
            if self.user_config
            and self.user_config.get_setting("query", "enable_smart_optimization")
            else "none",
        )
        fallback_strategy = arguments.get(
            "fallback_strategy",
            self.user_config.get_setting("query", "fallback_strategy")
            if self.user_config
            else "aggregation",
        )
        max_result_size_mb = arguments.get("max_result_size_mb", 10.0)
        query_timeout_seconds = arguments.get(
            "query_timeout_seconds",
            self.user_config.get_setting("query", "default_timeout_seconds")
            if self.user_config
            else 30,
        )

        logger.info(
            "Querying DShield events",
            time_range_hours=time_range_hours,
            indices=indices,
            fields=fields,
            page=page,
            page_size=page_size,
            include_summary=include_summary,
            optimization=optimization,
            fallback_strategy=fallback_strategy,
            max_result_size_mb=max_result_size_mb,
            query_timeout_seconds=query_timeout_seconds,
        )

        try:
            # Determine time range based on arguments
            if time_range:
                start_time = datetime.fromisoformat(time_range["start"])
                end_time = datetime.fromisoformat(time_range["end"])
            elif relative_time:
                time_delta = {
                    "last_6_hours": timedelta(hours=6),
                    "last_24_hours": timedelta(hours=24),
                    "last_7_days": timedelta(days=7),
                }
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
                "@timestamp": {"gte": start_time.isoformat(), "lte": end_time.isoformat()}
            }

            # Merge time filters with existing filters
            if filters:
                filters.update(time_filters)
            else:
                filters = time_filters

            # Query events with pagination and field selection
            if not self.elastic_client:
                logger.error("Elasticsearch client not initialized")
                return []

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
                query_timeout_seconds=query_timeout_seconds,
            )

            if not events:
                return [
                    {
                        "type": "text",
                        "text": f"No DShield events found for the specified criteria.\n\n"
                        f"Query Parameters:\n- Time Range: {start_time.isoformat()} to "
                        f"{end_time.isoformat()}\n- Page: {page}\n- Page Size: {page_size}\n- "
                        f"Sort: {sort_by} {sort_order}\n- Fields: {fields or 'All'}\n- "
                        f"Filters: {filters}",
                    }
                ]

            # Format response with enhanced pagination info
            response_text = f"DShield Events (Page {pagination_info['page_number']} of "
            f"{pagination_info['total_pages']}):\n\n"
            response_text += f"Total Events: {pagination_info['total_available']:,}\n"
            response_text += f"Events on this page: {len(events)}\n"
            response_text += f"Page Size: {pagination_info['page_size']}\n"
            response_text += (
                f"Sort: {pagination_info['sort_by']} {pagination_info['sort_order']}\n\n"
            )

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

            return [{"type": "text", "text": response_text}]
        except Exception as e:
            logger.error("Failed to query DShield events", error=str(e))
            return [
                {
                    "type": "text",
                    "text": f"Error querying DShield events: {e!s}\n\n"
                    "Please check your Elasticsearch configuration and ensure the server "
                    "is running.",
                }
            ]

    async def _query_dshield_aggregations(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Get aggregated summary data without full records."""
        time_range_hours = arguments.get("time_range_hours", 24)
        time_range = arguments.get("time_range")
        relative_time = arguments.get("relative_time")
        indices = arguments.get("indices")
        group_by = arguments.get("group_by", [])
        metrics = arguments.get("metrics", ["count"])
        filters = arguments.get("filters", {})
        top_n = arguments.get("top_n", 50)
        sort_by = arguments.get("sort_by", "count")
        sort_order = arguments.get("sort_order", "desc")

        logger.info(
            "Querying DShield aggregations",
            time_range_hours=time_range_hours,
            indices=indices,
            group_by=group_by,
            metrics=metrics,
            top_n=top_n,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        try:
            # Determine time range based on arguments
            if time_range:
                start_time = datetime.fromisoformat(time_range["start"])
                end_time = datetime.fromisoformat(time_range["end"])
            elif relative_time:
                time_delta = {
                    "last_6_hours": timedelta(hours=6),
                    "last_24_hours": timedelta(hours=24),
                    "last_7_days": timedelta(days=7),
                }
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
            filters["@timestamp"] = {"gte": start_time.isoformat(), "lte": end_time.isoformat()}

            # Add filters from arguments
            for key, value in filters.items():
                if isinstance(value, dict):
                    # Handle nested filters (e.g., "source_ip": {"eq": "1.2.3.4"})
                    for sub_key, sub_value in value.items():
                        filters[f"{key}.{sub_key}"] = sub_value
                    del filters[key]  # Remove original nested filter

            # Construct the aggregation query
            aggregation_query = {
                "size": 0,  # We only want aggregation results, not documents
                "aggs": {
                    "group_by_agg": {
                        "terms": {"field": group_by, "size": top_n},
                        "aggs": {
                            "metrics_agg": {
                                "sum": {"field": "bytes_sent"},
                                "avg": {"field": "duration"},
                                "count": {"value": 1},
                            }
                        },
                    }
                },
            }

            # Add sort if specified
            if sort_by:
                aggregation_query["aggs"]["group_by_agg"]["terms"]["order"] = {  # type: ignore[index]
                    sort_by: {"order": sort_order}
                }

            # Execute the aggregation query
            elastic_client = self._ensure_elastic_client()
            aggregation_results = await elastic_client.execute_aggregation_query(
                index=indices,
                query=filters,
                aggregation_query=aggregation_query,  # type: ignore[arg-type]
            )

            # Process aggregation results
            processed_aggregations = {}
            for bucket in (
                aggregation_results.get("aggregations", {})
                .get("group_by_agg", {})
                .get("buckets", [])
            ):
                key = bucket["key"]
                metrics_data = bucket["metrics_agg"]
                processed_aggregations[key] = {
                    "count": metrics_data.get("count", 0),
                    "sum_bytes_sent": metrics_data.get("sum_bytes_sent", 0),
                    "avg_duration": metrics_data.get("avg_duration", 0),
                }

            # Add summary information
            summary = {
                "total_count": aggregation_results.get("hits", {}).get("total", {}).get("value", 0),
                "total_bytes_sent": aggregation_results.get("aggregations", {})
                .get("group_by_agg", {})
                .get("sum_of_sum_bytes_sent", 0),
                "avg_duration": aggregation_results.get("aggregations", {})
                .get("group_by_agg", {})
                .get("avg_of_avg_duration", 0),
            }

            response_text = f"DShield Aggregated Statistics (Last {time_range_hours} hours):\n\n"
            response_text += f"- Total Events: {summary['total_count']}\n"
            response_text += f"- Total Bytes Sent: {summary['total_bytes_sent']}\n"
            response_text += f"- Average Duration: {summary['avg_duration']}\n\n"

            response_text += "Detailed Aggregations:\n" + json.dumps(
                processed_aggregations, indent=2, default=str
            )

            return [{"type": "text", "text": response_text}]
        except Exception as e:
            logger.error("Failed to query DShield aggregations", error=str(e))
            return [
                {
                    "type": "text",
                    "text": f"Error querying DShield aggregations: {e!s}\n\n"
                    "Please check your Elasticsearch configuration and ensure the server "
                    "is running.",
                }
            ]

    async def _stream_dshield_events(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
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

        logger.info(
            "Streaming DShield events",
            time_range_hours=time_range_hours,
            indices=indices,
            fields=fields,
            chunk_size=chunk_size,
            max_chunks=max_chunks,
            include_summary=include_summary,
            stream_id=stream_id,
        )

        try:
            # Determine time range based on arguments
            if time_range:
                start_time = datetime.fromisoformat(time_range["start"])
                end_time = datetime.fromisoformat(time_range["end"])
            elif relative_time:
                time_delta = {
                    "last_6_hours": timedelta(hours=6),
                    "last_24_hours": timedelta(hours=24),
                    "last_7_days": timedelta(days=7),
                }
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
                "@timestamp": {"gte": start_time.isoformat(), "lte": end_time.isoformat()}
            }
            if filters:
                filters.update(time_filters)
            else:
                filters = time_filters

            # Initialize stream state
            stream_state = {
                "current_chunk_index": 0,
                "total_events_processed": 0,
                "last_event_id": None,
            }

            # Collect all chunks into a single response
            all_chunks = []
            current_stream_id = stream_id

            # Fetch events in chunks
            for chunk_index in range(max_chunks):
                logger.info(
                    f"Fetching chunk {chunk_index + 1}/{max_chunks}",
                    start_time=start_time.isoformat(),
                    end_time=end_time.isoformat(),
                    chunk_size=chunk_size,
                    stream_id=current_stream_id,
                )

                (
                    events,
                    total_count,
                    last_event_id,
                ) = await self._ensure_elastic_client().stream_dshield_events(
                    time_range_hours=time_range_hours,
                    indices=indices,
                    filters=filters,
                    fields=fields,
                    chunk_size=chunk_size,
                    stream_id=current_stream_id,
                )

                if not events:
                    logger.info(f"No more events in chunk {chunk_index + 1}. Ending stream.")
                    break

                # Update stream state
                stream_state["current_chunk_index"] = chunk_index + 1
                if stream_state["total_events_processed"] is None:
                    stream_state["total_events_processed"] = 0
                stream_state["total_events_processed"] += len(events)
                stream_state["last_event_id"] = (
                    str(last_event_id) if last_event_id is not None else None
                )

                # Create chunk summary
                chunk_summary = {
                    "chunk_index": chunk_index + 1,
                    "events_count": len(events),
                    "total_count": total_count,
                    "stream_id": last_event_id,
                    "events": events,
                }

                all_chunks.append(chunk_summary)

                # Update stream_id for next chunk
                current_stream_id = last_event_id

                # If we've reached the end, break
                if not last_event_id:
                    break

            # Create comprehensive response
            response_text = "DShield Event Streaming Results:\n\n"
            response_text += f"Time Range: {start_time.isoformat()} to {end_time.isoformat()}\n"
            response_text += f"Total Chunks Processed: {stream_state['current_chunk_index']}\n"
            response_text += f"Total Events Processed: {stream_state['total_events_processed']}\n"
            response_text += f"Chunk Size: {chunk_size}\n"
            response_text += f"Max Chunks: {max_chunks}\n"
            response_text += f"Final Stream ID: {stream_state['last_event_id']}\n\n"

            if include_summary:
                response_text += "Stream Summary:\n"
                response_text += f"- Chunks returned: {len(all_chunks)}\n"
                response_text += (
                    f"- Events per chunk: {[chunk['events_count'] for chunk in all_chunks]}\n"
                )
                response_text += "- Stream IDs: "
                f"{[chunk['stream_id'] for chunk in all_chunks if chunk['stream_id']]}\n\n"

            response_text += "Chunk Details:\n" + json.dumps(all_chunks, indent=2, default=str)

            return [{"type": "text", "text": response_text}]

        except Exception as e:
            logger.error("Failed to stream DShield events", error=str(e))
            return [
                {
                    "type": "text",
                    "text": f"Error streaming DShield events: {e!s}\n\n"
                    "Please check your Elasticsearch configuration and ensure the server "
                    "is running.",
                }
            ]

    async def _stream_dshield_events_with_session_context(
        self, arguments: dict[str, Any]
    ) -> list[dict[str, Any]]:
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

        logger.info(
            "Streaming DShield events with session context",
            time_range_hours=time_range_hours,
            indices=indices,
            fields=fields,
            chunk_size=chunk_size,
            session_fields=session_fields,
            max_session_gap_minutes=max_session_gap_minutes,
            include_session_summary=include_session_summary,
            stream_id=stream_id,
        )

        try:
            # Stream events with session context
            (
                events,
                total_count,
                next_stream_id,
                session_context,
            ) = await self.elastic_client.stream_dshield_events_with_session_context(
                time_range_hours=time_range_hours,
                indices=indices,
                filters=filters,
                fields=fields,
                chunk_size=chunk_size,
                session_fields=session_fields,
                max_session_gap_minutes=max_session_gap_minutes,
                include_session_summary=include_session_summary,
                stream_id=stream_id,
            )

            # Format response with session context
            response = {
                "events": events,
                "total_count": total_count,
                "next_stream_id": next_stream_id,
                "session_context": session_context,
            }

            return [{"type": "text", "text": json.dumps(response, default=str, indent=2)}]

        except Exception as e:
            logger.error("Session context streaming failed", error=str(e))
            raise

    async def _query_dshield_attacks(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Query DShield attack data specifically."""
        time_range_hours = arguments.get("time_range_hours", 24)
        page = arguments.get("page", 1)
        page_size = arguments.get("page_size", 100)
        include_summary = arguments.get("include_summary", True)

        logger.info(
            "Querying DShield attacks",
            time_range_hours=time_range_hours,
            page=page,
            page_size=page_size,
            include_summary=include_summary,
        )

        try:
            attacks, total_count = await self.elastic_client.query_dshield_attacks(
                time_range_hours=time_range_hours,
                page=page,
                page_size=page_size,
                include_summary=include_summary,
            )

            # Generate pagination info
            pagination_info = self.elastic_client._generate_pagination_info(
                page, page_size, total_count
            )

            response_text = (
                f"Found {total_count} DShield attacks in the last {time_range_hours} hours.\n"
            )
            response_text += f"Showing page {page} of {pagination_info['total_pages']} "
            f"(results {pagination_info['start_index']}-{pagination_info['end_index']}).\n\n"

            if include_summary and attacks:
                # Add summary information
                summary = self.data_processor.generate_security_summary(attacks)
                response_text += "Page Summary:\n"
                response_text += f"- Attacks on this page: {len(attacks)}\n"
                response_text += f"- High risk attacks: {summary.get('high_risk_events', 0)}\n"
                response_text += (
                    f"- Unique attacker IPs: {len(summary.get('unique_source_ips', []))}\n"
                )
                response_text += (
                    f"- Attack patterns: {list(summary.get('attack_patterns', {}).keys())}\n\n"
                )

            response_text += "Attack Details:\n" + json.dumps(attacks, indent=2, default=str)

            # Add pagination info to response
            if pagination_info['has_next'] or pagination_info['has_previous']:
                response_text += "\n\nPagination Info:\n" + json.dumps(pagination_info, indent=2)

            return [{"type": "text", "text": response_text}]
        except Exception as e:
            logger.error("Failed to query DShield attacks", error=str(e))
            return [
                {
                    "type": "text",
                    "text": f"Error querying DShield attacks: {e!s}\n\n"
                    "Please check your Elasticsearch configuration and ensure the server "
                    "is running.",
                }
            ]

    async def _query_dshield_reputation(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Query DShield reputation data."""
        ip_addresses = arguments.get("ip_addresses", [])
        size = arguments.get("size", 1000)

        logger.info("Querying DShield reputation data", ip_addresses=ip_addresses, size=size)

        reputation_data = await self.elastic_client.query_dshield_reputation(
            ip_addresses=ip_addresses if ip_addresses else None, size=size
        )

        return [
            {
                "type": "text",
                "text": f"Found {len(reputation_data)} DShield reputation records:\n\n"
                + json.dumps(reputation_data, indent=2, default=str),
            }
        ]

    async def _query_dshield_top_attackers(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Query DShield top attackers data."""
        hours = arguments.get("hours", 24)
        limit = arguments.get("limit", 100)

        logger.info("Querying DShield top attackers", hours=hours, limit=limit)

        attackers = await self.elastic_client.query_dshield_top_attackers(hours=hours, limit=limit)

        return [
            {
                "type": "text",
                "text": f"Found {len(attackers)} top DShield attackers in the last "
                f"{hours} hours:\n\n" + json.dumps(attackers, indent=2, default=str),
            }
        ]

    async def _query_dshield_geographic_data(
        self, arguments: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Query DShield geographic data."""
        countries = arguments.get("countries")
        size = arguments.get("size", 1000)

        logger.info("Querying DShield geographic data", countries=countries, size=size)

        geo_data = await self.elastic_client.query_dshield_geographic_data(
            countries=countries, size=size
        )

        return [
            {
                "type": "text",
                "text": f"Found {len(geo_data)} DShield geographic records:\n\n"
                + json.dumps(geo_data, indent=2, default=str),
            }
        ]

    async def _query_dshield_port_data(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Query DShield port data."""
        ports = arguments.get("ports")
        size = arguments.get("size", 1000)

        logger.info("Querying DShield port data", ports=ports, size=size)

        port_data = await self.elastic_client.query_dshield_port_data(ports=ports, size=size)

        return [
            {
                "type": "text",
                "text": f"Found {len(port_data)} DShield port records:\n\n"
                + json.dumps(port_data, indent=2, default=str),
            }
        ]

    async def _get_dshield_statistics(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Get DShield statistics and summary."""
        time_range_hours = arguments.get("time_range_hours", 24)

        logger.info("Getting DShield statistics", time_range_hours=time_range_hours)

        stats = await self.elastic_client.get_dshield_statistics(time_range_hours=time_range_hours)

        return [
            {
                "type": "text",
                "text": f"DShield Statistics (Last {time_range_hours} hours):\n\n"
                + json.dumps(stats, indent=2, default=str),
            }
        ]

    async def _diagnose_data_availability(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Diagnose why queries return empty results and troubleshoot data availability issues."""
        check_indices = arguments.get("check_indices", True)
        check_mappings = arguments.get("check_mappings", True)
        check_recent_data = arguments.get("check_recent_data", True)
        sample_query = arguments.get("sample_query", True)

        logger.info(
            "Diagnosing data availability",
            check_indices=check_indices,
            check_mappings=check_mappings,
            check_recent_data=check_recent_data,
            sample_query=sample_query,
        )

        result = await self.threat_intelligence_manager.diagnose_data_availability(
            check_indices=check_indices,
            check_mappings=check_mappings,
            check_recent_data=check_recent_data,
            sample_query=sample_query,
        )

        return [
            {
                "type": "text",
                "text": "Data Availability Diagnosis Results:\n\n"
                + json.dumps(result, indent=2, default=str),
            }
        ]

    async def _enrich_ip_with_dshield(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Enrich IP address with DShield threat intelligence."""
        ip_address = arguments["ip_address"]

        logger.info("Enriching IP with DShield", ip_address=ip_address)

        threat_data = await self.dshield_client.get_ip_reputation(ip_address)

        return [
            {
                "type": "text",
                "text": f"DShield threat intelligence for {ip_address}:\n\n"
                + json.dumps(threat_data, indent=2, default=str),
            }
        ]

    async def _generate_attack_report(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate structured attack report."""
        events = arguments.get("events", [])
        threat_intelligence = arguments.get("threat_intelligence", {})

        logger.info("Generating attack report", event_count=len(events))

        report = self.data_processor.generate_attack_report(events, threat_intelligence)

        return [
            {
                "type": "text",
                "text": "Attack Report:\n\n" + json.dumps(report, indent=2, default=str),
            }
        ]

    async def _query_events_by_ip(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Query events for specific IP addresses."""
        ip_addresses = arguments["ip_addresses"]
        time_range_hours = arguments.get("time_range_hours", 24)

        logger.info(
            "Querying events by IP", ip_addresses=ip_addresses, time_range_hours=time_range_hours
        )

        events = await self.elastic_client.query_events_by_ip(
            ip_addresses=ip_addresses, time_range_hours=time_range_hours
        )

        processed_events = self.data_processor.process_security_events(events)

        return [
            {
                "type": "text",
                "text": f"Events for IPs {ip_addresses} in the last {time_range_hours} hours:\n\n"
                + json.dumps(processed_events, indent=2, default=str),
            }
        ]

    async def _get_security_summary(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
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

        return [
            {
                "type": "text",
                "text": "Security Summary (Last 24 Hours):\n\n"
                + json.dumps(summary, indent=2, default=str),
            }
        ]

    async def _test_elasticsearch_connection(
        self, arguments: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Test Elasticsearch connection and show available indices.

        This method performs a comprehensive test of the Elasticsearch
        connection, including cluster information, available indices,
        and cluster health status. It's useful for troubleshooting
        connection issues and verifying the Elasticsearch setup.

        Args:
            arguments: Dictionary containing test parameters (currently unused)

        Returns:
            List containing a single dictionary with 'type' and 'text' keys.
            The text contains connection status and cluster information.

        Raises:
            Exception: If Elasticsearch connection fails

        """
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
                    "status": health.get('status'),
                },
                "available_dshield_indices": indices,
                "total_indices": len(indices),
            }

            return [
                {
                    "type": "text",
                    "text": "✅ Elasticsearch connection successful!\n\n"
                    + json.dumps(result, indent=2, default=str),
                }
            ]

        except Exception as e:
            logger.error("Elasticsearch connection test failed", error=str(e))
            return [
                {
                    "type": "text",
                    "text": f"❌ Elasticsearch connection failed: {e!s}\n\n"
                    + "Please check:\n"
                    + "1. Elasticsearch is running\n"
                    + "2. The URL in mcp_config.yaml is correct\n"
                    + "3. Network connectivity to the Elasticsearch server\n"
                    + "4. Authentication credentials if required",
                }
            ]

    async def _get_data_dictionary(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Get comprehensive data dictionary for DShield SIEM fields and analysis guidelines."""
        format_type = arguments.get("format", "prompt")
        sections = arguments.get("sections", ["fields", "examples", "patterns", "guidelines"])

        logger.info("Getting data dictionary", format=format_type, sections=sections)

        if format_type == "prompt":
            # Return the formatted prompt
            prompt = DataDictionary.get_initial_prompt()
            return [{"type": "text", "text": prompt}]
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

            return [{"type": "text", "text": json.dumps(data, indent=2, default=str)}]

    async def _get_health_status(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Get health status of the MCP server and its dependencies."""
        detailed = arguments.get("detailed", False)

        logger.info("Getting health status", detailed=detailed)

        try:
            # Run all health checks
            health_results = await self.health_manager.run_all_checks()

            # Get feature availability summary
            feature_summary = self.feature_manager.get_feature_summary()

            if detailed:
                # Return comprehensive health information
                response_data = {
                    "status": "healthy" if health_results.get("summary", {}).get("healthy", 0) > 0 else "degraded",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "health_checks": health_results,
                    "features": feature_summary,
                    "server_info": {
                        "tools_loaded": len(self.tool_loader.get_all_tool_definitions()),
                        "tools_available": len(self.tool_loader.get_available_tools(
                            self.feature_manager.get_available_features()
                        )),
                    }
                }
            else:
                # Return summary information
                summary = health_results.get("summary", {})
                response_data = {
                    "status": "healthy" if summary.get("healthy", 0) > 0 else "degraded",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "healthy_services": summary.get("healthy", 0),
                    "unhealthy_services": summary.get("unhealthy", 0),
                    "available_features": len(self.feature_manager.get_available_features()),
                    "total_tools": len(self.tool_loader.get_all_tool_definitions()),
                }

            return [{"type": "text", "text": json.dumps(response_data, indent=2, default=str)}]

        except Exception as e:
            logger.error("Failed to get health status", error=str(e))
            return [
                {
                    "type": "text",
                    "text": f"Error getting health status: {e!s}\n\n"
                    "The health check system may not be fully initialized.",
                }
            ]

    async def _detect_statistical_anomalies(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Detect statistical anomalies in DShield event data."""
        time_range_hours = arguments.get("time_range_hours", 24)
        anomaly_methods = arguments.get("anomaly_methods", ["zscore"])
        sensitivity = arguments.get("sensitivity", 3.0)
        return_summary_only = arguments.get("return_summary_only", False)
        max_anomalies = arguments.get("max_anomalies", 100)
        dimension_schema = arguments.get("dimension_schema")

        logger.info(
            "Detecting statistical anomalies",
            time_range_hours=time_range_hours,
            methods=anomaly_methods,
            sensitivity=sensitivity,
        )

        try:
            if not self.elastic_client:
                logger.error("Elasticsearch client not initialized")
                return [
                    {
                        "type": "text",
                        "text": "Error: Elasticsearch client not initialized. "
                        "Statistical anomaly detection requires Elasticsearch.",
                    }
                ]

            # Initialize statistical analysis tools if needed
            from src.statistical_analysis_tools import StatisticalAnalysisTools
            stat_tools = StatisticalAnalysisTools(
                self.elastic_client,
                self.error_handler
            )

            # Detect anomalies using the specified methods
            results = {}
            for method in anomaly_methods:
                try:
                    if method == "zscore":
                        anomalies = await stat_tools.detect_zscore_anomalies(
                            time_range_hours=time_range_hours,
                            z_threshold=sensitivity,
                            dimension_schema=dimension_schema,
                        )
                    elif method == "iqr":
                        anomalies = await stat_tools.detect_iqr_anomalies(
                            time_range_hours=time_range_hours,
                            iqr_multiplier=sensitivity,
                            dimension_schema=dimension_schema,
                        )
                    elif method == "isolation_forest":
                        anomalies = await stat_tools.detect_isolation_forest_anomalies(
                            time_range_hours=time_range_hours,
                            contamination=0.1,
                            dimension_schema=dimension_schema,
                        )
                    elif method == "time_series":
                        anomalies = await stat_tools.detect_time_series_anomalies(
                            time_range_hours=time_range_hours,
                            sensitivity=sensitivity,
                            dimension_schema=dimension_schema,
                        )
                    else:
                        logger.warning("Unsupported anomaly detection method", method=method)
                        continue

                    # Limit anomalies if requested
                    if max_anomalies and len(anomalies) > max_anomalies:
                        anomalies = anomalies[:max_anomalies]

                    results[method] = anomalies

                except Exception as method_error:
                    logger.error(
                        "Failed to detect anomalies with method",
                        method=method,
                        error=str(method_error)
                    )
                    results[method] = {"error": str(method_error)}

            # Format response
            if return_summary_only:
                summary = {
                    "time_range_hours": time_range_hours,
                    "methods_used": anomaly_methods,
                    "sensitivity": sensitivity,
                    "results_by_method": {
                        method: {
                            "anomalies_found": len(data) if isinstance(data, list) else 0,
                            "error": data.get("error") if isinstance(data, dict) else None
                        }
                        for method, data in results.items()
                    }
                }
                return [{"type": "text", "text": json.dumps(summary, indent=2, default=str)}]
            else:
                response_text = f"Statistical Anomaly Detection Results\n"
                response_text += f"Time Range: {time_range_hours} hours\n"
                response_text += f"Methods: {', '.join(anomaly_methods)}\n"
                response_text += f"Sensitivity: {sensitivity}\n\n"
                response_text += json.dumps(results, indent=2, default=str)
                return [{"type": "text", "text": response_text}]

        except Exception as e:
            logger.error("Failed to detect statistical anomalies", error=str(e))
            return [
                {
                    "type": "text",
                    "text": f"Error detecting statistical anomalies: {e!s}\n\n"
                    "Please check your Elasticsearch configuration and ensure the statistical "
                    "analysis tools are properly initialized.",
                }
            ]

    async def _get_recent_dshield_events(self) -> list[dict[str, Any]]:
        """Get recent DShield events for resource reading."""
        events = await self.elastic_client.query_dshield_events(time_range_hours=1)
        return self.data_processor.process_security_events(events)

    async def _get_recent_dshield_attacks(self) -> list[dict[str, Any]]:
        """Get recent DShield attacks for resource reading."""
        attacks, _ = await self.elastic_client.query_dshield_attacks(time_range_hours=1)
        return attacks

    async def _get_dshield_top_attackers(self) -> list[dict[str, Any]]:
        """Get DShield top attackers for resource reading."""
        return await self.elastic_client.query_dshield_top_attackers(hours=24)

    async def _get_dshield_stats(self) -> dict[str, Any]:
        """Get DShield statistics for resource reading."""
        return await self.elastic_client.get_dshield_statistics(time_range_hours=24)

    # Campaign Analysis Tool Handlers

    async def _analyze_campaign(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Analyze attack campaigns from seed indicators."""
        seed_indicators = arguments["seed_indicators"]
        time_range_hours = arguments.get("time_range_hours", 168)
        correlation_methods = arguments.get("correlation_methods")
        min_confidence = arguments.get("min_confidence", 0.7)
        include_timeline = arguments.get("include_timeline", True)
        include_relationships = arguments.get("include_relationships", True)

        logger.info(
            "Analyzing campaign",
            seed_indicators=seed_indicators,
            time_range_hours=time_range_hours,
            correlation_methods=correlation_methods,
        )

        result = await self.campaign_tools.analyze_campaign(
            seed_indicators=seed_indicators,
            time_range_hours=time_range_hours,
            correlation_methods=correlation_methods,
            min_confidence=min_confidence,
            include_timeline=include_timeline,
            include_relationships=include_relationships,
        )

        return [
            {
                "type": "text",
                "text": "Campaign Analysis Results:\n\n"
                + json.dumps(result, indent=2, default=str),
            }
        ]

    async def _expand_campaign_indicators(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Expand IOCs to find related indicators."""
        campaign_id = arguments["campaign_id"]
        expansion_depth = arguments.get("expansion_depth", 3)
        expansion_strategy = arguments.get("expansion_strategy", "comprehensive")
        include_passive_dns = arguments.get("include_passive_dns", True)
        include_threat_intel = arguments.get("include_threat_intel", True)

        logger.info(
            "Expanding campaign indicators",
            campaign_id=campaign_id,
            expansion_depth=expansion_depth,
            expansion_strategy=expansion_strategy,
        )

        result = await self.campaign_tools.expand_campaign_indicators(
            campaign_id=campaign_id,
            expansion_depth=expansion_depth,
            expansion_strategy=expansion_strategy,
            include_passive_dns=include_passive_dns,
            include_threat_intel=include_threat_intel,
        )

        return [
            {
                "type": "text",
                "text": "Campaign Indicator Expansion Results:\n\n"
                + json.dumps(result, indent=2, default=str),
            }
        ]

    async def _get_campaign_timeline(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Build detailed attack timelines."""
        campaign_id = arguments["campaign_id"]
        timeline_granularity = arguments.get("timeline_granularity", "hourly")
        include_event_details = arguments.get("include_event_details", True)
        include_ttp_analysis = arguments.get("include_ttp_analysis", True)

        logger.info(
            "Building campaign timeline",
            campaign_id=campaign_id,
            timeline_granularity=timeline_granularity,
        )

        result = await self.campaign_tools.get_campaign_timeline(
            campaign_id=campaign_id,
            timeline_granularity=timeline_granularity,
            include_event_details=include_event_details,
            include_ttp_analysis=include_ttp_analysis,
        )

        return [
            {
                "type": "text",
                "text": "Campaign Timeline Results:\n\n"
                + json.dumps(result, indent=2, default=str),
            }
        ]

    async def _compare_campaigns(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Compare multiple campaigns for similarities."""
        campaign_ids = arguments["campaign_ids"]
        comparison_metrics = arguments.get("comparison_metrics")
        include_visualization_data = arguments.get("include_visualization_data", True)

        logger.info(
            "Comparing campaigns", campaign_ids=campaign_ids, comparison_metrics=comparison_metrics
        )

        result = await self.campaign_tools.compare_campaigns(
            campaign_ids=campaign_ids,
            comparison_metrics=comparison_metrics,
            include_visualization_data=include_visualization_data,
        )

        return [
            {
                "type": "text",
                "text": "Campaign Comparison Results:\n\n"
                + json.dumps(result, indent=2, default=str),
            }
        ]

    async def _detect_ongoing_campaigns(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Real-time detection of active campaigns."""
        time_window_hours = arguments.get("time_window_hours", 24)
        min_event_threshold = arguments.get("min_event_threshold", 15)
        correlation_threshold = arguments.get("correlation_threshold", 0.8)
        include_alert_data = arguments.get("include_alert_data", True)

        logger.info(
            "Detecting ongoing campaigns",
            time_window_hours=time_window_hours,
            min_event_threshold=min_event_threshold,
            correlation_threshold=correlation_threshold,
        )

        result = await self.campaign_tools.detect_ongoing_campaigns(
            time_window_hours=time_window_hours,
            min_event_threshold=min_event_threshold,
            correlation_threshold=correlation_threshold,
            include_alert_data=include_alert_data,
        )

        return [
            {
                "type": "text",
                "text": "Ongoing Campaign Detection Results:\n\n"
                + json.dumps(result, indent=2, default=str),
            }
        ]

    async def _search_campaigns(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Search existing campaigns by criteria."""
        search_criteria = arguments["search_criteria"]
        time_range_hours = arguments.get("time_range_hours", 168)
        max_results = arguments.get("max_results", 50)
        include_summaries = arguments.get("include_summaries", True)

        logger.info(
            "Searching campaigns",
            search_criteria=search_criteria,
            time_range_hours=time_range_hours,
            max_results=max_results,
        )

        result = await self.campaign_tools.search_campaigns(
            search_criteria=search_criteria,
            time_range_hours=time_range_hours,
            max_results=max_results,
            include_summaries=include_summaries,
        )

        return [
            {
                "type": "text",
                "text": "Campaign Search Results:\n\n" + json.dumps(result, indent=2, default=str),
            }
        ]

    async def _get_campaign_details(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Get comprehensive campaign information."""
        campaign_id = arguments["campaign_id"]
        include_full_timeline = arguments.get("include_full_timeline", False)
        include_relationships = arguments.get("include_relationships", True)
        include_threat_intel = arguments.get("include_threat_intel", True)

        logger.info(
            "Getting campaign details",
            campaign_id=campaign_id,
            include_full_timeline=include_full_timeline,
        )

        result = await self.campaign_tools.get_campaign_details(
            campaign_id=campaign_id,
            include_full_timeline=include_full_timeline,
            include_relationships=include_relationships,
            include_threat_intel=include_threat_intel,
        )

        return [
            {
                "type": "text",
                "text": "Campaign Details:\n\n" + json.dumps(result, indent=2, default=str),
            }
        ]

    async def _generate_latex_document(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Generate a complete document from a LaTeX template."""
        template_name = arguments["template_name"]
        document_data = arguments["document_data"]
        output_format = arguments.get("output_format", "pdf")
        include_assets = arguments.get("include_assets", True)
        compile_options = arguments.get("compile_options")

        logger.info(
            "Generating LaTeX document",
            template_name=template_name,
            output_format=output_format,
            include_assets=include_assets,
        )

        result = await self.latex_tools.generate_document(
            template_name=template_name,
            document_data=document_data,
            output_format=output_format,
            include_assets=include_assets,
            compile_options=compile_options,
        )

        return [
            {
                "type": "text",
                "text": "LaTeX Document Generation Results:\n\n"
                + json.dumps(result, indent=2, default=str),
            }
        ]

    async def _list_latex_templates(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """List all available LaTeX templates."""
        logger.info("Listing LaTeX templates")

        result = await self.latex_tools.list_available_templates()

        return [
            {
                "type": "text",
                "text": "Available LaTeX Templates:\n\n"
                + json.dumps(result, indent=2, default=str),
            }
        ]

    async def _get_latex_template_schema(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Get the schema for a specific LaTeX template."""
        template_name = arguments["template_name"]

        logger.info("Getting LaTeX template schema", template_name=template_name)

        result = await self.latex_tools.get_template_schema(template_name)

        return [
            {
                "type": "text",
                "text": f"LaTeX Template Schema for '{template_name}':\n\n"
                + json.dumps(result, indent=2, default=str),
            }
        ]

    async def _validate_latex_document_data(
        self, arguments: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Validate document data against template requirements."""
        template_name = arguments["template_name"]
        document_data = arguments["document_data"]

        logger.info("Validating LaTeX document data", template_name=template_name)

        result = await self.latex_tools.validate_document_data(template_name, document_data)

        return [
            {
                "type": "text",
                "text": f"LaTeX Document Data Validation for '{template_name}':\n\n"
                + json.dumps(result, indent=2, default=str),
            }
        ]

    # Enhanced Threat Intelligence Tool Handlers

    async def _enrich_ip_comprehensive(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Comprehensive IP enrichment from multiple threat intelligence sources."""
        ip_address = arguments["ip_address"]
        sources = arguments.get("sources", ["all"])
        include_raw_data = arguments.get("include_raw_data", False)

        logger.info(
            "Starting comprehensive IP enrichment",
            ip_address=ip_address,
            sources=sources,
            include_raw_data=include_raw_data,
        )

        try:
            result = await self.threat_intelligence_manager.enrich_ip_comprehensive(ip_address)

            # Format response
            response_data = {
                "ip_address": result.ip_address,
                "overall_threat_score": result.overall_threat_score,
                "confidence_score": result.confidence_score,
                "sources_queried": [source.value for source in result.sources_queried],
                "threat_indicators": result.threat_indicators,
                "geographic_data": result.geographic_data,
                "network_data": result.network_data,
                "first_seen": result.first_seen.isoformat() if result.first_seen else None,
                "last_seen": result.last_seen.isoformat() if result.last_seen else None,
                "cache_hit": result.cache_hit,
                "query_timestamp": result.query_timestamp.isoformat(),
            }

            if include_raw_data:
                response_data["source_results"] = result.source_results

            return [
                {
                    "type": "text",
                    "text": f"Comprehensive IP Enrichment Results for {ip_address}:\n\n"
                    + json.dumps(response_data, indent=2, default=str),
                }
            ]

        except Exception as e:
            logger.error("Comprehensive IP enrichment failed", ip_address=ip_address, error=str(e))
            return [{"type": "text", "text": f"Error enriching IP {ip_address}: {e!s}"}]

    async def _enrich_domain_comprehensive(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Comprehensive domain enrichment from multiple threat intelligence sources."""
        domain = arguments["domain"]
        sources = arguments.get("sources", ["all"])
        include_raw_data = arguments.get("include_raw_data", False)

        logger.info(
            "Starting comprehensive domain enrichment",
            domain=domain,
            sources=sources,
            include_raw_data=include_raw_data,
        )

        try:
            result = await self.threat_intelligence_manager.enrich_domain_comprehensive(domain)

            # Format response
            response_data = {
                "domain": result.domain,
                "threat_score": result.threat_score,
                "reputation_score": result.reputation_score,
                "ip_addresses": result.ip_addresses,
                "nameservers": result.nameservers,
                "registrar": result.registrar,
                "creation_date": result.creation_date.isoformat() if result.creation_date else None,
                "malware_families": result.malware_families,
                "categories": result.categories,
                "tags": result.tags,
                "sources_queried": [source.value for source in result.sources_queried],
                "cache_hit": result.cache_hit,
                "query_timestamp": result.query_timestamp.isoformat(),
            }

            if include_raw_data:
                response_data["source_results"] = result.source_results

            return [
                {
                    "type": "text",
                    "text": f"Comprehensive Domain Enrichment Results for {domain}:\n\n"
                    + json.dumps(response_data, indent=2, default=str),
                }
            ]

        except Exception as e:
            logger.error("Comprehensive domain enrichment failed", domain=domain, error=str(e))
            return [{"type": "text", "text": f"Error enriching domain {domain}: {e!s}"}]

    async def _correlate_threat_indicators(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Correlate multiple threat indicators across sources."""
        indicators = arguments["indicators"]
        correlation_method = arguments.get("correlation_method", "comprehensive")

        logger.info(
            "Starting threat indicator correlation",
            indicator_count=len(indicators),
            correlation_method=correlation_method,
        )

        try:
            result = await self.threat_intelligence_manager.correlate_threat_indicators(indicators)

            return [
                {
                    "type": "text",
                    "text": "Threat Indicator Correlation Results:\n\n"
                    + json.dumps(result, indent=2, default=str),
                }
            ]

        except Exception as e:
            logger.error(
                "Threat indicator correlation failed",
                indicators=indicators[:5],  # Log first 5 for privacy
                error=str(e),
            )
            return [{"type": "text", "text": f"Error correlating threat indicators: {e!s}"}]

    async def _get_threat_intelligence_summary(
        self, arguments: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Get summary of threat intelligence capabilities and status."""
        include_source_status = arguments.get("include_source_status", True)
        include_cache_stats = arguments.get("include_cache_stats", True)

        logger.info("Getting threat intelligence summary")

        try:
            summary = {
                "available_sources": [
                    source.value
                    for source in self.threat_intelligence_manager.get_available_sources()
                ],
                "total_sources": len(self.threat_intelligence_manager.get_available_sources()),
                "correlation_config": {
                    "confidence_threshold": self.threat_intelligence_manager.confidence_threshold,
                    "max_sources_per_query": self.threat_intelligence_manager.max_sources,
                },
            }

            if include_source_status:
                summary["source_status"] = self.threat_intelligence_manager.get_source_status()

            if include_cache_stats:
                cache_size = len(self.threat_intelligence_manager.cache)
                summary["cache_stats"] = {
                    "cache_size": cache_size,
                    "cache_ttl_hours": self.threat_intelligence_manager.cache_ttl.total_seconds()
                    / 3600,
                    "max_cache_size": self.threat_intelligence_manager.config.get(
                        "threat_intelligence", {}
                    ).get("max_cache_size", 1000),
                }

            return [
                {
                    "type": "text",
                    "text": "Threat Intelligence Summary:\n\n"
                    + json.dumps(summary, indent=2, default=str),
                }
            ]

        except Exception as e:
            logger.error("Failed to get threat intelligence summary", error=str(e))
            return [{"type": "text", "text": f"Error getting threat intelligence summary: {e!s}"}]

    async def _detect_statistical_anomalies(
        self, arguments: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Detect statistical anomalies in DShield data patterns.

        Notes:
            - mcp-protocol-core: Keep tool IO predictable; validate inputs and surface
              structured errors via MCPErrorHandler.
            - mcp-performance: Default to fast paths; heavy options (percentiles, robust
              time-series) are opt-in via parameters.
            - mcp-error-handling: Wrap execution in timeouts; do not raise raw exceptions.
        """
        time_range_hours = arguments.get("time_range_hours", 24)
        anomaly_methods = arguments.get("anomaly_methods", ["zscore", "iqr"])
        sensitivity = arguments.get("sensitivity", 2.5)
        dimensions = arguments.get(
            "dimensions", ["source_ip", "destination_port", "bytes_transferred", "event_rate"]
        )
        return_summary_only = arguments.get("return_summary_only", True)
        max_anomalies = arguments.get("max_anomalies", 50)
        # New optional parameters exposed via tool schema
        dimension_schema = arguments.get("dimension_schema")
        enable_iqr = arguments.get("enable_iqr")
        enable_percentiles = arguments.get("enable_percentiles")
        time_series_mode = arguments.get("time_series_mode", "fast")
        seasonality_hour_of_day = arguments.get("seasonality_hour_of_day")
        raw_sample_mode = arguments.get("raw_sample_mode", False)
        raw_sample_size = arguments.get("raw_sample_size", 50)
        min_iforest_samples = arguments.get("min_iforest_samples")
        scale_iforest_features = arguments.get("scale_iforest_features")

        logger.info(
            "Starting statistical anomaly detection",
            time_range_hours=time_range_hours,
            anomaly_methods=anomaly_methods,
            sensitivity=sensitivity,
            dimensions=dimensions,
        )

        try:
            # Create instance with existing Elasticsearch client
            stats_tools = StatisticalAnalysisTools(self.elastic_client)

            # Perform anomaly detection
            result = await stats_tools.detect_statistical_anomalies(
                time_range_hours=time_range_hours,
                anomaly_methods=anomaly_methods,
                sensitivity=sensitivity,
                dimensions=dimensions,
                return_summary_only=return_summary_only,
                max_anomalies=max_anomalies,
                dimension_schema=dimension_schema,
                enable_iqr=enable_iqr,
                enable_percentiles=enable_percentiles,
                time_series_mode=time_series_mode,
                seasonality_hour_of_day=seasonality_hour_of_day,
                raw_sample_mode=raw_sample_mode,
                raw_sample_size=raw_sample_size,
                min_iforest_samples=min_iforest_samples,
                scale_iforest_features=scale_iforest_features,
            )

            if result.get("success", False):
                return [
                    {
                        "type": "text",
                        "text": "Statistical Anomaly Detection Results:\n\n"
                        + json.dumps(result, indent=2, default=str),
                    }
                ]
            else:
                return [
                    {
                        "type": "text",
                        "text": f"Anomaly detection failed: {result.get('error', 'Unknown error')}",
                    }
                ]

        except Exception as e:
            logger.error("Statistical anomaly detection failed", error=str(e))
            return [{"type": "text", "text": f"Error during statistical anomaly detection: {e!s}"}]

    def _register_resources(self) -> None:
        # Register main resources for cleanup
        if self.elastic_client:
            self.resource_manager.register_cleanup_handler(self.elastic_client.close)
        if self.threat_intelligence_manager:
            self.resource_manager.register_cleanup_handler(self.threat_intelligence_manager.cleanup)
        # Add more as needed

    async def cleanup(self) -> None:
        """Cleanup resources.

        Properly closes all client connections and releases resources
        to prevent memory leaks and connection pool exhaustion.
        This method should be called when shutting down the server.
        """
        if self.elastic_client:
            await self.elastic_client.close()  # type: ignore[no-untyped-call]
        if self.threat_intelligence_manager:
            await self.threat_intelligence_manager.cleanup()
        await self.resource_manager.cleanup_all()
        logger.info("DShield MCP Server cleanup completed")

    def _ensure_elastic_client(self) -> ElasticsearchClient:
        """Ensure Elasticsearch client is initialized and return it.

        Returns:
            ElasticsearchClient: The initialized client

        Raises:
            RuntimeError: If client is not initialized
        """
        if not self.elastic_client:
            raise RuntimeError("Elasticsearch client not initialized")
        return self.elastic_client

    def _ensure_dshield_client(self) -> DShieldClient:
        """Ensure DShield client is initialized and return it.

        Returns:
            DShieldClient: The initialized client

        Raises:
            RuntimeError: If client is not initialized
        """
        if not self.dshield_client:
            raise RuntimeError("DShield client not initialized")
        return self.dshield_client

    def _ensure_data_processor(self) -> DataProcessor:
        """Ensure data processor is initialized and return it.

        Returns:
            DataProcessor: The initialized processor

        Raises:
            RuntimeError: If processor is not initialized
        """
        if not self.data_processor:
            raise RuntimeError("Data processor not initialized")
        return self.data_processor

    def _ensure_threat_intelligence_manager(self) -> ThreatIntelligenceManager:
        """Ensure threat intelligence manager is initialized and return it.

        Returns:
            ThreatIntelligenceManager: The initialized manager

        Raises:
            RuntimeError: If manager is not initialized
        """
        if not self.threat_intelligence_manager:
            raise RuntimeError("Threat intelligence manager not initialized")
        return self.threat_intelligence_manager

    def _ensure_campaign_tools(self) -> CampaignMCPTools:
        """Ensure campaign tools are initialized and return them.

        Returns:
            CampaignMCPTools: The initialized tools

        Raises:
            RuntimeError: If tools are not initialized
        """
        if not self.campaign_tools:
            raise RuntimeError("Campaign tools not initialized")
        return self.campaign_tools

    def _ensure_latex_tools(self) -> LaTeXTemplateTools:
        """Ensure LaTeX tools are initialized and return them.

        Returns:
            LaTeXTemplateTools: The initialized tools

        Raises:
            RuntimeError: If tools are not initialized
        """
        if not self.latex_tools:
            raise RuntimeError("LaTeX tools not initialized")
        return self.latex_tools

    def _is_tool_available(self, tool_name: str) -> bool:
        """Check if a tool is available based on feature flags."""
        feature_map = {
            'query_dshield_events': 'elasticsearch_queries',
            'query_dshield_aggregations': 'elasticsearch_queries',
            'stream_dshield_events': 'elasticsearch_queries',
            'stream_dshield_events_with_session_context': 'elasticsearch_queries',
            'query_dshield_attacks': 'elasticsearch_queries',
            'query_dshield_reputation': 'dshield_enrichment',
            'query_dshield_top_attackers': 'elasticsearch_queries',
            'query_dshield_geographic_data': 'elasticsearch_queries',
            'query_dshield_port_data': 'elasticsearch_queries',
            'get_dshield_statistics': 'elasticsearch_queries',
            'diagnose_data_availability': 'elasticsearch_queries',
            'enrich_ip_with_dshield': 'dshield_enrichment',
            'generate_attack_report': 'elasticsearch_queries',
            'query_events_by_ip': 'elasticsearch_queries',
            'get_security_summary': 'elasticsearch_queries',
            'test_elasticsearch_connection': 'elasticsearch_queries',
            'get_data_dictionary': 'data_dictionary',
            'analyze_campaign': 'campaign_analysis',
            'expand_campaign_indicators': 'campaign_analysis',
            'get_campaign_timeline': 'campaign_analysis',
            'compare_campaigns': 'campaign_analysis',
            'detect_ongoing_campaigns': 'campaign_analysis',
            'search_campaigns': 'campaign_analysis',
            'get_campaign_details': 'campaign_analysis',
            'generate_latex_document': 'latex_reports',
            'list_latex_templates': 'latex_reports',
            'get_latex_template_schema': 'latex_reports',
            'validate_latex_document_data': 'latex_reports',
            'enrich_ip_comprehensive': 'threat_intelligence',
            'enrich_domain_comprehensive': 'threat_intelligence',
            'correlate_threat_indicators': 'threat_intelligence',
            'get_threat_intelligence_summary': 'threat_intelligence',
            'detect_statistical_anomalies': 'statistical_analysis',
            'get_error_analytics': 'error_handling',
            'get_error_handling_status': 'error_handling',
            'get_elasticsearch_circuit_breaker_status': 'error_handling',
            'get_dshield_circuit_breaker_status': 'error_handling',
            'get_latex_circuit_breaker_status': 'error_handling',
        }
        feature = feature_map.get(tool_name)
        if not feature:
            return True  # Default: available if not mapped
        return self.feature_manager.is_feature_available(feature)

    async def _get_error_analytics(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Get error analytics and patterns from the error handler.

        Args:
            arguments: Tool arguments containing window_seconds (optional)

        Returns:
            List containing error analytics data.
        """
        try:
            window_seconds = arguments.get("window_seconds", 300)
            analytics = self.error_handler.get_error_analytics(window_seconds)

            return [
                {
                    "type": "error_analytics",
                    "data": analytics,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            ]
        except Exception as e:
            logger.error("Failed to get error analytics", error=str(e))
            return [
                self.error_handler.create_internal_error(f"Failed to get error analytics: {e!s}")
            ]

    async def _get_error_handling_status(self, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        """Get comprehensive error handling status and configuration.

        Args:
            arguments: Tool arguments containing include_analytics (optional)

        Returns:
            List containing error handling status and configuration.
        """
        try:
            include_analytics = arguments.get("include_analytics", True)

            status = {
                "error_handler_status": "active",
                "configuration": self.error_handler.get_enhanced_error_summary(),
                "timestamp": datetime.now(UTC).isoformat(),
            }

            if include_analytics:
                status["analytics"] = self.error_handler.get_error_analytics()

            return [{"type": "error_handling_status", "data": status}]
        except Exception as e:
            logger.error("Failed to get error handling status", error=str(e))
            return [
                self.error_handler.create_internal_error(
                    f"Failed to get error handling status: {e!s}"
                )
            ]

    async def _get_elasticsearch_circuit_breaker_status(
        self, arguments: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Get Elasticsearch circuit breaker status.

        Args:
            arguments: Tool arguments (unused)

        Returns:
            List containing Elasticsearch circuit breaker status.
        """
        try:
            if not hasattr(self, 'elasticsearch_client') or not self.elasticsearch_client:
                return [
                    {
                        "type": "error",
                        "error": {
                            "code": -32000,
                            "message": "Elasticsearch client not initialized",
                        },
                    }
                ]

            status = self.elasticsearch_client.get_circuit_breaker_status()

            return [
                {
                    "type": "elasticsearch_circuit_breaker_status",
                    "data": {"status": status, "timestamp": datetime.now(UTC).isoformat()},
                }
            ]
        except Exception as e:
            logger.error("Failed to get Elasticsearch circuit breaker status", error=str(e))
            return [
                self.error_handler.create_internal_error(
                    f"Failed to get Elasticsearch circuit breaker status: {e!s}"
                )
            ]

    async def _get_dshield_circuit_breaker_status(
        self, arguments: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Get DShield API circuit breaker status.

        Args:
            arguments: Tool arguments (unused)

        Returns:
            List containing DShield API circuit breaker status.
        """
        try:
            if not hasattr(self, 'dshield_client') or not self.dshield_client:
                return [
                    {
                        "type": "error",
                        "error": {"code": -32000, "message": "DShield client not initialized"},
                    }
                ]

            status = self.dshield_client.get_circuit_breaker_status()

            return [
                {
                    "type": "dshield_circuit_breaker_status",
                    "data": {"status": status, "timestamp": datetime.now(UTC).isoformat()},
                }
            ]
        except Exception as e:
            logger.error("Failed to get DShield circuit breaker status", error=str(e))
            return [
                self.error_handler.create_internal_error(
                    f"Failed to get DShield circuit breaker status: {e!s}"
                )
            ]

    async def _get_latex_circuit_breaker_status(
        self, arguments: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Get LaTeX compilation circuit breaker status.

        Args:
            arguments: Tool arguments (unused)

        Returns:
            List containing LaTeX compilation circuit breaker status.
        """
        try:
            if not hasattr(self, 'latex_tools') or not self.latex_tools:
                return [
                    {
                        "type": "error",
                        "error": {"code": -32000, "message": "LaTeX tools not initialized"},
                    }
                ]

            status = self.latex_tools.get_circuit_breaker_status()

            return [
                {
                    "type": "latex_circuit_breaker_status",
                    "data": {"status": status, "timestamp": datetime.now(UTC).isoformat()},
                }
            ]
        except Exception as e:
            logger.error("Failed to get LaTeX circuit breaker status", error=str(e))
            return [
                self.error_handler.create_internal_error(
                    f"Failed to get LaTeX circuit breaker status: {e!s}"
                )
            ]

    async def _tool_unavailable_response(self, tool_name: str) -> list[dict[str, Any]]:
        """Return a JSON-RPC error response for unavailable tool, and log to stderr."""
        feature_map = {
            'query_dshield_events': 'elasticsearch_queries',
            'query_dshield_aggregations': 'elasticsearch_queries',
            'stream_dshield_events': 'elasticsearch_queries',
            'stream_dshield_events_with_session_context': 'elasticsearch_queries',
            'query_dshield_attacks': 'elasticsearch_queries',
            'query_dshield_reputation': 'dshield_enrichment',
            'query_dshield_top_attackers': 'elasticsearch_queries',
            'query_dshield_geographic_data': 'elasticsearch_queries',
            'query_dshield_port_data': 'elasticsearch_queries',
            'get_dshield_statistics': 'elasticsearch_queries',
            'diagnose_data_availability': 'elasticsearch_queries',
            'enrich_ip_with_dshield': 'dshield_enrichment',
            'generate_attack_report': 'elasticsearch_queries',
            'query_events_by_ip': 'elasticsearch_queries',
            'get_security_summary': 'elasticsearch_queries',
            'test_elasticsearch_connection': 'elasticsearch_queries',
            'get_data_dictionary': 'data_dictionary',
            'analyze_campaign': 'campaign_analysis',
            'expand_campaign_indicators': 'campaign_analysis',
            'get_campaign_timeline': 'campaign_analysis',
            'compare_campaigns': 'campaign_analysis',
            'detect_ongoing_campaigns': 'campaign_analysis',
            'search_campaigns': 'campaign_analysis',
            'get_campaign_details': 'campaign_analysis',
            'generate_latex_document': 'latex_reports',
            'list_latex_templates': 'latex_reports',
            'get_latex_template_schema': 'latex_reports',
            'validate_latex_document_data': 'latex_reports',
            'enrich_ip_comprehensive': 'threat_intelligence',
            'enrich_domain_comprehensive': 'threat_intelligence',
            'correlate_threat_indicators': 'threat_intelligence',
            'get_threat_intelligence_summary': 'threat_intelligence',
            'detect_statistical_anomalies': 'statistical_analysis',
            'get_error_analytics': 'error_handling',
            'get_error_handling_status': 'error_handling',
            'get_elasticsearch_circuit_breaker_status': 'error_handling',
            'get_dshield_circuit_breaker_status': 'error_handling',
            'get_latex_circuit_breaker_status': 'error_handling',
        }
        feature = feature_map.get(tool_name, 'unknown')
        msg = f"Tool '{tool_name}' is currently unavailable due to missing or unhealthy "
        f"dependency: '{feature}'. Please try again later."
        # Log actionable user instructions to stderr
        print(
            f"[MCP SERVER] Tool '{tool_name}' unavailable. Dependency '{feature}' is not "
            f"healthy. Check service status, configuration, and logs for troubleshooting.",
            file=sys.stderr,
        )
        return [
            {
                "type": "error",
                "error": {
                    "code": -32000,  # Server-defined error
                    "message": msg,
                },
            }
        ]


async def main() -> None:
    """Start the DShield MCP server with graceful shutdown."""
    server = DShieldMCPServer()
    try:
        server.signal_handler.setup_handlers()
        await server.initialize()
        server._register_resources()
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
                                "description": "DShield SIEM data dictionary and analysis "
                                "guidelines",
                                "prompt": DataDictionary.get_initial_prompt(),
                            }
                        },
                    ),
                ),
            )
        # Wait for shutdown signal
        await server.signal_handler.wait_for_shutdown()
    except Exception as e:
        logger.error("Server error", error=str(e))
        raise
    finally:
        await server.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
