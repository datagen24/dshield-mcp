"""Fast tests for OnePasswordSecrets behaviors with subprocess mocked.

Covers resolve_op_url timeout/error and complex replacement paths.
"""

import subprocess
from types import SimpleNamespace

from src.op_secrets import OnePasswordSecrets


def test_resolve_op_url_timeout(monkeypatch) -> None:
    # Mock subprocess.run to satisfy --version and then raise TimeoutExpired on read
    def fake_run(args, **kwargs):  # type: ignore[no-redef]
        if args[:2] == ["op", "--version"]:
            return SimpleNamespace(returncode=0, stdout="1.0.0\n")
        raise subprocess.TimeoutExpired("op", 1)

    monkeypatch.setattr("subprocess.run", fake_run)
    s = OnePasswordSecrets()
    # Force available true (since version succeeded)
    s.op_available = True
    assert s.resolve_op_url("op://vault/item/field") is None


def test_complex_value_replacement(monkeypatch) -> None:
    # Fake run returns ok for version and a fixed secret for read
    def fake_run(args, **kwargs):  # type: ignore[no-redef]
        if args[:2] == ["op", "--version"]:
            return SimpleNamespace(returncode=0, stdout="1.2.3\n")
        if args[:2] == ["op", "read"]:
            return SimpleNamespace(returncode=0, stdout="SEC\n")
        raise AssertionError("unexpected op call")

    monkeypatch.setattr("subprocess.run", fake_run)
    s = OnePasswordSecrets()
    s.op_available = True
    out = s.resolve_environment_variable("prefix op://vault/item field op://v2/x")
    assert "SEC" in out

