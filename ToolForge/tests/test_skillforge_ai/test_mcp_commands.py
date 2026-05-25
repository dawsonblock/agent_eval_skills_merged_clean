from __future__ import annotations

import json
import signal
from pathlib import Path

import pytest

from skillforge_ai.commands import mcp as mcp_commands


def _seed_state(tmp_path: Path, payload: dict[str, dict[str, object]]) -> None:
    state_path = tmp_path / ".skillforge" / "runs" / "mcp_processes.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(payload), encoding="utf-8")


def test_list_running_servers_marks_pid_mismatch_not_running(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    slug = "csv-cleaner"
    _seed_state(
        tmp_path,
        {
            slug: {
                "pid": 12345,
                "server_path": "/tmp/expected/server.py",
                "command": ["python", "/tmp/expected/server.py"],
            }
        },
    )

    monkeypatch.setattr(mcp_commands, "_is_pid_running", lambda _pid: True)
    monkeypatch.setattr(
        mcp_commands,
        "_pid_command_line",
        lambda _pid: "python /tmp/other/server.py",
    )

    rows = mcp_commands.list_running_servers(tmp_path)

    assert len(rows) == 1
    assert rows[0]["slug"] == slug
    assert rows[0]["running"] is False


def test_stop_managed_server_refuses_pid_mismatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    slug = "csv-cleaner"
    _seed_state(
        tmp_path,
        {
            slug: {
                "pid": 45678,
                "server_path": "/tmp/expected/server.py",
                "command": ["python", "/tmp/expected/server.py"],
            }
        },
    )

    kill_calls: list[tuple[int, int]] = []

    monkeypatch.setattr(mcp_commands, "_is_pid_running", lambda _pid: True)
    monkeypatch.setattr(
        mcp_commands,
        "_pid_command_line",
        lambda _pid: "python /tmp/unrelated/process.py",
    )
    monkeypatch.setattr(
        mcp_commands.os,
        "kill",
        lambda pid, sig: kill_calls.append((pid, sig)),
    )

    with pytest.raises(RuntimeError, match="Refusing to stop pid"):
        mcp_commands.stop_managed_server(tmp_path, slug)

    assert kill_calls == []
    assert slug in mcp_commands._read_state(tmp_path)


def test_stop_managed_server_terminates_matching_pid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    slug = "csv-cleaner"
    _seed_state(
        tmp_path,
        {
            slug: {
                "pid": 78901,
                "server_path": "/tmp/expected/server.py",
                "command": ["python", "/tmp/expected/server.py"],
            }
        },
    )

    kill_calls: list[tuple[int, int]] = []
    running_states = iter([True, False])

    monkeypatch.setattr(mcp_commands, "_process_matches_entry", lambda _pid, _entry: True)
    monkeypatch.setattr(
        mcp_commands,
        "_is_pid_running",
        lambda _pid: next(running_states, False),
    )
    monkeypatch.setattr(
        mcp_commands.os,
        "kill",
        lambda pid, sig: kill_calls.append((pid, sig)),
    )

    stopped = mcp_commands.stop_managed_server(tmp_path, slug)

    assert stopped is True
    assert kill_calls == [(78901, signal.SIGTERM)]
    assert slug not in mcp_commands._read_state(tmp_path)
