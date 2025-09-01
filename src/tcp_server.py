#!/usr/bin/env python3
"""TCP server implementation for DShield MCP Server.

This module provides the core TCP server implementation with full MCP protocol
support, authentication, security, and integration with the existing MCP server.
"""

import asyncio
import json
from typing import Any, Dict, Optional, Set

import structlog

from .connection_manager import ConnectionManager
from .mcp_error_handler import ErrorHandlingConfig, MCPErrorHandler
from .tcp_auth import TCPAuthenticator
from .tcp_security import SecurityViolation, TCPSecurityManager
from .transport.tcp_transport import TCPConnection

logger = structlog.get_logger(__name__)


class MCPServerAdapter:
    """Adapter to integrate TCP transport with MCP server.
    
    This class bridges the gap between the TCP transport layer and the
    existing MCP server, handling protocol translation and message routing.
    """

    def __init__(self, mcp_server: Any, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the MCP server adapter.
        
        Args:
            mcp_server: The MCP server instance
            config: Adapter configuration

        """
        self.mcp_server = mcp_server
        self.config = config or {}
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")

        # Initialize error handler
        error_config = ErrorHandlingConfig()
        self.error_handler = MCPErrorHandler(error_config)

        # Track active sessions
        self.active_sessions: Dict[str, Dict[str, Any]] = {}

    async def process_mcp_message(self, connection: TCPConnection,
                                message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process an MCP protocol message.
        
        Args:
            connection: The TCP connection
            message: The MCP message to process
            
        Returns:
            Response message if applicable, None for notifications

        """
        try:
            # Check if this is an authentication message
            if message.get("method") == "authenticate":
                return await self._handle_authentication(connection, message)

            # Check if connection is authenticated
            if not connection.is_authenticated:
                return self._create_error_response(
                    message.get("id"),
                    -32001,  # RESOURCE_NOT_FOUND
                    "Authentication required",
                    {"required": "authenticate"},
                )

            # Route message to appropriate MCP handler
            return await self._route_mcp_message(connection, message)

        except Exception as e:
            self.logger.error("Error processing MCP message",
                            client_address=connection.client_address,
                            error=str(e))
            return self._create_error_response(
                message.get("id"),
                -32603,  # INTERNAL_ERROR
                "Internal server error",
                {"error": str(e)},
            )

    async def _handle_authentication(self, connection: TCPConnection,
                                   message: Dict[str, Any]) -> Dict[str, Any]:
        """Handle authentication message.
        
        Args:
            connection: The TCP connection
            message: Authentication message
            
        Returns:
            Authentication response

        """
        try:
            # This would integrate with the TCPAuthenticator
            # For now, we'll implement a simple authentication check
            api_key = message.get("params", {}).get("api_key")

            if not api_key:
                return self._create_error_response(
                    message.get("id"),
                    -32602,  # INVALID_PARAMS
                    "API key is required",
                    {"missing_field": "api_key"},
                )

            # Simple validation (would be replaced with real authentication)
            if api_key == "test-key":  # Placeholder
                connection.is_authenticated = True
                connection.api_key = api_key

                return {
                    "jsonrpc": "2.0",
                    "id": message.get("id"),
                    "result": {
                        "authenticated": True,
                        "permissions": {
                            "elastic_write_back": False,
                            "max_query_results": 1000,
                        },
                    },
                }
            return self._create_error_response(
                message.get("id"),
                -32001,  # RESOURCE_NOT_FOUND
                "Invalid API key",
                {"api_key": api_key[:8] + "..."},
            )

        except Exception as e:
            return self._create_error_response(
                message.get("id"),
                -32603,  # INTERNAL_ERROR
                "Authentication failed",
                {"error": str(e)},
            )

    async def _route_mcp_message(self, connection: TCPConnection,
                               message: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Route MCP message to appropriate handler.
        
        Args:
            connection: The TCP connection
            message: The MCP message
            
        Returns:
            Response message if applicable

        """
        method = message.get("method")
        message_id = message.get("id")
        params = message.get("params", {})

        try:
            # Handle different MCP methods
            if method == "initialize":
                return await self._handle_initialize(connection, message_id, params)
            if method == "initialized":
                return await self._handle_initialized(connection, message_id, params)
            if method == "tools/list":
                return await self._handle_tools_list(connection, message_id, params)
            if method == "tools/call":
                return await self._handle_tools_call(connection, message_id, params)
            if method == "resources/list":
                return await self._handle_resources_list(connection, message_id, params)
            if method == "resources/read":
                return await self._handle_resources_read(connection, message_id, params)
            if method == "prompts/list":
                return await self._handle_prompts_list(connection, message_id, params)
            if method == "prompts/get":
                return await self._handle_prompts_get(connection, message_id, params)
            return self._create_error_response(
                message_id,
                -32601,  # METHOD_NOT_FOUND
                f"Method '{method}' not found",
                {"method": method},
            )

        except Exception as e:
            self.logger.error("Error routing MCP message",
                            method=method,
                            client_address=connection.client_address,
                            error=str(e))
            return self._create_error_response(
                message_id,
                -32603,  # INTERNAL_ERROR
                "Error processing request",
                {"error": str(e)},
            )

    async def _handle_initialize(self, connection: TCPConnection,
                               message_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP initialize method.
        
        Args:
            connection: The TCP connection
            message_id: Message ID
            params: Initialize parameters
            
        Returns:
            Initialize response

        """
        # Get server capabilities
        capabilities = self.mcp_server.get_capabilities()

        return {
            "jsonrpc": "2.0",
            "id": message_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": capabilities,
                "serverInfo": {
                    "name": "dshield-elastic-mcp",
                    "version": "1.0.0",
                },
            },
        }

    async def _handle_initialized(self, connection: TCPConnection,
                                message_id: Any, params: Dict[str, Any]) -> None:
        """Handle MCP initialized notification.
        
        Args:
            connection: The TCP connection
            message_id: Message ID (should be None for notifications)
            params: Initialized parameters

        """
        # Mark connection as initialized
        connection.is_initialized = True
        self.logger.info("MCP connection initialized",
                        client_address=connection.client_address)

    async def _handle_tools_list(self, connection: TCPConnection,
                               message_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP tools/list method.
        
        Args:
            connection: The TCP connection
            message_id: Message ID
            params: List parameters
            
        Returns:
            Tools list response

        """
        # Get available tools from the MCP server
        tools = self.mcp_server.get_available_tools()

        return {
            "jsonrpc": "2.0",
            "id": message_id,
            "result": {
                "tools": tools,
            },
        }

    async def _handle_tools_call(self, connection: TCPConnection,
                               message_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP tools/call method.
        
        Args:
            connection: The TCP connection
            message_id: Message ID
            params: Call parameters
            
        Returns:
            Tool call response

        """
        tool_name = params.get("name")
        tool_arguments = params.get("arguments", {})

        if not tool_name:
            return self._create_error_response(
                message_id,
                -32602,  # INVALID_PARAMS
                "Tool name is required",
                {"missing_field": "name"},
            )

        try:
            # Call the tool through the MCP server
            result = await self.mcp_server.call_tool(tool_name, tool_arguments)

            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2),
                        },
                    ],
                },
            }

        except Exception as e:
            return self._create_error_response(
                message_id,
                -32603,  # INTERNAL_ERROR
                f"Tool execution failed: {e}",
                {"tool": tool_name, "error": str(e)},
            )

    async def _handle_resources_list(self, connection: TCPConnection,
                                   message_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP resources/list method.
        
        Args:
            connection: The TCP connection
            message_id: Message ID
            params: List parameters
            
        Returns:
            Resources list response

        """
        # Get available resources from the MCP server
        resources = self.mcp_server.get_available_resources()

        return {
            "jsonrpc": "2.0",
            "id": message_id,
            "result": {
                "resources": resources,
            },
        }

    async def _handle_resources_read(self, connection: TCPConnection,
                                   message_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP resources/read method.
        
        Args:
            connection: The TCP connection
            message_id: Message ID
            params: Read parameters
            
        Returns:
            Resource read response

        """
        resource_uri = params.get("uri")

        if not resource_uri:
            return self._create_error_response(
                message_id,
                -32602,  # INVALID_PARAMS
                "Resource URI is required",
                {"missing_field": "uri"},
            )

        try:
            # Read the resource through the MCP server
            content = await self.mcp_server.read_resource(resource_uri)

            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "result": {
                    "contents": content,
                },
            }

        except Exception as e:
            return self._create_error_response(
                message_id,
                -32603,  # INTERNAL_ERROR
                f"Resource read failed: {e}",
                {"uri": resource_uri, "error": str(e)},
            )

    async def _handle_prompts_list(self, connection: TCPConnection,
                                 message_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP prompts/list method.
        
        Args:
            connection: The TCP connection
            message_id: Message ID
            params: List parameters
            
        Returns:
            Prompts list response

        """
        # Get available prompts from the MCP server
        prompts = self.mcp_server.get_available_prompts()

        return {
            "jsonrpc": "2.0",
            "id": message_id,
            "result": {
                "prompts": prompts,
            },
        }

    async def _handle_prompts_get(self, connection: TCPConnection,
                                message_id: Any, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP prompts/get method.
        
        Args:
            connection: The TCP connection
            message_id: Message ID
            params: Get parameters
            
        Returns:
            Prompt get response

        """
        prompt_name = params.get("name")
        prompt_arguments = params.get("arguments", {})

        if not prompt_name:
            return self._create_error_response(
                message_id,
                -32602,  # INVALID_PARAMS
                "Prompt name is required",
                {"missing_field": "name"},
            )

        try:
            # Get the prompt through the MCP server
            prompt = await self.mcp_server.get_prompt(prompt_name, prompt_arguments)

            return {
                "jsonrpc": "2.0",
                "id": message_id,
                "result": {
                    "description": prompt.get("description", ""),
                    "messages": prompt.get("messages", []),
                },
            }

        except Exception as e:
            return self._create_error_response(
                message_id,
                -32603,  # INTERNAL_ERROR
                f"Prompt get failed: {e}",
                {"name": prompt_name, "error": str(e)},
            )

    def _create_error_response(self, message_id: Any, error_code: int,
                             error_message: str, error_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a JSON-RPC error response.
        
        Args:
            message_id: Message ID
            error_code: Error code
            error_message: Error message
            error_data: Additional error data
            
        Returns:
            Error response dictionary

        """
        error_response = {
            "jsonrpc": "2.0",
            "id": message_id,
            "error": {
                "code": error_code,
                "message": error_message,
            },
        }

        if error_data:
            error_response["error"]["data"] = error_data

        return error_response


class EnhancedTCPServer:
    """Enhanced TCP server with full MCP protocol support.
    
    This class provides a complete TCP server implementation that integrates
    with the existing MCP server, providing authentication, security, and
    full protocol compliance.
    """

    def __init__(self, mcp_server: Any, config: Optional[Dict[str, Any]] = None) -> None:
        """Initialize the enhanced TCP server.
        
        Args:
            mcp_server: The MCP server instance
            config: Server configuration

        """
        self.mcp_server = mcp_server
        self.config = config or {}
        self.logger = structlog.get_logger(f"{__name__}.{self.__class__.__name__}")

        # Initialize components
        self.connection_manager = ConnectionManager(self.config.get("connection_management", {}))
        self.security_manager = TCPSecurityManager(self.config.get("security", {}))
        self.authenticator = TCPAuthenticator(
            self.connection_manager,
            MCPErrorHandler(ErrorHandlingConfig()),
            self.config.get("authentication", {}),
        )
        self.mcp_adapter = MCPServerAdapter(mcp_server, self.config.get("mcp_adapter", {}))

        # Server state
        self.is_running = False
        self.server_socket = None
        self.connections: Set[TCPConnection] = set()
        self._cleanup_task = None

    async def start(self) -> None:
        """Start the enhanced TCP server.
        
        Raises:
            Exception: If server fails to start

        """
        try:
            print(f"DEBUG: EnhancedTCPServer.start() called on port {self.config.get('port')}")
            port = self.config.get("port", 3000)
            bind_address = self.config.get("bind_address", "127.0.0.1")
            max_connections = self.config.get("max_connections", 10)

            self.logger.info("Starting enhanced TCP server",
                           port=port, bind_address=bind_address, max_connections=max_connections)

            # Create TCP server
            self.server_socket = await asyncio.start_server(
                self._handle_connection,
                bind_address,
                port,
                limit=max_connections,
            )

            # Start cleanup task
            self._cleanup_task = asyncio.create_task(self._cleanup_expired_connections())

            self.is_running = True
            self.logger.info("Enhanced TCP server started successfully",
                           port=port, bind_address=bind_address)

        except Exception as e:
            print(f"ERROR starting server: {e}")
            import traceback
            self.logger.error("Failed to start enhanced TCP server", error=str(e), traceback=traceback.format_exc())
            raise  # Re-raise to see the error

    async def stop(self) -> None:
        """Stop the enhanced TCP server.
        
        Closes all connections and cleans up resources.
        """
        try:
            self.logger.info("Stopping enhanced TCP server")

            # Cancel cleanup task
            if self._cleanup_task:
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass

            # Close all connections
            for connection in list(self.connections):
                await connection.close()
            self.connections.clear()

            # Close server socket
            if self.server_socket:
                self.server_socket.close()
                await self.server_socket.wait_closed()

            self.is_running = False
            self.logger.info("Enhanced TCP server stopped successfully")

        except Exception as e:
            self.logger.error("Error stopping enhanced TCP server", error=str(e))

    async def _handle_connection(self, reader: asyncio.StreamReader,
                               writer: asyncio.StreamWriter) -> None:
        """Handle a new TCP connection.
        
        Args:
            reader: StreamReader for reading from the connection
            writer: StreamWriter for writing to the connection

        """
        client_address = writer.get_extra_info("peername")
        connection = None

        try:
            self.logger.info("New TCP connection", client_address=client_address)

            # Check connection attempt limits
            if not self.security_manager.record_connection_attempt(str(client_address)):
                self.logger.warning("Connection attempt blocked", client_address=client_address)
                writer.close()
                await writer.wait_closed()
                return

            # Create connection object
            connection = TCPConnection(reader, writer, client_address)
            self.connections.add(connection)
            self.connection_manager.add_connection(connection)

            # Handle the connection
            await self._process_connection(connection)

        except Exception as e:
            self.logger.error("Error handling TCP connection",
                            client_address=client_address, error=str(e))
        finally:
            # Clean up connection
            if connection:
                self.connections.discard(connection)
                self.connection_manager.remove_connection(connection)
                await connection.close()
            self.logger.info("TCP connection closed", client_address=client_address)

    async def _process_connection(self, connection: TCPConnection) -> None:
        """Process messages from a TCP connection.
        
        Args:
            connection: The TCP connection to process

        """
        try:
            while True:
                # Read message length (first 4 bytes)
                length_data = await connection.reader.readexactly(4)
                if not length_data:
                    break

                message_length = int.from_bytes(length_data, byteorder="big")

                # Read message data
                message_data = await connection.reader.readexactly(message_length)
                if not message_data:
                    break

                # Parse JSON message
                try:
                    message = json.loads(message_data.decode("utf-8"))
                    connection.update_activity()

                    # Validate message with security manager
                    validated_message = self.security_manager.validate_message(
                        message, str(connection.client_address),
                    )

                    # Process message through MCP adapter
                    response = await self.mcp_adapter.process_mcp_message(
                        connection, validated_message,
                    )

                    # Send response if applicable
                    if response:
                        await self._send_response(connection, response)

                except SecurityViolation as e:
                    await self._send_error_response(connection, e.violation_type, str(e))
                except json.JSONDecodeError as e:
                    await self._send_error_response(connection, "INVALID_JSON", f"Invalid JSON: {e}")
                except Exception as e:
                    await self._send_error_response(connection, "INTERNAL_ERROR", f"Internal error: {e}")

        except asyncio.IncompleteReadError:
            # Connection closed by client
            pass
        except Exception as e:
            self.logger.error("Error processing TCP connection",
                            client_address=connection.client_address, error=str(e))

    async def _send_response(self, connection: TCPConnection, response: Dict[str, Any]) -> None:
        """Send a response to a TCP connection.
        
        Args:
            connection: The TCP connection
            response: The response to send

        """
        try:
            message_data = json.dumps(response).encode("utf-8")
            message_length = len(message_data)

            # Send message length
            connection.writer.write(message_length.to_bytes(4, byteorder="big"))
            # Send message data
            connection.writer.write(message_data)
            await connection.writer.drain()

        except Exception as e:
            self.logger.error("Error sending TCP response",
                            client_address=connection.client_address, error=str(e))

    async def _send_error_response(self, connection: TCPConnection,
                                 error_type: str, error_message: str) -> None:
        """Send an error response to a TCP connection.
        
        Args:
            connection: The TCP connection
            error_type: Error type
            error_message: Error message

        """
        error_response = {
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32603,  # INTERNAL_ERROR
                "message": error_message,
                "data": {"error_type": error_type},
            },
        }
        await self._send_response(connection, error_response)

    async def _cleanup_expired_connections(self) -> None:
        """Clean up expired connections and security data.
        
        Runs periodically to remove expired connections and clean up security data.
        """
        timeout_seconds = self.config.get("connection_timeout_seconds", 300)

        while self.is_running:
            try:
                await asyncio.sleep(60)  # Check every minute

                # Clean up expired connections
                expired_connections = [
                    conn for conn in self.connections
                    if conn.is_expired(timeout_seconds)
                ]

                for connection in expired_connections:
                    self.logger.info("Closing expired connection",
                                   client_address=connection.client_address)
                    self.connections.discard(connection)
                    self.connection_manager.remove_connection(connection)
                    await connection.close()

                # Clean up security data
                self.security_manager.cleanup_expired_data()

                # Clean up expired API keys
                self.connection_manager.cleanup_expired_keys()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error("Error in cleanup task", error=str(e))

    def get_server_statistics(self) -> Dict[str, Any]:
        """Get server statistics.
        
        Returns:
            Dictionary of server statistics

        """
        return {
            "server": {
                "is_running": self.is_running,
                "port": self.config.get("port", 3000),
                "bind_address": self.config.get("bind_address", "127.0.0.1"),
                "max_connections": self.config.get("max_connections", 10),
            },
            "connections": {
                "active": len(self.connections),
                "total": len(self.connections),
            },
            "connection_manager": self.connection_manager.get_statistics(),
            "security": self.security_manager.get_security_statistics(),
            "authentication": self.authenticator.get_statistics(),
        }
