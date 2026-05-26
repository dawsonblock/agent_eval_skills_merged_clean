from __future__ import annotations

from pathlib import Path

from apps.local_deepseek_demo.toolforge_adapter import ToolForgeAdapter


def _write_dummy_tool(workspace: Path, slug: str = "demo-tool") -> tuple[str, str]:
    tool_dir = workspace / "tools" / "generated" / slug
    tool_dir.mkdir(parents=True, exist_ok=True)
    entry = tool_dir / "tool.py"
    entry.write_text(
        "from __future__ import annotations\n\n"
        "import json\n"
        "import os\n\n"
        "def main() -> int:\n"
        "    print(json.dumps({'ok': True, 'inputs': os.environ.get('TOOLFORGE_INPUTS', '{}')}))\n"
        "    return 0\n\n"
        "if __name__ == '__main__':\n"
        "    raise SystemExit(main())\n",
        encoding="utf-8",
    )
    return str(entry.relative_to(workspace)), str(tool_dir.relative_to(workspace))


def _write_dummy_spec(workspace: Path, slug: str = "demo-tool") -> None:
    spec_path = workspace / "tools" / "generated" / slug / "toolforge.yaml"
    spec_path.write_text(
        "name: demo-tool\n"
        "slug: demo-tool\n"
        "description: Demo tool\n"
        "language: python\n"
        "entry_point: tool.py\n"
        "parameters:\n"
        "  - name: request\n"
        "    type: string\n"
        "    description: Request text\n"
        "    required: true\n"
        "output:\n"
        "  type: object\n"
        "  description: Demo output\n"
        "security:\n"
        "  required_capabilities: [read_files]\n"
        "  requires_network: false\n"
        "  requires_shell: false\n"
        "  requires_filesystem: true\n"
        "  allowed_read_paths: ['./**']\n"
        "  allowed_write_paths: ['./generated_tools/_outputs/**']\n"
        "sandbox_level: 2\n",
        encoding="utf-8",
    )


def test_validate_tool_request_blocks_path_traversal(tmp_path: Path) -> None:
    adapter = ToolForgeAdapter(tmp_path)
    entrypoint, working_dir = _write_dummy_tool(tmp_path)

    adapter.registry.register_tool(
        {
            "name": "demo-tool",
            "type": "python",
            "entrypoint": entrypoint,
            "working_dir": working_dir,
            "description": "demo",
            "permissions": ["read_files"],
            "risk_level": "low",
            "validated": True,
            "mcp_server": None,
        }
    )

    result = adapter.validate_tool_request("demo-tool", {"path": "../secrets.txt"})
    assert result["allowed"] is False
    assert any("Blocked path access" in msg for msg in result["errors"])


def test_create_tool_from_plan_generates_expected_files(tmp_path: Path) -> None:
    adapter = ToolForgeAdapter(tmp_path)
    plan = {
        "tool_name": "csv analyzer",
        "purpose": "Analyze CSV files safely",
    }

    result = adapter.create_tool_from_plan(plan)

    assert result["tool_name"] == "csv-analyzer"
    assert result["validation"]["passed"] is True

    generated = tmp_path / "generated_tools" / "csv-analyzer"
    assert (generated / "tool.py").exists()
    assert (generated / "toolforge.yaml").exists()
    assert (generated / "README.md").exists()


def test_plan_tool_creation_returns_safety_metadata(tmp_path: Path) -> None:
    adapter = ToolForgeAdapter(tmp_path)

    plan = adapter.plan_tool_creation("create a csv helper tool")

    assert "tool_name" in plan
    assert "safety_risks" in plan
    assert isinstance(plan["safety_risks"], list)
    assert plan["safety_risks"]


def test_validate_tool_request_rejects_unknown_arg_key(tmp_path: Path) -> None:
    adapter = ToolForgeAdapter(tmp_path)
    entrypoint, working_dir = _write_dummy_tool(tmp_path)
    _write_dummy_spec(tmp_path)

    adapter.registry.register_tool(
        {
            "name": "demo-tool",
            "type": "python",
            "entrypoint": entrypoint,
            "working_dir": working_dir,
            "description": "demo",
            "permissions": ["read_files"],
            "risk_level": "low",
            "validated": True,
            "mcp_server": None,
        }
    )

    result = adapter.validate_tool_request(
        "demo-tool",
        {"request": "ok", "extra": "not-allowed"},
    )

    assert result["allowed"] is False
    assert any("Unknown argument keys" in msg for msg in result["errors"])


def test_validate_tool_request_requires_required_arg(tmp_path: Path) -> None:
    adapter = ToolForgeAdapter(tmp_path)
    entrypoint, working_dir = _write_dummy_tool(tmp_path)
    _write_dummy_spec(tmp_path)

    adapter.registry.register_tool(
        {
            "name": "demo-tool",
            "type": "python",
            "entrypoint": entrypoint,
            "working_dir": working_dir,
            "description": "demo",
            "permissions": ["read_files"],
            "risk_level": "low",
            "validated": True,
            "mcp_server": None,
        }
    )

    result = adapter.validate_tool_request("demo-tool", {})

    assert result["allowed"] is False
    assert any("Missing required argument" in msg for msg in result["errors"])
