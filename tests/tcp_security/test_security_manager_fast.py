"""Fast tests for TCPSecurityManager logic paths.

Covers validate_message happy/limit paths, client block/unblock, and connection attempts.
"""

import pytest

from datetime import datetime

from src.tcp_security import SecurityViolation, TCPSecurityManager, RateLimiter


def _valid_msg() -> dict:
    return {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}


def test_validate_message_allows_then_rate_limited() -> None:
    # Tight limits so second call fails quickly
    mgr = TCPSecurityManager(
        {
            "global_rate_limit": 1,
            "global_burst_limit": 1,
            "client_rate_limit": 1,
            "client_burst_limit": 1,
        }
    )
    client = "c1"
    # Align internal time zones: make last_refill naive to match utcnow()
    mgr.global_rate_limiter.last_refill = datetime.utcnow()
    # Pre-create client limiter with naive last_refill
    mgr.client_rate_limiters[client] = RateLimiter(requests_per_minute=1, burst_limit=1)
    mgr.client_rate_limiters[client].last_refill = datetime.utcnow()

    ok = mgr.validate_message(_valid_msg(), client)
    assert ok["method"] == "tools/list"

    with pytest.raises(SecurityViolation) as ei:
        mgr.validate_message(_valid_msg(), client)
    assert "Rate limit exceeded" in str(ei.value)


def test_client_block_and_unblock_path() -> None:
    mgr = TCPSecurityManager(
        {
            "abuse_threshold": 2,
            "block_duration_seconds": 60,
            "global_rate_limit": 1000,
            "global_burst_limit": 100,
            "client_rate_limit": 100,
            "client_burst_limit": 100,
        }
    )
    client = "badguy"
    # Trigger block
    mgr._record_violation(client, "X")
    mgr._record_violation(client, "Y")
    assert client in mgr.blocked_clients

    # Force unblock by mocking internal state: set block time far in the past
    # and check _is_client_blocked toggles off via validate path.
    mgr.client_block_times[client] = mgr.client_block_times[client].replace(year=2000)
    assert mgr._is_client_blocked(client) is False
    # Now validation should pass under generous limits
    mgr.global_rate_limiter.last_refill = datetime.utcnow()
    mgr.client_rate_limiters[client] = RateLimiter(requests_per_minute=100, burst_limit=100)
    mgr.client_rate_limiters[client].last_refill = datetime.utcnow()
    ok = mgr.validate_message(_valid_msg(), client)
    assert ok["jsonrpc"] == "2.0"


def test_connection_attempt_limit_and_cleanup() -> None:
    mgr = TCPSecurityManager(
        {
            "max_connection_attempts": 2,
            "connection_window_seconds": 300,
        }
    )
    client = "ratey"
    assert mgr.record_connection_attempt(client) is True
    assert mgr.record_connection_attempt(client) is True
    # Third within window should be denied
    assert mgr.record_connection_attempt(client) is False

    # Stale block and connection entries get cleaned
    mgr.blocked_clients.add(client)
    mgr.client_block_times[client] = datetime.utcnow()
    # Move the block time far into the past to trigger cleanup
    mgr.client_block_times[client] = mgr.client_block_times[client].replace(year=2000)
    cleaned = mgr.cleanup_expired_data()
    assert cleaned >= 1
    assert client not in mgr.blocked_clients
