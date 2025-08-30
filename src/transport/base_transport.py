#!/usr/bin/env python3
"""Base transport class for DShield MCP Server.

This module provides the abstract base class for all transport implementations,
defining the interface that must be implemented by STDIO and TCP transports.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import structlog

logger = structlog.get_logger(__name__)


class BaseTransport(ABC):
    """Abstract base class for MCP transport implementations.
    
    This class defines the interface that all transport implementations must
    follow to ensure consistent behavior and MCP protocol compliance.
    
    Attributes:
        server: The MCP server instance
        config: Transport-specific configuration
        is_running: Whether the transport is currently running
    """
    
    def __init__(self, server: Any, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the base transport.
        
        Args:
            server: The MCP server instance
            config: Transport-specific configuration
        """
        self.server = server
        self.config = config or {}
        self.is_running = False
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    async def start(self) -> None:
        """Start the transport and begin accepting connections.
        
        This method should initialize the transport mechanism and begin
        accepting connections or processing messages.
        
        Raises:
            TransportError: If the transport fails to start
        """
        pass
    
    @abstractmethod
    async def stop(self) -> None:
        """Stop the transport and clean up resources.
        
        This method should gracefully shutdown the transport, close all
        connections, and clean up any resources.
        """
        pass
    
    @abstractmethod
    async def run(self) -> None:
        """Run the transport main loop.
        
        This method should implement the main transport loop, handling
        incoming connections and messages according to the MCP protocol.
        """
        pass
    
    @property
    @abstractmethod
    def transport_type(self) -> str:
        """Get the transport type identifier.
        
        Returns:
            String identifier for the transport type (e.g., 'stdio', 'tcp')
        """
        pass
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        return self.config.get(key, default)
    
    def set_config(self, key: str, value: Any) -> None:
        """Set a configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self.config[key] = value
    
    async def __aenter__(self) -> "BaseTransport":
        """Async context manager entry.
        
        Returns:
            Self for use in async with statements
        """
        await self.start()
        return self
    
    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit.
        
        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback
        """
        await self.stop()


class TransportError(Exception):
    """Exception raised for transport-related errors.
    
    This exception is raised when transport operations fail, such as
    connection failures, protocol errors, or resource issues.
    """
    
    def __init__(self, message: str, transport_type: str = "unknown", error_code: Optional[str] = None) -> None:
        """Initialize the transport error.
        
        Args:
            message: Error message
            transport_type: Type of transport that failed
            error_code: Optional error code for programmatic handling
        """
        super().__init__(message)
        self.transport_type = transport_type
        self.error_code = error_code
        self.message = message
    
    def __str__(self) -> str:
        """Get string representation of the error.
        
        Returns:
            Formatted error string
        """
        return f"TransportError[{self.transport_type}]: {self.message}"
