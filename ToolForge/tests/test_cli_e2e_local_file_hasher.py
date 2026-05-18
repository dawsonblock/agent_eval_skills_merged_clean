"""CLI end-to-end smoke for local-file-hasher proof path."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def test_cli_e2e_local_file_hasher() -> None:
    """Run local-file-hasher e2e lifecycle in isolated subprocess."""
    root = Path(__file__).parent.parent
    script_path = root / "tests" / "e2e_scripts" / "run_local_file_hasher_e2e.py"

    # Build clean environment
    env = os.environ.copy()
    for key in (
        "PYTEST_CURRENT_TEST",
        "PYTEST_VERSION",
        "PYTEST_ADDOPTS",
        "PYTEST_PLUGINS",
        "COVERAGE_PROCESS_START",
    ):
        env.pop(key, None)
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUNBUFFERED"] = "1"

    # Set PYTHONPATH
    paths = [str(root), str(root / "apps" / "cli")]
    existing_pythonpath = env.get("PYTHONPATH", "")
    if existing_pythonpath:
        paths.append(existing_pythonpath)
    env["PYTHONPATH"] = os.pathsep.join(paths)

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        timeout=180,
    )

    if result.returncode != 0:
        raise AssertionError(
            f"E2E script failed with return code {result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

