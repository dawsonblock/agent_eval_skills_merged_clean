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


def _write_tree(tool_dir: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        path = tool_dir / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _assert_no_safety_errors(report: SafetyReport) -> None:
    errors = [issue for issue in report.issues if issue.severity == "error"]
    assert not errors, f"Unexpected safety errors: {[i.message for i in errors]}"


def _assert_safety_issue(report: SafetyReport, expected: str) -> None:
    haystack = "\n".join(
        f"{issue.code}: {issue.message}" for issue in report.issues if issue.severity == "error"
    )
    assert expected in haystack, haystack


def test_clean_tool_no_issues(tmp_path: Path) -> None:
    spec = _make_spec()
    _write_tool(tmp_path / "safety-test", "def run(inputs): return 'ok'\n")
    report = analyze_safety(spec, tmp_path / "safety-test")
    assert isinstance(report, SafetyReport)
    _assert_no_safety_errors(report)


def test_allows_tool_entrypoint_named_run(tmp_path: Path) -> None:
    spec = _make_spec()
    _write_tool(
        tmp_path / "safety-test",
        """
def run(input_path: str) -> dict:
    return {"ok": True}
""",
    )
    report = analyze_safety(spec, tmp_path / "safety-test")
    _assert_no_safety_errors(report)


def test_allows_importing_generated_tool_run_in_tests(tmp_path: Path) -> None:
    spec = _make_spec()
    tool_dir = tmp_path / "safety-test"
    _write_tree(
        tool_dir,
        {
            "tool.py": "def run(input_path: str) -> dict:\n    return {\"ok\": True}\n",
            "tests/test_tool.py": "from tool import run\n\ndef test_tool():\n    assert run('x')[\"ok\"]\n",
        },
    )
    report = analyze_safety(spec, tool_dir)
    _assert_no_safety_errors(report)


def test_allows_method_named_run(tmp_path: Path) -> None:
    spec = _make_spec()
    _write_tool(
        tmp_path / "safety-test",
        """
class Worker:
    def run(self):
        return True
""",
    )
    report = analyze_safety(spec, tmp_path / "safety-test")
    _assert_no_safety_errors(report)


def test_detects_hardcoded_secret(tmp_path: Path) -> None:
    spec = _make_spec()
    _write_tool(
        tmp_path / "safety-test",
        "API_KEY = 'sk-abc123secret'\ndef run(inputs): return 'ok'\n",
    )
    report = analyze_safety(spec, tmp_path / "safety-test")
    _assert_safety_issue(report, "HARDCODED_SECRET")


def test_detects_path_traversal(tmp_path: Path) -> None:
    spec = _make_spec()
    _write_tool(
        tmp_path / "safety-test",
        "path = '../../../etc/passwd'\ndef run(inputs): return open(path).read()\n",
    )
    report = analyze_safety(spec, tmp_path / "safety-test")
    assert any(i.code == "PATH_TRAVERSAL" for i in report.issues)


def test_detects_import_subprocess(tmp_path: Path) -> None:
    spec = _make_spec()
    _write_tool(tmp_path / "safety-test", "import subprocess\n")
    report = analyze_safety(spec, tmp_path / "safety-test")
    _assert_safety_issue(report, "subprocess")


def test_detects_subprocess_run_call(tmp_path: Path) -> None:
    spec = _make_spec()
    _write_tool(
        tmp_path / "safety-test",
        "import subprocess\nsubprocess.run(['echo', 'bad'])\n",
    )
    report = analyze_safety(spec, tmp_path / "safety-test")
    _assert_safety_issue(report, "subprocess.run")


def test_detects_subprocess_alias_run(tmp_path: Path) -> None:
    spec = _make_spec()
    _write_tool(
        tmp_path / "safety-test",
        "import subprocess as sp\nsp.run(['echo', 'bad'])\n",
    )
    report = analyze_safety(spec, tmp_path / "safety-test")
    _assert_safety_issue(report, "subprocess.run")


def test_detects_from_subprocess_import_run(tmp_path: Path) -> None:
    spec = _make_spec()
    _write_tool(
        tmp_path / "safety-test",
        "from subprocess import run\nrun(['echo', 'bad'])\n",
    )
    report = analyze_safety(spec, tmp_path / "safety-test")
    _assert_safety_issue(report, "subprocess.run")


def test_detects_os_system(tmp_path: Path) -> None:
    spec = _make_spec()
    _write_tool(tmp_path / "safety-test", "import os\nos.system('echo bad')\n")
    report = analyze_safety(spec, tmp_path / "safety-test")
    _assert_safety_issue(report, "os.system")


def test_detects_from_os_import_system(tmp_path: Path) -> None:
    spec = _make_spec()
    _write_tool(tmp_path / "safety-test", "from os import system\nsystem('echo bad')\n")
    report = analyze_safety(spec, tmp_path / "safety-test")
    _assert_safety_issue(report, "os.system")


def test_detects_eval(tmp_path: Path) -> None:
    spec = _make_spec()
    _write_tool(tmp_path / "safety-test", 'eval("1+1")\n')
    report = analyze_safety(spec, tmp_path / "safety-test")
    _assert_safety_issue(report, "eval")


def test_detects_exec(tmp_path: Path) -> None:
    spec = _make_spec()
    _write_tool(tmp_path / "safety-test", 'exec("print(1)")\n')
    report = analyze_safety(spec, tmp_path / "safety-test")
    _assert_safety_issue(report, "exec")


def test_does_not_flag_plain_words(tmp_path: Path) -> None:
    spec = _make_spec()
    _write_tool(
        tmp_path / "safety-test",
        """
system_name = "local"
def call_parser():
    return "ok"

def check_output_file(path):
    return path
""",
    )
    report = analyze_safety(spec, tmp_path / "safety-test")
    _assert_no_safety_errors(report)


def test_generated_csv_cleaner_passes_static_safety(tmp_path: Path) -> None:
    spec = _make_spec()
    tool_dir = tmp_path / "csv-cleaner"
    _write_tree(
        tool_dir,
        {
            "tool.py": (
                "def run(input_path: str) -> dict:\n"
                "    return {\"cleaned_path\": input_path}\n"
            ),
            "tests/test_csv_cleaner.py": (
                "from tool import run\n\n"
                "def test_csv_cleaner():\n"
                "    assert run('examples/input.csv')[\"cleaned_path\"]\n"
            ),
            "mcp/tool.py": "from tool import run\n",
            "mcp/server.py": (
                "from mcp.tool import run\n\n"
                "def handle(path: str):\n"
                "    return run(path)\n"
            ),
        },
    )
    report = analyze_safety(spec, tool_dir)
    _assert_no_safety_errors(report)


def test_generated_json_schema_validator_passes_static_safety(tmp_path: Path) -> None:
    spec = _make_spec()
    tool_dir = tmp_path / "json-schema-validator"
    _write_tree(
        tool_dir,
        {
            "tool.py": (
                "def run(data_path: str, schema_path: str) -> dict:\n"
                "    return {\"valid\": True}\n"
            ),
            "tests/test_json_schema_validator.py": (
                "from tool import run\n\n"
                "def test_validator():\n"
                "    assert run('examples/data_valid.json', 'examples/schema.json')[\"valid\"]\n"
            ),
            "mcp/tool.py": "from tool import run\n",
        },
    )
    report = analyze_safety(spec, tool_dir)
    _assert_no_safety_errors(report)


def test_generated_local_file_hasher_passes_static_safety(tmp_path: Path) -> None:
    spec = _make_spec()
    tool_dir = tmp_path / "local-file-hasher"
    _write_tree(
        tool_dir,
        {
            "tool.py": (
                "def run(file_path: str) -> dict:\n"
                "    return {\"algorithm\": \"sha256\", \"path\": file_path}\n"
            ),
            "tests/test_local_file_hasher.py": (
                "from tool import run\n\n"
                "def test_hasher():\n"
                "    assert run('examples/sample.txt')[\"algorithm\"] == 'sha256'\n"
            ),
            "mcp/server.py": (
                "from tool import run\n\n"
                "def handle(file_path: str):\n"
                "    return run(file_path)\n"
            ),
        },
    )
    report = analyze_safety(spec, tool_dir)
    _assert_no_safety_errors(report)
