"""
MCP Protocol Compliance and JSON-RPC 2.0 Validation Tests

This test suite validates that our DShield MCP server properly implements
the Model Context Protocol specification and JSON-RPC 2.0 standard.
"""

import pytest
from unittest.mock import MagicMock

from mcp_server import DShieldMCPServer
from src.mcp_error_handler import MCPErrorHandler, ErrorHandlingConfig


class TestMCPProtocolCompliance:
    """Test MCP protocol compliance and capability negotiation."""

    @pytest.mark.asyncio
    async def test_server_initialization(self):
        """Test that server initializes with proper MCP capabilities."""
        server = DShieldMCPServer()
        
        # Test server has required attributes
        assert hasattr(server, 'server')
        assert hasattr(server, 'error_handler')
        assert hasattr(server, 'tool_registry')
        
        # Test error handler is properly configured
        assert isinstance(server.error_handler, MCPErrorHandler)
        assert isinstance(server.error_handler.config, ErrorHandlingConfig)

    @pytest.mark.asyncio
    async def test_capability_negotiation(self):
        """Test MCP capability negotiation during initialization."""
        server = DShieldMCPServer()
        
        # Mock the notification options and experimental capabilities
        from mcp.server import NotificationOptions
        
        # Get server capabilities with proper parameters
        capabilities = server.server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={}
        )
        
        # Test required MCP capabilities
        assert hasattr(capabilities, 'tools')
        assert hasattr(capabilities, 'resources')
        
        # Test tools capability
        assert capabilities.tools is not None
        assert hasattr(capabilities.tools, 'listChanged')
        
        # Test resources capability
        assert capabilities.resources is not None
        assert hasattr(capabilities.resources, 'listChanged')

    @pytest.mark.asyncio
    async def test_tool_registry_initialization(self):
        """Test that tool registry is properly initialized."""
        server = DShieldMCPServer()
        
        # Test tool registry has required methods
        assert hasattr(server.tool_registry, 'available_tools')
        assert hasattr(server.tool_registry, 'is_tool_available')
        assert hasattr(server.tool_registry, 'get_tool_details')
        
        # Test tool registry is initialized (should be False before server.initialize())
        assert not server.tool_registry.is_initialized()
        
        # Initialize the server
        await server.initialize()
        
        # Now the tool registry should be initialized
        assert server.tool_registry.is_initialized()
        
        # Test that tools are available after initialization
        assert hasattr(server, 'available_tools')
        assert isinstance(server.available_tools, list)


class TestJSONRPCCompliance:
    """Test JSON-RPC 2.0 protocol compliance."""

    @pytest.mark.asyncio
    async def test_jsonrpc_error_codes(self):
        """Test that all JSON-RPC 2.0 error codes are properly implemented."""
        server = DShieldMCPServer()
        error_handler = server.error_handler
        
        # Test standard JSON-RPC 2.0 error codes
        standard_errors = [
            (-32700, 'PARSE_ERROR'),
            (-32600, 'INVALID_REQUEST'),
            (-32601, 'METHOD_NOT_FOUND'),
            (-32602, 'INVALID_PARAMS'),
            (-32603, 'INTERNAL_ERROR')
        ]
        
        for code, name in standard_errors:
            error = error_handler.create_error(code, f"Test {name}")
            assert error['error']['code'] == code
            assert 'message' in error['error']
            assert 'jsonrpc' in error
            assert error['jsonrpc'] == '2.0'

    @pytest.mark.asyncio
    async def test_server_defined_error_codes(self):
        """Test that server-defined error codes are properly implemented."""
        server = DShieldMCPServer()
        error_handler = server.error_handler
        
        # Test server-defined error codes
        server_errors = [
            (-32000, 'EXTERNAL_SERVICE_ERROR'),
            (-32001, 'RESOURCE_NOT_FOUND'),
            (-32002, 'RESOURCE_ACCESS_DENIED'),
            (-32003, 'RESOURCE_UNAVAILABLE'),
            (-32007, 'CIRCUIT_BREAKER_OPEN')
        ]
        
        for code, name in server_errors:
            error = error_handler.create_error(code, f"Test {name}")
            assert error['error']['code'] == code
            assert 'message' in error['error']
            assert 'jsonrpc' in error
            assert error['jsonrpc'] == '2.0'

    @pytest.mark.asyncio
    async def test_error_response_structure(self):
        """Test that error responses follow JSON-RPC 2.0 structure."""
        server = DShieldMCPServer()
        error_handler = server.error_handler
        
        # Test error response structure
        error = error_handler.create_internal_error("Test error message")
        
        # Required JSON-RPC 2.0 fields
        assert 'jsonrpc' in error
        assert error['jsonrpc'] == '2.0'
        assert 'error' in error
        assert 'code' in error['error']
        assert 'message' in error['error']
        
        # Optional fields
        if 'data' in error['error']:
            assert isinstance(error['error']['data'], (str, dict, list))


class TestErrorHandlingCompliance:
    """Test error handling compliance and behavior."""

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self):
        """Test that timeout errors are properly handled."""
        server = DShieldMCPServer()
        error_handler = server.error_handler
        
        # Test timeout error creation
        timeout_error = error_handler.create_timeout_error("test_tool", 30.0)
        
        assert 'error' in timeout_error
        assert 'code' in timeout_error['error']
        assert 'message' in timeout_error['error']
        assert 'jsonrpc' in timeout_error
        assert timeout_error['jsonrpc'] == '2.0'

    @pytest.mark.asyncio
    async def test_validation_error_handling(self):
        """Test that validation errors are properly handled."""
        server = DShieldMCPServer()
        error_handler = server.error_handler
        
        # Mock validation error with proper structure
        mock_validation_error = MagicMock()
        mock_validation_error.errors.return_value = [{'loc': ['field'], 'msg': 'Invalid value'}]
        
        # Test validation error creation
        validation_error = error_handler.create_validation_error("test_tool", mock_validation_error)
        
        assert 'error' in validation_error
        assert 'code' in validation_error['error']
        assert 'message' in validation_error['error']
        assert 'jsonrpc' in validation_error
        assert validation_error['jsonrpc'] == '2.0'

    @pytest.mark.asyncio
    async def test_external_service_error_handling(self):
        """Test that external service errors are properly handled."""
        server = DShieldMCPServer()
        error_handler = server.error_handler
        
        # Test external service error creation
        service_error = error_handler.create_external_service_error("test_service", "Service unavailable")
        
        assert 'error' in service_error
        assert 'code' in service_error['error']
        assert 'message' in service_error['error']
        assert 'jsonrpc' in service_error
        assert service_error['jsonrpc'] == '2.0'

    @pytest.mark.asyncio
    async def test_resource_error_handling(self):
        """Test that resource errors are properly handled."""
        server = DShieldMCPServer()
        error_handler = server.error_handler
        
        # Test resource error creation
        resource_error = error_handler.create_resource_error("test://resource", "not_found", "Resource not found")
        
        assert 'error' in resource_error
        assert 'code' in resource_error['error']
        assert 'message' in resource_error['error']
        assert 'jsonrpc' in resource_error
        assert resource_error['jsonrpc'] == '2.0'


class TestCircuitBreakerCompliance:
    """Test circuit breaker pattern compliance and behavior."""

    @pytest.mark.asyncio
    async def test_circuit_breaker_status_tools(self):
        """Test that circuit breaker status tools return proper responses."""
        server = DShieldMCPServer()
        
        # Test Elasticsearch circuit breaker status
        result = await server._get_elasticsearch_circuit_breaker_status({})
        assert isinstance(result, list)
        assert len(result) == 1
        
        # Test DShield circuit breaker status
        result = await server._get_dshield_circuit_breaker_status({})
        assert isinstance(result, list)
        assert len(result) == 1
        
        # Test LaTeX circuit breaker status
        result = await server._get_latex_circuit_breaker_status({})
        assert isinstance(result, list)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_circuit_breaker_error_responses(self):
        """Test that circuit breaker errors return proper JSON-RPC responses."""
        server = DShieldMCPServer()
        error_handler = server.error_handler
        
        # Test circuit breaker open error
        cb_error = error_handler.create_circuit_breaker_open_error("test_service")
        
        assert 'error' in cb_error
        assert 'code' in cb_error['error']
        assert cb_error['error']['code'] == -32007  # CIRCUIT_BREAKER_OPEN
        assert 'message' in cb_error['error']
        assert 'jsonrpc' in cb_error
        assert cb_error['jsonrpc'] == '2.0'


class TestMCPToolCompliance:
    """Test MCP tool compliance and behavior."""

    @pytest.mark.asyncio
    async def test_tool_availability_checking(self):
        """Test that tool availability is properly checked."""
        server = DShieldMCPServer()
        
        # Initialize the server first
        await server.initialize()
        
        # Test available tool (should be available if feature is healthy)
        assert server._is_tool_available("query_dshield_events")
        
        # Test tool that exists in feature map but might be unavailable
        # We can't easily test unavailable tools without mocking the feature manager
        # So let's just test that the method works for known tools
        
        # Test unavailable tool response for a tool that exists in feature map
        response = await server._tool_unavailable_response("query_dshield_events")
        assert isinstance(response, list)
        assert len(response) == 1
        assert 'error' in response[0]


class TestMCPResourceCompliance:
    """Test MCP resource compliance and behavior."""

    @pytest.mark.asyncio
    async def test_resource_listing(self):
        """Test that resources are properly listed."""
        server = DShieldMCPServer()
        
        # Test resource listing
        resources = server.server.get_capabilities(
            notification_options=MagicMock(),
            experimental_capabilities={}
        ).resources
        assert hasattr(resources, 'listChanged')
        
        # Test resource registration
        server._register_resources()
        # Resources should be registered without errors

    @pytest.mark.asyncio
    async def test_resource_error_handling(self):
        """Test that resource errors are properly handled."""
        server = DShieldMCPServer()
        error_handler = server.error_handler
        
        # Test resource error creation
        resource_error = error_handler.create_resource_error("test://resource", "not_found", "Resource not found")
        
        assert 'error' in resource_error
        assert 'code' in resource_error['error']
        assert 'message' in resource_error['error']
        assert 'jsonrpc' in resource_error
        assert resource_error['jsonrpc'] == '2.0'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
