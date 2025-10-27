"""Fast tests for InputValidator error paths and sanitization.

Validates message size guard, JSON-RPC structure, allowed method list, and id checks.
"""

import json
import pytest

from src.tcp_security import InputValidator, SecurityViolation


def test_message_size_exceeded() -> None:
    validator = InputValidator({"max_message_size": 10})
    message = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    big = json.loads(json.dumps(message))
    big["padding"] = "x" * 100
    with pytest.raises(SecurityViolation) as ei:
        validator.validate_message(big)
    assert "Message size exceeds maximum" in str(ei.value)


def test_invalid_jsonrpc_version() -> None:
    validator = InputValidator()
    with pytest.raises(SecurityViolation) as ei:
        validator.validate_message({"jsonrpc": "1.0", "id": 1, "method": "tools/list"})
    assert "Invalid JSON-RPC version" in str(ei.value)


def test_method_not_allowed() -> None:
    validator = InputValidator({"allowed_methods": ["tools/list"]})
    with pytest.raises(SecurityViolation) as ei:
        validator.validate_message({"jsonrpc": "2.0", "id": 1, "method": "admin/exec"})
    assert "is not allowed" in str(ei.value)


def test_invalid_id_type() -> None:
    validator = InputValidator()
    with pytest.raises(SecurityViolation) as ei:
        validator.validate_message({"jsonrpc": "2.0", "id": {"bad": True}, "method": "tools/list"})
    assert "ID must be a string" in str(ei.value)
