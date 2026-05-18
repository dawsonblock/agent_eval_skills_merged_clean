"""Test registry CLI commands exit reliably without hanging."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.e2e_scripts._process import run_process_tree


def test_registry_list_exits_cleanly() -> None:
    """Test registry list command exits without hanging."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Initialize workspace
        result = run_process_tree(
            [sys.executable, "-m", "apps.cli.toolforge_cli.main", "init", str(tmp_path)],
            cwd=tmp_path,
            env={"TOOLFORGE_TEST_USE_MODULE_CLI": "1"},
            timeout=30,
        )
        assert result.returncode == 0
        
        # Create a tool to register
        result = run_process_tree(
            [
                sys.executable,
                "-m",
                "apps.cli.toolforge_cli.main",
                "new",
                "tool",
                "--from-prompt",
                "Create a tool that cleans CSV files",
            ],
            cwd=tmp_path,
            env={"TOOLFORGE_TEST_USE_MODULE_CLI": "1"},
            timeout=120,
        )
        assert result.returncode == 0
        
        # Test registry list
        result = run_process_tree(
            [sys.executable, "-m", "apps.cli.toolforge_cli.main", "registry", "list"],
            cwd=tmp_path,
            env={"TOOLFORGE_TEST_USE_MODULE_CLI": "1"},
            timeout=30,
        )
        assert result.returncode == 0
        assert "csv-cleaner" in result.stdout.lower()


def test_registry_info_exits_cleanly() -> None:
    """Test registry info command exits without hanging."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # Initialize workspace
        result = run_process_tree(
            [sys.executable, "-m", "apps.cli.toolforge_cli.main", "init", str(tmp_path)],
            cwd=tmp_path,
            env={"TOOLFORGE_TEST_USE_MODULE_CLI": "1"},
            timeout=30,
        )
        assert result.returncode == 0
        
        # Create a tool to register
        result = run_process_tree(
            [
                sys.executable,
                "-m",
                "apps.cli.toolforge_cli.main",
                "new",
                "tool",
                "--from-prompt",
                "Create a tool that cleans CSV files",
            ],
            cwd=tmp_path,
            env={"TOOLFORGE_TEST_USE_MODULE_CLI": "1"},
            timeout=120,
        )
        assert result.returncode == 0
        
        # Test registry info
        result = run_process_tree(
            [sys.executable, "-m", "apps.cli.toolforge_cli.main", "registry", "info", "csv-cleaner"],
            cwd=tmp_path,
            env={"TOOLFORGE_TEST_USE_MODULE_CLI": "1"},
            timeout=30,
        )
        assert result.returncode == 0
        assert "csv-cleaner" in result.stdout.lower()
        assert "version" in result.stdout.lower()
