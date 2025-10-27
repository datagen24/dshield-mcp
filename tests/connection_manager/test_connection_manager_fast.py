"""Fast tests for ConnectionManager basic operations.

Avoids external calls by using in-memory APIKey instances and local methods.
"""

from datetime import UTC, datetime, timedelta
from dataclasses import dataclass

from src.connection_manager import ConnectionManager
from src.secrets_manager.base_secrets_manager import APIKey


def _make_key(key_id: str, value: str, expired: bool = False) -> APIKey:
    expires_at = None
    if expired:
        expires_at = datetime.now(UTC) - timedelta(days=1)
    else:
        expires_at = datetime.now(UTC) + timedelta(days=1)
    return APIKey(
        key_id=key_id,
        key_value=value,
        name=f"Key {key_id}",
        created_at=datetime.now(UTC),
        expires_at=expires_at,
        permissions={"read_tools": True},
        metadata={"t": 1},
    )


@dataclass(frozen=True)
class Conn:
    client_address: str
    api_key: str | None = None


def test_add_remove_connection_and_counts() -> None:
    cm = ConnectionManager(config={})

    # Add a fake connection
    conn = Conn(client_address="127.0.0.1:10000")
    cm.add_connection(conn)
    assert cm.get_connection_count() == 1

    # Remove and re-check
    cm.remove_connection(conn)
    assert cm.get_connection_count() == 0


def test_connections_info_with_api_key_present() -> None:
    cm = ConnectionManager(config={})

    # Prime cache with an API key and attach to connection
    key = _make_key("k1", "dshield_k1")
    cm.api_keys[key.key_value] = key

    conn = Conn(client_address="127.0.0.1:10001", api_key=key.key_value)
    cm.add_connection(conn)

    info = cm.get_connections_info()
    assert isinstance(info, list) and len(info) == 1
    assert info[0]["api_key_id"] == key.key_id


def test_cleanup_expired_keys_and_stats() -> None:
    cm = ConnectionManager(config={})
    active = _make_key("k2", "dshield_k2", expired=False)
    expired = _make_key("k3", "dshield_k3", expired=True)
    cm.api_keys[active.key_value] = active
    cm.api_keys[expired.key_value] = expired

    removed = cm.cleanup_expired_keys()
    assert removed == 1
    assert active.key_value in cm.api_keys and expired.key_value not in cm.api_keys

    stats = cm.get_statistics()
    assert stats["api_keys"]["total"] >= 1
    assert stats["api_keys"]["active"] >= 1
