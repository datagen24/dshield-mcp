"""Fast tests for TCPAuthenticator core logic.

Covers session limit checks, session creation, and authenticate error paths.
"""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.secrets_manager.base_secrets_manager import APIKey
from src.tcp_auth import AuthenticationError, TCPAuthenticator
from src.mcp_error_handler import MCPErrorHandler


@dataclass
class Conn:
    client_address: str
    api_key: str | None = None
    is_authenticated: bool = False
    session_id: str | None = None


class FakeCM:
    def __init__(self, api_key_obj: APIKey | None) -> None:
        self._api_key_obj = api_key_obj
        self.validate_api_key = AsyncMock(return_value=api_key_obj)


def make_key(key: str = "dshield_abc") -> APIKey:
    return APIKey(
        key_id="kid-1",
        key_value=key,
        name="kname",
        created_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(days=1),
        permissions={"read_tools": True},
        metadata={},
    )


@pytest.mark.asyncio
async def test_session_limit_and_create_session() -> None:
    cm = FakeCM(api_key_obj=make_key())
    auth = TCPAuthenticator(connection_manager=cm, error_handler=MCPErrorHandler(), config={"max_sessions_per_key": 1})
    c = Conn("127.0.0.1:1")

    # First session allowed
    res = await auth.authenticate_connection(c, {"api_key": cm._api_key_obj.key_value})
    assert res["authenticated"] is True and c.is_authenticated is True

    # Second session with same key should exceed limit
    c2 = Conn("127.0.0.1:2")
    with pytest.raises(AuthenticationError) as ei:
        await auth.authenticate_connection(c2, {"api_key": cm._api_key_obj.key_value})
    assert "Maximum sessions per API key exceeded" in str(ei.value)


@pytest.mark.asyncio
async def test_authenticate_missing_and_invalid_key() -> None:
    # Missing api_key
    cm = FakeCM(api_key_obj=None)
    auth = TCPAuthenticator(connection_manager=cm, error_handler=MCPErrorHandler())
    with pytest.raises(AuthenticationError) as ei:
        await auth.authenticate_connection(Conn("127.0.0.1:3"), {})
    assert "API key is required" in str(ei.value)

    # Provided but invalid key
    with pytest.raises(AuthenticationError) as ei2:
        await auth.authenticate_connection(Conn("127.0.0.1:4"), {"api_key": "bad"})
    assert "Invalid or expired API key" in str(ei2.value)

