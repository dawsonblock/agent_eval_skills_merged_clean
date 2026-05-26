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


def test_validate_tool_request_enforces_enum_and_length(tmp_path: Path) -> None:
    adapter = ToolForgeAdapter(tmp_path)
    entrypoint, working_dir = _write_dummy_tool(tmp_path, slug="enum-tool")

    spec_path = tmp_path / "tools" / "generated" / "enum-tool" / "toolforge.yaml"
    spec_path.write_text(
        "name: enum-tool\n"
        "slug: enum-tool\n"
        "description: Enum test tool\n"
        "language: python\n"
        "entry_point: tool.py\n"
        "parameters:\n"
        "  - name: mode\n"
        "    type: string\n"
        "    description: Mode\n"
        "    required: true\n"
        "    enum: [safe, fast]\n"
        "  - name: request\n"
        "    type: string\n"
        "    description: Request text\n"
        "    required: true\n"
        "    min_length: 3\n"
        "    max_length: 8\n"
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

    adapter.registry.register_tool(
        {
            "name": "enum-tool",
            "type": "python",
            "entrypoint": entrypoint,
            "working_dir": working_dir,
            "description": "enum",
            "permissions": ["read_files"],
            "risk_level": "low",
            "validated": True,
            "mcp_server": None,
        }
    )

    result = adapter.validate_tool_request(
        "enum-tool",
        {"mode": "unsafe", "request": "ok"},
    )

    assert result["allowed"] is False
    assert any("must be one of" in msg for msg in result["errors"])
    assert any("length must be >=" in msg for msg in result["errors"])


def test_validate_tool_request_enforces_numeric_bounds(tmp_path: Path) -> None:
    adapter = ToolForgeAdapter(tmp_path)
    entrypoint, working_dir = _write_dummy_tool(tmp_path, slug="bounds-tool")

    spec_path = tmp_path / "tools" / "generated" / "bounds-tool" / "toolforge.yaml"
    spec_path.write_text(
        "name: bounds-tool\n"
        "slug: bounds-tool\n"
        "description: Bounds test tool\n"
        "language: python\n"
        "entry_point: tool.py\n"
        "parameters:\n"
        "  - name: score\n"
        "    type: number\n"
        "    description: Score\n"
        "    required: true\n"
        "    minimum: 0\n"
        "    maximum: 1\n"
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

    adapter.registry.register_tool(
        {
            "name": "bounds-tool",
            "type": "python",
            "entrypoint": entrypoint,
            "working_dir": working_dir,
            "description": "bounds",
            "permissions": ["read_files"],
            "risk_level": "low",
            "validated": True,
            "mcp_server": None,
        }
    )

    result = adapter.validate_tool_request("bounds-tool", {"score": 2})

    assert result["allowed"] is False
    assert any("must be <=" in msg for msg in result["errors"])


def test_validate_tool_request_enforces_array_item_bounds(tmp_path: Path) -> None:
    adapter = ToolForgeAdapter(tmp_path)
    entrypoint, working_dir = _write_dummy_tool(tmp_path, slug="array-tool")

    spec_path = tmp_path / "tools" / "generated" / "array-tool" / "toolforge.yaml"
    spec_path.write_text(
        "name: array-tool\n"
        "slug: array-tool\n"
        "description: Array bounds test tool\n"
        "language: python\n"
        "entry_point: tool.py\n"
        "parameters:\n"
        "  - name: items\n"
        "    type: array\n"
        "    description: Values\n"
        "    required: true\n"
        "    min_items: 2\n"
        "    max_items: 3\n"
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

    adapter.registry.register_tool(
        {
            "name": "array-tool",
            "type": "python",
            "entrypoint": entrypoint,
            "working_dir": working_dir,
            "description": "array",
            "permissions": ["read_files"],
            "risk_level": "low",
            "validated": True,
            "mcp_server": None,
        }
    )

    result = adapter.validate_tool_request("array-tool", {"items": [1]})
    assert result["allowed"] is False
    assert any("item count must be >=" in msg for msg in result["errors"])

    result = adapter.validate_tool_request("array-tool", {"items": [1, 2, 3, 4]})
    assert result["allowed"] is False
    assert any("item count must be <=" in msg for msg in result["errors"])


def test_validate_tool_request_enforces_object_required_keys(tmp_path: Path) -> None:
    adapter = ToolForgeAdapter(tmp_path)
    entrypoint, working_dir = _write_dummy_tool(tmp_path, slug="object-tool")

    spec_path = tmp_path / "tools" / "generated" / "object-tool" / "toolforge.yaml"
    spec_path.write_text(
        "name: object-tool\n"
        "slug: object-tool\n"
        "description: Object required keys test tool\n"
        "language: python\n"
        "entry_point: tool.py\n"
        "parameters:\n"
        "  - name: config\n"
        "    type: object\n"
        "    description: Config object\n"
        "    required: true\n"
        "    required_keys: [mode, path]\n"
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

    adapter.registry.register_tool(
        {
            "name": "object-tool",
            "type": "python",
            "entrypoint": entrypoint,
            "working_dir": working_dir,
            "description": "object",
            "permissions": ["read_files"],
            "risk_level": "low",
            "validated": True,
            "mcp_server": None,
        }
    )

    result = adapter.validate_tool_request(
        "object-tool",
        {"config": {"mode": "safe"}},
    )
    assert result["allowed"] is False
    assert any("missing required keys" in msg for msg in result["errors"])
