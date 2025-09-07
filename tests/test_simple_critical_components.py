"""Simple tests for critical components to improve coverage."""

from unittest.mock import Mock, patch

from src.connection_manager import APIKey, ConnectionManager
from src.transport.tcp_transport import TCPConnection


class TestConnectionManagerSimple:
    """Simple tests for ConnectionManager."""

    def test_init(self) -> None:
        """Test ConnectionManager initialization."""
        with (
            patch('src.connection_manager.OnePasswordSecrets'),
            patch('src.connection_manager.OnePasswordAPIKeyManager'),
            patch('asyncio.create_task'),
        ):
            manager = ConnectionManager()
            assert manager is not None
            assert hasattr(manager, 'connections')
            assert hasattr(manager, 'api_keys')

    def test_add_connection(self) -> None:
        """Test adding a connection."""
        with (
            patch('src.connection_manager.OnePasswordSecrets'),
            patch('src.connection_manager.OnePasswordAPIKeyManager'),
            patch('asyncio.create_task'),
        ):
            manager = ConnectionManager()

            mock_reader = Mock()
            mock_writer = Mock()
            connection = TCPConnection(
                reader=mock_reader,
                writer=mock_writer,
                client_address=("127.0.0.1", 12345),
                api_key="test_key",
            )

            manager.add_connection(connection)
            assert len(manager.connections) == 1

    def test_remove_connection(self) -> None:
        """Test removing a connection."""
        with (
            patch('src.connection_manager.OnePasswordSecrets'),
            patch('src.connection_manager.OnePasswordAPIKeyManager'),
            patch('asyncio.create_task'),
        ):
            manager = ConnectionManager()

            mock_reader = Mock()
            mock_writer = Mock()
            connection = TCPConnection(
                reader=mock_reader,
                writer=mock_writer,
                client_address=("127.0.0.1", 12345),
                api_key="test_key",
            )

            manager.add_connection(connection)
            assert len(manager.connections) == 1

            manager.remove_connection(connection)
            assert len(manager.connections) == 0

    def test_get_connection_count(self) -> None:
        """Test getting connection count."""
        with (
            patch('src.connection_manager.OnePasswordSecrets'),
            patch('src.connection_manager.OnePasswordAPIKeyManager'),
            patch('asyncio.create_task'),
        ):
            manager = ConnectionManager()

            assert manager.get_connection_count() == 0

            mock_reader = Mock()
            mock_writer = Mock()
            connection = TCPConnection(
                reader=mock_reader,
                writer=mock_writer,
                client_address=("127.0.0.1", 12345),
                api_key="test_key",
            )

            manager.add_connection(connection)
            assert manager.get_connection_count() == 1

    def test_get_connections_info(self) -> None:
        """Test getting connections info."""
        with (
            patch('src.connection_manager.OnePasswordSecrets'),
            patch('src.connection_manager.OnePasswordAPIKeyManager'),
            patch('asyncio.create_task'),
        ):
            manager = ConnectionManager()

            info = manager.get_connections_info()
            assert isinstance(info, list)
            assert len(info) == 0


class TestAPIKeySimple:
    """Simple tests for APIKey."""

    def test_init(self) -> None:
        """Test APIKey initialization."""
        api_key = APIKey(
            key_id="test_key", key_value="test_value", permissions={"read": True, "write": False}
        )

        assert api_key.key_id == "test_key"
        assert api_key.key_value == "test_value"
        assert api_key.permissions == {"read": True, "write": False}
        assert api_key.is_active is True

    def test_init_with_expires_days(self) -> None:
        """Test APIKey initialization with custom expiration."""
        api_key = APIKey(
            key_id="test_key", key_value="test_value", permissions={"read": True}, expires_days=30
        )

        assert api_key.key_id == "test_key"
        assert api_key.expires_at > api_key.created_at

    def test_is_expired_false(self) -> None:
        """Test is_expired when key is not expired."""
        api_key = APIKey(
            key_id="test_key", key_value="test_value", permissions={"read": True}, expires_days=30
        )

        assert api_key.is_expired() is False

    def test_is_expired_true(self) -> None:
        """Test is_expired when key is expired."""
        api_key = APIKey(
            key_id="test_key",
            key_value="test_value",
            permissions={"read": True},
            expires_days=-1,  # Expired yesterday
        )

        assert api_key.is_expired() is True

    def test_is_valid_true(self) -> None:
        """Test is_valid when key is valid."""
        api_key = APIKey(
            key_id="test_key", key_value="test_value", permissions={"read": True, "write": False}
        )

        assert api_key.is_valid() is True

    def test_is_valid_false(self) -> None:
        """Test is_valid when key is invalid."""
        api_key = APIKey(
            key_id="test_key",
            key_value="test_value",
            permissions={"read": True},
            expires_days=-1,  # Expired
        )

        assert api_key.is_valid() is False

    def test_to_dict(self) -> None:
        """Test converting APIKey to dictionary."""
        api_key = APIKey(key_id="test_key", key_value="test_value", permissions={"read": True})

        result = api_key.to_dict()

        assert isinstance(result, dict)
        assert result["key_id"] == "test_key"
        assert result["key_value"] == "test_val..."  # Masked for security
        assert result["permissions"] == {"read": True}
        assert result["is_active"] is True
        assert "created_at" in result
        assert "expires_at" in result


class TestTCPConnectionSimple:
    """Simple tests for TCPConnection."""

    def test_init(self) -> None:
        """Test TCPConnection initialization."""
        mock_reader = Mock()
        mock_writer = Mock()

        connection = TCPConnection(
            reader=mock_reader,
            writer=mock_writer,
            client_address=("127.0.0.1", 12345),
            api_key="test_key",
        )

        assert connection.reader == mock_reader
        assert connection.writer == mock_writer
        assert connection.client_address == ("127.0.0.1", 12345)
        assert connection.api_key == "test_key"
        assert connection.is_authenticated is True  # True when api_key is provided

    def test_init_without_api_key(self) -> None:
        """Test TCPConnection initialization without API key."""
        mock_reader = Mock()
        mock_writer = Mock()

        connection = TCPConnection(
            reader=mock_reader, writer=mock_writer, client_address=("127.0.0.1", 12345)
        )

        assert connection.api_key is None
        assert connection.is_authenticated is False  # False when no api_key

    def test_update_activity(self) -> None:
        """Test updating connection activity."""
        mock_reader = Mock()
        mock_writer = Mock()

        connection = TCPConnection(
            reader=mock_reader,
            writer=mock_writer,
            client_address=("127.0.0.1", 12345),
            api_key="test_key",
        )

        # Test that update_activity method exists and works
        connection.update_activity()
        assert hasattr(connection, 'last_activity')

    def test_get_info(self) -> None:
        """Test getting connection info."""
        mock_reader = Mock()
        mock_writer = Mock()

        connection = TCPConnection(
            reader=mock_reader,
            writer=mock_writer,
            client_address=("127.0.0.1", 12345),
            api_key="test_key",
        )

        # Test that we can access the connection attributes
        assert connection.client_address == ("127.0.0.1", 12345)
        assert connection.api_key == "test_key"
        assert connection.is_authenticated is True
        assert hasattr(connection, 'connected_at')
        assert hasattr(connection, 'last_activity')
