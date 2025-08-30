#!/usr/bin/env python3
"""Server launcher for DShield MCP Server.

This module provides the main entry point for the DShield MCP server,
supporting both STDIO and TCP transport modes with automatic detection.
"""

import asyncio
import os
import sys
from typing import Any, Optional
import structlog

from .transport.transport_manager import TransportManager
from .tcp_server import EnhancedTCPServer
from .user_config import get_user_config

logger = structlog.get_logger(__name__)


class DShieldServerLauncher:
    """Launcher for the DShield MCP server with transport selection.
    
    This class handles the initialization and startup of the MCP server
    with automatic transport mode detection and configuration.
    """
    
    def __init__(self, config_path: Optional[str] = None) -> None:
        """Initialize the server launcher.
        
        Args:
            config_path: Optional path to configuration file
        """
        self.config_path = config_path
        self.user_config = get_user_config(config_path)
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")
        
        # Server components
        self.mcp_server = None
        self.transport_manager = None
        self.tcp_server = None
    
    async def initialize_server(self) -> Any:
        """Initialize the MCP server.
        
        Returns:
            Initialized MCP server instance
        """
        # Import here to avoid circular imports
        from mcp_server import DShieldMCPServer
        
        self.logger.info("Initializing DShield MCP server")
        
        # Create and initialize the MCP server
        self.mcp_server = DShieldMCPServer()
        self.mcp_server.signal_handler.setup_handlers()
        await self.mcp_server.initialize()
        self.mcp_server._register_resources()
        
        self.logger.info("DShield MCP server initialized successfully")
        return self.mcp_server
    
    async def start_stdio_mode(self) -> None:
        """Start the server in STDIO mode.
        
        This is the traditional MCP server mode using stdin/stdout.
        """
        from mcp.server.stdio import stdio_server
        from mcp.server.models import InitializationOptions
        from mcp.server import NotificationOptions
        from src.data_dictionary import DataDictionary
        
        self.logger.info("Starting server in STDIO mode")
        
        # Run the server with STDIO transport
        async with stdio_server() as (read_stream, write_stream):
            await self.mcp_server.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="dshield-elastic-mcp",
                    server_version="1.0.0",
                    capabilities=self.mcp_server.server.get_capabilities(
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
    
    async def start_tcp_mode(self) -> None:
        """Start the server in TCP mode.
        
        This mode provides network-based access with authentication and security.
        """
        self.logger.info("Starting server in TCP mode")
        
        # Get TCP configuration
        tcp_config = {
            "port": self.user_config.tcp_transport_settings.port,
            "bind_address": self.user_config.tcp_transport_settings.bind_address,
            "max_connections": self.user_config.tcp_transport_settings.max_connections,
            "connection_timeout_seconds": self.user_config.tcp_transport_settings.connection_timeout_seconds,
            "connection_management": {
                "api_key_management": self.user_config.tcp_transport_settings.api_key_management,
                "permissions": self.user_config.tcp_transport_settings.permissions
            },
            "security": {
                "global_rate_limit": 1000,
                "global_burst_limit": 100,
                "client_rate_limit": self.user_config.tcp_transport_settings.api_key_management.get("rate_limit_per_key", 60),
                "client_burst_limit": 10,
                "abuse_threshold": 10,
                "block_duration_seconds": 3600,
                "max_connection_attempts": 5,
                "connection_window_seconds": 300,
                "input_validation": {
                    "max_message_size": 1048576,  # 1MB
                    "max_field_length": 10000,
                    "allowed_methods": [
                        "initialize", "initialized", "tools/list", "tools/call",
                        "resources/list", "resources/read", "prompts/list", "prompts/get",
                        "authenticate"
                    ]
                }
            },
            "authentication": {
                "session_timeout_seconds": 3600,
                "max_sessions_per_key": 5
            }
        }
        
        # Create and start the enhanced TCP server
        self.tcp_server = EnhancedTCPServer(self.mcp_server, tcp_config)
        await self.tcp_server.start()
        
        self.logger.info("TCP server started successfully",
                        port=tcp_config["port"],
                        bind_address=tcp_config["bind_address"])
        
        # Keep the server running
        try:
            # Wait for shutdown signal
            await self.mcp_server.signal_handler.wait_for_shutdown()
        finally:
            await self.tcp_server.stop()
    
    async def run(self) -> None:
        """Run the server with automatic transport detection.
        
        This method detects the appropriate transport mode and starts the server.
        """
        try:
            # Initialize the MCP server
            await self.initialize_server()
            
            # Create transport manager
            self.transport_manager = TransportManager(
                self.mcp_server,
                {
                    "tcp_transport": {
                        "port": self.user_config.tcp_transport_settings.port,
                        "bind_address": self.user_config.tcp_transport_settings.bind_address,
                        "max_connections": self.user_config.tcp_transport_settings.max_connections,
                        "connection_timeout_seconds": self.user_config.tcp_transport_settings.connection_timeout_seconds,
                        "api_key_management": self.user_config.tcp_transport_settings.api_key_management,
                        "permissions": self.user_config.tcp_transport_settings.permissions
                    }
                }
            )
            
            # Detect transport mode
            transport_mode = self.transport_manager.detect_transport_mode()
            
            self.logger.info("Detected transport mode", mode=transport_mode)
            
            # Start server in appropriate mode
            if transport_mode == "tcp":
                await self.start_tcp_mode()
            else:
                await self.start_stdio_mode()
                
        except Exception as e:
            self.logger.error("Server error", error=str(e))
            raise
        finally:
            await self.cleanup()
    
    async def cleanup(self) -> None:
        """Clean up server resources.
        
        Performs graceful shutdown and cleanup of all server components.
        """
        try:
            self.logger.info("Cleaning up server resources")
            
            # Stop TCP server if running
            if self.tcp_server:
                await self.tcp_server.stop()
            
            # Cleanup MCP server
            if self.mcp_server:
                await self.mcp_server.cleanup()
            
            self.logger.info("Server cleanup completed")
            
        except Exception as e:
            self.logger.error("Error during cleanup", error=str(e))


async def main() -> None:
    """Main entry point for the DShield MCP server.
    
    This function serves as the main entry point, handling command-line
    arguments and starting the server with appropriate configuration.
    """
    # Configure logging
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
    
    try:
        # Get configuration path from command line or environment
        config_path = None
        if len(sys.argv) > 1:
            config_path = sys.argv[1]
        elif os.getenv("DSHIELD_MCP_CONFIG"):
            config_path = os.getenv("DSHIELD_MCP_CONFIG")
        
        # Create and run the server launcher
        launcher = DShieldServerLauncher(config_path)
        await launcher.run()
        
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error("Server failed to start", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
