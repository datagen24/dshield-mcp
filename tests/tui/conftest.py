"""TUI test configuration and fixtures."""

from unittest.mock import Mock

import pytest


class MockTUIApp:
    """Mock TUI application for testing."""

    def __init__(self):
        self.server_running = False
        self.tcp_server = Mock()
        self.connections = []
        self.api_keys = []
        self.logs = []
        self.current_panel = "connections"
        self.config = {"host": "127.0.0.1", "port": 3000}

    async def action_restart_server(self):
        """Mock server restart action."""
        self.server_running = True

    async def action_stop_server(self):
        """Mock server stop action."""
        self.server_running = False

    async def action_generate_api_key(self):
        """Mock API key generation."""
        new_key = {"id": "test_key", "name": "Test Key", "permissions": ["read", "write"]}
        self.api_keys.append(new_key)
        return new_key

    async def action_clear_logs(self):
        """Mock log clearing."""
        self.logs = []

    def add_connection(self, connection_id: str, client_ip: str):
        """Mock connection addition."""
        connection = {"id": connection_id, "ip": client_ip, "connected_at": "2024-01-01T00:00:00Z"}
        self.connections.append(connection)

    def remove_connection(self, connection_id: str):
        """Mock connection removal."""
        self.connections = [c for c in self.connections if c["id"] != connection_id]

    def add_log(self, level: str, message: str):
        """Mock log addition."""
        log_entry = {"level": level, "message": message, "timestamp": "2024-01-01T00:00:00Z"}
        self.logs.append(log_entry)


class MockConnectionPanel:
    """Mock connection panel for testing."""

    def __init__(self):
        self.connections = []
        self.api_keys = []
        self.selected_connection = None
        self.selected_api_key = None

    def update_connections(self, connections):
        """Mock connection update."""
        self.connections = connections

    def update_api_keys(self, api_keys):
        """Mock API key update."""
        self.api_keys = api_keys

    def remove_connection(self, connection_id):
        """Mock connection removal."""
        self.connections = [c for c in self.connections if c["id"] != connection_id]


@pytest.fixture
def mock_tui_app():
    """Fixture providing a mock TUI application."""
    return MockTUIApp()


@pytest.fixture
def mock_connection_panel():
    """Fixture providing a mock connection panel."""
    return MockConnectionPanel()
