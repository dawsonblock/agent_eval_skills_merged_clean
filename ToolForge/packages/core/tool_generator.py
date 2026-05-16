"""
Tool generator — scaffolds tool implementation files from a ToolSpec.

Creates:
  tools/generated/{slug}/
    ├── toolforge.yaml    (the spec)
    ├── tool.py           (implementation stub)
    ├── README.md
    └── tests/
        └── test_{slug}.py
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from packages.core.tool_spec import ToolSpec
from packages.core.generator_utils import render_template, write_rendered, TOOLFORGE_VERSION


def _ctx(spec: ToolSpec) -> dict[str, Any]:
    type_map = {"string": "str", "number": "float", "integer": "int",
                "boolean": "bool", "array": "list", "object": "dict"}
    output_type = type_map.get(spec.output.type, "Any")
    return {
        "spec": spec,
        "toolforge_version": TOOLFORGE_VERSION,
        "output_type": output_type,
    }


def scaffold_tool(spec: ToolSpec, output_root: Path, overwrite: bool = False) -> list[Path]:
    """
    Scaffold a tool directory at *output_root/{spec.slug}/*.
    Returns list of written file paths.
    """
    tool_dir = output_root / spec.slug
    tool_dir.mkdir(parents=True, exist_ok=True)
    (tool_dir / "tests").mkdir(exist_ok=True)

    ctx = _ctx(spec)
    written: list[Path] = []

    # --- toolforge.yaml ---
    spec_path = tool_dir / "toolforge.yaml"
    if not spec_path.exists() or overwrite:
        spec.to_yaml(spec_path)
        written.append(spec_path)

    # --- tool.py (implementation stub) ---
    tool_py = tool_dir / "tool.py"
    content = render_template("mcp_server_python", "tool.py.j2", ctx)
    if write_rendered(tool_py, content, overwrite):
        written.append(tool_py)

    # --- README.md ---
    readme = tool_dir / "README.md"
    content = render_template("readme_template", "README.md.j2", ctx)
    if write_rendered(readme, content, overwrite):
        written.append(readme)

    # --- tests/test_{slug}.py ---
    test_py = tool_dir / "tests" / f"test_{spec.slug.replace('-', '_')}.py"
    test_content = _generate_test(spec)
    if write_rendered(test_py, test_content, overwrite):
        written.append(test_py)

    return written


def _generate_test(spec: ToolSpec) -> str:
    """Generate a minimal pytest test file for the tool."""
    slug_id = spec.slug.replace("-", "_")
    lines = [
        "\"\"\"",
        f"Auto-generated tests for {spec.slug}.",
        "\"\"\"",
        "import pytest",
        "import sys",
        "from pathlib import Path",
        "",
        "sys.path.insert(0, str(Path(__file__).parent.parent))",
        "from tool import run",
        "",
    ]
    if spec.eval.cases:
        for case in spec.eval.cases:
            fn = f"test_{slug_id}_{case.id.replace('-', '_').replace(' ', '_')}"
            lines.append(f"def {fn}():")
            lines.append(f'    """Eval case: {case.description or case.id}"""')
            kw = ", ".join(f"{k}={v!r}" for k, v in case.inputs.items())
            lines.append(f"    result = run({kw})")
            if case.expected_output is not None:
                lines.append(f"    assert result == {case.expected_output!r}")
            else:
                lines.append("    assert result is not None")
            lines.append("")
    else:
        lines += [
            f"def test_{slug_id}_smoke():",
            '    """Smoke test — ensure run() is importable and raises NotImplementedError."""',
            "    with pytest.raises(NotImplementedError):",
            "        run()",
            "",
        ]
    return "\n".join(lines)
