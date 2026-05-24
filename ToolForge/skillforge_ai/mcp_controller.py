"""
MCPController — lifecycle manager and JSON-RPC 2.0 client for MCP servers.

Manages a single MCP server subprocess (Python or Node.js) via stdio transport.
Implements the MCP initialize + tools/list + tools/call handshake.

Usage::

    ctrl = MCPController(evidence_logger=ev, timeout_s=30)
    ctrl.start(Path("tools/generated/csv-cleaner/mcp/server.py"))

    tools = ctrl.list_tools()
    result = ctrl.call_tool("clean_csv", {"input_path": "data.csv"})

    ctrl.stop()

    # Or as context manager:
    with MCPController() as ctrl:
        ctrl.start(server_path)
        ...
"""
from __future__ import annotations

import json
import logging
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_JSONRPC_VERSION = "2.0"


class MCPError(Exception):
    """Raised for MCP protocol-level errors (server returned an error object)."""

    def __init__(self, code: int, message: str, data: Any = None) -> None:
        self.code = code
        self.data = data
        super().__init__(f"MCP error {code}: {message}")


class MCPTimeoutError(MCPError):
    """Raised when an MCP call times out."""


class MCPController:
    """
    Start and communicate with an MCP server over subprocess stdio.

    Only one server process is managed at a time.  Call stop() before
    start() to switch servers.
    """

    def __init__(
        self,
        evidence_logger: Any | None = None,
        timeout_s: float = 30.0,
    ) -> None:
        self._ev = evidence_logger
        self._timeout = timeout_s
        self._proc: subprocess.Popen | None = None
        self._request_id = 0
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> "MCPController":
        return self

    def __exit__(self, *_) -> None:
        self.stop()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(
        self,
        server_path: Path,
        server_type: str | None = None,
        extra_env: dict[str, str] | None = None,
    ) -> None:
        """
        Launch the MCP server at *server_path*.

        *server_type* is inferred from the file extension when not provided:
        ``.py`` → python, ``.js`` / ``.ts`` → node.
        """
        if self._proc is not None:
            raise RuntimeError("Server already running.  Call stop() first.")

        cmd = self._build_cmd(server_path, server_type)
        import os

        env = {**os.environ, **(extra_env or {})}
        logger.debug("Starting MCP server: %s", cmd)
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            bufsize=0,
        )
        # Initialize the MCP session
        try:
            self._initialize()
        except Exception as exc:
            logger.error("MCP initialize failed: %s", exc)
            self.stop()
            raise

    def stop(self) -> None:
        """Terminate the MCP server subprocess gracefully."""
        if self._proc is None:
            return
        try:
            self._proc.stdin.close()  # type: ignore[union-attr]
            self._proc.terminate()
            self._proc.wait(timeout=5)
        except Exception as exc:
            logger.debug("Error stopping MCP server: %s", exc)
            try:
                self._proc.kill()
            except Exception:
                pass
        finally:
            self._proc = None
            self._request_id = 0

    # ------------------------------------------------------------------
    # MCP methods
    # ------------------------------------------------------------------

    def list_tools(self) -> list[dict[str, Any]]:
        """Return the list of tools exposed by the server."""
        result = self._send_jsonrpc("tools/list", {})
        return result.get("tools", [])

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Call a tool on the MCP server.

        Returns the tool result dict.
        Logs the call via EvidenceLogger if configured.
        """
        from skillforge_ai.models import ToolCallRequest

        request = ToolCallRequest(
            tool="mcp",
            action=name,
            arguments=arguments,
        )

        try:
            result = self._send_jsonrpc(
                "tools/call",
                {"name": name, "arguments": arguments},
            )
            success = True
        except Exception as exc:
            if self._ev:
                try:
                    self._ev.log_tool_call(request, str(exc), success=False)
                except Exception:
                    pass
            raise

        if self._ev:
            try:
                self._ev.log_tool_call(request, result, success=success)
            except Exception:
                pass

        return result

    def run_sequence(
        self, calls: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """
        Execute a sequence of ``{name, arguments}`` dicts in order.
        Returns a list of results in the same order.
        """
        results: list[dict[str, Any]] = []
        for call in calls:
            results.append(self.call_tool(call["name"], call.get("arguments", {})))
        return results

    def smoke_test(self, server_path: Path, server_type: str | None = None) -> bool:
        """
        Start the server, list tools, and stop.  Returns True on success.
        """
        try:
            self.start(server_path, server_type)
            tools = self.list_tools()
            self.stop()
            logger.info("MCP smoke test passed — %d tool(s) listed", len(tools))
            return True
        except Exception as exc:
            logger.warning("MCP smoke test failed: %s", exc)
            self.stop()
            return False

    # ------------------------------------------------------------------
    # Internal JSON-RPC
    # ------------------------------------------------------------------

    def _initialize(self) -> None:
        """Send the MCP initialize request."""
        self._send_jsonrpc(
            "initialize",
            {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "skillforge", "version": "0.1.0"},
            },
        )
        # Send initialized notification (no response expected)
        notification = {
            "jsonrpc": _JSONRPC_VERSION,
            "method": "notifications/initialized",
            "params": {},
        }
        self._write_message(notification)

    def _next_id(self) -> int:
        with self._lock:
            self._request_id += 1
            return self._request_id

    def _send_jsonrpc(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON-RPC 2.0 request and return the result dict."""
        if self._proc is None:
            raise RuntimeError("MCP server is not running.  Call start() first.")

        request_id = self._next_id()
        message = {
            "jsonrpc": _JSONRPC_VERSION,
            "id": request_id,
            "method": method,
            "params": params,
        }
        self._write_message(message)
        return self._read_response(request_id)

    def _write_message(self, message: dict[str, Any]) -> None:
        """Write a newline-delimited JSON message to stdin."""
        assert self._proc and self._proc.stdin
        payload = (json.dumps(message) + "\n").encode("utf-8")
        self._proc.stdin.write(payload)
        self._proc.stdin.flush()

    def _read_response(self, expected_id: int) -> dict[str, Any]:
        """
        Read lines from stdout until we find the response matching *expected_id*.
        Raises MCPTimeoutError on timeout, MCPError on server error.
        """
        import select

        assert self._proc and self._proc.stdout

        deadline_remaining = self._timeout
        accumulated = b""

        while deadline_remaining > 0:
            # Use select for non-blocking check with timeout
            try:
                ready, _, _ = select.select([self._proc.stdout], [], [], min(1.0, deadline_remaining))
            except (ValueError, OSError):
                break

            if not ready:
                deadline_remaining -= 1.0
                # Check if process died
                if self._proc.poll() is not None:
                    stderr_data = b""
                    try:
                        stderr_data = self._proc.stderr.read(1024)  # type: ignore[union-attr]
                    except Exception:
                        pass
                    raise MCPError(-32603, f"Server process exited early. stderr: {stderr_data.decode('utf-8', errors='replace')}")
                continue

            chunk = self._proc.stdout.read1(4096)  # type: ignore[attr-defined]
            if not chunk:
                raise MCPError(-32603, "Server closed stdout unexpectedly")

            accumulated += chunk

            # Try to parse each newline-terminated JSON object
            while b"\n" in accumulated:
                line, accumulated = accumulated.split(b"\n", 1)
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line.decode("utf-8"))
                except json.JSONDecodeError:
                    continue

                # Notifications have no "id" — ignore them
                if "id" not in msg:
                    continue

                if msg.get("id") != expected_id:
                    # Response for a different request — discard
                    continue

                if "error" in msg:
                    err = msg["error"]
                    raise MCPError(
                        err.get("code", -1),
                        err.get("message", "unknown MCP error"),
                        err.get("data"),
                    )

                return msg.get("result", {})

        raise MCPTimeoutError(-32001, f"Timed out waiting for response to request {expected_id}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_cmd(self, server_path: Path, server_type: str | None) -> list[str]:
        ext = server_path.suffix.lower()
        if server_type == "python" or (server_type is None and ext == ".py"):
            return [sys.executable, str(server_path)]
        if server_type in ("node", "javascript", "typescript") or ext in (".js", ".ts"):
            return ["node", str(server_path)]
        # Fallback: treat as Python
        return [sys.executable, str(server_path)]

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None
