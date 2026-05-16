"""Unit tests for packages.core.safety_analyzer."""
from __future__ import annotations

from pathlib import Path

from packages.core.safety_analyzer import SafetyReport, analyze_safety
from packages.core.tool_spec import SecuritySpec, ToolLanguage, ToolSpec


def _make_spec(requires_network: bool = False) -> ToolSpec:
    return ToolSpec(
        name="Safety Test",
        slug="safety-test",
        version="0.1.0",
        description="Tool for safety testing",
        language=ToolLanguage.PYTHON,
        entry_point="tool.py",
        security=SecuritySpec(requires_network=requires_network),
    )


def _write_tool(tool_dir: Path, content: str) -> None:
    tool_dir.mkdir(parents=True, exist_ok=True)
    (tool_dir / "tool.py").write_text(content, encoding="utf-8")


def test_clean_tool_no_issues(tmp_path: Path) -> None:
    spec = _make_spec()
    _write_tool(tmp_path / "safety-test", "def run(inputs): return 'ok'\n")
    report = analyze_safety(spec, tmp_path / "safety-test")
    assert isinstance(report, SafetyReport)
    assert report.issue_count == 0


def test_detects_hardcoded_secret(tmp_path: Path) -> None:
    spec = _make_spec()
    _write_tool(
        tmp_path / "safety-test",
        "API_KEY = 'sk-abc123secret'\ndef run(inputs): return 'ok'\n",
    )
    report = analyze_safety(spec, tmp_path / "safety-test")
    assert report.issue_count > 0


def test_detects_path_traversal(tmp_path: Path) -> None:
    spec = _make_spec()
    _write_tool(
        tmp_path / "safety-test",
        "path = '../../../etc/passwd'\ndef run(inputs): return open(path).read()\n",
    )
    report = analyze_safety(spec, tmp_path / "safety-test")
    assert report.issue_count > 0


def test_detects_shell_exec(tmp_path: Path) -> None:
    spec = _make_spec()
    _write_tool(
        tmp_path / "safety-test",
        "import os\nos.system('rm -rf /')\ndef run(inputs): return 'ok'\n",
    )
    report = analyze_safety(spec, tmp_path / "safety-test")
    assert report.issue_count > 0
