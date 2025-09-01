#!/usr/bin/env python3
"""Transport manager for DShield MCP Server.

This module provides the transport manager that handles transport selection,
lifecycle management, and coordination between different transport types.
"""

import os
from typing import Any, Dict, Optional, Type

import psutil
import structlog

from .base_transport import BaseTransport, TransportError
from .stdio_transport import STDIOTransport
from .tcp_transport import TCPTransport

logger = structlog.get_logger(__name__)


class TransportManager:
    """Manages transport selection and lifecycle for the MCP server.
    
    This class handles the selection of appropriate transport mechanisms
    based on configuration and execution context, managing the lifecycle
    of transport instances.
    
    Attributes:
        server: The MCP server instance
        config: Transport configuration
        current_transport: Currently active transport
        transport_registry: Registry of available transport types

    """

    def __init__(self, server: Any, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the transport manager.
        
        Args:
            server: The MCP server instance
            config: Transport configuration

        """
        self.server = server
        self.config = config or {}
        self.current_transport: Optional[BaseTransport] = None

        # Registry of available transport types
        self.transport_registry: Dict[str, Type[BaseTransport]] = {
            "stdio": STDIOTransport,
            "tcp": TCPTransport,
        }

        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")

    def detect_transport_mode(self) -> str:
        """Detect the appropriate transport mode based on execution context.
        
        This method implements the transport detection logic:
        1. Check if TUI is the parent process (process parent detection)
        2. Fall back to command-line flag detection
        3. Default to STDIO mode for safety
        
        Returns:
            Transport mode identifier ('stdio' or 'tcp')

        """
        print("DEBUG: detect_transport_mode called")
        print(f"DEBUG: DSHIELD_TUI_MODE = {os.getenv('DSHIELD_TUI_MODE')}")
        print(f"DEBUG: DSHIELD_MCP_TCP_MODE = {os.getenv('DSHIELD_MCP_TCP_MODE')}")

        # Check if TUI is the parent process
        if self._is_tui_parent():
            print("DEBUG: TUI parent detected, using TCP transport")
            self.logger.info("Detected TUI parent process, using TCP transport")
            return "tcp"

        # Check command-line flags
        if self._has_tcp_flag():
            self.logger.info("Detected TCP flag, using TCP transport")
            return "tcp"

        # Check environment variable
        if os.getenv("DSHIELD_MCP_TCP_MODE", "").lower() in ("true", "1", "yes"):
            print("DEBUG: TCP mode environment variable detected")
            self.logger.info("Detected TCP mode environment variable, using TCP transport")
            return "tcp"

        # Default to STDIO mode
        print("DEBUG: Defaulting to STDIO transport mode")
        self.logger.info("Using default STDIO transport mode")
        return "stdio"

    def _is_tui_parent(self) -> bool:
        """Check if TUI is the parent process using multiple detection strategies.
        
        Detection order:
        1. Check environment variable DSHIELD_TUI_MODE
        2. Check parent process name/cmdline for TUI indicators
        3. Check for TUI-specific markers in command line
        4. Default to STDIO if uncertain
        
        Returns:
            True if TUI appears to be the parent process

        """
        # Strategy 1: Check environment variable first (most reliable)
        if os.getenv("DSHIELD_TUI_MODE", "").lower() in ("true", "1", "yes"):
            self.logger.debug("TUI detection: Environment variable DSHIELD_TUI_MODE is set")
            return True

        # Strategy 2: Check parent process information
        try:
            current_process = psutil.Process()
            parent_process = current_process.parent()

            if parent_process:
                parent_pid = parent_process.pid
                parent_name = parent_process.name().lower()
                parent_cmdline = " ".join(parent_process.cmdline()).lower()

                self.logger.debug("TUI detection: Parent process info",
                                parent_pid=parent_pid,
                                parent_name=parent_name,
                                parent_cmdline=parent_cmdline)

                # Strategy 3: Check for TUI-specific command line markers
                tui_indicators = [
                    "tui", "textual", "rich", "curses",
                    "dshield-mcp-tui", "mcp-tui", "tui_launcher.py",
                ]

                for indicator in tui_indicators:
                    if indicator in parent_name or indicator in parent_cmdline:
                        self.logger.debug("TUI detection: Found TUI indicator in parent",
                                        indicator=indicator,
                                        found_in_name=indicator in parent_name,
                                        found_in_cmdline=indicator in parent_cmdline)
                        return True

                # Strategy 4: Check if parent is running in a terminal multiplexer
                terminal_multiplexers = ["tmux", "screen", "byobu"]
                for mux in terminal_multiplexers:
                    if mux in parent_cmdline:
                        self.logger.debug("TUI detection: Found terminal multiplexer",
                                        multiplexer=mux)
                        return True

                self.logger.debug("TUI detection: No TUI indicators found in parent process")
            else:
                self.logger.debug("TUI detection: No parent process found")

        except psutil.NoSuchProcess:
            self.logger.debug("TUI detection: Parent process no longer exists")
        except psutil.AccessDenied:
            self.logger.debug("TUI detection: Access denied to parent process")
        except Exception as e:
            self.logger.debug("TUI detection: Error checking parent process", error=str(e))

        # Strategy 5: Fallback - check current process command line for TUI markers
        try:
            current_cmdline = " ".join(psutil.Process().cmdline()).lower()
            tui_launcher_indicators = ["tui_launcher.py", "src.tui_launcher", "-m src.tui_launcher"]
            for indicator in tui_launcher_indicators:
                if indicator in current_cmdline:
                    self.logger.debug("TUI detection: Found TUI launcher indicator in current process",
                                    indicator=indicator)
                    return True
        except Exception as e:
            self.logger.debug("TUI detection: Error checking current process", error=str(e))

        self.logger.debug("TUI detection: No TUI indicators found, defaulting to STDIO")
        return False

    def _has_tcp_flag(self) -> bool:
        """Check for TCP-related command-line flags.
        
        Returns:
            True if TCP flags are present

        """
        import sys

        tcp_flags = ["--tcp", "--tcp-mode", "--network", "--tui-managed"]

        for flag in tcp_flags:
            if flag in sys.argv:
                return True

        return False

    def create_transport(self, transport_type: Optional[str] = None) -> BaseTransport:
        """Create a transport instance.
        
        Args:
            transport_type: Type of transport to create (auto-detected if None)
            
        Returns:
            Transport instance
            
        Raises:
            TransportError: If transport type is not supported

        """
        if transport_type is None:
            transport_type = self.detect_transport_mode()

        if transport_type not in self.transport_registry:
            raise TransportError(f"Unsupported transport type: {transport_type}")

        transport_class = self.transport_registry[transport_type]

        # Get transport-specific configuration
        transport_config = self._get_transport_config(transport_type)

        self.logger.info("Creating transport",
                        transport_type=transport_type, config=transport_config)

        return transport_class(self.server, transport_config)

    def _get_transport_config(self, transport_type: str) -> Dict[str, Any]:
        """Get configuration for a specific transport type.
        
        Args:
            transport_type: Type of transport
            
        Returns:
            Transport-specific configuration

        """
        config = {}

        if transport_type == "tcp":
            # Get TCP-specific configuration
            tcp_config = self.config.get("tcp_transport", {})
            config.update({
                "port": tcp_config.get("port", 3000),
                "bind_address": tcp_config.get("bind_address", "127.0.0.1"),
                "max_connections": tcp_config.get("max_connections", 10),
                "connection_timeout_seconds": tcp_config.get("connection_timeout_seconds", 300),
                "api_key_management": tcp_config.get("api_key_management", {}),
                "permissions": tcp_config.get("permissions", {}),
            })

        elif transport_type == "stdio":
            # STDIO doesn't need much configuration
            config.update({
                "buffer_size": self.config.get("stdio", {}).get("buffer_size", 8192),
            })

        return config

    async def start_transport(self, transport_type: Optional[str] = None) -> BaseTransport:
        """Start a transport instance.
        
        Args:
            transport_type: Type of transport to start (auto-detected if None)
            
        Returns:
            Started transport instance
            
        Raises:
            TransportError: If transport fails to start

        """
        if self.current_transport is not None:
            raise TransportError("Transport is already running")

        self.current_transport = self.create_transport(transport_type)

        try:
            await self.current_transport.start()
            self.logger.info("Transport started successfully",
                           transport_type=self.current_transport.transport_type)
            return self.current_transport

        except Exception as e:
            self.current_transport = None
            raise TransportError(f"Failed to start transport: {e}")

    async def stop_transport(self) -> None:
        """Stop the current transport.
        
        Raises:
            TransportError: If no transport is running

        """
        if self.current_transport is None:
            raise TransportError("No transport is currently running")

        try:
            await self.current_transport.stop()
            self.logger.info("Transport stopped successfully",
                           transport_type=self.current_transport.transport_type)
        finally:
            self.current_transport = None

    async def restart_transport(self, transport_type: Optional[str] = None) -> BaseTransport:
        """Restart the transport with optional type change.
        
        Args:
            transport_type: New transport type (keeps current if None)
            
        Returns:
            New transport instance
            
        Raises:
            TransportError: If restart fails

        """
        self.logger.info("Restarting transport",
                        current_type=self.current_transport.transport_type if self.current_transport else None,
                        new_type=transport_type)

        # Stop current transport
        if self.current_transport is not None:
            await self.stop_transport()

        # Start new transport
        return await self.start_transport(transport_type)

    def get_current_transport(self) -> Optional[BaseTransport]:
        """Get the currently active transport.
        
        Returns:
            Current transport instance or None

        """
        return self.current_transport

    def get_transport_info(self) -> Dict[str, Any]:
        """Get information about the current transport.
        
        Returns:
            Transport information dictionary

        """
        if self.current_transport is None:
            return {"status": "not_running"}

        info = {
            "status": "running",
            "type": self.current_transport.transport_type,
            "is_running": self.current_transport.is_running,
        }

        # Add transport-specific information
        if self.current_transport.transport_type == "tcp":
            tcp_transport = self.current_transport
            # Type check to ensure we have the right transport type
            if hasattr(tcp_transport, "get_connection_count") and hasattr(tcp_transport, "get_connections_info"):
                info.update({
                    "connection_count": tcp_transport.get_connection_count(),
                    "connections": tcp_transport.get_connections_info(),
                })

        return info

    async def __aenter__(self) -> "TransportManager":
        """Async context manager entry.
        
        Returns:
            Self for use in async with statements

        """
        await self.start_transport()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit.
        
        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback

        """
        await self.stop_transport()
