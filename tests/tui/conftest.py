#!/usr/bin/env python3
"""Test fixtures for TUI components.

This module provides shared test fixtures for testing TUI components,
including mock servers, applications, and test data.
"""

from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock

import pytest

# Note: textual.testing.AppTest may not be available in all versions
# We'll use a simpler testing approach
from src.tcp_server import EnhancedTCPServer
from src.tui.tui_app import DShieldTUIApp
from src.user_config import UserConfigManager


@pytest.fixture
def mock_tcp_server() -> Mock:
    """Create a mock TCP server for testing.
    
    Returns:
        Mock: A mock TCP server with common methods

    """
    server = Mock(spec=EnhancedTCPServer)
    server.start = AsyncMock()
    server.stop = AsyncMock()
    server.restart = AsyncMock()
    server.get_server_statistics = Mock(return_value={
        "server": {"is_running": True, "port": 3000, "bind_address": "127.0.0.1"},
        "connections": {"active": 2, "total": 10},
        "uptime": "00:05:30",
    })
    server.get_connections = Mock(return_value=[
        {"id": "conn1", "address": "127.0.0.1:12345", "connected_at": "2024-01-01T10:00:00Z"},
        {"id": "conn2", "address": "127.0.0.1:12346", "connected_at": "2024-01-01T10:01:00Z"},
    ])
    server.disconnect_client = AsyncMock()
    server.disconnect_all_clients = AsyncMock()
    return server


@pytest.fixture
def mock_mcp_server() -> Mock:
    """Create a mock MCP server for testing.
    
    Returns:
        Mock: A mock MCP server

    """
    server = Mock()
    server.start = AsyncMock()
    server.stop = AsyncMock()
    server.is_running = Mock(return_value=True)
    server.get_statistics = Mock(return_value={
        "tools_registered": 15,
        "requests_processed": 100,
        "uptime": "00:05:30",
    })
    return server


@pytest.fixture
def mock_user_config() -> Mock:
    """Create a mock user configuration manager.
    
    Returns:
        Mock: A mock UserConfigManager

    """
    config = Mock(spec=UserConfigManager)
    config.tcp_transport_settings = Mock()
    config.tcp_transport_settings.port = 3000
    config.tcp_transport_settings.bind_address = "127.0.0.1"
    config.tcp_transport_settings.enable_tls = False
    config.tcp_transport_settings.cert_file = None
    config.tcp_transport_settings.key_file = None
    config.tcp_transport_settings.api_key_required = True
    config.tcp_transport_settings.max_connections = 10
    config.tcp_transport_settings.connection_timeout = 30
    config.tcp_transport_settings.keep_alive_timeout = 60
    config.tcp_transport_settings.max_request_size = 1024 * 1024
    config.tcp_transport_settings.enable_compression = True
    config.tcp_transport_settings.log_level = "INFO"
    config.tcp_transport_settings.enable_metrics = True
    config.tcp_transport_settings.metrics_port = 9090
    config.tcp_transport_settings.enable_health_check = True
    config.tcp_transport_settings.health_check_interval = 30
    config.tcp_transport_settings.enable_graceful_shutdown = True
    config.tcp_transport_settings.shutdown_timeout = 30
    config.tcp_transport_settings.enable_cors = False
    config.tcp_transport_settings.cors_origins = []
    config.tcp_transport_settings.enable_rate_limiting = True
    config.tcp_transport_settings.rate_limit_requests = 100
    config.tcp_transport_settings.rate_limit_window = 60
    config.tcp_transport_settings.enable_request_logging = True
    config.tcp_transport_settings.enable_response_logging = False
    config.tcp_transport_settings.enable_error_logging = True
    config.tcp_transport_settings.log_format = "json"
    config.tcp_transport_settings.log_file = None
    config.tcp_transport_settings.log_rotation = True
    config.tcp_transport_settings.log_max_size = 10 * 1024 * 1024
    config.tcp_transport_settings.log_backup_count = 5
    config.tcp_transport_settings.enable_debug_mode = False
    config.tcp_transport_settings.debug_port = 5678
    config.tcp_transport_settings.enable_profiling = False
    config.tcp_transport_settings.profile_output_dir = None
    config.tcp_transport_settings.enable_tracing = False
    config.tcp_transport_settings.trace_sample_rate = 0.1
    config.tcp_transport_settings.trace_output_dir = None
    config.tcp_transport_settings.enable_metrics_export = True
    config.tcp_transport_settings.metrics_export_interval = 60
    config.tcp_transport_settings.metrics_export_endpoint = None
    config.tcp_transport_settings.enable_health_export = True
    config.tcp_transport_settings.health_export_interval = 30
    config.tcp_transport_settings.health_export_endpoint = None
    config.tcp_transport_settings.enable_status_export = True
    config.tcp_transport_settings.status_export_interval = 60
    config.tcp_transport_settings.status_export_endpoint = None
    config.tcp_transport_settings.enable_log_export = False
    config.tcp_transport_settings.log_export_interval = 300
    config.tcp_transport_settings.log_export_endpoint = None
    config.tcp_transport_settings.enable_alerting = False
    config.tcp_transport_settings.alert_endpoints = []
    config.tcp_transport_settings.alert_thresholds = {}
    config.tcp_transport_settings.enable_notifications = False
    config.tcp_transport_settings.notification_endpoints = []
    config.tcp_transport_settings.notification_templates = {}
    config.tcp_transport_settings.enable_webhooks = False
    config.tcp_transport_settings.webhook_endpoints = []
    config.tcp_transport_settings.webhook_secret = None
    config.tcp_transport_settings.enable_authentication = True
    config.tcp_transport_settings.auth_provider = "api_key"
    config.tcp_transport_settings.auth_config = {}
    config.tcp_transport_settings.enable_authorization = True
    config.tcp_transport_settings.authorization_provider = "rbac"
    config.tcp_transport_settings.authorization_config = {}
    config.tcp_transport_settings.enable_audit_logging = True
    config.tcp_transport_settings.audit_log_level = "INFO"
    config.tcp_transport_settings.audit_log_file = None
    config.tcp_transport_settings.audit_log_rotation = True
    config.tcp_transport_settings.audit_log_max_size = 10 * 1024 * 1024
    config.tcp_transport_settings.audit_log_backup_count = 5
    config.tcp_transport_settings.enable_session_management = True
    config.tcp_transport_settings.session_timeout = 3600
    config.tcp_transport_settings.session_cleanup_interval = 300
    config.tcp_transport_settings.enable_connection_pooling = True
    config.tcp_transport_settings.connection_pool_size = 10
    config.tcp_transport_settings.connection_pool_timeout = 30
    config.tcp_transport_settings.enable_connection_reuse = True
    config.tcp_transport_settings.connection_reuse_timeout = 60
    config.tcp_transport_settings.enable_keep_alive = True
    config.tcp_transport_settings.keep_alive_interval = 30
    config.tcp_transport_settings.enable_tcp_nodelay = True
    config.tcp_transport_settings.enable_tcp_keepalive = True
    config.tcp_transport_settings.tcp_keepalive_idle = 600
    config.tcp_transport_settings.tcp_keepalive_interval = 60
    config.tcp_transport_settings.tcp_keepalive_count = 3
    config.tcp_transport_settings.enable_so_reuseport = False
    config.tcp_transport_settings.enable_so_reuseaddr = True
    config.tcp_transport_settings.enable_so_keepalive = True
    config.tcp_transport_settings.enable_so_linger = False
    config.tcp_transport_settings.so_linger_timeout = 0
    config.tcp_transport_settings.enable_so_rcvbuf = True
    config.tcp_transport_settings.so_rcvbuf_size = 65536
    config.tcp_transport_settings.enable_so_sndbuf = True
    config.tcp_transport_settings.so_sndbuf_size = 65536
    config.tcp_transport_settings.enable_so_rcvtimeo = True
    config.tcp_transport_settings.so_rcvtimeo_timeout = 30
    config.tcp_transport_settings.enable_so_sndtimeo = True
    config.tcp_transport_settings.so_sndtimeo_timeout = 30
    config.tcp_transport_settings.enable_so_error = True
    config.tcp_transport_settings.enable_so_broadcast = False
    config.tcp_transport_settings.enable_so_dontroute = False
    config.tcp_transport_settings.enable_so_oobinline = False
    config.tcp_transport_settings.enable_so_priority = False
    config.tcp_transport_settings.so_priority_value = 0
    config.tcp_transport_settings.enable_so_rcvlowat = False
    config.tcp_transport_settings.so_rcvlowat_size = 1
    config.tcp_transport_settings.enable_so_sndlowat = False
    config.tcp_transport_settings.so_sndlowat_size = 1
    config.tcp_transport_settings.enable_so_rcvtimeo = True
    config.tcp_transport_settings.so_rcvtimeo_timeout = 30
    config.tcp_transport_settings.enable_so_sndtimeo = True
    config.tcp_transport_settings.so_sndtimeo_timeout = 30
    config.tcp_transport_settings.enable_so_error = True
    config.tcp_transport_settings.enable_so_broadcast = False
    config.tcp_transport_settings.enable_so_dontroute = False
    config.tcp_transport_settings.enable_so_oobinline = False
    config.tcp_transport_settings.enable_so_priority = False
    config.tcp_transport_settings.so_priority_value = 0
    config.tcp_transport_settings.enable_so_rcvlowat = False
    config.tcp_transport_settings.so_rcvlowat_size = 1
    config.tcp_transport_settings.enable_so_sndlowat = False
    config.tcp_transport_settings.so_sndlowat_size = 1
    return config


@pytest.fixture
async def tui_app(mock_tcp_server: Mock, mock_user_config: Mock) -> DShieldTUIApp:
    """Create a TUI app instance for testing.
    
    Args:
        mock_tcp_server: Mock TCP server
        mock_user_config: Mock user configuration
        
    Returns:
        DShieldTUIApp: TUI app instance with mocked dependencies

    """
    app = DShieldTUIApp()
    app.tcp_server = mock_tcp_server
    app.user_config = mock_user_config
    return app


@pytest.fixture
def sample_connections() -> List[Dict[str, Any]]:
    """Create sample connection data for testing.
    
    Returns:
        List[Dict[str, Any]]: Sample connection data

    """
    return [
        {
            "id": "conn1",
            "address": "127.0.0.1:12345",
            "connected_at": "2024-01-01T10:00:00Z",
            "last_activity": "2024-01-01T10:05:00Z",
            "requests_count": 15,
            "status": "active",
        },
        {
            "id": "conn2",
            "address": "127.0.0.1:12346",
            "connected_at": "2024-01-01T10:01:00Z",
            "last_activity": "2024-01-01T10:04:00Z",
            "requests_count": 8,
            "status": "active",
        },
        {
            "id": "conn3",
            "address": "127.0.0.1:12347",
            "connected_at": "2024-01-01T09:30:00Z",
            "last_activity": "2024-01-01T09:35:00Z",
            "requests_count": 3,
            "status": "idle",
        },
    ]


@pytest.fixture
def sample_api_keys() -> List[Dict[str, Any]]:
    """Create sample API key data for testing.
    
    Returns:
        List[Dict[str, Any]]: Sample API key data

    """
    return [
        {
            "id": "key1",
            "name": "Test Key 1",
            "created_at": "2024-01-01T09:00:00Z",
            "last_used": "2024-01-01T10:00:00Z",
            "usage_count": 25,
            "status": "active",
        },
        {
            "id": "key2",
            "name": "Test Key 2",
            "created_at": "2024-01-01T08:00:00Z",
            "last_used": "2024-01-01T09:30:00Z",
            "usage_count": 12,
            "status": "active",
        },
        {
            "id": "key3",
            "name": "Test Key 3",
            "created_at": "2024-01-01T07:00:00Z",
            "last_used": None,
            "usage_count": 0,
            "status": "revoked",
        },
    ]


@pytest.fixture
def sample_log_entries() -> List[Dict[str, Any]]:
    """Create sample log entry data for testing.
    
    Returns:
        List[Dict[str, Any]]: Sample log entry data

    """
    return [
        {
            "timestamp": "2024-01-01T10:00:00Z",
            "level": "INFO",
            "message": "Server started successfully",
            "source": "tcp_server",
            "details": {"port": 3000, "bind_address": "127.0.0.1"},
        },
        {
            "timestamp": "2024-01-01T10:01:00Z",
            "level": "WARNING",
            "message": "Connection timeout detected",
            "source": "connection_manager",
            "details": {"connection_id": "conn1", "timeout_duration": 30},
        },
        {
            "timestamp": "2024-01-01T10:02:00Z",
            "level": "ERROR",
            "message": "Failed to process request",
            "source": "request_handler",
            "details": {"error": "Invalid JSON", "request_id": "req123"},
        },
        {
            "timestamp": "2024-01-01T10:03:00Z",
            "level": "DEBUG",
            "message": "Processing MCP request",
            "source": "mcp_handler",
            "details": {"method": "tools/list", "request_id": "req124"},
        },
    ]


@pytest.fixture
def sample_server_status() -> Dict[str, Any]:
    """Create sample server status data for testing.
    
    Returns:
        Dict[str, Any]: Sample server status data

    """
    return {
        "server": {
            "is_running": True,
            "port": 3000,
            "bind_address": "127.0.0.1",
            "uptime": "00:05:30",
            "started_at": "2024-01-01T09:55:00Z",
        },
        "connections": {
            "active": 2,
            "total": 10,
            "max_connections": 10,
            "connection_rate": 0.5,
        },
        "requests": {
            "total": 150,
            "successful": 145,
            "failed": 5,
            "rate": 2.5,
        },
        "performance": {
            "cpu_usage": 15.5,
            "memory_usage": 128.7,
            "response_time_avg": 45.2,
            "response_time_p95": 120.5,
        },
        "errors": {
            "total": 5,
            "rate": 0.1,
            "last_error": "2024-01-01T10:02:00Z",
        },
    }


@pytest.fixture
def mock_app_test():
    """Create a mock app test instance for testing TUI components.
    
    Returns:
        Mock: Mock app test instance for testing

    """
    return Mock()
