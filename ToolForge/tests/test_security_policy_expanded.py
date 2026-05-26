"""Expanded security policy tests for ToolForge guardrails."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from packages.core.path_safety import PathViolationError, validate_path_input
from packages.core.process_timeout import ProcessTimeoutError
from packages.core.tool_spec import ToolLanguage, ToolSpec
from packages.runners.sandbox_runner import _minimal_env, run_in_sandbox
from packages.validators.security_validator import validate_security


def _make_spec(**kwargs) -> ToolSpec:
    defaults = {
        "name": "Security Expanded Tool",
        "slug": "security-expanded-tool",
        "version": "0.1.0",
        "description": "Security policy expanded tests",
        "language": ToolLanguage.PYTHON,
        "entry_point": "tool.py",
    }
    defaults.update(kwargs)
    return ToolSpec(**defaults)


def test_path_traversal_rejected() -> None:
    spec = _make_spec(
        security={
            "requires_filesystem": True,
            "allowed_write_paths": ["./outputs/**"],
        }
    )

    with pytest.raises(PathViolationError):
        validate_path_input("output_path", "../escape/out.txt", spec.security, Path.cwd())


def test_symlink_escape_rejected(tmp_path: Path) -> None:
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    inputs = tmp_path / "inputs"
    inputs.mkdir()
    link = inputs / "linked.txt"
    link.symlink_to(outside)

    spec = _make_spec(
        security={
            "requires_filesystem": True,
            "allowed_read_paths": ["./inputs/**"],
        }
    )

    with pytest.raises(PathViolationError):
        validate_path_input("input_path", str(link.relative_to(tmp_path)), spec.security, tmp_path)


def test_secret_env_is_stripped_from_minimal_env() -> None:
    env = _minimal_env(
        {
            "OPENAI_API_KEY": "secret",
            "AWS_SECRET": "secret",
            "SAFE_FLAG": "ok",
        }
    )

    assert "OPENAI_API_KEY" not in env
    assert "AWS_SECRET" not in env
    assert env.get("SAFE_FLAG") == "ok"


def test_network_disabled_in_docker_sandbox(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, list[str]] = {}

    class _Proc:
        def __init__(self) -> None:
            self.stdout = ""
            self.stderr = ""
            self.returncode = 0

    def _fake_run(cmd, capture_output, text, timeout):  # noqa: ANN001
        captured["cmd"] = list(cmd)
        return _Proc()

    monkeypatch.setattr("packages.runners.sandbox_runner.subprocess.run", _fake_run)

    result = run_in_sandbox(["python", "-c", "print('ok')"], sandbox_level=3, timeout_s=1)

    assert result.exit_code == 0
    assert "--network=none" in captured["cmd"]


def test_write_outside_root_rejected(tmp_path: Path) -> None:
    spec = _make_spec(
        security={
            "requires_filesystem": True,
            "allowed_write_paths": ["./outputs/**"],
        }
    )

    with pytest.raises(PathViolationError):
        validate_path_input("output_path", "/tmp/out.txt", spec.security, tmp_path)


def test_dangerous_shell_command_rejected() -> None:
    spec = _make_spec(
        security={
            "requires_shell": True,
            "allowed_commands": ["sudo ls -la"],
        }
    )

    violations = validate_security(spec)
    assert any("blocked pattern" in item for item in violations)


def test_timeout_enforced(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_timeout(*args, **kwargs):  # noqa: ANN002, ANN003
        raise ProcessTimeoutError("timeout")

    monkeypatch.setattr(
        "packages.runners.sandbox_runner.run_with_process_tree_timeout",
        _raise_timeout,
    )

    result = run_in_sandbox(
        [sys.executable, "-c", "import time; time.sleep(2)"],
        sandbox_level=2,
        timeout_s=0.2,
    )

    assert result.timed_out is True
    assert result.exit_code == -1
