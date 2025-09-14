"""Fast tests for MCPErrorHandler core utilities.

Covers error creation, timeout wrapper, and retry logic.
"""

import asyncio
import pytest

from src.mcp_error_handler import MCPErrorHandler


def test_create_error_structure() -> None:
    h = MCPErrorHandler()
    err = h.create_error(h.INVALID_PARAMS, "bad args", {"field": "x"}, request_id="1")
    assert err["jsonrpc"] == "2.0"
    assert err["error"]["code"] == h.INVALID_PARAMS
    assert err["error"]["message"] == "bad args"
    assert err["error"]["data"]["field"] == "x"
    assert err["id"] == "1"


@pytest.mark.asyncio
async def test_execute_with_timeout_raises() -> None:
    h = MCPErrorHandler()

    async def slow():
        await asyncio.sleep(0.05)
        return 123

    with pytest.raises(asyncio.TimeoutError):
        await h.execute_with_timeout("op", slow(), timeout_seconds=0.01)


@pytest.mark.asyncio
async def test_execute_with_retry_succeeds_on_second() -> None:
    h = MCPErrorHandler()
    calls = {"n": 0}

    async def maybe_fail():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("boom")
        return "ok"

    res = await h.execute_with_retry(
        "op",
        lambda: maybe_fail(),
        max_retries=1,
        base_delay=0.01,
        max_delay=0.02,
        exponential_base=2.0,
    )
    assert res == "ok"

