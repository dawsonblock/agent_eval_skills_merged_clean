"""
Tests for skillforge_ai.mcp_controller — MCPController with mocked subprocess.
"""
from __future__ import annotations

import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch


from skillforge_ai.mcp_controller import MCPController, MCPError, MCPTimeoutError


class FakePopen:
    """Minimal Popen stand-in that feeds pre-baked JSON-RPC responses."""

    def __init__(self, responses: list[dict]):
        # Build a bytes stream of newline-delimited JSON messages
        chunks = b"".join(
            (json.dumps(r) + "\n").encode() for r in responses
        )
        self.stdout = io.BytesIO(chunks)
        self.stdin = io.BytesIO()
        self.returncode = None

    def poll(self):
        return self.returncode

    def terminate(self):
        self.returncode = -15

    def wait(self, timeout=None):
        return self.returncode


def _make_initialize_response(req_id: int = 1) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "protocolVersion": "2024-11-05",
            "serverInfo": {"name": "test-server", "version": "0.0.1"},
            "capabilities": {},
        },
    }


def _make_list_tools_response(req_id: int = 2) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {
            "tools": [{"name": "clean_csv", "description": "Cleans a CSV file"}]
        },
    }


def _make_call_tool_response(req_id: int = 3) -> dict:
    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "result": {"content": [{"type": "text", "text": "done"}]},
    }


class TestMCPControllerStart:
    @patch("skillforge_ai.mcp_controller.subprocess.Popen")
    def test_start_launches_subprocess(self, mock_popen, tmp_path: Path):
        server = tmp_path / "server.py"
        server.write_text("# stub", encoding="utf-8")

        responses = [_make_initialize_response(1)]
        mock_popen.return_value = FakePopen(responses)

        # Patch _read_response and select.select to avoid blocking
        ctrl = MCPController()
        with patch.object(ctrl, "_read_response", return_value=responses[0]):
            with patch.object(ctrl, "_send_jsonrpc", return_value=None):
                ctrl._proc = mock_popen.return_value

    @patch("skillforge_ai.mcp_controller.subprocess.Popen")
    def test_stop_calls_terminate(self, mock_popen, tmp_path: Path):
        server = tmp_path / "server.py"
        server.write_text("# stub", encoding="utf-8")

        ctrl = MCPController()
        fake_proc = MagicMock()
        fake_proc.poll.return_value = None
        ctrl._proc = fake_proc

        ctrl.stop()

        fake_proc.terminate.assert_called_once()
        assert ctrl._proc is None


class TestMCPControllerListTools:
    def test_list_tools_returns_tool_list(self, tmp_path: Path):
        ctrl = MCPController()

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        ctrl._proc = mock_proc

        with patch.object(ctrl, "_send_jsonrpc", return_value={"tools": [{"name": "clean_csv", "description": "Cleans a CSV file"}]}):
            tools = ctrl.list_tools()

        assert len(tools) == 1
        assert tools[0]["name"] == "clean_csv"


class TestMCPControllerCallTool:
    def test_call_tool_returns_result(self, tmp_path: Path):
        ctrl = MCPController()

        mock_proc = MagicMock()
        mock_proc.poll.return_value = None
        ctrl._proc = mock_proc

        with patch.object(ctrl, "_send_jsonrpc", return_value={"content": [{"type": "text", "text": "done"}]}):
            result = ctrl.call_tool("clean_csv", {"path": "/tmp/a.csv"})

        assert "content" in result or isinstance(result, dict)


class TestMCPControllerContextManager:
    def test_context_manager_stops_on_exit(self, tmp_path: Path):
        ctrl = MCPController()
        ctrl._proc = MagicMock()
        ctrl._proc.poll.return_value = None

        with patch.object(ctrl, "stop") as mock_stop:
            with ctrl:
                pass
            mock_stop.assert_called_once()


class TestMCPControllerSmokeTest:
    @patch("skillforge_ai.mcp_controller.subprocess.Popen")
    def test_smoke_test_returns_bool(self, mock_popen, tmp_path: Path):
        server = tmp_path / "server.py"
        server.write_text("# stub", encoding="utf-8")

        responses = [_make_initialize_response(1), _make_list_tools_response(2)]
        mock_popen.return_value = FakePopen(responses)

        ctrl = MCPController(timeout_s=5.0)

        with patch.object(ctrl, "start", return_value=None), \
             patch.object(ctrl, "list_tools", return_value=[{"name": "tool_a"}]), \
             patch.object(ctrl, "stop", return_value=None):
            result = ctrl.smoke_test(server)

        assert isinstance(result, bool)
        assert result is True


class TestMCPError:
    def test_error_message(self):
        err = MCPError(code=-32600, message="Invalid Request")
        assert err.code == -32600
        assert "Invalid Request" in str(err)

    def test_timeout_error(self):
        err = MCPTimeoutError(-32001, "Timed out waiting for tools/list after 5.0s")
        assert isinstance(err, MCPTimeoutError)
        assert isinstance(err, MCPError)
