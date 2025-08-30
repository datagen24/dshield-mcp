"""Transport layer for DShield MCP Server.

This module provides the transport abstraction layer for the DShield MCP server,
supporting both STDIO and TCP transport mechanisms while maintaining full MCP
protocol compliance.

Classes:
    BaseTransport: Abstract base class for all transport implementations
    STDIOTransport: STDIO-based transport implementation
    TCPTransport: TCP socket-based transport implementation
    TransportManager: Manages transport selection and lifecycle
"""

from .base_transport import BaseTransport
from .stdio_transport import STDIOTransport
from .tcp_transport import TCPTransport
from .transport_manager import TransportManager

__all__ = [
    "BaseTransport",
    "STDIOTransport", 
    "TCPTransport",
    "TransportManager"
]
