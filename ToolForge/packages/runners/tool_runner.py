"""
Tool runner — loads a tool spec from disk and executes the tool in a sandbox.
"""
from __future__ import annotations

import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from packages.core.tool_spec import ToolSpec
from packages.core.path_safety import validate_path, PathViolationError
from packages.runners.sandbox_runner import SandboxResult, run_in_sandbox


@dataclass
class ToolRunResult:
    output: str
    error: str
    elapsed_ms: float
    exit_code: int

    @property
    def success(self) -> bool:
        return self.exit_code == 0


def run_tool(
    spec: ToolSpec,
    tool_dir: Path,
    inputs: dict,
    timeout_s: float = 30.0,
    env: dict[str, str] | None = None,
) -> ToolRunResult:
    """
    Execute the tool described by *spec* located at *tool_dir*.

    The tool's entry-point is called with *inputs* serialised to JSON on stdin.
    The subprocess is expected to write its output to stdout.

    Returns a ToolRunResult.
    """
    entry_point = tool_dir / spec.entry_point
    if not entry_point.exists():
        return ToolRunResult(
            output="",
            error=f"Entry point not found: {entry_point}",
            elapsed_ms=0.0,
            exit_code=1,
        )

    # Determine interpreter / command
    if spec.language.value == "typescript":
        cmd = ["node", str(entry_point)]
    else:
        cmd = [sys.executable, str(entry_point)]

    # Pass inputs via environment variable to avoid shell injection
    run_env = dict(env or {})
    run_env["TOOLFORGE_INPUTS"] = json.dumps(inputs)

    # Validate file paths before execution (path safety enforcement)
    for param_name, param_value in inputs.items():
        if isinstance(param_value, str) and (param_name.endswith("_path") or param_name.endswith("_file")):
            # This is a file path parameter — validate it
            allowed_read = getattr(spec.security, "allowed_read_paths", [])
            allowed_write = getattr(spec.security, "allowed_write_paths", [])
            
            # Guess if this is a read or write path based on context
            # For now, check against both lists
            allowed = allowed_read + allowed_write if (allowed_read or allowed_write) else None
            try:
                validate_path(param_value, allowed, str(tool_dir))
            except PathViolationError as e:
                return ToolRunResult(
                    output="",
                    error=f"Path validation failed: {e}",
                    elapsed_ms=0.0,
                    exit_code=1,
                )


    start = time.monotonic()
    result: SandboxResult = run_in_sandbox(
        cmd=cmd,
        sandbox_level=spec.sandbox_level,
        timeout_s=timeout_s,
        env=run_env,
        cwd=str(tool_dir),
    )
    elapsed_ms = (time.monotonic() - start) * 1000

    return ToolRunResult(
        output=result.stdout,
        error=result.stderr,
        elapsed_ms=elapsed_ms,
        exit_code=result.exit_code,
    )
