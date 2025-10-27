"""Fast tests for config_loader core behaviors.

Covers missing file error, invalid error-handling values, and secret resolution shim.
"""

import os
from pathlib import Path

import pytest

from src.config_loader import ConfigError, _resolve_secrets, get_error_handling_config


def test_get_error_handling_config_invalid_timeout(tmp_path: Path) -> None:
    # Write a minimal config with invalid negative timeout
    cfg = (
        "error_handling:\n"
        "  timeouts:\n"
        "    tool_execution: -5\n"
    )
    p = tmp_path / "mcp.yaml"
    p.write_text(cfg)
    with pytest.raises(ConfigError):
        get_error_handling_config(str(p))


def test_get_error_handling_config_valid_minimal(tmp_path: Path) -> None:
    cfg = (
        "error_handling:\n"
        "  timeouts:\n"
        "    tool_execution: 10\n"
        "  retry_settings:\n"
        "    max_retries: 1\n"
        "    base_delay: 0.1\n"
        "    max_delay: 1\n"
        "    exponential_base: 2\n"
        "  logging:\n"
        "    include_stack_traces: true\n"
        "    include_request_context: false\n"
        "    include_user_parameters: true\n"
        "    log_level: INFO\n"
    )
    p = tmp_path / "mcp.yaml"
    p.write_text(cfg)
    cfg_obj = get_error_handling_config(str(p))
    assert cfg_obj.timeouts["tool_execution"] == 10.0
    assert cfg_obj.retry_settings["max_retries"] == 1
    assert cfg_obj.logging["log_level"] == "INFO"


def test_resolve_secrets_shim(monkeypatch) -> None:
    # Shim OnePasswordSecrets.resolve_environment_variable to return replaced values
    calls = {"n": 0}

    class FakeOP:
        def resolve_environment_variable(self, v: str):
            calls["n"] += 1
            if v.startswith("op://"):
                return "resolved"
            return v

    monkeypatch.setattr("src.config_loader.OnePasswordSecrets", lambda: FakeOP())
    data = {"a": "op://vault/item/field", "b": ["x", "op://y/z"], "c": {"k": "v"}}
    out = _resolve_secrets(data)
    assert out["a"] == "resolved"
    assert out["b"][1] == "resolved"
    assert out["c"]["k"] == "v"
    assert calls["n"] >= 2

