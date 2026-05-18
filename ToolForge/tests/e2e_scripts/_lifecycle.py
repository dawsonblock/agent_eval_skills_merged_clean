"""
E2E lifecycle helpers - direct Python API calls for ToolForge operations.

This module provides functions that call ToolForge core modules directly,
avoiding the overhead and potential hangs of spawning CLI subprocesses.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path

from packages.core.eval_generator import generate_eval as _generate_eval
from packages.core.mcp_generator import generate_mcp_server as _generate_mcp_server
from packages.core.package_builder import build_package
from packages.core.registry import ToolRegistry
from packages.core.skill_generator import generate_skill as _generate_skill
from packages.core.spec_from_prompt import generate_spec_from_prompt
from packages.core.tool_generator import scaffold_tool
from packages.core.tool_spec import ToolSpec


def create_workspace(tmp_root: Path) -> Path:
    """Create a ToolForge workspace in tmp_root."""
    workspace = tmp_root / "toolforge_workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    marker = workspace / ".toolforge"
    marker.mkdir(exist_ok=True)
    for subdir in ("tools/generated", "skills/generated", "evals/generated", "dist"):
        (workspace / subdir).mkdir(parents=True, exist_ok=True)
    registry_file = workspace / "toolforge_registry.json"
    registry_file.write_text("{}", encoding="utf-8")
    return workspace


def init_workspace(workspace: Path) -> None:
    """Initialize an existing workspace directory."""
    marker = workspace / ".toolforge"
    marker.mkdir(exist_ok=True)
    for subdir in ("tools/generated", "skills/generated", "evals/generated", "dist"):
        (workspace / subdir).mkdir(parents=True, exist_ok=True)
    registry_file = workspace / "toolforge_registry.json"
    if not registry_file.exists():
        registry_file.write_text("{}", encoding="utf-8")


def generate_tool_from_prompt(
    workspace: Path,
    prompt: str,
    slug: str | None = None,
    provider: str = "rule_based",
) -> ToolSpec:
    """Generate a tool spec and scaffold from a prompt."""
    spec = generate_spec_from_prompt(prompt, provider=provider)
    if slug:
        spec = spec.model_copy(update={"slug": slug})
    
    output_root = workspace / "tools" / "generated"
    scaffold_tool(spec, output_root, overwrite=True)
    
    # Register the tool
    registry = ToolRegistry(workspace / "toolforge_registry.json")
    registry.register(spec)
    
    return spec


def generate_mcp(workspace: Path, slug: str) -> None:
    """Generate MCP server for a tool."""
    tool_dir = workspace / "tools" / "generated" / slug
    spec = ToolSpec.from_yaml(tool_dir / "toolforge.yaml")
    _generate_mcp_server(spec, tool_dir, overwrite=True)
    
    registry = ToolRegistry(workspace / "toolforge_registry.json")
    registry.set_mcp_path(slug, tool_dir / "mcp")


def generate_skill(workspace: Path, slug: str) -> None:
    """Generate SKILL.md for a tool."""
    tool_dir = workspace / "tools" / "generated" / slug
    spec = ToolSpec.from_yaml(tool_dir / "toolforge.yaml")
    skill_root = tool_dir / "skill"
    _generate_skill(spec, skill_root, overwrite=True)
    
    registry = ToolRegistry(workspace / "toolforge_registry.json")
    registry.set_skill_path(slug, tool_dir / "skill")


def generate_eval(workspace: Path, slug: str) -> None:
    """Generate eval harness for a tool."""
    tool_dir = workspace / "tools" / "generated" / slug
    spec = ToolSpec.from_yaml(tool_dir / "toolforge.yaml")
    eval_root = tool_dir / "evals"
    _generate_eval(spec, eval_root, overwrite=True)


def validate_tool(workspace: Path, slug: str) -> None:
    """Validate a tool (schema, security, MCP, skill, eval, tests, safety)."""
    from packages.validators.schema_validator import validate_yaml_file
    from packages.validators.security_validator import enforce_security
    from packages.validators.mcp_validator import validate_mcp_server
    from packages.validators.skill_validator import validate_skill_file
    from packages.validators.test_validator import run_tests, run_safety_checks
    
    tool_dir = workspace / "tools" / "generated" / slug
    spec = ToolSpec.from_yaml(tool_dir / "toolforge.yaml")
    
    # Schema validation (re-parse to validate)
    validate_yaml_file(tool_dir / "toolforge.yaml")
    
    # Security validation
    enforce_security(spec)
    
    # MCP validation
    mcp_dir = tool_dir / "mcp"
    if mcp_dir.exists():
        errors = validate_mcp_server(spec, mcp_dir)
        if errors:
            raise AssertionError(f"MCP validation failed: {errors}")
    
    # Skill validation
    skill_dir = tool_dir / "skill"
    if skill_dir.exists():
        errors = validate_skill_file(skill_dir / "SKILL.md")
        if errors:
            raise AssertionError(f"Skill validation failed: {errors}")
    
    # Eval artifact validation
    eval_dir = tool_dir / "evals"
    if eval_dir.exists():
        # Check for task_config.json
        if not (eval_dir / "task_config.json").exists():
            raise ValueError(f"evals/task_config.json not found for {slug}")
    
    # Run tests
    test_report = run_tests(tool_dir, timeout=30)
    if not test_report.all_passed:
        raise AssertionError(f"Tests failed: {test_report.failures}")
    
    # Run safety checks
    safety_report = run_safety_checks(spec, tool_dir)
    if safety_report.errors > 0:
        raise AssertionError(f"Safety checks failed: {safety_report.failures}")


def package_tool(workspace: Path, slug: str) -> Path:
    """Build a distributable zip package for a tool."""
    tool_dir = workspace / "tools" / "generated" / slug
    dist_dir = workspace / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)
    
    spec = ToolSpec.from_yaml(tool_dir / "toolforge.yaml")
    package_path = build_package(spec, tool_dir, dist_dir)
    
    # Update registry with package path
    registry = ToolRegistry(workspace / "toolforge_registry.json")
    registry.set_package_path(slug, package_path)
    
    return package_path


def assert_registry_packaged(workspace: Path, slug: str) -> None:
    """Assert that a tool is registered with package path."""
    registry = ToolRegistry(workspace / "toolforge_registry.json")
    metadata = registry.get_metadata(slug)

    if metadata is None:
        raise AssertionError(f"Tool {slug} not found in registry")

    if not metadata.get("package_path"):
        raise AssertionError(f"Tool {slug} has no package path in registry")

    package_path = Path(metadata["package_path"])
    if not package_path.exists():
        raise AssertionError(f"Package path does not exist: {package_path}")


def read_registry(workspace: Path) -> dict:
    """Read the toolforge registry as a dict."""
    registry_file = workspace / "toolforge_registry.json"
    if not registry_file.exists():
        return {}
    return json.loads(registry_file.read_text(encoding="utf-8"))


def run_eval_internal(workspace: Path, slug: str) -> None:
    """Run eval harness internally for a tool."""
    from packages.runners.eval_runner import run_evals as _run_evals

    tool_dir = workspace / "tools" / "generated" / slug
    spec = ToolSpec.from_yaml(tool_dir / "toolforge.yaml")

    # Run eval harness
    report = _run_evals(spec, tool_dir)
    print(f"Eval pass rate: {report.pass_rate:.1%}")
    if not report.overall_pass:
        raise AssertionError(f"Eval failed: pass rate {report.pass_rate:.1%} < baseline {report.baseline_pass_rate:.1%}")


def assert_package_contains(zip_path: Path, required: list[str]) -> None:
    """Assert that zip file contains required files."""
    with zipfile.ZipFile(zip_path) as zf:
        names = set(zf.namelist())
        for expected in required:
            if expected not in names:
                raise AssertionError(
                    f"Zip {zip_path} missing expected file: {expected}"
                )


def assert_package_excludes(zip_path: Path, forbidden: list[str]) -> None:
    """Assert that zip file excludes files matching patterns."""
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
        for pattern in forbidden:
            for name in names:
                if pattern in name:
                    raise AssertionError(
                        f"Zip {zip_path} should exclude pattern "
                        f"'{pattern}' but found: {name}"
                    )
